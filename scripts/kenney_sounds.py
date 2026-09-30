"""Add Kenney "Music Jingles" (CC0) to the celebration's cheer set, same shaping as the Tux Paint clips.

Run AFTER scripts/tuxpaint_sounds.py (that one rebuilds src/assets/sounds from scratch):
uv run --no-project --with soundfile --with numpy python scripts/kenney_sounds.py <kenney_music-jingles dir> src/assets/sounds
(pack: https://kenney.nl/assets/music-jingles)

The jingles were picked unheard, by measurement: the ones whose pitch rises most from start to
end (a "you win" shape) and last close to a second or more.
"""

import shutil
import sys
from pathlib import Path

from tuxpaint_sounds import convert

JINGLES = [
    "Hit jingles/jingles_HIT11", "Hit jingles/jingles_HIT15", "8-Bit jingles/jingles_NES12",
    "Sax jingles/jingles_SAX02", "Pizzicato jingles/jingles_PIZZI02", "Steel jingles/jingles_STEEL02",
    "Steel jingles/jingles_STEEL06", "Pizzicato jingles/jingles_PIZZI12",
]


def main():
    pack, out = Path(sys.argv[1]), Path(sys.argv[2])
    for j in JINGLES:
        name = "cheer_" + Path(j).name.removeprefix("jingles_").lower() + ".wav"
        dur = convert(pack / "Audio" / f"{j}.ogg", out / name, 3)
        print(f"{name} {dur:.1f}s")
    shutil.copy(pack / "License.txt", out / "KENNEY_LICENSE.txt")


if __name__ == "__main__":
    main()
