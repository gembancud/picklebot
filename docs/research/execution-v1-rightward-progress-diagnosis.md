# Rightward return failure split

The fixed movement-progress endpoint does not register an accepted paddle-face contact on any rightward 50, 75, or 100 cm case (49 cases per target condition). At 25 cm it registers 3/15 contacts under target A and 1/15 under target B. None crosses the net; all recorded contacts end with WrongSide. The remaining attempts end at SecondBounce without an accepted face contact.

The no-progress control made 7/15 contacts at 25 cm under each target, also without crossing the net. Thus the new reward did not improve contact acquisition or turn these contacts into returns. Larger rightward offsets have no accepted contacts in any of the four compared models.

These are paired development feeds, not independent repeated trials. The offset is nominal feed displacement, not required body travel. WrongSide is the rule engine's wrong-half landing fault; summary data does not identify whether the outgoing ball lacked forward velocity, hit the net, or had insufficient height. No-contact data likewise does not establish a reach limitation.

Next: record time-resolved ball, root, joint/action, paddle-face, and contact trajectories for representative 25 cm rightward misses and contacts, retaining exact policy/seed/target identities. Compare against nearby successful feeds and the prior control. Use the trace to distinguish positioning/timing, swing orientation, and post-contact trajectory before choosing another training change. Broader movement remains part of the goal; these traces diagnose the earliest failing stage.

No new training or simulation was run for this diagnosis. No acceptance seeds were consumed. The raw evaluation files remain unchanged. Machine-readable counts, seeds and input hashes are in `research/hierarchy-v1/movement-progress-01/diagnosis/rightward-progress-diagnosis.json`.
