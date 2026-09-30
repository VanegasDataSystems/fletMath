"""fletMath - timed addition game.

Two addends are drawn from [lo, hi]; after they animate in, a countdown starts
and the player taps the sum in a grid holding every possible sum (2*lo .. 2*hi).
"""

import asyncio
import random
import time

import flet as ft

SLIDE = ft.Animation(450, ft.AnimationCurve.EASE_OUT_BACK)
POP = ft.Animation(250, ft.AnimationCurve.EASE_OUT_BACK)
TICK = 0.05  # countdown refresh, seconds

DEFAULTS = {"lo": 1, "hi": 10, "secs": 10}


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


class Game:
    def __init__(self, page: ft.Page):
        self.page = page
        self.prefs = Prefs()
        self.lo, self.hi, self.secs = DEFAULTS["lo"], DEFAULTS["hi"], DEFAULTS["secs"]
        self.best = 0
        self.round_id = 0
        self.accepting = False
        self.answer = 0
        self.t0 = 0.0
        self.cells: dict[int, ft.Container] = {}
        self._build_setup()
        self._build_play()

    # ---------- setup screen ----------

    def _build_setup(self):
        self.range_label = ft.Text(size=18, weight=ft.FontWeight.W_600)
        self.range_slider = ft.RangeSlider(
            min=0, max=20, divisions=20,
            start_value=self.lo, end_value=self.hi,
            on_change=self._on_setup_change,
        )
        self.secs_label = ft.Text(size=18, weight=ft.FontWeight.W_600)
        self.secs_slider = ft.Slider(
            min=3, max=30, divisions=27, value=self.secs,
            on_change=self._on_setup_change,
        )
        self.best_label = ft.Text(size=14, color=ft.Colors.ON_SURFACE_VARIANT)
        self.setup_view = ft.Column(
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=18,
            controls=[
                ft.Icon(ft.Icons.CALCULATE_ROUNDED, size=72, color=ft.Colors.PRIMARY),
                ft.Text("fletMath", size=40, weight=ft.FontWeight.BOLD),
                ft.Container(height=12),
                self.range_label,
                self.range_slider,
                self.secs_label,
                self.secs_slider,
                ft.Container(height=12),
                ft.FilledButton(
                    content=ft.Text("Start", size=22),
                    icon=ft.Icons.PLAY_ARROW_ROUNDED,
                    height=56, width=220,
                    on_click=self._start,
                ),
                self.best_label,
            ],
        )
        self._refresh_setup_labels()

    def _refresh_setup_labels(self):
        lo, hi = int(self.range_slider.start_value), int(self.range_slider.end_value)
        self.range_label.value = f"Numbers {lo} to {hi}"
        self.secs_label.value = f"{int(self.secs_slider.value)} seconds per problem"
        self.best_label.value = f"Best streak: {self.best}" if self.best else ""

    def _on_setup_change(self, e):
        self._refresh_setup_labels()

    # ---------- play screen ----------

    def _build_play(self):
        self.score_t = ft.Text("0", size=18, weight=ft.FontWeight.BOLD)
        self.miss_t = ft.Text("0", size=18, weight=ft.FontWeight.BOLD)
        self.streak_t = ft.Text("0", size=18, weight=ft.FontWeight.BOLD)
        top = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.IconButton(ft.Icons.ARROW_BACK_ROUNDED, on_click=self._stop),
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

        self.grid = ft.GridView(expand=True, max_extent=68, spacing=8, run_spacing=8,
                                child_aspect_ratio=1, build_controls_on_demand=False)
        self.play_view = ft.Column(
            expand=True, spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[top, ft.Container(height=8), self.problem, timer, self.grid],
        )

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
        self.best = await self.prefs.get_int("best", 0)
        self.range_slider.start_value, self.range_slider.end_value = self.lo, self.hi
        self.secs_slider.value = self.secs
        self._refresh_setup_labels()
        self.show(self.setup_view)

    def show(self, view):
        self.page.controls.clear()
        self.page.controls.append(ft.SafeArea(content=view, expand=True))
        self.page.update()

    async def _start(self, e):
        self.lo, self.hi = int(self.range_slider.start_value), int(self.range_slider.end_value)
        self.secs = int(self.secs_slider.value)
        for k in ("lo", "hi", "secs"):
            await self.prefs.set_int(k, getattr(self, k))
        self.score = self.misses = self.streak = 0
        self.times: list[float] = []
        self.cells = {n: self._make_cell(n) for n in range(2 * self.lo, 2 * self.hi + 1)}
        self.grid.controls = list(self.cells.values())
        self._update_stats()
        self.show(self.play_view)
        self.page.run_task(self._round)

    async def _stop(self, e):
        self.round_id += 1  # cancels any running countdown
        self.accepting = False
        self._refresh_setup_labels()
        self.show(self.setup_view)

    def _update_stats(self):
        self.score_t.value = str(self.score)
        self.miss_t.value = str(self.misses)
        self.streak_t.value = str(self.streak)

    async def _round(self):
        self.round_id += 1
        rid = self.round_id
        self.accepting = False
        a, b = random.randint(self.lo, self.hi), random.randint(self.lo, self.hi)
        self.answer = a + b

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
        await asyncio.sleep(0.5)
        if rid != self.round_id:
            return

        # countdown
        self.accepting = True
        self.t0 = time.monotonic()
        while rid == self.round_id and self.accepting:
            left = self.secs - (time.monotonic() - self.t0)
            if left <= 0:
                await self._timeout(rid)
                return
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
        self.streak = 0
        self._update_stats()
        self.ring.value = 0
        self.ring_t.value = "0"
        self.feedback.value = "Time!"
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
            self.accepting = False
            dt = time.monotonic() - self.t0
            self.times.append(dt)
            self.score += 1
            self.streak += 1
            if self.streak > self.best:
                self.best = self.streak
                await self.prefs.set_int("best", self.best)
            self._update_stats()
            c.bgcolor = ft.Colors.GREEN
            c.content.color = ft.Colors.WHITE
            c.scale = 1.3
            self.eq_t.value = f"= {self.answer}"
            self.eq_t.color = ft.Colors.GREEN
            avg = sum(self.times) / len(self.times)
            self.feedback.value = f"{dt:.2f}s  (avg {avg:.2f}s)"
            self.page.update()
            await asyncio.sleep(0.9)
            if rid == self.round_id:
                self.page.run_task(self._round)
        else:
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
    page.title = "fletMath"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)
    page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)
    page.padding = 16
    game = Game(page)
    await game.load()


if __name__ == "__main__":
    ft.run(main)
