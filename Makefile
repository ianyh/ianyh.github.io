generate-notes:
	curl https://github.com/ianyh/Amethyst/releases/tag/v${VERSION} | pup "div.Box-body h1" > source/amethyst/versions/Amethyst-0.16.1.html
	curl https://github.com/ianyh/Amethyst/releases/tag/v${VERSION} | pup "div.markdown-body ul" >> source/amethyst/versions/Amethyst-0.16.1.html

generate:
	node build.js
	cp -r build/ deploy/
