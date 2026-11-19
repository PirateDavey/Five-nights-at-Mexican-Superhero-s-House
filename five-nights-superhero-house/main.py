"""Five Nights at Mexican Superhero's House - an unofficial survival-horror fan game.

Run:    python main.py
Test:   python main.py --smoke      (headless self-test, used by CI)
"""
import json
import os
import random
import sys
from pathlib import Path

SMOKE = "--smoke" in sys.argv
if SMOKE:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

import art  # noqa: E402
import audio  # noqa: E402
import logic  # noqa: E402

SAVE_FILE = Path.home() / ".superhero_house_save.json"

# (start_second, end_second, text) shown as subtitles at the start of a night
PHONE_CALLS = {
    1: [
        (2, 9, "Hello? Hello, is this thing on? Welcome to the house, new guy!"),
        (9, 18, "I had your job before you. Just a few tips, since the local heroes get... restless after midnight."),
        (18, 28, "El Trueno prefers the west side, La Mariposa the east. Glowing eyes in your doorway? Shut the door."),
        (28, 38, "Doors, lights and cameras eat power. Run out, and you'll hear the music box."),
        (38, 47, "El Tornado hides in the storage closet. He only moves when nobody is looking at him. Buena suerte!"),
    ],
    2: [
        (2, 10, "Hey, you're back! Great. Most people don't come back for a second night."),
        (10, 20, "La Mariposa is waking up now. She's quiet. Listen for footsteps and watch the east hall."),
        (20, 30, "If El Tornado leaves the closet, he'll charge a door. Close it fast, but it costs a little power."),
    ],
    3: [
        (2, 11, "Night three. They're getting restless. Between us, I never made it past this point."),
        (11, 20, "Check the cameras in bursts. Staring at them all night will drain you dry."),
    ],
    4: [
        (2, 10, "Still here? ...Okay. Don't relax. Don't blink. Keep that power up."),
    ],
    5: [
        (2, 11, "Last night. Whatever happens, make it to six. Just... make it to six."),
    ],
}


def load_progress():
    try:
        return max(1, min(logic.MAX_NIGHT, int(json.loads(SAVE_FILE.read_text())["night"])))
    except Exception:
        return 1


