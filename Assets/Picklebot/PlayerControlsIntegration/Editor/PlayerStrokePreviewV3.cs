using System;
using System.IO;
using System.Collections.Generic;
using Picklebot.PlayerControls;
using Picklebot.Doubles;
using UnityEngine;
using UnityEditor;
namespace Picklebot.PlayerControlsIntegration.Editor
{
    public static class PlayerStrokePreviewV3
    {
        [Serializable] public sealed class Sample
        {
            public string phase;
            public float time,faceSpeed;
            public Vector3 torsoAngles,shoulder,elbow,hand,face,faceNormal,tipDirection;
            public float[] armAngles;
        }
        [Serializable] public sealed class Report
        {
            public string note="Scripted pose review, not a learned stroke or biomechanical calibration.";
            public List<Sample> samples=new List<Sample>();
        }
        public static string Render(string directory)
        {
            if(!EditorApplication.isPlaying)throw new InvalidOperationException("Enter play mode for the isolated physics preview.");
            if(Directory.Exists(directory))throw new IOException("Use a fresh preview directory.");
            Directory.CreateDirectory(directory);
            var report=new Report();var motor=new PlayerUpperBodyMotorV3();
            // Phase decomposition follows USTA p88; compactness/grip guidance follows
            // USA Pickleball fundamentals. Joint values are prototype fits, not measured motion capture.
            var names=new[]{"ready","unit-turn","loading","forward-swing","contact-pose","extension","finish","recovery"};
            var torsoTargets=new[]{Vector3.zero,new Vector3(30,5,0),new Vector3(40,10,0),new Vector3(20,10,0),
                new Vector3(5,10,0),new Vector3(-15,10,0),new Vector3(-40,5,0),Vector3.zero};
            var jointTargets=new[]{PlayerArmJointsV3.Ready,PlayerArmJointsV3.Ready,
                new PlayerArmJointsV3(new[]{55f,0f,20f,75f,45f,-20f,0f}),
                new PlayerArmJointsV3(new[]{-5f,5f,20f,65f,0f,10f,0f}),
                new PlayerArmJointsV3(new[]{-10f,20f,20f,50f,-5f,10f,0f}),
                new PlayerArmJointsV3(new[]{-35f,40f,20f,60f,-5f,10f,0f}),
                new PlayerArmJointsV3(new[]{-60f,55f,25f,85f,90f,-50f,-20f}),PlayerArmJointsV3.Ready};
            var counts=new[]{1,100,120,120,100,100,100,220};
            var cameraObject=new GameObject("Temporary articulated pose review camera");
            var lightObject=new GameObject("Temporary articulated pose review light");
            var rt=new RenderTexture(800,900,24);var texture=new Texture2D(800,900,TextureFormat.RGB24,false);
            var previous=RenderTexture.active;
            try
            {
                var camera=cameraObject.AddComponent<Camera>();camera.enabled=false;camera.orthographic=true;camera.orthographicSize=1.03f;
                camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.075f,.09f,.12f);camera.cullingMask=1<<30;
                camera.targetTexture=rt;camera.nearClipPlane=.01f;camera.farClipPlane=20;
                var light=lightObject.AddComponent<Light>();light.type=LightType.Directional;light.intensity=2;light.cullingMask=1<<30;
                lightObject.transform.rotation=Quaternion.Euler(35,-30,0);
                using(var match=new PlayerControlMatch(false))
                {
                    var body=match.World.Players[0];var root=match.Controls.StateFor(0);var legs=match.Controls.PoseFor(0);
                    foreach(var parent in new[]{body.Root.transform,body.Paddle.transform})
                        foreach(var transform in parent.GetComponentsInChildren<Transform>())
                        {transform.gameObject.layer=30;var renderer=transform.GetComponent<Renderer>();if(renderer!=null)renderer.enabled=true;}
                    var focus=root.position+new Vector3(0,.85f,0);
                    cameraObject.transform.position=focus+new Vector3(2.4f,1.0f,3.5f);cameraObject.transform.LookAt(focus);
                    body.Reset(root.position);int tick=0;
                    var oldHand=body.Root.transform.Find("Right hand grip");oldHand.GetComponent<Renderer>().enabled=false;
                    var handView=PlayerHandPreviewV3.Create(body.Root.transform,oldHand.GetComponent<Renderer>().sharedMaterial,
                        match.World.Players[2].Root.transform.Find("Torso").GetComponent<Renderer>().sharedMaterial);
                    for(int phase=0;phase<names.Length;phase++)
                    {
                        for(int step=0;step<counts[phase];step++)
                        {
                            motor.Step(torsoTargets[phase],jointTargets[phase]);
                            var torso=motor.Pose(legs.Pelvis,Quaternion.Euler(0,root.facingYaw,0));
                            var arm=torso.Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
                            var frame=PlayerArticulatedFrameV3.Compose(new PlayerBodyFrame{position=root.position,pelvis=legs.Pelvis,
                                leftFoot=legs.Left.center,rightFoot=legs.Right.center,leftHip=legs.LeftHip,rightHip=legs.RightHip,
                                leftKnee=legs.LeftKnee,rightKnee=legs.RightKnee},torso,arm,motor.TorsoRates,motor.ArmRates,Vector3.zero,Vector3.zero);
                            body.ApplyExternalFrame(frame,tick==0);match.World.Simulate();tick++;
                            handView.SetPositionAndRotation(arm.hand,arm.handRotation);
                            var face=arm.PaddlePoint(new Vector3(0,.0635f,0));
                            report.samples.Add(new Sample{phase=names[phase],time=tick*DoublesWorld.Dt,torsoAngles=motor.TorsoAngles,
                                armAngles=motor.ArmAngles.ToArray(),shoulder=arm.shoulder,elbow=arm.elbow,hand=arm.hand,face=face,
                                tipDirection=arm.paddleRotation*Vector3.up,faceNormal=arm.paddleRotation*Vector3.forward,faceSpeed=body.ContactVelocity(face).magnitude});
                        }
                        Physics.SyncTransforms();camera.Render();RenderTexture.active=rt;
                        texture.ReadPixels(new Rect(0,0,800,900),0,0);texture.Apply();
                        File.WriteAllBytes(Path.Combine(directory,phase+"-"+names[phase]+".png"),texture.EncodeToPNG());
                        if(phase==0)
                        {
                            var savedPosition=camera.transform.position;var savedRotation=camera.transform.rotation;
                            camera.orthographicSize=.22f;
                            camera.transform.position=handView.position+handView.rotation*new Vector3(.30f,.12f,.45f);
                            camera.transform.LookAt(handView.position+handView.right*.07f,handView.rotation*Vector3.up);
                            camera.Render();RenderTexture.active=rt;texture.ReadPixels(new Rect(0,0,800,900),0,0);texture.Apply();
                            File.WriteAllBytes(Path.Combine(directory,"grip-closeup.png"),texture.EncodeToPNG());
                            camera.orthographicSize=1.03f;camera.transform.SetPositionAndRotation(savedPosition,savedRotation);
                        }
                    }
                }
                File.WriteAllText(Path.Combine(directory,"poses.json"),JsonUtility.ToJson(report,true));
                return directory;
            }
            finally
            {
                RenderTexture.active=previous;UnityEngine.Object.DestroyImmediate(cameraObject);UnityEngine.Object.DestroyImmediate(lightObject);
                UnityEngine.Object.DestroyImmediate(texture);rt.Release();UnityEngine.Object.DestroyImmediate(rt);
            }
        }
    }
}
