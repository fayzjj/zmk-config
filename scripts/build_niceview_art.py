#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from shutil import copy2
from PIL import Image, ImageOps, ImageEnhance

PW, PH = 68, 140
NW, NH = 160, 68
FRAME_BYTES = 1360
PREVIEW_COLUMNS = 3
CACHE_SCHEMA = 2


def images_in(folder: Path):
    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts)


def slugify(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "image"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def recipe_hash(mode: str, raw_defaults) -> str:
    recipe = {
        "cache_schema": CACHE_SCHEMA,
        "mode": mode,
        "raw_defaults": raw_defaults if mode == "raw" else {},
        "physical_size": [PW, PH],
        "native_size": [NW, NH],
        "packing": "rotate_270_msb_first",
    }
    payload = json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def cache_key(source_hash: str, recipe_digest: str) -> str:
    return hashlib.sha256(f"{source_hash}:{recipe_digest}".encode("utf-8")).hexdigest()


def flatten_black(im: Image.Image):
    if im.mode in ("RGBA", "LA") or "transparency" in im.info:
        rgba = im.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
        bg.alpha_composite(rgba)
        return bg.convert("L")
    return im.convert("L")


def prepare_raw(im: Image.Image, opt):
    im = flatten_black(im)
    im = ImageOps.fit(
        im,
        (int(opt.get("width", 68)), int(opt.get("height", 140))),
        method=Image.Resampling.LANCZOS,
        centering=(float(opt.get("anchor_x", 0.5)), float(opt.get("anchor_y", 0.45))),
    )
    im = ImageEnhance.Contrast(im).enhance(float(opt.get("contrast", 1.25)))
    if bool(opt.get("dither", False)):
        bw = im.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    else:
        t = int(opt.get("threshold", 128))
        bw = im.point(lambda p: 255 if p >= t else 0, mode="1")
    if bool(opt.get("invert", True)):
        bw = ImageOps.invert(bw.convert("L")).point(lambda p: 255 if p >= 128 else 0, mode="1")
    return bw


def prepare_final(im: Image.Image):
    bw = im.convert("1", dither=Image.Dither.NONE)
    if bw.size != (PW, PH):
        raise ValueError(f"prepared mode requires 68x140, got {bw.size}")
    return bw


def frame_bytes(art: Image.Image):
    native = art.transpose(Image.Transpose.ROTATE_270)
    full = Image.new("1", (NW, NH), 0)
    full.paste(native, (0, 0))
    px = full.load()
    data = bytearray()
    for y in range(NH):
        for bx in range(NW // 8):
            v = 0
            for bit in range(8):
                if px[bx * 8 + bit, y]:
                    v |= 1 << (7 - bit)
            data.append(v)
    assert len(data) == FRAME_BYTES
    return bytes(data)


def emit_c(path: Path, frames):
    parts = ["#include <stdint.h>\n"]
    for i, data in enumerate(frames, 1):
        lines = []
        for j in range(0, len(data), 16):
            lines.append("    " + ", ".join(f"0x{x:02x}" for x in data[j:j + 16]) + ",")
        parts.append(f"const uint8_t nv_frame_{i:02d}[1360] = {{\n" + "\n".join(lines) + "\n};\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")


def emit_h(path: Path, count: int):
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


def ensure_clean_dir(folder: Path):
    if folder.exists():
        for p in folder.iterdir():
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                for sub in sorted(p.rglob("*"), reverse=True):
                    if sub.is_file():
                        sub.unlink()
                    elif sub.is_dir():
                        sub.rmdir()
                p.rmdir()
    folder.mkdir(parents=True, exist_ok=True)


def next_run_dir(preview_root: Path) -> Path:
    runs_root = preview_root / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    existing = []
    for p in runs_root.iterdir():
        if p.is_dir():
            m = re.match(r"run_(\d{4})_", p.name)
            if m:
                existing.append(int(m.group(1)))
    next_num = (max(existing) + 1) if existing else 1
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = runs_root / f"run_{next_num:04d}_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def prepare_art_from_source(src: Path, mode: str, raw_defaults):
    with Image.open(src) as im:
        return prepare_final(im) if mode == "prepared" else prepare_raw(im, raw_defaults)


def source_group_dir(preview_root: Path, src: Path) -> Path:
    return preview_root / "by_source" / slugify(src.stem)


def update_source_history(preview_root: Path, src: Path, art: Image.Image,
                          source_digest: str, recipe_digest: str, key: str, mode: str):
    grp = source_group_dir(preview_root, src)
    versions = grp / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    latest_png = grp / "latest_68x140_1bit.png"
    latest_meta = grp / "latest.json"
    version_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{key[:10]}_68x140_1bit.png"
    version_png = versions / version_name
    art.save(version_png)
    art.save(latest_png)
    meta = {
        "source_file": str(src).replace('\\', '/'),
        "source_filename": src.name,
        "source_stem": src.stem,
        "hash": source_digest,
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
    history = load_json(grp / "history.json", {"versions": []})
    history.setdefault("versions", []).append(meta | {"version_png": f"versions/{version_name}"})
    save_json(grp / "history.json", history)
    return latest_png, "processed"


def get_or_build_source_art(preview_root: Path, src: Path, mode: str, raw_defaults):
    source_digest = sha256_file(src)
    recipe_digest = recipe_hash(mode, raw_defaults)
    key = cache_key(source_digest, recipe_digest)
    grp = source_group_dir(preview_root, src)
    latest_meta_path = grp / "latest.json"
    latest_png_path = grp / "latest_68x140_1bit.png"
    latest_meta = load_json(latest_meta_path, None)

    if latest_meta and latest_meta.get("cache_key") == key and latest_png_path.exists():
        with Image.open(latest_png_path) as im:
            art = im.convert("1", dither=Image.Dither.NONE)
        if art.size == (PW, PH):
            return art, source_digest, recipe_digest, key, latest_png_path, "reused"

    art = prepare_art_from_source(src, mode, raw_defaults)
    latest_png_path, status = update_source_history(
        preview_root, src, art, source_digest, recipe_digest, key, mode
    )
    return art, source_digest, recipe_digest, key, latest_png_path, status


def copy_prepared_art_to_target(art_path: Path, target_path: Path):
    with Image.open(art_path) as im:
        im.convert("1", dither=Image.Dither.NONE).save(target_path)


def write_manifest(path: Path, mode: str, items):
    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "count": len(items),
        "items": items,
    }
    save_json(path, manifest)


def render_contact_sheet(folder: Path, image_paths):
    big = []
    for p in image_paths:
        with Image.open(p) as im:
            big.append(im.convert("L").resize((340, 700), Image.Resampling.NEAREST))
    rows = max(1, (len(big) + PREVIEW_COLUMNS - 1) // PREVIEW_COLUMNS)
    sheet = Image.new("L", (340 * PREVIEW_COLUMNS, 700 * rows), 255)
    for i, im in enumerate(big):
        sheet.paste(im, ((i % PREVIEW_COLUMNS) * 340, (i // PREVIEW_COLUMNS) * 700))
    sheet.save(folder / "CONTACT_SHEET.png")


def render_run_folder(folder: Path, items, root: Path, cfg):
    folder.mkdir(parents=True, exist_ok=True)
    saved = []
    manifest_items = []
    for idx, item in enumerate(items, 1):
        out_name = f"{idx:02d}_{slugify(item['source_path'].stem)}_final_68x140_1bit.png"
        out_path = folder / out_name
        copy2(item["prepared_path"], out_path)
        saved.append(out_path)
        manifest_items.append({
            "index": idx,
            "source_file": str(item["source_path"]).replace('\\', '/'),
            "source_filename": item["source_path"].name,
            "source_hash": item["source_digest"],
            "recipe_hash": item["recipe_digest"],
            "cache_key": item["cache_key"],
            "status": item["status"],
            "prepared_source": str(item["prepared_path"]).replace('\\', '/'),
            "output_file": out_name,
        })
    render_contact_sheet(folder, saved)
    write_manifest(folder / "manifest.json", cfg.get("mode", "prepared"), manifest_items)


def snapshot_generated_sources(run_dir: Path, root: Path, cfg):
    snapshot_dir = run_dir / "generated_sources"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for rel in [cfg["output_art_c"], cfg["output_header"]]:
        src = root / rel
        if src.exists():
            copy2(src, snapshot_dir / src.name)


def update_index(preview_root: Path, run_dir: Path, count: int, mode: str):
    index_path = preview_root / "index.json"
    data = load_json(index_path, {"runs": []})
    data.setdefault("runs", []).append({
        "run": run_dir.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": count,
        "mode": mode,
        "path": str(run_dir.relative_to(preview_root)).replace('\\', '/'),
    })
    save_json(index_path, data)


def previews(preview_root: Path, items, root: Path, cfg):
    preview_root.mkdir(parents=True, exist_ok=True)
    latest_dir = preview_root / "latest"
    ensure_clean_dir(latest_dir)
    render_run_folder(latest_dir, items, root, cfg)

    run_dir = next_run_dir(preview_root)
    render_run_folder(run_dir, items, root, cfg)
    snapshot_generated_sources(run_dir, root, cfg)
    update_index(preview_root, run_dir, len(items), cfg.get("mode", "prepared"))
    return latest_dir, run_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="niceview_art.json")
    ap.add_argument("--mode", choices=["prepared", "raw"])
    a = ap.parse_args()
    root = Path.cwd()
    cfg = json.loads((root / a.config).read_text(encoding="utf-8"))
    mode = a.mode or cfg.get("mode", "prepared")
    cfg["mode"] = mode
    files = images_in(root / cfg["input_dir"])
    if not files:
        raise SystemExit("No input images.")

    preview_root = root / cfg["preview_dir"]
    raw_defaults = cfg.get("raw_defaults", {})
    items = []
    frames = []
    reused = 0
    processed = 0

    for src in files:
        art, source_digest, recipe_digest, key, prepared_path, status = get_or_build_source_art(
            preview_root, src, mode, raw_defaults
        )
        frames.append(frame_bytes(art))
        items.append({
            "source_path": src,
            "prepared_path": prepared_path,
            "source_digest": source_digest,
            "recipe_digest": recipe_digest,
            "cache_key": key,
            "status": status,
        })
        if status == "reused":
            reused += 1
        else:
            processed += 1

    emit_c(root / cfg["output_art_c"], frames)
    emit_h(root / cfg["output_header"], len(frames))
    latest_dir, run_dir = previews(preview_root, items, root, cfg)

    print(f"Generated {len(frames)} NiceView frame(s) in {mode} mode.")
    print(f"Processed new/changed: {processed}")
    print(f"Reused unchanged:     {reused}")
    print(f"Latest preview: {latest_dir}")
    print(f"Archived run:   {run_dir}")


if __name__ == "__main__":
    main()