def save_progress(night):
    if SMOKE:
        return
    try:
        SAVE_FILE.write_text(json.dumps({"night": night}))
    except OSError:
        pass


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Five Nights at Mexican Superhero's House  (unofficial fan game)")
        try:
            flags = 0 if SMOKE else (pygame.SCALED | pygame.RESIZABLE)
            self.screen = pygame.display.set_mode((art.W, art.H), flags)
        except pygame.error:
            self.screen = pygame.display.set_mode((art.W, art.H))
        art.init_assets()
        try:
            pygame.display.set_icon(art.make_icon())
        except pygame.error:
            pass
        self.clock = pygame.time.Clock()
        self.audio = audio.Audio()
        self.running = True
        self.t = 0.0
        self.state = "title"
        self.state_t = 0.0
        self.progress = load_progress()
        self.menu_index = 0
        self.menu_items = []
        self.menu_rects = []
        self.refresh_menu()
        self.night = None
        self.night_num = 1
        self.slide = {"west": 0.0, "east": 0.0}
        self.glitch = 0.0
        self.flicker = False
        self.call_muted = False
        self.scare_who = "moose"
        self.paused = False

    # ------------------------------------------------------------ flow
    def refresh_menu(self):
        self.menu_items = ["NEW GAME"]
        if self.progress > 1:
            self.menu_items.append(f"CONTINUE (NIGHT {self.progress})")
        self.menu_items.append("QUIT")
        self.menu_index = min(self.menu_index, len(self.menu_items) - 1)

    def go_title(self):
        self.audio.stop_all()
        self.state = "title"
        self.state_t = 0.0
        self.paused = False
        self.refresh_menu()

    def start_night(self, n):
        self.audio.stop_all()
        self.night_num = n
        self.night = logic.Night(n)
        self.slide = {"west": 0.0, "east": 0.0}
        self.glitch = 0.0
        self.flicker = False
        self.call_muted = False
        self.paused = False
        self.state = "intro"
        self.state_t = 0.0

    def begin_play(self):
        self.state = "play"
        self.state_t = 0.0
        self.audio.loop("hum")
        if PHONE_CALLS.get(self.night_num):
            self.audio.play("ring")

    def begin_scare(self, who):
        self.scare_who = who
        self.audio.stop_all()
        self.audio.play("scare")
        self.state = "scare"
        self.state_t = 0.0

    def begin_win(self):
        self.audio.stop_all()
        self.audio.play("chime")
        if self.night_num < logic.MAX_NIGHT:
            self.progress = max(self.progress, self.night_num + 1)
        save_progress(self.progress)
        self.state = "win"
        self.state_t = 0.0

    def menu_activate(self):
        label = self.menu_items[self.menu_index]
        if label == "NEW GAME":
            self.start_night(1)
        elif label.startswith("CONTINUE"):
            self.start_night(self.progress)
        else:
            self.running = False

    def current_subtitle(self):
        if self.call_muted or self.night is None:
            return ""
        for start, end, msg in PHONE_CALLS.get(self.night_num, []):
            if start <= self.night.time < end:
                return msg
        return ""

    # ------------------------------------------------------------ input
    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.KEYDOWN:
            self.on_key(e.key)
        elif e.type == pygame.MOUSEBUTTONDOWN and getattr(e, "button", 1) == 1:
            self.on_click(e.pos)
        elif e.type == pygame.MOUSEMOTION and self.state == "title":
            for i, r in enumerate(self.menu_rects):
                if r.collidepoint(e.pos):
                    self.menu_index = i

    def on_key(self, key):
        if key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
            return
        st = self.state
        if st == "title":
            if key in (pygame.K_UP, pygame.K_w):
                self.menu_index = (self.menu_index - 1) % len(self.menu_items)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu_index = (self.menu_index + 1) % len(self.menu_items)
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.menu_activate()
            elif key == pygame.K_ESCAPE:
                self.running = False
        elif st == "play":
            self.on_play_key(key)
        elif st == "over":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.start_night(self.night_num)
            elif key == pygame.K_ESCAPE:
                self.go_title()
        elif st == "win":
            if self.state_t > 5.0 and key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                if self.night_num >= logic.MAX_NIGHT:
                    self.state = "ending"
                    self.state_t = 0.0
                else:
                    self.start_night(self.night_num + 1)
        elif st == "ending":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                self.go_title()
        elif st == "intro":
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                self.state_t = max(self.state_t, 3.2)

    def on_play_key(self, key):
        n = self.night
        if key == pygame.K_ESCAPE:
            self.paused = not self.paused
            if self.paused:
                self.audio.stop_all()
            else:
                self.audio.loop("hum")
            return
        if self.paused:
            if key == pygame.K_t:
                self.go_title()
            return
        if key == pygame.K_a:
            n.toggle_door("west")
        elif key == pygame.K_d:
            n.toggle_door("east")
        elif key == pygame.K_q:
            n.toggle_light("west")
        elif key == pygame.K_e:
            n.toggle_light("east")
        elif key == pygame.K_SPACE:
            n.toggle_camera()
        elif key == pygame.K_m:
            self.call_muted = True
        elif pygame.K_1 <= key <= pygame.K_6:
            n.select_camera(key - pygame.K_0)
        self.process_events()

    def on_click(self, pos):
        st = self.state
        if st == "title":
            for i, r in enumerate(self.menu_rects):
                if r.collidepoint(pos):
                    self.menu_index = i
                    self.menu_activate()
                    return
        elif st == "play" and not self.paused:
            n = self.night
            if art.OFFICE_BUTTONS["cam"].collidepoint(pos):
                n.toggle_camera()
            elif n.cam_up:
                cam = art.cam_button_at(pos)
                if cam:
                    n.select_camera(cam)
            else:
                name = art.office_button_at(pos)
                if name == "door_west":
                    n.toggle_door("west")
                elif name == "door_east":
                    n.toggle_door("east")
                elif name == "light_west":
                    n.toggle_light("west")
                elif name == "light_east":
                    n.toggle_light("east")
            self.process_events()
        elif st in ("over", "win", "ending", "intro"):
            self.on_key(pygame.K_RETURN)

    # ------------------------------------------------------------ simulation
    def process_events(self):
        n = self.night
        for ev in n.events:
            kind = ev[0]
            if kind == "door":
                self.audio.play("door")
            elif kind == "light":
                if any(n.lights.values()):
                    self.audio.loop("buzz")
                else:
                    self.audio.stop_loop("buzz")
            elif kind == "camera":
                self.audio.play("cam_up" if ev[1] else "cam_down")
                self.audio.stop_loop("buzz")
            elif kind == "cam_switch":
                self.audio.play("switch")
                self.glitch = 0.12
            elif kind == "move":
                self.audio.play("step")
                if n.cam_up:
                    room = logic.CAM_ROOMS[n.cam]
                    if room in (ev[2], ev[3]):
                        self.glitch = 0.3
            elif kind == "at_door":
                self.audio.play("step", 0.8)
            elif kind == "knock":
                self.audio.play("knock")
            elif kind == "gus_stage":
                self.audio.play("step", 0.3)
            elif kind == "gus_run":
                self.audio.play("run")
                if n.cam_up and n.cam in (4, 5):
                    self.glitch = 0.4
            elif kind == "blackout":
                self.audio.stop_loop("buzz")
                self.audio.stop_loop("hum")
                self.audio.play("power_down")
            elif kind == "jingle":
                self.audio.loop("jingle")
        n.events.clear()

    def update(self, dt):
        self.t += dt
        self.state_t += dt
        st = self.state
        if st == "intro":
            if self.state_t >= 3.2:
                self.begin_play()
        elif st == "play":
            if not self.paused:
                self.update_play(dt)
        elif st == "scare":
            if self.state_t >= 1.6:
                self.state = "over"
                self.state_t = 0.0

    def update_play(self, dt):
        n = self.night
        n.update(dt)
        self.process_events()
        if n.jumpscare:
            self.begin_scare(n.jumpscare)
            return
        if n.won:
            self.begin_win()
            return
        for side in ("west", "east"):
            target = 1.0 if n.doors[side] else 0.0
            cur = self.slide[side]
            step = dt * 4.5
            self.slide[side] = min(target, cur + step) if cur < target else max(target, cur - step)
        self.glitch = max(0.0, self.glitch - dt)
        self.flicker = (n.lights["west"] or n.lights["east"]) and random.random() < 0.015

    # ------------------------------------------------------------ drawing
    def draw(self):
        s = self.screen
        st = self.state
        if st == "title":
            self.menu_rects = art.draw_title(s, self.t, self.menu_index, self.menu_items)
        elif st == "intro":
            art.draw_night_card(s, self.night_num, self.state_t)
        elif st == "play":
            n = self.night
            if n.cam_up and not n.blackout:
                art.draw_camera(s, n, self.t, self.glitch)
            else:
                art.draw_office(s, n, self.t, self.slide, self.flicker)
            art.draw_subtitle(s, self.current_subtitle())
            if self.paused:
                art.draw_pause(s)
        elif st == "scare":
            art.draw_jumpscare(s, self.scare_who, self.state_t)
        elif st == "over":
            art.draw_game_over(s, self.t)
        elif st == "win":
            art.draw_win(s, self.state_t, self.night_num)
        elif st == "ending":
            art.draw_ending(s, self.t)
        pygame.display.flip()

    # ------------------------------------------------------------ loops
    def run(self):
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.1)
            for e in pygame.event.get():
                self.handle_event(e)
            self.update(dt)
            self.draw()
        pygame.quit()

    def smoke(self):
        """Headless self-test: drives every screen and every input path."""
        rng = random.Random(1)
        key = pygame.event.Event
        self.progress = 3
        self.refresh_menu()
        self.draw()
        self.handle_event(key(pygame.MOUSEMOTION, pos=(640, 400), rel=(0, 0), buttons=(0, 0, 0)))
        self.handle_event(key(pygame.KEYDOWN, key=pygame.K_DOWN))
        self.handle_event(key(pygame.KEYDOWN, key=pygame.K_UP))
        self.draw()

        actions = [pygame.K_a, pygame.K_d, pygame.K_q, pygame.K_e, pygame.K_SPACE,
                   pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_m]
        for night in range(1, logic.MAX_NIGHT + 1):
            self.start_night(night)
            self.night.gus_stage = 3
            for frame in range(60 * 70):
                if self.state == "play" and frame % 20 == 0:
                    self.handle_event(key(pygame.KEYDOWN, key=rng.choice(actions)))
                if self.state == "play" and frame % 97 == 0:
                    pos = rng.choice([(370, 300), (370, 390), (900, 300), (900, 390),
                                      (640, 680), (1100, 470), (1015, 590)])
                    self.handle_event(key(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
                self.update(1 / 60)
                self.draw()
                if self.state in ("over", "win"):
                    break
            self.state_t = 10.0
            self.draw()

        # power failure sequence
        self.start_night(5)
        self.state = "play"
        self.night.power = 0.01
        for _ in range(60 * 30):
            self.update(1 / 60)
            self.draw()
            if self.state != "play":
                break

        # every remaining screen
        for who in ("moose", "penny", "gus"):
            self.scare_who = who
            self.state = "scare"
            self.state_t = 0.4
            self.draw()
        for st in ("over", "ending", "win", "title"):
            self.state = st
            self.state_t = 8.0
            self.draw()
        self.start_night(2)
        self.state = "play"
        self.handle_event(key(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.draw()
        self.handle_event(key(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        print("SMOKE OK")


def main():
    game = Game()
    if SMOKE:
        game.smoke()
        pygame.quit()
        return
    game.run()


if __name__ == "__main__":
    main()
