'''
Radio play {neil young|artist} radio
Shuffle shuffle {number} {neil young|artist} songs
Select {myartist}
Deborah play {number} of Deborah's albums
WhatIsPlaying what is playing now
WhatIsPlaying what song is playing now
WhatIsPlaying what is playing
WhatIsPlaying what song is playing
Skip skip song
Skip next song
Skip skip this song
TurnTheVolume Turn the volume {volume}
TurnTheVolume Turn {volume} the volume
'''
import boto3
from boto3.dynamodb.conditions import Attr, Key
import json
from decimal import Decimal
from time import time
from datetime import datetime

appVersion = "1.0"

def send_sqs(**kw):
    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName='echo_sonos')
    sqs_response = queue.send_message(MessageBody=json.dumps(kw))

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
    output_speech = "Welcome to Sonos. Some things you can do are Play Neil Young radio or Shuffle 5 Neil Young songs or ask what is playing or skip, louder, quieter"
    output_type = 'PlainText'

    response = {'outputSpeech': {'type':output_type,'text':output_speech},'shouldEndSession':False}

    return response

def intent_request(session, request):
    print "intent_request"

    intent = request['intent']['name']

    if intent ==  "Radio":

        artist = request['intent']['slots']['artist']['value']

        #sqs = boto3.resource('sqs')
        #queue = sqs.get_queue_by_name(QueueName='echo_sonos')
        #sqs_response = queue.send_message(MessageBody=json.dumps({'action':'radio','artist':artist}))
        send_sqs(action='radio', artist=artist)

        output_speech = artist + " radio will start playing soon"
        output_type = 'PlainText'

        response = {'outputSpeech': {'type':output_type,'text':output_speech},'shouldEndSession':True}

        return response

    elif intent ==  "Shuffle":

        number = request['intent']['slots']['number']['value']
        artist = request['intent']['slots']['artist']['value']

        #sqs = boto3.resource('sqs')
        #queue = sqs.get_queue_by_name(QueueName='echo_sonos')
        #sqs_response = queue.send_message(MessageBody=json.dumps({"action":"shuffle", "artist":artist,"number":number}))
        send_sqs(action='shuffle', artist=artist, number=number)

        output_speech = "I will shuffle " + str(number) + " songs from " + artist
        output_type = 'PlainText'

        response = {'outputSpeech': {'type':output_type,'text':output_speech},'shouldEndSession':True}

        return response

    elif intent ==  "Select":

        number = 5
        artist = request['intent']['slots']['myartist']['value']

        send_sqs(action='shuffle', artist=artist, number=number)

        output_speech = "I will select " + str(number) + " songs from " + artist
        output_type = 'PlainText'

        response = {'outputSpeech': {'type':output_type,'text':output_speech},'shouldEndSession':True}

        return response
    elif intent ==  "Deborah":

        number = request['intent']['slots']['number']['value']

        #sqs = boto3.resource('sqs')
        #queue = sqs.get_queue_by_name(QueueName='echo_sonos')
        #sqs_response = queue.send_message(MessageBody=json.dumps({"action":"deborah", "number":number}))
        send_sqs(action='deborah', number=number)

        output_speech = "I will play " + str(number) + " of Deborah's albums"
        output_type = 'PlainText'

        response = {'outputSpeech': {'type':output_type,'text':output_speech},'shouldEndSession':True}

        return response

    elif intent == "WhatIsPlaying":

        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('scrobble_new')
        result = table.query(KeyConditionExpression=Key('location').eq('nyc'), ScanIndexForward=False, Limit=1) #by default the sort order is ascending

        if result['Count']:
            track = result['Items'][0]
            if track['ts'] > Decimal(time.time())-300:
                output_speech = "The song is {}. The artist is {} and the album is {}.".format(track.get('title','No title'), track.get('artist', 'No artist'), track.get('album', 'No album'))
            else:
                output_speech = "Nothing appears to be playing right now, Steve"
        else:
            output_speech = "It appears that nothing has ever been scrobbled"

        output_type = 'PlainText'
        response = {'outputSpeech': {'type':output_type,'text':output_speech},'shouldEndSession':True}
        return response

    elif intent == "Skip":

        send_sqs(action='skip')

        output_speech = "skipped"
        output_type = 'PlainText'
        response = {'outputSpeech': {'type':output_type,'text':output_speech},'shouldEndSession':True}
        return response

    elif intent == "PausePlay":

        pauseorplay = request['intent']['slots']['pauseorplay']['value']

        if pauseorplay in ('pause','stop'):
            action = 'pause'
        elif pauseorplay in ('play','resume'):
            action = 'resume'
        else:
            action = None

        if action:

            #sqs = boto3.resource('sqs')
            #queue = sqs.get_queue_by_name(QueueName='echo_sonos')
            #sqs_response = queue.send_message(MessageBody=json.dumps({'action':action}))
            send_sqs(action=action)

            output_speech = "The music will {}".format(action)

        else:
            output_speech = "I have no idea what you said."

        output_type = 'PlainText'
        response = {'outputSpeech': {'type':output_type,'text':output_speech},'shouldEndSession':True}
        return response

    #elif intent == "Louder":

    #    sqs = boto3.resource('sqs')
    #    queue = sqs.get_queue_by_name(QueueName='echo_sonos')
    #    sqs_response = queue.send_message(MessageBody=json.dumps({"action":"louder"}))

    #    output_speech = "louder"
    #    output_type = 'PlainText'
    #    response = {'outputSpeech': {'type':output_type,'text':output_speech},'shouldEndSession':True}
    #    return response

    #elif intent == "Quieter":

    #    sqs = boto3.resource('sqs')
    #    queue = sqs.get_queue_by_name(QueueName='echo_sonos')
    #    sqs_response = queue.send_message(MessageBody=json.dumps({"action":"quieter"}))

    #    output_speech = "quieter"
    #    output_type = 'PlainText'
    #    response = {'outputSpeech': {'type':output_type,'text':output_speech},'shouldEndSession':True}
    #    return response

    elif intent == "TurnTheVolume":
        # Turn the volume down; turn the volume up, turn it down, turn it up
        volume = request['intent']['slots']['volume']['value']

        if volume in ('louder','higher','up'):
            action = 'louder'
        elif volume in ('down','quieter','lower'):
            action = 'quieter'
        else:
            action = None

        if action:

            #sqs = boto3.resource('sqs')
            #queue = sqs.get_queue_by_name(QueueName='echo_sonos')
            #sqs_response = queue.send_message(MessageBody=json.dumps({'action':action}))
            send_sqs(action=action)

            output_speech = "I will make the volume {}".format(action)

        else:
            output_speech = "I have no idea what you said."

        output_type = 'PlainText'
        response = {'outputSpeech': {'type':output_type,'text':output_speech},'shouldEndSession':True}
        return response
