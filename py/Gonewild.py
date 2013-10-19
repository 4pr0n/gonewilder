#!/usr/bin/python

from DB import DB
from Reddit import Reddit, Child, Post, Comment

class Gonewild(object):
	db = DB()

	@staticmethod
	def user_already_added(user):
		return Gonewild.db.user_already_added(user)

	'''
		Gets new posts/comments for user,
		Finds URLs in posts/comments,
		"Processes" (downloads) URLs,
		Adds results to database.
	'''
	@staticmethod
	def poll_user(user):
		since_id = Gonewild.db.get_last_since_id(user)
		# Get posts/comments for user
		children = Reddit.get(user, since=since_id)

		# Set lats 'since' to the most-recent post/comment ID
		if len(children) > 0:
			Gonewild.db.set_last_since_id(user, children[0].id)

		for child in children:
			urls = Gonewild.get_urls(child)
			if type(child) == Post:
				Gonewild.db.add_post(child)
				urls = Gonewild.get_urls_from_post(child)
			elif type(child) == Comment:
				Gonewild.db.add_comment(child)
				urls = Gonewild.get_urls_from_comment(child)
			for url_index, url in enumerate(urls):
				process_url(url, url_index, child)

	''' Returns list of URLs found in a reddit child (post or comment) '''
	@staticmethod
	def get_urls(child):
		if type(child) == Post:
			if child.selftext != None:
				return Reddit.get_links_from_text(child.selftext)
			elif child.url != None:
				return [child.url]
			return []
		elif type(child) == Comment:
			return Reddit.get_links_from_text(child.selftext)
		raise Exception('unsupported child type: %s' % child)
			
	@staticmethod
	def process_url(url, url_index, child):
		userid = Gonewild.db.get_user_id(child.author)
		if type(child) == Post:
			base_fname = '%s-%d' % (child.id, url_index)
			postid = child.id
			commid = None
		elif type(child) == Comment:
			base_fname = '%s-%s-%d' % (child.post_id, child.id, url_index)
			postid = child.post_id
			commid = child.id

		# A single URL can contain multiple medias (i.e. albums)
		(media_type, medias) = ImageUtils.get_urls(url)
		if len(medias) > 1:
			# Album!
			# Add to database, get ID
			#album_id = (the album id)
			# Create subdir? Store albums in subdir?
			pass
		else:
			album_id = None
		for media_index, media in enumerate(medias):
			# Construct save path: /user/post[-comment]-index-filename
			fname = ImageUtils.get_filename_from_url(media)
			saveas = '%s-%02d-%s' % (base_fname, media_index, fname)
			saveas = path.join(child.author, saveas)
			# Download URL
			
			# Create thumbnail
			#thumbnail = same as saveas, but pointing to /thumbs/
			# Might need to copy nothumb.png, or reference it instead?

			# Get image information (width, height, size)
			
			# Add to DB
			'''
			id=NULL
			path=saveas (/users/%s)
			userid=userid
			media
			width
			height
			size
			thumb=thumbnail
			type=media_type
			albumid=album_id
			post=postid
			comment=commid
			views=rating=ratings=0
			'''

if __name__ == '__main__':
	Gonewild.poll_user('4_pr0n')
