"""Stage 1: build canonical 0/255 binary masks (+ PNG previews) from ilastik
Simple Segmentation TIFFs.

Each input segmentation file should be named:
    <seg-prefix><key><seg-suffix>
The <key> is preserved and used to pair masks with raw images in stage 2.

The --mask-rule flag handles ilastik's variable foreground encoding:
    nonzero   any non-zero pixel is foreground (covers both 1 and 255 cases)
    eq:N      pixels equal to N are foreground
    neq:N     everything except N is foreground (use when N is the background label)
    gt:N      pixels strictly greater than N
    lt:N      pixels strictly less than N

Run stage 1, eyeball the PNGs in mask_previews/, re-run with a different rule
if the foreground inverted, then move on to stage 2.

Example:
    python 01_build_masks.py /path/to/ilastik_out /path/to/stage1_out \\
        --seg-prefix "C4-" --seg-suffix "_Simple Segmentation.tif" \\
        --mask-rule nonzero
"""
import argparse
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image


def parse_mask_rule(rule_str):
    if rule_str == "nonzero":
        return lambda arr: arr != 0
    for op, fn in (
        ("eq:",  lambda n: (lambda arr: arr == n)),
        ("neq:", lambda n: (lambda arr: arr != n)),
        ("gt:",  lambda n: (lambda arr: arr >  n)),
        ("lt:",  lambda n: (lambda arr: arr <  n)),
    ):
        if rule_str.startswith(op):
            return fn(int(rule_str[len(op):]))
    raise ValueError(
        f"unknown --mask-rule {rule_str!r}; expected one of: "
        "nonzero, eq:N, neq:N, gt:N, lt:N"
    )


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("input_dir", type=Path, help="directory of ilastik Simple Segmentation TIFFs")
    ap.add_argument("output_dir", type=Path, help="directory to write masks/ and mask_previews/")
    ap.add_argument("--seg-prefix", default="C4-",
                    help="filename prefix on segmentation files; stripped to derive the key")
    ap.add_argument("--seg-suffix", default="_Simple Segmentation.tif",
                    help="filename suffix on segmentation files; stripped to derive the key")
    ap.add_argument("--mask-rule", default="nonzero",
                    help="foreground rule: nonzero | eq:N | neq:N | gt:N | lt:N")
    args = ap.parse_args()

    rule = parse_mask_rule(args.mask_rule)

    masks_dir = args.output_dir / "masks"
    previews_dir = args.output_dir / "mask_previews"
    masks_dir.mkdir(parents=True, exist_ok=True)
    previews_dir.mkdir(parents=True, exist_ok=True)

    candidates = sorted(p for p in args.input_dir.iterdir() if p.is_file())
    seg_files = [
        p for p in candidates
        if p.name.startswith(args.seg_prefix) and p.name.endswith(args.seg_suffix)
    ]
    if not seg_files:
        print(f"no segmentation files in {args.input_dir} matching "
              f"{args.seg_prefix}*{args.seg_suffix}")
        return

    n_done = 0
    for seg_path in seg_files:
        key = seg_path.name[len(args.seg_prefix):-len(args.seg_suffix)]
        seg = np.squeeze(tifffile.imread(seg_path))
        if seg.ndim != 2:
            print(f"skip {seg_path.name}: expected 2D segmentation, got shape {seg.shape}")
            continue

        mask = (rule(seg).astype(np.uint8)) * 255
        tifffile.imwrite(masks_dir / f"{key}_mask.tif", mask)
        Image.fromarray(mask).save(previews_dir / f"{key}_preview.png")

        fg_pixels = int((mask > 0).sum())
        print(f"{seg_path.name} -> key={key}  foreground_pixels={fg_pixels}")
        n_done += 1

    print(f"\ndone: {n_done}/{len(seg_files)} segmentations processed")
    print(f"masks:    {masks_dir}")
    print(f"previews: {previews_dir}")


if __name__ == "__main__":
    main()
