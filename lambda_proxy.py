'''
Lambda script to respond to a Sonos echo command and direct the action to the right local
raspberry pi in nyc or ct
Also directly addresses a request to get and set the location.
'''

import requests
import boto3
import json
from config import urls

appVersion = '1.00'

s3 = boto3.resource('s3')
obj = s3.Object('sonos-scrobble','location')
location = obj.get()['Body'].read()

def lambda_handler(event, context=None):
    session = event['session']
    request = event['request']
    requestType = request['type']
	
    if requestType == "LaunchRequest":
        response = launch_request(session, request)
    elif requestType == "IntentRequest":
        response = intent_request(event, request)
    else:
        output_speech = "I couldn't tell which type of request that was.  Try again."
        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':False}

    print "response =",response

    return {"version":appVersion,"response":response}

def intent_request(event, request):

    intent = request['intent']['name']
    print "intent_request: {}".format(intent)

    if intent == "SetLocation":

        s3 = boto3.resource('s3')
        obj = s3.Object('sonos-scrobble','location')

        location = request['intent']['slots']['location']['value']

        if location.lower() in "new york city":
            obj.put(Body='nyc')
            output_speech = "I will set the location to New York City"

        elif location.lower() in ('westport', 'connecticut'):
            obj.put(Body='ct')
            output_speech = "I will set the location to Connecticut"

        else:
            output_speech = "I have no idea where you want to set the location."

        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    elif intent == "GetLocation":

        s3 = boto3.resource('s3')
        obj = s3.Object('sonos-scrobble','location')
        location = obj.get()['Body'].read()

        output_speech = "The location is currently {}".format("New York City" if location == 'nyc' else "Westport, Connecticut")

        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    else:
        s3 = boto3.resource('s3')
        obj = s3.Object('sonos-scrobble','location')
        location = obj.get()['Body'].read()
        url = urls[location]
        print "url =", url
        try:
            response = requests.post(url, json=event)
        except Exception as e:
            print "Exception in sending post to alexa app: ", e
            response = {'outputSpeech': {'type':'PlainText','text':"An exception occured: "+e},'shouldEndSession':True}
            return response

        return response.json()['response']
