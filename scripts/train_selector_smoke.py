from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.bandit import LinUCB, mean_oracle_gap, oracle_actions
from vanderpol.experiments import run_algorithm_matrix


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patients-per-scenario", type=int, default=5)
    args = parser.parse_args()

    _, _, contexts, reward_matrix, acls_actions = run_algorithm_matrix(
        patients_per_scenario=args.patients_per_scenario
    )
    oracle = oracle_actions(reward_matrix)

    bandit = LinUCB(n_actions=5, n_features=contexts.shape[1], alpha=0.5)
    order = np.arange(len(contexts))
    for idx in order:
        for action in range(5):
            bandit.update(action, contexts[idx], reward_matrix[idx, action])

    chosen = bandit.predict_many(contexts)
    metrics = {
        "n_contexts": int(len(contexts)),
        "selector_oracle_match": float(np.mean(chosen == oracle)),
        "selector_oracle_gap": mean_oracle_gap(chosen, reward_matrix),
        "acls_oracle_match": float(np.mean(acls_actions == oracle)),
        "acls_oracle_gap": mean_oracle_gap(acls_actions, reward_matrix),
    }
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
