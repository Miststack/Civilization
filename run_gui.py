from __future__ import annotations

import sys

from main import main

if __name__ == "__main__":
    sys.argv = [
        sys.argv[0],
        "--gui",
        "--map-size",
        "10",
        "--turns",
        "30",
        "--play",
        "human",
        *sys.argv[1:],
    ]
    main()
