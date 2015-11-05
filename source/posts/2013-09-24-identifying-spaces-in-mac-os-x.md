---
title: "Identifying Spaces in Mac OS X"
publishDate: 2013-09-24
author: Ian Ynda-Hummel
template: post.jade
---

I recently implemented a featured in [Amethyst](http://ianyh.com/amethyst/) that
allowed every space to have its own unique set of resources. In implementing
this feature I ran into a problem: how do you determine which space you're
currently on?

One might think that this would be a sensible piece of information to expose,
but alas and alack it is hidden behind private APIs. So what is a
tiling-window-management-inclined programmer to do? Dig into a bunch of weird
pieces of public information. The first being the preferences of spaces itself.

<!--more-->

Preferences on OS X
===================

The first piece of information to know is how preferences work. Here's a
lightning overview. You may be familiar with `NSUserDefaults`. It is used to
store application preferences. By default it accesses the application's
preferences, which are backed by a file in `~/Library/Preferences` named using
your application's bundle identifier. Amethyst, for example, has a file at
`~/Library/Preferences/com.amethyst.Amethyst.plist`. 

Additionally, `NSUserDefaults` has an interesting method
`-[NSUserDefaults addSuiteNamed:]`, which takes a single argument called
`suiteName`. From the docs

> The suiteName domain is similar to a bundle identifier string, but is not tied
> to a particular application or bundle. A suite can be used to hold preferences
> that are shared between multiple applications.

How does this help us? Well, you can look for yourself and note that
`~/Library/Preferences/com.apple.spaces.plist` exists. You can read that file
using the `defaults` command.

```bash
$ defaults read com.apple.spaces
```

There's a whole bunch of data. And if you try
`[[NSUserDefaults standardUserDefaults] addSuiteNamed:@"com.apple.spaces"]` you
will indeed have access to all of that data. Progress!

Spaces Preferences
==================

So let's dig into what's actually in the preferences. There's a list of spaces:

```objectivec
Spaces =                     (
   {
      id64 = 4;
      pid =                             (
         48173,
         218
      );
      type = 2;
      uuid = dashboard;
   },
   {
      id64 = 3;
      type = 0;
      uuid = "";
      wsid = 1;
   },
   {
      id64 = 5;
      type = 0;
      uuid = "B8E129CC-DDDF-44D9-A583-6DE0FB39319E";
   },
   {
      id64 = 7;
      type = 0;
      uuid = "21359712-DBFB-40AA-BAB5-87D1DDC6D442";
   },
   {
      id64 = 6;
      type = 0;
      uuid = "956AEFA7-387D-463D-A90B-341E2137644A";
   },
   {
      id64 = 8;
      type = 0;
      uuid = "599C0154-A9E1-4FD4-9489-54212240B3AE";
   }
)
```

Great. They've got uuids! We can use those as identifiers. And if we look
closely there seems to even be a specific preference for the current space!

```objectivec
"Current Space" =                     {
   id64 = 3;
   type = 0;
   uuid = "";
   wsid = 1;
};
```

Now just to confirm you can switch to a different space and read the defaults
again and get:

```objectivec
"Current Space" =                     {
   id64 = 3;
   type = 0;
   uuid = "";
   wsid = 1;
};
```

Wait. The `uuid` didn't change at all. What the hell? Okay, well, it's not going
to be that easy. So let's look at something else. There's a list of windows in
each space, that's promising.

Here's an excerpt of what it looks like on my machine right now for one of my
spaces:

```objectivec
{
   name = "";
   windows =                 (
      70,
      101,
      102,
      14747,
      48
   );
}
```

Okay, so we've got a name which seems to be the space's uuid and a list of
window numbers. That's useful. Maybe we can find the window numbers on the
current space and use that to match up to a space identifier. So let's take a
look at windows and window numbers.

Windows Of The Current Space
============================

It turns out there is a public API for accessing all of the windows on the
current space. It is done using the method

```objectivec
CFArrayRef CGWindowListCopyWindowInfo(CGWindowListOption option, CGWindowID relativeToWindow);
```

The options for `option` are

```objectivec
enum
{
   kCGWindowListOptionAll                 = 0,
   kCGWindowListOptionOnScreenOnly        = (1 << 0),
   kCGWindowListOptionOnScreenAboveWindow = (1 << 1),
   kCGWindowListOptionOnScreenBelowWindow = (1 << 2),
   kCGWindowListOptionIncludingWindow     = (1 << 3),
   kCGWindowListExcludeDesktopElements    = (1 << 4)
}
```

We can not specify a `relativeToWindow` ID and use the option
`kCGWindowListOptionOnScreenOnly` to get all windows that are on the screen
right now. That means all the windows in the current space, as any other windows
are not on screen.

It gives you a bunch of dictionaries that look like

```objectivec
{
   kCGWindowAlpha = 1;
   kCGWindowBounds =         {
      Height = 22;
      Width = 212;
      X = 1662;
      Y = 0;
   };
   kCGWindowIsOnscreen = 1;
   kCGWindowLayer = 25;
   kCGWindowMemoryUsage = 30104;
   kCGWindowName = "";
   kCGWindowNumber = 14;
   kCGWindowOwnerName = SystemUIServer;
   kCGWindowOwnerPID = 99;
   kCGWindowSharingState = 1;
   kCGWindowStoreType = 2;
}
```

which conveniently has a window number under the key `kCGWindowNumber`.

Putting It All Together
=======================

Okay, so we can get a list of windows connected to space uuids and we can get a
list of windows on the current space. We should be able to cross-reference the
lists to figure out the uuid of the current space. Great.

But there's one subtle problem here. Windows can be on many spaces. So we have
to make sure to ignore any windows on more than one space.

The final code looks like:

```objectivec
- (NSString *)activeSpaceIdentifier {
    [[NSUserDefaults standardUserDefaults] removeSuiteNamed:@"com.apple.spaces"];
    [[NSUserDefaults standardUserDefaults] addSuiteNamed:@"com.apple.spaces"];

    NSArray *spaceProperties = [[NSUserDefaults standardUserDefaults] dictionaryForKey:@"SpacesConfiguration"][@"Space Properties"];
    NSMutableDictionary *spaceIdentifiersByWindowNumber = [NSMutableDictionary dictionary];
    for (NSDictionary *spaceDictionary in spaceProperties) {
        NSArray *windows = spaceDictionary[@"windows"];
        for (NSNumber *window in windows) {
            if (spaceIdentifiersByWindowNumber[window]) {
                spaceIdentifiersByWindowNumber[window] = [spaceIdentifiersByWindowNumber[window] arrayByAddingObject:spaceDictionary[@"name"]];
            } else {
                spaceIdentifiersByWindowNumber[window] = @[ spaceDictionary[@"name"] ];
            }
        }
    }

    CFArrayRef windowDescriptions = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID);
    NSString *activeSpaceIdentifier = nil;

    for (NSDictionary *dictionary in (__bridge NSArray *)windowDescriptions) {
        NSNumber *windowNumber = dictionary[(__bridge NSString *)kCGWindowNumber];
        NSArray *spaceIdentifiers = spaceIdentifiersByWindowNumber[windowNumber];

        if (spaceIdentifiers.count == 1) {
            activeSpaceIdentifier = spaceIdentifiers[0];
            break;
        }
    }

    CFRelease(windowDescriptions);

    return activeSpaceIdentifier;
}
```

But wait! What if there's no windows in a space? Well, it turns out that unless
you're doing something really weird there's always _something_ in every space
because the system has a bunch of hidden windows you never see. If you're doing
something really weird and you actually encounter a space with no windows in it
I would love to hear about it.
