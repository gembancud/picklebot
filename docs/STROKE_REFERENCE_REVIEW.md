# Stroke reference for Picklebot

Reviewed the actual photographs in the USTA manual, not just the extracted text.

- [USTA forehand sequence, page 88](https://www.usta.com/es/content/dam/usta/sections/southern/pdf/net-generation-high-school-team-tennis-manual.pdf#page=88): seven photographed phases and eastern-grip close-ups. The turn, loading, contact and extension are distinguishable stages.
- [USTA continental grip and volleys, page 92](https://www.usta.com/es/content/dam/usta/sections/southern/pdf/net-generation-high-school-team-tennis-manual.pdf#page=92): close-ups of the handle in the hand, plus separate forehand/backhand sequences. This is a different stroke from the forehand groundstroke.
- [USA Pickleball fundamentals](https://usapickleball.org/pickleball-skills/level-one/pickleball-fundamentals-for-beginners/): continental grip guidance, upward paddle tip in ready position, and compact preparation.

## Implications for our implementation

The current four-pose preview is not an accepted reference. Its hand coordinate convention, fixed 90-degree neutral handle angle and bevel setting were prototype choices, not measurements established by these sources. Passing their tests establishes mathematical consistency only.

Before changing more angles:

1. Represent the palm, thumb side, knuckle line, handle axis, paddle edge and face normal explicitly. A sphere cannot make grip orientation reviewable.
2. Establish the handle-in-hand transform from grip close-ups separately from the wrist posture. Do not infer it solely from where the face should point at contact.
3. Replace the four arbitrary targets with a reference-linked sequence. Distinguish initial preparation from late loading rather than treating all of the backswing as one pose.
4. Compare tip and edge directions relative to the hand, torso and court at each phase. Show side and front views, plus the intended ball/contact location.
5. Keep joint limits and motors, but do not call their numerical limits anatomically calibrated. Preserve distinct forearm rotation and wrist bending.
6. Use pickleball proportions and compactness. The tennis photographs guide the decomposition, not a direct transfer of stroke scale or grip choice.

Historical status at reference review: 217 editor passes and 8/10 physical integration passes. Subsequent results and outstanding failures are recorded in ARTICULATED_PLAYER_CONTROLS.md; these counts are not current acceptance evidence.
