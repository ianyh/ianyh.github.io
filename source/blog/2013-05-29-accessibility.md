---
title: "Accessibility, Windows, and Spaces in OS X"
publishDate: 2013-05-29
author: Ian Ynda-Hummel
template: post.jade
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

<!--more-->

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

```objectivec
void CGEventPost(CGEventTapLocation tap, CGEventRef event)
```

This allows you to post events directly to the window server. Great. So that
should let us post mouse events and keyboard events. So let's take a look at the
parameters.

The first is the tap location, of which there are three possible values:

```objectivec
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

```objectivec
CGEventRef CGEventCreateMouseEvent(CGEventSourceRef source, CGEventType mouseType, CGPoint mouseCursorPosition, CGMouseButton mouseButton);
```

As the name implies this method is used to create mouse events. `source` is
basically meaningless for our purposes as it used for generating new events from
existing ones. `mouseCursorPosition` is pretty straightforward. It's the the
point on the screen that the mouse event should happen at.

There are a bunch of `CGEventType` values, which themselves are just proxies for
values buried deep in the HID system. The ones we care about for mouse events
are:

```objectivec
enum {
  ...
  kCGEventLeftMouseDown = NX_LMOUSEDOWN,
  kCGEventLeftMouseUp = NX_LMOUSEUP,
  kCGEventMouseMoved = NX_MOUSEMOVED,
  ...
}
```

There are a couple `CGMouseButton` values as well:

```objectivec
enum {
  kCGMouseButtonLeft = 0,
  kCGMouseButtonRight = 1,
  kCGMouseButtonCenter = 2
};
```

To simulate a standard tap we just want `kCGMouseButtonLeft`. To actually
simulate a tap we can do something like

```objectivec
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

```objectivec
CGEventRef CGEventCreateKeyboardEvent(CGEventSourceRef source, CGKeyCode virtualKey, bool keyDown);
```

`source` is about as useful here as it was for mouse events, and hopefully
`keyDown` is self explanatory. The important thing to note is that to perform a
keypress we actually need two events: one for `keyDown = true` followed by one
for `keyDown = false`.

`virtualKey` can probably take its values from a variety of places. I went with
the virtual keycodes defined in the Carbon framework. It's
`Carbon.framework/Frameworks/HIToolbox.framework/Events.h` if you want to look
them up. Repeating them all here isn't particularly useful.

So let's say we want to perform the standard keyboard shortcut for moving one
space to the right (^ + Right Arrow). We could do

```objectivec
CGEventRef keyboardDownEvent = CGEventCreateKeyboardEvent(NULL, kVK_RightArrow, true);
CGEventRef keyboardUpEvent = CGEventCreateKeyboardEvent(NULL, kVK_RightArrow, false);

CGEventPost(keyboardDownEvent);
CGEventPost(keyboardUpEvent);

CFRelease(keyboardDownEvent);
CFRelease(keyboardUpEvent);
```

But wait, what about the control key? Well, there's a method for that.

```objectivec
void CGEventSetFlags(CGEventRef event, CGEventFlags flags);
```

Where `flags` is some OR'd combination of possible flag values. The ones we care
about here are

```objectivec
enum {
  /* Device-independent modifier key bits. */
  kCGEventFlagMaskAlphaShift =          NX_ALPHASHIFTMASK,
  kCGEventFlagMaskShift =               NX_SHIFTMASK,
  kCGEventFlagMaskControl =             NX_CONTROLMASK,
  kCGEventFlagMaskAlternate =           NX_ALTERNATEMASK,
  kCGEventFlagMaskCommand =             NX_COMMANDMASK,
  ...
};
```

So to fix the keyboard event code from above.

```objectivec
CGEventRef keyboardDownEvent = CGEventCreateKeyboardEvent(NULL, kVK_RightArrow, true);
CGEventRef keyboardUpEvent = CGEventCreateKeyboardEvent(NULL, kVK_RightArrow, false);

CGEventSetFlags(keyboardDownEvent, kCGEventFlagMaskControl);

CGEventPost(keyboardDownEvent);
CGEventPost(keyboardUpEvent);

CFRelease(keyboardDownEvent);
CFRelease(keyboardUpEvent);
```

