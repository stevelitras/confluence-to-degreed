from utils import *
import logging
import json
import hashlib
import sys
import tempfile
import csv
from collections import OrderedDict
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



def getWikiPages(config, event):
  content = []
  s3 = boto3.client('s3')
  logging.info("In getWikiPages, event: " + json.dumps(event))
  space = event['space']

  murl = config['wiki']['url'] + "/rest/api/content/search?cql=space.key=" + space + "+AND+Type=page&expand=metadata.labels,history.lastUpdated&limit=1000"

  for result in getWikiPagination(config,murl):
    logging.debug("Result: " + json.dumps(result))
    resurl = config['wiki']['uiurl'] + result['_links']['webui']
    m = hashlib.sha256()

    m.update(resurl.encode("utf-8"))
    content_id = "CONFLUENCE-" + str(m.hexdigest())

    # NEED TO SERIALIZE FOR CSV
    foo = OrderedDict()
    foo["ContentID"] = content_id
    foo["url"] = resurl
    foo["ContentType"] = "article"
    foo["Title"] = result['title']
    foo["Owners"] = result['history']['lastUpdated']['by']['displayName']

    if ("labels" in result['metadata']):
      labres = result['metadata']['labels']['results']
      label_count = 1
      max_labels = 0
      if ("max_labels" in config['wiki']):
        label_top = int(config['wiki']['max_labels'])
      else:
        label_top = 20
      for label in labres:
        # Degreed recommends no more than 20 topics assigned to a piece of content,
        # so we only take the first 20 labels.
        if (label_count > label_top):
          break
        logging.debug ("Label: " + json.dumps(label))
        topic = "Topic" + str(label_count)
        foo[topic] = label['name']
        label_count += 1
        max_labels = max(max_labels, label_count)
    content.append(foo)
    logging.debug("Result URL: " + resurl)
    logging.info("Content: " + json.dumps(foo))

  mfields = ["ContentID", "url", "ContentType", "Title", "Owners"]

  m_iter = 1
  while(m_iter <= label_top):
    topic = "Topic" + str(m_iter)
    logging.info("Topic: " + topic)
    mfields.append(topic)
    m_iter += 1
  logging.info("Fields: " + json.dumps(mfields))
  targ_file = tempfile.NamedTemporaryFile(delete=False)

  with open(targ_file.name, mode='w') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=mfields)
    #writer.writeheader()
    for record in content:
      logging.info("Record: " + json.dumps(record))
      writer.writerow(record)

  response = s3.upload_file(targ_file.name, os.environ['RESULTS_BUCKET'], "spaces/" + space + ".csv")
  logging.debug("S3 Response: " + json.dumps(response))
  os.environ['ATHENA_DB'] = "confluencetodegreed"
  aquery = "CREATE DATABASE IF NOT EXISTS confluencetodegreed"
  results = athena_query(aquery)
  logging.debug("Results: " + json.dumps(results))
  aquery = "CREATE EXTERNAL TABLE IF NOT EXISTS `wiki_spaces` ("
  for field in mfields:
    aquery += " `" + field + "` string,\n"
  aquery = aquery[:-2]
  aquery += ")\n"
  aquery += "ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde' \n"

  aquery += "WITH SERDEPROPERTIES ('escapeChar'='\\\'', 'quoteChar'='\\\"', 'separatorChar'=',')\n"
  aquery += "LOCATION 's3://" + os.environ['RESULTS_BUCKET'] + "/spaces/'"

  logging.info("Athena Query: " + aquery)
  rows = athena_query(aquery)
  logging.debug("Query Results: " + json.dumps(rows))
  return content

def getWikiPagination(config, url):

    first_time=True
    next_url = ""
    while (first_time == True) or (next_url != ""):
      first_time = False
      if(next_url != ''):
        murl = next_url
      else:
        murl = url
      logging.info("MURL: " + murl)
      o = get_url(murl, auth=HTTPBasicAuth(config['wiki']['username'], config['wiki']['passwd']))
      logging.info("Response: " + json.dumps(o.json()))
      response = o.json()
      results = response['results']
      for result in results:
        yield result
      if ("_links" in response) and ("next" in response['_links']):
        next_url = response['_links']['base'] + response['_links']['next']
      else:
        next_url = ""
      logging.info("First Time: " + str(first_time) + " - Next URL: " + next_url)


def lambda_handler(event, context):
  config = getParamInfo()
  template_values(config,config,tokens)
  logging.debug("Config: " + json.dumps(config))
  logging.info("Event: " + json.dumps(event))
  url_list = getWikiPages(config, event)
  logging.info("Page List Params: " + json.dumps(url_list))
  #wiki_content = getWikiPages(config)
  #degreed_content = getDegreedArticles(config)

  #logging.info("Wiki Content: " + json.dumps(wiki_content))

