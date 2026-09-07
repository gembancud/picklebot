using UnityEngine;

namespace Picklebot.Rally
{
    public sealed class RallyBallContacts : MonoBehaviour
    {
        [System.NonSerialized] public RallyWorld World;
        private void OnCollisionEnter(Collision collision)
        {
            World?.Contact(collision.collider.name, collision.GetContact(0).point);
        }
    }
}
