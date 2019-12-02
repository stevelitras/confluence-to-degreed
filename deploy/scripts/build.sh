#!/bin/bash -e

S3_PREFIX=${STACK_NAME}
CFN_TEMPLATE_FILE=sam/cfn/example-api.yaml
OUTPUT_CFN_TEMPLATE_FILE=app-sam-output.yaml.tmp

# install sam function/layer requirements
deploy/install_requirements.sh

# Prepare CloudFormation package
echo "Packaging deployment artifacts for template..."
aws cloudformation package \
--template-file ${CFN_TEMPLATE_FILE} \
--output-template-file ${OUTPUT_CFN_TEMPLATE_FILE} \
--s3-bucket ${DEPLOY_BUCKET} \
--s3-prefix ${S3_PREFIX}
