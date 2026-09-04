# Piantor Pro BT V1.4 — 9-image nice!view test

Fast GitHub Actions package.

## Display behavior
- Right nice!view: 9 selected images
- Changes image every 10 seconds
- Physical top 20 px: live split-link indicator + live battery percentage/bar
- Artwork: 68x140 beneath the status strip
- Left nice!view: unchanged standard ZMK nice!view screen

## Keyboard
Carries forward the prior V1.2 Gallium + Seniply keymap and config.

## Build targets
Only 2 targets are built for speed:
1. piantor_pro_bt_left + nice_view
2. piantor_pro_bt_right + nice_view + nice_view_art

Extract this ZIP over the root of your Keebart/zmk-config fork, preserving folders,
commit, and run GitHub Actions.

If the build fails, send the last ~100 lines of the failing Actions log.

## V1.5 inversion note
Only the 9 artwork bitmaps were inverted 1:1 from V1.4 so that the physical
nice!view panel's observed polarity reversal produces the desired black-background
appearance on the keyboard.

Slideshow timing, battery display, link status, keymap, build matrix, and all
firmware behavior are unchanged from V1.4.

## V1.5.1 linker fix

Corrected the generated ZMK display-listener initialization function names:

- `widget_nv_battery_init()` -> `nv_battery_init()`
- `widget_nv_link_init()` -> `nv_link_init()`

No artwork, keymap, timing, status UI, or build-target changes.
