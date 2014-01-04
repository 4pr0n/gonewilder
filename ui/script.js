var POST_COLUMNS = 5;
var POSTS_PER_REQUEST = 10;
var USERS_PER_REQUEST = 5;

function init() {
	setupSearch();
	// Setup header buttons
	$('.header .menu div')
		.click(function() {
			tabClickHandler($(this));
		})
		.removeClass('active');
	// Create/click header depending on hash
	var keys = getQueryHashKeys(window.location.hash);
	keys['page'] = keys['page'] || 'users'; // Default to users page
	if (keys['page'] === 'posts' || keys['page'] === 'users') {
		$('.header .menu div#menu_' + keys['page'])
			.addClass('active')
			.click();
	} else {
		userTab(keys['page']);
	}
}

function getQueryHashKeys() {
	var a = window.location.hash.substring(1).split('&');
	if (a == "") return {};
	var b = {};
	for (var i = 0; i < a.length; ++i) {
		var p=a[i].split('=');
		if (p.length != 2) continue;
		b[p[0]] = decodeURIComponent(p[1].replace(/\+/g, " "));
	}
	return b;
}

function handleResponse(json) {
	var $table, posts;
	if ( 'user' in json ) {
		handlePosts( $('table#user_' + json.user), json );
	}
	else if ( 'posts' in json ) {
		handlePosts( $('table#posts'), json );
	}
	else if ( 'users' in json ) {
		handleUsers( $('table#users'), json );
	}
	scrollHandler();
}

function handlePosts($table, json) {
	$table.find('tr.loading td img')
		.slideUp(500, function() {
			$table.find('tr.loading tr').remove()
		});

	if ($table.attr('id').indexOf('user_') === 0 &&
			json.post_count !== undefined &&
			json.image_count !== undefined) {
		var $tr = $table.find('tr.userinfo');
		$tr.find('#post_count')
			.html('posts: ' + json.post_count);
		$tr.find('#image_count')
			.html('images: ' + json.image_count);
		$tr.find('#video_count')
			.html('videos: ' + json.video_count);
		if (json.video_count == 0) {
			$tr.find('#zip_no_videos').hide();
		} else {
			$tr.find('#zip_no_videos').show();
		}
		var date = new Date(json.updated * 1000);
		var updated = date.toLocaleDateString() +
			//' @ ' + date.toLocaleTimeString() + 
			' (' + timestampToHR(json.updated) + ')';
		date = new Date(json.created * 1000);
		var created = date.toLocaleDateString() +
			//' @ ' + date.toLocaleTimeString() + 
			' (' + timestampToHR(json.created) + ')';
		$tr.find('#updated')
			.html('updated: ' + updated);
		$tr.find('#created')
			.html('created: ' + created);
	}
	$table.append( $('<tr/>') );
	var index = 0;
	for (var i in json.posts) {
		var post = json.posts[i];
		index += addPost($table, index, post);
	}
	$table.data('has_more',   (json.posts.length == POSTS_PER_REQUEST) );
	$table.data('next_index', $table.data('next_index') + json.posts.length);
	$table.data('loading',    false);
}

function handleUsers($table, json) {
	$table.find('tr.loading td img')
		.slideUp(500, function() {
			$table.find('tr.loading tr').remove()
		});
	$table.append( $('<tr/>') );
	for (var i in json.users) {
		addUser($table, i, json.users[i]);
	}
	$table.data('has_more',   (json.users.length == USERS_PER_REQUEST) );
	$table.data('next_index', $table.data('next_index') + json.users.length);
	$table.data('loading',    false);
}

function loadMore() {
	var $table = $('table').filter(function() {
		return $(this).css('display') !== 'none' && $(this).attr('class') === 'posts';
	});
	if ( $table.data('loading'))  { return; }
	if (!$table.data('has_more')) { return; }
	var url = window.location.pathname + 'api.cgi';
	var params = $table.data('next_params');
	var hash = {
		'page'  : $table.attr('id').replace(/^user_/, ''),
		'sort'  : params['sort'],
		'order' : params['order']
	};
	window.location.hash = $.param(hash);
	params['start'] = $table.data('next_index');
	url += '?' + $.param(params);
	$table.data('loading', true);
	var $tr = $('<tr/>')
		.addClass('loading')
		.appendTo($table);
	var $td = $('<td/>')
		.addClass('loading')
		.attr('colspan', POST_COLUMNS)
		.append(
			$('<img/>')
				.attr('src', './ui/spinner.gif')
				.addClass('spin_big')
		)
		.appendTo($tr);
	setTimeout(function() {
		$.getJSON(url)
			.fail(function(data) {
				statusbar('failed to load ' + url + ': ' + String(data));
			})
			.done(handleResponse);
	}, 500);
}

