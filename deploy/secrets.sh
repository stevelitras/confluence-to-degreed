#!/bin/bash -e
# This script will deploy Secrets Manager resources.
# To delete a stack: aws cloudformation delete-stack --stack-name your-stack-name

while getopts :n:e: option; do
  case "${option}" in
    n)
      STACK_NAME=${OPTARG}
    ;;
    e)
      ENVIRONMENT=${OPTARG}
    ;;
    \?)
      echo "Usage: deploy/secrets.sh [-n STACK_NAME] [-e ENVIRONMENT]"
      exit 1
    ;;
  esac
done

if [ "$STACK_NAME" == "" ]; then
  echo "Stack name not set. Please pass one via the -n parameter."
  exit 1
fi

# make sure ENVIRONMENT is set and is in accepted values
declare -A environmentValues
environmentValues=([test]=1 [prd]=1)
if [ "$ENVIRONMENT" == "" ]; then
  echo "Environment param not set. Please pass one via the -e parameter. Accepted values: test|prd"
  exit 1
elif ! [ ${environmentValues[$ENVIRONMENT]} ]; then
  echo "Environment -e value is invalid. Accepted values: test|prd"
  exit 1
fi

echo "STACK_NAME: $STACK_NAME"
echo "ENVIRONMENT: $ENVIRONMENT"

# Set variables. Set paths relative to the root.
SERVICE_NAME='YOUR_SERVICE_NAME'
AWS_ACCOUNT=$(aws sts get-caller-identity --query "Account" --output text)
AWS_REGION=$(aws configure get region)
S3_PREFIX=${STACK_NAME}
DEPLOY_BUCKET=deploy-${AWS_ACCOUNT}-${AWS_REGION}
CFN_TEMPLATE_FILE=sam/cfn/secrets.yaml
OUTPUT_CFN_TEMPLATE_FILE=${CFN_TEMPLATE_FILE}.tmp

# set tags for the stack, these tags will be propogated to all resources that support tags.
# Specify your tags as "key=value".
# Note: These are temporary params (used as placeholders).
TAG_ADSK_MONIKER="adsk:moniker=${SERVICE_NAME}-${ENVIRONMENT}-${AWS_REGION}"
TAG_ADSK_SERVICE="adsk:service=${SERVICE_NAME}-${ENVIRONMENT}-${AWS_REGION}"
TAG_ADSK_ENVIRONMENT="adsk:environment=${ENVIRONMENT}"

# If not present, create S3 bucket for deployment support files.
echo "Creating $DEPLOY_BUCKET..."
aws s3api get-bucket-location \
  --bucket ${DEPLOY_BUCKET} &>/dev/null \
|| aws s3 mb \
  --region $AWS_REGION \
  s3://${DEPLOY_BUCKET} 2>&1 >/dev/null

# Prepare CloudFormation package
echo "Packaging deployment artifacts..."
aws cloudformation package \
--template-file ${CFN_TEMPLATE_FILE} \
--output-template-file ${OUTPUT_CFN_TEMPLATE_FILE} \
--s3-bucket $DEPLOY_BUCKET \
--s3-prefix ${S3_PREFIX}

# Deploy CloudFormation stack
echo "Deploying to stack ${STACK_NAME}..."
aws cloudformation deploy \
--template-file ${OUTPUT_CFN_TEMPLATE_FILE} \
--role-arn arn:aws:iam::${AWS_ACCOUNT}:role/AdskCfnAdministratorAccessExecutionRole \
--capabilities CAPABILITY_IAM \
--stack-name ${STACK_NAME} \
--tags \
${TAG_ADSK_MONIKER} \
${TAG_ADSK_SERVICE} \
${TAG_ADSK_ENVIRONMENT} \
--parameter-overrides \
Environment=${ENVIRONMENT}

# Clean-up tmp files
rm -f ${OUTPUT_CFN_TEMPLATE_FILE}

echo "Deploy Complete - Secrets stack name is ${STACK_NAME}"
