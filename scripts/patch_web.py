"""Load sfx.js in a `flet publish` build: add its <script> tag to dist/index.html.

uv run python scripts/patch_web.py dist
"""

import sys
from pathlib import Path

TAG = '<script src="sfx.js"></script>'


def main():
    index = Path(sys.argv[1]) / "index.html"
    html = index.read_text(encoding="utf-8")
    if TAG in html:
        return
    if "</head>" not in html:
        sys.exit(f"no </head> in {index}")
    index.write_text(html.replace("</head>", f"  {TAG}\n</head>", 1), encoding="utf-8", newline="")
    print(f"patched {index}")


main()
