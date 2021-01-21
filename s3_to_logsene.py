import json
import urllib
import boto3
import socket
import time
import zlib
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

LOGSENE_SERVER = 'logsene-receiver-syslog.sematext.com'
LOGSENE_PORT = 514

# application where you want to send your logs
LOGSENE_APP_TOKEN = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'

s3 = boto3.client('s3')

# clean up a potential dangling connection
logsene_dangling = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
logsene_dangling.close()

def send_to_logsene(text, logsene_connection):
  to_send = "aws-lambda " + LOGSENE_APP_TOKEN + ":" + text + "\n"
  logsene_connection.send(to_send.encode())
  logger.debug("Sent string: " + to_send)
  

def lambda_handler(event, context):
    logsene_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logsene_connection.connect((LOGSENE_SERVER, LOGSENE_PORT))
    
    logger.debug("Received event: " + json.dumps(event))

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        body = response['Body']
        data = body.read()
    except Exception as e:
        logger.error(f'Error getting object {key} from bucket {bucket}. Make sure they exist and your bucket is in the same region as this function.')
        logsene_connection.close()
        raise e

    try:
        data = zlib.decompress(data, 16+zlib.MAX_WBITS)
        logger.debug("Detected gzipped content")
    except zlib.error:
        logger.error("Content couldn't be ungzipped, assuming plain text")

    lines = data.splitlines()
    
    for line in lines:
        line = line.decode()
        try: # trying to parse JSON logs here
            json_line = json.loads(line)
            try:
                for record in json_line['Records']: # these would be CloudTrail logs
                    send_to_logsene("@cee:" + json.dumps(record), logsene_connection)
            except KeyError: # no CloudTrail logs then, will send the whole JSON line
                 send_to_logsene("@cee:" + line, logsene_connection)
        except ValueError: # ok, so it's not JSON
            if line: # let's skip empty strings
                send_to_logsene(line, logsene_connection)
    
    logsene_connection.close()
    logger.debug("Done processing")