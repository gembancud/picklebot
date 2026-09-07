import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_brush_command import validate_parameters, validate_pair


class BrushCommandTests(unittest.TestCase):
    def setUp(self):
        self.frozen = dict(strokes=[dict(brushBias=5., pitch=2., speed=1.) for _ in range(3)])
        self.report = dict(version="player-brush-command-v1", flatBrushBias=0., flatPitchOffsetDegrees=0.,
            experimentalContactOverride=True, candidateContactParameters=copy.deepcopy(self.frozen["strokes"]))
        self.report["candidateContactParameters"][0]["brushBias"] = 0.

    def test_only_flat_brush_can_change(self):
        validate_parameters(self.report, self.frozen)
        for kind, field in ((0,"pitch"),(0,"speed"),(1,"brushBias"),(2,"brushBias")):
            bad = copy.deepcopy(self.report); bad["candidateContactParameters"][kind][field] += 1
            with self.assertRaises(ValueError): validate_parameters(bad,self.frozen)

    def test_control_must_be_labelled_unchanged(self):
        self.report.update(flatBrushBias=5.,candidateContactParameters=copy.deepcopy(self.frozen["strokes"]),experimentalContactOverride=False)
        validate_parameters(self.report,self.frozen)
        self.report["experimentalContactOverride"] = True
        with self.assertRaises(ValueError): validate_parameters(self.report,self.frozen)

    def test_invalid_commands_and_hidden_pitch_are_rejected(self):
        for field,value in (("flatBrushBias",True),("flatBrushBias",2),("flatBrushBias",float("nan")),("flatPitchOffsetDegrees",1)):
            bad=copy.deepcopy(self.report);bad[field]=value
            with self.assertRaises(ValueError):validate_parameters(bad,self.frozen)

    def test_nonfinite_parameters_are_rejected(self):
        for value in (float("nan"),float("inf"),True):
            bad=copy.deepcopy(self.report);bad["candidateContactParameters"][1]["pitch"]=value
            with self.assertRaises(ValueError):validate_parameters(bad,self.frozen)

    def test_missing_pair_conditions_are_rejected(self):
        with self.assertRaises(ValueError):validate_pair({}, {}, {})

    def test_pair_requires_exact_original_events(self):
        keys=("sourceHash","configurationHash","actorHash","actorTrainingSourceHash","historicalCandidate",
            "contactHash","opponentHash","baselineManifestHash","protocolHash","seedBase","caseCount",
            "maximumRalliesPerCase","sampledActor","sampledBaseline")
        original={k:k for k in keys};original.update(rallies=[{"event":"hit"}],games=[{"score":[1,2]}])
        control=dict(original,flatBrushBias=5,collectorHash="collector")
        candidate=dict(original,flatBrushBias=0,collectorHash="collector")
        validate_pair(original,control,candidate)
        changed=copy.deepcopy(control);changed["rallies"][0]["event"]="fault"
        with self.assertRaises(ValueError):validate_pair(original,changed,candidate)
        changed=dict(candidate,actorHash="other")
        with self.assertRaises(ValueError):validate_pair(original,control,changed)
