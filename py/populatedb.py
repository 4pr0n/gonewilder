#!/usr/bin/python

from os import listdir, path, walk
from DB import DB

db = DB()

for user in listdir('users'):
	userdir = path.join('users', user)
	if not path.isdir(userdir): continue
	for item in listdir(userdir):
		itempath = path.join(userdir, item)
		if path.isfile(itempath):
			# Image
			print "image: %s" % itempath
			db.add_existing_image(user, item)
		elif path.isdir(itempath):
			# Album
			print "album: %s" % itempath
			db.add_existing_album(user, item)
