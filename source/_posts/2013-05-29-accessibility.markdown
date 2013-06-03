---
layout: post
title: "Accessibility, Windows, and Spaces in OS X"
date: 2013-05-29 20:50
comments: true
categories: 
published: false
---

A couple weeks ago I decided to sit down and write a tiling window manager. As a
first and second pass it pretty much works, though there's definitely room for
improvement. I'm calling it [Amethyst](https://github.com/ianyh/Amethyst). (It's
a kind of quartz, you see. Get it? _Get it_?)

The first pass dealt with multiple screens fairly well as I was implementing it
at a desk with multiple screens and managing windows across screen is a simple
matter of position. It wasn't until I started trying it out on my laptop that I
realized that Spaces support was fairly key. There's just not enough room on
this 13" screen. I spent a long time digging into moving windows between spaces
and have some insights I couldn't find anywhere else and I thought I'd share
them here.

Spaces API
==========

It used to be the case that there was a public API for moving windows between
spaces. They went private in 10.7, I think. There's a couple projects around
that utilize the private APIs, but I didn't want to go that route. For one thing
it might be nice to toss something into the AppStore, but it's mostly a
stability problem in that I don't want to have to go back and entirely
reimplement parts of the code due to radically shifting private APIs.

In my searching I dug into a variety of possible paths. I eventually came upon a
fascinating tidbit of information.

> If the mouse has hold of a window, switching to a Space via Mission Control
> will take the window to that Space.

Intriguing! You can test it out if you like. Works like a charm when you do it
manually. So how do we do it programmatically? Well, we manually post keyboard
and mouse events!

CGEvents
========

A quick overview of how `CGEvent` works. My use of it is mostly centered around
the following method:

```objective-c
void CGEventPost(CGEventTapLocation tap, CGEventRef event)
```

This allows you to post events directly to the window server. Great. So that
should let us post mouse events and keyboard events. So let's take a look at the
parameters.

The first is the tap location, of which there are three possible values:

```objective-c
enum _CGEventTapLocation {
   kCGHIDEventTap = 0,
   kCGSessionEventTap,
   kCGAnnotatedSessionEventTap
};
```

`kCGHIDEventTap` is the one we want. From the documentation:

> Specifies that an event tap is placed at the point where HID system events
> enter the window server.

`kCGSessionEventTap` includes remote control events and stuff, and
`kCGAnnotatedSessionEventTap` is for sending events to specific applications.

The second parameter is a `CGEventRef`, which describes things like keyboard
modifier flags, mouse button, mouse state, mouse position, keyboard key codes,
etc. There are a variety of methods that can be used to create `CGEvent`
objects. The two we care about are `CGEventCreateMouseEvent` and
`CGEventCreateKeyboardEvent`.

CGEventCreateMouseEvent
-----------------------

```objective-c
CGEventRef CGEventCreateMouseEvent(CGEventSourceRef source, CGEventType mouseType, CGPoint mouseCursorPosition, CGMouseButton mouseButton);
```

As the name implies this method is used to create mouse events. `source` is
basically meaningless for our purposes as it used for generating new events from
existing ones. `mouseCursorPosition` is pretty straightforward. It's the the
point on the screen that the mouse event should happen at.

There are a bunch of `CGEventType` values, which themselves are just proxies for
values buried deep in the HID system. The ones we care about for mouse events
are:

```objective-c
enum {
  ...
  kCGEventLeftMouseDown = NX_LMOUSEDOWN,
  kCGEventLeftMouseUp = NX_LMOUSEUP,
  kCGEventMouseMoved = NX_MOUSEMOVED,
  ...
}
```

There are a couple `CGMouseButton` values as well:

```objective-c
enum {
  kCGMouseButtonLeft = 0,
  kCGMouseButtonRight = 1,
  kCGMouseButtonCenter = 2
};
```

To simulate a standard tap we just want `kCGMouseButtonLeft`. To actually
simulate a tap we can do something like

```objective-c
CGPoint point = { .x = 0, .y = 0 };
CGEventRef mouseMoveEvent = CGEventCreateMouseEvent(NULL, kCGEventMouseMoved, point, kCGMouseButtonLeft);
CGEventRef mouseDownEvent = CGEventCreateMouseEvent(NULL, kCGEventLeftMouseDown, point, kCGMouseButtonLeft);
CGEventRef mouseUpEvent = CGEventCreateMouseEvent(NULL, kCGEventLeftMouseUp, point, kCGMouseButtonLeft);

CGEventPost(mouseMoveEvent);
CGEventPost(mouseDownEvent);
CGEventPost(mouseUpEvent);

CFRelease(mouseMoveEvent);
CFRelease(mouseDownEvent);
CFRelease(mouseUpEvent);
```

to simulate a tap at (0, 0). Cool. Let's look at keyboard events.

CGEventCreateKeyboardEvent
--------------------------

```objective-c
CGEventRef CGEventCreateKeyboardEvent(CGEventSourceRef source, CGKeyCode virtualKey, bool keyDown);
```