from pathlib import Path

from portfolio.gamepulse import build

if __name__ == "__main__":
    result = build(Path("data/gamepulse"))
    print(result["manifest"])
    print(result["model"])
