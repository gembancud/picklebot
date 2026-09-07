using System;
using System.IO;
using Picklebot.Doubles.Editor;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Picklebot.PlayerAgents.Editor
{
    public static class PlayerScene
    {
        public const string ScenePath = "Assets/Picklebot/Scenes/IndependentPlayers.unity";

        [MenuItem("Picklebot/Player agents/Open control probe")]
        public static void Open()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Stop Play first.");
            if (UnityEngine.SceneManagement.SceneManager.GetActiveScene().isDirty)
                throw new InvalidOperationException("Save the current scene before switching scenes.");
            if (File.Exists(ScenePath)) { EditorSceneManager.OpenScene(ScenePath); return; }
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var demo = new GameObject("Independent player control probe").AddComponent<PlayerAgentsDemo>();
            demo.ContactAsset = AssetDatabase.LoadAssetAtPath<TextAsset>(ContactTraining.ModelPath);
            var camera = new GameObject("Main Camera").AddComponent<Camera>(); camera.tag = "MainCamera";
            camera.orthographic = true; camera.orthographicSize = 9.1f;
            camera.transform.position = new Vector3(10, 12, -13); camera.transform.LookAt(new Vector3(0, .4f, 0));
            camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = new Color(.04f, .07f, .1f);
            camera.gameObject.AddComponent<AudioListener>();
            var light = new GameObject("Sun").AddComponent<Light>(); light.type = LightType.Directional;
            light.intensity = 1.4f; light.transform.rotation = Quaternion.Euler(50, -30, 0);
            RenderSettings.ambientLight = new Color(.5f, .5f, .5f);
            EditorSceneManager.SaveScene(scene, ScenePath);
        }
    }
}