function addUser($table, index, user) {
	var $tr = $('<tr/>')
		.addClass('user')
		.appendTo( $table )
		.click(function() {
			userTab(user.user);
		});
	var $td = $('<td/>')
		.addClass('user')
		.appendTo($tr);
	var $div = $('<div/>').addClass('user');
	$div.append(
			$('<div/>')
				.html(user.user)
				.addClass('username')
		);
	$div.append(
			$('<div/>')
				.html(user.post_n + ' posts')
				.addClass('userinfo')
		);
	$div.append(
			$('<div/>')
				.html(user.image_n + ' images')
				.addClass('userinfo')
		);
	if (user.video_n > 0) {
		$div.append(
				$('<div/>')
					.html(user.video_n + ' videos')
					.addClass('userinfo')
			);
	}
	$div.append(
			$('<div/>')
				.html('last updated ' + timestampToHR(user.updated) + ' ago')
				.addClass('userinfo')
		);
	$div.append(
			$('<div/>')
				.html('started ' + timestampToHR(user.created) + ' ago')
				.addClass('userinfo')
		);
	$div.appendTo($td);
	for (var i in user.images) {
		var $imgtd = $('<td/>')
			.addClass('user')
			.appendTo($tr);
		$('<img/>')
			.addClass('post')
			.attr('src', user.images[i].thumb.substr(1))
			.appendTo($imgtd);
	}
}

function addPost($table, index, post) {
	if (index != 0 && index % (POST_COLUMNS) == 0) {
		$('<tr/>').appendTo( $table );
	}
	var $div = $('<td/>')
		.addClass('post')
		.click(function() {
			postClickHandler($(this), post);
		})
		.appendTo( $table.find('tr:last') );

	if (post.images.length > 0 && post.images[0].thumb !== null) {
		// Imagecount
		var $imgcount = $('<span/>')
			.addClass('info')
			.css({
				'position': 'absolute',
			})
			.html(post.images.length + ' image' + (post.images.length == 1 ? '' : 's'))
			.hide()
			.appendTo($div);
		// Permalink
		$imgcount.append( $('<span/>').html(' | ') );
		var $permalink = $('<a/>')
			.addClass('info')
			.attr('href', post.permalink)
			.attr('target', '_BLANK' + post.id)
			.click(function(e) {
				e.stopPropagation();
			})
			.html('post')
			.appendTo($imgcount);
		// Thumbnail
		var $img = $('<img/>')
			.addClass('post')
			.attr('src', post.images[0].thumb.substr(1))
			.appendTo($div);
		if (post.images.length > 1) {
			var d = Math.max(post.images.length / 2, 6);
			$img.css('box-shadow', d + 'px ' + d + 'px 1px rgba(0, 0, 0, 0.5)');
		}
		$div
			.hover(function() {
				$imgcount
					.css({
						'position' : 'absolute',
						'top' : $img.offset().top + $img.height() - $imgcount.height(),
						'left' : $img.position().left + ($img.width() / 2) - ($imgcount.width() / 2),
						'background-color' : '#909',
						'opacity': 0.8,
						'padding': '3px'
					})
					.stop().fadeIn(500);
			}, function() {
				$imgcount.stop().fadeOut(500);
			});
	}

	$div.append( $('<br/>') );
	// Author
	if (post.author !== undefined) {
		$('<a/>')
			.addClass('author')
			.attr('href', '#user=' + post.author)
			.html(post.author)
			.click(function(e) {
				e.stopPropagation();
				userTab(post.author);
			})
			.appendTo($div);
		$div.append( $('<br/>') );
	}
	return 1;
}

