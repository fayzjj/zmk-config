#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from shutil import copy2
from PIL import Image, ImageEnhance, ImageOps

PW, PH = 68, 140
NW, NH = 160, 68
FRAME_BYTES = 1360
CACHE_SCHEMA = 3
PREVIEW_COLUMNS = 3


def images_in(folder):
    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts)


def slugify(name):
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    return re.sub(r"_+", "_", name).strip("_") or "image"


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def recipe_hash(mode, raw_defaults):
    recipe = {
        "cache_schema": CACHE_SCHEMA,
        "mode": mode,
        "raw_defaults": raw_defaults if mode == "raw" else {},
        "physical_size": [PW, PH],
        "preview_recipe": "68x140_1bit",
    }
    payload = json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def cache_key(source_hash, recipe_digest):
    return hashlib.sha256(f"{source_hash}:{recipe_digest}".encode("utf-8")).hexdigest()


def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def flatten_black(im):
    if im.mode in ("RGBA", "LA") or "transparency" in im.info:
        rgba = im.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
        bg.alpha_composite(rgba)
        return bg.convert("L")
    return im.convert("L")


def prepare_raw(im, opt):
    im = flatten_black(im)
    im = ImageOps.fit(
        im,
        (int(opt.get("width", PW)), int(opt.get("height", PH))),
        method=Image.Resampling.LANCZOS,
        centering=(float(opt.get("anchor_x", 0.5)), float(opt.get("anchor_y", 0.45))),
    )
    im = ImageEnhance.Contrast(im).enhance(float(opt.get("contrast", 1.25)))
    if bool(opt.get("dither", False)):
        bw = im.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    else:
        t = int(opt.get("threshold", 128))
        bw = im.point(lambda p: 255 if p >= t else 0, mode="1")
    if bool(opt.get("invert", False)):
        bw = ImageOps.invert(bw.convert("L")).point(lambda p: 255 if p >= 128 else 0, mode="1")
    return bw


def prepare_final(im):
    bw = im.convert("1", dither=Image.Dither.NONE)
    if bw.size != (PW, PH):
        raise ValueError(f"prepared mode requires {PW}x{PH}, got {bw.size}")
    return bw


def prepare_art(src, mode, raw_defaults):
    with Image.open(src) as im:
        return prepare_final(im) if mode == "prepared" else prepare_raw(im, raw_defaults)


