const metalsmith = require('metalsmith');
const branch = require('metalsmith-branch');
const collections = require('metalsmith-collections');
const excerpts = require('metalsmith-excerpts');
const markdown = require('metalsmith-markdown');
const permalinks = require('metalsmith-permalinks');
const sass = require('metalsmith-sass');
const serve = require('metalsmith-serve');
const templates = require('metalsmith-templates');
const watch = require('metalsmith-watch');
const moment = require('moment');

metalsmith(__dirname)
	.metadata({
		site: {
			title: 'ianyh',
			url: 'https://ianyh.com'
		}
	})
	.source('./source')
	.destination('./build')
	.use(markdown())
	.use(excerpts())
	.use(collections({
		posts: {
			pattern: 'posts/**.html',
			sortBy: 'publishDate',
			reverse: true
		}
	}))
	.use(branch('posts/**.html')
		.use(permalinks({
			pattern: 'posts/:title',
			relative: false
		}))
	)
	.use(branch('!posts/**.html')
		.use(branch('!index.md').use(permalinks({
			relative: false
		})))
	)
	.use(sass({
		includePaths: [
			'./styles'
		]
	}))
	.use(templates({
		engine: 'jade',
		moment: moment
	}))
	.use(serve({
		port: 8080,
		verbose: true
	}))
	.use(watch({
		pattern: '**/*',
		livereload: true
	}))
	.build(function build(err) {
		if (err) {
			console.log(err);
		} else {
			console.log('Site build complete!');
		}
	});
