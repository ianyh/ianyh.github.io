---
layout: post
title: "Amethyst 0.8"
date: 2013-08-19 16:43
comments: true
categories: 
---

Released Amethyst version 0.8 yesterday. It has some significant improvements to
stability as well as adding a few new features. There's a new column layout that
tiles windows into full height columns and the addition of floating windows. It
can be downloaded [here](http://ianyh.com/Amethyst/versions/Amethyst-0.8.zip) or
installed via [homebrew cask](https://github.com/phinze/homebrew-cask).

<!--more-->

Floating Windows
================

I had a request for floating windows and it's now in the app. `mod1 + t` can be
used to toggle whether a window is tiled or floating. A floating window will not
be tiled, but will be part of the focus chain.

Additionally, you can supply a list of bundle identifiers for which windows will
be floating by default. They can be specified by defining an array of bundle
identifier strings under the `floating` key in your `.amethyst` file. Any
application matching a bundle identifier in the list will have its windows float
by default, though use of `mod1 + t` will tile it if you want. I find this quite
useful for windows that Amethyst generally can't resize or position correctly
(e.g., Photoshop).
