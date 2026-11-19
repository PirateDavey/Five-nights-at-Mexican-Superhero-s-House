import random
import unittest

from logic import NIGHT_LENGTH, HOUR_SECONDS, Night


def simulate(night, seed, policy, dt=0.05):
    n = Night(night, random.Random(seed))
    for _ in range(int(NIGHT_LENGTH / dt) + 800):
        policy(n)
        n.update(dt)
        n.events.clear()
        if n.jumpscare or n.won:
            break
    return n


def idle(n):
    pass


def perfect(n):
    """Closes a door only while something is threatening it."""
    for side in ("west", "east"):
        threatened = (n.at_door(side) is not None
                      or (n.gus_charge > 0 and n.gus_side == side))
        if n.doors[side] != threatened:
            n.toggle_door(side)


def lockdown(n):
    """Both doors shut all night."""
    for side in ("west", "east"):
        if not n.doors[side]:
            n.toggle_door(side)


class NightTests(unittest.TestCase):
    def test_clock_and_win(self):
        n = Night(1, random.Random(0))
        n.moose.base = 0
        self.assertEqual(n.clock_label, "12 AM")
        n.update(HOUR_SECONDS * 2 + 1)
        self.assertEqual(n.clock_label, "2 AM")
        n.update(NIGHT_LENGTH)
        self.assertTrue(n.won)
        self.assertEqual(n.clock_label, "6 AM")
        self.assertIn(("win",), n.events)

    def test_power_usage(self):
        n = Night(1, random.Random(0))
        base = n.drain_rate()
        n.toggle_door("west")
        n.toggle_door("east")
        self.assertEqual(n.usage, 2)
        self.assertGreater(n.drain_rate(), base)
        n.toggle_camera()
        self.assertEqual(n.usage, 3)

    def test_lights_are_exclusive_and_off_on_camera(self):
        n = Night(1, random.Random(0))
        n.toggle_light("west")
        n.toggle_light("east")
        self.assertFalse(n.lights["west"])
        self.assertTrue(n.lights["east"])
        n.toggle_camera()
        self.assertFalse(n.lights["east"])
        self.assertFalse(n.toggle_light("west"))   # not while on camera

    def test_camera_select_needs_monitor(self):
        n = Night(1, random.Random(0))
        self.assertFalse(n.select_camera(3))
        n.toggle_camera()
        self.assertTrue(n.select_camera(3))
        self.assertEqual(n.cam, 3)

    def test_gus_freezes_while_watched(self):
        n = Night(5, random.Random(3))
        n.moose.base = 0
        n.penny.base = 0
        n.gus_stage = 3
        n.toggle_camera()
        n.select_camera(6)
        for _ in range(int(60 / 0.05)):
            n.update(0.05)
            if n.power < 20:
                n.power = 100.0   # keep the lights on for this test
        self.assertEqual(n.gus_stage, 3)
        self.assertEqual(n.gus_charge, 0.0)
        self.assertTrue(n.alive)

    def test_gus_charges_when_unwatched(self):
        n = Night(5, random.Random(3))
        n.moose.base = 0
        n.penny.base = 0
        n.gus_stage = 3
        ran = False
        for _ in range(int(120 / 0.05)):
            n.update(0.05)
            if n.gus_charge > 0:
                ran = True
                break
        self.assertTrue(ran)
        self.assertIn(n.gus_room(), ("WEST_HALL", "EAST_HALL"))

    def test_open_door_means_jumpscare(self):
        n = Night(2, random.Random(1))
        n.moose.room = "WEST_DOOR"
        n.moose.door_wait = 1.0
        for _ in range(40):
            n.update(0.1)
        self.assertEqual(n.jumpscare, "moose")

    def test_closed_door_holds(self):
        n = Night(2, random.Random(1))
        n.penny.room = "EAST_DOOR"
        n.penny.door_wait = 1.0
        n.toggle_door("east")
        for _ in range(15):
            n.update(0.1)
        self.assertIsNone(n.jumpscare)
        self.assertEqual(n.penny.room, "DINING")
        self.assertIn(("knock", "east"), n.events)

    def test_blackout_opens_doors_and_ends_badly(self):
        n = Night(1, random.Random(5))
        n.moose.base = 0
        n.toggle_door("west")
        n.power = 0.01
        n.update(0.5)
        self.assertTrue(n.blackout)
        self.assertFalse(n.doors["west"])
        self.assertFalse(n.toggle_door("west"))
        for _ in range(int(40 / 0.1)):
            n.update(0.1)
        self.assertEqual(n.jumpscare, "moose")

    def test_perfect_defender_always_survives(self):
        for night in range(1, 6):
            for seed in range(25):
                n = simulate(night, seed, perfect)
                self.assertTrue(n.won, f"night {night} seed {seed} died to {n.jumpscare}")

    def test_idle_guard_usually_dies_late_game(self):
        deaths = sum(1 for seed in range(40) if not simulate(5, seed, idle).won)
        self.assertGreaterEqual(deaths, 36)

    def test_night_one_is_gentle_for_a_careful_guard(self):
        wins = sum(1 for seed in range(40) if simulate(1, seed, perfect).won)
        self.assertEqual(wins, 40)

    def test_lockdown_runs_out_of_power(self):
        for seed in range(15):
            n = simulate(5, seed, lockdown)
            self.assertFalse(n.won, f"seed {seed}")
            self.assertTrue(n.blackout)


if __name__ == "__main__":
    unittest.main()
