from __future__ import annotations

import unittest

import numpy as np

from vanderpol.features import classify_acls_features, make_observation
from vanderpol.scenarios import sample_patient
from vanderpol.simulator import GoisSaviSimulator
from vanderpol.types import RhythmScenario


class SimulatorTests(unittest.TestCase):
    def test_all_scenarios_produce_finite_traces(self) -> None:
        simulator = GoisSaviSimulator(fs_hz=250)
        for idx, scenario in enumerate(RhythmScenario):
            patient = sample_patient(scenario, seed=idx)
            trace = simulator.simulate(patient, duration_s=4.0)
            self.assertEqual(trace.states.shape[1], 6)
            self.assertEqual(len(trace.ecg), 1000)
            self.assertTrue(np.isfinite(trace.states).all())
            self.assertTrue(np.isfinite(trace.ecg).all())

    def test_features_are_present_and_classifiable(self) -> None:
        simulator = GoisSaviSimulator(fs_hz=250)
        patient = sample_patient(RhythmScenario.MONOMORPHIC_VT, seed=42)
        trace = simulator.simulate(patient, duration_s=4.0)
        observation = make_observation(trace.ecg, trace.fs_hz)
        self.assertGreater(observation.features["heart_rate_bpm"], 0.0)
        self.assertIn("qrs_width_s", observation.features)
        self.assertIsInstance(classify_acls_features(observation.features), str)


if __name__ == "__main__":
    unittest.main()
