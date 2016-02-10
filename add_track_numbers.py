import pysolr
import requests
import config as c

solr = pysolr.Solr(c.ec_uri+':8983/solr/sonos_companion/', timeout=10)
collection = 'sonos_companion'

album_title = raw_input("what album do you want? ")
s = 'album:' + ' AND album:'.join(album_title.split())
result = solr.search(s, fl='id,album,title', rows=25) #**{'rows':25}) #only brings back actual matches but 25 seems like max for most albums
tracks = result.docs
for track in tracks:
    print "What is the track number for track {} from album {}".format(track['title'],track['album'])
    n = raw_input("What is the track number? ")
    n = int(n)
    print "The track number asigned to {} is {}".format(track['title'],n)
    print track['id']
    url = c.ec_uri+":8983/solr/"+collection+"/update"
    data = [{"id":track['id'], "track": {"set":n}}]
    headers =  { "content-type" : "application/json" }
    r = requests.post(url, json=data, headers=headers)
    print r.json()
    r = requests.post(url, data={"commit":"true"})
    print r
