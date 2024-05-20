import boto3
import datetime
import base64
import secrets 
import os
import json

region_name = "il-central-1"# os.environ.get('AWS_REGION')

s3 = boto3.client('s3', region_name=region_name)
# see: https://github.com/boto/boto3/issues/3015
s3 = boto3.client('s3', endpoint_url=s3.meta.endpoint_url) 
sqs = boto3.client('sqs', region_name=region_name) 

upload_bucket = os.environ.get('UPLOAD_BUCKET') #or "cloud-dead-drop-c151295"

queue_url = os.environ.get('NOTIFICATIONS_QUEUE') #or "https://sqs.il-central-1.amazonaws.com/069584382138/cloud-dead-drop-ids-9d7b4b6"

def generate_upload_url(event, context):
    id = secrets.token_urlsafe(32)
    resp = s3.generate_presigned_url('put_object', 
        Params={'Bucket': upload_bucket, 'Key': 'uploads/' + id }, 
        ExpiresIn=3600)  
    body = json.dumps({'id': id, 'url': resp})
    return {'statusCode': 200,'body': body}

def register_id_internal(msg):
    if len(msg) != 108: # 32 bytes + SealedBox = 80 bytes -> base 64 == 108 bytes
        return {'statusCode': 400, 'body': 'Invalid ID'}
    sqs.send_message(QueueUrl=queue_url, MessageBody=msg)
    return {'statusCode': 204}

def register_id(event, context):
    return register_id_internal(event['body'])

def maybe_publish_decoy(event, context):
    if secrets.randbelow(5) != 0:
        return # 80% of the time, do nothing
    # 20% of the time, generate a decoy message
    return register_id_internal(
        base64.urlsafe_b64encode(secrets.token_bytes(80)).decode('ascii')
    )

MAX_MSGS = 8
def publish_ids(event, context):
    while True:
        result = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=MAX_MSGS)
        msgs = result.get('Messages', [])
        ids = [msg['Body'] for msg in msgs]
        while len(ids) < MAX_MSGS:
            ids.append(base64.urlsafe_b64encode(secrets.token_bytes(80)).decode('ascii'))
        ids = sorted(ids, key=lambda _: secrets.randbelow(1024))
        output = '\n'.join(ids)
        now = datetime.datetime.now(datetime.timezone.utc)  \
            .isoformat(timespec='microseconds')             \
            .replace('+00:00','').replace('.','-')
        s3.put_object(Bucket=upload_bucket, Key='ids/' + now, Body=bytes(output, 'ascii'))

        if len(msgs) == 0:
            break
        sqs.delete_message_batch(QueueUrl=queue_url, Entries=[
           {'Id': msg['MessageId'], 'ReceiptHandle': msg['ReceiptHandle']}
           for msg in msgs
        ])

publish_ids(None,None)