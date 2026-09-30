# fletMath — SCRATCH

> Thinking sink beside `BACKLOG.md`: approaches, open questions, reusable recipes. Not a register.

### #1

**Source.** <https://www.pond5.com/free#Free-music>; first pick
<https://www.pond5.com/royalty-free-music/item/63342861-work-and-fun-upbeat-and-playful-acoustic-ukulele-music>.
Pond5 answers 403 to automated fetches, so the dev downloads (a free account is probably needed).

**License, as far as reachable (2026-09-29).** Press coverage of the free collection: royalty-free, commercial use,
**artist credit required**. The license text itself was not readable from here. Open: does it allow shipping the
file in a public repo, served as its own URL by GitHub Pages? Stock licenses usually allow a track *inside* a
production, not as a standalone downloadable file. Options: (a) a short trimmed clip in the public app;
(b) keep Pond5 files out of the repo and serve them only from the Mac mini's tailnet build; (c) the dev reads the
license on the download page first. The dev picks.

**Steps once cleared.**
1. The dev drops the files in `C:/Users/vanegasf/Downloads/pond5/` with each title + artist.
2. Pick the most upbeat 6-8 s per track, same shaping as `scripts/tuxpaint_sounds.py` (`convert`): mono 22.05 kHz
   WAV, fade-out, peak-normalized; name `perfect_<slug>.wav`.
3. Add the names to `SOUNDS["perfect"]` in `src/main.py` (the celebration picks one bed at random).
4. Credit: "Music: <title> by <artist> (Pond5)" on the stats screen after a perfect round + a README line.

<!-- template: scratch | version: 2026-09-07 -->
