"""Stage 2: measure per-channel mean gray values inside the masks built by stage 1.

Pairs each multi-channel TIFF in --raw-dir with its mask in --masks-dir by key:
the raw filename's --raw-prefix and --raw-suffix are stripped, and the result
must match <key>_mask.tif in the masks directory.

Masks larger than the image plane are center-cropped to fit (handles ilastik
halo padding). Smaller or otherwise mismatched masks are skipped with a warning.

Outputs two CSVs:
    per_image_means.csv  one row per (image, channel) -- whole-mask mean
    per_mask_means.csv   one row per (image, channel, connected component)
                         for cell-level heterogeneity analysis

Multi-channel TIFFs are expected to be multi-page with shape (C, H, W).
Single-page 2D TIFFs are treated as one channel.

Example:
    python 02_measure_channels.py /path/to/raw_tifs /path/to/stage1_out/masks \\
        /path/to/stage2_out --raw-suffix ".czi_MIP.tif" \\
        --channels DAPI,IBA1,CD68,TMEM119
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile
from scipy import ndimage


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("raw_dir", type=Path, help="directory of multi-channel TIFFs")
    ap.add_argument("masks_dir", type=Path,
                    help="directory of <key>_mask.tif files (the masks/ output of stage 1)")
    ap.add_argument("output_dir", type=Path, help="directory to write CSVs")
    ap.add_argument("--raw-prefix", default="",
                    help="filename prefix on raw TIFFs; stripped to derive the key")
    ap.add_argument("--raw-suffix", default=".tif",
                    help="filename suffix on raw TIFFs; stripped to derive the key")
    ap.add_argument("--channels", default="",
                    help="comma-separated channel labels (e.g. 'DAPI,IBA1,CD68,TMEM119'); "
                         "falls back to ch1/ch2/...")
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    labels = [s.strip() for s in args.channels.split(",")] if args.channels else []

    raw_files = sorted(
        p for p in args.raw_dir.iterdir()
        if p.is_file()
        and p.name.startswith(args.raw_prefix)
        and p.name.endswith(args.raw_suffix)
    )
    if not raw_files:
        print(f"no files in {args.raw_dir} matching "
              f"{args.raw_prefix or '*'}{args.raw_suffix or '*'}")
        return

    per_image_rows = []
    per_mask_rows = []

    for raw_path in raw_files:
        end = -len(args.raw_suffix) if args.raw_suffix else None
        key = raw_path.name[len(args.raw_prefix):end]
        mask_path = args.masks_dir / f"{key}_mask.tif"
        if not mask_path.exists():
            print(f"skip {raw_path.name}: no mask at {mask_path}")
            continue

        img = np.squeeze(tifffile.imread(raw_path))
        if img.ndim == 2:
            img = img[np.newaxis, ...]
        if img.ndim != 3:
            print(f"skip {raw_path.name}: expected 2D or 3D image, got shape {img.shape}")
            continue

        mask = np.squeeze(tifffile.imread(mask_path))
        if mask.shape != img.shape[1:]:
            mh, mw = mask.shape
            ih, iw = img.shape[1:]
            if mh >= ih and mw >= iw:
                dh = (mh - ih) // 2
                dw = (mw - iw) // 2
                mask = mask[dh:dh + ih, dw:dw + iw]
                print(f"  center-cropped mask ({mh}, {mw}) -> ({ih}, {iw})")
            else:
                print(f"skip {raw_path.name}: mask shape {mask.shape} smaller than "
                      f"image plane {img.shape[1:]}")
                continue

        binary = mask > 0
        labeled, n_components = ndimage.label(binary)
        n_channels = img.shape[0]
        whole_mask_pixels = int(binary.sum())

        for ch_idx in range(n_channels):
            label = labels[ch_idx] if ch_idx < len(labels) else f"ch{ch_idx + 1}"
            channel = img[ch_idx]

            mean_val = float(channel[binary].mean()) if whole_mask_pixels > 0 else float("nan")
            per_image_rows.append({
                "image": raw_path.name,
                "key": key,
                "channel_index": ch_idx + 1,
                "channel_label": label,
                "mean": mean_val,
                "n_pixels": whole_mask_pixels,
                "n_components": n_components,
            })

            if n_components > 0:
                index = np.arange(1, n_components + 1)
                per_label_means = ndimage.mean(channel, labels=labeled, index=index)
                per_label_sizes = ndimage.sum(binary, labels=labeled, index=index)
                for comp_id, m, sz in zip(index, per_label_means, per_label_sizes):
                    per_mask_rows.append({
                        "image": raw_path.name,
                        "key": key,
                        "channel_index": ch_idx + 1,
                        "channel_label": label,
                        "component_id": int(comp_id),
                        "mean": float(m),
                        "n_pixels": int(sz),
                    })

        print(f"{raw_path.name}: channels={n_channels}  components={n_components}  "
              f"mask_pixels={whole_mask_pixels}")

    per_image_csv = args.output_dir / "per_image_means.csv"
    per_mask_csv = args.output_dir / "per_mask_means.csv"
    pd.DataFrame(per_image_rows).to_csv(per_image_csv, index=False)
    pd.DataFrame(per_mask_rows).to_csv(per_mask_csv, index=False)

    print(f"\nwrote {per_image_csv}  ({len(per_image_rows)} rows)")
    print(f"wrote {per_mask_csv}  ({len(per_mask_rows)} rows)")


if __name__ == "__main__":
    main()
