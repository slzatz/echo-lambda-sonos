'''
Requires pysolr.py, config.py, requests - note pysolr.py needs requests
Below are the Alexa intents
PlayStation play {mystation} radio
PlayStation play {mystation} pandora
PlayStation play {mystation} station
PlayTrack play {mytitle} by {myartist}
PlayTrack play {mytitle}
AddTrack add {mytitle} by {myartist}
AddTrack add {mytitle}
AddTrack add {mytitle} to the queue
AddTrack add {mytitle} by {myartist} to the queue
Shuffle shuffle {myartist}
Shuffle play some {myartist}
Shuffle play some music from {myartist}
SetShuffleNumber Set shuffle number to {mynumber}
GetShuffleNumber What is the shuffle number
WhatIsPlaying what is playing
WhatIsPlaying what song is playing
Skip skip
Skip next
Skip skip song
Skip next song
PlayAlbum play album {myalbum}
PlayAlbum play the album {myalbum}
AddAlbum add album {myalbum}
AddAlbum add the album {myalbum}
PauseResume {pauseorresume} the music
PauseResume {pauseorresume} the radio
PauseResume {pauseorresume} sonos
TurnTheVolume Turn the volume {volume}
TurnTheVolume Turn {volume} the volume
SetLocation Set location to {location}
SetLocation I am in {location}
GetLocation Where am I
GetLocation What is the location
'''
import boto3
import botocore
from boto3.dynamodb.conditions import Key
import json
import random
from operator import itemgetter 
from decimal import Decimal
import time
import pysolr
import requests
from config import ec_uri, last_fm_api_key
#last.fm 
base_url = "http://ws.audioscrobbler.com/2.0/"

appVersion = '1.0'

solr = pysolr.Solr(ec_uri+':8983/solr/sonos_companion/', timeout=10)

def send_sqs(**kw):

    # The  below also works
    #s3 = boto3.client('s3')
    #response = s3.get_object(Bucket='sonos-scrobble', Key='location')
    #body = response['Body']

    s3 = boto3.resource('s3')
    object = s3.Object('sonos-scrobble','location')
    location = object.get()['Body'].read()
    queue_name = 'echo_sonos_ct' if location=='ct' else 'echo_sonos'

    sqs = boto3.resource('sqs')
    # below is the action queue; may also need storage queue or use S3, e.g., echo_sonos_history
    queue = sqs.get_queue_by_name(QueueName=queue_name)
    sqs_response = queue.send_message(MessageBody=json.dumps(kw))

