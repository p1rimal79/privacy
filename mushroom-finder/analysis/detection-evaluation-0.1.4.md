# Camera update 0.1.4-alpha.5

Camera inference now runs on its own serial queue, with at most one in-flight frame and no backlog. Expiry remains responsive during inference. Evidence survives up to 1.5 seconds between detections, while preview boxes and alerts must reference a source frame no older than 0.5 seconds. Duplicate timestamps cannot stabilize a track. Results from a paused/replaced session are discarded. Initial detections use dashed boxes, repeated detections use solid boxes.

The camera explicitly searches for mushrooms with a visible part at the surface, including partial leaf/needle occlusion. Hidden-mushroom inference from bumps is disabled: there are no verified positive/negative labels for this task. Slow processing, darkness, glare and low detail have visible warnings.

102 display JPEGs retain dimensions, attribution and per-file hashes after compression. Training/test originals are not changed. Compression is checked against decoded original pixels with PSNR >=35 dB; this is not biological feature validation. See reference-compression-0.1.4.json.

The owner's species target is 99–100% first-label agreement. `species_top1_gate` counts ALL eligible independent expert-labelled findings, not only confident outputs, and requires a lower 95% Wilson bound >=99%. Existing community-label top-1 remains 63.8% and fails this requirement. No species production classes are enabled.

The 640x640 detector weights are unchanged in this checkpoint. Automatic tiling is not enabled: prior exploratory testing showed additional false boxes with little gain. The prior training/ROI research results were not durably saved before the runtime reset, so they are not presented as independently reproducible release evidence. A fresh 640/960 comparison is being prepared with original unpainted photographs corresponding to owner red marks; marks denote regions, not tight object boxes.

Python checks, source hashes, Swift syntax, localization and Xcode project integrity are checked in this environment. Native XCTest, iPhone inference, box orientation, preview/alert latency, thermal behavior and offline device tests require Xcode/macOS and a physical iPhone. They have not been executed here. This remains an internal Research build, not a field-validated release.

## Repeated resolution comparison, clean owner images
All 60 owner-marked photographs were matched to clean originals, including three rotated copies. 64 freehand regions; these are not 64 independent mushrooms. With unchanged source weights, threshold 0.2, NMS 0.5 and max 10 boxes: 640 matched 1 region at IoU >=0.3 (0 at >=0.5); 960 matched 0 at either threshold. Median CPU inference 254 ms versus 499 ms. No painted photograph entered inference. These results reject an automatic resolution increase for this candidate; they do not establish field recall or a false-alert rate. `resolution-evaluation-0.1.4.json` records exact counts/timing.

## Completed object experiments
The source object material contains 186 downloaded photographs; exact image bytes are deduplicated for training. Official source validation/test partitions are DEVELOPMENT here, not an untouched benchmark. Owner photos stay test-only. Primary publisher CC BY 2.0 image listings and source URLs are retained; current individual rights recheck and production training approval are incomplete.

The frozen-feature category head used 149 training and 36 held-author validation photographs. Development recall improved 10/73 to 25/73, but unmatched boxes increased 2 to 8. Threshold 0.95 and epoch 350 were frozen using development data. On owner originals, this candidate reached only 2/64 marked regions at IoU >=0.3 and >=0.5. It was rejected for the camera.

A binary category projection and proposal/decoder training used 119 train / 26 validation photographs after excluding all scenes with ignored group/depiction/inside regions. Three real optimization epochs completed. None surpassed the initialization on the development precision-constrained criterion; epoch zero remained selected. On owner originals, this selected variant matched only 1/64 regions at IoU >=0.3. It was rejected for the camera.

A separate crop search reused the existing fungus classifier without owner training or threshold tuning: 122 predetermined crop windows per image. It matched 6/64 freehand regions at IoU >=0.3 and 3/64 at >=0.5, with proposal centers inside 17 marked regions. It emitted 398 coarse crop rectangles and required median 1,933 ms CPU per photograph. These are NOT tight mushroom boxes or calibrated fungus-presence scores. Unknown includes other fungi. This path was rejected for live scanning.

No tested candidate established adequate forest detection or the 99–100% species target. Source-domain improvements did not transfer reliably to the supplied forest images. The app keeps the original engineering detector, clearly marked experimental. Queue/expiry/UI fixes are implemented, but a new field recall is not claimed.

Required next data: an authorized TRAINING set of visible forest mushrooms with tight object boxes/instance masks, including small and partially occluded targets; reviewed forest background negatives; held-out independent forest sessions; iPhone latency/thermal measurements. The supplied owner red-marked set is kept for testing rather than reused to train a result presented as independent. Expert species labels remain a separate missing requirement.

General camera search no longer depends on species classification being available. A persisted selected-mode preference falls back to general detection when the live classifier is unavailable, with an explicit uk/en notice and no change to the selected IDs. Native SearchMode regression cases cover this fallback; execution awaits Xcode.
