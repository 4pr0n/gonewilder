#!/usr/bin/python
import time
from os import path, listdir
from sys import stderr
from shutil import copy2
from Reddit import Comment, Post
from ImageUtils import ImageUtils

try:                import sqlite3
except ImportError: import sqlite as sqlite3

SCHEMA = {
	'newusers' :
		'\n\t' +
		'username text unique \n\t',

	'users' :
		'\n\t' +
		'id        integer primary key autoincrement, \n\t' +
		'username  text unique, \n\t' +
		'sinceid   text,    \n\t' +
		'created   integer, \n\t' + 
		'updated   integer, \n\t' +
		'deleted   integer, \n\t' +
		'blacklist integer, \n\t' +
		'views     integer, \n\t' +
		'rating    integer, \n\t' +
		'ratings   integer  \n\t',

	'posts' :
		'\n\t' +
		'id        text primary key, \n\t' +
		'userid    integer, \n\t' +
		'title     text,    \n\t' +
		'url       text,    \n\t' +
		'selftext  text,    \n\t' +
		'subreddit text,    \n\t' +
		'over_18   integer, \n\t' +
		'created   integer, \n\t' +
		'legacy    integer, \n\t' +
		'permalink text,    \n\t' +
		'ups       integer, \n\t' +
		'downs     integer, \n\t' +
		'foreign key(userid) references users(id)\n\t',

	'comments' :
		'\n\t' +
		'id        text primary key, \n\t' +
		'userid    integer, \n\t' +
		'postid    text,    \n\t' +
		'subreddit text,    \n\t' +
		'text      text,    \n\t' +
		'created   integer, \n\t' +
		'legacy    integer, \n\t' +
		'permalink text,    \n\t' +
		'ups       integer, \n\t' +
		'downs     integer, \n\t' +
		'foreign key(userid) references users(id)\n\t',

	'albums' : 
		'\n\t'
		'id      integer primary key, \n\t' +
		'path    text unique, \n\t' +
		'userid  integer,     \n\t' +
		'url     text,    \n\t' +
		'post    text,    \n\t' +
		'comment text,    \n\t' +
		'views   integer, \n\t' +
		'foreign key(userid) references users(id)\n\t',

	'images' :
		'\n\t' +
		'id      integer primary key, \n\t' +
		'path    text unique,  \n\t' +
		'userid  integer, \n\t' +
		'source  text,    \n\t' +
		'width   integer, \n\t' +
		'height  integer, \n\t' +
		'size    integer, \n\t' + 
		'thumb   text,    \n\t' +
		'type    text,    \n\t' + # image/video
		'albumid integer, \n\t' +
		'post    text,    \n\t' +
		'comment text,    \n\t' +
		'views   integer, \n\t' +
		'foreign key(userid) references users(id), \n\t' +
		'foreign key(albumid) references albums(id)\n\t',
	
	'zips' :
		'\n\t' +
		'zippath text unique, \n\t' +
		'user   text,    \n\t' +
		'album  text,    \n\t' +
		'images integer, \n\t' +
		'videos integer, \n\t' +
		'audios integer, \n\t' +
		'size   integer \n\t',

	'credentials' :
		'\n\t' +
		'site     text primary key, \n\t' +
		'username text, \n\t' +
		'password text  \n\t',

	'config' :
		'\n\t' +
		'key text primary key, \n\t' +
		'value text  \n\t',

	'friends' :
		'\n\t' +
		'username text primary key\n\t',
}

DB_FILE = path.join(ImageUtils.get_root(), 'database.db')

