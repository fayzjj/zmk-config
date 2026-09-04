#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance

PHYS_W, PHYS_H = 68, 140
NATIVE_W, NATIVE_H = 160, 68
FRAME_BYTES = 1360

def image_files(folder: Path):
    exts = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts)

def flatten_black(im):
    if im.mode in ('RGBA', 'LA') or 'transparency' in im.info:
        rgba = im.convert('RGBA')
        bg = Image.new('RGBA', rgba.size, (0,0,0,255))
        bg.alpha_composite(rgba)
        return bg.convert('L')
    return im.convert('L')

def prepare_raw(im, opt):
    im = flatten_black(im)
    im = ImageOps.fit(
        im,
        (int(opt.get('width', 68)), int(opt.get('height', 140))),
        method=Image.Resampling.LANCZOS,
        centering=(float(opt.get('anchor_x', 0.5)), float(opt.get('anchor_y', 0.45)))
    )
    im = ImageEnhance.Contrast(im).enhance(float(opt.get('contrast', 1.25)))
    if bool(opt.get('dither', False)):
        bw = im.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
    else:
        threshold = int(opt.get('threshold', 128))
        bw = im.point(lambda p: 255 if p >= threshold else 0, mode='1')
    if bool(opt.get('invert', True)):
        bw = ImageOps.invert(bw.convert('L')).point(lambda p: 255 if p >= 128 else 0, mode='1')
    return bw

def pack_frame(art):
    native = art.transpose(Image.Transpose.ROTATE_270)
    full = Image.new('1', (NATIVE_W, NATIVE_H), 0)
    full.paste(native, (0, 0))
    px = full.load()
    data = bytearray()
    for y in range(NATIVE_H):
        for bx in range(NATIVE_W // 8):
            value = 0
            for bit in range(8):
                if px[bx * 8 + bit, y]:
                    value |= 1 << (7 - bit)
            data.append(value)
    assert len(data) == FRAME_BYTES
    return bytes(data)

def emit_art_c(path: Path, frames):
    parts = ['#include <stdint.h>\n']
    for i, data in enumerate(frames, 1):
        lines = []
        for j in range(0, len(data), 16):
            lines.append('    ' + ', '.join(f'0x{x:02x}' for x in data[j:j+16]) + ',')
        parts.append(f'const uint8_t nv_frame_{i:02d}[1360] = {{\n' + '\n'.join(lines) + '\n};\n')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(parts), encoding='utf-8')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='niceview_art.json')
    args = ap.parse_args()
    root = Path.cwd()
    cfg = json.loads((root / args.config).read_text(encoding='utf-8'))
    if cfg.get('mode') != 'raw':
        raise SystemExit('This repository workflow is configured for raw mode.')
    files = image_files(root / cfg['input_dir'])
    if len(files) != 9:
        raise SystemExit(f'Expected exactly 9 source images, found {len(files)}.')
    frames = []
    for p in files:
        with Image.open(p) as im:
            art = prepare_raw(im, cfg.get('raw_defaults', {}))
        frames.append(pack_frame(art))
    emit_art_c(root / cfg['output_art_c'], frames)
    print('Generated 9 NiceView frames from RAW images.')

if __name__ == '__main__':
    main()
