import json
import boto3
sqs = boto3.resource('sqs')
queue = sqs.get_queue_by_name(QueueName='echo_sonos')

appVersion = "1.0"

def lambda_handler(event, context):
	#print event['session']
    print event
    session = event['session']
    request = event['request']
    response = request_handler(session, request)
    print response
    print json.dumps({"version":appVersion,"response":response}) #,sort_keys=True,indent=4)

    #return json.dumps({"version":appVersion,"response":response}) #,indent=2,sort_keys=True)
    return {"version":appVersion,"response":response} #,indent=2,sort_keys=True)

def request_handler(session, request):
    requestType = request['type']
	
    if requestType == "LaunchRequest":
        return launch_request(session, request)
    elif requestType == "IntentRequest":
        return intent_request(session, request)

def launch_request(session, request):
    output_speech = "Welcome to Sonos. Please say a command."
    output_type = "PlainText"

    card_type = "Simple"
    card_title = "Sonos - Welcome"
    card_content = "Welcome to Sonos. Please say a command."

    response = {"outputSpeech": {"type":output_type,"text":output_speech},"card":{"type":card_type,"title":card_title,"content":card_content},'shouldEndSession':False}

    return response

def intent_request(session, request):
    print "intent_request"

    if request['intent']['name'] ==  "OneshotSonosIntent":
        artist = request['intent']['slots']['artist']['value']
        source = request['intent']['slots']['source']['value']

        sqs_response = queue.send_message(MessageBody=json.dumps({"action":"deborah", "number":number}))

        output_speech = artist + " from " + source + " will start playing soon"
        output_type = "PlainText"

        card_type = "Simple"
        card_title = "Sonos - playing random selection from artist"
        card_content = artist + " from " + source + " will start playing soon"

        response = {"outputSpeech": {"type":output_type,"text":output_speech},"card":{"type":card_type,"title":card_title,"content":card_content},'shouldEndSession':True}

        return response

    elif request['intent']['name'] ==  "Shuffle":
        number = request['intent']['slots']['number']['value']
        artist = request['intent']['slots']['artist']['value']

        sqs_response = queue.send_message(MessageBody=json.dumps({"action":"shuffle", "artist":artist,"number":number}))

        output_speech = "I will shuffle " + str(number) + " songs from " + artist
        output_type = "PlainText"

        card_type = "Simple"
        card_title = "Shuffle"
        card_content = "Shuffle ..."

        response = {"outputSpeech": {"type":output_type,"text":output_speech},"card":{"type":card_type,"title":card_title,"content":card_content},'shouldEndSession':True}

        return response

    elif request['intent']['name'] ==  "Deborah":
        number = request['intent']['slots']['number']['value']

        sqs_response = queue.send_message(MessageBody=json.dumps({"action":"deborah", "number":number}))

        output_speech = "I will play " + str(number) + " of Deborah's albums"
        output_type = "PlainText"

        card_type = "Simple"
        card_title = "Nest Control - Setting Nest Temp"
        card_content = "Telling Nest to set to " + "str(setTemp+2)" + " degrees fahrenheit."

        response = {"outputSpeech": {"type":output_type,"text":output_speech},"shouldEndSession":True, "sessionAttributes":{}}

        return response
    
