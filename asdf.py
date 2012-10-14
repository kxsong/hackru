import urlparse
import requests
import json
from os import path
from time import sleep

botheaders = {'User-agent': 'youtube repost finder by kxsong'}
latest = "t3_11ffdr"
modhash = ""
cookies = {}

def login():
	global modhash, cookies, botheaders
	f = open(path.expanduser('~/username.txt'))
	user = f.readline().rstrip('\n')
	password = f.readline().rstrip('\n')
	payload = {'api_type': 'json', 'user': user, 'passwd': password}
	r = requests.post('http://www.reddit.com/api/login/' + user, data=payload, headers=botheaders)
	if r.status_code != 200:
		print "error logging in: HTTP code " + r.status_code
	else:
		j = json.loads(r.text)
		print j
		if len(j["json"]["errors"]) > 0:
			print "error logging in:"
		else:
			modhash = j['json']['data']['modhash']
			cookies = r.cookies
			print "logged in"
	sleep(2)

def scrape(subreddit):
	r = requests.get('http://www.reddit.com/r/'+subreddit+'/new/.json?sort=new')
	sleep(2)
	j = json.loads(r.text)
	for submission in j['data']['children']:
		data = submission['data']
		if data['domain'] == "youtu.be" or data['domain'] == "youtube.com":
			v_id = getv_id(data['url'])
			reddit_id = data['name']
			print data['name'] + ": " + data['title'] + ": " + v_id
			reposts = getreposts(data['url'], subreddit, reddit_id)
			comment = makecomment(reposts, data)
			postcomment(comment, 't3_'+data['id'])

def postcomment(text, parent):
	global modhash, cookies, botheaders
	payload = {'text': text, 'parent': parent, 'uh': modhash}
	print payload
	r = requests.post('http://www.reddit.com/api/comment', data=payload, headers=botheaders, cookies=cookies)
	print r.text
	sleep(2)

def makecomment(reposts, original):
	tablebody = ""
	for data in reposts:
		tablebody += "|/r/" + data['subreddit'] + '|[' + data['title'] + '](' + 'http://reddit.com' + \
		data['permalink'] + ')|todo|\n'
	comment = \
"""{0} duplicate youtube submissions in this subreddit:

|Subreddit|Title|Time|
|-|-|-|
{1}
[^about ^this ^bot](https://github.com/kxsong/hackru/wiki/About) ^| [^send ^feedback](http://www.reddit.com/message/compose/?to=kxsong&subject=Bot%20feedback&message=%5Bcontext%5D%28{2}%29)"""\
	.format(len(reposts), tablebody, "http://reddit.com" + original['permalink'])
	return comment	
	
def getv_id(url):
	o = urlparse.urlparse(url)
	if o.netloc == 'youtu.be' or o.netloc == 'www.youtu.be':
		return o.path[1:]
	if (o.netloc == 'youtube.com' or o.netloc == 'www.youtube.com') and o.path == '/watch':
		query = urlparse.parse_qs(o.query)
		return query['v'].pop().rstrip('?')
	return ''
	
def getreposts(url, subreddit=None, reddit_id=None, utc=0):
	v_id = getv_id(url)
	print "vid : " + v_id
	result = []
	base_urls = ["http://www.reddit.com/api/info.json?url=youtube.com/watch?v=" + v_id, \
	"http://www.reddit.com/api/info.json?url=youtu.be/" + v_id]
	for url in base_urls:
		r = requests.get(url, headers=botheaders)
		j = json.loads(r.text)
		for submission in j["data"]["children"]:
			data = submission["data"]
			if (not subreddit or data["subreddit"] == subreddit) and data['name'] != reddit_id:
				result.append(data)
		sleep(2)
	return result