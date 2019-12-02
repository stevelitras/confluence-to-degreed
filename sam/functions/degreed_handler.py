from utils import *
import logging
import json
#import hashlib
import sys
import re
import csv
import tempfile
import boto3
#from requests.auth import HTTPBasicAuth
from collections import OrderedDict


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

def getDegreedArticles(config):
  #articles = {}
  scopes = "content:read,pathways:read"

  if ("degreed" not in config):
    logging.error("Degreed configuration not specified")
    return False

  if ("article_limit" in config['degreed']):
    art_limit = config['degreed']['article_limit']
  else:
    art_limit = 100
  # First Authenticate
  auth_data = {
    "grant_type": "client_credentials",
    "client_id": config['degreed']['client_id'],
    "client_secret": config['degreed']['client_secret'],
    "scope": scopes
  }
  o = post_url(config['degreed']['oauthurl'], data=auth_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
  logging.debug("Post Response: " + json.dumps(o.json()))
  token = o.json()['access_token']

  headers = {"Authorization": "Bearer " + token}
  logging.debug("Headers: " + json.dumps(headers))
  murl = config['degreed']['url'] + "/content/articles?limit=" + str(art_limit)
  next_url = ''
  first_time = True

  targ_file = tempfile.NamedTemporaryFile(delete=False)
  mfields = ["ContentID", "url", "ContentType", "Title"]

  with open(targ_file.name, mode='w') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=mfields)
    #writer.writeheader()


    while (first_time) or (next_url != ''):
      first_time=False
      if (next_url != ''):
        murl = next_url

      contentr = get_url(murl, headers=headers)
      response_data = contentr.json()
      if ("data" not in response_data):
        logging.info("No data elements in response")
        break
      else:
        art_resp = response_data['data']

        for article in art_resp:
          if (re.search('(wiki.autodesk.com)', article['attributes']['url']) == None):
            logging.debug("Rejected: " + json.dumps(article))
          else:
            mreq = OrderedDict()
            mreq["ContentID"] = article['id']
            mreq["url"] = article['attributes']['url']
            mreq["ContentType"] = "article"
            mreq["Title"] = article['attributes']['title']
            logging.info("Writing Record: " + json.dumps(mreq))
            writer.writerow(mreq)

      if ("links" in response_data) and ("next" in response_data['links']):
        next_url = response_data['links']['next']
  s3 = boto3.client('s3')
  response = s3.upload_file(targ_file.name, os.environ['RESULTS_BUCKET'], "degreed/articles.csv")
  logging.debug("S3 Response: " + json.dumps(response))
  os.environ['ATHENA_DB'] = "confluencetodegreed"
  aquery = "CREATE DATABASE IF NOT EXISTS confluencetodegreed"
  results = athena_query(aquery)
  logging.debug("Results: " + json.dumps(results))
  aquery = "CREATE EXTERNAL TABLE IF NOT EXISTS `degreed_articles` ("
  for field in mfields:
    aquery += " `" + field + "` string,\n"
  aquery = aquery[:-2]
  aquery += ")\n"
  aquery += "ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde' \n"

  aquery += "WITH SERDEPROPERTIES ('escapeChar'='\\\'', 'quoteChar'='\\\"', 'separatorChar'=',')\n"
  aquery += "LOCATION 's3://" + os.environ['RESULTS_BUCKET'] + "/degreed/'"

  logging.info("Athena Query: " + aquery)
  rows = athena_query(aquery)
  logging.debug("Query Results: " + json.dumps(rows))

def lambda_handler(event, context):
  config = getParamInfo()
  template_values(config,config,tokens)
  logging.debug("Config: " + json.dumps(config))

  getDegreedArticles(config)


