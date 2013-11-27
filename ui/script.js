var POST_COLUMNS = 5;
var POSTS_PER_REQUEST = 10;

function init() {
	setupMenu();
	setupSearch();
	// Click header to load images
	$('.header .menu div:first').click();
}

function handlePosts(json) {
	if (!'posts' in json) {
		throw new Error('posts not found in JSON');
	}
	$('table#posts').append($('<tr/>'));
	var index = 0;
	for (var i in json.posts) {
		var post = json.posts[i];
		index += addPost(index, post);
	}
	if (json.posts.length != POSTS_PER_REQUEST) {
		$('body').data('has_more', false);
	} else {
		$('body').data('has_more', true);
	}
	var this_index = $('body').data('next_index');
	$('body').data('next_index', this_index + json.posts.length);
	$('body').data('loading', false);
	scrollHandler();
}

function loadMore() {
	if ($('body').data('loading')) {
		// Already loading more
		return;
	} else if (!$('body').data('has_more')) {
		// No more to load
		return;
	}
	var url = window.location.pathname + 'api.cgi';
	var params = $('body').data('next_params');
	var index  = $('body').data('next_index');
	params['start'] = index;
	url += '?' + $.param(params);
	$('body').data('loading', true);
	// TODO display loading message
	setTimeout(function() {
		$.getJSON(url)
			.fail(function() {
				// TODO handle failure
			})
			.done(handlePosts);
	}, 500);
}

function addPost(index, post) {
	if (post.images.length == 0) {
		console.log("No images for post " + post.id);
		return 0;
	}
	if (index != 0 && index % (POST_COLUMNS) == 0) {
		$('<tr/>').appendTo('table#posts');
	}
	var $div = $('<td/>')
		.addClass('post')
		.data('post', post)
		.click(function() {
			// Select
			$('td.selected').removeClass('selected');
			$(this).addClass('selected');
			// Expand
			$('#expandrow')
				.stop()
				.removeAttr('id')
				.remove();
			var $etr = $('<tr/>')
				.attr('id', 'expandrow')
				.hide()
				.insertAfter($(this).closest('tr'))
				.show(500);
			var $etd = $('<td/>')
				.addClass('expanded')
				.attr('colspan', POST_COLUMNS)
				.appendTo($etr);
			var $countdiv = $('<div/>')
				.attr('id', 'expandcount')
				.html('1 of ' + post.images.length)
				.appendTo($etd);
			if (post.images.length == 1) {
				$countdiv.hide();
			} else {
				$countdiv.show();
			}
			var $img = $('<img/>')
				.addClass('expanded')
				.data('images', post.images)
				.data('index', 0)
				.attr('src', post.images[0].path.substr(1))
				.css({
					'max-width': ($('body').innerWidth()-40) + 'px',
				})
				.appendTo($etd)
				.click(function() {
					var index = $(this).data('index');
					var images = $(this).data('images');
					index += 1;
					if (index >= images.length) index = 0;
					$(this)
						.attr('src', images[index].path.substr(1))
						.data('index', index);
					$('#expandcount').html((index + 1) + ' of ' + images.length);
				});
			// Scroll
			$('html,body')
				.animate({
					'scrollTop': $('#expandrow').prev().offset().top,
				}, 500);
		})

	// Thumbnail
	var $img = $('<img/>')
		.addClass('post')
		.attr('src', post.images[0].thumb.substr(1))
		.appendTo($div);

	$div.append( $('<br/>') );
	// Author
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
	// Title
	$('<span/>')
		.addClass('info')
		.html(post.images.length + ' image' + (post.images.length == 1 ? '' : 's') + ' | ')
		.appendTo($div);
	$('<a/>')
		.addClass('info')
		.attr('href', post.permalink)
		.attr('target', '_BLANK' + post.id)
		.click(function(e) {
			e.stopPropagation();
		})
		.html('post')
		.appendTo($div);
	$('table#posts tr:last')
		.append($div);
	return 1;
}

function userTab(user) {
	$('#' + user).hide().remove();
	$('<li/>')
		.attr('id', user)
		.append(
			$('<div/>')
				.html(user)
				.click(function() { tabClickHandler($(this)) })
				.click()
		)
		.appendTo($('#menubar'));
}

function setupMenu() {
	$('.header .menu div:first').addClass('active');
	$('.header .menu div').click(function() {
		tabClickHandler($(this));
	});
}

function tabClickHandler($element) {
	$('table#posts tr').hide().remove();
	$('table#posts').empty();
	$('.header .menu div').removeClass('active');
	// TODO insert row for sorting
	// TODO insert row for user info (download, get URLs, karma, created, updated, etc)
	$element.addClass('active');
	var url = window.location.pathname + 'api.cgi';
	var params = {
		'method' : 'get_posts',
		'sort'   : 'ups',
		'count'  : POSTS_PER_REQUEST
	};
	if ($element.html() === 'gonewilder') {
		// Main header
		window.location.hash = '';
	} else {
		// Not the main header
		params['user'] = $element.html();
		window.location.hash = 'user=' + $element.html();
	}
	$('body').data('next_params', params);
	$('body').data('next_index', 0);
	url += '?' + $.param(params);
	$.getJSON(url)
		.fail(function(data) {
			// TODO failure message
		})
		.done(handlePosts);
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
	url += '?method=search';
	url += '&search=user:' + text;
	$.getJSON(url)
		.fail(function(data) {
			// TODO failure handling
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

			for (var i in data.users) {
				$('<div/>')
					.addClass('search_result')
					.html(data.users[i].user)
					.click(function(e) {
						e.stopPropagation()
						userTab( $(this).html() );
					})
					.appendTo($div);
			}
			if (data.users.length == 0) {
				$('<div/>')
					.addClass('search_result')
					.html('no results')
					.appendTo($div);
			}
			$div
				.show()
				.slideDown(500);
		});
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
