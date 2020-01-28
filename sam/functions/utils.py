import requests
import backoff
import boto3
import botocore
import time
import logging
import json
from jinja2 import Template
import os
from datetime import date,timedelta
from slackclient import SlackClient


# Tokens for substitution in the parameter templates.
tokens = {
  "today":  date.today().strftime('%Y-%m-%d'),
  "yesterday": (date.today() - timedelta(1)).strftime('%Y-%m-%d')
}

sleeptime=2

# Must have an environment variable for Error Topic that is the arn
# to the ERROR SNS topic.
error_topic = os.environ['ERROR_TOPIC']
sns = boto3.client('sns')

# Set up a ParamError Exception to throw if we have any error
# pulling SSM params.
class ParamError(Exception):
  pass

# slack_notify(config, text) sends the specified text to the slack channel
# specified in the SLACK_CHANNEL environment variable, using the
# SLACK_TOKEN environment variable. If either of those as missing,
# it skips the slack message and logs it being missing.
def slack_notify(config, text):

  if ("slack" in config) and ("slack_token" in config["slack"]) and ("slack_channel" in config["slack"]):

    sc = SlackClient(config['slack']['slack_token'])

    try:
      sc.api_call(
        "chat.postMessage",
        channel=config['slack']['slack_channel'],
        text=os.path.basename(__file__).upper().replace('.PY', "") + " - " + text
      )
    except Exception as e:
      print("Slack Post Error: ", e.read())

  else:
    print("No valid slack config specified - can not notify via Slack")


# fatal_code handles backoff/requests exceptions
def fatal_code(e):
  try:
    return 400 <= e.response.status_code < 500
  except Exception as e:
    logging.info("Requests Exception" + str(e))
    return e

def backoff_hdlr(details):
  logging.info("Backing off {wait:0.1f} seconds afters {tries} tries "
        "calling function {target} with args {args} and kwargs "
        "{kwargs}".format(**details))

# Decorate get requests with backoff, set up to do exponential backoff retries
@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException,
                      max_time=300,
                      giveup=fatal_code,
                      on_backoff=backoff_hdlr)
def get_url(*args, **kwargs):
    return requests.get(*args, **kwargs)

# Decorate post requests with backoff, set up to do exponential backoff retries
@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException,
                      max_time=300,
                      giveup=fatal_code,
                      on_backoff=backoff_hdlr)
def post_url(*args, **kwargs):
    return requests.post(*args, **kwargs)

# Decorate put requests with backoff, set up to do exponential backoff retries
@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException,
                      max_time=300,
                      giveup=fatal_code,
                      on_backoff=backoff_hdlr)
def put_url(*args, **kwargs):
  return requests.put(*args, **kwargs)


# Decorate delete requests with backoff, set up to do exponential backoff retries
@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException,
                      max_time=300,
                      giveup=fatal_code)
def delete_url(*args, **kwargs):
    return requests.delete(*args, **kwargs)



# hier2dict creates a dictionary out of the parameter hierarchy - it is a recursive function.
def hier2dict(items, existing_dict, value):
  if (len(items) == 1) :
    existing_dict[items[0]] = value
  else:
    if (items[0] not in existing_dict):
      existing_dict[items[0]] = {}
    this_key = items.pop(0)
    if (isinstance(value, list)):
      hier2dict(items, existing_dict[this_key], value)
    else:
      hier2dict(items, existing_dict[this_key], value.replace("[", "{").replace("]", "}").replace("urlhead", "http"))



# getParamInfo() grabs the hierarchy of parameters from the SSM Parameter store.
def getParamInfo():

  ssm = boto3.client('ssm')

  outputs = {}
  nexttoken = ""
  paramdata = False
  while(1):
    if (nexttoken == ""):
      try:
        paramdata = ssm.get_parameters_by_path(Path=os.environ['SSMPATHROOT'], Recursive=True, WithDecryption=True, MaxResults=10)
      except botocore.exceptions.ClientError as e:
        raise ParamError(str(e))
    else:
      try:
        paramdata = ssm.get_parameters_by_path(Path=os.environ['SSMPATHROOT'], Recursive=True, MaxResults=10, WithDecryption=True,
                                             NextToken=nexttoken)
      except botocore.exceptions.ClientError as e:
        raise ParamError(str(e))
    if ("DEBUG" in os.environ): print("Paramdata: ", paramdata)

    data = paramdata['Parameters']
    for param in data:
      pathcheck = param.get("Name").replace(os.environ['SSMPATHROOT'], "")
      items = pathcheck.split("/")
      if (items[0] == ""):
        items.pop(0)
      if (param.get("Type") == "StringList"):
        vallist = param.get("Value").split(",")
        logging.debug("IsInstance: " + str(isinstance(vallist, list)))
        hier2dict(items, outputs, vallist)
      else:
        hier2dict(items, outputs, param.get("Value"))

    if ("NextToken" in paramdata):
      nexttoken = paramdata["NextToken"]
    else:
      break

  return(outputs)

