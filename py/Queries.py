#!/usr/bin/python

from DB import DB

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
				conditions += ['UPPER(username) like UPPER(?)'] * len(filters['user'])
				search_values += filters['user']
			elif len(texts) > 0:
				conditions += ['UPPER(username) like UPPER(?)'] * len(texts)
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
			conditions_and.extend(['UPPER(username) like UPPER(?)'] * len(filters['user']))
			search_values.extend(filters['user'])
		else:
			conditions_or.extend(['UPPER(username) like UPPER(?)'] * len(texts))
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
			image_count = db.count('images', 'userid = ? and (type = \'image\' or type = \'album\')', [userid])
			video_count = db.count('images', 'userid = ? and type = \'video\'', [userid])
			
			users.append( {
				'user'    : username,
				'created' : created,
				'updated' : updated,
				'images'  : images,
				'post_n'  : post_count,
				'image_n' : image_count,
				'video_n' : video_count
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
					(select id from users where UPPER(username) = UPPER(?))
			order by %s %s
			limit  %d
			offset %d
		''' % (sortby, orderby, count, start)
		db = DB()
		cur = db.conn.cursor()
		execur = cur.execute(query, [user])
		posts = []
		for (postid, title, url, selftext, subreddit, created, permalink, ups, downs) in execur.fetchall():
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
			userid = db.select_one('id', 'users', 'UPPER(username) = UPPER(?)', [user])
			response['post_count']  = db.count('posts',  'userid = ?', [userid])
			response['image_count'] = db.count('images', 'userid = ? and (type = \'image\' or type = \'album\')', [userid])
			response['video_count'] = db.count('images', 'userid = ? and type =  \'video\'', [userid])
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
					(select id from users where UPPER(username) = UPPER(?))
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
			where = 'where UPPER(username) = UPPER(?)'
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

	@staticmethod
	def get_zip(user, include_videos=False, album=None):
		from os      import path, mkdir, walk, remove, sep as ossep
		from zipfile import ZipFile, ZIP_STORED
		db = DB()
		
		# Verify the user exists
		if not path.exists(path.join('content', user)):
			return {'error' : 'user dir "%s" not found' % user}
		source = path.join('content', user)
		if album != None:
			if not path.exists(path.join(source, album)):
				return {'error' : 'album dir "%s" not found' % album}
			source = path.join(source, album)
		if db.count('users', 'UPPER(username) like UPPER(?)', [user]) == 0:
			return {'error' : 'user "%s" not in db' % user}
		if not path.exists('zips'): mkdir('zips')

		zip_path = path.join('zips', user)
		if album != None: zip_path = '%s-%s' % (zip_path, album)
		if not include_videos:
			zip_path = '%s-novids' % zip_path
		zip_path = '%s.zip' % zip_path

		# Check for existing zip
		if path.exists(zip_path):
			zip_time = path.getmtime(zip_path)
			source_time = db.select_one('max(created)', 'posts', 'userid in (select id from users where UPPER(username) = UPPER(?))', [user])
			if album == None:
				q = 'user = ? and album is null'
				v = [user]
			else:
				q = 'user = ? and album = ?'
				v = [user, album]
			if zip_time > source_time and db.count('zips', q, v) > 0:
				# Zip is fresher than source album, don't need to re-zip
				(images, videos, audios) = db.select('images, videos, audios', 'zips', q, v)[0]
				return {
					'zip'    : zip_path,
					'size'   : path.getsize(zip_path),
					'images' : images,
					'videos' : videos,
					'audios' : audios
				}
			else:
				remove(zip_path) # Delete the stale zip
		
		# Create new zip
		zipped_file_ids = []
		images = videos = audios = 0
		z = ZipFile(zip_path, "w", ZIP_STORED)
		for root, dirs, files in walk(source):
			if root.endswith('/thumbs'): continue
			for fn in files:
				if not '.' in fn: continue # We need a file extension
				# Check for duplicates
				file_id = fn[fn.rfind('-')+1:]
				if file_id in zipped_file_ids: continue
				zipped_file_ids.append(file_id)
				# Count images/videos/audios
				ext = fn[fn.rfind('.')+1:].lower()
				if ext in ['mp4', 'flv', 'wmv']:
					if not include_videos: continue
					videos += 1
				elif ext in ['jpg', 'jpeg', 'png', 'gif']: images += 1
				elif ext in ['wma', 'm4v', 'mp3', 'wav']:  audios += 1
				absfn = path.join(root, fn) # content/user/
				source_minus_one = source[:source.rfind(ossep)]
				zipfn = absfn[len(source_minus_one):]
				z.write(absfn, zipfn)
		z.close()

		if images == 0 and videos == 0 and audios == 0:
			remove(zip_path)
			return {'error':'no images, videos, or audio files could be zipped'}

		zip_size = path.getsize(zip_path)
		# Update DB
		db.delete('zips', 'zippath = ?', [zip_path])
		db.insert('zips', (zip_path, user, album, images, videos, audios, zip_size))
		db.commit()
		return {
			'zip'    : zip_path,
			'size'   : zip_size,
			'images' : images,
			'videos' : videos,
			'audios' : audios
		}


	@staticmethod
	def get_rip(user):
		from DB import DB
		from os import walk, path, mkdir, remove
		from shutil import copy
		from subprocess import Popen, PIPE

		# Get proper user case
		db = DB()
		try:
			user = db.select_one('username', 'users', 'UPPER(username) like UPPER(?)', [user])
		except:
			user = None
		if user == None:
			return {'error':'user not found in database'}

		# Source of files
		source = path.join('content', user)
		if not path.exists(source):
			return {'error':'user not found at %s' % source}
		# Destination
		dest   = path.join('..', 'rip.rarchives.com', 'rips', 'gonewild_%s' % user)
		already_copied = []
		new_files = 0

		# Copy files
		for root, subdirs, files in walk(source):
			destsub = path.join(dest, root[len(source)+1:])
			if not path.exists(destsub):
				mkdir(destsub)

			for fil in files:
				# Avoid copying unnecessary files
				if '.' in fil and fil[fil.rfind('.')+1:] in ['log', 'txt', 'zip']: continue
				if not 'thumbs' in root:
					if   '_' in fil: imgid = fil[fil.rfind('_')+1:]
					elif '-' in fil: imgid = fil[fil.rfind('-')+1:]
					else: imgid = fil
					if imgid in already_copied:
						#Already copied file with this ID
						continue
					already_copied.append(imgid)

				fil = path.join(root, fil)
				saveas = path.join(dest, fil[len(source)+1:])
				if not path.exists(saveas):
					new_files += 1
					copy(fil, saveas)
					pass

		# Creat zip if needed
		savezip = '%s.zip' % dest
		if path.exists(savezip) and new_files > 0:
			remove(savezip)
		if new_files > 0:
			pid = Popen(['zip', '-r', '-0', savezip, source], stdout=PIPE) 
			(stdo, stde) = pid.communicate()

		return {
			'count' : len(already_copied),
			'url'   : 'http://rip.rarchives.com/rips/#gonewild_%s' % user,
			'zip'   : 'http://rip.rarchives.com/#gonewild:%s' % user,
			'new_files' : new_files
		}


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
	#print q.get_posts()
	#print q.get_zip('littlesugarbaby')
	print q.get_rip('LoveKitten69')
