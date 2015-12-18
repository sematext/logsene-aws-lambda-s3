#################IMPORTS##############
import json
import urllib
import boto3
import socket
import time
import zlib

#################VARIABLES###########
LOGSENE_SERVER = 'logsene-receiver-syslog.sematext.com'
LOGSENE_PORT = 514

# application where you want to send your logs
LOGSENE_APP_TOKEN = 'xxxx-xxxxx-xxxxx-xxxxx'

# application where you'd send debug messages of this script
# empty string will skip logging debug messages
LOGSENE_DEBUG_TOKEN = ''

RETRIES = 10      # how many times to retry sending a log if something breaks in the connection
RETRY_SLEEP = 6   # number of seconds to sleep between retries

################SETUP################
if LOGSENE_DEBUG_TOKEN <> '':
    DEBUG_ENABLED = True
else:
    DEBUG_ENABLED = False

s3 = boto3.client('s3')
logsene_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

###############FUNCTIONS##################
def debug(text):
    if DEBUG_ENABLED:
        try_sending(LOGSENE_DEBUG_TOKEN, text, "aws-lambda-debug")

def forward_to_logsene(text):
    try_sending(LOGSENE_APP_TOKEN, text, "aws-lambda")

def try_sending(token, text, host_value, current_retry=1):
    try:
        if current_retry > 1: # maybe there's something with the connection, let's try reopening
            logsene_connection.close()
            logsene_connection.connect((LOGSENE_SERVER, LOGSENE_PORT))
        logsene_connection.send(host_value + " " + token + ":" + text + "\n")
    except socket.error as e:
        if current_retry < RETRIES:
            time.sleep(RETRY_SLEEP)
            try_sending(token, text, host_value, current_retry+1)
        else:
            logsene_connection.close()
            raise e

def try_connecting(logsene_connection, current_retry=1):
    try:
        logsene_connection.connect((LOGSENE_SERVER, LOGSENE_PORT))
    except socket.error as e:
        if current_retry < RETRIES:
            time.sleep(RETRY_SLEEP)
            try_connecting(logsene_connection, current_retry+1)
        else:
            raise e

###############MAIN STUFF#################

def lambda_handler(event, context):
    try_connecting(logsene_connection)
    
    debug("Received event: " + json.dumps(event))

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key']).decode('utf8')
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        body = response['Body']
        data = body.read()
    except Exception as e:
        debug(str(e))
        debug('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        logsene_connection.close()
        raise e

    try:
        data = zlib.decompress(data, 16+zlib.MAX_WBITS)
        debug("Detected gzipped content")
    except zlib.error:
        debug("Content couldn't be ungzipped, assuming plain text")

    lines = data.split("\n")

    for line in lines:
        try: # trying to parse JSON logs here
            json_line = json.loads(line)
            try:
                for record in json_line['Records']: # these would be CloudTrail logs
                    forward_to_logsene("@cee:" + json.dumps(record))
            except KeyError: # no CloudTrail logs then, will send the whole JSON line
                 forward_to_logsene("@cee:" + line)
        except ValueError: # ok, so it's not JSON
            if line <> "": # let's skip empty strings
                forward_to_logsene(line)
    
    logsene_connection.close()
