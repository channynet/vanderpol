from __future__ import annotations

import unittest

import numpy as np

from vanderpol.bandit import LinUCB, mean_oracle_gap, oracle_actions
from vanderpol.experiments import run_algorithm_matrix
from vanderpol.reward import RewardWeights, episode_reward
from vanderpol.types import EpisodeResult, PatientParams, RhythmScenario, StimulusProtocol


class RewardSelectorTests(unittest.TestCase):
    def _result(
        self,
        success: bool,
        energy: float,
        rhythm: RhythmScenario = RhythmScenario.MONOMORPHIC_VT,
        safety_violations: int = 0,
        time_to_termination_s: float = 1.0,
    ) -> EpisodeResult:
        patient = PatientParams(
            rhythm=rhythm,
            seed=1,
            sa_frequency_hz=1.0,
            av_frequency_hz=1.0,
            hp_frequency_hz=3.0,
            mu_sa=1.0,
            mu_av=1.0,
            mu_hp=1.0,
            coupling_sa_av=0.1,
            coupling_av_hp=0.1,
            coupling_hp_sa=0.1,
            delay_sa_av_s=0.1,
            delay_av_hp_s=0.1,
            qrs_width_s=0.14,
            noise_std=0.01,
            artifact_level=0.01,
            treatment_sensitivity=1.0,
            phase_sensitivity=1.0,
            energy_tolerance=1.0,
            irregularity=0.05,
        )
        protocol = StimulusProtocol(
            name="test",
            pulse_times_s=(0.1,),
            amplitudes=(energy,),
            pulse_width_s=1.0,
        )
        return EpisodeResult(
            algorithm="test",
            action_id=0,
            patient=patient,
            success=success,
            restored_rhythm=RhythmScenario.NSR if success else patient.rhythm,
            energy=energy,
            time_to_termination_s=time_to_termination_s,
            safety_violations=safety_violations,
            protocol=protocol,
            trace_summary={},
        )

    def test_reward_ranks_success_but_ignores_energy_by_default(self) -> None:
        weights = RewardWeights()
        success_low = episode_reward(self._result(True, 1.0), weights)
        success_high = episode_reward(self._result(True, 3.0), weights)
        failure_low = episode_reward(self._result(False, 1.0), weights)
        self.assertGreater(success_low, failure_low)
        self.assertEqual(success_low, success_high)

    def test_time_penalty_uses_current_default_weight(self) -> None:
        weights = RewardWeights()
        fast = episode_reward(self._result(True, 1.0, time_to_termination_s=1.0), weights)
        slow = episode_reward(self._result(True, 1.0, time_to_termination_s=4.0), weights)
        self.assertAlmostEqual(fast - slow, 3.0)

    def test_energy_does_not_affect_reward_for_any_hidden_rhythm_label(self) -> None:
        weights = RewardWeights()
        normal_delta = episode_reward(
            self._result(True, 1.0, RhythmScenario.MONOMORPHIC_VT), weights
        ) - episode_reward(
            self._result(True, 3.0, RhythmScenario.MONOMORPHIC_VT), weights
        )
        polymorphic_delta = episode_reward(
            self._result(True, 1.0, RhythmScenario.POLYMORPHIC_VT), weights
        ) - episode_reward(
            self._result(True, 3.0, RhythmScenario.POLYMORPHIC_VT), weights
        )
        vf_delta = episode_reward(
            self._result(True, 1.0, RhythmScenario.VF_LIKE), weights
        ) - episode_reward(
            self._result(True, 3.0, RhythmScenario.VF_LIKE), weights
        )

        self.assertAlmostEqual(normal_delta, 0.0)
        self.assertAlmostEqual(polymorphic_delta, 0.0)
        self.assertAlmostEqual(vf_delta, 0.0)

    def test_default_reward_ignores_heuristic_safety_violations(self) -> None:
        weights = RewardWeights()
        no_violation = episode_reward(
            self._result(True, 1.0, safety_violations=0), weights
        )
        heuristic_violation = episode_reward(
            self._result(True, 1.0, safety_violations=2), weights
        )
        self.assertEqual(no_violation, heuristic_violation)

    def test_linucb_smoke_is_deterministic(self) -> None:
        _, _, contexts, rewards, _ = run_algorithm_matrix(patients_per_scenario=1)
        oracle = oracle_actions(rewards)
        model = LinUCB(n_actions=5, n_features=contexts.shape[1], alpha=0.0)
        for idx, x in enumerate(contexts):
            for action in range(5):
                model.update(action, x, rewards[idx, action])
        chosen = model.predict_many(contexts)
        self.assertEqual(chosen.shape, oracle.shape)
        self.assertTrue(np.isfinite(mean_oracle_gap(chosen, rewards)))


if __name__ == "__main__":
    unittest.main()