def frame_bytes(art, framebuffer_invert=False):
    # Preview stays visually correct. Only the bytes sent to NiceView are inverted
    # when framebuffer_invert=true, because this keyboard's artwork polarity is
    # opposite to the preview/image polarity.
    native = art.transpose(Image.Transpose.ROTATE_270)
    full = Image.new("1", (NW, NH), 0)
    full.paste(native, (0, 0))
    px = full.load()
    data = bytearray()
    for y in range(NH):
        for bx in range(NW // 8):
            v = 0
            for bit in range(8):
                on = bool(px[bx * 8 + bit, y])
                if framebuffer_invert:
                    on = not on
                if on:
                    v |= 1 << (7 - bit)
            data.append(v)
    assert len(data) == FRAME_BYTES
    return bytes(data)


def emit_c(path, frames):
    parts = ["#include <stdint.h>\n"]
    for i, data in enumerate(frames, 1):
        rows = []
        for j in range(0, len(data), 16):
            rows.append("    " + ", ".join(f"0x{x:02x}" for x in data[j:j + 16]) + ",")
        parts.append(f"const uint8_t nv_frame_{i:02d}[1360] = {{\n" + "\n".join(rows) + "\n};\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")


def emit_h(path, count):
    lines = ["#pragma once", "#include <stdint.h>", ""]
    lines += [f"extern const uint8_t nv_frame_{i:02d}[1360];" for i in range(1, count + 1)]
    lines += [
        "",
        "static const uint8_t *const nv_frames[] = {",
        "    " + ", ".join(f"nv_frame_{i:02d}" for i in range(1, count + 1)),
        "};",
        f"#define NV_FRAME_COUNT {count}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def source_group(preview_root, src):
    return preview_root / "by_source" / slugify(src.stem)


def get_or_build(preview_root, src, mode, raw_defaults):
    source_digest = sha256_file(src)
    recipe_digest = recipe_hash(mode, raw_defaults)
    key = cache_key(source_digest, recipe_digest)
    grp = source_group(preview_root, src)
    latest_png = grp / "latest_68x140_1bit.png"
    latest_meta = grp / "latest.json"
    meta = load_json(latest_meta, None)

    if meta and meta.get("cache_key") == key and latest_png.exists():
        with Image.open(latest_png) as im:
            art = im.convert("1", dither=Image.Dither.NONE)
        if art.size == (PW, PH):
            return art, latest_png, source_digest, recipe_digest, key, "reused"

    art = prepare_art(src, mode, raw_defaults)
    versions = grp / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_name = f"{stamp}_{key[:10]}_68x140_1bit.png"
    version_png = versions / version_name
    art.save(version_png)
    art.save(latest_png)
    meta = {
        "source_file": str(src).replace("\\", "/"),
        "source_filename": src.name,
        "source_hash": source_digest,
        "recipe_hash": recipe_digest,
        "cache_key": key,
        "cache_schema": CACHE_SCHEMA,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "latest_png": latest_png.name,
        "latest_version": version_name,
    }
    save_json(latest_meta, meta)
    hist = load_json(grp / "history.json", {"versions": []})
    hist.setdefault("versions", []).append(meta | {"version_png": f"versions/{version_name}"})
    save_json(grp / "history.json", hist)
    return art, latest_png, source_digest, recipe_digest, key, "processed"


def clean_dir(folder):
    if folder.exists():
        for p in sorted(folder.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                p.rmdir()
    folder.mkdir(parents=True, exist_ok=True)


def next_run_dir(preview_root):
    runs = preview_root / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    nums = []
    for p in runs.iterdir():
        if p.is_dir():
            m = re.match(r"run_(\d{4})_", p.name)
            if m:
                nums.append(int(m.group(1)))
    n = max(nums, default=0) + 1
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = runs / f"run_{n:04d}_{stamp}"
    out.mkdir(parents=True, exist_ok=False)
    return out


def render_folder(folder, items, mode):
    folder.mkdir(parents=True, exist_ok=True)
    previews = []
    manifest = []
    for i, item in enumerate(items, 1):
        name = f"{i:02d}_{slugify(item['src'].stem)}_final_68x140_1bit.png"
        dst = folder / name
        copy2(item["prepared_path"], dst)
        previews.append(dst)
        manifest.append({
            "index": i,
            "source_filename": item["src"].name,
            "source_hash": item["source_digest"],
            "recipe_hash": item["recipe_digest"],
            "cache_key": item["key"],
            "status": item["status"],
            "output_file": name,
        })

    big = []
    for p in previews:
        with Image.open(p) as im:
            big.append(im.convert("L").resize((340, 700), Image.Resampling.NEAREST))
    rows = max(1, (len(big) + PREVIEW_COLUMNS - 1) // PREVIEW_COLUMNS)
    sheet = Image.new("L", (340 * PREVIEW_COLUMNS, 700 * rows), 255)
    for i, im in enumerate(big):
        sheet.paste(im, ((i % PREVIEW_COLUMNS) * 340, (i // PREVIEW_COLUMNS) * 700))
    sheet.save(folder / "CONTACT_SHEET.png")
    save_json(folder / "manifest.json", {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "count": len(items),
        "items": manifest,
    })


def save_previews(preview_root, items, root, cfg, mode):
    preview_root.mkdir(parents=True, exist_ok=True)
    latest = preview_root / "latest"
    clean_dir(latest)
    render_folder(latest, items, mode)

    run_dir = next_run_dir(preview_root)
    render_folder(run_dir, items, mode)
    snap = run_dir / "generated_sources"
    snap.mkdir(parents=True, exist_ok=True)
    for rel in (cfg["output_art_c"], cfg["output_header"]):
        src = root / rel
        if src.exists():
            copy2(src, snap / src.name)

    index = load_json(preview_root / "index.json", {"runs": []})
    index.setdefault("runs", []).append({
        "run": run_dir.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(items),
        "mode": mode,
        "path": str(run_dir.relative_to(preview_root)).replace("\\", "/"),
    })
    save_json(preview_root / "index.json", index)
    return latest, run_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="niceview_art.json")
    ap.add_argument("--mode", choices=["prepared", "raw"])
    args = ap.parse_args()

    root = Path.cwd()
    cfg = json.loads((root / args.config).read_text(encoding="utf-8"))
    mode = args.mode or cfg.get("mode", "raw")
    files = images_in(root / cfg["input_dir"])
    if not files:
        raise SystemExit("No input images.")

    raw_defaults = cfg.get("raw_defaults", {})
    framebuffer_invert = bool(cfg.get("framebuffer_invert", False))
    preview_root = root / cfg["preview_dir"]
    frames = []
    items = []
    processed = reused = 0

    for src in files:
        art, prepared_path, sd, rd, key, status = get_or_build(preview_root, src, mode, raw_defaults)
        frames.append(frame_bytes(art, framebuffer_invert=framebuffer_invert))
        items.append({
            "src": src,
            "prepared_path": prepared_path,
            "source_digest": sd,
            "recipe_digest": rd,
            "key": key,
            "status": status,
        })
        if status == "reused":
            reused += 1
        else:
            processed += 1

    emit_c(root / cfg["output_art_c"], frames)
    emit_h(root / cfg["output_header"], len(frames))
    latest, run_dir = save_previews(preview_root, items, root, cfg, mode)

    print(f"Generated {len(frames)} NiceView frame(s) in {mode} mode.")
    print(f"Processed new/changed: {processed}")
    print(f"Reused unchanged:     {reused}")
    print(f"Framebuffer inverted: {framebuffer_invert}")
    print(f"Latest preview: {latest}")
    print(f"Archived run:   {run_dir}")


if __name__ == "__main__":
    main()
