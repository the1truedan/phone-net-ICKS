# Earmark: spare-phone app routines (grocery deals, coupons, lists), later

**Asked 2026-11-11.** Not started. Parked behind transcription and packet work.

**Goal:** an old phone (cracked screen is fine) stays plugged into the desk Mac and runs recorded routines in store and
deal apps (Flipp, local grocer apps) on a schedule, so coupons, weekly deals and shopping lists stay current with no one
touching the phone. Results land as local files the job board can show.

## How it would work
- **Driver:** adb, not finger macros. `uiautomator dump` finds a button by its text or id, `input tap/swipe` presses it,
  `screencap` saves what was shown. scrcpy is for watching or recording a routine, not for running one. The Blink clip
  saver already works this way.
- **Routine file:** one small file per app: open app, wait for a named element, scroll N pages, save each screen. Steps
  name elements, never fixed screen coordinates, so a cracked or different-size screen does not matter.
- **Reading the data:** screenshots go to the existing caption/OCR lane; the UI dump often carries the item text and
  price directly, which is cheaper and more exact than OCR.
- **Schedule:** a LaunchAgent on the desk Mac, one phone job at a time, never while a pull is running on that phone.
- **App:** a "Routines" row per phone next to Pull: last run, next run, items found, failures.

## Limits to decide first
- Clipping a coupon or changing a list is an action on an account. Start read-only (view deals, save screens); add
  clipping per app only after a manual run looks right.
- Apps change layout often; a routine that cannot find its element stops and reports, it never taps blind.
- Store apps may forbid automated use in their terms. Read each one's terms before scheduling it.
- The phone must stay unlocked: stay-awake on charge, no lock screen, so use a phone with no personal accounts beyond
  the store logins. Never store a PIN or password in a routine.
- Where a store has a web flyer or an official feed, use that instead; the phone is the fallback.

## First test (when ready)
One app, one routine, read-only: open the weekly flyer, page through it, save the UI dump and screenshots, list items
and prices. Done when two runs a day apart produce a correct diff of what changed.
