using System;
using UnityEngine;
namespace Picklebot.Doubles
{
    [Serializable] public sealed class ContactParameters
    {
        public float pitch,timing,brushBias,speed=1,brush=1;
        public void Apply(StrokeController stroke) {stroke.PitchBias=pitch;stroke.TimingBias=timing;stroke.SpeedScale=speed;stroke.BrushScale=brush;stroke.BrushBias=brushBias;}
        public ContactParameters Copy()=>new(){pitch=pitch,timing=timing,speed=speed,brush=brush,brushBias=brushBias};
    }
    [Serializable] public sealed class ContactModel
    {
        public string version="doubles-contact-residual-v2",method="Unity contact parameter search with scripted interception",sourceHash,configurationHash,createdUtc;
        public int seed,trials;
        public ContactParameters[] strokes={new(),new(),new()};
        public static ContactModel Load(string json)
        {
            var model=JsonUtility.FromJson<ContactModel>(json);
            if(model?.version!="doubles-contact-residual-v2"||model.strokes?.Length!=3)throw new ArgumentException("Invalid contact model.");
            foreach(var p in model.strokes)if(p==null||!float.IsFinite(p.pitch)||!float.IsFinite(p.timing)||!float.IsFinite(p.speed)||!float.IsFinite(p.brush)||!float.IsFinite(p.brushBias)||Mathf.Abs(p.brushBias)>6||Mathf.Abs(p.pitch)>20||Mathf.Abs(p.timing)>.05f||p.speed<.5f||p.speed>1.5f||p.brush<.1f||p.brush>2)throw new ArgumentException("Invalid contact parameters.");
            return model;
        }
    }
}
