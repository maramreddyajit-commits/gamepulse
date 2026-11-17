import sys
from pathlib import Path

from portfolio.gamepulse import ingest

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m scripts.ingest_gamepulse INPUT.csv OUTPUT.sqlite")
    print(ingest(Path(sys.argv[1]), Path(sys.argv[2])))
