# Piantor Pro BT V1.3 — Gallium + Seniply + 12-image nice!view test

This package is meant to be extracted **at the root of your fork of
Keebart/zmk-config**.

It keeps the V1.2 keymap changes:
- Gallium colstag base
- Seniply layer system
- `?` on SYMBOL while keeping an independent `"`
- fixed built-in `&sk` override
- right outer thumb = FUN

Display test:
- Left half: unchanged standard `nice_view`
- Right half: standard `nice_view` hardware + `nice_view_art`
- 12 images rotate every 15 seconds
- artwork region: 140x68 native / 68x140 portrait
- physical top 20 pixels intentionally blank in this first test
- no battery/connection UI in the reserved strip yet; this build is only to
  compare artwork readability on the real display

## Install into GitHub

1. Open your fork of `Keebart/zmk-config`.
2. Upload/extract this ZIP **into the repository root**, preserving folders.
3. Allow replacements for:
   - `build.yaml`
   - `config/piantor_pro_bt.conf`
   - `config/piantor_pro_bt.keymap`
4. Commit the files.
5. Open **Actions** and wait for the build workflow.

The Piantor targets should include:
- `piantor_pro_bt_left` + `nice_view`
- `piantor_pro_bt_right` + `nice_view nice_view_art`
- both settings-reset targets

## Flash

For the artwork test itself, the important firmware is the **right-half**
Piantor UF2. The left-half UF2 is also built from the same V1.2 keymap package.

If you have stale ZMK Studio settings overriding the keymap, flash the
Piantor settings-reset UF2 once, then flash the normal firmware again.

## If Actions fails

Send the failing Actions log back to ChatGPT. This package is source/static
checked here, but the authoritative compile test is the GitHub Actions ZMK v0.3
toolchain used by the Keebart repository.


## FAST TEST BUILD

This FAST package intentionally builds only two targets:

- `piantor_pro_bt_left` + `nice_view`
- `piantor_pro_bt_right` + `nice_view nice_view_art`

Corne, Sofle, and both Piantor `settings_reset` targets are omitted to reduce
GitHub Actions build time.

For the current display test, the right-half UF2 is the important artifact.
If you later need `settings_reset`, use the full V1.3 package or add that target
back to `build.yaml`.
