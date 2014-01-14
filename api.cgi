#!/usr/bin/python

from py.Queries import Queries # Interacting w/ database
from py.Gonewild import Gonewild

from json import dumps

from traceback import format_exc # Stack traces

from cgi   import FieldStorage # Query keys
from cgitb import enable as cgi_enable; cgi_enable() # for debugging


''' Where the magic happens '''
def main():
	keys = get_keys()

	# Input sanitization
	if not 'method' in keys:
		return {'error':'unspecified method'}
	if 'start' in keys and not keys['start'].isdigit():
		return {'error':'start parameter must be numeric'}
	if 'count' in keys and not keys['count'].isdigit():
		return {'error':'count parameter must be numeric'}

	method = keys['method']

	if   method == 'get_users': return get_users(keys)
	elif method == 'get_user':  return get_user(keys)
	elif method == 'get_posts': return get_posts(keys)
	elif method == 'search':    return search(keys)
	elif method == 'add_user':  return add_user(keys)
	elif method == 'get_zip':   return get_zip(keys)
	elif method == 'get_rip':   return get_rip(keys)
	elif method == 'search_user': return search_user(keys)
	else: return {'error':'unexpected method'}


'''
	Get list of users
'''
def get_users(keys):
	return Queries.get_users(
			sortby  = keys.get('sort', ''),
			orderby = keys.get('order', ''),
			start   = int(keys.get('start', 0)),
			count   = int(keys.get('count', 10))
		)


'''
	Get posts/images for a specific user
'''
def get_user(keys):
	if not 'user' in keys:
		return {'error' : 'user required for get_user API'}

	if keys.get('feed', 'posts') != 'posts':
		return Queries.get_user_comments(
				keys['user'],
				sortby  =     keys.get('sort',  ''),
				orderby =     keys.get('order', ''),
				start   = int(keys.get('start', 0)),
				count   = int(keys.get('count', 10))
			)
	else:
		return Queries.get_user_posts(
				keys['user'],
				sortby  =     keys.get('sort',  ''),
				orderby =     keys.get('order', ''),
				start   = int(keys.get('start', 0)),
				count   = int(keys.get('count', 10))
			)
	

'''
	Get list of posts
'''
def get_posts(keys):
	return Queries.get_posts(
			user    = keys.get('user', None),
			sortby  = keys.get('sort', ''),
			orderby = keys.get('order', ''),
			start   = int(keys.get('start', 0)),
			count   = int(keys.get('count', 10))
		)


'''
	Search for user/post/comment
'''
def search(keys):
	if not 'search' in keys:
		return {'error':'search parameter required for search method'}
	if not 'type' in keys:
		# Default search
		return Queries.search(
				keys['search'],
				start   = int(keys.get('start', 0)),
				count   = int(keys.get('count', 10))
			)
	elif keys['type'] == 'post':
		return Queries.search_posts(
				keys['search'],
				start   = int(keys.get('start', 0)),
				count   = int(keys.get('count', 10))
			)
	elif keys['type'] == 'user':
		return Queries.search_users(
				keys['search'],
				start   = int(keys.get('start', 0)),
				count   = int(keys.get('count', 10))
			)
		
'''
	Search by user
'''
def search_user(keys):
	if not 'user' in keys:
		return {'error':'user required'}
	from py.DB import DB
	db = DB()
	cursor = db.conn.cursor()
	try:
		user = db.select_one('username', 'users', 'username like ?', [keys['user']])
		if user != None:
			return {'users' : [user]}
	except:
		pass
	q = '''
		select username
		from users
		where username like ?
		limit %d
		offset %d
	''' % (keys.get('count', 10), keys.get('start', 0))
	curexec = cursor.execute(q, ['%%%s%%' % keys['user'] ])
	result = []
	for (username,) in curexec:
		result.append(username)
	cursor.close()
	return {
			'users' : result
		}

'''
	Add user to list
'''
def add_user(keys):
	if not 'user' in keys:
		return {'error':'user not entered'}
	user = sanitize_user(keys['user'])
	if len(user) < 3:
		return {'error':'invalid username: "%s" -- too short' % user}
	if Queries.user_already_added(user):
		return {'error':'user already added'}
	gonewild = Gonewild()
	if not gonewild.user_has_gone_wild(keys['user']):
		return {'error':'user "%s" has not recently gone wild' % user}
	gonewild.db.add_user(user, new=True)
	return {'error':'added user "%s"' % user}


def get_zip(keys):
	user   = keys.get('user')
	album  = keys.get('album', None)
	videos = keys.get('include_videos', 'false')
	include_videos = videos in ['true', 'True']
	return Queries.get_zip(
			user,
			include_videos = include_videos,
			album = album
		)


def get_rip(keys):
	if not 'user' in keys:
		return {'error':'user not entered'}
	return Queries.get_rip(keys['user'])


#####################
# HELPER METHODS

def get_cookies(): # Get client cookies
	d = {}
	if not 'HTTP_COOKIE' in os.environ: return d
	cookies = os.environ['HTTP_COOKIE'].split(";")
	for cookie in cookies:
		cookie = cookie.strip()
		(key, value) = cookie.split('=')
		d[key] = value
	return d

def get_keys(): # Get query keys
	form = FieldStorage()
	keys = {}
	for key in form.keys():
		keys[key] = form[key].value
	return keys

def sanitize_user(user): # lower() and strip() non-valid characters from user
	return ''.join([c if c.lower() in 'abcdefghijklmnopqrstuvwxyz1234567890_-' else '' for c in user])


########################
# ENTRY POINT

if __name__ == '__main__':
	print "Content-Type: application/json"
	print ""
	try:
		print dumps(main(), indent=2)
	except Exception, e:
		# Return stacktrace
		print dumps({'error': str(format_exc())})
	print "\n\n"
