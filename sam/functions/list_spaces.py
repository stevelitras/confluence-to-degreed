from utils import *
import logging
import json
import sys

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
  spaces = []
  if ("spaces" in config['wiki']):
    splist = config['wiki']['spaces']
    logging.info("Using Parameter instread of DynamoTable")
    for space in splist:
      spaces.append( {"space": space})

  elif ("dynamo_table" in config):
    dynamo = boto3.client("dynamodb")
    if ("dynamo_table" in config) and ("name" in config['dynamo_table']):
      response = dynamo.scan(TableName=config['dynamo_table']['name'])
    else:
      logging.info("Dynamo Configuration missing from SSM")
    logging.debug("Response: " + json.dumps(response))
    if ("Count" in response) and (response['Count'] > 0):
      items = response['Items']
      for item in items:
        logging.info("I'm in Items: " + json.dumps(item))
        spaces.append( {"space": item['space']['S']} )
  return spaces

def lambda_handler(event, context):
  config = getParamInfo()
  template_values(config,config,tokens)
  logging.debug("Config: " + json.dumps(config))
  spaces = getSpaceWhiteList(config)
  logging.info("Spaces: " + json.dumps(spaces))
  return spaces


