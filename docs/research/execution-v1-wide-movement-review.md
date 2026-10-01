# Wider movement recordings

The frozen executor at **1,048,609 experiences** replayed all **512 condition-A attempts** with matching physical episodes, goal/landing evidence and first observations/actions. The local viewer contains **7 clips** selected systematically to show available successes and failures.

| Direction | Legal returns / all directional A attempts | Selected illustrations |
|---|---:|---|
| Left | 3 / 66 | legal-return, unsuccessful-return |
| Right | 0 / 64 | unsuccessful-return |
| Shallow | 19 / 62 | legal-return, unsuccessful-return |
| Deep | 16 / 64 | legal-return, unsuccessful-return |

Nominal feed displacement and measured player travel are different quantities. The camera detail follows the player; the full-court view makes repositioning easier to judge. A legal return and a target hit are separate outcomes.

The right-direction cohort has no successful A return, so no successful right clip is invented. Directional results include all 256 challenges; familiar drills make up the other 256 replayed attempts. No mastery or generalization is claimed.

[Recording evidence](execution-v1-evidence/wide-movement-review-01/archive-manifest.json) · [Original diagnostic](execution-v1-wide-movement.md)

The JPEG gallery remains local. The repository preserves replay evidence, compressed actual pose records, the viewer/capture workflow and image hashes without a large image commit.

All 444 JPEGs passed image-decoding checks. Interactive browser playback remains unverified: the in-app browser's local-file URL policy blocked opening the gallery. The local UI-validation record preserves this limitation.

The first capture attempt completed its simulations but failed while reading an evidence file whose writer was still open. Its failure, raw evidence and JPEG hashes are preserved separately. Its unsaved pose records were lost; none were reconstructed. The successful retry uses the same selected cases with a terminal writer-lifecycle correction, recorded in its amendment.
