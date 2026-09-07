using UnityEngine;
namespace Picklebot.Competition
{
    public sealed class CompetitiveContacts : MonoBehaviour
    {
        public CompetitiveWorld World;
        private void OnCollisionEnter(Collision collision)
        {
            if(collision.contactCount>0) World?.Contact(collision.collider.name,collision.GetContact(0).point);
        }
    }
}
