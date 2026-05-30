from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.data.manifest import EXTERNAL_DATASETS


def main() -> None:
    print(
        json.dumps(
            [dataset.__dict__ for dataset in EXTERNAL_DATASETS],
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
