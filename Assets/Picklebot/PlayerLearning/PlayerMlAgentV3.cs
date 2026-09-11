using System;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;
using Unity.MLAgents;
using Unity.MLAgents.Actuators;
using Unity.MLAgents.Sensors;
using UnityEngine;

namespace Picklebot.PlayerLearning
{
    // The framework owns policy sampling and optimization. This adapter only
    // translates physical controls and supplies this player's observations.
    public sealed class PlayerMlAgentV3 : Agent, IPlayerPolicyV3
    {
        public const string BehaviorName = "PicklebotArticulated";
        public const string ContractVersion = "mlagents-v3-124obs-16continuous-release-v1";
        public const int ContinuousCount = 16;
        private static readonly int[] Channels = {0,1,2,3,5,6,7,8,9,10,11,12,13,14,15,17};
        private Func<PlayerObservationV3> capture;
        private Func<bool> releaseAvailable;
        private PlayerActionV3 command;
        public int Seat { get; private set; }
        public bool Learning { get; set; }
        public int ObservedTick { get; private set; } = -1;
        public event Action<PlayerMlAgentV3, ActionBuffers> Received;
        public int DecisionsReceived { get; private set; }
        public PlayerObservationV3 LastObservation { get; private set; }
        public PlayerActionV3 LastCommand => command;
        // Test/manual control only, never enabled by the training launcher.
        public float[] HeuristicControls;
        public int HeuristicRelease;
        string IPlayerPolicyV3.Name => "ML-Agents " + Seat;

        public void Bind(int seat, Func<PlayerObservationV3> observation, Func<bool> canRelease)
        {
            if (seat < 0 || seat > 3 || observation == null || canRelease == null)
                throw new ArgumentException("A private player observation source is required.");
            Seat = seat; capture = observation; releaseAvailable = canRelease;
        }
        public override void Initialize() { MaxStep = 0; }
        public override void OnEpisodeBegin() { ClearCommand(); }
        public void ClearCommand() { command = default; ObservedTick = -1; }
        void IPlayerPolicyV3.Reset() { ClearCommand(); }
        public override void CollectObservations(VectorSensor sensor)
        {
            if (capture == null) throw new InvalidOperationException("Agent was enabled before binding.");
            LastObservation = capture().Copy();
            if (LastObservation.player != Seat) throw new InvalidOperationException("Private observation identity mismatch.");
            ObservedTick = LastObservation.tick;
            sensor.AddObservation(LastObservation.ToArray());
        }
        public override void WriteDiscreteActionMask(IDiscreteActionMask mask)
        { mask.SetActionEnabled(0, 1, Learning && releaseAvailable()); }

        public static PlayerActionV3 Decode(ActionBuffers actions, bool canRelease)
        {
            if (actions.ContinuousActions.Length != ContinuousCount || actions.DiscreteActions.Length != 1)
                throw new ArgumentException("Expected 16 continuous controls and one release branch.");
            int release = actions.DiscreteActions[0];
            if (release < 0 || release > 1) throw new ArgumentException("Invalid release action.");
            var values = new float[PlayerActionV3.Count];
            for (int i = 0; i < Channels.Length; i++)
            {
                float value = actions.ContinuousActions[i];
                if (!float.IsFinite(value)) throw new ArgumentException("Non-finite action.");
                value = Mathf.Clamp(value, -1, 1);
                int channel = Channels[i];
                values[channel] = channel == 3 || channel == 5 || channel == 17 ? (value + 1) * .5f : value;
            }
            values[16] = canRelease ? release : 0;
            // Grounded V3 already excludes the physically infeasible jump action.
            values[4] = 0;
            return new PlayerActionV3(values);
        }
        public override void OnActionReceived(ActionBuffers actions)
        {
            if (!Learning) throw new InvalidOperationException("Inactive drill player received a decision.");
            command = Decode(actions, releaseAvailable());
            DecisionsReceived++;
            Received?.Invoke(this, actions);
        }
        PlayerActionV3 IPlayerPolicyV3.Decide(PlayerObservationV3 observation, System.Random random)
        {
            if (!Learning) return default;
            if (observation.player != Seat || observation.tick != ObservedTick)
                throw new InvalidOperationException("ML-Agents decision and body clock disagree.");
            return command;
        }
        public override void Heuristic(in ActionBuffers actions)
        {
            actions.ContinuousActions.Clear(); actions.DiscreteActions.Clear();
            var continuous = actions.ContinuousActions;
            // Exact zero physical command after mapping positive-only channels.
            continuous[3] = continuous[4] = continuous[15] = -1;
            if (HeuristicControls != null)
            {
                if (HeuristicControls.Length != ContinuousCount) throw new ArgumentException("Heuristic shape mismatch.");
                for (int i = 0; i < ContinuousCount; i++) continuous[i] = HeuristicControls[i];
            }
            var discrete = actions.DiscreteActions;
            discrete[0] = HeuristicRelease;
        }
    }
}