Putting It All Together
-----------------------

So let's say you have an accessibility reference to a window and want to move it
to a different space. There's an important question you need to answer first: at
what point do you move the mouse to grab the window? Conceptually the answer is
pretty straightforward. You move the mouse to the window's toolbar. In practice
there's a couple unintuitive gotchas.

My initial intuition for this was to take the min-y and mid-x of the window's
frame, so the cursor ends up in the middle of the window's toolbar. Should work
fine, should work with every window. But when I implemented that it would fail
for some windows, namely Xcode. As best I can tell the middle of Xcode's toolbar
as depicted below is grabbing mouse down events for something.

![toolbar](/images/2013-05-29-accessibility/xcode-toolbar.png)

Okay, so what other point on the x-axis do all windows have in common? That
little green zoom button!

But Wait, What About Modifiers?
-------------------------------

There is one more point to consider. We are going to be executing this operation
from an event handler triggered by a keyboard shortcut. Let's take an example
shortcut `ctrl + option + right arrow` for taking the currently focused window
and moving it one space right. You hit this keyboard shortcut and we go and
create events and post them. There's a gotcha here. `CGEvent` create methods
_start with the current modifiers unless otherwise specified_. Depending on the
timing we could accidentally create a `ctrl + click` event instead of just a
`click` event. Most windows don't care, but Xcode (why is it always Xcode?)
does. We need to thus make sure that we clear out any modifier flags on keyboard
and mouse events that we don't expect to have any modifiers.

The Final Method
----------------

To avoid unnecessary details of the accessibility API the following code uses an
`NSObject` wrapper.

```objectivec
AMAccessibilityElement *windowElement = [self window];
AMAccessibilityElement *zoomButtonElement = [windowElement elementForKey:kAXZoomButtonAttribute];
CGRect zoomButtonFrame = zoomButtonElement.frame;
CGRect windowFrame = windowElement.frame;

CGPoint mouseCursorPoint = { .x = CGRectGetMaxX(zoomButtonFrame) + 5.0, .y = windowFrame.origin.y + 5.0 };

CGEventRef mouseMoveEvent = CGEventCreateMouseEvent(NULL, kCGEventMouseMoved, mouseCursorPoint, kCGMouseButtonLeft);
CGEventRef mouseDownEvent = CGEventCreateMouseEvent(NULL, kCGEventLeftMouseDown, mouseCursorPoint, kCGMouseButtonLeft);
CGEventRef mouseUpEvent = CGEventCreateMouseEvent(NULL, kCGEventLeftMouseUp, mouseCursorPoint, kCGMouseButtonLeft);

CGEventRef keyboardDownEvent = CGEventCreateKeyboardEvent(NULL, kVK_RightArrow, true);
CGEventRef keyboardUpEvent = CGEventCreateKeyboardEvent(NULL, kVK_RightArrow, false);

CGEventSetFlags(mouseMoveEvent, 0);
CGEventSetFlags(mouseDownEvent, 0);
CGEventSetFlags(mouseUpEvent, 0);
CGEventSetFlags(keyboardDownEvent, kCGEventFlagMaskControl);
CGEventSetFlags(keyboardUpEvent, 0);

CGEventPost(kCGHIDEventTap, mouseMoveEvent);
CGEventPost(kCGHIDEventTap, mouseDownEvent);
CGEventPost(kCGHIDEventTap, keyboardDownEvent);
CGEventPost(kCGHIDEventTap, keyboardUpEvent);
CGEventPost(kCGHIDEventTap, mouseUpEvent);

CFRelease(mouseMoveEvent);
CFRelease(mouseDownEvent);
CFRelease(mouseUpEvent);
CFRelease(keyboardEvent);
CFRelease(keyboardEventUp);							
```
