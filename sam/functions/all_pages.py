from utils import *
import logging
import json
import sys
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

def getAllWikiPages(config):
  active_pages = []
  if ("item_limit" in config['wiki']):
    item_limit = int(config['wiki']['item_limit'])
  else:
    item_limit = 100
  murl = config['wiki']['url'] + '/rest/searchv3/1.0/search?type=page'
  o = get_url(murl, auth=HTTPBasicAuth(config['wiki']['username'], config['wiki']['passwd']))
  logging.debug("Raw: " + o.text)
  res = o.json()
  logging.debug("Res of All: " + json.dumps(res))
  total_count = int(res['total'])
  batches = int(total_count / item_limit) + 1
  logging.info("Total Count: " + str(total_count) + " - Number of batches: " + str(batches))
  start = 0
  while(start < total_count):
    page_block = {"start": start, "limit": item_limit}
    active_pages.append(page_block)
    start += item_limit

  return active_pages



def lambda_handler(event, context):
  config = getParamInfo()
  template_values(config,config,tokens)
  logging.debug("Config: " + json.dumps(config))
  url_list = getAllWikiPages(config)
  logging.debug("Page List Params: " + json.dumps(url_list))
  return url_list


