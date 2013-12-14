#!/usr/bin/python

from DB import DB
from time import time as timetime

# Request user
# Get: Posts and comments
# Each post/comment: list of images.
class Queries(object):
	SEARCH_FIELDS = ['user', 'reddit', 'title', 'comment', 'from', 'to', 'album', 'url']

	'''
		Parses search fields from text.
		Similar to reddit's specialized search.
		returns tuple:
			[0] list of unspecified text fields
			[1] dict of lists; containing specified text fields
		Quoted fields will be combined.
		Non-specified text will be returned in the first tuple
		Specified fields will be added to a specified bucket. Examples:
		'one two three'         => ( ['one', 'two', 'three'], {} )
		'"one two" three'       => ( ['one two', 'three'],    {} )
		'blah user:asdf         => ( ['blah'], { 'user': ['asdf'] } )
		'reddit:nsfw user:asdf  => ( [], { 'reddit': ['nsfw'], 'user': ['asdf'] } )
		'title:this title:first => ( [], { 'title': ['this', 'first'] } )
	'''
	@staticmethod
	def get_search_fields(text):
		fields = text.split(' ')
		i = 0
		# Combine quoted fields
		while i < len(fields):
			if fields[i].startswith('"'):
				fields[i] = fields[i][1:]
				while i + 1 < len(fields):
					fields[i] += ' ' + fields[i+1]
					fields.pop(i+1)
					if fields[i].endswith('"'):
						fields[i] = fields[i][:-1]
						break
			i += 1
		# Split into 'texts' and 'filters'
		filters = {}
		texts = []
		for field in fields:
			if ':' in field:
				key = field.split(':')[0]
				value = ':'.join(field.split(':')[1:])
				if key in Queries.SEARCH_FIELDS:
					lst = filters.get(key, [])
					lst.append('%%%s%%' % value)
					filters[key] = lst
			else:
				texts.append('%%%s%%' % field)
		return (texts, filters)

	@staticmethod
	def search_users(texts, filters, start, count):
		results_users = []
		if len(texts) > 0 or len(filters['user']) > 0:
			query = '''
				select 
					users.username, users.created, users.updated, 
					users.deleted, users.views, users.rating, users.ratings
				from (select * from users
					where
			'''
			conditions     = []
			search_values  = []
			if 'user' in filters and len(filters['user']) > 0:
				conditions += ['username like ?'] * len(filters['user'])
				search_values += filters['user']
			elif len(texts) > 0:
				conditions += ['username like ?'] * len(texts)
				search_values += texts
			query += ' OR '.join(conditions)
			query += '''
					limit %d
					offset %d
				) users
			''' % (count, start)
			db = DB()
			cur = db.conn.cursor()
			execur = cur.execute(query, search_values)
			results = execur.fetchall()
			for (username, created, updated, 
					 deleted, views, rating, ratings) in results:
				results_users.append( {
					'user'     : username,
					'created'  : created,
					'updated'  : updated,
					'deleted'  : deleted,
					'views'    : views,
					'rating'   : rating,
					'ratings'  : ratings,
				})
		return results_users
	
	@staticmethod
	def search_posts(texts, filters, start, count):
		results_posts = []
		query = '''
			select
					posts.id, posts.title, posts.url, posts.subreddit, 
					posts.created, posts.permalink, users.username
				from posts,users
				where
					users.id = posts.userid AND
					'''
		conditions_or  = []
		conditions_and = []
		search_values  = []

		if 'title' in filters and len(filters['title']) > 0:
			conditions_and.extend(['title like ?'] * len(filters['title']))
			search_values.extend(filters['title'])
		else:
			conditions_or.extend(['title like ?'] * len(texts))
			search_values.extend(texts)

		if 'user' in filters and len(filters['user']) > 0:
			conditions_and.extend(['username like ?'] * len(filters['user']))
			search_values.extend(filters['user'])
		else:
			conditions_or.extend(['username like ?'] * len(texts))
			search_values.extend(texts)
		if 'reddit' in filters and len(filters['reddit']) > 0:
			conditions_and.extend(['subreddit like ?'] * len(filters['reddit']))
			search_values.extend(filters['reddit'])
		else:
			conditions_or.extend(['subreddit like ?'] * len(texts))
			search_values.extend(texts)

		if len(conditions_or) > 0:
			query += '(%s)' % ' OR '.join(conditions_or)
		if len(conditions_or) > 0 and len(conditions_and) > 0:
			query += ' AND '
		if len(conditions_and) > 0:
			query += '(%s)' % ' AND '.join(conditions_and)

		query += '''
				limit %d
				offset %d
		''' % (count, start)

		db = DB()
		cur = db.conn.cursor()
		execur = cur.execute(query, search_values)
		results = execur.fetchall()
		for (postid, title, url, reddit, created, permalink, user) in results:
			results_posts.append( {
				'id'        : postid,
				'title'     : title,
				'url'       : url,
				'subreddit' : reddit,
				'created'   : created,
				'permalink' : permalink,
				'user'      : user,
			})
		return results_posts
		
	@staticmethod
	def search(text, start=0, count=20):
		(texts, filters) = Queries.get_search_fields(text)

		# USERS
		results_users = Queries.search_users(texts, filters, start, count)

		# POSTS
		results_posts = Queries.search_posts(texts, filters, start, count)

		# COMMENTS
		# TODO
		pass

		return {
			'users' : results_users,
			'posts' : results_posts
		}

	'''
		Retrieves from full list of users
		Returns user info along with # of images, albums, posts, and comments.
	'''
	@staticmethod
	def get_users(sortby='username', orderby='asc', start=0, count=20):
		if sortby not in ['username', 'created', 'updated']:
			sortby = 'username'
		if orderby not in ['asc', 'desc']:
			orderby = 'asc'
		query = '''
			select
				id, users.username, users.created, users.updated
			from users
			order by %s %s
			limit %d
			offset %d
		''' % (sortby, orderby, count, start)
		db = DB()
		cur = db.conn.cursor()
		execur = cur.execute(query)
		results = execur.fetchall()
		users = []
		for (userid, username, created, updated) in results:
			images = []
			query = '''
				select
					path, width, height, size, thumb, type
				from images
				where
					images.userid = ?
				limit 4
			'''
			execur = cur.execute(query, [userid])
			image_results = execur.fetchall()
			for (path, width, height, size, thumb, imagetype) in image_results:
				images.append({
					'path'   : path,
					'width'  : width,
					'height' : height,
					'size'   : size,
					'thumb'  : thumb,
					'type'   : imagetype
				})

			post_count  = db.count('posts',  'userid = ?', [userid])
			image_count = db.count('images', 'userid = ?', [userid])
			
			users.append( {
				'user'    : username,
				'created' : created,
				'updated' : updated,
				'images'  : images,
				'post_n'  : post_count,
				'image_n' : image_count
			})
		cur.close()
		return {
				'users' : users
			}

	@staticmethod
	def get_user_posts(user, sortby='created', orderby='asc', start=0, count=20):
		# XXX Select from images, group by post,album
		# ... but images -> post is many->one (even when not an album)

		if sortby not in ['id', 'created', 'subreddit', 'ups']:
			sortby = 'created'
		if orderby not in ['asc', 'desc']:
			orderby = 'desc'

		query = '''
			select
				id, title, url, selftext, subreddit, created, permalink, ups, downs
			from posts
			where 
				posts.userid in
					(select id from users where username = ?)
			order by %s %s
			limit  %d
			offset %d
		''' % (sortby, orderby, count, start)
		db = DB()
		cur = db.conn.cursor()
		execur = cur.execute(query, [user])
		results = execur.fetchall()
		posts = []
		for (postid, title, url, selftext, subreddit, created, permalink, ups, downs) in results:
			images = []
			query = '''
				select
					path, width, height, size, thumb, type
				from images
				where
					images.post = ?
			'''
			execur = cur.execute(query, [postid])
			image_results = execur.fetchall()
			for (path, width, height, size, thumb, imagetype) in image_results:
				images.append({
					'path'   : path,
					'width'  : width,
					'height' : height,
					'size'   : size,
					'thumb'  : thumb,
					'type'   : imagetype
				})
			posts.append({
				'id'        : postid,
				'title'     : title,
				'url'       : url,
				'selftext'  : selftext,
				'subreddit' : subreddit,
				'created'   : created,
				'permalink' : permalink,
				'ups'       : ups,
				'downs'     : downs,
				'images'    : images
			})

		response = {
				'user'  : user,
				'posts' : posts
			}

		if start == 0:
			userid = db.select_one('id', 'users', 'username = ?', [user])
			response['post_count']  = db.count('posts',  'userid = ?', [userid])
			response['image_count'] = db.count('images', 'userid = ?', [userid])
			response['updated'] = db.select_one('updated', 'users', 'id = ?', [userid])
			response['created'] = db.select_one('created', 'users', 'id = ?', [userid])

		cur.close()
		return response

	@staticmethod
	def get_user_comments(user, sortby='created', orderby='asc', start=0, count=20):
		if sortby not in ['id', 'postid', 'created', 'subreddit', 'ups']:
			sortby = 'created'
		if orderby not in ['asc', 'desc']:
			orderby = 'desc'

		query = '''
			select
				id, postid, text, subreddit, created, permalink, ups, downs
			from comments
			where 
				comments.userid in
					(select id from users where username = ?)
			order by %s %s
			limit  %d
			offset %d
		''' % (sortby, orderby, count, start)
		db = DB()
		cur = db.conn.cursor()
		execur = cur.execute(query, [user])
		results = execur.fetchall()
		comments = []
		for (commentid, postid, text, subreddit, created, permalink, ups, downs) in results:
			images = []
			query = '''
				select
					path, width, height, size, thumb, type
				from images
				where
					images.post = ?
			'''
			execur = cur.execute(query, [postid])
			image_results = execur.fetchall()
			for (path, width, height, size, thumb, imagetype) in image_results:
				images.append({
					'path'   : path,
					'width'  : width,
					'height' : height,
					'size'   : size,
					'thumb'  : thumb,
					'type'   : imagetype
				})
			comments.append({
				'id'        : commentid,
				'postid'    : postid,
				'text'      : text,
				'subreddit' : subreddit,
				'created'   : created,
				'permalink' : permalink,
				'ups'       : ups,
				'downs'     : downs,
				'images'    : images
			})
		cur.close()
		return {
				'user'     : user,
				'comments' : comments
			}

	@staticmethod
	def get_posts(user=None, sortby='created', orderby='asc', start=0, count=20):
		if sortby not in ['created', 'subreddit', 'ups', 'username']:
			sortby = 'created'
		if sortby == 'username':
			sortby = 'users.username'
		else:
			sortby = 'posts.%s' % sortby
		if orderby not in ['asc', 'desc']:
			orderby = 'desc'

		if user != None:
			where = 'where username = ?'
			values = [user]
		else:
			where = ''
			values = []
		query = '''
			select
				posts.id, title, url, selftext, subreddit, 
				posts.created, permalink, ups, downs, username
			from posts inner join users on users.id = posts.userid
			%s
			order by %s %s
			limit  %d
			offset %d
		''' % (where, sortby, orderby, count, start)
		db = DB()
		cur = db.conn.cursor()
		execur = cur.execute(query, values)
		results = execur.fetchall()
		posts = []
		for (postid, title, url, selftext, subreddit, created, permalink, ups, downs, author) in results:
			images = []
			query = '''
				select
					path, width, height, size, thumb, type
				from images
				where
					images.post = ?
			'''
			execur = cur.execute(query, [postid])
			image_results = execur.fetchall()
			for (path, width, height, size, thumb, imagetype) in image_results:
				images.append({
					'path'   : path,
					'width'  : width,
					'height' : height,
					'size'   : size,
					'thumb'  : thumb,
					'type'   : imagetype
				})
			posts.append({
				'id'        : postid,
				'title'     : title,
				'url'       : url,
				'selftext'  : selftext,
				'subreddit' : subreddit,
				'created'   : created,
				'permalink' : permalink,
				'ups'       : ups,
				'downs'     : downs,
				'images'    : images,
				'author'    : author
			})
		response = {
			'posts' : posts
		}
		cur.close()
		return response

	@staticmethod
	def user_already_added(user):
		db = DB()
		return db.user_already_added(user)

if __name__ == '__main__':
	q = Queries()
	#print q.get_users('username', 'asc', start=0, count=20)
	#print q.get_search_fields('testing one two three reddit:asdf user:fdsa')
	#print q.get_search_fields('testing "one two three" reddit:asdf user:fdsa')
	#print q.get_search_fields('testing "one two three" "reddit:asdf 789" reddit:890 user:fdsa')
	#print q.get_search_fields('testing url:http://test.com/asdf more')
	#print q.search('reddit:gonewild user:thatnakedgirl album:yes')
	#print q.search('sexy')
	#print q.get_user_posts('1_more_time')
	#print q.get_user_comments('1_more_time')
	print q.get_posts()
