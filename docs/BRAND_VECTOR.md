# MisePort storefront — vector reconstruction candidate v02

Status: **review candidate, not the original SVG and not a user-approved final master**. Created 2026-10-29 from the two supplied raster references in `assets/original/`. The earlier single-M concept is not the construction source for this candidate.

## Source and preservation

- `assets/original/miseport-logo.png` supplies the storefront silhouette, stacked arrangement, approximate proportions, and visible wordmark contours.
- `assets/original/miseport-brand-board.png` supplies the stated brand palette and an Inter typography reference.
- The original files are retained unchanged. Their recorded hashes remain in `assets/original/provenance.json`.

No original vector or authoritative wordmark font file was supplied. All candidate artwork is newly constructed vector geometry. The wordmark is a hand-outlined approximation of the visible raster lettering; the brand board's use of Inter does not establish that the logo itself was typeset in Inter. No font identification or exact typographic match is claimed. These paths do not depend on any installed font and contain no embedded raster artwork.

## Deliverables

| File | Purpose | Format / dimensions |
|---|---|---|
| `assets/storefront-v02.svg` | Complete storefront plus outlined MisePort wordmark, for light contexts | SVG, transparent, 1080 × 760 viewBox |
| `assets/storefront-v02-dark.svg` | Same lockup in a dark context | SVG, navy background, cloud-colored primary contours, 1080 × 760 |
| `assets/storefront-v02.png` | Transparent high-density preview of the light SVG | PNG, 2160 × 1520, RGBA |
| `assets/favicon-storefront-v02.png` | Storefront symbol without the wordmark | PNG, 256 × 256, RGBA |

The PNGs are rendered from the new SVG geometry with CairoSVG. The favicon selects the `storefront-symbol` group and uses an icon-only crop; it does not trace, crop, or edit the source PNG.

## Geometry brief and topology

The reading order remains storefront above MisePort. There are four independent canopy panels, a single open-bottom arched storefront body, one coral circular shape with a flat lower cut, and three independent teal steps widening toward the bottom. The awning separation, arch opening, and step gaps are transparent negative spaces. They are not white masks.

Symbol coordinates follow the original raster's approximate visible positions before a common translation. Let symbol height `H = 416` native units, equivalent to normalized height 100. Measurements below are axis-aligned unless stated otherwise; they describe this candidate rather than exact measurements of an unavailable source vector.

| Measurement | Native units | Normalized to H = 100 | Direction / meaning |
|---|---:|---:|---|
| Symbol top / bottom | y = 236 / 652 | 0 / 100 | Vertical extent |
| Symbol centerline | x = 724 | — | Vertical symmetry reference; manual optical corrections retained |
| Main wall width | 393 | 94.47 | Horizontal, x = 527 to 920 |
| Portal opening width | 220 | 52.88 | Horizontal, x = 614 to 834 |
| Central awning separation | 16 | 3.85 | Horizontal, x = 716 to 732 |
| Symbol-to-wordmark gap | 42 | 10.10 | Vertical ink edge, step bottom 652 to i-dot top 694 |
| Wordmark cap height | 168 | 40.38 | Vertical, y = 698 to 866 |
| Wordmark width | 936 | 225.00 | Horizontal, x = 256 to 1192 |
| r-to-t optical gap | 12 | 2.88 | Horizontal, r right edge 1113 to t stem 1125 |

All 18 light-master paths are closed filled contours. Counters in e, P, and o use even-odd filling; there are no font references, images, filters, masks, clip paths, external URLs, or decorative internal facets. The curves simplify the raster's soft edges and small asymmetries. No golden-ratio or mathematically exact source reconstruction is asserted.

Machine-readable construction summary:

```json
{
  "candidate": "storefront-v02",
  "approval": "pending_user_review",
  "source_kind": "user_supplied_raster",
  "original_vector": false,
  "view_box": [0, 0, 1080, 760],
  "source_geometry_translation": [-184, -172],
  "symbol_height_native": 416,
  "normalized_symbol_height": 100,
  "canopy_panels": 4,
  "port_steps": 3,
  "wordmark": "MisePort",
  "wordmark_construction": "approximate_hand_outlined_paths",
  "font_dependencies": [],
  "raster_dependencies": [],
  "internal_facets": false,
  "favicon_source_group": "storefront-symbol",
  "favicon_view_box": [464, 188, 520, 520]
}
```

## Color

Flat fills follow the explicit values printed in the supplied brand board: Navy `#0B2F54`, Teal `#0EA5B7`, Coral `#FF7F66`, and Cloud `#F4F7FA`. Aqua `#38C6D9` remains a supporting brand color and is not introduced into the primary logo. The i dot and Port remain teal; Mise and the storefront are navy in the light master.

The original raster has subtle texture and color variation. Those variations are intentionally not copied into the flat vector candidate, so a pixel-perfect color comparison is not expected. The dark version is a newly derived adaptation: primary navy contours become Cloud, while the teal and coral components retain their palette colors. It is not a supplied original dark master. The light master should be placed on a light background; its transparent preview may display poorly in a black image viewer.

## Actual checks

- Both SVGs parsed and passed the skill's `validate_svg_logo.py --strict-contours`: zero errors, zero warnings; 18 paths in the light master and 19 in the dark version including its background.
- The skill's parallelism helper confirmed the two central awning top edges `(647,236)–(716,236)` and `(732,236)–(801,236)` are horizontal with 0° deviation. No broader parallelism claim is inferred from that check.
- CairoSVG successfully rendered both SVGs directly. A light/dark review sheet was inspected at 580 px width, with a light version at 320 px width, favicon views at 64/32/16 px, and a 4× density enlargement of the awning gaps and wall contour.
- Visual review retained all four panels, open arch, coral mark, three separate steps, outlined wordmark and readable counters. An overlong t crossbar was removed after the first render to preserve separation from r.
- The complete PNG has a transparent perimeter; the dark SVG deliberately includes an opaque navy context. Favicon and wordmark rendering have no runtime font dependency.

At 16 px, the complete symbol's fine step and awning gaps are naturally reduced. The 256 px favicon is suitable as a source for review, but no separately pixel-hinted 16 px master is claimed. Rendering was inspected through CairoSVG exports; an independent browser-engine or print proof has not been performed in this asset subtask.

## Remaining differences and approval

This is a faithful topology and palette reconstruction with manually approximated curves, terminals, wordmark spacing, and letter shapes. It omits raster texture and does not prove the original font, vector construction, exact geometry, or original dark treatment. The original PNG remains the visual reference. User comparison and approval are still required before labeling v02 as the official master. No external transfer, publication, or replacement of the original artwork occurred in this subtask.
