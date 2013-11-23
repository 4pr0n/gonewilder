#!/usr/bin/python

"""
	"Backfill" existing database data.
	Gets titles, permalinks, dates, etc from reddit.
	Overwrites existing 'bad' data with accurate data.
"""

from DB      import DB
from Reddit  import Reddit
from sys     import exit, stdout
from urllib2 import HTTPError

db = DB()
reddit = Reddit()

def backfill_users():
	q_users = '''
		select id,username
			from users
			where deleted = 0
	'''
	cur = db.conn.cursor()
	execur = cur.execute(q_users)
	ids_and_users = execur.fetchall() # Get list of users + ids
	index = 0
	for (userid, username) in ids_and_users:
		index += 1
		print '(%d/%d) updating %s...' % (index, len(ids_and_users), username),
		stdout.flush()
		try:
			ui = Reddit.get_user_info(username)
		except Exception, e:
			print str(e)
			continue
		q_user = '''
			update users 
				set
					created  = %d,
					username = "%s"
				where id = %d
		''' % (ui.created, ui.name, userid)
		cur.execute(q_user)
		print 'done'
	
	cur.close()

def backfill_posts():
	POSTS = {}

	(username, password) = db.get_credentials('reddit')
	reddit.login(username, password)

	cur = db.conn.cursor()
	query = '''
		select id, userid, title, selftext, url, subreddit, over_18, created, legacy, permalink, ups, downs
			from posts
			where legacy = 1
			order by id
	'''
	execur = cur.execute(query)
	results = execur.fetchall()

	# Store existing values in dict
	for (postid, userid, title, selftext, url, subreddit, over_18, created, legacy, permalink, ups, downs) in results:
		postid = str(postid)
		POSTS[postid] = {
				'userid'    : userid,
				'title'     : title,
				'url'       : url,
				'selftext'  : selftext,
				'subreddit' : subreddit,
				'over_18'   : over_18,
				'created'   : created,
				'legacy'    : legacy,
				'permalink' : permalink,
				'ups'       : ups,
				'downs'     : downs
			}

	posts_per_page = 99
	i = 0
	while i < len(results):
		ids = [str(x[0]) for x in results[i:i+posts_per_page]]
		ids.append('t3_1234')
		url = 'http://www.reddit.com/by_id/t3_%s.json' % ',t3_'.join(ids)
		try:
			posts = reddit.get(url)
		except HTTPError:
			posts = []

		for post in posts:
			post.id = str(post.id)
			if not post.id in POSTS: post.id = post.id.rjust(6, '0')
			if not post.id in POSTS: continue
			oldpost = POSTS[post.id]
			oldpost['title']     = post.title
			oldpost['url']       = post.url
			oldpost['selftext']  = post.selftext
			oldpost['subreddit'] = post.subreddit
			oldpost['created']   = int(post.created)
			oldpost['permalink'] = post.permalink()
			oldpost['over_18']   = int(post.over_18)
			oldpost['legacy']    = 0
			oldpost['id']        = post.id
			oldpost['ups']       = post.ups
			oldpost['downs']     = post.downs
			Reddit.debug('updating post %s by %s' % (post.id, post.author))
			update_post(oldpost)
		db.conn.commit()
		i += posts_per_page
		Reddit.debug('%d/%d - %d remaining' % (i, len(results), len(results)-i))

def update_post(post):
	query = '''
		update posts
			set
				title     = ?,
				url       = ?,
				selftext  = ?,
				subreddit = ?,
				over_18   = ?,
				created   = ?,
				permalink = ?,
				legacy    = 0,
				ups       = ?,
				downs     = ?
			where
				id = ?
	'''
	cur = db.conn.cursor()
	cur.execute(query, (post['title'], post['url'], post['selftext'], post['subreddit'], 
	                    post['over_18'], post['created'], post['permalink'],
	                    post['ups'], post['downs'], post['id']) )
	cur.close()


def backfill_comments():
	(username, password) = db.get_credentials('reddit')
	reddit.login(username, password)

	cur = db.conn.cursor()
	query = '''
		select
				id,
				userid,
				postid,
				subreddit,
				text,
				created,
				legacy,
				permalink,
				ups,
				downs
		from comments
		where legacy = 1
		order by id
	'''
	execur = cur.execute(query)
	results = execur.fetchall()

	for (commentid,
	     userid,
	     postid,
	     subreddit,
	     text,
	     created,
	     legacy,
	     permalink,
	     ups,
	     downs) in results:
		# Get comment from reddit
		post = Reddit.get('http://www.reddit.com/comments/%s/_/%s' % (postid, commentid))
		if len(post.comments) > 0:
			comment = post.comments[0]
			# Update db
			query = '''
				update comments
					set
						postid    = ?,
						subreddit = ?,
						text      = ?,
						created   = ?,
						permalink = ?,
						legacy    = 0,
						ups       = ?,
						downs     = ?
					where
						id = ?
			'''
			cur.execute(query, (postid, subreddit, text, created, permalink, legacy, ups, downs, commentid) )
	cur.close()

if __name__ == '__main__':
	#backfill_users()
	backfill_posts()
