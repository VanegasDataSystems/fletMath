# fletMath

Timed addition game in [Flet](https://flet.dev) 1.0.

- Pick a number range (x to y) and seconds per problem.
- Two numbers from the range slide in; then the countdown ring starts.
- Tap the sum in the grid (every possible sum, 2x to 2y). Wrong taps shake and reset the streak; a timeout reveals the answer.
- Range, time limit and best streak persist on the device.

## Run locally

```
uv sync
uv run flet run src/main.py          # desktop window
uv run flet run --web src/main.py    # browser
```

## iPhone

Every push to `main` builds a static Pyodide web app (`flet publish`) and deploys it to GitHub Pages
(`.github/workflows/pages.yml`). On the iPhone, open <https://vanegasdatasystems.github.io/fletMath/> in Safari, then
Share -> Add to Home Screen: it launches full-screen like an app. First load downloads the
Python runtime (~20 MB); later loads come from cache.

A native `.ipa` (`flet build ipa`) needs macOS, Xcode and an Apple developer account.
