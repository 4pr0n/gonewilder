#!/usr/bin/python
from ImageUtils import ImageUtils
import time
from os import path, listdir, getcwd, sep

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
		'views     integer, \n\t' +
		'rating    integer, \n\t' +
		'ratings   integer, \n\t' +
		'blacklist integer  \n\t',

	'posts' :
		'\n\t' +
		'id        string primary key, \n\t' +
		'userid    integer, \n\t' +
		'title     string,  \n\t' +
		'url       string,  \n\t' +
		'subreddit string,  \n\t' +
		'over_18   integer, \n\t' +
		'created   integer, \n\t' +
		'foreign key(userid) references users(id)',
	
	'comments' :
		'\n\t' +
		'id        string primary key, \n\t' +
		'userid    integer, \n\t' +
		'postid    string,  \n\t' +
		'subreddit string,  \n\t' +
		'text      string,  \n\t' +
		'created   integer, \n\t' +
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

cwd = getcwd()
if cwd.endswith('py'):
	cwd = cwd[:cwd.rfind(sep)]

DB_FILE = '%sdatabase.db' % cwd

class DB:
	def __init__(self):
		self.conn = None
		self.conn = sqlite3.connect(DB_FILE) #TODO CHANGE BACK, encoding='utf-8')
		self.conn.text_factory = lambda x: unicode(x, "utf-8", "ignore")
		# Don't create tables if not supplied.
		if SCHEMA != None and SCHEMA != {} and len(SCHEMA) > 0:
			# Create table for every schema given.
			for key in SCHEMA:
				self.create_table(key, SCHEMA[key])
	
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
		cur.execute('insert into %susers values (NULL, "%s", "", %d, %d, 0, 0, 0, 0, 0)' % ('new' if new else '', user, int(time.time()), int(time.time())))
		self.conn.commit()

	''' Finds user ID for username; creates new user if not found '''
	def get_user_id(self, user):
		cur = self.conn.cursor()
		results = cur.execute('select id from users where username like "%s"' % user)
		users = results.fetchall()
		if len(users) == 0:
			self.add_user(user, new=False)
			results = cur.execute('select id from users where username like "%s"' % user)
			users = results.fetchall()
		cur.close()
		return users[0][0]

	def album_exists(self, user, albumdir):
		cur = self.conn.cursor()
		results = cur.execute('select * from albums where path = "%s"' % albumdir)
		return len(results.fetchall()) > 0

	def image_exists(self, user, imagedir):
		cur = self.conn.cursor()
		results = cur.execute('select * from images where path = "%s"' % imagedir)
		return len(results.fetchall()) > 0

	''' True if user has been added to 'users' or 'newusers', False otherwise '''
	def user_already_added(self, user):
		cur = self.conn.cursor()
		results = cur.execute('select * from users where username like "%s"' % user)
		if len(results.fetchall()) > 0:
			return True
		results = cur.execute('select * from newusers where username like "%s"' % user)
		if len(results.fetchall()) > 0:
			return True
		return False

	def get_last_since_id(self, user):
		cur = self.conn.cursor()
		results = cur.execute('select max(sinceid) from users where username like "%s"' % user)
		return results.fetchall()[0][0]

	def set_last_since_id(self, user, since_id):
		cur = self.conn.cursor()
		cur.execute('''
			update users
				set sinceid = "%s"
				where username like "%s"
		''' % (since_id, user))
		self.conn.commit()
	
	def add_post(self, post):
		userid = self.get_user_id(post.author)
		q = 'insert into posts values ('
		q += '"%s",' % post.id
		q += '%d,'   % userid
		q += '"%s",' % post.title
		q += '"%s",' % post.url
		q += '"%s",' % post.subreddit
		q += '%d,'   % post.over_18  # comment id
		q += '%d'    % post.created
		q += ')'
		cur = self.conn.cursor()
		try:
			result = cur.execute(q)
		except sqlite3.IntegrityError, e:
			# Column already exists
			raise Exception('post already exists in DB (%s): %s' % (post.id, str(e)))
		cur.close()
		self.conn.commit()

	def add_comment(self, comment):
		userid = self.get_user_id(comment.author)
		q = 'insert into comments values ('
		q += '"%s",' % comment.id
		q += '%d,'   % userid
		q += '"%s",' % comment.post_id
		q += '"%s",' % comment.subreddit
		q += '"%s",' % comment.body
		q += '%d'    % comment.created
		q += ')'
		cur = self.conn.cursor()
		try:
			result = cur.execute(q)
		except sqlite3.IntegrityError, e:
			# Column already exists
			raise Exception('comment already exists in DB (%s): %s' % (comment.id, str(e)))
		cur.close()
		self.conn.commit()



	########################
	# STUPID EXTRA FUNCTIONS
	def get_image_type(self, url):
		if url.lower().endswith('.mp4') or url.lower().endswith('.flv'):
			return 'video'
		return 'image'

	def get_post_comment_id(self, pci):
		if not '_' in pci: return ('', '', '')
		(pc, i) = pci.split('_')
		if '-' in pc:
			(post, comment) = pc.split('-')
		else:
			post = pc
			comment = ''
		return (post, comment, i)

	def add_image(self, user, image):
		(post, comment, imgid) = self.get_post_comment_id(image)
		imagedir = path.join('users', user, image)
		if self.image_exists(imagedir):
			raise Exception('image already exists in DB: %s' % imagedir)
		userid   = self.get_user_id(user)
		url      = 'http://i.imgur.com/%s' % imgid
		dims     = ImageUtils.dimensions(imagedir)
		size     = path.getsize(imagedir)
		thumb    = imagedir.replace('/users/', '/thumbs/')
		ImageUtils.create_thumbnail(imagedir, thumb)
		q = 'insert into images values ('
		q += 'NULL,'            # imageid
		q += '"%s",' % imagedir # image path
		q += '%d,'   % userid   # user
		q += '"%s",' % url      # source (url)
		q += '%d,'   % dims[0]  # width
		q += '%d,'   % dims[1]  # height
		q += '%d,'   % size     # file size
		q += '"%s",' % thumb    # thumbnail path
		q += '"%s",' % get_image_type(imagedir) # imagetype
		q += '-1,'              # album id
		q += '"%s",' % post     # post id
		q += '"%s",' % comment  # comment id
		q += '0,0,0)'           # views, rating, ratings
		cur = self.conn.cursor()
		try:
			result = cur.execute(q)
		except sqlite3.IntegrityError, e:
			# Column already exists
			raise Exception('path to image already exists in DB (%s): %s' % (imagedir, str(e)))
		cur.close()
		self.conn.commit()

	def add_album(self, user, album):
		(post, comment, imgid) = self.get_post_comment_id(album)
		albumdir = path.join('users', user, album)
		if self.album_exists(user, album):
			raise Exception('album already exists in DB: %s' % albumdir)
		userid   = self.get_user_id(user)
		url      = 'http://imgur.com/a/%s' % imgid
		q = 'insert into albums values ('
		q += 'NULL,'            # albumid
		q += '"%s",' % albumdir # album path
		q += '%d,'   % userid   # user
		q += '"%s",' % url      # source (url)
		q += '"%s",' % post     # post id
		q += '"%s",' % comment  # comment id
		q += '0,0,0)'           # views, rating, ratings
		cur = self.conn.cursor()
		try:
			result = cur.execute(q)
		except sqlite3.IntegrityError, e:
			# Column already exists
			raise Exception('path to album already exists in DB (%s): %s' % (albumdir, str(e)))
		cur.close()
		self.conn.commit()
		pass


if __name__ == '__main__':
	db = DB()
	#db.add_user('4_pr0n')
	#print db.get_last_since_id('4_pr0n')
	print db.set_last_since_id('4_pr0n', 'ccs4ule')
