"""Give math a chance (repo: fletMath) - timed addition game.

Two addends are drawn from [lo, hi]; after they animate in, a countdown starts
and the player taps the sum in a grid holding every possible sum (2*lo .. 2*hi).
"""

import asyncio
import math
import random
import sys
import time

import flet as ft
import flet_audio as fta

try:
    from build_info import BUILD  # written by the Pages workflow
except ImportError:
    BUILD = "dev"

SLIDE = ft.Animation(450, ft.AnimationCurve.EASE_OUT_BACK)
POP = ft.Animation(250, ft.AnimationCurve.EASE_OUT_BACK)
TICK = 0.05  # countdown refresh, seconds
GAP = 8  # grid spacing, px

APP_NAME = "Give math a chance"
DEFAULTS = {"lo": 0, "hi": 4, "secs": 10, "count": 5, "theme": 3}
CYCLE_SECS = 5  # opening screen: seconds per theme
THEMES = [ft.Colors.RED, ft.Colors.ORANGE, ft.Colors.GREEN, ft.Colors.BLUE]  # pref "theme" = index
RANGE_MIN, RANGE_MAX = 0, 20


class Prefs:
    """SharedPreferences wrapper that never breaks the game (web private mode, etc.)."""

    def __init__(self):
        try:
            self._sp = ft.SharedPreferences()
        except Exception:
            self._sp = None

    async def get_int(self, key, default):
        try:
            v = await self._sp.get(f"fletmath.{key}")
            return int(v) if v is not None else default
        except Exception:
            return default

    async def set_int(self, key, value):
        try:
            await self._sp.set(f"fletmath.{key}", int(value))
        except Exception:
            pass


# Tux Paint sounds (GPL-2.0 and per-file CC licenses, see assets/sounds/TUXPAINT_*.txt),
# stored as assets/sounds/<event>_<name>.wav; one is picked at random per event.
SOUNDS = {
    "start": ["grow", "zoom_up", "flower_click"],
    "slide": ["flip", "bubble", "light1", "stamp", "fold", "ripples", "snowball", "paint4"],
    "tick": ["click"],
    "correct": ["giggle", "tuxok", "cartoon", "googlyeyes", "toothpaste", "realrainbow",
                "polyfill_place", "string", "alien"],
    "wrong": ["youcannot", "doublevision", "distortion", "polyfill_remove", "italic_off"],
    "timeout": ["areyousure", "drip", "tv", "rain", "crescent"],
    "finish": ["harp", "polyfill_finish", "comic_dots", "bloom"],
    "back": ["shrink", "zoom_down", "return"],
    "perfect": ["comic_dots", "swirls_rays"],  # all-correct celebration, played together
}
PHOTOS = [f"peace{i}.jpg" for i in range(1, 6)]  # double peace signs (Unsplash, see README), one at random
CONFETTI = [ft.Colors.RED, ft.Colors.ORANGE, ft.Colors.AMBER, ft.Colors.GREEN, ft.Colors.BLUE,
            ft.Colors.PURPLE, ft.Colors.PINK, ft.Colors.CYAN]


class Sfx:
    """Random pick per event, never the same clip twice in a row; audio errors never stop the game.

    Static web build (Pyodide in a worker): posts the clip name to assets/sfx.js over a BroadcastChannel,
    which plays pre-decoded Web Audio buffers - flet-audio's <audio> element lags on iOS.
    Desktop / server runs: flet-audio players.
    """

    def __init__(self, page: ft.Page):
        self.page = page
        self.on = True
        self.last: dict[str, str] = {}
        self.players: dict[str, dict[str, fta.Audio]] = {}
        self.channel = None
        clips = [f"{event}_{n}" for event, names in SOUNDS.items() for n in names]
        if sys.platform == "emscripten":
            try:
                import js  # ty: ignore[unresolved-import]  # Pyodide only

                self.channel = js.BroadcastChannel.new("fletmath-sfx")
                self.channel.postMessage("preload:" + ",".join(clips))
                return
            except Exception:
                self.channel = None
        for event, names in SOUNDS.items():
            self.players[event] = {}
            for n in names:
                a = fta.Audio(src=f"sounds/{event}_{n}.wav", release_mode=fta.ReleaseMode.STOP)
                self.players[event][n] = a
                page.services.append(a)

    def play(self, event):
        if not self.on:
            return
        names = SOUNDS[event]
        pick = random.choice([n for n in names if n != self.last.get(event)] or names)
        self.last[event] = pick
        self.play_clip(event, pick)

    def play_clip(self, event, name):
        if not self.on:
            return
        if self.channel is not None:
            try:
                self.channel.postMessage(f"play:{event}_{name}")
            except Exception:
                pass
            return
        self.page.run_task(self._play, self.players[event][name])

    async def _play(self, audio):
        try:
            await audio.play()
        except Exception:
            pass


