# Give math a chance (fletMath)

Timed addition game in [Flet](https://flet.dev) 1.0.

- Pick a number range (x to y), seconds per problem and how many problems (defaults: 0-2, 10 s, 5 problems; the range resets to 0-2 every time the app opens), and a colour theme: red, orange, green or blue (default). The opening screen cycles the themes every few seconds until Start or a colour is tapped.
- Two numbers from the range slide in; then the countdown ring starts.
- Tap the sum in the grid (every possible sum, 2x to 2y). Wrong taps shake and reset the streak; a timeout reveals the answer.
- The answer buttons resize to fill the free space on any screen. Portrait only: native builds lock
  it; in the browser / home-screen app turn on the iPhone's Portrait Orientation Lock (Control Center).
- "All done" ends the session and shows stats (solved, timeouts, times, streak, problems to practice).
- All problems right: a confetti burst over a blurred screen, a bouncing PERFECT! star and a random mix of
  happy sounds (one long bed from the `perfect` set - superhero theme or Ride of the Valkyries - plus five random
  cheers), then a dare: "Nobody could do x numbers, could they?" (x = the top of the range + 1); "I can!"
  starts a round with the higher range. The `cheer` set adds [Kenney's Music Jingles](https://kenney.nl/assets/music-jingles)
  (CC0; `scripts/kenney_sounds.py`, run after `scripts/tuxpaint_sounds.py`).
- Sounds (toggle on the setup screen): a random pick per event from Tux Paint's sound effects,
  `src/assets/sounds/<event>_<name>.wav`, listed in `SOUNDS` in `src/main.py`. Drop in your own
  recordings with the same naming and add them to the list. In the web build the sounds play through
  `src/assets/sfx.js` (Web Audio, near-instant on iPhone; `scripts/patch_web.py` loads it into
  `index.html` after `flet publish`); desktop runs use flet-audio. Tux Paint is GPL-2.0; per-file credits
  and licenses are in `src/assets/sounds/TUXPAINT_AUTHORS.txt`.
- Range, time limit and best streak persist on the device.
- Setup-screen photo: one of five peace-sign photos, `src/assets/peace1.jpg`..`peace5.jpg`, picked at random
  on open and on each return to setup, cropped to 3:2. Free use, no attribution required: 1, 2, 4, 5 from Unsplash
  ([license](https://unsplash.com/license)) - [1](https://unsplash.com/photos/iXakCfUG8do),
  [2](https://unsplash.com/photos/o_xBvCuVoo8), [4](https://unsplash.com/photos/gDQi4l7H7gA),
  [5](https://unsplash.com/photos/Mvivn0YyVxg); 3 from Pexels ([license](https://www.pexels.com/license/)) -
  [3](https://www.pexels.com/photo/a-boy-doing-a-peace-sign-14622673/).

## Run locally

```
uv sync
uv run flet run src/main.py          # desktop window
uv run flet run --web src/main.py    # browser
uv run flet publish .                # static web build into dist/ (run from the project root)
```

## iPhone (self-hosted on the tailnet, no Apple account)

On the Mac mini (Tailscale logged in; MagicDNS + HTTPS certificates on in the admin console):

```
./scripts/serve_tailnet.sh
```

It builds the static Pyodide web app (`flet publish`), serves it locally on port 8550 and puts it
behind `tailscale serve` at `https://<mac-mini>.<tailnet>.ts.net/`. On the iPhone (Tailscale app
connected) open that URL in Safari, then Share -> Add to Home Screen: it launches full-screen like an
app. Python runs on the phone; the Mac only serves files. The first load pulls the Python runtime
(~20 MB); later loads come from cache.

GitHub Pages also deploys every push to `main` (`.github/workflows/pages.yml`):
<https://vanegasdatasystems.github.io/fletMath/>.

A native `.ipa` (`flet build ipa`) needs Xcode and an Apple ID; sideloads with a free ID expire
after 7 days.
