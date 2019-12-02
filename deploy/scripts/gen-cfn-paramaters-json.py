import argparse
import json
import logging
import os

log = logging.getLogger()
log.setLevel(logging.INFO)

def main(args):
  log.info(f'Generating {args.output_file}')

  # set variables used in parameters file from the CodeBuild project Environment variables
  aws_region = os.environ['AWS_REGION']
  domain_name = os.environ['DOMAIN_NAME']
  deploy_bucket = os.environ['DEPLOY_BUCKET']
  swagger_s3_location = os.environ['SWAGGER_S3_LOCATION']
  moniker_prefix = os.environ['MONIKER_PREFIX']
  tag_adsk_moniker = f'{moniker_prefix}-{args.env}-{aws_region}'
  tag_adsk_service= f'{moniker_prefix}-{args.env}-{aws_region}'

  # purely informational
  log.info(f'env: {args.env}')
  log.info(f'output_file: {args.output_file}')
  log.info(f'input_file: {args.input_file}')
  log.info(f'aws_region: {aws_region}')
  log.info(f'deploy_bucket: {deploy_bucket}')
  log.info(f'domain_name: {domain_name}')
  log.info(f'moniker_prefix: {moniker_prefix}')
  log.info(f'swagger_s3_location: {swagger_s3_location}')
  log.info(f'tag_adsk_moniker: {tag_adsk_moniker}')
  log.info(f'tag_adsk_service: {tag_adsk_service}')

  # read params template
  with open(args.input_file, 'r') as f:
    params = json.loads(f.read())
    print(params)

  # Replace values in params with the variables
  params['Parameters']['DomainName'] = domain_name
  params['Parameters']['Environment'] = args.env
  params['Parameters']['LambdaAlias'] = args.env
  params['Parameters']['StageName'] = args.env
  params['Parameters']['SwaggerFile'] = swagger_s3_location
  params['Tags']['adsk:moniker'] = tag_adsk_moniker
  params['Tags']['adsk:service'] = tag_adsk_service
  params['Tags']['adsk:environment'] = args.env

  # write params file to output_file
  with open(args.output_file, 'a') as f:
    f.write(json.dumps(params))

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Generate CFN parameters json file')
  parser.add_argument(
    '--env', '-e',
    help="Environment of the cfn params json file",
    dest='env',
    required=True
  )
  parser.add_argument(
    '--input-file', '-i',
    help="The name of the input file",
    dest='input_file',
    required=True
  )
  parser.add_argument(
    '--output-file', '-o',
    help="The name of the output file",
    dest='output_file',
    required=True
  )
  args = parser.parse_args()
  main(args)