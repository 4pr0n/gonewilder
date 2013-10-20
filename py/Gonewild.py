#!/usr/bin/python

from DB         import DB
from os         import path, mkdir
from sys        import stderr
from Reddit     import Reddit, Child, Post, Comment
from ImageUtils import ImageUtils
from time       import strftime, gmtime

class Gonewild(object):
	logger = stderr
	db = DB() # Database instance
	
	@staticmethod
	def debug(text):
		tstamp = strftime('[%Y-%m-%dT%H:%M:%SZ]', gmtime())
		text = '%s Gonewild: %s' % (tstamp, text)
		Gonewild.logger.write('%s\n' % text)
		if Gonewild.logger != stderr:
			stderr.write('%s\n' % text)

	@staticmethod
	def user_already_added(user):
		return Gonewild.db.user_already_added(user)

	def user_has_gone_wild(user):
		Reddit.logger = Gonewild.logger
		r = Reddit.get(user)

	'''
		Gets new posts/comments for user,
		Finds URLs in posts/comments,
		"Processes" (downloads) URLs,
		Adds results to database.
	'''
	@staticmethod
	def poll_user(user):
		# Create directories if needed
		user_dir = path.join(ImageUtils.get_root(), 'content', user)
		ImageUtils.create_subdirectories(user_dir)
		# Setup logger
		Gonewild.logger = open(path.join(user_dir, 'history.log'), 'a')
		Gonewild.db.logger = Gonewild.logger
		ImageUtils.logger  = Gonewild.logger
		Reddit.logger      = Gonewild.logger

		since_id = Gonewild.db.get_last_since_id(user)
		# Get posts/comments for user
		Gonewild.debug('poll_user: "%s" since "%s"' % (user, since_id))
		try:
			children = Reddit.get(user, since=since_id)
		except Exception, e:
			Gonewild.debug('poll_user: error %s' % str(e))
			return
		Gonewild.debug('poll_user: %d new posts and comments found' % len(children))

		if len(children) == 0:
			#Gonewild.debug('poll_user: no new posts/comments found')
			return

		# Set lats 'since' to the most-recent post/comment ID
		#Gonewild.debug('poll_user: setting most-recent since_id to "%s"' % children[0].id)
		#Gonewild.db.set_last_since_id(user, children[0].id)

		for child in children:
			urls = Gonewild.get_urls(child)
			try:
				if type(child) == Post:
					#Gonewild.debug('   Post: %d urls: %s "%s"' % (len(urls), child.permalink(), child.title.replace('\n', '')[0:30]))
					Gonewild.db.add_post(child)
				elif type(child) == Comment:
					#Gonewild.debug('Comment: %d urls: %s "%s"' % (len(urls), child.permalink(), child.body.replace('\n', '')[0:30]))
					Gonewild.db.add_comment(child)
			except Exception, e:
				Gonewild.debug('poll_user: %s' % str(e))
				continue # If we can't add the post/comment to DB, skip it
			if len(urls) > 0:
				Gonewild.debug('poll_user: found %d url(s) in child %s' % (len(urls), child.permalink()))
				for url_index, url in enumerate(urls):
					Gonewild.process_url(url, url_index, child)
		Gonewild.debug('poll_user: done')
		Gonewild.logger.close()

	''' Returns list of URLs found in a reddit child (post or comment) '''
	@staticmethod
	def get_urls(child):
		if type(child) == Post:
			if child.selftext != None and child.selftext != '':
				return Reddit.get_links_from_text(child.selftext)
			elif child.url != None:
				return [child.url]
			return []
		elif type(child) == Comment:
			return Reddit.get_links_from_text(child.body)
		raise Exception('unsupported child type: %s' % child)

	''' Downloads media(s) at url, adds to database. '''
	@staticmethod
	def process_url(url, url_index, child):
		Gonewild.debug('process_url: %s' % url)
		userid = Gonewild.db.get_user_id(child.author)
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
			Gonewild.debug('process_url: unable to get URLs for %s: %s' % (url, str(e)))
			return

		if albumname != None:
			# Album!
			albumname = '%s-%s' % (base_fname, albumname)
			working_dir = path.join(working_dir, albumname)
			#Gonewild.debug('process_url: adding album to database')
			album_id = Gonewild.db.add_album(
					working_dir,
					child.author,
					url,
					postid,
					commid,
			)
		else:
			album_id = None

		ImageUtils.create_subdirectories(path.join(working_dir, 'thumbs'))

		for media_index, media in enumerate(medias):
			# Construct save path: /user/post[-comment]-index-filename
			fname = ImageUtils.get_filename_from_url(media)
			fname = '%s-%02d-%s' % (base_fname, media_index, fname)
			saveas = path.join(working_dir, fname)

			# Download URL
			try:
				Gonewild.debug('process_url: downloading #%d %s' % (media_index + 1, media))
				ImageUtils.httpy.download(media, saveas)
				if path.getsize(saveas) == 503:
					raise Exception('503b = removed')
			except Exception, e:
				Gonewild.debug('process_url: failed to download #%d: %s, moving on' % (media_index + 1, str(e)))
				continue

			# Get media information (width, height, size)
			try:
				(width, height) = ImageUtils.get_dimensions(saveas)
			except Exception, e:
				# If we cannot process the media file, skip it!
				Gonewild.debug('process_url: #%d %s' % (media_index + 1, str(e)))
				continue
			size = path.getsize(saveas)

			# Create thumbnail
			savethumbas = path.join(working_dir, 'thumbs', fname)
			try:
				#Gonewild.debug('process_url: #%d creating thumbnail %s' % (media_index + 1, savethumbas))
				ImageUtils.create_thumbnail(saveas, savethumbas)
			except Exception, e:
				savethumbas = path.join(ImageUtils.get_root(), 'images', 'nothumb.png')
				Gonewild.debug('process_url: failed to create thumb #%d: %s, using default' % (media_index + 1, str(e)))

			# Add to DB
			Gonewild.db.add_image(
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
			#Gonewild.debug('process_url: added image to database')
	
	@staticmethod
	def infinite_loop():
		users = Gonewild.db.get_users(new=False)
		while True:
			for user in users:
				newusers = Gonewild.db.get_users(new=True) # Check for newly-added users
				for newuser in newusers:
					users.append(newuser)       # Add new user to existing list
					Gonewild.poll_user(newuser) # Poll new user for content
				Gonewild.poll_user(user) # Poll user for content

if __name__ == '__main__':
	try: Gonewild.db.add_user('delectable_me', new=True)
	except: pass
	Gonewild.infinite_loop()
