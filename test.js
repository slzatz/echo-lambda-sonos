var alexa = require('alexa-app');
var http = require('http');

// config.App_ID contains the app id for the skill
var config = require('./config');

var app = new alexa.app('test');

app.dictionary = {
	//artists: ["Neil Young", "Patty Griffin", "Dar Williams", "Bruce Springsteen"], sources: ["Pandora", "Amazon"]
	artists: ["neil young", "patty griffin", "dar williams", "bruce springsteen", "bob dylan", "damien rice", "lucinda williams"], sources: ["pandora", "amazon"]
};

app.launch(function(request,response) {
    response.shouldEndSession(false);
	response.say("App launched!");
});


app.intent('OneshotSonosIntent',
    // The lines below that define slots and utterances can be eliminated unless you are trying to generate them

	{
		"slots":{artist:"LITERAL", source:"LITERAL"}, 
		"utterances":[ "Play {artists|artist} through {sources|source}" ]
	},

	function(request,response) {

        var artist = request.slot('artist');
        var source = request.slot('source');
      
        makeSonosRequest(artist, source, function sonosResponseCallback(err) { 

          if (err) {
              console.log("Sorry, something went wrong -- maybe Steve's Amazon AWS site seems to be down");
          } else {
              console.log(artist + " from " + source + " will start playing soon");
              response.say(artist + " from " + source + " will start playing soon");
              response.send();
        }
    }); 
    
      return false;
	}
);

app.intent('Shuffle',
    // The lines below that define slots and utterances can be eliminated unless you are trying to generate them

	{
		"slots":{number:"NUMBER", artist:"LITERAL"}, 
		"utterances":[ "please shuffle {1-10|number} songs from {artists|artist}" ]
	},

	function(request,response) {

        var number = request.slot('number');
        var artist = request.slot('artist');
      
        makeSonosRequest(artist, number, function sonosResponseCallback(err) { 

          if (err) {
              console.log("Sorry, something went wrong -- maybe Steve's Amazon AWS site seems to be down");
          } else {
              console.log("I will start shuffling " + number + " songs from " + artist + " in a few moments");
              response.say("I will start shuffling " + number + " songs from " + artist + " in a few moments");
              response.send();
        }
    }); 
    
      return false;
	}
);
// Output the schema - app.schema()  outputs the schema - not sure that providng the schema to the framework any
//console.log( "\n\nSCHEMA:\n\n"+app.schema()+"\n\n" );
// Output sample utterances - as above, I think the only use of utterances in the framework is to produce a combinatorial output
console.log( "\n\nUTTERANCES:\n\n"+app.utterances()+"\n\n" );

function makeSonosRequest(arg1,arg2, sonosResponseCallback) {

    var endpoint = config.APP_URI
    var queryString = '/echo';
    queryString += '/' + arg1;
    queryString += '/' + arg2; 

    http.get(endpoint + queryString, function (res) {
        var sonosResponseString = '';

        res.on('data', function (data) {
            sonosResponseString += data;
        });

        res.on('end', function () {
            var sonosResponseObject = JSON.parse(sonosResponseString);

            if (sonosResponseObject.error) {
                console.log("Sonos error: " + sonosResponseObject.error.message);
                sonosResponseCallback(new Error(sonosResponseObject.error.message));
            } else {
                sonosResponseCallback(null);
            }
        });
    }).on('error', function (e) {
        console.log("Communications error: " + e.message);
        sonosResponseCallback(new Error(e.message));
    });
}

exports.handler = app.lambda();



