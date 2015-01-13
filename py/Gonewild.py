#!/usr/bin/python

from DB         import DB
from os         import path, mkdir, devnull
from sys        import stderr
from Reddit     import Reddit, Child, Post, Comment
from ImageUtils import ImageUtils
from time       import strftime, gmtime

'''
	Brings everything together:
	 * Retrieves gonewild posts and content,
	 * Adds results to database
'''
class Gonewild(object):

	def __init__(self):
		# Single file that all output is written to, to track usage
		self.exit_if_already_started()
		self.db = DB() # Database instance

		log_level = self.db.get_config('log_level', default='user')
		if log_level == 'none':
			self.root_log = open(devnull, 'w')
		else:
			self.root_log = open(path.join(ImageUtils.get_root(), 'history.log'), 'a')
		self.logger   = self.root_log # Logger used by helper classes

		self.reddit   = Reddit()
		self.excluded_subs = self.db.get_excluded_subreddits()
		
	def debug(self, text):
		tstamp = strftime('[%Y-%m-%dT%H:%M:%SZ]', gmtime())
		text = '%s Gonewild: %s' % (tstamp, text)
		self.root_log.write('%s\n' % text)
		if self.logger != self.root_log:
			self.logger.write('%s\n' % text)
		stderr.write('%s\n' % text)

	def user_already_added(self, user):
		return self.db.user_already_added(user)

	def user_has_gone_wild(self, user):
		# Look at last 100 submissions
		try:
			children = self.reddit.get_user('%s/submitted' % user, max_pages=1)
		except Exception:
			# User is 404
			return False
		for child in children:
			if type(child) == Post:
				if 'gonewild'   in child.subreddit.lower() or \
				   'gw'         in child.subreddit.lower() or \
				   'asstastic'  in child.subreddit.lower() or \
				   'girlsgone'  in child.subreddit.lower() or \
				   'gone'       in child.subreddit.lower():
					return True
		return False

	def add_excluded_subreddit(self, subreddit):
		return self.db.add_excluded_subreddit(subreddit)

	def setup_loggers_for_user(self, user):
		# Create directories if needed
		user_dir = path.join(ImageUtils.get_root(), 'content', user)
		ImageUtils.create_subdirectories(user_dir)
		# Setup logger
		log_level = self.db.get_config('log_level', default='user')
		if   log_level == 'none':   self.logger = open(devnull, 'w')
		elif log_level == 'user':   self.logger = open(path.join(user_dir, 'history.log'), 'a')
		elif log_level == 'global': self.logger = self.root_log
		self.db.logger     = self.logger
		ImageUtils.logger  = self.logger
		self.reddit.logger = self.logger

	def restore_loggers(self):
		log_level = self.db.get_config('log_level', default='user')
		if log_level == 'user':
			self.logger.close()
			self.logger = self.root_log
			self.db.logger     = self.logger
			ImageUtils.logger  = self.logger
			self.reddit.logger = self.logger

	def is_excluded_child(self, child):
		if child.subreddit.lower() in [x.lower() for x in self.excluded_subs]:
			self.debug('''%s: poll_user: Ignoring post/comment in excluded subreddit ("%s")
  Permalink: %s
    Ignored: %s''' % (child.author, child.subreddit, child.permalink(), str(child)))
			return True
		return False

	def get_and_process_urls_from_child(self, child):
		urls = self.get_urls(child)
		try:
			if type(child) == Post:
				self.db.add_post(child)
			elif type(child) == Comment:
				self.db.add_comment(child)
		except Exception, e:
			if 'already exists' not in str(e):
				self.debug('%s: poll_user: %s' % (child.author, str(e)))
			return # If we can't add the post/comment to DB, skip it
		if len(urls) > 0:
			self.debug('%s: poll_user: found %d url(s) in child %s' % (child.author, len(urls), child.permalink()))
			for url_index, url in enumerate(urls):
				self.process_url(url, url_index, child)

	def poll_user(self, user):
		'''
			Gets new posts/comments for user,
			Finds URLs in posts/comments,
			"Processes" (downloads) URLs,
			Adds results to database.
		'''
		self.setup_loggers_for_user(user)

		since_id = self.db.get_last_since_id(user)
		# Get posts/comments for user
		self.debug('%s: poll_user: since "%s"' % (user, since_id))
		try:
			children = self.reddit.get_user(user, since=since_id)
		except Exception, e:
			if '404: Not Found' in str(e):
				# User is deleted, mark it as such
				self.debug('%s: poll_user: user is 404, marking as deleted' % user)
				self.db.mark_as_deleted(user)
				return
			self.debug('%s: poll_user: error %s' % (user, str(e)))
			return

		if len(children) == 0:
			#self.debug('%s: poll_user: no new posts/comments found' % user)
			return

		self.debug('%s: poll_user: %d new posts and comments found' % (user, len(children)))

		for child in children:
			# Ignore certain subreddits
			if self.is_excluded_child(child):
				continue

			self.get_and_process_urls_from_child(child)
			
		self.debug('%s: poll_user: done' % user)

		# Set last 'since' to the most-recent post/comment ID
		self.debug('%s: poll_user: setting most-recent since_id to "%s"' % (user, children[0].id))
		self.db.set_last_since_id(user, children[0].id)

	def poll_friends(self):
		'''
			Retrieve posts & comments from /r/friends.
			Scrape new content, store in database.
		'''

		for friend_url in ['/r/friends/new', '/r/friends/comments']:
			children = self.reddit.get('http://www.reddit.com%s.json' % friend_url)
			self.debug('poll_friends: loaded %d items from %s' % (len(children), friend_url))
			for child in children:
				user = child.author
				if user == '[deleted]': continue

				# Add friend as 'user' in DB if needed
				if not self.db.user_already_added(user):
					self.db.add_user(user)

				# Check child.id matches the child.author's lastsinceid in DB
				lastsinceid = self.db.get_last_since_id(user)
				if lastsinceid == child.id:
					# We've already retrieved this post
					continue

				# Setup loggers
				self.setup_loggers_for_user(user)

				# Ignore excluded subreddits
				if self.is_excluded_child(child):
					continue

				self.get_and_process_urls_from_child(child)

				# Close loggers
				self.restore_loggers()


	''' Returns list of URLs found in a reddit child (post or comment) '''
	def get_urls(self, child):
		if type(child) == Post:
			if child.selftext != None and child.selftext != '':
				return self.reddit.get_links_from_text(child.selftext)
			elif child.url != None:
				return [child.url]
			return []
		elif type(child) == Comment:
			return self.reddit.get_links_from_text(child.body)
		raise Exception('unsupported child type: %s' % child)

	''' Downloads media(s) at url, adds to database. '''
	def process_url(self, url, url_index, child):
		self.debug('%s: process_url: %s' % (child.author, url))

		# Ignore duplicate albums
		if self.db.album_exists(url):
			self.debug('''%s: process_url: album %s already exists in database.
Permalink: %s
   Object: %s''' % (child.author, url, child.permalink(), str(child)))
			return

		userid = self.db.get_user_id(child.author)
		if type(child) == Post:
			base_fname = '%s-%d' % (child.id, url_index)
			postid = child.id
			commid = None
		elif type(child) == Comment:
			base_fname = '%s-%s-%d' % (child.post_id, child.id, url_index)
			postid = child.post_id
			commid = child.id

		working_dir = path.join(ImageUtils.get_root(), 'content', child.author)

		# A single URL can contain multiple medias (i.e. albums)
		try:
			(media_type, albumname, medias) = ImageUtils.get_urls(url)
		except Exception, e:
			self.debug('%s: process_url: unable to get URLs for %s: %s' % (child.author, url, str(e)))
			if 'domain not supported' in str(e):
				# Save domain-not-supported URLs to new file
				user_dir = path.join(ImageUtils.get_root(), 'content', child.author)
				f = open(path.join(user_dir, 'unsupported.txt'), 'a')
				f.write(url)
				f.write('\n')
				f.flush()
				f.close()
			return

		if albumname != None:
			# Album!
			albumname = '%s-%s' % (base_fname, albumname)
			working_dir = path.join(working_dir, albumname)
			#self.debug('%s: process_url: adding album to database' % child.author)
			album_id = self.db.add_album(
					working_dir,
					child.author,
					url,
					postid,
					commid,
			)
		else:
			album_id = None

		if self.db.get_config('save_thumbnails', default='true') == 'true':
			ImageUtils.create_subdirectories(path.join(working_dir, 'thumbs'))
		else:
			ImageUtils.create_subdirectories(working_dir)

		for media_index, media in enumerate(medias):
			# Construct save path: /user/post[-comment]-index-filename
			fname = ImageUtils.get_filename_from_url(media, media_type)
			fname = '%s-%02d-%s' % (base_fname, media_index, fname)
			saveas = path.join(working_dir, fname)

			# Download URL
			try:
				self.debug('%s: process_url: downloading #%d %s' % (child.author, media_index + 1, media))
				headers = {
					'Referer' : url
				}
				ImageUtils.httpy.download(media, saveas, headers=headers)
				if path.getsize(saveas) == 503:
					raise Exception('503b = removed')
			except Exception, e:
				self.debug('%s: process_url: failed to download #%d: %s, moving on' % (child.author, media_index + 1, str(e)))
				continue

			# Get media information (width, height, thumbsaveas)
			if media_type == 'audio':
				# Audio files don't have width/height/thumbnail
				width = height = 0
				savethumbas = path.join(ImageUtils.get_root(), 'images', 'audio.png')
			else:
				try:
					(width, height) = ImageUtils.get_dimensions(saveas)
				except Exception, e:
					# If we cannot process the media file, skip it!
					self.debug('%s: process_url: #%d %s' % (child.author, media_index + 1, str(e)))
					continue

				# Create thumbnail if needed
				if self.db.get_config('save_thumbnails', 'true') == 'false':
					savethumbas = path.join(ImageUtils.get_root(), 'images', 'nothumb.png')
				else:
					savethumbas = path.join(working_dir, 'thumbs', fname)
					try:
						savethumbas = ImageUtils.create_thumbnail(saveas, savethumbas)
					except Exception, e:
						savethumbas = path.join(ImageUtils.get_root(), 'images', 'nothumb.png')
						self.debug('%s: process_url: failed to create thumb #%d: %s, using default' % (child.author, media_index + 1, str(e)))

			size = path.getsize(saveas)

			# Add to DB
			self.db.add_image(
					saveas,
					child.author,
					media,
					width,
					height,
					size,
					savethumbas,
					media_type,
					album_id,
					postid,
					commid
			)
		self.db.update_user(child.author)
	
	def infinite_loop(self):
		users = self.db.get_users(new=False)

		last_user = self.db.get_config('last_user')
		last_index = 0 if last_user == None or last_user not in users else users.index(last_user)

		while True:
			# Look for and poll newly-added users
			newusers = self.db.get_users(new=True)
			for newuser in newusers:
				# Add new user to existing list
				users.append(newuser)
				# Add user to friends list if applicable
				friend_zone = self.db.get_config('friend_zone')
				if friend_zone == None or friend_zone == 'none':
					self.add_friend(newuser)
				self.poll_user(newuser) # Poll new user for content

			last_index += 1
			if last_index >= len(users):
				last_index = 0
				# Get top users if it's enabled
				if self.db.get_config('add_top_users') != 'false':
					for new_top_user in self.add_top_users():
						# Add top users to users list
						if not new_top_user.lower() in [x.lower() for x in users]:
							users.append(new_top_user)

			# Check if there are actually users to retrieve
			if len(users) == 0:
				self.debug('no users to retrieve. exiting')
				break

			user = users[last_index]
			# Add user to friends list if applicable
			friend_zone = self.db.get_config('friend_zone')
			if friend_zone == 'only' or friend_zone == 'some':
				if not self.db.already_friend(user):
					self.add_friend(user)

				# Scan for updates from friends
				try:
					self.poll_friends()
				except Exception, e:
					self.debug('infinite_loop: poll_friends: %s' % str(e))
					from traceback import format_exc
					print format_exc()

			# Poll user if applicable
			if friend_zone != 'only':
				try:
					self.poll_user(user) # Poll user for content
					self.db.set_config('last_user', user)
				except Exception, e:
					self.debug('infinite_loop: poll_user: %s' % str(e))
					from traceback import format_exc
					print format_exc()			

	def add_top_users(self):
		users = []
		subs = ['gonewild']
		self.debug('add_top_users: loading top posts for the week from %s' % ','.join(subs))
		try:
			posts = self.reddit.get('http://www.reddit.com/r/%s/top.json?t=week' % '+'.join(subs))
		except Exception, e:
			self.debug('add_top_users: Exception: %s' % str(e))
			return users
		for post in posts:
			if post.author == '[deleted]': continue
			if not self.db.user_already_added(post.author):
				self.debug('add_top_users: Found new user, adding /u/%s' % post.author)
				self.db.add_user(post.author, new=True)
				friend_zone = self.db.get_config('friend_zone')
				if friend_zone == None or friend_zone == 'none':
					self.add_friend(post.author)
				users.append(post.author)
		return users


	def add_friend(self, user):
		try:
			self.reddit.add_friend(user)
		except Exception, e:
			self.debug(str(e))
			return

		if self.db.already_friend(user):
			self.debug('Warning: User /u/%s is already considered a "friend" in the DB; tried to friend on reddit anyway' % user)
		else:
			self.db.add_friend(user)
			self.debug('User /u/%s saved as friend on reddit & DB' % user)

	def remove_friend(self, user):
		try:
			self.reddit.remove_friend(user)
		except Exception, e:
			self.debug(str(e))
			return

		if not self.db.already_friend(user):
			self.debug('Warning: User /u/%s is not considered a friend in the DB; tried to unfriend on reddit anyway' % user)
		else:
			self.db.remove_friend(user)
			self.debug('User /u/%s removed as friend on reddit & DB' % user)

	def compare_friends(self, add_friends=False):
		db_users = self.db.get_users_list()
		db_friends = self.db.get_friends_list()
		self.login()
		try:
			reddit_friends = self.reddit.get_friends_list()
		except Exception, e:
			self.debug(str(e))
			reddit_friends = []
		self.debug('%d total users, %d friends in DB, %d friends on reddit' % (len(db_users), len(db_friends), len(reddit_friends)))

		need2add = []

		# Add friends from reddit to the DB
		for friend in reddit_friends:
			if friend.lower() not in [x.lower() for x in db_friends]:
				self.db.add_friend(friend)
				self.debug('Added reddit friend to DB: /u/%s' % friend)

		# Add friends in DB to reddit's friends list
		for friend in db_friends:
			if friend.lower() not in [x.lower() for x in reddit_friends]:
				need2add.append(friend)

		# Add users from DB to reddit's friends list
		for friend in db_users:
			if friend.lower() not in [x.lower() for x in db_friends]:
				need2add.append(friend)
			elif friend.lower() not in [x.lower() for x in reddit_friends]:
				need2add.append(friend)

		# Remove duplicates
		need2add = list(set(need2add))

		if len(need2add) > 0:
			if add_friends:
				self.debug('Synchronizing friends...')
				for friend in need2add:
					self.add_friend(friend)
					self.debug('Added /u/%s as a friend on reddit' % friend)
			else:
				self.debug('Found %d users that are not friended. to friend them, execute:\npython Gonewild.py --friend %s' % (len(need2add), ','.join(need2add)))
		
	def toggle_addtop(self):
		if self.db.get_config('add_top_users') != 'false':
			self.db.set_config('add_top_users', 'false')
			self.debug('Will stop automatically adding top users from http://reddit.com/r/gonewild/top?t=week')
		else:
			self.db.set_config('add_top_users', 'true')
			self.debug('Will automatically add top users from http://reddit.com/r/gonewild/top?t=week')

	def print_posts(self, user):
		userid = self.db.get_user_id(user)
		posts = self.db.select('id,title,url,selftext,subreddit,created,permalink,ups,downs', 'posts', 'userid = ? order by created asc', [userid])
		for (postid, title, url, selftext, subreddit, created, permalink, ups, downs) in posts:
			output = ['']
			output.append(    'Permalink: %s' % permalink)
			output.append(    '    Title: %s' % title.replace('\n', ''))
			if url != None:
				output.append(' Url/Text: %s' % url)
			elif selftext != None:
				output.append(' Url/Text: %s' % selftext)
			output.append(    '     Date: %s' % strftime('%y-%m-%dT%H:%M:%SZ', gmtime(created)))
			output.append(    '    Votes: +%d/-%d' % (ups, downs))
			print '\n'.join(output)

	def print_comments(self, user):
		userid = self.db.get_user_id(user)
		comments = self.db.select('id,subreddit,text,created,permalink,ups,downs', 'comments', 'userid = ? order by created asc', [userid])
		for (commentid, subreddit, body, created, permalink, ups, downs) in comments:
			output = ['']
			output.append(    'Permalink: %s' % permalink)
			output.append(    '     Date: %s' % strftime('%y-%m-%dT%H:%M:%SZ', gmtime(created)))
			output.append(    '    Votes: +%d/-%d' % (ups, downs))
			output.append(    '  Comment: %s' % body.replace('\n\n', '\n').replace('\n', '\n           '))
			print '\n'.join(output)

	def exit_if_already_started(self):
		from commands import getstatusoutput
		(status, output) = getstatusoutput('ps aux')
		running_processes = 0
		for line in output.split('\n'):
			if 'python' in line and 'Gonewild.py' in line and not '/bin/sh -c' in line:
				running_processes += 1
		if running_processes > 1:
			exit(0) # Quit silently if the bot is already running

	def login(self):
		try:
			(username, password) = self.db.get_credentials('reddit')
			try:
				self.reddit.login(username, password)
			except Exception, e:
				self.debug('login: Failed to login to reddit: %s' % str(e))
				raise e
		except Exception, e:
			self.debug('login: Failed to get reddit credentials: %s' % str(e))
			raise e

	def setup_config(self):
		keys = {
			'save_thumbnails' : 'true',
			'add_top_users' : 'true',
			'excluded_subreddits' : '',
			'friend_zone' : 'some',
			'last_user' : ''
		}
		for (key,value) in keys.iteritems():
			if self.db.get_config(key) == None:
				self.db.set_config(key, value)

