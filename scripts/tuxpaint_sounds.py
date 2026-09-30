"""Convert chosen Tux Paint sounds to mono 22.05 kHz PCM16 WAV, trimmed, peak-normalized.

uv run --no-project --with soundfile --with numpy python scripts/tuxpaint_sounds.py <tuxpaint src dir> src/assets/sounds
(tuxpaint src: github.com/tux4kids/Tuxpaint-Android, app/src/main/jni/tuxpaint)
"""

import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

TP = Path(sys.argv[1])  # .../jni/tuxpaint
OUT = Path(sys.argv[2])  # fletMath/src/assets/sounds
RATE = 22050

# event -> [(source, max seconds)]
D, M = "data/sounds", "magic/sounds"
POOLS = {
    "start": [(f"{D}/grow.wav", 2), (f"{M}/zoom_up.ogg", 2), (f"{M}/flower_click.ogg", 2)],
    "slide": [(f"{D}/flip.wav", 1), (f"{D}/bubble.wav", 1), (f"{M}/light1.ogg", 1),
              (f"{D}/stamp.wav", 1), (f"{M}/fold.wav", 1), (f"{M}/ripples.ogg", 1),
              (f"{M}/snowball.ogg", 1), (f"{D}/paint4.wav", 1)],
    "tick": [(f"{D}/click.wav", 0.5)],
    "correct": [(f"{D}/giggle.wav", 2), (f"{D}/tuxok.wav", 2), (f"{M}/cartoon.wav", 2),
                (f"{M}/googlyeyes.ogg", 2), (f"{M}/toothpaste.ogg", 2),
                (f"{M}/realrainbow.ogg", 2), (f"{M}/polyfill_place.ogg", 2),
                (f"{M}/string.ogg", 2), (f"{M}/alien.ogg", 2)],
    "wrong": [(f"{D}/youcannot.wav", 2), (f"{M}/doublevision.ogg", 2),
              (f"{M}/distortion.ogg", 2), (f"{M}/polyfill_remove.ogg", 2),
              (f"{D}/italic_off.wav", 2)],
    "timeout": [(f"{D}/areyousure.wav", 2.5), (f"{M}/drip.wav", 2), (f"{M}/tv.ogg", 2),
                (f"{M}/rain.ogg", 2), (f"{M}/crescent.ogg", 2.5)],
    "finish": [(f"{D}/harp.wav", 4), (f"{M}/polyfill_finish.ogg", 4),
               (f"{M}/comic_dots.ogg", 6), (f"{M}/bloom.ogg", 4)],
    "back": [(f"{D}/shrink.wav", 1.5), (f"{M}/zoom_down.ogg", 1.5), (f"{D}/return.wav", 1.5)],
    # all-correct celebration: the long happy ones (superhero theme; Ride of the Valkyries)
    "perfect": [(f"{M}/comic_dots.ogg", 9), (f"{M}/swirls_rays.ogg", 3)],
}


def convert(src: Path, dst: Path, max_s: float):
    data, sr = sf.read(src, dtype="float32", always_2d=True)
    x = data.mean(axis=1)
    if sr != RATE:
        n = int(round(len(x) * RATE / sr))
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
    x = x[: int(max_s * RATE)]
    fade = min(len(x), int(0.08 * RATE))
    if fade:
        x[-fade:] *= np.linspace(1, 0, fade)
    peak = float(np.max(np.abs(x))) or 1.0
    x = x / peak * 0.89  # about -1 dBFS
    sf.write(dst, x.astype(np.float32), RATE, subtype="PCM_16")
    return len(x) / RATE


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    total = 0
    for event, items in POOLS.items():
        for src, max_s in items:
            name = f"{event}_{Path(src).stem}.wav"
            dur = convert(TP / src, OUT / name, max_s)
            total += (OUT / name).stat().st_size
            print(f"{name} {dur:.1f}s")
    for doc in ("AUTHORS.txt", "COPYING.txt"):
        shutil.copy(TP / "docs" / doc, OUT / f"TUXPAINT_{doc}")
    print(f"total {total / 1024:.0f} KB")


main()