function postClickHandler($td, post) {
	// Mark post as selected
	if ($td.hasClass('selected')) {
		// Selected post was clicked
		$('td.selected').removeClass('selected');
		$('#expandrow td img').stop().slideUp(500);
		$('#expandrow').stop().hide(500, function() { $(this).remove() });
		return;
	}
	$('td.selected').removeClass('selected');
	$td.addClass('selected');
	// Expand
	$('#expandrow')
		.stop()
		.removeAttr('id')
		.remove();
	var $etr = $('<tr/>')
		.attr('id', 'expandrow')
		.hide()
		.insertAfter($td.closest('tr'))
		.show(500);
	var $etd = $('<td/>')
		.addClass('expanded')
		.attr('colspan', POST_COLUMNS)
		.remove('img')
		.appendTo($etr)
		.hide()
		.fadeIn(500);
	var $infodiv = $('<div/>')
		.appendTo($etd);
	if (post.permalink !== undefined) {
		$('<a/>')
			.addClass('post-title')
			.attr('href', post.permalink)
			.attr('target', '_BLANK_' + post.id)
			.html(post.title)
			.appendTo($infodiv);
	}
	if (post.url !== undefined && post.url !== null) {
		$('<a/>')
			.addClass('post-url')
			.attr('href', post.url)
			.html(post.url)
			.appendTo($infodiv);
	}
	var $countdiv = $('<div/>')
		.attr('id', 'expandcount')
		.html('1 of ' + post.images.length)
		.hide()
		.appendTo($etd);
	if (post.images.length > 1) {
		$countdiv.show();
	}
	// Image
	var width = post.images[0].width,
			height = post.images[0].height
			maxw = screen.width * 0.95,
			maxh = screen.height - 400,
			ratio = 1.0;
	if (maxw / width < ratio) {
		ratio = maxw / width;
	}
	if (maxh / height < ratio) {
		ratio = maxh / height;
	}
	width *= ratio;
	height *= ratio;
	var $img = $('<img/>')
		.addClass('expanded')
		.data('images', post.images)
		.data('index', 0)
		.attr('src', post.images[0].path.substr(1))
		.css({
			'width' : width,
			'height' : height,
		})
		.appendTo($etd)
		.click(function() {
			var images = $(this).data('images');
			if (images.length == 0) { return };
			var index = $(this).data('index');
			index += 1;
			if (index >= images.length) index = 0;
			var width = images[index].width,
					height = images[index].height
					maxw = screen.width * 0.95,
					maxh = screen.height - $td.height() - 100,
					ratio = 1.0;
			if (maxw / width < ratio) {
				ratio = maxw / width;
			}
			if (maxh / height < ratio) {
				ratio = maxh / height;
			}
			width *= ratio;
			height *= ratio;
			$(this)
				.attr('src', images[index].path.substr(1))
				.data('index', index)
				.css({
					'width': width,
					'height': height
				});
			$('#expandcount').html((index + 1) + ' of ' + images.length);
		})
		.hide()
		.slideDown(500);
	// Scroll
	$('html,body')
		.animate({
			'scrollTop': $('#expandrow').prev().offset().top,
		}, 500);
}

function userTab(user) {
	$('#tab_' + user).hide().remove();
	var $div = 
		$('<div/>')
			.html(user)
			.attr('id', 'menu_' + user)
			.click(function() {
				tabClickHandler($(this))
			});
	$('<li/>')
		.attr('id', 'tab_' + user)
		.append($div)
		.appendTo($('#menubar'));
	$div.click();
}

