from utils import *
import logging
import json
import hashlib
import sys
import tempfile
import csv
import pysftp
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

def lambda_handler(event, context):
  config = getParamInfo()
  template_values(config,config,tokens)
  
  logging.info("Event: %s" % json.dumps(event))
  if not isinstance(event, list):
    logging.error("Event is not a list - incorrect format for processing: %s" % json.dumps(event))
  else:
    for record in event:
      logging.info("Would send email to %s, about pathway %s and url %s" % (record.send_to,record.pathway_title,record.wiki_url))