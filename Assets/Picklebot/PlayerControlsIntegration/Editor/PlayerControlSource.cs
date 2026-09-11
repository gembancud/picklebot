using System.IO;
using System.Linq;
using Picklebot.Doubles.Editor;
using Picklebot.PlayerAgents.Editor;

namespace Picklebot.PlayerControlsIntegration.Editor
{
    public static class PlayerControlSource
    {
        public static string SourceHash()=>ContactTraining.Hash(PlayerDiagnostics.SourceHash()+"\n"+ContactTraining.SourceText(
            new[]{"Assets/Picklebot/PlayerControls","Assets/Picklebot/PlayerControlsIntegration"}
                .SelectMany(p=>Directory.GetFiles(p,"*.cs",SearchOption.AllDirectories))
                .Where(p=>!ContactTraining.CanonicalPath(p).Contains("/Tests/"))));
    }
}
