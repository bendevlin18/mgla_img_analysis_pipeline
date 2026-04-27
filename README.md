# mgla_img_analysis_pipeline

Pipeline for quantifying microglial marker intensities from multi-channel
fluorescence microscopy images. Built around the workflow:

```
CZI z-stacks  -->  MIP TIFFs  -->  ilastik pixel classifier  -->  masks  -->  per-channel intensity CSVs
   (raw)         (Fiji macro)        (manual training)         (Python)        (Python)
```

Typical input is a multi-channel maximum intensity projection (MIP) where one
channel is IBA1 (microglia marker, used for segmentation) and the other
channels carry stains for homeostatic / activation markers (e.g. TMEM119,
CD68, P2YR12). Output is whole-mask and per-cell mean gray values per channel,
ready for downstream statistics.

## Two pipelines, one repo

There are two coexisting end-to-end paths. The Python pipeline is preferred
for new work; the legacy Fiji-based path is kept because old analyses
reference it.

| Path | Inputs | Mask building | Measurement | Output |
|---|---|---|---|---|
| **Python (new)** | TIFF MIPs | `01_build_masks.py` | `02_measure_channels.py` | `per_image_means.csv` + `per_mask_means.csv` |
| **Fiji (legacy)** | CZI MIPs | `MASKING_SIMPLE_SEGMENTATIONS.ijm` (Fiji) | same macro | `<key>_full_output_fiji.csv` per image, aggregated by notebook |

`batch_MIP_tif.ijm` is an upstream Fiji macro that converts a directory of
CZI z-stacks into channel-per-page MIP TIFFs (`<original>.czi_MIP.tif`).
Run this once per dataset before ilastik training.

## Prerequisites

- **Fiji / ImageJ** with the Bio-Formats plugin (for `batch_MIP_tif.ijm` and
  the legacy macro).
- **ilastik** for pixel classification (Simple Segmentation workflow). The
  protocol document `IHC Counting and Masking Analysis using Ilastik.docx`
  walks through training a classifier — read it before running ilastik.
- **Python 3.12** with the deps in `environment.yml` / `requirements.txt`.
  Conda is recommended:
  ```
  conda env create -f environment.yml
  conda activate mgla-img-analysis
  ```

## Running the Python pipeline

### 1. CZI → MIP TIFFs (one-time per dataset)

Open `batch_MIP_tif.ijm` in Fiji, run, and select your CZI directory. Output
TIFFs land in `<czi_dir>/batch_output_files/`, named like `B01_1.czi_MIP.tif`.

### 2. ilastik Simple Segmentation (one-time per dataset)

Train an ilastik pixel classifier on the IBA1 channel of the MIP TIFFs and
export Simple Segmentations. Default convention: ilastik runs on channel 4
and outputs files named `C4-<key>_MIP_Simple Segmentation.tif`. ilastik label
values vary across runs (sometimes 1=foreground/2=background, sometimes
0/255) — stage 3 handles this with `--mask-rule`.

### 3. Build masks (`01_build_masks.py`)

```
python 01_build_masks.py \
    /path/to/ilastik_segmentations \
    /path/to/stage1_out \
    --seg-prefix "C4-" \
    --seg-suffix "_MIP_Simple Segmentation.tif" \
    --mask-rule eq:1
```

Outputs:
- `stage1_out/masks/<key>_mask.tif` — canonical 0/255 binary mask, consumed
  by stage 4.
- `stage1_out/mask_previews/<key>_preview.png` — PNG version of the same
  mask, for visual QC.

**Open the PNGs and confirm masks look right before running stage 4.** If
foreground/background are inverted, re-run with a different `--mask-rule`
(`nonzero`, `eq:N`, `neq:N`, `gt:N`, `lt:N`).

### 4. Measure channels (`02_measure_channels.py`)

```
python 02_measure_channels.py \
    /path/to/MIP_tiffs \
    /path/to/stage1_out/masks \
    /path/to/stage2_out \
    --raw-suffix ".czi_MIP.tif"
```

Outputs:
- `per_image_means.csv` — one row per (image, channel). Whole-mask mean.
  Columns: `image, key, channel_index, channel_label, mean, n_pixels, n_components`.
- `per_mask_means.csv` — one row per (image, channel, connected component).
  For per-cell heterogeneity analysis. Columns: `image, key, channel_index,
  channel_label, component_id, mean, n_pixels`.

Channel labels come from `--channels DAPI,IBA1,CD68,TMEM119` (comma-separated)
and fall back to `ch1, ch2, ...` if omitted — the user can rename columns
downstream.

## Filename pairing — the one thing to get right

The two stages talk to each other through a shared **key**: whatever's left
after stripping `--seg-prefix` / `--seg-suffix` (stage 3) or `--raw-prefix` /
`--raw-suffix` (stage 4) from each filename. Pick prefix/suffix on each side
so the remaining string is the same identifier.

Example for the default convention:
- Segmentation: `C4-B01_1_MIP_Simple Segmentation.tif`
  - strip `C4-` and `_MIP_Simple Segmentation.tif` → key = `B01_1`
- Raw TIFF: `B01_1.czi_MIP.tif`
  - strip `` and `.czi_MIP.tif` → key = `B01_1`
- Mask written / read as `B01_1_mask.tif`

If a key on one side is `B01_1` but on the other is `B01_1_MIP`, stage 4
won't find the mask and will skip the file with a warning.

## Notes / gotchas

- **Mask shape vs. raw shape.** ilastik sometimes emits a small halo
  (e.g. 6 px larger in each dimension). Stage 4 center-crops the mask to fit
  the raw image. Smaller-or-otherwise-mismatched masks are skipped with a
  warning rather than guessed at.
- **Empty masks.** If ilastik classifies an entire image as background, the
  resulting mask preview will be all black and the corresponding
  `per_image_means.csv` row will have `n_pixels = 0` and `mean = NaN`.
  Re-run ilastik prediction on that file or drop it from analysis.
- **Component counts.** `per_mask_means.csv` treats every connected component
  as a row, including very small fragments. If you want morphology-based
  filtering (size, eccentricity, etc.) see `plans.md`.

## Repo layout

```
01_build_masks.py        Python stage 1 — segmentation -> 0/255 masks + previews
02_measure_channels.py   Python stage 2 — masks -> per-image / per-mask CSVs
batch_MIP_tif.ijm        Fiji helper — CZI z-stacks -> MIP TIFFs
MASKING_SIMPLE_SEGMENTATIONS.ijm   legacy Fiji pipeline (CZI inputs)
combining_tmem119_cd68_output.ipynb   legacy aggregation notebook
environment.yml          conda env definition
requirements.txt         pip equivalent
plans.md                 deliberately deferred features
CLAUDE.md                guidance for AI coding assistants in this repo
IHC Counting and Masking Analysis using Ilastik.docx   ilastik training protocol
```
