# Late axes-training breakdown

Only the new `axes-recovery-01` training run is included, from1048609 to2097159. Take the last floor(N/4) completed episodes separately within each of the8workers, then retain axes focus episodes. These are changing stochastic training policies and reset draws, not evaluation of the frozen final checkpoint.

| Direction | Shift | Attempts | Contacts | Crossed net | Legal returns | Target hits |
|---|---:|---:|---:|---:|---:|---:|
| Left |6.25cm|246|246|243|241|55|
| Left |12.5cm|249|249|202|191|42|
| Left |18.75cm|248|221|109|101|10|
| Left |25cm|255|145|32|31|2|
| Right |6.25cm|251|251|240|237|51|
| Right |12.5cm|239|230|187|176|40|
| Right |18.75cm|232|172|72|56|7|
| Right |25cm|247|62|13|12|2|

The small lateral offsets have many successful returns during training. Success declines sharply at18.75–25cm, inside the training distribution. At25cm there are both missed contacts and contacts that fail to cross the net legally; this is not solely a question of landing on the requested target.

Across all four trained distances, legal-return rates in the first versus last quarter were: left54.2%→56.5%, right49.4%→49.6%, shallow80.3%→80.1%, deep95.0%→93.8%. The aggregate trajectory does not show a broad late improvement. Completion order is not an exact wall-time or global-policy-step slice, and these rates use different reset draws.

Late25cm depth results were much stronger: shallow126/238 legal returns with183contacts, deep204/248 legal returns with242contacts. The lateral gap appears in both feed types: over all four distances, late air-feed legal returns were252/495 left and221/484 right; bounce-feed results were312/503 left and260/485 right.

Interpretation for the pending frozen evaluation: poor lateral25cm results would be consistent with this training evidence and would not be explained merely by the wider50–100cm evaluation shifts. The logs alone do not identify whether the remaining failure comes from positioning, swing execution, timing, or the available physical contact window.

Raw counts, all16 direction/distance cells, feed-type/instruction splits, worker window bounds, and32input hashes are in `axes-training-late-summary.json`. Reproduction script: `axes_training_direction_summary.py`. No source, training, policy, or F: files were changed.
