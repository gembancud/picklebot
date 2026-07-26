using UnityEngine;

namespace Picklebot.Simulation
{
    public enum CollisionEntityKindV0
    {
        Floor,
        Net,
        ControlledPaddle,
        Other
    }

    public sealed class CollisionIdentityV0 : MonoBehaviour
    {
        [SerializeField] private CollisionEntityKindV0 kind = CollisionEntityKindV0.Other;
        [SerializeField] private int stableEntityId = 1000;

        public CollisionEntityKindV0 Kind => kind;
        public int StableEntityId => stableEntityId;

        public void Configure(CollisionEntityKindV0 entityKind, int entityId)
        {
            kind = entityKind;
            stableEntityId = entityId;
        }
    }
}