function tabClickHandler($element) {
	// Set up URL and parameters for request
	var url = window.location.pathname + 'api.cgi';
	// Set active tab
	$('.header .menu div').removeClass('active');
	$element.addClass('active');
	// Hide existing table
	$('table').filter(function() {
		return $(this).css('display') !== 'none';
	}).hide().css('display', 'none');

	// Query parameters
	var params = {};
	var keys = getQueryHashKeys();

	var defaultSort = 'ups';
	if ($element.html() === 'users') {
		defaultSort = 'updated';
	}
	params['sort']  = keys['sort']  || defaultSort;
	params['order'] = keys['order'] || 'desc';

	// Get table/params depending on type of content
	var $table;
	if ($element.html() === 'posts') {
		// List of posts from all users
		$table = $('table#posts');
		params['method'] = 'get_posts';
		params['count'] = POSTS_PER_REQUEST;
		addSortRow($table, ['ups', 'created', 'username']);
		if ('page' in keys && keys['page'] !== 'posts') {
			params['sort']  = 'ups';
			params['order'] = 'desc';
		}
	}
	else if ($element.html() === 'users') {
		// List of all users
		$table = $('table#users');
		params['method'] = 'get_users';
		params['count']  = USERS_PER_REQUEST;
		// Insert sort options if needed
		addSortRow($table, ['updated', 'username', 'created']);
		if ('page' in keys && keys['page'] !== 'users') {
			params['sort']  = 'updated';
			params['order'] = 'desc';
		}
	}
	else {
		// List of posts for specific user
		var user = $element.html();
		$table = $('table#user_' + user);
		if ( $table.size() == 0 ) {
			$table = $('<table/>')
				.attr('id', 'user_' + user)
				.addClass('posts')
				.insertAfter( $('table#users') );

			var $tr = $('<tr/>')
				.addClass('userinfo')
				.appendTo($table);
			var $td = $('<td>')
				.addClass('userinfo')
				.attr('colspan', POST_COLUMNS)
				.html('')
				.appendTo($tr);
			var $infotable = $('<table/>')
				.css('width', '100%')
				.appendTo($td);
			var $area = $('<tr/>')
				.appendTo( $infotable );
			$('<span/>')
				.attr('id', 'post_count')
				.addClass('userinfo')
				.html('posts: xxx')
				.appendTo(
					$('<td/>')
						.css({'text-align': 'right', 'width': '30%'})
						.appendTo($area)
					);
			$('<span/>')
				.attr('id', 'created')
				.addClass('userinfo')
				.html('created: xx/xx/xxxx (x ...)')
				.appendTo(
					$('<td/>')
						.css({'text-align': 'left', 'width': '30%'})
						.appendTo($area)
					);
			$area = $('<tr/>')
				.appendTo( $infotable );
			$('<span/>')
				.appendTo(
					$('<td/>')
						.css({'text-align': 'left', 'width': '30%'})
						.appendTo($area)
					);
			$('<span/>')
				.attr('id', 'updated')
				.addClass('userinfo')
				.html('updated: xx/xx/xxxx (x ...)')
				.appendTo(
					$('<td/>')
						.css({'text-align': 'left', 'width': '30%'})
						.appendTo($area)
					);
			$area = $('<tr/>')
				.appendTo( $infotable );
			$('<span/>')
				.attr('id', 'image_count')
				.addClass('userinfo')
				.html('images: xxx')
				.appendTo(
					$('<td/>')
						.css({'text-align': 'right', 'width': '30%'})
						.appendTo($area)
					);
			$('<span/>')
				.attr('id', 'video_count')
				.addClass('userinfo')
				.html('videos: xxx')
				.appendTo(
					$('<td/>')
						.css({'text-align': 'left', 'width': '30%'})
						.appendTo($area)
					);
			$area = $('<tr/>')
				.appendTo( $infotable );
			$('<span/>')
				.html('download')
				.addClass('zip')
				.data('user', user)
				.click(function() {
					getZip($(this), $(this).data('user'), true);
				})
				.appendTo(
					$('<td/>')
						.css({'text-align': 'right', 'width': '30%'})
						.appendTo($area)
					);
			$('<span/>')
				.attr('id', 'zip_no_videos')
				.html('download (no videos)')
				.addClass('zip')
				.data('user', user)
				.click(function() {
					getZip($(this), $(this).data('user'), false);
				})
				.appendTo(
					$('<td/>')
						.css({'text-align': 'left', 'width': '30%'})
						.appendTo($area)
					);
		}
		params['user']   = user;
		params['method'] = 'get_user';
		params['count']  = POSTS_PER_REQUEST;
		addSortRow($table, ['ups', 'created']);
		if ('page' in keys && keys['page'] !== user) {
			params['sort']  = 'ups';
			params['order'] = 'desc';
		}
	}
	$('#' + $table.attr('id') + '_sort_' + params['sort']).addClass('sort_active');
	$('#' + $table.attr('id') + '_order_' + params['order']).addClass('order_active');

	$.extend(params, $table.data('next_params'));
	
	// Store query parameters in table
	$table.data('next_params', params);
	$table.data('loading', false);
	$table.data('has_more', true);
	if ( $table.data('next_index') === undefined) {
		$table.data('next_index', 0); // Start at 0
	}
	$table.show(500, function() {
		scrollHandler();
	});

	var hash = {
		'page'  : $element.html(),
		'sort'  : params['sort'],
		'order' : params['order']
	};
	window.location.hash = $.param(hash);
}