# template_values(items,params,tokens) goes through the hierarchy, doing template
# substitution to replace all jinja2 tokens.
def template_values(items, params, tokens):
  #print ("Entry Items:", items)
  for item in items:
    if (isinstance(items[item], dict)):
      template_values(items[item], params, tokens)
    elif (isinstance(items[item],list)):
      logging.debug(item + ": " + json.dumps(items[item]))
      next
    else:
      #print("Templated Items: ", items[item])
      try:
        urltpl = Template(items[item])
      except Exception as e:
        print("Error: ", e)
      items[item] = urltpl.render(tokens=tokens, params=params)


# req_check, given an athena client and a query execution id as arguments, will wait for
# success or failure, and return the status once one of those occurs.
def req_check (athena, qid):
  mystatus = ""
  # Until the status var is set to "COMPLETED", keep checking the status of the request
  # with a sleep interval between each check
  while(mystatus != "SUCCEEDED" and mystatus != "FAILED") :
    time.sleep(sleeptime)
    try:
      testcheck = athena.get_query_execution(QueryExecutionId=qid)
    except botocore.exceptions.ClientError as e:
      print("Error: ", e)
    if ("DEBUG" in os.environ): print("Test Check Output: ")
    if ("DEBUG" in os.environ): print(testcheck)
    mystatus = testcheck.get("QueryExecution").get("Status").get("State")
    if ("DEBUG" in os.environ): print (mystatus)

  print ("Check Complete - moving on")
  return mystatus

# athena_query(query) executes the specified query and returns the
# resulting rows - it handles pagination appropriately, and returns
# the *entire* result set...
def athena_query(config, query):

  # Get AWS Account and Region runtime information
  try:
    aws_account = boto3.client('sts').get_caller_identity().get('Account')
  except Exception as e:
    logging.error("Get Account Info Error: %s" % e)
  logging.debug("AWS Account: %s" % aws_account)
  try:
    aws_region = boto3.session.Session().region_name
  except botocore.exceptions.ClientError as e:
    logging.errors("Get Region Info Error: %s" % e)
  logging.debug("AWS Region: %s" % aws_region)

  output_location = "s3://aws-athena-results-" + aws_account + "-" + aws_region + "/"
  logging.debug("Output Location: %s" % output_location)
  athena = boto3.client('athena')

  try:
    create_response = athena.start_query_execution(
      QueryString=query,
      QueryExecutionContext={
        'Database': config['athena_db']
      },
      ResultConfiguration={
        'OutputLocation': output_location
      }
    )
  except botocore.exceptions.ClientError as e:
    logging.error("Athena Query Execution Error: %s" % e)
    message = "Athena Query Execution Error - Query Failed: %s, Error: %s" % (query, e)
    sns.publish(TopicArn=error_topic, Message=message)
    slack_notify(config,message)

  logging.debug("Response: %s" % create_response)

  try:
    qid = create_response.get("QueryExecutionId")
  except botocore.exceptions.ClientError as e:
    logging.info("Get Athena QID Error: %s" % e)
    message = "Athena Error - Get ID Failed: %s, Error: %s" % (query, e)
    sns.publish(TopicArn=error_topic, Message=message)
    slack_notify(config,message)


  logging.info("Checking Create Query: %s" % qid)

  response = req_check(athena, qid)
  if ( response == "SUCCEEDED"):
    logging.info("Query Succeeded")
  else:
    logging.error("Athena Query Failed with message: %s" % response)
    message = "Athena Query check Error - Query Failed: %s, Response: %s" % (query, response)
    sns.publish(TopicArn=error_topic, Message=message)
    slack_notify(config,message)

  next = True
  results = []
  iteration = 0
  while next:
    try:
      if next == True:
        response = athena.get_query_results(
          QueryExecutionId=qid,
          MaxResults=1000
        )
      elif next != False:
        response = athena.get_query_results(
          QueryExecutionId=qid,
          NextToken=next,
          MaxResults=1000
        )
    except botocore.exceptions.ClientError as e:
      logging.error("Athena get Results Error: %s" % e)
      message = "Athena Query getResults Error - Query Failed: %s, Error: %s" % (query, e)
      sns.publish(TopicArn=error_topic, Message=message)
      slack_notify(config,message)

    if 'ResultSet' in response and "Rows" in response['ResultSet']:
      logging.debug ("LEN: %d" % len(response['ResultSet']['Rows']))
      if iteration > 0:
        response['ResultSet']['Rows'].pop(0)
      else:
        iteration += 1
      results = results + response['ResultSet']['Rows']
    if 'NextToken' in response:
      next = response['NextToken']
    else:
      next = False

  if len(results) > 0:
    logging.debug("Results: %s" % results)
    return results
  else:
    logging.debug("No Rows Found")
    return []