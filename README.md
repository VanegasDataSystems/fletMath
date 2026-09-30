# fletMath

Timed addition game in [Flet](https://flet.dev) 1.0.

- Pick a number range (x to y) and seconds per problem.
- Two numbers from the range slide in; then the countdown ring starts.
- Tap the sum in the grid (every possible sum, 2x to 2y). Wrong taps shake and reset the streak; a timeout reveals the answer.
- The answer buttons resize to fill the free space on any screen.
- "All done" ends the session and shows stats (solved, timeouts, times, streak, problems to practice).
- Range, time limit and best streak persist on the device.

## Run locally

```
uv sync
uv run flet run src/main.py          # desktop window
uv run flet run --web src/main.py    # browser
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
