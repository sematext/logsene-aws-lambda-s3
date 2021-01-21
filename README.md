
# AWS S3 + AWS Lambda --> Sematext Cloud
[AWS Lambda](https://aws.amazon.com/documentation/lambda/) function to send logs stored in [Amazon S3](https://aws.amazon.com/documentation/s3/) to [Sematext Logs](https://sematext.com/logsene/), a Log Management SaaS that's part of [Sematext Cloud](https://sematext.com/cloud). As new log files are added to your S3 bucket, this function will fetch and parse them before sending their contents to your Logs App in Sematext Cloud.

## Features
 - deals with GZIPped logs
 - parses JSON logs (one JSON per line)
 - parses [AWS CloudTrail logs](http://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-log-file-examples.html), where the JSON contains an array of *Records* entries, each being an event (that is forwarded independently to Sematext
 - sends each line of the log to Sematext via TCP syslog, filling in the token in the [syslog TAG field](https://tools.ietf.org/html/rfc3164#section-4.1.3). It uses *aws-lambda* as a predefined host name
 - we can add more :) Feel free to file issues!

## How To
To start, log in to your AWS Console, then go to *Services* -> *Lambda*. From there, you'd either create a new function or click on Get Started Now to create your first Lambda function.

Then the first step is to select a blueprint for your function. Select *s3-get-object-python*.

Next, select the source for your logs. The source type needs to be S3. You'll need to provide the Bucket for your logs and specify Object Created (All) as the Event type.

Next, configure your function. A few things are needed here:
- provide a name for your function
- set Runtime to Python 3.7
- paste the contents of s3_to_logsene.py and use it to replace all existing function code. Also replace the dummy token (xxxx-xxxx-xxxx-xxxx) with 3cc59684-8457-4080-af6e-13f2b5c7b0bf (this application's token).
- set the trigger to be *All object create events* and select your S3 bucket
- select an execution role that allows this function to access the S3 bucket in order to fetch logs. If you don't have one already, select S3 execution role from the dropdown, and you'll be redirected to the IAM window, where you can accept the provided values and return
- select how much memory you allow for the function and how long you allow it to run. The default 128MB should be enough to load typical CloudTrail logs, which are small. You'd need more memory if you upload larger logs. As for timeout, 4-5 minutes should be enough to give some resiliency in case of a network issue, allowing the function to retry

At this point, whenever new logs are uploaded to your S3 bucket, the Lambda should pick them up and send them.