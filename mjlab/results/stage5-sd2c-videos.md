# Stage 5 S-D2c video diagnosis (`student-swing-d2c/model_3900`)

Date: 2026-10-07. Ghost-ball shadow swings, dev seed 4,200,229, 8 s per clip, env 0 of 2, side and behind views. Clips: `mjlab/artifacts/videos/stage5/sd2c-{reach_short,reach_deep,reach_backhand,easy_forehand}-{side,behind}.mp4` (local; all eight sent to the user). The ball passes through the paddle by design.

| Family | What the robot does |
|---|---|
| easy_forehand | Compact, balanced forehand at a ball it reaches without moving. |
| reach_short | Stays near its start spot, swings early and twists its body; the ball bounces twice in front of it. No forward steps. |
| reach_deep | Leans back and lifts a knee as the lob passes overhead, then swings forward toward the net after the ball is already behind it. No backward steps. |
| reach_backhand | A deep, low lunge to the left without crossing over, then it tips backward and flails its arms to regain balance. |

**User's observation (2026-10-07):**
- the robot lacks proper balancing movement: after a risky swing it drifts and struggles to find its footing;
- it reaches with a backhand-like swipe instead of a proper stroke.

## Measured hint and drill flaws (`artifacts/eval/hint_clamp.py`, offline, all start depths)
| Family | Hint stance x (median) | Hint clamped by SPOT_BOX | Travel needed (median) |
|---|---:|---:|---:|
| reach_deep | −8.7 to −9.2 m (2–2.5 m behind the baseline) | **100 %** | 2.9–3.8 m |
| reach_short | −2.9 to −4.5 m | 0 % | **1.8–2.1 m** |
| reach_backhand / reach_forehand / deep | from the back start depth (−6.3 m) | **99 %** | 1.2–1.5 / 0.2–0.4 m |
| easy_forehand | from the back start depth | 22 % | 0.2 m |

1. **The deep-ball hint aimed at the wrong point.** It used where the ball descends back through 0.8 m after the bounce, which for high-bouncing lobs is 2–2.5 m behind the baseline. A player takes such a ball earlier, near the top of the bounce or on the rise.
2. **The spot box stops at x = −6.4 m, inside the baseline (−6.7 m).** Every deep hint, and almost every hint for robots starting at the back of the start box, was clamped to the box edge, so it said roughly "stay here". Players routinely stand behind the baseline.
3. **reach_short needs about 1.8–2.1 m of travel in well under a second**, more than the 0.5–1.5 m the family was designed for.

## Implications for Drill 3 (changes to make before it is built)
- **Interception point:** target the ball near the top of its bounce, clamped to a comfortable paddle height (about 0.7–1.1 m), instead of where it descends through 0.8 m.
- **Spot box:** extend behind the baseline (x down to about −8.5 m), and keep the sidelines plus margin.
- **Reach curriculum:** start every reach family at a fraction of its travel, just past arm reach, and widen on success. This includes reach_short's distance, so early balls are reachable.
- **Balance and stroke form are not addressed by any of the above.** They are the case for Stage 5B motion priors (footwork and stroke clips via AMP), which the user is considering bringing forward.
