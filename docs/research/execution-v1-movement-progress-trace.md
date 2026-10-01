# Movement-progress trace findings

All 512 replay episodes, target/landing rows and first observations/actions matched the original final-model target-A evaluation byte-for-byte. Five selected cases record each physics tick before stepping. The instrumented replay made no simulation or reward changes.

| Case | Seed | Root lateral movement by closest approach, canonical metres | First accepted-contact forward ball speed, m/s |
|---|---:|---:|---:|
| Right air miss | 1109945 | -0.207 | No accepted contact |
| Right bounce-feed miss | 1109899 | -0.180 | No accepted contact |
| Right bounce-feed failed contact | 1109964 | -0.168 | -0.155 |
| Shallow air success | 1109881 | -0.223 | 8.258 |
| Shallow bounce-feed success | 1109963 | -0.207 | 8.457 |

Positive canonical x is right. Both rightward misses move left by roughly18–21cm before closest approach. Similar movement in the successful shallow examples suggests reuse of a familiar movement pattern; this is an inference from five cases, not proof of why the policy chose it. Arm joints move substantially across each recorded attempt; a globally frozen arm is not the explanation.

The rightward contact leaves with approximately -0.155m/s forward velocity and0.346m/s upward velocity, versus roughly8m/s forward in the two successful examples. This isolates a poor contact outcome; it does not by itself attribute the fault to face orientation or relative surface velocity.

Next: inspect the pre-contact observation/action response to lateral feed differences and the contact-relative paddle velocity and face normal. Address contact acquisition separately from the post-contact return objective. Do not repeat a position bonus or smaller-feed curriculum without comparing it with the already failed interventions. Broader movement, skill retention and target-following remain required.

Limitations: five descriptive cases selected by lowest seed in available task/direction/contact strata; differing seats and feeds are not controlled interventions. Paddle-centre distance is not collision-surface clearance. Contact velocity is sampled on the next pre-step and terminal pose can be omitted on reset. No final acceptance seeds or new training were used.

Raw traces are preserved losslessly in `research/hierarchy-v1/movement-progress-trace-01/trace.json.gz`; the adjacent manifest, scripts and analysis identify the exact model/template and replay parity.
