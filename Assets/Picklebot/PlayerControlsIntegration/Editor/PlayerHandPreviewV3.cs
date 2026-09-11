using UnityEngine;
namespace Picklebot.PlayerControlsIntegration.Editor
{
    // Diagnostic geometry only. No finger joints, colliders, or anatomical calibration.
    public static class PlayerHandPreviewV3
    {
        public static Transform Create(Transform parent,Material skin,Material thumb)
        {
            var root=new GameObject("Grip review / schematic hand");root.transform.SetParent(parent,false);
            Shape(root.transform,"Palm",PrimitiveType.Cube,new Vector3(0,.018f,-.027f),new Vector3(.075f,.055f,.018f),skin);
            for(int finger=0;finger<4;finger++)
            {
                float x=-.027f+finger*.018f;
                for(int segment=0;segment<5;segment++)
                {
                    float a=(-90+segment*50)*Mathf.Deg2Rad,b=(-90+(segment+1)*50)*Mathf.Deg2Rad;
                    var first=new Vector3(x,-.025f*Mathf.Cos(a),.025f*Mathf.Sin(a));
                    var last=new Vector3(x,-.025f*Mathf.Cos(b),.025f*Mathf.Sin(b));
                    Segment(root.transform,"Curled finger",first,last,.007f,skin);
                }
            }
            Segment(root.transform,"Thumb marker",new Vector3(.044f,.032f,-.015f),new Vector3(.02f,-.005f,.028f),.009f,thumb);
            return root.transform;
        }
        private static void Segment(Transform parent,string name,Vector3 a,Vector3 b,float radius,Material material)
        {
            var t=Shape(parent,name,PrimitiveType.Capsule,(a+b)*.5f,new Vector3(2*radius,(b-a).magnitude*.5f,2*radius),material);
            t.localRotation=Quaternion.FromToRotation(Vector3.up,b-a);
        }
        private static Transform Shape(Transform parent,string name,PrimitiveType type,Vector3 position,Vector3 scale,Material material)
        {
            var o=GameObject.CreatePrimitive(type);o.name=name;o.layer=30;o.transform.SetParent(parent,false);
            o.transform.localPosition=position;o.transform.localScale=scale;o.GetComponent<Renderer>().sharedMaterial=material;
            Object.DestroyImmediate(o.GetComponent<Collider>());return o.transform;
        }
    }
}
