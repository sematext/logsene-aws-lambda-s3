import json
import urllib
import boto3
import socket
import time
import zlib

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
  logsene_connection.send(to_send)
  #print "Sent string: " + to_send
  

def lambda_handler(event, context):
    logsene_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logsene_connection.connect((LOGSENE_SERVER, LOGSENE_PORT))
    
    print "Received event: " + json.dumps(event)

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key']).decode('utf8')
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        body = response['Body']
        data = body.read()
    except Exception as e:
        print 'Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket)
        logsene_connection.close()
        raise e

    try:
        data = zlib.decompress(data, 16+zlib.MAX_WBITS)
        print "Detected gzipped content"
    except zlib.error:
        print "Content couldn't be ungzipped, assuming plain text"

    lines = data.split("\n")
    
    for line in lines:
        try: # trying to parse JSON logs here
            json_line = json.loads(line)
            try:
                for record in json_line['Records']: # these would be CloudTrail logs
                    send_to_logsene("@cee:" + json.dumps(record), logsene_connection)
            except KeyError: # no CloudTrail logs then, will send the whole JSON line
                 send_to_logsene("@cee:" + line, logsene_connection)
        except ValueError: # ok, so it's not JSON
            if line <> "": # let's skip empty strings
                send_to_logsene(line, logsene_connection)
    
    logsene_connection.close()
    print "Done processing"
