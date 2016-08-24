'''
var http = require('http'); 
var URLParser = require('url'); 
exports.handler = function (json, context)

          { try 
          
          { // A list of URL's to call for each applicationId

     var handlers = { 'appId':'url', 'amzn1.echo-sdk-ams.app.999999-d0ed-9999-ad00-999999d00ebe':'http://alexa-app.com/helloworld' }; // Look up the url to call based on the appId 
     var url = handlers[json.session.application.applicationId]; 

if (!url) { context.fail("No url found for application id"); } 

var parts = URLParser.parse(url); 
var post_data = JSON.stringify(json); // An object of options to indicate where to post to 
var post_options = { host: parts.hostname, port: (parts.port || 80), path: parts.path, method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': post_data.length } 
}; // Initiate the request to the HTTP endpoint 

var req = http.request(post_options,function(res) { var body = ""; // Data may be chunked res.on('data', function(chunk) { body += chunk; }); res.on('end', function() { // When data is 
done, finish the request context.succeed(JSON.parse(body)); }); }); req.on('error', function(e) { context.fail('problem with request: ' + e.message); }); // Send the JSON data req.write
(post_data); req.end(); }

catch (e) { context.fail("Exception: " + e); }

}; 
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
        try:
            response = requests.post(url, json=event)
        except Exception as e:
            print "Exception in sending post to alexa app: ", e
            response = {'outputSpeech': {'type':'PlainText','text':"An exception occured: "+e},'shouldEndSession':True}
            return response

        return response.json()['response']
