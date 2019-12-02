#!/bin/bash -e

# env variables set from AWS::CodeBuild::Project
echo "AWS_REGION: $AWS_REGION"
echo "DEPLOY_BUCKET: $DEPLOY_BUCKET"
echo "STACK_NAME: $STACK_NAME"
echo "SWAGGER_FILE: $SWAGGER_FILE"
echo "SWAGGER_S3_LOCATION: $SWAGGER_S3_LOCATION"

# generate test and prd cfn-parameters json files
echo "Generating test-parameters.json.tmp"
python deploy/scripts/gen-cfn-paramaters-json.py -e test -i deploy/cfn-params/app-parameters.json -o test-app-parameters.json.tmp

echo "Generating prd-parameters.json.tmp"
python deploy/scripts/gen-cfn-paramaters-json.py -e prd -i deploy/cfn-params/app-parameters.json -o prd-app-parameters.json.tmp

# Upload the swagger file to $DEPLOY_BUCKET
echo "aws s3 cp $SWAGGER_FILE $SWAGGER_S3_LOCATION"
aws s3 cp $SWAGGER_FILE $SWAGGER_S3_LOCATION
