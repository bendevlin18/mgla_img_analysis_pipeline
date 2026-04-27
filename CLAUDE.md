# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

A microglial image analysis pipeline. Input images are multi-channel maximum intensity projections (MIPs) in CZI format, where one channel is IBA1 (microglia marker for cell counts) and the other channels carry stains for homeostatic/other microglial proteins (e.g. TMEM119, P2YR12, CD68). Output is per-cell measurements aggregated to per-image and per-animal CSVs.

## Pipeline architecture

There are two coexisting pipelines: the original Fiji macro + Jupyter notebook (CZI inputs), and a newer Python pipeline (TIFF inputs). Both are research workflows run by hand — no build system, no test suite. They are paired by filename convention, not by code, and the upstream ilastik training step is not automated by either.

`batch_MIP_tif.ijm` is an upstream helper that converts a directory of CZI z-stacks into max-intensity-projection TIFFs (multi-page, channel-per-page) using Bio-Formats + `Z Project`. Output filenames are `<original>.czi_MIP.tif`, which is what the Python pipeline expects when run with `--raw-suffix .czi_MIP.tif`. Run this once per dataset before doing ilastik prediction and the Python pipeline.

### Python pipeline (`01_build_masks.py` + `02_measure_channels.py`)

Two CLI scripts, deliberately split so the user can visually QC masks before measuring. Run stage 1, eyeball the PNGs in `mask_previews/`, and only then run stage 2.

**Stage 1 (`01_build_masks.py`)** reads ilastik Simple Segmentation TIFFs, applies a `--mask-rule` to convert to a canonical 0/255 binary mask, and writes both the mask TIFF (`masks/<key>_mask.tif`, consumed by stage 2) and a PNG preview (`mask_previews/<key>_preview.png`, for human QC). The mask rule abstraction (`nonzero` / `eq:N` / `neq:N` / `gt:N` / `lt:N`) exists because ilastik's foreground encoding is inconsistent across runs (sometimes 1, sometimes 255, sometimes everything-but-2). The key is derived by stripping `--seg-prefix` and `--seg-suffix` from the input filename.

**Stage 2 (`02_measure_channels.py`)** reads multi-page TIFFs as `(C, H, W)`, pairs each with `<key>_mask.tif` by stripping `--raw-prefix` and `--raw-suffix` from the raw filename (symmetric with stage 1's seg-prefix/suffix). Masks larger than the image plane are center-cropped to fit (handles ilastik halo padding); smaller or otherwise mismatched masks are skipped. Emits two tidy CSVs:
- `per_image_means.csv` — one row per (image, channel), whole-mask mean. Replaces the row-index footgun in the legacy notebook.
- `per_mask_means.csv` — one row per (image, channel, connected component) via `scipy.ndimage.label` + `ndimage.mean`. For per-cell heterogeneity analysis.

Channel labels come from `--channels DAPI,IBA1,CD68,TMEM119` and fall back to `ch1/ch2/...`. The two scripts only share filename conventions (the `<key>_mask.tif` artifact) — there is no shared module.

`plans.md` tracks deliberately deferred features (overlay previews, regionprops morphology, background subtraction, config-file support). Promote items from there when there's a real driver.

### Legacy Fiji + notebook pipeline

**Stage 1 — Segmentation + measurement (`MASKING_SIMPLE_SEGMENTATIONS.ijm`)** runs in Fiji/ImageJ. It expects two sibling directories the user picks at runtime:
- A directory of MIP CZI files (opened via Bio-Formats).
- A directory of corresponding ilastik **Simple Segmentation** TIFFs produced upstream by ilastik (not part of this repo).

The macro pairs each CZI with its segmentation by filename convention: for a CZI `XXXXXXXXX*.czi`, it expects `C4-XXXXXXXXX_Simple Segmentation.tif` in the prediction directory (i.e. ilastik was run on channel 4, and the first 9 characters of the CZI filename are the join key). It thresholds the segmentation, runs `Analyze Particles` to populate the ROI manager, then splits the CZI's channels and `roiManager("Measure")` against each of channels 1–4. Per-image results are written to `<MIP_dir>/mask_combined_output/<first-9-chars>_full_output_fiji.csv`, plus a final `results.csv` aggregate.

If you change the channel layout (number of channels, which channel ilastik segmented, the filename prefix), you must update both the `C4-` prefix and the `selectImage(ch_nbr)` loop bounds — they are independent and both hardcoded.

**Stage 2 — Aggregation (`combining_tmem119_cd68_output.ipynb`)** is run from inside the `mask_combined_output` directory produced by stage 1. It scans `os.listdir()` for `.csv` files, parses `animal` and `img_num` from the underscore-split filename (`<animal>_<img_num>_..._fiji.csv`), and pulls `Mean` rows 2 and 3 as CD68 and TMEM119 respectively — these row indices correspond to the channel ordering in stage 1's measure loop and will silently produce wrong columns if that loop changes. Outputs `output_by_image_cd68_tmem.csv` and `grouped_output_by_animal_cd68_tmem.csv`.

The `results.csv` written by the macro is also picked up by the glob and will pollute the aggregation — run the notebook against a directory containing only the per-image CSVs, or filter it out.

## Running

**Python pipeline** (preferred for new work; TIFF inputs):

```
conda env create -f environment.yml   # or: pip install -r requirements.txt
conda activate mgla-img-analysis
python 01_build_masks.py   <ilastik_dir> <stage1_out>  --seg-prefix C4- --seg-suffix "_Simple Segmentation.tif" --mask-rule nonzero
# review PNGs in <stage1_out>/mask_previews/ before continuing
python 02_measure_channels.py <raw_tif_dir> <stage1_out>/masks <stage2_out>  --raw-suffix .tif --channels DAPI,IBA1,CD68,TMEM119
```

The two stages share the *key* — whatever's left after stripping prefix/suffix from each side. They must align. Pick prefix/suffix on each side so the remaining string is the same identifier (e.g. `B01_1`).

**Legacy Fiji pipeline** (CZI inputs):

- Stage 1: open `MASKING_SIMPLE_SEGMENTATIONS.ijm` in Fiji and run. It will prompt for the two directories and the parameter dialog.
- Stage 2: launch Jupyter with the working directory set to the `mask_combined_output` folder, then run the notebook top-to-bottom.

## Reference

`IHC Counting and Masking Analysis using Ilastik.docx` is the human-facing protocol covering the upstream ilastik training step (which this repo does not automate). Consult it before changing the segmentation contract between stages.
