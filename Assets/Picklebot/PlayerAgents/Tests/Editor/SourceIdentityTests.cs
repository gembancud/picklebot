using System.Collections.Generic;
using NUnit.Framework;
using Picklebot.Doubles.Editor;

namespace Picklebot.PlayerAgents.Tests
{
    public sealed class SourceIdentityTests
    {
        [Test] public void WindowsPathsAndLineEndingsMatchPosix()
        {
            var posix = new[] { new KeyValuePair<string,string>("Assets/A.cs", "a\nb\n"), new KeyValuePair<string,string>("Assets/nested/B.cs", "c\n") };
            var windows = new[] { new KeyValuePair<string,string>(@"Assets\nested\B.cs", "c\r"), new KeyValuePair<string,string>(@"Assets\A.cs", "a\r\nb\r\n") };
            Assert.AreEqual(ContactTraining.SourceRecordText(posix), ContactTraining.SourceRecordText(windows));
        }

        [Test] public void OrdinalOrderingAndSourceChangesArePreserved()
        {
            var records = new[] { new KeyValuePair<string,string>("a.cs", "a"), new KeyValuePair<string,string>("Z.cs", "z") };
            string text = ContactTraining.SourceRecordText(records);
            Assert.AreEqual("Z.cs\nz\na.cs\na", text);
            Assert.AreNotEqual(ContactTraining.Hash(text), ContactTraining.Hash(text + "changed"));
        }
    }
}
