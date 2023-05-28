#!/bin/zsh

rm "./source/amethyst/versions/Amethyst-$1.html"

for VERSION in "$@"
do
    curl https://github.com/ianyh/Amethyst/releases/tag/v${VERSION} | pup "div.Box-body div:not(.markdown-body) h1" >> source/amethyst/versions/Amethyst-$1.html
	curl https://github.com/ianyh/Amethyst/releases/tag/v${VERSION} | pup "div.markdown-body" >> source/amethyst/versions/Amethyst-$1.html
done
