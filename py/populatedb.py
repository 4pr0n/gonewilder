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
				#print "image: %s" % itempath
				db.add_existing_image(user, item, itempath)
			elif path.isdir(itempath):
				# Album
				#print "album: %s" % itempath
				db.add_existing_album(user, item, itempath)

if __name__ == '__main__':
	populate_db()
	pass