def handle_arguments(gw):
	import argparse
	parser = argparse.ArgumentParser(description='''
Gonewild content aggregator.
Run without any arguments to start scraping in an infinite loop.
Be sure to add a working reddit account before scraping.
Arguments can continue multiple values (separated by commas)
''')

	parser.add_argument('--add', '-a',
		help='Add user(s) to scan for new content',
		metavar='USER')
	parser.add_argument('--add-top', '-tz',
		help='Toggle adding top users from /r/gonewild',
		action='store_true')
	parser.add_argument('--remove',
		help='Remove user from database',
		metavar='USER')

	parser.add_argument('--exclude',
		help='Add subreddit to exclude (ignore)',
		metavar='SUBREDDIT')
	parser.add_argument('--include',
		help='Remove subreddit from excluded list',
		metavar='SUBREDDIT')

	parser.add_argument('--friend',
		help='Add user(s) to reddit "friends" list',
		metavar='USER')
	parser.add_argument('--unfriend',
		help='Remove user(s) from reddit "friends" list',
		metavar='USER')
	parser.add_argument('--no-friend-zone',
		help='Do not poll /r/friends, only user pages (default)',
		action='store_true')
	parser.add_argument('--friend-zone',
		help='Poll both /r/friends AND user pages',
		action='store_true')
	parser.add_argument('--just-friends',
		help='Only use /r/friends; Don\'t poll user pages',
		action='store_true')
	parser.add_argument('--sync-friends',
		help='Synchronizes database with reddit\'s friends list',
		action='store_true')
	parser.add_argument('--reddit',
		help='Store reddit user account credentials',
		nargs=2,
		metavar=('user', 'pass'))
	parser.add_argument('--soundcloud',
		help='Store soundcloud API credentials',
		nargs=2,
		metavar=('api', 'key'))

	parser.add_argument('--backfill-thumbnails',
		help='Attempt to create missing thumbnails',
		action='store_true')

	parser.add_argument('--comments',
		help='Dump all comments for a user',
		metavar='USER')
	parser.add_argument('--posts',
		help='Print all posts made by a user',
		metavar='USER')

	parser.add_argument('--log',
		help='Set logging level (global, user, none)',
		metavar='LEVEL')

	parser.add_argument('--config',
		help='Show or set configuration values',
		nargs='*',
		metavar=('key', 'value'))

	args = parser.parse_args()

	if args.friend_zone:
		gw.db.set_config('friend_zone', 'some')
		gw.debug('Friend-zone enabled; Will scrape both /r/friends AND user pages')
		gw.compare_friends()
	elif args.just_friends:
		gw.db.set_config('friend_zone', 'only')
		gw.debug('Friend-zone enabled; Will ONLY scrape /r/friends (not user pages)')
		gw.compare_friends()
	elif args.no_friend_zone:
		gw.db.set_config('friend_zone', 'none')
		gw.debug('Friend-zone disabled; Will ONLY scrape user pages (not /r/friends)')
	elif args.sync_friends:
		gw.compare_friends(add_friends=True)
		gw.debug('Friends list synced with database')

	elif args.add_top:
		gw.toggle_addtop()

	elif args.add:
		users = args.add.replace('u/', '').replace('/', '').split(',')
		for user in users:
			if not gw.db.user_already_added(user):
				gw.db.add_user(user, new=True)
				gw.debug('Add new user: /u/%s' % user)
			else:
				gw.debug('Warning: User already added: /u/%s' % user)
	elif args.remove:
		users = args.remove.replace('u/', '').replace('/', '').split(',')
		for user in users:
			if gw.db.user_already_added(user):
				gw.db.remove_user(user, new=True)
				gw.debug('Add new user: /u/%s' % user)
			else:
				gw.debug('Warning: User already added: /u/%s' % user)

	elif args.friend:
		users = args.friend.replace('u/', '').replace('/', '').split(',')
		gw.login()
		for user in users:
			gw.add_friend(user)
	elif args.unfriend:
		users = args.unfriend.replace('u/', '').replace('/', '').split(',')
		gw.login()
		for user in users:
			gw.remove_friend(user)

	elif args.exclude:
		subs = args.exclude.replace('r/', '').replace('/', '').split(',')
		for sub in subs:
			try:
				gw.add_excluded_subreddit(sub)
				gw.debug('Added excluded subreddit: /r/%s' % sub)
			except Exception, e:
				gw.debug('Unable to exclude subreddit /r/%s: %s' % (sub, str(e)))
	elif args.include:
		subs = args.include.replace('r/', '').replace('/', '').split(',')
		for sub in subs:
			try:
				gw.db.remove_excluded_subreddit(sub)
				gw.debug('Removed excluded subreddit: /r/%s' % sub)
			except Exception, e:
				gw.debug('Unable to remove excluded subreddit /r/%s: %s' % (sub, str(e)))

	elif args.reddit:
		gw.db.set_credentials('reddit', args.reddit[0], args.reddit[1])
		gw.debug('Added/updated reddit login credentials for user "%s"' % args.reddit[0])
	elif args.soundcloud:
		gw.db.set_credentials('soundcloud', args.soundcloud[0], args.soundcloud[1])
		gw.debug('Added/updated soundcloud login credentials for user "%s"' % args.soundcloud[0])

	elif args.backfill_thumbnails:
		for imageid,imagepath in gw.db.select('id,path', 'images', 'thumb like "%nothumb.png"'):
			fname = path.basename(imagepath)
			fpath = path.dirname(imagepath)

			thumbpath = path.join(fpath, 'thumbs')
			ImageUtils.create_subdirectories(thumbpath)
			savethumbas = path.join(thumbpath, fname)

			try:
				savethumbas = ImageUtils.create_thumbnail(imagepath, savethumbas)
				gw.db.update('images', 'thumb = ?', 'id = ?', [savethumbas, imageid])
				gw.debug('created thumbnail %s' % savethumbas)
			except Exception, e:
				savethumbas = path.join(ImageUtils.get_root(), 'images', 'nothumb.png')
				gw.debug('Backfill-Thumbnails: Failed to create thumb for %s: %s, using nothumb.png' % (imagepath, str(e)))
		gw.db.commit()

	elif args.comments:
		users = args.comments.replace('u/', '').replace('/', '').split(',')
		for user in users:
			gw.print_comments(user)
	elif args.posts:
		users = args.posts.replace('u/', '').replace('/', '').split(',')
		for user in users:
			gw.print_posts(user)
	
	elif args.log:
		level = args.log
		if not level.lower() in ['global', 'user', 'none', 'off']:
			gw.debug('Failed to set log level: given level "%s" is not valid' % level.lower())
			gw.debug('Use "global", "user" or "none"')
		else:
			gw.db.set_config('log_level', level.lower())
			gw.debug('Set Log Level to: %s' % level.lower())

	elif args.config == [] or args.config:
		if len(args.config) == 0:
			gw.debug('Dumping configuration values...')
			for (key, value) in sorted(gw.db.select('key,value', 'config')):
				gw.debug('%s = "%s"' % (key, value))
		elif len(args.config) == 1:
			key = args.config[0]
			value = gw.db.get_config(key)
			if value == None:
				gw.debug('Configuration key not found for "%s"' % key)
			else:
				gw.debug('Configuration: %s = "%s"' % (key, value))
		elif len(args.config) == 2:
			key = args.config[0]
			value = args.config[1]
			gw.db.set_config(key, value)
			gw.debug('Saved configuration: %s = "%s"' % (key, value))
	else:
		return False
	return True

if __name__ == '__main__':

	gw = Gonewild()
	gw.setup_config()
	try:
		if handle_arguments(gw):
			exit(0)
	except Exception, e:
		gw.debug('\n[!] Error: %s' % str(e.message))
		from traceback import format_exc
		print format_exc()

		from sys import exit
		exit(1)

	gw.login()
	gw.infinite_loop()
	
