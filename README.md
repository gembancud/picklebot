# Picklebot

**Teaching a simulated player to move, swing and play pickleball.**

Unity · ML-Agents PPO · constrained body control · independent players with shared weights

| Serve | Return after a bounce |
|:---:|:---:|
| ![Learned fixed-ball serve](docs/media/serve.gif) | ![Learned return after the ball bounces](docs/media/return.gif) |
| Volley | Two-player practice |
| ![Learned airborne return](docs/media/volley.gif) | ![Two independently controlled teammates practising a return](docs/media/paired.gif) |

Recorded policy actions from the same historical checkpoint. Paired play is an unfinished baseline. [Clips & replay details](docs/DEMO.md)

## Where it stands

| Working | Still learning |
|---|---|
| Fixed-ball serves and central returns | Wide, deep and shallow movement returns |
| Bounded shoulder, elbow, wrist and body controls | Reliable transitions between shots |
| Parallel drills, paired practice and self-play infrastructure | Sustained learned 2v2 play |

**Latest evaluation:** all four compared models kept **64/64 serves** and **64/64 on each central-return test**. A critic-clipping correction did **not** improve the main varied-return metric. [Measured results](docs/research/critic-key-comparison.md)

## Try it

Open the project in **Unity 6000.5.5f1**. Trained ONNX models and preview scenes are included.

[Unity demo guide](docs/DEMO.md) · [Training setup](docs/TRAINING_SETUP.md) · [Current checkpoint](docs/CURRENT_STATE.md)

## Next

**Strategy → execution:** a proposed two-policy design for choosing goals and coordinating movement with the swing. This checkpoint preserves the current single-actor system before that work begins.

Physics and body motion remain simplified. This is a learning prototype; match-level acceptance is still open.

[Technical archive](docs/archive/README-before-2026-09-11.md) · [Architecture history](docs/ARCHITECTURE.md) · [Decision log](docs/DECISIONS.md)
