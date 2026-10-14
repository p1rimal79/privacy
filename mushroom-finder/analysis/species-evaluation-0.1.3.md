# Species research update — 0.1.3-alpha.4

## Concrete result

A real local classifier has been trained and exported: EfficientNet-B0 pretrained feature extractor plus a learned 31-output head (30 species and unknown). Four last-block fine-tuning epochs were evaluated on validation; all had worse validation cross-entropy than the linear-head candidate. The saved model is the selected better linear candidate, not the last epoch. Temperature and confidence/margin rejection were fitted using validation only. The production trainer still rejects community-only labels.

Material: 1,906 existing source photographs plus 744 new Ukrainian-filtered openly licensed photographs (344 other fungi, 400 plants). All labels are unreviewed community/source identifications. The plant/other-fungus set is not certified negative presence/absence truth. Four low-data species were excluded from the 30 named classes: Agaricus sylvaticus, Cortinarius rubellus, Inosperma erubescens, Russula emetica. These excluded examples contribute to unknown; Cortinarius orellanus remains without examples.

Source splits retained observer/day and exact-image independence. Observer holdout authors are disjoint from all other partitions. Train 1,731, validation 379, test 334, observer holdout 206. Unknown-labelled images across partitions: 850. Samples, class mapping, source hashes and predictions are preserved in the separate experiment archive. No private user test photographs were used.

## Measured results against source/community labels

| Partition | Images | Top-1 | Top-3 | Returned shortlist | Correct first candidate among returned |
|---|---:|---:|---:|---:|---:|
| Validation | 379 | 62.8% | 83.6% | 113 | 80.5% |
| Test | 334 | 63.8% | 84.4% | 111 | 82.9% |
| Observer holdout | 206 | 63.1% | 85.4% | 49 | 79.6% |

On the 80 unknown-labelled test photos, 77 were rejected (96.25%); on 64 observer-holdout unknowns, 61 were rejected (95.31%). These are dataset-specific measurements, not biological correctness or independent forest acceptance. Rejection selected on validation requires top score at least 0.525 and margin at least 0.15, comparing all classes including unknown. Three unknown-labelled test photographs passed incorrectly. The model therefore cannot establish food safety, complete taxonomic coverage or rare-species recognition.

## App integration

Photo check: select an image; tap a detected box or draw around ONE mushroom; Suggest type; open a candidate's reference card for comparison. The model abstains on insufficient score/margin and on a small, dark, overexposed or low-detail crop. Classification uses the full 31-output vector, not a renormalized personal selection. Research results remain ambiguous hypotheses; no accepted selected-species match or reference edibility category is enabled.

Both detector and classifier operate locally in optimized MushroomFinder-Research. Ordinary Release continues to reject engineering candidates. Live-video species classification is deliberately disabled pending iPhone latency/crop freshness validation; existing detector/camera preview remains available. This update adds working source code and a real model, not an iOS-runtime verification.

Bilingual documents disclose the on-device crop/candidate processing. Private photographs and guesses are not automatically saved or uploaded. The journal/map behavior and bundled Ukraine overview are preserved. Operator/contact/legal approval are still unresolved.

## Verification and limitations

The Core ML MLProgram exports for iOS 16 with RGB image input 224×224, scale 1/255, normalization mean/std inside the model, and class_scores [1,31]. Exact class mapping, source/weight/package hashes are included. Torch eager vs traced parity passed on 24 real test images with maximum error 0.0. This does not execute Core ML; macOS runtime and iPhone pixelbuffer/crop orientation, thermal behavior and latency remain untested. A Mac parity runner and attributed golden inputs are included.

Python checks: 16 tests pass. Swift syntax, 22 schemas, 190 locale keys, Xcode references and model/pack checksums checked. Xcode compile, XCTest/device/airplane-mode tests are blocked without Mac/iPhone. Current source-quality accuracy is too low for a production release. Per-class test sizes are small; labels, photo angles, lighting and specimen identity need expert review. Whole-photo training vs user-cropped images creates domain shift. No unsupported taxon is made supported merely by training a class.

## Reproduction

Use a fresh virtual environment; install CPU torch/torchvision first with the official CPU wheel index, then remaining pinned research dependencies with torch versions constrained. Do not run competing pip installations in the same environment.

Run ml/tools/collect_unknown_material.py with the known source manifest and output directory, then ml/tools/train_research_species.py with --known, --unknown, --source (pinned timm backbone source), --output. The exact backbone revision and SHA-256 are in species-model-card.json. Run ml/tools/verify_species_export.py to create attributed golden examples; on macOS run ml/tools/verify_species_coreml_macos.py against the experiment folder.

The separately delivered experiment includes the checkpoint, Core ML package, mapping, source hashes, training/validation history, per-class metrics, predictions, sample split record, golden photographs and source/usage notices. Feature caches and raw API responses are excluded. Training material remains separate from Git and the app bundle.
