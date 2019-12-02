import boto3
import logging
import sys
import json

# import lambda layers
sys.path.append('/opt')
import cfnresponse

s3 = boto3.client('s3')

log = logging.getLogger()
log.setLevel(logging.INFO)

def lambda_handler(event, context):
  log.info(f'Received event: {json.dumps(event)}')

  try:
    # only support delete event
    if event['RequestType'] == 'Delete':

      s3_bucket = event["ResourceProperties"]["S3Bucket"]
      log.info(f'Deleting objects in S3 Bucket: {s3_bucket}')

      log.info('Delete s3bucket objects with versioning enabled...')
      objects = []
      versions = s3.list_object_versions(Bucket=s3_bucket)
      while versions:
        if 'Versions' in versions.keys():
          for v in versions['Versions']:
            objects.append({'Key':v['Key'],'VersionId': v['VersionId']})
        if 'DeleteMarkers'in versions.keys():
          for v in versions['DeleteMarkers']:
            objects.append({'Key':v['Key'],'VersionId': v['VersionId']})
        if versions['IsTruncated']:
          versions=s3.list_object_versions(
            Bucket=s3_bucket,
            VersionIdMarker=versions['NextVersionIdMarker']
          )
        else:
          versions=False

      if objects != []:
        s3.delete_objects(
          Bucket=s3_bucket,
          Delete={'Objects':objects}
        )
      else:
        log.info('Versioning was not enabled, try to delete s3 objects...')
        s3objects = s3.list_objects_v2(Bucket=s3_bucket)
        if 'Contents' in s3objects.keys():
          log.info('Deleting KeyBucket objects %s...' % str([{'Key':key['Key']} for key in s3objects['Contents']]))
          s3.delete_objects(
            Bucket=s3_bucket,
            Delete={'Objects':[{'Key':key['Key']} for key in s3objects['Contents']]}
          )

    cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
  except Exception as err:
    log.info(err)
    cfnresponse.send(event, context, cfnresponse.FAILED, {})