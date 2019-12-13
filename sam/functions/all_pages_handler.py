from utils import *
import logging
import json
import sys
import csv
import tempfile
import os
from requests.auth import HTTPBasicAuth

# Setting up some pseudo constants
LOG_LEVEL = logging.INFO if ("DEBUG" not in os.environ) else logging.DEBUG

#logging.basicConfig(format='%(asctime)s - %(message)s', level=LOG_LEVEL)
root = logging.getLogger()
root.setLevel(LOG_LEVEL)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(LOG_LEVEL)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)


def getAllWikiPages(config, params):
  targ_file = tempfile.NamedTemporaryFile(delete=False)
  s3 = boto3.client('s3')

  murl = config['wiki']['url'] + '/rest/api/content?type=page&start=' + str(params['start']) + "&limit=" + str(params['limit'])
  logging.info("Retrieving Payload")
  try:
    o = get_url(murl, auth=HTTPBasicAuth(config['wiki']['username'], config['wiki']['passwd']), timeout=300)
  except Exception as e:
    logging.info("get_url Exception: " + str(e))
    return("Retrieval Failed")



  logging.debug("Raw: " + o.text)
  logging.info("Retrieved Payload: " + str(o.status_code))
  res = o.json()
  results = res['results']
  logging.info("WRiting CSV File")
  with open(targ_file.name, mode='w') as csv_file:
    csv_writer = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)

    for result in results:
      logging.debug("Overall URL Result: " + config['wiki']['uiurl'] + result['_links']['webui'])
      logging.debug("Overall URL Result: " + config['wiki']['uiurl'] + result['_links']['tinyui'])
      logging.debug("Overall URL Result: " + config['wiki']['uiurl'] + "/pages/viewpage.action?pageId=" + result['id'])
      csv_writer.writerow([config['wiki']['uiurl'] + result['_links']['webui']])
      csv_writer.writerow([config['wiki']['uiurl'] + result['_links']['tinyui']])
      csv_writer.writerow([config['wiki']['uiurl'] + "/pages/viewpage.action?pageId=" + result['id']])

  logging.info("CSV File written")

  logging.info("Uploading to S3")
  response = s3.upload_file(targ_file.name, os.environ['RESULTS_BUCKET'], "allpages/" + str(params['start']) + ".csv")
  logging.debug("S3 Response: " + json.dumps(response))
  logging.info("Past Upload")

  os.environ['ATHENA_DB'] = "confluencetodegreed"

  logging.info("Creating DB if necessary")
  aquery = "CREATE DATABASE IF NOT EXISTS confluencetodegreed"
  results = athena_query(aquery)
  logging.debug("Results: " + json.dumps(results))
  logging.info("DB Creation step done")

  aquery = """CREATE EXTERNAL TABLE IF NOT EXISTS `page_inventory` (
      `url` string
  )
  ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
  WITH SERDEPROPERTIES ('escapeChar'='\\\'', 'quoteChar'='\\\"', 'separatorChar'=',')
  LOCATION 's3://"""
  aquery += os.environ['RESULTS_BUCKET'] + "/allpages/'"

  logging.info("Execution Athena Query: " + aquery)
  rows = athena_query(aquery)
  logging.debug("Query Results: " + json.dumps(rows))
  logging.info("Athena table create step complete")
  return ("Success")

def lambda_handler(event, context):
  config = getParamInfo()
  template_values(config,config,tokens)
  logging.debug("Config: " + json.dumps(config))
  logging.info("Event: " + json.dumps(event))
  return getAllWikiPages(config, event)
