#!/usr/bin/python

from Httpy    import Httpy
from os       import path, getcwd, sep, mkdir
from PIL      import Image # Python Image Library
from commands import getstatusoutput
from sys      import stderr

class ImageUtils(object):
	logger = stderr

	# Static class variables
	MAXIMUM_THUMBNAIL_SIZE = 5 * 1024 * 1024 # In bytes
	MAXIMUM_THUMBNAIL_DIM  = 4000 # In pixels
	httpy = Httpy()

	@staticmethod
	def debug(text):
		ImageUtils.logger.write('ImageUtils: %s\n' % text)
		if ImageUtils.logger != stderr:
			stderr.write('ImageUtils: %s\n' % text)

	'''
		Given a URL, return a tuple containig:
		[0] media type ('video', 'image')
		[1] filesystem-safe album name, or None if not an album
		[2] List of all direct links to relevant media. E.g.:
					imgur.com/asdf1 -> [i.imgur.com/asdf1.jpg]
					i.imgur.com/smallh.jpg -> [i.imgur.com/large.jpg]
					imgur.com/a/album -> [i.imgur.com/image1.jpg, i.imgur.com/image2.jpg]
					xhamster.com/video -> xhamster.com/cdn/video.mp4
					etc
		Throws exception if domain is not supported.
	'''
	@staticmethod
	def get_urls(url):
		if 'imgur.com' in url:
			return ImageUtils.get_urls_imgur(url)
		elif '.' in url and url.lower()[url.rfind('.')+1:] in ['jpg', 'jpeg', 'png', 'gif']:
			# Direct link to image
			return ('image', None, [url])
		elif 'xhamster.com' in url:
			# xhamster
			return ImageUtils.get_urls_xhamster(url)
		elif 'videobam.com' in url:
			# videobam
			return ImageUtils.get_urls_videobam(url)
		elif 'sexykarma.com' in url:
			# sexykarma
			return ImageUtils.get_urls_sexykarma(url)
		elif 'tumblr.com' in url:
			# tumblr
			return ImageUtils.get_urls_tumblr(url)
		elif 'vine.co/' in url:
			# vine
			return ImageUtils.get_urls_vine(url)
		else:
			raise Exception('domain not supported; %s' % url)
	
	''' Removes excess fields from URL '''
	@staticmethod
	def strip_url(url):
		if '?' in url: url = url[:url.find('?')]
		if '#' in url: url = url[:url.find('#')]
		if '&' in url: url = url[:url.find('&')]
		return url

	################
	# XHAMSTER
	@staticmethod
	def get_urls_xhamster(url):
		ImageUtils.debug('xhamster: getting %s' % url)
		r = ImageUtils.httpy.get(url)
		if not "<div class='mp4'>" in r:
			raise Exception('no mp4 found at %s' % url)
		chunk = ImageUtils.httpy.between(r, "<div class='mp4'>", "</div>")[0]
		return ('video', None, [ImageUtils.httpy.between(chunk, 'href="', '"')[0]])

	################
	# VIDEOBAM
	@staticmethod
	def get_urls_videobam(url):
		ImageUtils.debug('videobam: getting %s' % url)
		r = ImageUtils.httpy.get(url)
		if not ',"url":"' in r:
			raise Exception('no url found at %s' % url)
		for link in ImageUtils.httpy.between(r, '"url":"', '"'):
			if not '.mp4' in link: continue
			return ('video', None, [link.replace('\\', '')])
		raise Exception('no mp4 found at %s' % url)

	################
	# SEXYKARMA
	@staticmethod
	def get_urls_sexykarma(url):
		ImageUtils.debug('sexykarma: getting %s' % url)
		r = ImageUtils.httpy.get(url)
		if not "url: escape('" in r:
			raise Exception('no url found at %s' % url)
		for link in ImageUtils.httpy.between(r, "url: escape('", "'"):
			return ('video', None, [link])
		raise Exception('no video found at %s' % url)

	################
	# TUMBLR
	@staticmethod
	def get_urls_tumblr(url):
		ImageUtils.debug('tumbmlr: getting %s' % url)
		r = ImageUtils.httpy.get(url)
		if not 'source src=\\x22' in r:
			raise Exception('no src= found at %s' % url)
		for link in ImageUtils.httpy.between(r, 'source src=\\x22', '\\x22'):
			link = ImageUtils.httpy.unshorten(link)
			return ('video', None, [link])
		raise Exception('no video found at %s' % url)

	################
	# VINE
	@staticmethod
	def get_urls_vine(url):
		ImageUtils.debug('vine: getting %s' % url)
		r = ImageUtils.httpy.get(url)
		if not 'property="twitter:image" content="' in r:
			raise Exception('no twitter:image found at %s' % url)
		for link in ImageUtils.httpy.between(r, 'property="twitter:image" content="', '"'):
			return ('video', None, [link])
		raise Exception('no video found at %s' % url)

	################
	# IMGUR
	@staticmethod
	def get_urls_imgur(url):
		if url.startswith('//'): url = 'http:%s' % url
		url = ImageUtils.strip_url(url)
		if '/m.imgur.com/' in url: url = url.replace('/m.imgur.com/', '/imgur.com/')
		if '.com/a/' in url:
			# Album
			albumid = url[url.find('/a/')+3:]
			if '/' in albumid: albumid = albumid[:albumid.find('/')]
			if '#' in albumid: albumid = albumid[:albumid.find('#')]
			if '?' in albumid: albumid = albumid[:albumid.find('?')]
			return ('album', albumid, ImageUtils.get_imgur_album(url))
		else:
			# Image
			ImageUtils.debug('imgur: found %s' % url)
			return ('image', None, [ImageUtils.get_imgur_highest_res(url)])
		raise Exception('unable to get urls from %s' % url)

	@staticmethod
	def get_imgur_album(url):
		# Sanitize album URL
		url = url.replace('http://', '').replace('https://', '')
		fields = url.split('/')
		while fields[-2] != 'a': fields.pop(-1)
		url = 'http://%s' % '/'.join(fields)
		# Get album
		result = []
		ImageUtils.debug('imgur_album: loading %s' % url)
		r = ImageUtils.httpy.get('%s/noscript' % url)
		for image in ImageUtils.httpy.between(r, '<img src="//i.', '"'):
			image = 'http://i.%s' % image
			image = ImageUtils.get_imgur_highest_res(image)
			result.append(image)
		ImageUtils.debug('imgur_album: found %d images in album' % len(result))
		return result
	
	@staticmethod
	def get_imgur_highest_res(url):
		return url
		if not '/' in url:
			raise Exception('invalid url: %s' % url)
		fname = url.split('/')[-1]
		if '.' in fname and fname[fname.rfind('.')-1] == 'h':
			# Might not be highest res, revert to image-page
			noh = url[:url.rfind('h.')] + url[url.rfind('h.')+1:]
			ImageUtils.debug('imgur_highest_res: get_meta on %s' % noh)
			meta = ImageUtils.httpy.get_meta(noh)
			if 'Content-Length' in meta and meta['Content-Length'] == '503':
				return url
			else:
				return noh
		elif not '.' in fname:
			# Need to get full-size and extension
			ImageUtils.debug('imgur_highest_res: getting %s' % url)
			r = ImageUtils.httpy.get(url)
			if not '<link rel="image_src" href="' in r:
				raise Exception('image not found')
			image = ImageUtils.httpy.between(r, '<link rel="image_src" href="', '"')[0]
			return 'http:%s' % image
		return url


	'''
		Return just filename (no path) for a URL
			http://i.imgur.com/asdf1.jpg -> "asdf1.jpg"
			amazonaws.com/crazystuff/theimage.jpg?morecrazy=stuff&asdf=123 -> "theimage.jpg"
			http://2.videobam.com/storage/encoded.mp4/2d1/5113?ss=177 -> "encoded.mp4"
	'''
	@staticmethod
	def get_filename_from_url(url):
		fname = ImageUtils.strip_url(url)
		fields = fname.split('/')
		while not '.' in fields[-1]: fields.pop(-1)
		return fields[-1]


	########################
	# ACTUAL IMAGE FUNCTIONS

	'''
		Create thumbnail from existing image file.
		Raises exception if unable to save thumbnail
	'''
	@staticmethod
	def create_thumbnail(image, saveas):
		if image.lower().endswith('.mp4') or \
		   image.lower().endswith('.flv'):
			ImageUtils.create_video_thumbnail(image, saveas)
			return
		if path.getsize(image) > ImageUtils.MAXIMUM_THUMBNAIL_SIZE:
			raise Exception('Image too large: %db %db' % 
					(path.getsize(image), ImageUtils.MAXIMUM_THUMBNAIL_SIZE))
		try:
			im = Image.open(image)
		except Exception, e:
			raise Exception('failed to create thumbnail: %s' % str(e))
		(width, height) = im.size
		if width  > ImageUtils.MAXIMUM_THUMBNAIL_DIM or \
		   height > ImageUtils.MAXIMUM_THUMBNAIL_DIM:
			raise Exception(
					'Image too large: %dx%d > %dpx' % 
					(width, height, ImageUtils.MAXIMUM_THUMBNAIL_DIM))
			
		if im.mode != 'RGB': im = im.convert('RGB')
		im.thumbnail( (200,200), Image.ANTIALIAS)
		im.save(saveas, 'JPEG')

	''' 
		Create thumbnail for video file using ffmpeg.
		Raises exception if unable to save video thumbnail
	'''
	@staticmethod
	def create_video_thumbnail(video, saveas):
		overlay = path.join(ImageUtils.get_root(), 'images', 'play_overlay.png')
		ffmpeg = '/usr/bin/ffmpeg'
		if not path.exists(ffmpeg):
			ffmpeg = '/opt/local/bin/ffmpeg'
			if not path.exists(ffmpeg):
				raise Exception('ffmpeg not found; unable to create video thumbnail')
		cmd = ffmpeg
		cmd += ' -i "'
		cmd += video
		cmd += '" -vf \'movie='
		cmd += overlay
		cmd += ' [watermark]; '
		cmd += '[in]scale=200:200 [scale]; '
		cmd += '[scale][watermark] overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2 [out]\' '
		cmd += saveas
		output = ''
		try:
			(status, output) = getstatusoutput(cmd)
		except:
			raise Exception('failed to generate thumbnail using ffmpeg: %s' % output)

	@staticmethod
	def get_image_dimensions(image):
		im = Image.open(image)
		return im.size


	###############
	# MISCELLANEOUS

	@staticmethod
	def create_subdirectories(directory):
		current = ''
		for subdir in directory.split(sep):
			if subdir == '': continue
			current = path.join(current, subdir)
			if not path.exists(current):
				mkdir(current)

	''' Get root working dir '''
	@staticmethod
	def get_root():
		cwd = getcwd()
		if cwd.endswith('py'):
			return '..'
		return '.'

if __name__ == '__main__':
	#url = 'http://www.sexykarma.com/gonewild/video/cum-compilation-YIdo9ntfsWo.html'
	#url = 'http://xhamster.com/movies/1435778/squirting_hard.html'
	#url = 'http://videobam.com/jcLzr'
	#url = 'http://alwaysgroundedx.tumblr.com/private/22807448211/tumblr_m3tyhmw3mQ1ruoc8i'
	#url = 'https://vine.co/v/h6Htgnj7Z5q'
	#print ImageUtils.get_urls(url)
	#ImageUtils.create_thumbnail('test.jpg', 'test_thumb.jpg')
	#ImageUtils.create_thumbnail('../test.mp4', '../test_thumb.jpg')
	pass
