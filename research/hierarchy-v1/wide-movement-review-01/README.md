# Wider movement recording workflow

The frozen executor at 1,048,609 experiences replays the same 512 condition-A resets as the wider diagnostic. The selection rule chooses the first legal and unsuccessful return per direction when available. These clips illustrate behavior; their balance is not an estimate of success rate.

The capture stores actual 20 fps Unity JPEGs and body/ball poses, and verifies all 512 physical episode/goal/first-decision records against the diagnostic. Rendering changes only renderer visibility. No policy, simulation source or ledger changes occur.

Metadata, replay evidence and exact scripts are preserved alongside losslessly compressed pose recordings. Decompress each recording.json.gz to recover the original byte-identical recording.json. JPEGs and redundant data.js remain in the local output directory with hashes in local-viewer-files.json; this Git archive is not a standalone playable gallery.
