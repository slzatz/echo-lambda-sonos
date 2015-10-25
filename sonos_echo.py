import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
from time import time
from datetime import datetime

appVersion = "1.0"

def lambda_handler(event, context):
	#print event['session']
    print event
    session = event['session']
    request = event['request']
    response = request_handler(session, request)
    print response
    print json.dumps({"version":appVersion,"response":response}) #,sort_keys=True,indent=4)

    return {"version":appVersion,"response":response}

def request_handler(session, request):
    requestType = request['type']
	
    if requestType == "LaunchRequest":
        return launch_request(session, request)
    elif requestType == "IntentRequest":
        return intent_request(session, request)

def launch_request(session, request):
    output_speech = "Welcome to Sonos. Please say a command."
    output_type = 'PlainText'

    response = {'outputSpeech': {'type':output_type,'text':output_speech},'shouldEndSession':False}

    return response

def intent_request(session, request):
    print "intent_request"

    intent = request['intent']['name']

    if intent ==  "OneshotSonosIntent":

        artist = request['intent']['slots']['artist']['value']
        source = request['intent']['slots']['source']['value']

        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName='echo_sonos')
        sqs_response = queue.send_message(MessageBody=json.dumps({'action':'radio','artist':artist, 'source':source}))

        output_speech = artist + " from " + source + " will start playing soon"
        output_type = 'PlainText'

        response = {'outputSpeech': {'type':output_type,'text':output_speech},'shouldEndSession':True}

        return response

    elif intent ==  "Shuffle":

        number = request['intent']['slots']['number']['value']
        artist = request['intent']['slots']['artist']['value']

        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName='echo_sonos')
        sqs_response = queue.send_message(MessageBody=json.dumps({"action":"shuffle", "artist":artist,"number":number}))

        output_speech = "I will shuffle " + str(number) + " songs from " + artist
        output_type = 'PlainText'

        response = {'outputSpeech': {'type':output_type,'text':output_speech},'shouldEndSession':True}

        return response

    elif intent ==  "Deborah":

        number = request['intent']['slots']['number']['value']

        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName='echo_sonos')
        sqs_response = queue.send_message(MessageBody=json.dumps({"action":"deborah", "number":number}))

        output_speech = "I will play " + str(number) + " of Deborah's albums"
        output_type = 'PlainText'

        response = {'outputSpeech': {'type':output_type,'text':output_speech},"shouldEndSession":True}

        return response

    elif intent == "WhatIsPlaying":

        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('scrobble')
        z = time()
        #>>> rrr = table.scan(Limit=10, FilterExpression=Attr("ts").gt(Decimal(z)-1000000))
        #>>> rrr
        #{u'Count': 1, u'Items': [{u'album': u'I Carry Your Heart With Me (c)', u'artist': u'Hem', u'title': u'The Part Where You Let Go', 
        #u'ts': Decimal('1445364875'), u'date': u'2007 - Home
        # Again, Home Again', u'scrobble': u'27'}], u'LastEvaluatedKey': {u'ts': Decimal('1442178047'), u'artist': u'Leo Kottke'}, 
        #u'ScannedCount': 10, 'ResponseMetadata': {'HTTPStatusCode':
        #200, 'RequestId': 'P3U632LF4NKTGP6MEJ228MLRDBVV4KQNSO5AEMVJF66Q9ASUAAJG'}}

        #{u'Count': 0, u'Items': [], u'LastEvaluatedKey': {u'ts': Decimal('1442178047'), u'artist': u'Leo Kottke'}, u'ScannedCount': 10, 
        #'ResponseMetadata': {'HTTPStatusCode': 200, 'RequestId
        #': '2UVLSDD8147256OV6P0T03IBV7VV4KQNSO5AEMVJF66Q9ASUAAJG'}}

        result = table.scan(FilterExpression=Attr('ts').gt(Decimal(z)-300))

        if result['Count']:
            songs = result['Items']
            y = [(s.get('ts', ''), s.get('title', ''), s.get('artist', ''), s.get('album', '')) for s in songs]
            y.sort(key = lambda x:x[0], reverse=True)
            
            for x in y:
                print "{}: {} - {} - {}".format(datetime.fromtimestamp(x[0]).strftime("%a %I:%M%p"), x[1], x[2], x[3])

            last_song = y[0]
            output_speech = "Song is {} Artist is {} Album is {}".format(last_song[1], last_song[2], last_song[3])

        else:
            out_speech = "Nothing appears to be playing right now, Steve"

        output_type = 'PlainText'

        response = {'outputSpeech': {'type':output_type,'text':output_speech},"shouldEndSession":True}

        return response

    elif intent == "Skip":

        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName='echo_sonos')
        sqs_response = queue.send_message(MessageBody=json.dumps({"action":"skip"}))

        output_speech = "skipped"
        output_type = 'PlainText'
        response = {'outputSpeech': {'type':output_type,'text':output_speech},"shouldEndSession":True}

        return response

    elif intent == "Louder":

        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName='echo_sonos')
        sqs_response = queue.send_message(MessageBody=json.dumps({"action":"louder"}))

        output_speech = "louder"
        output_type = 'PlainText'
        response = {'outputSpeech': {'type':output_type,'text':output_speech},"shouldEndSession":True}

        return response

    elif intent == "Lower":

        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName='echo_sonos')
        sqs_response = queue.send_message(MessageBody=json.dumps({"action":"lower"}))

        output_speech = "lower"
        output_type = 'PlainText'
        response = {'outputSpeech': {'type':output_type,'text':output_speech},"shouldEndSession":True}

        return response
