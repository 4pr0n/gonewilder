#!/usr/bin/python

from DB import DB
from time import time as timetime

class Queries(object):
	SEARCH_FIELDS = ['user', 'reddit', 'title', 'comment', 'from', 'to', 'album', 'url']
	def __init__(self):
		self.db = DB()

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
	def get_search_fields(self, text):
		fields = text.split(' ')
		filters = {}
		texts = []
		i = 0
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
		for field in fields:
			if ':' in field:
				key = field.split(':')[0]
				value = ':'.join(field.split(':')[1:])
				if key in Queries.SEARCH_FIELDS:
					lst = filters.get(key, [])
					lst.append(value)
					filters[key] = lst
			else:
				texts.append(field)
		return (texts, filters)

	def search_users(self, texts, filters, start, count):
		results_users = []
		if len(texts) > 0 or len(filters['user']) > 0:
			query = '''
				select 
					users.username, users.created, users.updated, 
					users.deleted, users.views, users.rating, users.ratings
				from (select * from users
					where
			'''
			conditions = []
			if len(texts) > 0:
				conditions += ['username like ?'] * len(texts)
			if len(filters['user']) > 0:
				conditions += ['username = ?'] * len(filters['user'])
			query += ' OR '.join(conditions)
			query += '''
					limit %d
					offset %d
				) users
			''' % (count, start)
			cur = self.db.conn.cursor()
			execur = cur.execute(query, texts + filters['user'])
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
	
	def search_posts(self, texts, filters, start, count):
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
			conditions_and.extend(['subreddit = ?'] * len(filters['reddit']))
			search_values.extend(filters['reddit'])
		else:
			conditions_or.extend(['reddit like ?'] * len(texts))
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

		cur = self.db.conn.cursor()
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
		
	def search(self, text, start=0, count=20):
		started = float(timetime())

		(texts, filters) = self.get_search_fields(text)

		# USERS
		results_users = self.search_users(texts, filters, start, count)

		# POSTS
		results_posts = self.search_posts(texts, filters, start, count)

		# COMMENTS
		# TODO
		pass

		return {
			'users' : results_users,
			'posts' : results_posts
		}

	def get_users(self, sortby='username', orderby='asc', start=0, count=20):
		if sortby not in ['username', 'sinceid', 'created', 'updated', 
		               'deleted', 'blacklist', 'views', 'rating', 'ratings']:
			sortby = 'username'
		if orderby not in ['asc', 'desc']:
			orderby = 'desc'
		started = float(timetime())
		query = '''
		select
				users.username, users.created, users.updated, 
				users.deleted, users.views, users.rating, users.ratings,
				(select count(*) from posts    where posts.userid    = users.id) as post_count,
				(select count(*) from comments where comments.userid = users.id) as comment_count,
				(select count(*) from images   where images.userid   = users.id) as image_count,
				(select count(*) from albums   where albums.userid   = users.id) as album_count
			from (select * from users
				group by users.username
				order by %s %s
				limit %d
				offset %d
				) users
		''' % (sortby, orderby, count, start)
		cur = self.db.conn.cursor()
		execur = cur.execute(query)
		results = execur.fetchall()
		db_latency = float(timetime()) - started
		users = []
		for (username, created, updated, 
		     deleted, views, rating, ratings, 
		     post_count, comment_count, image_count, album_count) in results:
			users.append( {
				'user'     : username,
				'created'  : created,
				'updated'  : updated,
				'deleted'  : deleted,
				'views'    : views,
				'rating'   : rating,
				'ratings'  : ratings,
				'posts'    : post_count,
				'comments' : comment_count,
				'images'   : image_count,
				'albums'   : album_count
			})
		cur.close()
		response = {
			'users' : users,
			'latency' : '%dms' % int(db_latency * 1000)
		}
		return response
		

	def get_user(self, user, sorting, start, count):
		pass

if __name__ == '__main__':
	q = Queries()
	#print q.get_users('username', 'asc', start=0, count=20)
	#print q.get_search_fields('testing one two three reddit:asdf user:fdsa')
	#print q.get_search_fields('testing "one two three" reddit:asdf user:fdsa')
	#print q.get_search_fields('testing "one two three" "reddit:asdf 789" reddit:890 user:fdsa')
	#print q.get_search_fields('testing url:http://test.com/asdf more')
	print q.search('reddit:gonewild user:thatnakedgirl')
