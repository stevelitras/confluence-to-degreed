import sys
import os
import logging
import json

# Path to modules needed to package local lambda function for upload
currentdir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(currentdir, "./vendored"))

import requests

# import lambda layers
sys.path.append('/opt')
import cfnresponse

log = logging.getLogger()
log.setLevel(logging.INFO)

def lambda_handler(event, context):

  try:
    log.info(f'Received event {json.dumps(event)}')

    aws_account_id = event['ResourceProperties']['AwsAccountId']
    api_endpoint = event['ResourceProperties']['APIEndpoint']
    solution_id = event['ResourceProperties']['SolutionId']
    version = event['ResourceProperties']['Version']
    stack_id = event['ResourceProperties']['StackId']
    action = event['RequestType']

    log.info(f'aws_account_id: {aws_account_id}')
    log.info(f'api_endpoint: {api_endpoint}')
    log.info(f'solution_id: {solution_id}')
    log.info(f'version: {version}')
    log.info(f'stack_id: {stack_id}')
    log.info(f'action: {action}')

    headers = {
      'Content-Type': 'application/json'
    }
    payload = {
      'aws_account_id': aws_account_id,
      'solution_id': solution_id,
      'version': 1,
      'stack_id': stack_id,
      'action': action
    }

    log.info(f'headers: {json.dumps(headers)}')
    log.info(f'payload: {json.dumps(payload)}')

    response = requests.request("POST", api_endpoint, data=json.dumps(payload), headers=headers)
    response_data = json.loads(response.content)

    log.info('response_data: ')
    log.info(response_data)

    log.info('response.status_code: ')
    log.info(response.status_code)

    response_data = {'Success': 'Usage data sent'}
    cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)

  except Exception as err:
    log.info(err)
    response_data = {'Error': 'An exception has occured, usage data not sent'}
    # if an error happens do not return failed, it will make the stack fail.
    cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
