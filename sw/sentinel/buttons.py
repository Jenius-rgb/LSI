"""START, STOP and RUN buttons of ZERO7, read by the Raspberry Pi (ADR-016).

The buttons share GPIO20 (START), GPIO21 (STOP) and GPIO16 (RUN) with FPGA pins that SENTINEL leaves
unused [OFFICIAL: board/BOARD_INFO.md]. Their polarity is [UNKNOWN], so it is a required argument of
`open_pi_buttons`; measure it at bring-up. `ButtonControl` holds the logic and is tested with stand-ins.
"""
from __future__ import annotations

START_GPIO, STOP_GPIO, RUN_GPIO = 20, 21, 16


class ButtonControl:
    """START: classify every frame. STOP: pause. RUN while paused: classify one frame."""

    def __init__(self, start, stop, run):
        self.running = False
        self.single = False
        start.when_pressed = self._start
        stop.when_pressed = self._stop
        run.when_pressed = self._run

    def _start(self):
        self.running = True

    def _stop(self):
        self.running = False

    def _run(self):
        self.single = True

    def should_classify(self) -> bool:
        if self.running:
            return True
        if self.single:
            self.single = False
            return True
        return False


def open_pi_buttons(active_high: bool) -> ButtonControl:
    """gpiozero buttons on the Pi; active_high must come from a measurement on the board."""
    from gpiozero import Button  # available on the Pi only

    from sentinel.transport import lgpio_factory

    kwargs = {"pull_up": None, "active_state": active_high, "bounce_time": 0.05, "pin_factory": lgpio_factory()}
    return ButtonControl(Button(START_GPIO, **kwargs), Button(STOP_GPIO, **kwargs), Button(RUN_GPIO, **kwargs))
