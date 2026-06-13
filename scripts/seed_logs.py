"""Generate realistic sample log batches and POST them to the running API.

Usage:
    python scripts/seed_logs.py [--api http://localhost:8000] [--scenario lateral_movement]
"""

import argparse
import json
import sys
from pathlib import Path

import httpx

FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_logs"
SCENARIOS = [p.stem for p in FIXTURES.glob("*.json")]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--scenario", choices=SCENARIOS, default=None,
                        help="Seed one scenario (default: all)")
    args = parser.parse_args()

    targets = [args.scenario] if args.scenario else SCENARIOS
    for name in targets:
        batch = json.loads((FIXTURES / f"{name}.json").read_text())
        response = httpx.post(f"{args.api}/ingest", json=batch, timeout=30)
        response.raise_for_status()
        payload = response.json()
        print(f"[{name}] job_id={payload['job_id']}  →  {args.api}/stream/{payload['job_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
