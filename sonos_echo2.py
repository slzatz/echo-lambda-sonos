'''
Invoked by "Sonos"
PlayStation play {mystation} radio
PlayStation play {mystation} pandora
PlayStation play {mystation} station
PlayTrack play {mytitle} by {myartist}
AddTrack add {mytitle} by {myartist}
Shuffle shuffle {myartist}
WhatIsPlaying what is playing
WhatIsPlaying what song is playing
Skip skip
Skip next
PlayAlbum play album {myalbum}
PauseResume {pauseorresume} the music
TurnTheVolume Turn the volume {volume}
TurnTheVolume Turn {volume} the volume
'''
import boto3
from boto3.dynamodb.conditions import Key
import json
from decimal import Decimal
import time

appVersion = '1.0'

#s3 = boto3.client('s3')
#response = s3.get_object(Bucket='sonos-scrobble', Key='location')
#body = response['Body']
#queue_name = 'echo_sonos_ct' if body.read()=='ct' else 'echo_sonos'

def send_sqs(**kw):
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket='sonos-scrobble', Key='location')
    body = response['Body']
    queue_name = 'echo_sonos_ct' if body.read()=='ct' else 'echo_sonos'
    sqs = boto3.resource('sqs')
    # below is the action queue; may also need storage queue or use S3, e.g., echo_sonos_history
    queue = sqs.get_queue_by_name(QueueName=queue_name)
    sqs_response = queue.send_message(MessageBody=json.dumps(kw))

def lambda_handler(event, context):
    print event['session']
    #print event
    session = event['session']
    request = event['request']
    requestType = request['type']
	
    if requestType == "LaunchRequest":
        response = launch_request(session, request)
    elif requestType == "IntentRequest":
        response = intent_request(session, request)
    else:
        output_speech = "I couldn't tell which type of request that was.  Try again."
        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':False}

    print json.dumps(response) 

    return {"version":appVersion,"response":response}

def launch_request(session, request):
    output_speech = "Welcome to Sonos. Some things you can do are: Select Neil Young radio or Shuffle Neil Young or Play After the Gold Rush or ask what is playing or skip, louder, quieter"
    response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':False}
    return response

def intent_request(session, request):

    intent = request['intent']['name']
    print "intent_request: {}".format(intent)

    if intent ==  "PlayStation":

        station = request['intent']['slots']['mystation']['value']
        send_sqs(action='radio', station=station)

        output_speech = station + " radio will start playing soon"
        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    elif intent ==  "PlayAlbum":

        album = request['intent']['slots']['myalbum']['value']
        send_sqs(action='play_album', album=album)

        output_speech = "I will try to play album " + album + "."
        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    elif intent ==  "PlayTrack":

        try:
            artist = request['intent']['slots']['myartist']['value']
        except KeyError:
            artist = ''

        title = request['intent']['slots']['mytitle']['value']
        trackinfo = "{} {}".format(artist, title)
        send_sqs(action='play', trackinfo=trackinfo)

        output_speech = "I will try to play " + trackinfo + "."
        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    elif intent ==  "AddTrack":

        try:
            artist = request['intent']['slots']['myartist']['value']
        except KeyError:
            artist = ''

        title = request['intent']['slots']['mytitle']['value']
        trackinfo = "{} {}".format(artist, title)
        send_sqs(action='add', trackinfo=trackinfo)

        output_speech = "I will try to add " + trackinfo + " to the queue."
        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    elif intent ==  "Shuffle":

        number = 8
        artist = request['intent']['slots']['myartist']['value']
        send_sqs(action='shuffle', artist=artist, number=number)

        output_speech = "I will select " + str(number) + " songs from " + artist
        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    elif intent ==  "Deborah": # not in use

        number = request['intent']['slots']['number']['value']
        send_sqs(action='deborah', number=number)

        output_speech = "I will play " + str(number) + " of Deborah's albums"
        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    elif intent == "WhatIsPlaying":

        s3 = boto3.client('s3')
        response = s3.get_object(Bucket='sonos-scrobble', Key='location')
        body = response['Body']
        location = body.read()
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('scrobble_new')
        result = table.query(KeyConditionExpression=Key('location').eq(location), ScanIndexForward=False, Limit=1) #by default the sort order is ascending

        if result['Count']:
            track = result['Items'][0]
            if track['ts'] > Decimal(time.time())-300:
                output_speech = "The song is {}. The artist is {} and the album is {}.".format(track.get('title','No title'), track.get('artist', 'No artist'), track.get('album', 'No album'))
            else:
                output_speech = "Nothing appears to be playing right now, Steve"
        else:
            output_speech = "It appears that nothing has ever been scrobbled"

        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    elif intent == "Skip":

        send_sqs(action='skip')

        response = {'outputSpeech': {'type':'PlainText','text':'skipped'},'shouldEndSession':True}
        return response

    elif intent == "PauseResume":

        pauseorresume = request['intent']['slots']['pauseorresume']['value']

        if pauseorresume in ('pause','stop'):
            action = 'pause'
        elif pauseorresume in ('unpause','resume'):
            action = 'resume'
        else:
            action = None

        if action:

            send_sqs(action=action)

            output_speech = "The music will {}".format(pauseorresume)

        else:
            output_speech = "I have no idea what you said."

        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    elif intent == "TurnTheVolume":

        volume = request['intent']['slots']['volume']['value']

        if volume in ('louder','higher','up'):
            action = 'louder'
        elif volume in ('down','quieter','lower'):
            action = 'quieter'
        else:
            action = None

        if action:

            send_sqs(action=action)

            output_speech = "I will make the volume {}".format(action)

        else:
            output_speech = "I have no idea what you said."

        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    else:
        output_speech = "I couldn't tell which type of intent request that was.  Try again."
        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':False}
