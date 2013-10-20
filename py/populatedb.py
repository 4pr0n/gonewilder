#!/usr/bin/python

from os import listdir, path, walk
from DB import DB
from ImageUtils import ImageUtils

db = DB()
root = ImageUtils.get_root()

'''
	Iterates over existing sets,
	adds sets to database,
	attempts to populate DB with information based on filenames:
		* URL (http://i.imgur.com/<image>
		* Post ID
		* Comment ID
		* Creation time
	Copies existing set to new directory (/content/),
	Generates new thumbnails for the sets
'''
def populate_db():
	for user in listdir(path.join(root, 'users')):
		userdir = path.join(root, 'users', user)
		if not path.isdir(userdir): continue
		for item in listdir(userdir):
			itempath = path.join(userdir, item)
			if path.isfile(itempath):
				# Image
				print "image: %s" % itempath
				db.add_existing_image(user, item, itempath)
			elif path.isdir(itempath):
				# Album
				print "album: %s" % itempath
				db.add_existing_album(user, item, itempath)

'''
	Iterate over every user, 
	Get most-recent post id,
	Set user's "last since" id to the latest post id
'''
def set_last_since():
	cur = db.conn.cursor()
	query = 'select username,themax from users,(select userid,max(posts.id) as themax from posts group by posts.userid) where userid = users.id'
	for user,since in cur.execute(query).fetchall():
		print user,since
		db.set_last_since_id(user, since)

if __name__ == '__main__':
	#populate_db()
	#set_last_since()
	pass
