# coding: utf-8
from __future__ import (absolute_import, division, print_function, unicode_literals)

import json
import logging
import boto3
from boto3.dynamodb.conditions import Key, Attr
import os
import sys
import datetime

# Path to modules needed to package local lambda function for upload
currentdir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(currentdir, "./vendored"))

# Modules downloaded into the vendored directory
import requests
from requests_aws4auth import AWS4Auth

# Logging for Serverless
log = logging.getLogger()
log.setLevel(logging.DEBUG)

# Initializing AWS services
dynamodb = boto3.resource('dynamodb')
sts = boto3.client('sts')
kms = boto3.client('kms')


def handler(event, context):
    log.debug("Received event {}".format(json.dumps(event)))

    accountInfo = dynamodb.Table(os.environ['TAILOR_TABLENAME_ACCOUNTINFO'])
    cbInfo = dynamodb.Table(os.environ['TAILOR_TABLENAME_CBINFO'])
    tailorApiDomain = os.environ['TAILOR_API_DOMAINNAME']

    # Look up all CBs in talr-cbInfo and process based on each.
    scanCbInfo = cbInfo.scan(
        ProjectionExpression='accountCbAlias'
    )

    for i in scanCbInfo['Items']:
        tailorApiAccessKey, tailorApiSecretKey = getTailorCreds(cbInfo, i['accountCbAlias'])
        accountIds = getAccountIds(tailorApiAccessKey, tailorApiSecretKey, tailorApiDomain)

    return accountIds


def getAccountIds(access_key, secret_key, domain):

    boto3Session = boto3.Session()
    region = boto3Session.region_name

    tailorEndpoint = 'https://' + domain + '/accounts/ids'
    auth = AWS4Auth(access_key, secret_key, region, 'execute-api')
    headers = {
        'host': 'api.tailor.autodesk.com',
        'accountCbAlias': 'eis-main'
    }
    tailorResponse = requests.get(tailorEndpoint, auth=auth, headers=headers)

    return json.loads(tailorResponse.content)


def getTailorCreds(cb_object, cb_alias):
    getCbInfo = cb_object.get_item(
        Key={
            'accountCbAlias': cb_alias
        }
    )
    tailorApiAccessKey = getCbInfo['Item']['tailorApiAccessKey']
    tailorApiSecretKey = getCbInfo['Item']['tailorApiSecretKey']

    return tailorApiAccessKey, tailorApiSecretKey