function getZip($button, user, includeVideos, album) {
	// Change button to show loading
	$button
		.addClass('zip-noclick')
		.unbind('click') // So they can't request more than 1 zip
		.html('zipping...')
		.append(
			$('<img/>')
				.addClass('spin_small')
				.attr('src', './ui/spinner.gif')
		);
	// Construct request
	var params = {
		'method' : 'get_zip',
		'user' : user,
		'include_videos' : includeVideos
	};
	var url = window.location.pathname + 'api.cgi?' + $.param(params);
	$.getJSON(url)
		.fail(function() {
			statusbar('failed to get zip');
		})
		.done(function(data) {
			if ('error' in data) {
				statusbar(data.error);
				$button.html('zip failed')
				return;
			}
			else if ('zip' in data) {
				var title = ''
				if (data.images > 0) {
					title += ' ' + data.images + ' image' + (data.images == 1 ? '' : 's');
				} else if (data.videos > 0) {
					title += ' ' + data.videos + ' video' + (data.videos == 1 ? '' : 's');
				} else if (data.audios > 0) {
					title += ' ' + data.audios + ' audio' + (data.audios == 1 ? '' : 's');
				}
				$button
					.empty()
					.removeClass('zip-noclick')
					.click(function() {
						window.location.href = data.zip;
					})
					.attr('title', 'size: ' + bytesToHR(data.size) + ', ' + title)
					.html(data.zip.substring(data.zip.lastIndexOf('/')+1))
					.hide()
					.fadeIn(500);
				//window.open(data.zip);
			}
			else {
				statusbar('unexpected response: ' + JSON.stringify(data));
				$button.html('zip failed')
			}
				
		});
}

function setupSearch() {
	$('input#search')
		.css({
			'width': '60px',
			'opacity' : '0.5'
		})
		.focusin(function() {
			if ($(this).val() === 'search') {
				$(this).val('')
			}
			$(this)
				.stop()
				.animate(
					{
						'width': '125px',
						'opacity': '1',
					}, 
					500);
			$(this).keyup();
		})
		.focusout(function() {
			if ($(this).val() === '') {
				$(this).val('search')
			}
			$(this)
				.stop()
				.animate(
					{
						'width': '60px',
						'opacity': '0.5'
					}, 
					500);
			$('#search_box')
				.slideUp(
					200,
					function() {
						$(this).remove()
					}
				);
		})
		.data('timeout', null)
		.keyup(function(k) {
			if (k.keyCode != 13) {
				return;
			}
			if (!$('input#search').is(':focus')) {
				return;
			}
			$('#search_box').hide().remove();
			var $div = $('<div/>')
				.attr('id', 'search_box')
				.addClass('search')
				.hide()
				.css({
					'top'  : $('#menubar').position().top + $('#menubar').height() - 10,
					'left' : $('input#search').position().left + 10
				})
				.append(
					$('<img/>')
						.attr('src', './images/spinner.gif')
						.css({
							'width'  : '25px',
							'height' : '25px'
						})
				)
				.appendTo( $('body') )
				.slideDown(200);
			clearTimeout($(this).data('timeout'));
			var to = setTimeout(function() {
				searchText( $('input#search').val() );
			}, 500);
			$(this).data('timeout', to);
		});
}

