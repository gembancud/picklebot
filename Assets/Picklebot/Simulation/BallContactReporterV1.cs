using UnityEngine;

namespace Picklebot.Simulation
{
    [RequireComponent(typeof(Rigidbody), typeof(Collider))]
    public sealed class BallContactReporterV1 : MonoBehaviour
    {
        private PicklebotEnvironmentV1 owner;

        public void Configure(PicklebotEnvironmentV1 environment)
        {
            owner = environment;
        }

        private void OnCollisionEnter(Collision collision)
        {
            if (owner == null || collision.contactCount == 0)
            {
                return;
            }

            var identity = collision.collider.GetComponentInParent<CollisionIdentityV0>();
            var contact = collision.GetContact(0);
            owner.ReportContact(
                identity,
                contact.point,
                contact.normal,
                collision.impulse.magnitude);
        }
    }
}