class DB:
	def __init__(self):
		self.logger = stderr
		if path.exists(DB_FILE):
			self.debug('__init__: using database file: %s' % DB_FILE)
		else:
			self.debug('__init__: database file (%s) not found, creating...' % DB_FILE)
		self.conn = None
		self.conn = sqlite3.connect(DB_FILE) #TODO CHANGE BACK, encoding='utf-8')
		self.conn.text_factory = lambda x: unicode(x, "utf-8", "ignore")
		# Don't create tables if not supplied.
		if SCHEMA != None and SCHEMA != {} and len(SCHEMA) > 0:
			# Create table for every schema given.
			for key in SCHEMA:
				self.create_table(key, SCHEMA[key])
	
	def debug(self, text):
		tstamp = time.strftime('[%Y-%m-%dT%H:%M:%SZ]', time.gmtime())
		text = '%s DB: %s' % (tstamp, text)
		self.logger.write('%s\n' % text)
		if self.logger != stderr:
			stderr.write('%s\n' % text)
	
	def create_table(self, table_name, schema):
		cur = self.conn.cursor()
		query = '''create table if not exists %s (%s)''' % (table_name, schema)
		cur.execute(query)
		self.commit()
		cur.close()
	
	def commit(self):
		try_again = True
		while try_again:
			try:
				self.conn.commit()
				try_again = False
			except:
				time.sleep(1)
	
	def insert(self, table, values):
		cur = self.conn.cursor()
		try:
			questions = ''
			for i in xrange(0, len(values)):
				if questions != '': questions += ','
				questions += '?'
			exec_string = '''insert into %s values (%s)''' % (table, questions)
			result = cur.execute(exec_string, values)
			last_row_id = cur.lastrowid
			cur.close()
			return last_row_id
		except sqlite3.IntegrityError:
			cur.close()
			return -1
	
	def delete(self, table, where, values=[]):
		cur = self.conn.cursor()
		q = '''
			delete from %s
				where %s
		''' % (table, where)
		cur.execute(q, values)
	
	def get_cursor(self):
		return self.conn.cursor()
	
	def count(self, table, where='', values=[]):
		return self.select_one('count(*)', table, where, values=values)
	
	def select(self, what, table, where='', values=[]):
		cur = self.conn.cursor()
		query = '''
			select %s
				from %s
		''' % (what, table)
		if where != '':
			query += 'where %s' % (where)
		cur.execute(query, values)
		results = []
		for result in cur:
			results.append(result)
		cur.close()
		return results

	def select_one(self, what, table, where='', values=[]):
		cur = self.conn.cursor()
		if where != '':
			where = 'where %s' % where
		query = '''
			select %s
				from %s
				%s
		''' % (what, table, where)
		execur = cur.execute(query, values)
		one = execur.fetchone()
		cur.close()
		return one[0]
	
	def update(self, table, what, where='', values=[]):
		cur = self.conn.cursor()
		if where != '':
			where = 'where %s' % where
		query = '''
			update %s
				set %s
				%s
		''' % (table, what, where)
		execur = cur.execute(query, values)
		one = execur.fetchone()
		cur.close()

	def execute(self, statement):
		cur = self.conn.cursor()
		result = cur.execute(statement)
		return result

	#####################
	# GW-specific methods

	''' Add user to list of either 'users' or 'newusers' table '''
	def add_user(self, user, new=False):
		cur = self.conn.cursor()
		if new:
			q = '''
				insert into newusers values ("%s")
			''' % user
		else:
			now = int(time.time())
			q = 'insert into users values ('
			q += 'NULL,'         # user id
			q += '"%s",' % user  # username
			q += ' "" ,'         # since id
			q += ' %d ,' % now   # created
			q += ' %d ,' % now   # updated
			q += '  0 ,'         # deleted
			q += '  0 ,'         # blacklisted
			q += '0,0,0)'        # views, rating, ratings
		try:
			cur.execute(q)
		except sqlite3.IntegrityError, e:
			self.debug('add_user: user "%s" already exists in %susers: %s' % (user, 'new' if new else '', str(e)))
			raise e
		self.commit()

	''' Finds user ID for username; creates new user if not found '''
	def get_user_id(self, user):
		cur = self.conn.cursor()
		results = cur.execute('''
			select id
				from users
				where username like "%s"
		''' % user)
		users = results.fetchall()
		if len(users) == 0:
			self.add_user(user, new=False)
			results = cur.execute('''
				select id
					from users
					where username like "%s"
			''' % user)
			users = results.fetchall()
		cur.close()
		return users[0][0]

	''' True if user has been added to 'users' or 'newusers', False otherwise '''
	def user_already_added(self, user):
		cur = self.conn.cursor()
		results = cur.execute('''
			select *
				from users
				where username like "%s"
		''' % user)
		if len(results.fetchall()) > 0:
			return True
		results = cur.execute('''
			select *
				from newusers
				where username like "%s"
		''' % user)
		return len(results.fetchall()) > 0

	def get_last_since_id(self, user):
		cur = self.conn.cursor()
		results = cur.execute('''
			select sinceid
				from users
				where username like "%s"
		''' % user)
		return results.fetchall()[0][0]

	def set_last_since_id(self, user, since_id):
		cur = self.conn.cursor()
		query = '''
			update users
				set sinceid = "%s"
				where username like "%s"
		''' % (since_id, user)
		cur.execute(query)
		self.commit()
	
	def add_post(self, post, legacy=0):
		userid = self.get_user_id(post.author)
		values = [ (
				post.id,         # reddit post id
				userid,          # id of user in 'users' table
				post.title,      # title of reddit post
				post.selftext,   # selftext
				post.url,        # reddit post url
				post.subreddit,  # subreddit
				post.over_18,    # NSFW
				post.created,    # UTC timestamp
				legacy,          # If post was generated (legacy) or retrieved in-full from reddit
				post.permalink(),# link to post on reddit,
				post.ups,        # upvotes
				post.downs       # downvotes
			) ]
		q = 'insert into posts values (%s)' % ','.join(['?'] * len(values[0]))
		cur = self.conn.cursor()
		try:
			result = cur.executemany(q, values)
		except sqlite3.IntegrityError, e: # Column already exists
			raise Exception('post already exists in DB (%s): %s' % (post.id, str(e)))
		cur.close()
		self.commit()

	def add_comment(self, comment, legacy=0):
		userid = self.get_user_id(comment.author)
		values = [ (
				comment.id,         # reddit comment id
				userid,             # id of user in 'users' table
				comment.post_id,    # reddit post id
				comment.subreddit,  # subreddit
				comment.body,       # body of comment
				comment.created,    # utc timestamp
				legacy,             # if comment was 'generated' (legacy) or retrieved from reddit
				comment.permalink(),# link to comment
				comment.ups,        # upvotes
				comment.downs       # downvotes
			) ]
		q = 'insert into comments values (%s)' % ','.join(['?'] * len(values[0]))
		cur = self.conn.cursor()
		try:
			result = cur.executemany(q, values)
		except sqlite3.IntegrityError, e: # Column already exists
			raise Exception('comment already exists in DB (%s): %s' % (comment.id, str(e)))
		cur.close()
		self.commit()

	def add_album(self, path, user, url, postid, commentid):
		userid = self.get_user_id(user)
		values = [ (
				None,      # albumid
				path,      # path to album (filesystem)
				userid,    # if of user in 'users' table
				url,       # url to album
				postid,    # reddit post id
				commentid, # reddit comment id
				0          # views
			) ]
		q = 'insert into albums values (%s)' % ','.join(['?'] * len(values[0]))
		cur = self.conn.cursor()
		try:
			result = cur.executemany(q, values)
		except sqlite3.IntegrityError, e: # Column already exists
			raise Exception('album already exists in DB (%s): %s' % (path, str(e)))
		lastrow = cur.lastrowid
		cur.close()
		self.commit()
		return lastrow

	def album_exists(self, album_url):
		return self.count('albums', 'url = ?', [album_url])

	'''
		Add an "image" to the database. Might be a video
	'''
	def add_image(self, path, user, url, width, height, size, thumb,
	                    mediatype, albumid, postid, commentid):
		userid = self.get_user_id(user)
		values = [ (
				None,      # imageid
				path,      # path to image (locally)
				userid,    # id of user in 'users' table
				url,       # image source
				width,     # image width
				height,    # image height
				size,      # size of image (in bytes)
				thumb,     # path to thumbnail (locally)
				mediatype, # 'image' or 'video'
				albumid,   # album in which the image is contained
				postid,    # reddit post
				commentid, # reddit comment
				0          # views
			) ]
		q = 'insert into images values (%s)' % ','.join(['?'] * len(values[0]))
		cur = self.conn.cursor()
		try:
			result = cur.executemany(q, values)
		except sqlite3.IntegrityError, e: # Column already exists
			raise Exception('image already exists in DB (%s): %s' % (path, str(e)))
		lastrow = cur.lastrowid
		cur.close()
		self.commit()
		return lastrow

	'''
		Get list of (non-deleted) users.
		If "new" is flagged:
			* Deletes list of 'newusers'
			* Adds 'newusers' to 'users' list.
			* Returns list of 'newusers'
	'''
	def get_users(self, new=False):
		if new: q = 'select username from newusers'
		else:   q = 'select username from users where deleted = 0'
		cur = self.conn.cursor()
		users = cur.execute(q).fetchall()
		if new:
			# Delete list of new users, add to new users list
			for user in [x[0] for x in users]:
				delq = 'delete from newusers where username like "%s"' % user
				cur.execute(delq)
				try: self.add_user(user, new=False)
				except: pass
			cur.close()
			self.commit()
		else:
			cur.close()
		return [str(x[0]) for x in users]

	########################
	# STUPID EXTRA FUNCTIONS

	def get_post_comment_id(self, pci):
		if not '_' in pci:
			raise Exception('unable to find post/comment/imgid from filename %s' % pci)
		(pc, i) = pci.split('_')
		if '-' in pc:
			(post, comment) = pc.split('-')
		else:
			post = pc
			comment = None
		return (post, comment, i)

	'''
		Copy old image (/users/<user>/...) to new format (/content/<user>/...)
		Create new thumbnail
		Derive values for post/comment from filename
	'''
	def add_existing_image(self, user, oldimage, oldpath, subdir='', album_id=-1):
		if 'tumblr' in oldpath:
			# Can't properly handle tumblr links
			self.debug('cannot properly handle tumblr links; trying anyway')
			#return
		if subdir == '' and album_id == -1:
			self.debug('adding image: %s' % oldpath)
		# Ensure image is an actual image
		try:
			dims = ImageUtils.get_dimensions(oldpath)
		except:
			self.debug('failed to load image: %s, skipping' % oldpath)
			return
		newimage  = path.join(ImageUtils.get_root(), 'content', user, subdir, oldimage)
		newimage = newimage.replace('.jpeg.jpg', '.jpg')
		thumbnail = path.join(ImageUtils.get_root(), 'content', user, subdir, 'thumbs', oldimage)
		thumbnail = thumbnail.replace('.jpeg.jpg', '.jpg')
		if path.exists(newimage):
			self.debug('new image already exists: %s' % newimage)
			return

		ImageUtils.create_subdirectories(path.join(ImageUtils.get_root(), 'content', user, subdir, 'thumbs'))

		copy2(oldpath, newimage)
		try:
			ImageUtils.create_thumbnail(newimage, thumbnail)
		except Exception, e:
			self.debug('failed to create thumbnail: %s' % str(e))
			thumbnail = path.join(ImageUtils.get_root(), 'images', 'nothumb.png')

		(post, comment, imgid) = self.get_post_comment_id(oldimage)
		url  = 'http://i.imgur.com/%s' % imgid
		dims = ImageUtils.get_dimensions(newimage)
		size = path.getsize(newimage)
		try:
			ImageUtils.create_thumbnail(newimage, thumbnail)
		except Exception, e:
			self.debug('add_existing_image: create_thumbnail failed: %s' % str(e))
			thumbnail = path.join(ImageUtils.get_root(), 'images', 'nothumb.png')
		try:
			self.add_image(newimage, user, url, 
					dims[0], dims[1], size, thumbnail, 'image', 
					album_id, post, comment)
		except Exception, e:
			self.debug('add_existing_image: failed: %s' % str(e))
			return

		if subdir == '' and album_id == -1: # Not an album
			# Add post
			p = Post()
			p.id = post
			p.author = user
			if comment == None: p.url = url
			p.created = path.getctime(oldpath)
			p.subreddit = ''
			p.title = ''
			try:
				self.add_post(p, legacy=1)
			except Exception, e:
				self.debug('add_existing_image: create post failed: %s' % str(e))

			# Add comment
			if comment != None:
				c = Comment()
				c.id = comment
				c.post_id = post
				c.author = user
				if comment != None: c.body = url
				p.created = path.getctime(oldpath)
				try:
					self.add_comment(c, legacy=1)
				except Exception, e:
					self.debug('add_existing_image: create comment failed: %s' % str(e))

	def add_existing_album(self, user, oldalbum, oldpath):
		newalbum = path.join(ImageUtils.get_root(), 'content', user, oldalbum)
		if path.exists(newalbum):
			self.debug('album already exists: %s' % newalbum)
			return

		(post, comment, imgid) = self.get_post_comment_id(oldalbum)
		url = 'http://imgur.com/a/%s' % imgid
		try:
			album_id = self.add_album(newalbum, user, url, post, comment)
		except Exception, e:
			self.debug('add_existing_album: failed: %s' % str(e))
			return

		for image in listdir(oldpath):
			self.debug('add_existing_album: image=%s' % path.join(oldpath, image))
			fakeimage = post
			if comment != None:
				fakeimage = '%s-%s' % (fakeimage, comment)
			fakeimage = '%s_%s' % (fakeimage, image.split('_')[-1])
			self.add_existing_image(user, fakeimage, path.join(oldpath, image), subdir=oldalbum, album_id=album_id)

			# Add post
			p = Post()
			p.id = post
			p.author = user
			if comment == None: p.url = url
			p.created = path.getctime(oldpath)
			p.subreddit = ''
			p.title = ''
			try:
				self.add_post(p, legacy=1)
			except Exception, e:
				#self.debug('add_existing_image: %s' % str(e))
				pass

			# Add comment
			if comment != None:
				c = Comment()
				c.id = comment
				c.post_id = post
				c.author = user
				if comment != None: c.body = url
				p.created = path.getctime(oldpath)
				try:
					self.add_comment(c, legacy=1)
				except Exception, e:
					#self.debug('add_existing_image: %s' % str(e))
					pass
	
	def get_credentials(self, site):
		if self.count('credentials', 'site = ?', [site]) == 0:
			raise Exception('Credentials for %s not found in database, run "Gonewild.py --help" for more info' % site)

		q = 'select username,password from credentials where site = "%s"' % site
		cur = self.conn.cursor()
		(username, password) = cur.execute(q).fetchone()
		cur.close()
		return (username, password)

	def set_credentials(self, site, username, password):
		cur = self.conn.cursor()
		try:
			q = 'insert into credentials values (?,?,?)'
			cur.execute(q, [site, username, password])
			cur.close()
			self.commit()
		except Exception, e:
			#self.debug('[!] unable to add new credentials: %s' % str(e))
			q = 'update credentials set username = ?, password = ? where site = ?'
			try:
				result = cur.execute(q, [username, password, site])
				cur.close()
				self.commit()
			except Exception, e:
				self.debug('[!] unable to update existing credentials: %s' % str(e))
				from traceback import format_exc
				self.debug('\n%s' % format_exc())
				raise e
		
	def update_user(self, user):
		cur = self.conn.cursor()
		query = '''
			update users
				set updated = %d
				where username like ?
		''' % int(time.time())
		cur.execute(query, [user])
		self.commit()

	def get_excluded_subreddits(self):
		csv_subs = self.get_config('excluded_subreddits')
		if csv_subs == None or csv_subs.strip() == '':
			return []
		return csv_subs.split(',')

	def add_excluded_subreddit(self, subreddit):
		subs = self.get_excluded_subreddits()
		if subreddit.strip().lower() in subs:
			raise Exception('subreddit "%s" already exists in list of excluded subreddits: %s' % (subreddit.strip().lower(), str(subs)))
		subs.append(subreddit.strip().lower())
		self.set_config('excluded_subreddits', ','.join(subs))

	def remove_excluded_subreddit(self, subreddit):
		subs = self.get_excluded_subreddits()
		if not subreddit.strip().lower() in subs:
			raise Exception('subreddit "%s" not found in list of excluded subreddits: %s' % (subreddit.strip().lower(), str(subs)))
		subs.remove(subreddit.strip().lower())
		self.set_config('excluded_subreddits', ','.join(subs))

	def mark_as_deleted(self, user):
		cur = self.conn.cursor()
		query = '''
			update users
				set deleted = 1
				where username like "%s"
		''' % (user)
		cur.execute(query)
		self.commit()

	def already_friend(self, user):
		return self.count('friends', 'username = ?', [user]) > 0
	
	def add_friend(self, user):
		cur = self.conn.cursor()
		cur.execute('insert into friends values (?)', [user])
		self.commit()

	def remove_friend(self, user):
		self.delete('friends', 'username like ?', [user])
		self.commit()

	def get_friends_list(self):
		result = []
		for friend in self.select('username', 'friends'):
			result.append(friend[0])
		return result

	def get_users_list(self):
		result = []
		for user in self.select('username', 'users'):
			result.append(user[0])
		for user in self.select('username', 'newusers'):
			result.append(user[0])
		return result

	def get_config(self, key, default=None):
		cur = self.conn.cursor()
		query = '''
			select value
				from config
				where key = "%s"
		''' % key
		try:
			execur = cur.execute(query)
			result = execur.fetchone()[0]
			cur.close()
		except Exception, e:
			return default
		return result

	def set_config(self, key, value):
		cur = self.conn.cursor()
		query = '''
			insert or replace into config (key, value)
				values ("%s", "%s")
		''' % (key, value)
		try:
			execur = cur.execute(query)
			result = execur.fetchone()
			self.commit()
			cur.close()
		except Exception, e:
			self.debug('failed to set config key "%s" to value "%s": %s' % (key, value, str(e)))
		

if __name__ == '__main__':
	db = DB()
	try: db.add_user('4_pr0n')
	except: pass
	db.set_last_since_id('4_pr0n', 'ccs4ule')
	print db.get_last_since_id('4_pr0n')
