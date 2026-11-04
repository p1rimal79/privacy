# Data and reference update — 0.1.2-alpha.3

## Actual delivered material

- 1,906 real source JPEGs, 295,048,940 bytes, 34 labelled species; 471 photos from Ukraine-filtered observations, 1,435 from a global query with country intentionally not retained.
- Observation metadata and photo licences independently restricted to CC0/CC BY. Author attribution and source URL retained per photo. No user test ZIP images, exact locations, raw API responses or copied First Nature photographs/descriptions are distributed.
- 1,461 conservative observer/day components; 1,906 unique SHA-256 values. Observer holdout: 157 photos from 44 authors, disjoint from other splits. Train 1,185, validation 291, test 273. Perceptual duplicates and actual finding identity still require review.
- Reference pack: 1,219 source taxa, 35 editorial trait cards, seven bidirectional comparison pairs, 102 local attributed photographs, SQLite export, JSON, checksums and explicit missing evidence.
- Historical checklist: Prylutskyi et al. (2023), 1,201 source taxon rows and 8,797 occurrences. CC0. This is a gilled Agaricales checklist, not all Ukrainian fungi. Eighteen priority taxa added outside that historical registry; their Ukrainian presence is not presumed.
- Traits are original concise paraphrases with source links and retrieval checksums, awaiting review. Expert-approved cards, expert image labels and detector boxes: zero. No reference food-safety categories or supported model classes are activated.

## App changes

Research configuration/scheme permits the existing D-FINE detector in optimized internal builds. Its weights and previous poor forest performance are unchanged. Standard Release still requires field validation. New selected-photo pipeline normalizes EXIF orientation, limits the thumbnail, runs locally, warns about frame quality and discards stale results. Photograph/box orientation and Core ML execution require a physical iPhone check.

Offline card comparison distinguishes agreement, contradiction and not-visible information. Any contradiction is shown independently of matches. Priority species appear first/by default, with access to the full source registry. Local reference media is checked against SHA-256; reference JSON is verified before loading. These features do not establish an identification.

The bundled 720-tile Ukraine overview and optional map-import/download code are preserved. A zoom-9 overview does not provide detailed trail navigation. Airplane-mode rendering and regional detail remain device acceptance items.

## Data gaps and release constraints

Current examples: Cortinarius orellanus 0; Inosperma erubescens 8; Russula emetica 15; Cortinarius rubellus 37; Agaricus sylvaticus 46. Many priority species are represented mainly by non-Ukrainian records. The newest-record selection and medium derivatives (normally a 500-pixel maximum edge) create sampling/quality limitations. Photo angles, actual illumination, age and device are unlabelled. Community research-grade is not expert biological truth.

Need: expert review of labels and morphology/translations, bounding boxes, verified negative forest scenes, multiview material, balanced regions/seasons/lighting, independent forest event/video holdout, unknown calibration, actual training/export and iPhone measurements. The existing production trainer correctly rejects unverified samples; collection is not falsely promoted to approved training data.

Native compile/runtime, model acceptance, complete reference coverage, operator/private contact, legal approval and App Store release remain blocked. GitHub PR is a draft; Pages deployment/production public URLs are not claimed.

## Sources and reproduction

Commands below refer to the native project archive. This analysis subtree contains the standalone collector and its configuration; the pack builder and native source are delivered in the app archive.

- https://api.inaturalist.org/v1
- https://www.inaturalist.org/pages/api+recommended+practices
- https://help.inaturalist.org/en/support/solutions/articles/151000173511
- https://www.gbif.org/dataset/f994f6e8-4d7d-45bd-ab10-d59ecdfdbe80
- https://doi.org/10.3897/BDJ.11.e99101
- https://www.first-nature.com/fungi/index1binom.php
- https://developer.apple.com/documentation/photosui/photospicker

Install tools/requirements.txt in a virtual environment. Run `python tools/collect_reference.py --output ../data-work --observations-per-species 60 --max-media-mib 512`. `--resume` reuses completed species and retries empty ones; use it only with the same collection options. Future collection can request `--image-size large`, respecting provider bandwidth limits. API requests are spaced at least one second; downloads have bounded concurrency, time and size. Run `python tools/build_reference_pack.py --input ../data-work` to verify bytes, splits, licences and SQLite, and install the pack into the native source tree. No individual source descriptions or precise occurrence locations are redistributed.
