using UnityEngine;
namespace Picklebot.Inspection
{
    public sealed class InspectionContacts:MonoBehaviour
    {
        public InspectionWorld World;
        private void OnCollisionEnter(Collision collision)
        {
            if(collision.contactCount>0) { var c=collision.GetContact(0);World?.Contact(collision.collider,c.point,c.normal); }
        }
    }
}
