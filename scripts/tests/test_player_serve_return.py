from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_serve_return import event_outcome


class ServeReturnTests(unittest.TestCase):
    def test_legal_first_return_requires_both_bounces(self):
        events = [dict(kind=k, player=p) for k,p in [('serve',0),('bounce',-1),('hit',2),('bounce',-1)]]
        self.assertEqual(event_outcome(events,0,2), dict(serveLanded=True,returnHit=True,returnLanded=True))
        self.assertFalse(event_outcome(events[:-1],0,2)['returnLanded'])

    def test_fault_after_serve_is_not_a_return(self):
        events = [dict(kind='serve',player=0),dict(kind='fault',player=2)]
        self.assertEqual(event_outcome(events,0,2), dict(serveLanded=False,returnHit=False,returnLanded=False))

    def test_wrong_receiver_and_early_volley_are_rejected(self):
        for events in ([('serve',0),('hit',2)], [('serve',0),('bounce',-1),('hit',3)]):
            with self.assertRaises(ValueError): event_outcome([dict(kind=k,player=p) for k,p in events],0,2)
