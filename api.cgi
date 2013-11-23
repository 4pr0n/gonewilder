#!/usr/bin/python

from py.Queries import Queries # Interacting w/ database

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
	elif method == 'search':    return get(keys)


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
	Search for user/post/comment
'''
def search(keys):
	if not 'search' in keys:
		return {'error':'search parameter required for search method'}

	return Queries.search(
			keys['search'],
			start   = int(keys.get('start', 0)),
			count   = int(keys.get('count', 10))
		)


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
	return ''.join([c if c in 'abcdefghijklmnopqrstuvwxyz1234567890_-' else '' for c in user])


########################
# ENTRY POINT

if __name__ == '__main__':
	print "Content-Type: text/html"
	print ""
	try:
		print dumps(main())
	except Exception, e:
		# Return stacktrace
		print dumps({'error': format_exc()})
	print "\n\n"