def lambda_handler(event, context):
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

    elif intent ==  "PlayAlbum" or intent == "AddAlbum":

        album = request['intent']['slots']['myalbum'].get('value', '')
        print "album =",album
        if album:
            s = 'album:' + ' AND album:'.join(album.split())
            result = solr.search(s, fl='score,track,uri,album', sort='score desc', rows=25) #**{'rows':25}) #only brings back actual matches but 25 seems like max for most albums
            if  result.docs:
                selected_album = result.docs[0]['album']
                tracks = sorted([t for t in result.docs],key=itemgetter('track'))
                # The if t['album']==selected_album only comes into play if we retrieved more than one album
                uris = [t['uri'] for t in tracks if t['album']==selected_album]
                action = 'play' if intent=="PlayAlbum" else 'add'
                send_sqs(action=action, uris=uris)
                output_speech = "I will play {} songs from {}".format(len(uris), selected_album)
                end_session = True
            else:
                output_speech = "I couldn't find {}. Try again.".format(album)
                end_session = False

        else:
            output_speech = "I couldn't find the album. Try again."
            end_session = False

        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':end_session}
        return response

    elif intent == "PlayTrack" or intent == "AddTrack":
        # title must be present; artist is optional

        artist = request['intent']['slots']['myartist'].get('value', '')
        title = request['intent']['slots']['mytitle'].get('value', '')
        print "artist =",artist
        print "title =",title

        if title:
            s = 'title:' + ' AND title:'.join(title.split())
            if artist:
                s = s + ' artist:' + ' AND artist:'.join(artist.split())

            result = solr.search(s, rows=1) #**{'rows':1})
            if len(result):
                track = result.docs[0]
                action = 'play' if intent=="PlayTrack" else 'add'
                send_sqs(action=action, uris=[track['uri']])

                output_speech = "I will play {} by {} from album {}".format(track['title'], track['artist'], track['album'])
                end_session = True
            else:
                output_speech = "I couldn't find the song {} by {}. Try again.".format(title,artist)
                end_session = False
        else:
            output_speech = "I couldn't find the song. Try again."
            end_session = False

        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':end_session}
        return response

    elif intent == "PlayPlaylist" or intent == "AddPlaylist":
        playlist_name = request['intent']['slots']['myplaylist'].get('value', '')
        playlist_name = playlist_name.title()
        print playlist_name
        s3 = boto3.resource('s3')
        object = s3.Object('sonos-scrobble','playlists/'+playlist_name)
        try:
            z = object.get()['Body'].read()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "NoSuchKey":
                exists = False
            else:
                raise e
        else:
            exists = True
        
        if exists:
            playlist = json.loads(z)
            uris = [x[1] for x in playlist]
            action = 'play' if intent=="PlayPlaylist" else 'add'
            send_sqs(action=action, uris=uris)
            output_speech = "I will {} playlist {} ".format(action, playlist_name)
            end_session = True
        else:
            output_speech = "I couldn't find the playlist. Try again."
            end_session = False

        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':end_session}
        return response

    elif intent ==  "Shuffle":

        s3 = boto3.resource('s3')
        object = s3.Object('sonos-scrobble','shuffle_number')
        shuffle_number = int(object.get()['Body'].read())

        artist = request['intent']['slots']['myartist'].get('value')
        if artist:
            s = 'artist:' + ' AND artist:'.join(artist.split())
            result = solr.search(s, fl='uri', rows=500) 
            count = len(result)
            if count:
                print "Total track count for {} was {}".format(artist, count)
                tracks = result.docs
                k = shuffle_number if shuffle_number <= count else count
                uris = []
                for j in range(k):
                    while 1:
                        n = random.randint(0, count-1) if count > shuffle_number else j
                        uri = tracks[n]['uri']
                        if not uri in uris:
                            uris.append(uri)
                            break

                send_sqs(action='play', uris=uris)
                output_speech = "I will play {} songs by {}.".format(shuffle_number, artist)
                end_session = True
            else:
                output_speech = "The artist {} didn't have any songs.".format(artist)
                end_session = False
        else:
            output_speech = "I couldn't find the artist you were looking for. Try again."
            end_session = False

        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':end_session}
        return response

    elif intent ==  "Deborah": # not in use

        number = request['intent']['slots']['number']['value']
        send_sqs(action='deborah', number=number)

        output_speech = "I will play " + str(number) + " of Deborah's albums"
        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    elif intent == "ListPlaylists":
        s3 = boto3.resource('s3')
        bucket = s3.Bucket('sonos-scrobble')
        z = bucket.objects.filter(Prefix='playlists/')
        playlists = filter(None, [x.key.split('/')[1] for x in z.all()])
        s = ', '.join(playlists)
        output_speech = "The playlists that currently exist are: {}".format(s)
        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    elif intent == "WhichTracks":

        #collection = request['intent']['slots']['mycollection'].get('value', '')
        playlist_name = request['intent']['slots']['myplaylist'].get('value', '')
        playlist_name = playlist_name.title()
        print playlist_name
        s3 = boto3.resource('s3')
        object = s3.Object('sonos-scrobble','playlists/'+playlist_name)
        try:
            z = object.get()['Body'].read()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "NoSuchKey":
                exists = False
            else:
                raise e
        else:
            exists = True
        
        if exists:
            playlist = json.loads(z)
            ids = ['"{}"'.format(x[0]) for x in playlist] #" are necessary I suspect because of non-a-z characters like (
            s = 'id:' + ' id:'.join(ids)
            print s
            result = solr.search(s, fl='title,uri,album,artist', rows=25) #**{'rows':25}) #only brings back actual matches but 25 seems like max for most albums
            tracks = [t['title'] + ' from ' + t['album'] + ' by ' + t['artist'] for t in result.docs]
            #uris = [x[1] for x in playlist]
            s = ', '.join(tracks)
            s = s.replace('&', 'and') #Alexa doesn't like to speak an ampersand
            output_speech = "Playlist {} includes {}".format(playlist_name, s)
            end_session = True
        else:
            output_speech = "I couldn't find the playlist. Try again."
            end_session = False

        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':end_session}
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

    elif intent == "RecentTracks":

        payload = {'method':'user.getRecentTracks', 'user':'slzatz', 'format':'json', 'api_key':last_fm_api_key, 'from':int(time.time())-604800, 'limit':6}
        
        try:
            r = requests.get(base_url, params=payload)
            z = r.json()['recenttracks']['track']
        except Exception as e:
            print "Exception in get_scrobble_info: ", e
            z = []

        if z:
            dic = {}
            for d in z:
                dic[d['album']['#text']+'_'+d['name']] = dic.get(d['album']['#text']+'_'+d['name'],0) + 1

            a = sorted(dic.items(), key=lambda x:(x[1],x[0]), reverse=True) 
            current_album = ''
            output_speech = ''
            for t in a:
                album,track = t[0].split('_')
                if current_album == album:
                    line = ", {} ".format(track)
                else:
                    line = ". From {}, {} ".format(album,track)
                    current_album = album
                #track = 'From ' + ', track: '.join(t[0].split('_')) + ', ' 
                #output_speech+=track + str(t[1]) + ' plays. ' if t[1]>1 else track + '. '
                output_speech+=line + str(t[1]) + " plays" if t[1]>1 else line


        else:
            output_speech = "I could  not retrieve recently played tracks or there aren't any."

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

    elif intent == "SetLocation":

        s3 = boto3.resource('s3')
        object = s3.Object('sonos-scrobble','location')

        location = request['intent']['slots']['location']['value']

        if location.lower() in "new york city":
            object.put(Body='nyc')
            output_speech = "I will set the location to New York City"

        elif location.lower() in ('westport', 'connecticut'):
            object.put(Body='ct')
            output_speech = "I will set the location to Connecticut"

        else:
            output_speech = "I have no idea where you want to set the location."

        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    elif intent == "GetLocation":

        s3 = boto3.resource('s3')
        object = s3.Object('sonos-scrobble','location')
        location = object.get()['Body'].read()

        output_speech = "The location is currently {}".format("New York City" if location == 'nyc' else "Westport, Connecticut")

        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    elif intent == "SetShuffleNumber":

        new_shuffle_number = request['intent']['slots']['mynumber']['value']
        s3 = boto3.resource('s3')
        object = s3.Object('sonos-scrobble','shuffle_number')
        shuffle_number = object.get()['Body'].read()
        object.put(Body=new_shuffle_number)

        output_speech = "The shuffle number is currently {} and will be changed to {}".format(shuffle_number, new_shuffle_number)

        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    elif intent == "GetShuffleNumber":

        s3 = boto3.resource('s3')
        object = s3.Object('sonos-scrobble','shuffle_number')
        shuffle_number = object.get()['Body'].read()

        output_speech = "The shuffle number is currently {}".format(shuffle_number)

        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':True}
        return response

    else:
        output_speech = "I couldn't tell which type of intent request that was.  Try again."
        response = {'outputSpeech': {'type':'PlainText','text':output_speech},'shouldEndSession':False}
        return response
