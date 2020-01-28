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

# This pulls the metadata for all "pages" in the specific space.
# The "event" contains the space key to retrieve.
def getWikiPages(config, event):
  content = []
  s3 = boto3.client('s3')
  logging.info("In getWikiPages, event: " + json.dumps(event))
  space = event['space']

  murl = config['wiki']['url'] + "/rest/api/content/search?cql=space.key=" + space + "+AND+Type=page&expand=metadata.labels,history.lastUpdated&limit=1000"

  for result in getWikiPagination(config,murl):
    logging.debug("Result: " + json.dumps(result))
    resurl = config['wiki']['uiurl'] + result['_links']['webui']

    # the scheme for the content id for degreed is the string "CONFLUENCE-" 
    # plus a sha256 hash of the URL. This ensures consistency, and allows
    # data in the internal catalog to be easily identified as Confluence
    # based.
    m = hashlib.sha256()
    m.update(resurl.encode("utf-8"))
    content_id = "CONFLUENCE-" + str(m.hexdigest())

    # NEED TO SERIALIZE FOR CSV
    temp_dict = OrderedDict()
    temp_dict["ContentID"] = content_id
    temp_dict['id'] = result['id']
    temp_dict["url"] = resurl
    temp_dict["ContentType"] = "article"
    temp_dict["Title"] = result['title']
    temp_dict["Owners"] = result['history']['lastUpdated']['by']['displayName']

    # Grab labels from the wiki metadata, and up to 20 of them
    # will get added as Topics in the output. This enables the 
    # "tagging" for skills. 
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
        temp_dict[topic] = label['name']
        label_count += 1
        max_labels = max(max_labels, label_count)
        
    # Add to the content output.
    content.append(temp_dict)
    logging.debug("Result URL: " + resurl)
    logging.debug("Content: " + json.dumps(temp_dict))

  # Set up the fieldnames for future...
  mfields = ["ContentID", "id", "url", "ContentType", "Title", "Owners"]

  # Topics 1...20
  m_iter = 1
  while(m_iter <= label_top):
    topic = "Topic" + str(m_iter)
    logging.debug("Topic: " + topic)
    mfields.append(topic)
    m_iter += 1
  logging.debug("Fields: " + json.dumps(mfields))
  targ_file = tempfile.NamedTemporaryFile(delete=False)

  # Write the CSV file
  with open(targ_file.name, mode='w') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=mfields)
    for record in content:
      logging.debug("Record: " + json.dumps(record))
      writer.writerow(record)

  # Upload to the S3 bucket...
  response = s3.upload_file(targ_file.name, os.environ['RESULTS_BUCKET'], "spaces/" + space + ".csv")
  logging.debug("S3 Response: " + json.dumps(response))
  
  if "athena_db" not in config:
    config['athena_db'] = "confluencetodegreed"

  aquery = "CREATE DATABASE IF NOT EXISTS confluencetodegreed"
  results = athena_query(config, aquery)
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
  rows = athena_query(config, aquery)
  logging.debug("Query Results: " + json.dumps(rows))
  return content

def getWikiPagination(config, url):

  total_pages = 0
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
    logging.info("Request Response: %d, %s" % (o.status_code, o.reason))
    logging.debug("Response: " + json.dumps(o.json()))
    response = o.json()
    results = response['results']
    logging.info("Retrieved: %d records" % len(results))
    total_pages += len(results)
    for result in results:
      yield result
    if ("_links" in response) and ("next" in response['_links']):
      next_url = response['_links']['base'] + response['_links']['next']
    else:
      next_url = ""
    logging.info("First Time: " + str(first_time) + " - Next URL: " + next_url)
  logging.info("Total Results: %d" % total_pages)


def lambda_handler(event, context):
  config = getParamInfo()
  template_values(config,config,tokens)
  logging.debug("Config: " + json.dumps(config))
  logging.info("Event: " + json.dumps(event))
  url_list = getWikiPages(config, event)
  #return url_list
  #logging.info("Page List Params: " + json.dumps(url_list))
  #wiki_content = getWikiPages(config)
  #degreed_content = getDegreedArticles(config)

  #logging.info("Wiki Content: " + json.dumps(wiki_content))

