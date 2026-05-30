from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.features import classify_acls_features
from vanderpol.experiments import observe_patient
from vanderpol.simulator import GoisSaviSimulator
from vanderpol.types import RhythmScenario


def main() -> None:
    simulator = GoisSaviSimulator(fs_hz=250)
    rows = []
    for idx, scenario in enumerate(RhythmScenario):
        patient, observation, trace = observe_patient(
            simulator,
            scenario,
            seed=100 + idx,
            observation_s=4.0,
            variability=0.2,
        )
        rows.append(
            {
                "scenario": patient.rhythm.value,
                "samples": int(len(trace.ecg)),
                "acls_label": classify_acls_features(observation.features),
                "features": {
                    key: round(value, 4)
                    for key, value in observation.features.items()
                },
            }
        )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