class Game:
    def __init__(self, page: ft.Page):
        self.page = page
        self.prefs = Prefs()
        self.sfx = Sfx(page)
        self.lo, self.hi, self.secs, self.count = (DEFAULTS[k] for k in ("lo", "hi", "secs", "count"))
        self.best = 0
        self.round_id = 0
        self.cycling = False
        self.theme_i = DEFAULTS["theme"]
        self.accepting = False
        self.answer = 0
        self.t0 = 0.0
        self.cells: dict[int, ft.Container] = {}
        self._build_setup()
        self._build_play()

    # ---------- setup screen ----------

    def _build_setup(self):
        self.range_slider = ft.RangeSlider(
            min=RANGE_MIN, max=RANGE_MAX, divisions=RANGE_MAX - RANGE_MIN,
            start_value=self.lo, end_value=self.hi, label="{value}",  # number shows while dragging
            on_change=self._on_setup_change,
        )
        self.secs_label = ft.Text(size=18, weight=ft.FontWeight.W_600)
        self.secs_slider = ft.Slider(
            min=3, max=30, divisions=27, value=self.secs,
            on_change=self._on_setup_change,
        )
        self.count_label = ft.Text(size=18, weight=ft.FontWeight.W_600)
        self.count_slider = ft.Slider(
            min=1, max=30, divisions=29, value=self.count,
            on_change=self._on_setup_change,
        )
        self.sound_sw = ft.Switch(label="Sounds", value=True, on_change=self._on_sound)
        self.swatches = [
            ft.Container(width=34, height=34, border_radius=17, bgcolor=c, data=i,
                         on_click=self._on_theme)
            for i, c in enumerate(THEMES)
        ]
        self.best_label = ft.Text(size=14, color=ft.Colors.ON_SURFACE_VARIANT)
        self.photo = ft.Image(
            src=random.choice(PHOTOS), width=150, height=100, fit=ft.BoxFit.COVER, border_radius=20,
            semantics_label="Kids making peace signs",
            error_content=ft.Icon(ft.Icons.CALCULATE_ROUNDED, size=56, color=ft.Colors.PRIMARY),
        )
        self.setup_view = ft.Column(
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
            controls=[
                self.photo,
                ft.Text(APP_NAME, size=34, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Container(height=12),
                self.range_slider,
                self.secs_label,
                self.secs_slider,
                self.count_label,
                self.count_slider,
                ft.Container(height=12),
                ft.FilledButton(
                    content=ft.Text("Start", size=22),
                    icon=ft.Icons.PLAY_ARROW_ROUNDED,
                    height=56, width=220,
                    on_click=self._start,
                ),
                ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10,
                       controls=[self.sound_sw, ft.Container(width=8), *self.swatches]),
                self.best_label,
                ft.Text(f"build {BUILD}", size=11, color=ft.Colors.OUTLINE),
            ],
        )
        self._refresh_setup_labels()

    def _refresh_setup_labels(self):
        self.secs_label.value = f"{int(self.secs_slider.value)} seconds per problem"
        self.count_label.value = f"{int(self.count_slider.value)} problems"
        self.best_label.value = f"Best streak: {self.best}" if self.best else ""

    def _apply_theme(self, i):
        i = i if 0 <= i < len(THEMES) else DEFAULTS["theme"]
        self.page.theme = ft.Theme(color_scheme_seed=THEMES[i])
        self.page.dark_theme = ft.Theme(color_scheme_seed=THEMES[i])
        for sw in self.swatches:  # ring the chosen colour
            sw.border = ft.Border.all(3, ft.Colors.ON_SURFACE) if sw.data == i else None
        self.theme_i = i
        return i

    async def _cycle_themes(self):
        """Opening screen shows off the themes until Start or a colour tap; the saved choice is untouched."""
        while self.cycling:
            await asyncio.sleep(CYCLE_SECS)
            if not self.cycling:
                return
            self._apply_theme((self.theme_i + 1) % len(THEMES))
            self.page.update()

    async def _on_theme(self, e):
        self.cycling = False
        i = self._apply_theme(e.control.data)
        self.page.update()
        await self.prefs.set_int("theme", i)

    async def _on_sound(self, e):
        self.sfx.on = self.sound_sw.value
        await self.prefs.set_int("sound", int(self.sfx.on))
        self.sfx.play("correct")

    def _on_setup_change(self, e):
        self._refresh_setup_labels()

    # ---------- play screen ----------

    def _build_play(self):
        self.score_t = ft.Text("0", size=18, weight=ft.FontWeight.BOLD)
        self.miss_t = ft.Text("0", size=18, weight=ft.FontWeight.BOLD)
        self.streak_t = ft.Text("0", size=18, weight=ft.FontWeight.BOLD)
        self.progress_t = ft.Text("", size=18, weight=ft.FontWeight.BOLD,
                                  color=ft.Colors.ON_SURFACE_VARIANT)
        top = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.IconButton(ft.Icons.ARROW_BACK_ROUNDED, on_click=self._stop),
                self.progress_t,
                ft.Row(spacing=4, controls=[
                    ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=ft.Colors.GREEN), self.score_t,
                    ft.Container(width=10),
                    ft.Icon(ft.Icons.CANCEL_ROUNDED, color=ft.Colors.RED), self.miss_t,
                    ft.Container(width=10),
                    ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED, color=ft.Colors.ORANGE), self.streak_t,
                ]),
            ],
        )

        def num(start_x):
            return ft.Container(
                content=ft.Text("", size=56, weight=ft.FontWeight.BOLD),
                offset=ft.Offset(start_x, 0), opacity=0,
                animate_offset=SLIDE, animate_opacity=250,
            )

        self.a_box, self.b_box = num(-4), num(4)
        self.plus_box = ft.Container(
            content=ft.Text("+", size=48, color=ft.Colors.PRIMARY),
            scale=0, animate_scale=POP,
        )
        self.eq_t = ft.Text("= ?", size=48, color=ft.Colors.ON_SURFACE_VARIANT)
        self.problem = ft.Container(
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER, spacing=12,
                controls=[self.a_box, self.plus_box, self.b_box, self.eq_t],
            ),
            offset=ft.Offset(0, 0), animate_offset=60,
        )

        self.ring = ft.ProgressRing(value=1, stroke_width=8, width=76, height=76,
                                    color=ft.Colors.GREEN, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST)
        self.ring_t = ft.Text("", size=20, weight=ft.FontWeight.BOLD)
        self.feedback = ft.Text("", size=18, color=ft.Colors.ON_SURFACE_VARIANT)
        timer = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER, spacing=16,
            controls=[
                ft.Stack(width=76, height=76, alignment=ft.Alignment.CENTER,
                         controls=[self.ring, self.ring_t]),
                self.feedback,
            ],
        )

        # runs_count / aspect ratio are recomputed in _fit_grid to fill the free space
        self.grid_w = self.grid_h = 0.0
        self.grid = ft.GridView(expand=True, runs_count=5, spacing=GAP, run_spacing=GAP,
                                child_aspect_ratio=1, build_controls_on_demand=False,
                                on_size_change=self._on_grid_size)
        done = ft.OutlinedButton(
            content=ft.Text("All done", size=18),
            icon=ft.Icons.FLAG_ROUNDED,
            height=52,
            on_click=self._done,
        )
        self.play_view = ft.Column(
            expand=True, spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[top, ft.Container(height=8), self.problem, timer, self.grid,
                      ft.Container(height=4), done],
        )

    def _on_grid_size(self, e: ft.LayoutSizeChangeEvent):
        if (e.width, e.height) == (self.grid_w, self.grid_h):
            return
        self.grid_w, self.grid_h = e.width, e.height
        self._fit_grid()
        self.page.update()

    def _fit_grid(self):
        """Pick the column count that gives the biggest square, then stretch cells to fill."""
        n, w, h = len(self.cells), self.grid_w, self.grid_h
        if not n or w <= 0 or h <= 0:
            return
        best_side, cols = 0.0, 1
        for c in range(1, n + 1):
            rows = -(-n // c)
            side = min((w - GAP * (c - 1)) / c, (h - GAP * (rows - 1)) / rows)
            if side > best_side:
                best_side, cols = side, c
        rows = -(-n // cols)
        cw = (w - GAP * (cols - 1)) / cols
        ch = (h - GAP * (rows - 1)) / rows - 1  # 1px slack so rounding never scrolls
        self.grid.runs_count = cols
        self.grid.child_aspect_ratio = cw / ch
        size = max(18, min(cw / 1.6, ch * 0.5))
        for cell in self.cells.values():
            cell.content.size = size

    def _make_cell(self, n):
        return ft.Container(
            content=ft.Text(str(n), size=22, weight=ft.FontWeight.W_600,
                            color=ft.Colors.ON_PRIMARY_CONTAINER),
            alignment=ft.Alignment.CENTER,
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
            border_radius=14,
            scale=1, animate_scale=POP, animate=200,
            ink=True,
            data=n,
            on_click=self._on_cell,
        )

    def _reset_cell(self, c):
        c.bgcolor = ft.Colors.PRIMARY_CONTAINER
        c.content.color = ft.Colors.ON_PRIMARY_CONTAINER
        c.scale = 1

    # ---------- flow ----------

    async def load(self):
        self.lo = await self.prefs.get_int("lo", DEFAULTS["lo"])
        self.hi = await self.prefs.get_int("hi", DEFAULTS["hi"])
        self.secs = await self.prefs.get_int("secs", DEFAULTS["secs"])
        self.count = await self.prefs.get_int("count", DEFAULTS["count"])
        self.best = await self.prefs.get_int("best", 0)
        self.sfx.on = self.sound_sw.value = bool(await self.prefs.get_int("sound", 1))
        self._apply_theme(await self.prefs.get_int("theme", DEFAULTS["theme"]))
        self.range_slider.start_value, self.range_slider.end_value = self.lo, self.hi
        self.secs_slider.value = self.secs
        self.count_slider.value = self.count
        self._refresh_setup_labels()
        self.show(self.setup_view)
        self.cycling = True
        self.page.run_task(self._cycle_themes)

    def show(self, view):
        self.page.controls.clear()
        self.page.controls.append(ft.SafeArea(content=view, expand=True))
        self.page.update()

    async def _start(self, e):
        self.sfx.play("start")  # first thing, while iOS still counts the tap
        self.cycling = False  # the game keeps the colour on screen
        self.lo, self.hi = int(self.range_slider.start_value), int(self.range_slider.end_value)
        self.secs = int(self.secs_slider.value)
        self.count = int(self.count_slider.value)
        for k in ("lo", "hi", "secs", "count"):
            await self.prefs.set_int(k, getattr(self, k))
        self.score = self.misses = self.streak = self.wrong = self.session_best = 0
        self.times: list[float] = []
        self.missed: list[str] = []
        self.cells = {n: self._make_cell(n) for n in range(2 * self.lo, 2 * self.hi + 1)}
        self.grid.controls = list(self.cells.values())
        self._fit_grid()
        self._update_stats()
        self.show(self.play_view)
        self.page.run_task(self._round)

    async def _stop(self, e):
        self.round_id += 1  # cancels any running countdown
        self.accepting = False
        self.sfx.play("back")
        self.photo.src = random.choice([p for p in PHOTOS if p != self.photo.src])
        self._refresh_setup_labels()
        self.show(self.setup_view)

    async def _done(self, e):
        self.round_id += 1  # the unfinished problem is not counted
        self.accepting = False
        self.sfx.play("finish")
        self.show(self._build_summary())

    def _build_summary(self, perfect=False):
        total = self.score + self.misses
        avg = f"{sum(self.times) / len(self.times):.1f}s" if self.times else "-"
        fast = f"{min(self.times):.1f}s" if self.times else "-"

        def tile(value, label, icon, color):
            return ft.Container(
                col=6, padding=12, border_radius=16,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                content=ft.Column(
                    spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(icon, color=color),
                        ft.Text(value, size=30, weight=ft.FontWeight.BOLD),
                        ft.Text(label, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                ),
            )

        tiles = ft.ResponsiveRow(spacing=12, run_spacing=12, controls=[
            tile(f"{self.score}/{total}", "solved", ft.Icons.CHECK_CIRCLE_ROUNDED, ft.Colors.GREEN),
            tile(str(self.misses), "timed out", ft.Icons.HOURGLASS_BOTTOM_ROUNDED, ft.Colors.AMBER),
            tile(avg, "average", ft.Icons.TIMER_ROUNDED, ft.Colors.PRIMARY),
            tile(fast, "fastest", ft.Icons.BOLT_ROUNDED, ft.Colors.PRIMARY),
            tile(str(self.session_best), "best streak",
                 ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED, ft.Colors.ORANGE),
            tile(str(self.wrong), "wrong taps", ft.Icons.CANCEL_ROUNDED, ft.Colors.RED),
        ])
        practice = list(dict.fromkeys(self.missed))[:8]
        return ft.Column(
            expand=True, spacing=16, scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(height=8),
                ft.Icon(ft.Icons.EMOJI_EVENTS_ROUNDED, size=64, color=ft.Colors.AMBER),
                ft.Text("PERFECT!" if perfect else "All done!", size=36, weight=ft.FontWeight.BOLD),
                tiles,
                ft.Text("Practice: " + ",  ".join(practice), size=16,
                        text_align=ft.TextAlign.CENTER) if practice else ft.Container(),
                *(self._challenge_controls() if perfect else []),
                ft.Container(height=8),
                ft.FilledButton(
                    content=ft.Text("Play again", size=20),
                    icon=ft.Icons.REPLAY_ROUNDED,
                    height=56, width=240,
                    on_click=self._start,
                ),
                ft.TextButton(content=ft.Text("Settings", size=16), on_click=self._stop),
            ],
        )

    def _challenge_controls(self):
        """After a perfect round: dare them one number higher."""
        x = self.hi + 1
        if x > RANGE_MAX:
            return [ft.Text("You beat the biggest numbers!", size=22, weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER)]
        return [
            ft.Text(f"Nobody could do {x} numbers, could they?", size=24, weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER, color=ft.Colors.PRIMARY),
            ft.FilledButton(
                content=ft.Text("I can!", size=24), icon=ft.Icons.ROCKET_LAUNCH_ROUNDED,
                height=64, width=240, on_click=self._challenge,
            ),
        ]

    async def _challenge(self, e):
        self.range_slider.end_value = min(self.hi + 1, RANGE_MAX)
        await self._start(e)  # saves the new range with the other settings

    async def _celebrate(self):
        """Every problem right: confetti burst from the middle, a star pops in, the happy sounds stack up."""
        w, h = self.page.width or 400, self.page.height or 700
        cx, cy = w / 2, h / 2
        pieces = [
            ft.Container(
                width=random.choice([8, 10, 12]), height=random.choice([12, 16, 20]), border_radius=3,
                bgcolor=random.choice(CONFETTI), left=cx, top=cy, rotate=0,
                animate_position=ft.Animation(random.randint(700, 1100), ft.AnimationCurve.EASE_OUT),
                animate_rotation=ft.Animation(2600, ft.AnimationCurve.LINEAR),
            )
            for _ in range(70)
        ]
        star = ft.Container(
            content=ft.Column(
                tight=True, spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.STAR_ROUNDED, size=160, color=ft.Colors.AMBER),
                    ft.Text("PERFECT!", size=52, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Text(f"{self.count} out of {self.count}!", size=26, color=ft.Colors.WHITE),
                ],
            ),
            scale=0, rotate=-0.6,
            animate_scale=ft.Animation(900, ft.AnimationCurve.ELASTIC_OUT),
            animate_rotation=ft.Animation(900, ft.AnimationCurve.EASE_OUT_BACK),
        )
        # blurs the game screen behind the confetti; fades in and out with its opacity
        shade = ft.Container(left=0, top=0, width=w, height=h, opacity=0, animate_opacity=400,
                             blur=ft.Blur(12, 12), bgcolor=ft.Colors.with_opacity(0.35, ft.Colors.BLACK))
        layer = ft.Stack(width=w, height=h, controls=[
            shade, *pieces,
            ft.Container(left=0, top=0, width=w, height=h, alignment=ft.Alignment.CENTER, content=star),
        ])
        self.page.overlay.append(layer)
        self.page.update()
        await asyncio.sleep(0.05)
        self.page.run_task(self._celebration_sounds)

        # burst outward
        shade.opacity = 1
        for p in pieces:
            angle, dist = random.uniform(0, 2 * math.pi), random.uniform(0.2, 0.65) * max(w, h)
            p.left = cx + math.cos(angle) * dist
            p.top = cy + math.sin(angle) * dist * 0.8 - h * 0.12
            p.rotate = random.uniform(-14, 14)
        star.scale, star.rotate = 1, 0
        self.page.update()
        await asyncio.sleep(1.1)

        # confetti rains down while the star beats
        for p in pieces:
            p.animate_position = ft.Animation(random.randint(1600, 2600), ft.AnimationCurve.EASE_IN)
            p.left += random.uniform(-70, 70)
            p.top = h + 60
            p.rotate += random.uniform(-12, 12)
        self.page.update()
        star.animate_scale = ft.Animation(300, ft.AnimationCurve.EASE_OUT)
        for s in (1.18, 1, 1.18, 1, 1.25, 1):
            await asyncio.sleep(0.32)
            star.scale = s
            self.page.update()
        await asyncio.sleep(0.8)
        shade.opacity = 0
        star.scale = 0
        self.page.update()
        await asyncio.sleep(0.4)
        self.page.overlay.remove(layer)
        self.page.update()

    async def _celebration_sounds(self):
        """Superhero theme and Valkyries underneath; the short happy ones on top."""
        sfx = self.sfx
        sfx.play_clip("perfect", "comic_dots")
        for delay, event, name in ((0.1, "finish", "polyfill_finish"), (0.5, "correct", "giggle"),
                                   (0.5, "perfect", "swirls_rays"), (0.9, "correct", "realrainbow"),
                                   (0.9, "finish", "harp"), (0.8, "finish", "bloom")):
            await asyncio.sleep(delay)
            sfx.play_clip(event, name)

    def _update_stats(self):
        self.score_t.value = str(self.score)
        self.miss_t.value = str(self.misses)
        self.streak_t.value = str(self.streak)

    async def _round(self):
        done = self.score + self.misses
        if done >= self.count:
            self.round_id += 1
            self.accepting = False
            perfect = self.score == self.count  # every problem solved, none timed out
            if perfect:
                await self._celebrate()
            else:
                self.sfx.play("finish")
            self.show(self._build_summary(perfect))
            return
        self.progress_t.value = f"{done + 1}/{self.count}"
        self.round_id += 1
        rid = self.round_id
        self.accepting = False
        a, b = random.randint(self.lo, self.hi), random.randint(self.lo, self.hi)
        self.answer = a + b
        self.problem_text = f"{a} + {b}"

        # exit: old numbers fly off to the right
        for box in (self.a_box, self.b_box):
            box.offset = ft.Offset(4, 0)
            box.opacity = 0
        self.plus_box.scale = 0
        self.eq_t.value = "= ?"
        self.eq_t.color = ft.Colors.ON_SURFACE_VARIANT
        self.feedback.value = ""
        self.ring.value = 1
        self.ring.color = ft.Colors.GREEN
        self.ring_t.value = str(self.secs)
        for c in self.cells.values():
            self._reset_cell(c)
        self.page.update()
        await asyncio.sleep(0.25)
        if rid != self.round_id:
            return

        # jump offstage without animating, then slide in
        self.a_box.animate_offset = self.b_box.animate_offset = None
        self.a_box.offset, self.b_box.offset = ft.Offset(-4, 0), ft.Offset(4, 0)
        self.a_box.content.value, self.b_box.content.value = str(a), str(b)
        self.page.update()
        await asyncio.sleep(0.03)
        self.a_box.animate_offset = self.b_box.animate_offset = SLIDE
        for box in (self.a_box, self.b_box):
            box.offset = ft.Offset(0, 0)
            box.opacity = 1
        self.plus_box.scale = 1
        self.page.update()
        self.sfx.play("slide")
        await asyncio.sleep(0.5)
        if rid != self.round_id:
            return

        # countdown; tick at 3, 2, 1 seconds left
        self.accepting = True
        self.t0 = time.monotonic()
        tick_at = min(3, self.secs - 1)
        while rid == self.round_id and self.accepting:
            left = self.secs - (time.monotonic() - self.t0)
            if left <= 0:
                await self._timeout(rid)
                return
            if 0 < tick_at and left <= tick_at:
                self.sfx.play("tick")
                tick_at -= 1
            frac = left / self.secs
            self.ring.value = frac
            self.ring.color = (ft.Colors.GREEN if frac > 0.5
                               else ft.Colors.AMBER if frac > 0.25 else ft.Colors.RED)
            self.ring_t.value = f"{left:.1f}" if left < 5 else str(int(left) + 1)
            self.page.update()
            await asyncio.sleep(TICK)

    async def _timeout(self, rid):
        self.accepting = False
        self.misses += 1
        self.missed.append(self.problem_text)
        self.streak = 0
        self._update_stats()
        self.ring.value = 0
        self.ring_t.value = "0"
        self.feedback.value = "Time!"
        self.sfx.play("timeout")
        self.eq_t.value = f"= {self.answer}"
        self.eq_t.color = ft.Colors.AMBER
        c = self.cells[self.answer]
        c.bgcolor = ft.Colors.AMBER
        c.content.color = ft.Colors.BLACK
        c.scale = 1.25
        self.page.update()
        await asyncio.sleep(1.4)
        if rid == self.round_id:
            self.page.run_task(self._round)

    async def _on_cell(self, e):
        if not self.accepting:
            return
        c: ft.Container = e.control
        rid = self.round_id
        if c.data == self.answer:
            self.sfx.play("correct")  # sound and colour first; bookkeeping after
            self.accepting = False
            dt = time.monotonic() - self.t0
            self.times.append(dt)
            self.score += 1
            self.streak += 1
            self.session_best = max(self.session_best, self.streak)
            new_best = self.streak > self.best
            if new_best:
                self.best = self.streak
            self._update_stats()
            c.bgcolor = ft.Colors.GREEN
            c.content.color = ft.Colors.WHITE
            c.scale = 1.3
            self.eq_t.value = f"= {self.answer}"
            self.eq_t.color = ft.Colors.GREEN
            avg = sum(self.times) / len(self.times)
            self.feedback.value = f"{dt:.2f}s  (avg {avg:.2f}s)"
            self.page.update()
            if new_best:
                await self.prefs.set_int("best", self.best)
            await asyncio.sleep(0.9)
            if rid == self.round_id:
                self.page.run_task(self._round)
        else:
            self.sfx.play("wrong")
            self.wrong += 1
            self.streak = 0
            self._update_stats()
            c.bgcolor = ft.Colors.RED
            c.content.color = ft.Colors.WHITE
            c.scale = 0.85
            self.page.update()
            for dx in (0.04, -0.04, 0.03, -0.03, 0):  # shake the problem
                self.problem.offset = ft.Offset(dx, 0)
                self.page.update()
                await asyncio.sleep(0.06)
            await asyncio.sleep(0.25)
            if rid == self.round_id and c.data != self.answer:
                self._reset_cell(c)
                self.page.update()


async def main(page: ft.Page):
    page.title = APP_NAME
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 16
    # portrait only, so thumbs reach the grid; native builds only - a browser
    # (iOS Safari / home-screen app) cannot lock, use the phone's rotation lock there
    if not page.web:
        try:
            await page.set_allowed_device_orientations([ft.DeviceOrientation.PORTRAIT_UP])
        except Exception:
            pass  # desktop
    game = Game(page)
    await game.load()


if __name__ == "__main__":
    ft.run(main)