function searchText(text) {
	var url = window.location.pathname + 'api.cgi';
	url += '?method=search_user';
	url += '&user=' + text;
	$.getJSON(url)
		.fail(function(data) {
			statusbar('search failed, server error');
		})
		.done(function(data) {
			if (!$('input#search').is(':focus')) {
				return;
			}
			if (!'users' in data) {
				return;
			}
			$('#search_box').hide().remove();
			var $div = $('<div/>')
				.attr('id', 'search_box')
				.addClass('search')
				.css({
					'top'  : $('#menubar').position().top + $('#menubar').height() - 10,
					'left' : $('input#search').position().left + 10
				})
				.appendTo( $('body') );

			var not_in_users = true;
			for (var i in data.users) {
				if (data.users[i].toLowerCase() === text.toLowerCase()) {
					not_in_users = false;
				}
				$('<div/>')
					.addClass('search_result')
					.html(data.users[i])
					.click(function(e) {
						e.stopPropagation()
						userTab( $(this).html() );
					})
					.appendTo($div);
			}
			if (not_in_users) {
				$('<div/>')
					.addClass('search_result')
					.click(function() {
						var url = window.location.pathname + 'api.cgi';
						url += '?method=add_user';
						url += '&user=' + text;
						$.getJSON(url)
							.fail(function(data) {
								statusbar('failed to add user, server error');
							})
							.done(function(data) {
								if ('error' in data) {
									statusbar(data.error);
								} else {
									statusbar('undefined error when adding user "' + text + '"');
								}
							});
					})
					.html('+add user "' + text + '"')
					.appendTo($div);
			}
			$div
				.show()
				.slideDown(500);
		});
}

function statusbar(text, timeout) {
	if (timeout === undefined) timeout = 2000;
	$('div#statusbar')
		.stop()
		.hide()
		.html(text)
		.slideDown(500,
			function() {
				setTimeout( function() {
					$('div#statusbar').slideUp(500);
				}, timeout);
			});
}

function addSortRow($table, sorts) {
	if ( $table.find('tr.sort').size() > 0 ) {
		return;
	}
	$table.find('tr.sort').remove();
	var $tr = $('<tr/>').addClass('sort');
	var $td = $('<td/>')
		.attr('colspan', POST_COLUMNS)
		.addClass('sort')
		.appendTo($tr)
		.append( $('<span/>').html('sort:') );
	for (var i in sorts) { // username, created, updated
		$td.append(createSortButton($table, 'sort', sorts[i]));
	}
	$td
		.append( $('<div/>').css('height', '10px') )
		.append( $('<span/>').html('order:') )
		.append(createSortButton($table, 'order', 'asc &#9650;', 'asc'))
		.append(createSortButton($table, 'order', 'desc &#9660;', 'desc'));
	$table.append($tr);
}

function createSortButton($table, type, label, sorttype) {
	if (sorttype === undefined) {
		sorttype = label;
	}
	return $('<span/>')
		.addClass('sort')
		.attr('id', $table.attr('id') + '_' + type + '_' + sorttype)
		.html(label)
		.click(function() {
			// Set params
			$('span.sort').removeClass(type + '_active');
			$(this).addClass(type + '_active');
			$table.data('next_params')[type] = sorttype;
			$table.data('next_index', 0);
			// Remove existing content
			$table.find('tr:not(.sort)').remove();
			// Refresh with new params
			scrollHandler();
		});
}

function timestampToHR(tstamp) {
	var old = new Date(tstamp * 1000),
			now = new Date(),
			diff = (now - old) / 1000,
			units = {
				31536000: 'year',
				2592000 : 'month',
				86400   : 'day',
				3600    : 'hour',
				60      : 'min',
				1       : 'sec'
			};
	for (var unit in units) {
		if (diff > unit) {
			var hr = Math.floor(diff / unit);
			return hr + ' ' + units[unit] + (hr == 1 ? '' : 's');
		}
	}
	return '? sec';
}

function bytesToHR(bytes) {
	var units = ['g', 'm', 'k', ''];
	var chunk = 1024 * 1024 * 1024;
	for (var unit in units) {
		if (bytes >= chunk) {
			return (bytes / chunk).toFixed(2) + units[unit] + 'b';
		}
		chunk /= 1024;
	}
	return '?b';
}

function scrollHandler() {
	var page     = $(document).height(); // Height of document
	var viewport = $(window).height();   // Height of viewing window
	var scroll   = $(document).scrollTop() || window.pageYOffset; // Scroll position (top)
	var remain = page - (viewport + scroll);
	if (viewport > page || // Viewport is bigger than entire page
	    remain < 300) {    // User has scrolled down far enough
		loadMore();
	}
}

$(document).ready(init);
$(window).scroll(scrollHandler);
