from __future__ import annotations

import unittest

from vanderpol.algorithms import all_algorithms
from vanderpol.experiments import observe_patient
from vanderpol.simulator import GoisSaviSimulator
from vanderpol.types import RhythmScenario


class AlgorithmTests(unittest.TestCase):
    def test_all_algorithms_run_and_emit_bounded_protocols(self) -> None:
        simulator = GoisSaviSimulator(fs_hz=250)
        patient, observation, _ = observe_patient(
            simulator,
            RhythmScenario.MONOMORPHIC_VT,
            seed=123,
            observation_s=4.0,
        )
        for algorithm in all_algorithms():
            result = algorithm.run(patient, observation, simulator, horizon_s=3.0)
            self.assertEqual(result.action_id, algorithm.action_id)
            self.assertGreaterEqual(result.energy, 0.0)
            self.assertLessEqual(max(result.protocol.amplitudes or (0.0,)), 7.0)
            self.assertGreaterEqual(result.time_to_termination_s, 0.0)
            self.assertLessEqual(result.time_to_termination_s, 3.0)


if __name__ == "__main__":
    unittest.main()
