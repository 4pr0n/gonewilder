#!/usr/bin/python
from ImageUtils import ImageUtils
import time
from os import path, listdir
from shutil import copy2
from sys import stderr
from Reddit import Comment, Post

try:                import sqlite3
except ImportError: import sqlite as sqlite3


SCHEMA = {
	'newusers' :
		'\n\t' +
		'username string unique \n\t',

	'users' :
		'\n\t' +
		'id        integer primary key autoincrement, \n\t' +
		'username  string unique, \n\t' +
		'sinceid   string,  \n\t' +
		'created   integer, \n\t' + 
		'updated   integer, \n\t' +
		'deleted   integer, \n\t' +
		'blacklist integer, \n\t' +
		'views     integer, \n\t' +
		'rating    integer, \n\t' +
		'ratings   integer  \n\t',

	'posts' :
		'\n\t' +
		'id        string primary key, \n\t' +
		'userid    integer, \n\t' +
		'title     string,  \n\t' +
		'url       string,  \n\t' +
		'subreddit string,  \n\t' +
		'over_18   integer, \n\t' +
		'created   integer, \n\t' +
		'legacy    integer, \n\t' +
		'permalink string,  \n\t' +
		'foreign key(userid) references users(id)',
	
	'comments' :
		'\n\t' +
		'id        string primary key, \n\t' +
		'userid    integer, \n\t' +
		'postid    string,  \n\t' +
		'subreddit string,  \n\t' +
		'text      string,  \n\t' +
		'created   integer, \n\t' +
		'legacy    integer, \n\t' +
		'permalink string,  \n\t' +
		'foreign key(userid) references users(id)',

	'albums' : 
		'\n\t'
		'id      integer primary key, \n\t' +
		'path    string unique, \n\t' +
		'userid  integer, \n\t' +
		'url     string,  \n\t' +
		'post    string,  \n\t' +
		'comment string,  \n\t' +
		'views   integer, \n\t' +
		'rating  integer, \n\t' +
		'ratings integer, \n\t' +
		'foreign key(userid) references users(id)',

	'images' :
		'\n\t' +
		'id      integer primary key, \n\t' +
		'path    string unique,  \n\t' +
		'userid  integer, \n\t' +
		'source  string,  \n\t' +
		'width   integer, \n\t' +
		'height  integer, \n\t' +
		'size    integer, \n\t' + 
		'thumb   string,  \n\t' +
		'type    string,  \n\t' + # image/video
		'albumid integer, \n\t' +
		'post    string,  \n\t' +
		'comment string,  \n\t' +
		'views   integer, \n\t' +
		'rating  integer, \n\t' +
		'ratings integer, \n\t' +
		'foreign key(userid) references users(id), \n\t' +
		'foreign key(albumid) references albums(id)\n\t',
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
		self.conn.commit()
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
			#self.conn.commit()
			last_row_id = cur.lastrowid
			cur.close()
			return last_row_id
		except sqlite3.IntegrityError:
			cur.close()
			return -1
	
	def get_cursor(self):
		return self.conn.cursor()
	
	def count(self, table, where):
		cur = self.conn.cursor()
		result = cur.execute('''select count(*) from %s where %s''' % (table, where, )).fetchall()
		cur.close()
		return result[0][0]
	
	def select(self, what, table, where=''):
		cur = self.conn.cursor()
		query_string = '''SELECT %s FROM %s''' % (what, table)
		if where != '':
			query_string += ''' WHERE %s''' % (where)
		cur.execute(query_string)
		results = []
		for result in cur:
			results.append(result)
		cur.close()
		return results
	
	def execute(self, statement):
		cur = self.conn.cursor()
		result = cur.execute(statement)
		#self.conn.commit()
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
		self.conn.commit()

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
			select max(sinceid)
				from users
				where username = "%s"
		''' % user)
		return results.fetchall()[0][0]

	def set_last_since_id(self, user, since_id):
		cur = self.conn.cursor()
		query = '''
			update users
				set sinceid = "%s"
				where username = "%s"
		''' % (since_id, user)
		cur.execute(query)
		self.conn.commit()
	
	def add_post(self, post, legacy=0):
		userid = self.get_user_id(post.author)
		q = 'insert into posts values ('
		q += '"%s",' % post.id
		q += ' %d ,' % userid
		q += '"%s",' % post.title
		q += '"%s",' % post.url
		q += '"%s",' % post.subreddit
		q += ' %d ,' % post.over_18  # comment id
		q += ' %d ,' % post.created
		q += ' %d ,' % legacy
		if legacy == 0 and post.subreddit != '':
			q += '"http://reddit.com/r/%s/comments/%s"' % (post.subreddit, post.id)
		else:
			q += '"http://reddit.com/comments/%s"' % post.id
		q += ')'
		cur = self.conn.cursor()
		try:
			result = cur.execute(q)
		except sqlite3.IntegrityError, e:
			# Column already exists
			raise Exception('post already exists in DB (%s): %s' % (post.id, str(e)))
		cur.close()
		self.conn.commit()

	def add_comment(self, comment, legacy=0):
		userid = self.get_user_id(comment.author)
		q = 'insert into comments values ('
		q += '"%s",' % comment.id
		q += ' %d ,' % userid
		q += '"%s",' % comment.post_id
		q += '"%s",' % comment.subreddit
		q += '"%s",' % comment.body
		q += ' %d ,' % comment.created
		q += ' %d ,' % legacy
		if legacy == 0 and comment.subreddit != '':
			q += '"http://reddit.com/r/%s/comments/%s/_/%s"' % (comment.subreddit, comment.post_id, comment.id)
		else:
			q += '"http://reddit.com/comments/%s/_/%s"' % (comment.post_id, comment.id)
		q += ')'
		cur = self.conn.cursor()
		try:
			result = cur.execute(q)
		except sqlite3.IntegrityError, e:
			# Column already exists
			raise Exception('comment already exists in DB (%s): %s' % (comment.id, str(e)))
		cur.close()
		self.conn.commit()

	def add_album(self, path, user, url, postid, commentid):
		userid = self.get_user_id(user)
		q = 'insert into albums values ('
		q += 'NULL,'  # albumid
		q += '"%s",'  % path
		q += ' %d ,'  % userid
		q += '"%s",'  % url
		q += '"%s",'  % postid
		q += 'NULL,' if commentid == None else '"%s",' % commentid
		q += '0,0,0)' # views, rating, ratings
		cur = self.conn.cursor()
		try:
			result = cur.execute(q)
		except sqlite3.IntegrityError, e:
			# Column already exists
			raise Exception('album already exists in DB (%s): %s' % (path, str(e)))
		lastrow = cur.lastrowid
		cur.close()
		self.conn.commit()
		return lastrow

	def add_image(self, path, user, url, width, height, size, thumb,
	                    mediatype, albumid, postid, commentid):
		userid = self.get_user_id(user)
		q = 'insert into images values ('
		q += 'NULL,'  # imageid
		q += '"%s",'  % path
		q += ' %d ,'  % userid
		q += '"%s",'  % url
		q += ' %d ,'  % width
		q += ' %d ,'  % height
		q += ' %d ,'  % size
		q += '"%s",'  % thumb
		q += '"%s",'  % mediatype
		q += 'NULL,' if albumid   == None else '"%s",' % albumid
		q += '"%s",'  % postid
		q += 'NULL,' if commentid == None else '"%s",' % commentid
		q += '0,0,0)' # views, rating, ratings
		cur = self.conn.cursor()
		try:
			result = cur.execute(q)
		except sqlite3.IntegrityError, e:
			# Column already exists
			raise Exception('image already exists in DB (%s): %s' % (path, str(e)))
		lastrow = cur.lastrowid
		cur.close()
		self.conn.commit()
		return lastrow

	'''
		Get list of users.
		If "new" is flagged:
			* Deletes list of 'newusers'
			* Adds 'newusers' to 'users' list.
			* Returns list of 'newusers'
	'''
	def get_users(self, new=False):
		q = 'select username from %susers' % ('new' if new else '')
		cur = self.conn.cursor()
		users = cur.execute(q).fetchall()
		if new:
			# Delete list of new users, add to new users list
			for user in [x[0] for x in users]:
				delq = 'delete from newusers where username = "%s"' % user
				cur.execute(delq)
				try: self.add_user(user, new=False)
				except: pass
			cur.close()
			self.conn.commit()
		else:
			cur.close()
		return [x[0] for x in users]

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
			self.debug('cannot properly handle tumblr links')
			return
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
			self.debug('image already exists: %s' % newimage)
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
			self.debug('add_existing_album: error adding album: %s' % str(e))
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


if __name__ == '__main__':
	db = DB()
	try: db.add_user('4_pr0n')
	except: pass
	db.set_last_since_id('4_pr0n', 'ccs4ule')
	print db.get_last_since_id('4_pr0n')
