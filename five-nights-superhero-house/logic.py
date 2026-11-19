"""Game rules for "Five Nights at Mexican Superhero's House".

Pure Python (no pygame) so the rules can be unit-tested anywhere.

The player is the night guard. Three original masked heroes roam the house:

* El Trueno    (internal key "moose") - works his way to the WEST door.
* La Mariposa  (internal key "penny") - works her way to the EAST door.
* El Tornado   (internal key "gus")   - lurks in the storage closet. He only
                    creeps forward while you are NOT watching him on camera 6,
                    and when he is ready he charges one of the doors.

Doors, lights and the camera monitor all drain power. If the power hits zero
the doors open, the lights die and a music box starts to play.
Survive until 6 AM.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

HOUR_SECONDS = 45.0          # real seconds per in-game hour
HOURS = 6                    # 12 AM -> 6 AM
NIGHT_LENGTH = HOUR_SECONDS * HOURS
MAX_NIGHT = 5

HOUR_LABELS = ["12 AM", "1 AM", "2 AM", "3 AM", "4 AM", "5 AM", "6 AM"]

CAM_ROOMS = {
    1: "STAGE",
    2: "DINING",
    3: "KITCHEN",
    4: "WEST_HALL",
    5: "EAST_HALL",
    6: "CLOSET",
}
CAM_NAMES = {
    1: "FIESTA ROOM",
    2: "DINING ROOM",
    3: "KITCHEN",
    4: "WEST HALL",
    5: "EAST HALL",
    6: "STORAGE CLOSET",
}

# Aggression out of 20, rolled on every move tick: (Mortimer, Penny, Gus).
AGGRESSION = {
    1: (2, 0, 0),
    2: (4, 3, 1),
    3: (6, 5, 3),
    4: (9, 8, 5),
    5: (12, 11, 8),
}

# Where each animatronic can go next: room -> [(next_room, weight), ...]
MOOSE_PATH = {
    "STAGE": [("DINING", 1)],
    "DINING": [("WEST_HALL", 3), ("KITCHEN", 1)],
    "KITCHEN": [("DINING", 1)],
    "WEST_HALL": [("WEST_DOOR", 1)],
}
PENNY_PATH = {
    "STAGE": [("DINING", 1)],
    "DINING": [("KITCHEN", 2), ("EAST_HALL", 1)],
    "KITCHEN": [("EAST_HALL", 3), ("DINING", 1)],
    "EAST_HALL": [("EAST_DOOR", 1)],
}

SIDES = ("west", "east")


@dataclass
class Animatronic:
    key: str
    name: str
    base: int                 # base aggression (0 = asleep tonight)
    interval: float           # seconds between move attempts
    path: dict
    door_room: str
    side: str
    retreat_room: str
    room: str = "STAGE"
    timer: float = 0.0
    door_wait: float = 0.0


class Night:
    """One night's worth of game state. Call update(dt) every frame."""

    def __init__(self, night: int = 1, rng: random.Random | None = None):
        self.night = max(1, min(MAX_NIGHT, int(night)))
        self.rng = rng or random.Random()
        agg = AGGRESSION[self.night]

        self.time = 0.0
        self.power = 100.0
        self.doors = {"west": False, "east": False}     # True = closed
        self.lights = {"west": False, "east": False}    # True = on
        self.cam_up = False
        self.cam = 1

        self.jumpscare: str | None = None
        self.won = False

        self.blackout = False
        self.blackout_time = 0.0
        self.blackout_limit = 0.0
        self.jingle_started = False

        self.moose = Animatronic("moose", "El Trueno", agg[0], 5.0,
                                 MOOSE_PATH, "WEST_DOOR", "west", "DINING")
        self.penny = Animatronic("penny", "La Mariposa", agg[1], 5.5,
                                 PENNY_PATH, "EAST_DOOR", "east", "DINING")

        # Gus is handled separately.
        self.gus_base = agg[2]
        self.gus_timer = 0.0
        self.gus_interval = 4.0
        self.gus_stage = 0          # 0..3 inside the supply closet
        self.gus_charge = 0.0       # >0 while he is sprinting at a door
        self.gus_side = "west"

        self.events: list[tuple] = []

    # ------------------------------------------------------------ queries
    @property
    def hour(self) -> int:
        return min(HOURS, int(self.time // HOUR_SECONDS))

    @property
    def clock_label(self) -> str:
        return HOUR_LABELS[self.hour]

    @property
    def progress(self) -> float:
        return min(1.0, self.time / NIGHT_LENGTH)

    @property
    def alive(self) -> bool:
        return self.jumpscare is None and not self.won

    @property
    def usage(self) -> int:
        return (sum(self.doors.values()) + sum(self.lights.values())
                + (1 if self.cam_up else 0))

    @property
    def power_percent(self) -> int:
        return max(0, int(math.ceil(self.power)))

    def drain_rate(self) -> float:
        """Power lost per second."""
        return 0.11 + 0.012 * (self.night - 1) + 0.15 * self.usage

    def aggression(self, base: int) -> int:
        if base <= 0:
            return 0
        return min(20, base + self.hour // 2)

    def gus_room(self) -> str:
        if self.gus_charge > 0:
            return "WEST_HALL" if self.gus_side == "west" else "EAST_HALL"
        return "CLOSET"

    def occupants(self, room: str) -> list[str]:
        out = []
        for a in (self.moose, self.penny):
            if a.room == room:
                out.append(a.key)
        if self.gus_room() == room:
            out.append("gus")
        return out

    def at_door(self, side: str) -> str | None:
        room = "WEST_DOOR" if side == "west" else "EAST_DOOR"
        for a in (self.moose, self.penny):
            if a.room == room:
                return a.key
        return None

    @property
    def watching_gus(self) -> bool:
        return self.cam_up and self.cam == 6

    # ------------------------------------------------------------ controls
    def _can_act(self) -> bool:
        return self.alive and not self.blackout

    def toggle_door(self, side: str) -> bool:
        if not self._can_act() or side not in SIDES:
            return False
        self.doors[side] = not self.doors[side]
        self.events.append(("door", side, self.doors[side]))
        return True

    def toggle_light(self, side: str) -> bool:
        if not self._can_act() or side not in SIDES or self.cam_up:
            return False
        other = "east" if side == "west" else "west"
        if self.lights[other]:
            self.lights[other] = False
            self.events.append(("light", other, False))
        self.lights[side] = not self.lights[side]
        self.events.append(("light", side, self.lights[side]))
        return True

    def toggle_camera(self) -> bool:
        if not self._can_act():
            return False
        self.cam_up = not self.cam_up
        if self.cam_up:
            for side in SIDES:
                if self.lights[side]:
                    self.lights[side] = False
                    self.events.append(("light", side, False))
        self.events.append(("camera", self.cam_up))
        return True

    def select_camera(self, cam: int) -> bool:
        if not self._can_act() or not self.cam_up or cam not in CAM_ROOMS:
            return False
        self.cam = cam
        self.events.append(("cam_switch", cam))
        return True

    # ------------------------------------------------------------ simulation
    def update(self, dt: float) -> None:
        if not self.alive:
            return
        self.time += dt
        if self.time >= NIGHT_LENGTH:
            self.time = NIGHT_LENGTH
            self.won = True
            self.events.append(("win",))
            return

        self.power = max(0.0, self.power - self.drain_rate() * dt)
        if self.power <= 0.0 and not self.blackout:
            self._begin_blackout()

        if self.blackout:
            self._update_blackout(dt)
            return

        self._tick_animatronic(self.moose, dt)
        self._tick_animatronic(self.penny, dt)
        self._tick_gus(dt)

    # -- Mortimer & Penny
    def _tick_animatronic(self, a: Animatronic, dt: float) -> None:
        aggr = self.aggression(a.base)
        if aggr <= 0:
            return
        if a.room == a.door_room:
            a.door_wait -= dt
            if a.door_wait <= 0:
                self._attack(a)
            return
        a.timer += dt
        if a.timer >= a.interval:
            a.timer -= a.interval
            if self.rng.randint(1, 20) <= aggr:
                self._advance(a)

    def _advance(self, a: Animatronic) -> None:
        options = a.path.get(a.room)
        if not options:
            return
        rooms = [r for r, _ in options]
        weights = [w for _, w in options]
        new_room = self.rng.choices(rooms, weights)[0]
        old = a.room
        a.room = new_room
        self.events.append(("move", a.key, old, new_room))
        if new_room == a.door_room:
            a.door_wait = self.rng.uniform(2.5, 5.0)
            self.events.append(("at_door", a.side, a.key))

    def _attack(self, a: Animatronic) -> None:
        if self.doors[a.side]:
            a.room = a.retreat_room
            a.door_wait = 0.0
            a.timer = 0.0
            self.events.append(("knock", a.side))
        else:
            self.jumpscare = a.key
            self.events.append(("jumpscare", a.key))

    # -- Gus
    def _tick_gus(self, dt: float) -> None:
        aggr = self.aggression(self.gus_base)
        if aggr <= 0:
            return
        if self.gus_charge > 0:
            self.gus_charge -= dt
            if self.gus_charge <= 0:
                self.gus_charge = 0.0
                self._gus_hit()
            return
        self.gus_timer += dt
        if self.gus_timer < self.gus_interval:
            return
        self.gus_timer -= self.gus_interval
        if self.watching_gus:
            return                      # he freezes while you watch him
        if self.rng.randint(1, 20) <= aggr:
            if self.gus_stage < 3:
                self.gus_stage += 1
                self.events.append(("gus_stage", self.gus_stage))
            else:
                self.gus_side = self.rng.choice(SIDES)
                self.gus_charge = self.rng.uniform(2.5, 3.5)
                self.events.append(("gus_run", self.gus_side))

    def _gus_hit(self) -> None:
        side = self.gus_side
        if self.doors[side]:
            self.power = max(0.0, self.power - 3.0)   # banging drains power
            self.gus_stage = 0
            self.gus_timer = 0.0
            self.events.append(("knock", side))
        else:
            self.jumpscare = "gus"
            self.events.append(("jumpscare", "gus"))

    # -- Power out
    def _begin_blackout(self) -> None:
        self.blackout = True
        self.blackout_time = 0.0
        self.blackout_limit = self.rng.uniform(16.0, 24.0)
        self.jingle_started = False
        for side in SIDES:
            self.doors[side] = False
            self.lights[side] = False
        self.cam_up = False
        self.events.append(("blackout",))

    def _update_blackout(self, dt: float) -> None:
        self.blackout_time += dt
        if not self.jingle_started and self.blackout_time >= 6.0:
            self.jingle_started = True
            self.events.append(("jingle",))
        if self.blackout_time >= self.blackout_limit:
            self.jumpscare = "moose"
            self.events.append(("jumpscare", "moose"))
