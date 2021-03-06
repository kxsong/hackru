import urlparse
import requests
import json
from os import path
from time import sleep
from sys import argv, exit
from string import find

botheaders = {'User-agent': 'youtube repost finder by kxsong'}
last_id = ''
last_time = 0
modhash = ''
cookies = {}

def main():
	if len(argv) >= 3:
		login()
		scrape(argv[1], argv[2])
	elif len(argv) == 2:
		login()
		scrape(argv[1])
	else:
		print 'Usage: python yt_repost.py subreddit [last_ID]'

def login():
	global modhash, cookies, botheaders
	f = open(path.expanduser('~/username.txt'))
	user = f.readline().rstrip('\n')
	password = f.readline().rstrip('\n')
	payload = {'api_type': 'json', 'user': user, 'passwd': password}
	r = requests.post('http://www.reddit.com/api/login/' + user, data=payload, headers=botheaders)
	if r.status_code != 200:
		print 'error logging in: HTTP code ' + r.status_code
	else:
		j = json.loads(r.text)
		print j
		if len(j['json']['errors']) > 0:
			print 'error logging in:'
		else:
			modhash = j['json']['data']['modhash']
			cookies = r.cookies
			print 'logged in'
	sleep(2)

def scrape(subreddit, start=None):
	global last_id, last_time
	if start:
		r = requests.get('http://www.reddit.com/'+start+'/.json')
		try:
			j = json.loads(r.text)
			last_id = 't3_' + start
			last_time = j[0]['data']['children'][0]['data']['created_utc']
		except:
			print 'unable to get submission data for http://reddit.com/'+start+'/'
			exit(1)
	while True:
		r = requests.get('http://www.reddit.com/r/'+subreddit+'/new/.json?sort=new&before='+last_id)
		#print 'searching with before=' + last_id
		try:
			j = json.loads(r.text)
		except:
			print 'unable to get subreddit data for /r/'+subreddit+'/. Does the subreddit exist? If it is'+\
			'a private subreddit, does the bot have access to it?'
			exit(1)
		print 'searching through ' + str(len(j['data']['children'])) + ' submissions'
		sleep(2)
		for submission in j['data']['children']:
			data = submission['data']
			if data['created_utc'] > last_time:
				print 'New most recent: ' + data['id'] + ' ' + data['title'] + ' at ' + str(data['created_utc'])
				last_time = data['created_utc']
				last_id = 't3_' + data['id']
			if data['domain'] == 'youtu.be' or data['domain'] == 'youtube.com':
				v_id = getv_id(data['url'])
				reddit_id = data['name']
				print data['name'] + ': ' + data['title'] + ': ' + v_id
				reposts = getreposts(data['url'], subreddit, reddit_id)
				if not reposts:
					continue
				comment = makecomment(reposts, data, subreddit)
				#print comment
				postcomment(comment, 't3_'+data['id'])
		sleep(30)
		
def makecomment(reposts, original, subreddit):
	tablebody = u''
	for data in reposts:
		tablebody += '|[' + data['title'] + '](' + 'http://reddit.com' + \
		data['permalink'] + ')|'+data['url']+'|+'+ str(data['ups']) + ' -' + str(data['downs'])+ \
		'|' + str(data['num_comments']) + '|\n'
	comment = \
u'''This bot found {0} duplicate submissions in /r/{1} that Reddit may not have detected while submitting:

|Title|URL|votes|comments|
|-|-|-|-|
{2}
[^about ^this ^bot](https://github.com/kxsong/hackru/wiki/About) ^| [^send ^feedback](http://www.reddit.com/message/compose/?to=kxsong&subject=Bot%20feedback&message=%5Bcontext%5D%28{3}%29)'''\
	.format(len(reposts), subreddit, tablebody, 'http://reddit.com' + original['permalink'])
	print 'found ' + str(len(reposts)) + ' reposts'
	return comment	

def postcomment(text, parent):
	global modhash, cookies, botheaders
	payload = {'text': text, 'parent': parent, 'uh': modhash}
	#print payload
	success = False
	while not success:
		r = requests.post('http://www.reddit.com/api/comment', data=payload, headers=botheaders, cookies=cookies)
		ratelimited = find(r.text, 'try again in ')
		if ratelimited > 0:
			print "rate limited, sleeping"
			sleep(30)
			#sleeping only makes sense if this bot is running on a single subreddit
		else:
			success = True
	#print r.text
	sleep(2)	
	
def getv_id(url):
	o = urlparse.urlparse(url)
	if o.netloc == 'youtu.be' or o.netloc == 'www.youtu.be':
		return o.path[1:]
	if (o.netloc == 'youtube.com' or o.netloc == 'www.youtube.com') and o.path == '/watch':
		query = urlparse.parse_qs(o.query)
		if 'v' in query:
			return query['v'].pop().rstrip('?')
	return ''
	
def getreposts(url, subreddit=None, reddit_id=None, utc=0):
	v_id = getv_id(url)
	if not v_id:
		return
	print 'looking for duplicates with id : ' + v_id
	results = []
	merge = True
	base_urls = ['http://www.reddit.com/api/info.json?url=youtube.com/watch?v=' + v_id, \
	'http://www.reddit.com/api/info.json?url=youtu.be/' + v_id, \
	'http://www.reddit.com/api/info.json?url=youtube.com/watch?v=' + v_id + '%26feature=youtu.be', \
	'http://www.reddit.com/api/info.json?url=youtube.com/watch?feature=player_embedded%26v=' + v_id]
	#feature after: related|plcp|relmfu, youtu.be, g-all-u, endscreen, share, youtube_gdata_player, fvwrel
	#feature before: player_embedded, player_detailpage
	#sns=fb
	for base_url in base_urls:
		subresults = []
		merge = True
		r = requests.get(base_url, headers=botheaders)
		j = json.loads(r.text)
		for submission in j['data']['children']:
			data = submission['data']
			if data['name'] == reddit_id:
				merge = False #if reddit can detect these duplicates, no need to retell
			if (not subreddit or data['subreddit'] == subreddit):
				subresults.append(data)				
		if merge:
			for result in subresults:
				results.append(result)
		sleep(2)
	return results

if __name__ == '__main__':
    main()