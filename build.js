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
const highlight = require('metalsmith-code-highlight');

const bourbon = require('bourbon');
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
	.use(highlight({
		languages: []
	}))
	.use(excerpts())
	.use(collections({
		posts: {
			pattern: 'blog/**.html',
			sortBy: 'publishDate',
			reverse: true
		}
	}))
	.use(branch('blog/**.html')
		.use(permalinks({
			pattern: 'blog/:title',
			relative: false
		}))
	)
	.use(branch('!blog/**.html')
		.use(branch('!index.md').use(permalinks({
			relative: false
		})))
	)
	.use(sass({
		includePaths: [
			'./styles'
		].concat(bourbon.includePaths),
		outputStyle: 'expanded'
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
		paths: {
			'source/**/*': '**/*',
			'templates/**/*': '**/*',
			'styles/**/*': '**/*'
		},
		livereload: true
	}))
	.build(function build(err) {
		if (err) {
			console.log(err);
		} else {
			console.log('Site build complete!');
		}
	});