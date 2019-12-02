from utils import *
import logging
import json
import hashlib
import sys
import re
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

def getSpaceWhiteList(config):
  dynamo = boto3.client("dynamodb")
  if ("dynamo_table" in config) and ("name" in config['dynamo_table']):
    response = dynamo.scan(TableName=config['dynamo_table']['name'])
  else:
    logging.info("Dynamo Configuration missing from SSM")

  logging.debug("Response: " + json.dumps(response))
  if ("Count" in response) and (response['Count'] > 0):
    spaces = []
    items = response['Items']
    for item in items:
      spaces.append(item['space']['S'])

  logging.debug("Spaces: " + json.dumps(spaces))
  return spaces

def getWikiPages(config):
  content = {}
  spaces = getSpaceWhiteList(config)

  for space in spaces:
    murl = config['wiki']['url'] + "/rest/api/content/search?cql=space.key=" + space + "+AND+Type=page&expand=metadata.labels,history.lastUpdated&limit=1000"


    for result in getWikiPagination(config,murl):
      logging.debug("Result: " + json.dumps(result))
      resurl = config['wiki']['uiurl'] + result['_links']['webui']
      m = hashlib.sha256()

      m.update(resurl.encode("utf-8"))
      content_id = "CONFLUENCE-" + str(m.hexdigest())

      content[resurl] = {
        "ContentID": content_id,
        "ContentType": "article",
        "Title": result['title'],
        "Owners": result['history']['lastUpdated']['by']['displayName']
      }

      if ("labels" in result['metadata']):
        labres = result['metadata']['labels']['results']
        label_count = 1
        for label in labres:
          # Degreed recommends no more than 20 topics assigned to a piece of content,
          # so we only take the first 20 labels.
          if (label_count > 20):
            break
          logging.debug ("Label: " + json.dumps(label))
          topic = "Topic" + str(label_count)
          content[resurl][topic] = label['name']
          label_count += 1
      logging.debug("Result URL: " + resurl)
      logging.info("Content: " + json.dumps(content[resurl]))
  return content

def getAllWikiPages(config):
  active_pages = []
  if ("item_limit" in config['wiki']):
    item_limit = int(config['wiki']['item_limit'])
  else:
    item_limit = 100
  murl = config['wiki']['url'] + '/rest/searchv3/1.0/search?type=page'
  o = get_url(murl, auth=HTTPBasicAuth(config['wiki']['username'], config['wiki']['passwd']))
  logging.info("Raw: " + o.text)
  res = o.json()
  logging.info("Res of All: " + json.dumps(res))
  total_count = int(res['total'])
  logging.info("Total Count: " + str(total_count))
  batches = int(total_count / item_limit) + 1
  logging.info("Number of Batches = " + str(batches))
  start = 0;
  while(start < total_count):
    page_block = {"start": start, "limit": item_limit}
    active_pages.append(page_block)
    start += item_limit

  return active_pages

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

def getDegreedArticles(config):
  articles = {}
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
          articles[article['attributes']['url']] = {
            "ContentID": article['id'],
            "ContentType": "article",
            "Title": article['attributes']['title']
          }

    if ("links" in response_data) and ("next" in response_data['links']):
      next_url = response_data['links']['next']

  logging.info("Articles Response: " + json.dumps(articles))
  return articles


def lambda_handler(event, context):
  config = getParamInfo()
  template_values(config,config,tokens)
  logging.debug("Config: " + json.dumps(config))
  url_list = getAllWikiPages(config)
  logging.info("Page List Params: " + json.dumps(url_list))
  #wiki_content = getWikiPages(config)
  #degreed_content = getDegreedArticles(config)

  #logging.info("Wiki Content: " + json.dumps(wiki_content))

