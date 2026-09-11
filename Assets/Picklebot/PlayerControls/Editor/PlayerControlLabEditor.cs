using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Picklebot.PlayerControls.Editor
{
    public static class PlayerControlLabEditor
    {
        public const string Path="Assets/Picklebot/Scenes/PlayerControlLab.unity";
        [MenuItem("Picklebot/Controls/Create Control Lab")]
        public static string Create()
        {
            if(EditorApplication.isPlaying)throw new System.InvalidOperationException("Leave Play first.");
            if(SceneManager.GetActiveScene().isDirty)throw new System.InvalidOperationException("Save or discard the current scene yourself first.");
            if(System.IO.File.Exists(Path))throw new System.InvalidOperationException("Control lab already exists; open it instead.");
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var ground=GameObject.CreatePrimitive(PrimitiveType.Plane);ground.name="Flat ground fixture";ground.transform.localScale=new Vector3(2,1,2);
            var cameraObject=new GameObject("Main Camera");cameraObject.tag="MainCamera";
            var camera=cameraObject.AddComponent<Camera>();cameraObject.transform.position=new Vector3(0,14,-13);cameraObject.transform.LookAt(Vector3.zero);
            camera.orthographic=true;camera.orthographicSize=7.5f;camera.backgroundColor=new Color(.08f,.10f,.12f);
            var lightObject=new GameObject("Directional Light");lightObject.AddComponent<Light>().type=LightType.Directional;lightObject.transform.rotation=Quaternion.Euler(50,-30,0);
            new GameObject("Four independent control states").AddComponent<PlayerControlLab>();
            EditorSceneManager.SaveScene(scene,Path);return Path;
        }
    }
}
