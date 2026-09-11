using System;
using System.Security.Cryptography;
using System.Text;
using Picklebot.Doubles;
namespace Picklebot.PlayerControlsIntegration
{
    // Immutable validated residuals may be shared; each player owns its planner.
    public sealed class PlayerContactCalibrationV2
    {
        private readonly ContactParameters[] strokes;
        public string Hash {get;}
        private PlayerContactCalibrationV2(ContactModel model,string hash)
        {Hash=hash;strokes=Array.ConvertAll(model.strokes,p=>p.Copy());}
        public static PlayerContactCalibrationV2 Load(string json,string expectedHash)
        {
            if(json==null||string.IsNullOrEmpty(expectedHash))throw new ArgumentException("Calibration and expected checkpoint hash are required.");
            string hash;
            using(var sha=SHA256.Create())hash=BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(json.Replace("\r\n","\n").Replace("\r","\n")))).Replace("-","").ToLowerInvariant();
            if(!string.Equals(hash,expectedHash,StringComparison.OrdinalIgnoreCase))throw new ArgumentException("Contact calibration does not match checkpoint provenance.");
            return new PlayerContactCalibrationV2(ContactModel.Load(json),hash);
        }
        public void Apply(StrokeKind kind,StrokeController controller)
        {
            if((int)kind<0||(int)kind>=strokes.Length||controller==null)throw new ArgumentException("Invalid stroke or controller.");
            strokes[(int)kind].Apply(controller);
        }
    }
}
