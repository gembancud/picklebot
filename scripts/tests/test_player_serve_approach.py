from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from player_serve_approach import geometry, paired_prefix


class ServeApproachTests(unittest.TestCase):
    def observation(self, x=0):
        o=[0.]*54; o[0]=x; o[40]=1; return o

    def test_geometry_preserves_absolute_ball_when_feet_move(self):
        a=self.observation(); b=self.observation(.5); b[4]=-.25
        self.assertEqual(geometry(a)["ball"],geometry(b)["ball"])
        self.assertAlmostEqual(geometry(b)["feet"][0],2.1)

    def test_rejects_nonfinite_geometry(self):
        o=self.observation(); o[25]=float("nan")
        with self.assertRaises(ValueError): geometry(o)

    def test_excludes_contact_time_and_nonserve_phase(self):
        rows=[dict(observationTick=t,observation=self.observation()) for t in (12,24,36)]
        rows[0]["observation"][40]=0
        pairs,error=paired_prefix(rows,rows,.15)
        self.assertEqual([a["observationTick"] for a,t in pairs],[24])
        self.assertEqual(error,0)

    def test_rejects_divergent_ball_paths(self):
        a=[dict(observationTick=12,observation=self.observation())]
        b=[dict(observationTick=12,observation=self.observation(.5))]
        with self.assertRaisesRegex(ValueError,"ball paths"):
            paired_prefix(a,b,1)


if __name__ == "__main__": unittest.main()
