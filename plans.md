# Future improvements

Things considered but deliberately out of scope for the initial Python pipeline.
Add to this list as ideas come up; promote to implementation when a real need shows up.

## Stage 1 — mask building

- **Overlay previews.** Alongside the bare B/W mask PNG, generate a preview that
  overlays the mask outline (or a translucent fill) onto a chosen raw channel.
  Useful for QC — lets the user see whether the mask actually tracks the
  structures of interest, rather than just "is the mask the right shape in
  isolation". Implementation sketch: take an extra `--overlay-from <raw_dir>`
  and `--overlay-channel-index N`, extract contours with
  `skimage.segmentation.find_boundaries`, composite onto the chosen channel
  (rescaled to 8-bit) with PIL, write `<key>_overlay.png` next to the bare
  preview.

## Stage 2 — measurement

- **Per-mask morphology.** Alongside per-component mean, record area, centroid,
  eccentricity, perimeter, etc. via `skimage.measure.regionprops_table`.
  Useful for filtering out artifacts (very small / very large components)
  and for morphological heterogeneity analysis on top of intensity heterogeneity.

- **Background subtraction.** Optional per-image background mean (mean over
  `~mask` pixels) reported alongside foreground mean, so heterogeneity isn't
  confounded by acquisition-level intensity drift between images.

## Pipeline-wide

- **Single CLI with subcommands** (`mgla mask` / `mgla measure`) instead of two
  numbered scripts, once the workflow has stabilized and the parameters stop
  shifting.

- **Config file support** (YAML or TOML). A study's parameters — channel
  labels, mask rule, key length, prefix/suffix — would live next to the data
  and be versioned, instead of being recalled from shell history each run.
