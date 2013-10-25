#!/usr/bin/python

from json  import loads
from Httpy import Httpy
from time  import sleep, strftime, gmtime
from sys   import stderr

class Child(object):
	def __init__(self):
		self.id        = ''
		self.subreddit = ''
		self.created   = 0
		self.author    = ''

class Post(Child,object):
	def __init__(self):
		super(Post,self).__init__()
		self.over_18  = False
		self.url      = ''
		self.selftext = ''
		self.title    = ''
	def permalink(self):
		if self.subreddit != '':
			return 'http://reddit.com/r/%s/comments/%s' % (self.subreddit, self.id)
		else:
			return 'http://reddit.com/comments/%s' % self.id

class Comment(Child,object):
	def __init__(self):
		super(Comment,self).__init__()
		self.body    = ''
		self.post_id = ''
	def permalink(self):
		if self.subreddit != '':
			return 'http://reddit.com/r/%s/comments/%s/_/%s' % (self.subreddit, self.post_id, self.id)
		else:
			return 'http://reddit.com/comments/%s/_/%s' % (self.post_id, self.id)

''' Retrieve posts/comments from reddit '''
class Reddit(object):
	logger = stderr
	httpy = Httpy(user_agent='user ripper by /u/4_pr0n, or contact admin@rarchives.com')

	@staticmethod
	def debug(text):
		tstamp = strftime('[%Y-%m-%dT%H:%M:%SZ]', gmtime())
		text = '%s Reddit: %s' % (tstamp, text)
		Reddit.logger.write('%s\n' % text)
		if Reddit.logger != stderr:
			stderr.write('%s\n' % text)

	@staticmethod
	def login(user, password):
		Reddit.httpy.clear_cookies()
		d = {
				'user'   : user,
				'passwd' : password,
				'api_type' : 'json'
			}
		r = Reddit.httpy.oldpost('http://www.reddit.com/api/login/%s' % user, d)
		if 'WRONG_PASSWORD' in r:
			raise Exception('login: invalid password')
		if 'RATELIMIT' in r:
			raise Exception('login: rate limit')
		try:
			json = loads(r)
		except Exception, e:
			raise Exception('login: failed to parse response: %s' % r)
		if not 'json' in json or not 'data' in json['json']:
			raise Exception('login: failed: %s' % r)
		# Logged in
		Reddit.debug('logged in')

	@staticmethod
	def get(url):
		results = []
		Reddit.debug('loading %s' % url)
		sleep(2)
		try:
			r = Reddit.httpy.get(url)
			json = loads(r)
		except Exception, e:
			Reddit.debug('exception: %s' % str(e))
			raise e
		children = json['data']['children']
		#Reddit.debug('get: found %d posts/comments' % len(children))
		for child in children:
			result = {}
			if child['kind'] == 't1':
				# Comment
				comment = child['data']
				result = Comment()
				result.id        = comment['id']
				result.author    = comment['author']
				result.post_id   = comment['link_id'].split('_')[-1]
				result.body      = comment['body']
				result.subreddit = comment['subreddit']
				result.created   = comment['created_utc']
			elif child['kind'] == 't3':
				# Post
				post = child['data']
				result = Post()
				result.id        = post['id']
				result.author    = post['author']
				result.over_18   = post['over_18']
				result.title     = post['title']
				result.subreddit = post['subreddit']
				result.created   = post['created_utc']
				if post['is_self'] and 'selftext' in post:
					result.selftext = post['selftext']
				else:
					result.url = post['url']
			results.append(result)
		return results
		
		
	@staticmethod
	def get_user(user, since=None, max_pages=None):
		""" 
			Get all comments and posts for a user since 'since'.
			'since' is either a post id or comment id
		"""
		results = []
		url = 'http://www.reddit.com/user/%s.json' % user
		Reddit.debug('loading %s' % url)
		sleep(2)
		try:
			r = Reddit.httpy.get(url)
		except Exception, e:
			Reddit.debug('exception: %s' % str(e))
			raise e
		if r.strip() == '':
			# User is deleted
			raise Exception('user is deleted')
		page = 1
		while True:
			try:
				json = loads(r)
			except Exception, e:
				Reddit.debug('failed to load JSON: %s\n%s' % (str(e), r))
				return results
			if 'error' in json and json['error'] == 404:
				raise Exception('account %s is deleted (404)' % user)
			if not 'data' in json or not 'children' in json['data']:
				return []
			children = json['data']['children']
			#Reddit.debug('get: found %d posts/comments' % len(children))
			for child in children:
				if since != None and child['data']['id'] == since:
					return results
				result = {}
				if child['kind'] == 't1':
					# Comment
					comment = child['data']
					result = Comment()
					result.id        = comment['id']
					result.author    = comment['author']
					result.post_id   = comment['link_id'].split('_')[-1]
					result.body      = comment['body']
					result.subreddit = comment['subreddit']
					result.created   = comment['created_utc']
				elif child['kind'] == 't3':
					# Post
					post = child['data']
					result = Post()
					result.id        = post['id']
					result.author    = post['author']
					result.over_18   = post['over_18']
					result.title     = post['title']
					result.subreddit = post['subreddit']
					result.created   = post['created_utc']
					if post['is_self'] and 'selftext' in post:
						result.selftext = post['selftext']
					else:
						result.url = post['url']
				results.append(result)
			if len(children) == 0 or not 'after' in json['data']: break
			after = json['data']['after']
			if after == None:
				Reddit.debug('get: hit end of posts/comments')
				break
			if max_pages != None and max_pages >= page: break
			next_url = '%s?after=%s' % (url, after)
			Reddit.debug('loading %s' % next_url)
			sleep(2)
			r = Reddit.httpy.get(next_url)
			page += 1
		return results

	@staticmethod
	def get_links_from_text(text):
		''' Returns list of URLs from given text (comment or selftext) '''
		urls = []
		i = -1
		while True:
			i = text.find('://', i+1)
			if i == -1: break
			j = i
			while j < len(text) and text[j] not in [')', ']', ' ', '"', '\n', '\t']:
				j += 1
			urls.append('http%s' % text[i:j])
			i = j
		return list(set(urls)) # Kill duplicates

if __name__ == '__main__':
	for child in Reddit.get_user('hornysailor80', since='ccpj21b'): # ccbzguz
		if type(child) == Post:
			if child.selftext != None:
				print 'POST selftext:', Reddit.get_links_from_text(child.selftext),
			else:
				print 'POST url:', child.url,
		elif type(child) == Comment:
			print 'COMMENT', child.body, #Reddit.get_links_from_text(child.body)
		print 'created: %d' % child.created

