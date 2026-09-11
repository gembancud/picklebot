using UnityEngine;

namespace Picklebot.PlayerControls
{
    // A visible flat-ground motor fixture, not a pickleball match or trained AI.
    public sealed class PlayerControlLab : MonoBehaviour
    {
        private readonly PlayerControlWorld world = new PlayerControlWorld();
        private readonly Transform[] bodies = new Transform[4], headings = new Transform[4];
        private readonly Material[] materials = new Material[4];
        private readonly Transform[,] legs=new Transform[4,6];
        private int selected;
        private float budget;
        public PlayerControlState StateFor(int player) => world.StateFor(player);
        public int PhysicsSteps { get; private set; }

        private void Start()
        {
            for(int i=0;i<4;i++)
            {
                var body=GameObject.CreatePrimitive(PrimitiveType.Capsule);body.name="Control fixture player "+(i+1);
                body.transform.SetParent(transform);Destroy(body.GetComponent<Collider>());bodies[i]=body.transform;
                materials[i]=new Material(Shader.Find("Standard")){color=i<2?new Color(1,.45f,.15f):new Color(.2f,.7f,1)};
                body.GetComponent<Renderer>().sharedMaterial=materials[i];
                var heading=GameObject.CreatePrimitive(PrimitiveType.Cube);heading.name="Facing marker "+(i+1);
                heading.transform.SetParent(transform);Destroy(heading.GetComponent<Collider>());headings[i]=heading.transform;
                heading.GetComponent<Renderer>().sharedMaterial=materials[i];
                for(int part=0;part<6;part++)
                {
                    var go=GameObject.CreatePrimitive(part<4?PrimitiveType.Capsule:PrimitiveType.Cube);
                    go.name="Articulated leg or shoe "+part;go.transform.SetParent(transform);
                    Destroy(go.GetComponent<Collider>());go.GetComponent<Renderer>().sharedMaterial=materials[i];legs[i,part]=go.transform;
                }
            }
            DrawBodies();
        }

        private void Update()
        {
            for(int i=0;i<4;i++)if(Input.GetKeyDown((KeyCode)((int)KeyCode.Alpha1+i)))selected=i;
            if(Input.GetKeyDown(KeyCode.R))
                world.Reset();
            budget+=Mathf.Min(Time.unscaledDeltaTime,.1f);
            while(budget>=1f/240f)
            {
                var commands=new PlayerControlCommand[4];
                for(int i=0;i<4;i++)
                {
                    var command=new PlayerControlCommand{facingYaw=world.StateFor(i).facingYaw};
                    if(i==selected)
                    {
                        command.move=new Vector2((Input.GetKey(KeyCode.D)?1:0)-(Input.GetKey(KeyCode.A)?1:0),
                            (Input.GetKey(KeyCode.W)?1:0)-(Input.GetKey(KeyCode.S)?1:0));
                        command.facingYaw+=((Input.GetKey(KeyCode.E)?1:0)-(Input.GetKey(KeyCode.Q)?1:0))*360f/240f;
                        command.sprint=Input.GetKey(KeyCode.LeftShift);command.jump=Input.GetKey(KeyCode.Space);
                        command.crouch=Input.GetKey(KeyCode.C)?1:0;
                    }
                    commands[i]=command;
                }
                world.Step(commands,1f/240f);
                budget-=1f/240f;PhysicsSteps++;
            }
            DrawBodies();
        }

        private void DrawBodies()
        {
            for(int i=0;i<4;i++)
            {
                var s=world.StateFor(i);var pose=world.PoseFor(i);float height=Mathf.Lerp(1.7f,1.05f,s.crouch);
                float trunkHeight=s.position.y+height-pose.Pelvis.y;
                bodies[i].position=pose.Pelvis+Vector3.up*(trunkHeight/2);bodies[i].localScale=new Vector3(.5f,trunkHeight/2,.5f);
                Segment(legs[i,0],pose.LeftHip,pose.LeftKnee);Segment(legs[i,1],pose.LeftKnee,pose.Left.center);
                Segment(legs[i,2],pose.RightHip,pose.RightKnee);Segment(legs[i,3],pose.RightKnee,pose.Right.center);
                Shoe(legs[i,4],pose.Left);Shoe(legs[i,5],pose.Right);
                headings[i].rotation=Quaternion.Euler(0,s.facingYaw,0);
                headings[i].position=s.position+Vector3.up*(height+.08f)+headings[i].forward*.25f;
                headings[i].localScale=new Vector3(.1f,.1f,.5f);
            }
        }

        private static void Segment(Transform part,Vector3 a,Vector3 b)
        { part.position=(a+b)/2;part.rotation=Quaternion.FromToRotation(Vector3.up,b-a);part.localScale=new Vector3(.12f,Vector3.Distance(a,b)/2,.12f); }
        private static void Shoe(Transform part,PlayerFootPose pose)
        { part.position=pose.center;part.rotation=Quaternion.Euler(0,pose.yaw,0);part.localScale=new Vector3(.13f,.11f,.28f); }

        private void OnGUI()
        {
            GUILayout.BeginArea(new Rect(16,16,750,250),GUI.skin.box);
            GUILayout.Label("PLAYER CONTROL LAB — untrained, provisional motor fixture");
            GUILayout.Label("1–4 select player | WASD move | Q/E turn | Shift sprint | C crouch | Space jump | R reset");
            GUILayout.Label("Player contacts, articulated legs and foot support enabled. Paddle and match integration pending.");
            for(int i=0;i<4;i++)
            {
                var s=world.StateFor(i);
                GUILayout.Label($"{(i==selected?">":" ")} Player {i+1}: energy {s.energy:P0} | speed {new Vector2(s.velocity.x,s.velocity.z).magnitude:F2} m/s | height {s.position.y:F2} m | {(s.grounded?(s.landingRemaining>0?"landing recovery":"grounded"):"airborne")}");
            }
            GUILayout.EndArea();
        }
        private void OnDestroy(){foreach(var material in materials)if(material!=null)Destroy(material);}
    }
}
