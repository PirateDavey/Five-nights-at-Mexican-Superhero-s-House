"""All drawing code. Everything is generated procedurally - no image files."""
from __future__ import annotations

import math
import random

import pygame

import logic

W, H = 1280, 720

WHITE = (240, 240, 240)
GREY = (150, 150, 155)
RED = (205, 35, 40)
GREEN = (60, 200, 90)
YELLOW = (235, 200, 60)
ORANGE = (235, 130, 40)

# ---------------------------------------------------------------- layout
DL = pygame.Rect(60, 140, 250, 430)      # west doorway
DR = pygame.Rect(970, 140, 250, 430)     # east doorway
OFFICE_BUTTONS = {
    "door_west": pygame.Rect(330, 270, 76, 76),
    "light_west": pygame.Rect(330, 358, 76, 76),
    "door_east": pygame.Rect(874, 270, 76, 76),
    "light_east": pygame.Rect(874, 358, 76, 76),
    "cam": pygame.Rect(440, 652, 400, 54),
}
CAM_BUTTONS = {
    1: pygame.Rect(1100, 450, 70, 44),
    2: pygame.Rect(1100, 512, 70, 44),
    3: pygame.Rect(1185, 512, 70, 44),
    6: pygame.Rect(1015, 512, 70, 44),
    4: pygame.Rect(1015, 574, 70, 44),
    5: pygame.Rect(1185, 574, 70, 44),
}
MAP_BOX = pygame.Rect(1000, 436, 270, 262)

# ---------------------------------------------------------------- helpers
_fonts: dict[int, pygame.font.Font] = {}


def font(size: int) -> pygame.font.Font:
    f = _fonts.get(size)
    if f is None:
        f = pygame.font.Font(None, size)
        _fonts[size] = f
    return f


def text(s, msg, size, color, pos, anchor="topleft", shadow=True):
    f = font(size)
    img = f.render(msg, True, color)
    r = img.get_rect(**{anchor: pos})
    if shadow:
        s.blit(f.render(msg, True, (0, 0, 0)), r.move(2, 2))
    s.blit(img, r)
    return r


def _i(v):
    return int(round(v))


def _ell(s, c, cx, cy, w, h, width=0):
    w = max(2, _i(w))
    h = max(2, _i(h))
    pygame.draw.ellipse(s, c, (_i(cx - w / 2), _i(cy - h / 2), w, h), width)


def _rect(s, c, x, y, w, h, r=0):
    pygame.draw.rect(s, c, (_i(x), _i(y), max(1, _i(w)), max(1, _i(h))),
                     0, border_radius=max(0, _i(r)))


def _poly(s, c, pts):
    pygame.draw.polygon(s, c, [(_i(x), _i(y)) for x, y in pts])


def _line(s, c, a, b, w=1):
    pygame.draw.line(s, c, (_i(a[0]), _i(a[1])), (_i(b[0]), _i(b[1])), max(1, _i(w)))


def _vgrad(s, rect, c1, c2):
    x, y, w, h = rect
    for i in range(h):
        k = i / max(1, h - 1)
        col = tuple(_i(c1[j] + (c2[j] - c1[j]) * k) for j in range(3))
        pygame.draw.line(s, col, (x, y + i), (x + w - 1, y + i))


# ---------------------------------------------------------------- characters
def _eye(s, x, y, r, hostile, color=(235, 235, 225)):
    _ell(s, color, x, y, r * 2, r * 2)
    if hostile:
        _ell(s, (255, 30, 30), x, y, r * 1.1, r * 1.1)
        _ell(s, (255, 190, 190), x, y, r * 0.35, r * 0.35)
    else:
        _ell(s, (12, 12, 12), x, y, r * 1.0, r * 1.0)
        _ell(s, (255, 255, 255), x - r * 0.2, y - r * 0.2, r * 0.3, r * 0.3)


def _hero(s, cx, cy, sc, mask, trim, cape, suit, hostile, scream, style):
    """An original caped luchador-style hero. style: crest / wings / horns."""
    if style == "wings":
        for sg in (-1, 1):
            _poly(s, cape, [(cx + sg * 40 * sc, cy + 90 * sc), (cx + sg * 235 * sc, cy + 10 * sc),
                            (cx + sg * 215 * sc, cy + 250 * sc), (cx + sg * 60 * sc, cy + 300 * sc)])
            _poly(s, trim, [(cx + sg * 70 * sc, cy + 150 * sc), (cx + sg * 175 * sc, cy + 118 * sc),
                            (cx + sg * 165 * sc, cy + 230 * sc)])
    else:
        _poly(s, cape, [(cx - 110 * sc, cy + 80 * sc), (cx + 110 * sc, cy + 80 * sc),
                        (cx + 165 * sc, cy + 335 * sc), (cx - 165 * sc, cy + 335 * sc)])
        _line(s, trim, (cx - 140 * sc, cy + 320 * sc), (cx + 140 * sc, cy + 320 * sc), 8 * sc)
    _rect(s, suit, cx - 85 * sc, cy + 75 * sc, 170 * sc, 230 * sc, 36 * sc)
    _ell(s, trim, cx, cy + 130 * sc, 60 * sc, 60 * sc)
    _ell(s, suit, cx, cy + 130 * sc, 36 * sc, 36 * sc)
    _ell(s, (240, 205, 70), cx, cy + 130 * sc, 16 * sc, 16 * sc)
    _rect(s, trim, cx - 85 * sc, cy + 200 * sc, 170 * sc, 26 * sc, 6 * sc)
    _ell(s, (240, 205, 70), cx, cy + 213 * sc, 34 * sc, 34 * sc)
    if style == "crest":
        _poly(s, trim, [(cx - 24 * sc, cy - 60 * sc), (cx + 24 * sc, cy - 60 * sc), (cx, cy - 165 * sc)])
    elif style == "wings":
        for sg in (-1, 1):
            _line(s, trim, (cx + sg * 30 * sc, cy - 70 * sc), (cx + sg * 80 * sc, cy - 150 * sc), 6 * sc)
            _ell(s, (250, 210, 60), cx + sg * 82 * sc, cy - 154 * sc, 22 * sc, 22 * sc)
    else:
        for sg in (-1, 1):
            _poly(s, trim, [(cx + sg * 30 * sc, cy - 60 * sc), (cx + sg * 78 * sc, cy - 62 * sc),
                            (cx + sg * 70 * sc, cy - 150 * sc)])
    _ell(s, mask, cx, cy, 166 * sc, 166 * sc)
    _line(s, trim, (cx, cy - 82 * sc), (cx, cy - 44 * sc), 9 * sc)
    for sg in (-1, 1):
        _ell(s, trim, cx + sg * 42 * sc, cy - 14 * sc, 58 * sc, 42 * sc)
        _eye(s, cx + sg * 42 * sc, cy - 14 * sc, 15 * sc, hostile)
    if scream:
        _ell(s, (40, 0, 6), cx, cy + 52 * sc, 84 * sc, 64 * sc)
        for k in range(-3, 4):
            x = cx + k * 11 * sc
            _poly(s, (235, 235, 220), [(x - 5 * sc, cy + 24 * sc), (x + 5 * sc, cy + 24 * sc), (x, cy + 46 * sc)])
    else:
        _line(s, trim, (cx - 28 * sc, cy + 52 * sc), (cx + 28 * sc, cy + 52 * sc), 5 * sc)


def draw_moose(s, cx, cy, sc=1.0, hostile=False, scream=False):
    """El Trueno - green and gold, cape, head crest."""
    _hero(s, cx, cy, sc, (52, 130, 70), (224, 178, 50), (30, 90, 52), (38, 100, 60), hostile, scream, "crest")


def draw_penny(s, cx, cy, sc=1.0, hostile=False, scream=False):
    """La Mariposa - purple and pink, butterfly-wing cape."""
    _hero(s, cx, cy, sc, (130, 60, 160), (240, 120, 190), (170, 80, 200), (96, 44, 124), hostile, scream, "wings")


def draw_gus(s, cx, cy, sc=1.0, hostile=False, scream=False):
    """El Tornado - orange and black, horned mask."""
    _hero(s, cx, cy, sc, (40, 40, 44), (235, 120, 30), (210, 90, 20), (30, 30, 34), hostile, scream, "horns")


CHARACTERS = {"moose": draw_moose, "penny": draw_penny, "gus": draw_gus}


# ---------------------------------------------------------------- cached assets
_noise_frames: list[pygame.Surface] = []
_scan: pygame.Surface | None = None
_vig: pygame.Surface | None = None
_dark: pygame.Surface | None = None
_cam_surf: pygame.Surface | None = None
_scene_cache: dict = {}
_office_cache: list = []


def init_assets():
    global _scan, _vig, _dark, _cam_surf
    rnd = random.Random(7)
    for _ in range(6):
        w, h = 256, 144
        gray = rnd.randbytes(w * h)
        buf = bytearray(w * h * 3)
        buf[0::3] = gray
        buf[1::3] = gray
        buf[2::3] = gray
        small = pygame.image.frombuffer(bytes(buf), (w, h), "RGB")
        _noise_frames.append(pygame.transform.scale(small, (W, H)).convert())
    _scan = pygame.Surface((W, H), pygame.SRCALPHA)
    for y in range(0, H, 4):
        pygame.draw.line(_scan, (0, 0, 0, 55), (0, y), (W, y), 1)
    _vig = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(0, 160, 5):
        a = _i(170 * (1 - i / 160) ** 2)
        pygame.draw.rect(_vig, (0, 0, 0, a), (i, i, W - 2 * i, H - 2 * i), 5)
    _dark = pygame.Surface((W, H))
    _dark.fill((0, 0, 0))
    _cam_surf = pygame.Surface((W, H))


def _darken(s, alpha):
    _dark.set_alpha(max(0, min(255, _i(alpha))))
    s.blit(_dark, (0, 0))


def _static(s, t, alpha):
    f = _noise_frames[int(t * 24) % len(_noise_frames)]
    f.set_alpha(max(0, min(255, _i(alpha))))
    s.blit(f, (0, 0))


def _finish(s, t, noise=30, vignette=True):
    _static(s, t, noise)
    s.blit(_scan, (0, 0))
    if vignette:
        s.blit(_vig, (0, 0))


# ---------------------------------------------------------------- camera scenes
def _scene_stage():
    s = pygame.Surface((W, H))
    s.fill((26, 16, 34))
    for x in range(0, W, 80):
        pygame.draw.rect(s, (34, 22, 44) if (x // 80) % 2 else (28, 18, 38), (x, 0, 80, 430))
    _poly(s, (120, 20, 30), [(0, 0), (270, 0), (190, 430), (0, 430)])
    _poly(s, (120, 20, 30), [(W, 0), (W - 270, 0), (W - 190, 430), (W, 430)])
    for k in range(1, 6):
        _line(s, (80, 10, 20), (k * 42, 0), (k * 30, 430), 3)
        _line(s, (80, 10, 20), (W - k * 42, 0), (W - k * 30, 430), 3)
    _poly(s, (92, 62, 40), [(150, 430), (W - 150, 430), (W, H), (0, H)])
    for k in range(1, 8):
        y = 430 + k * k * 6
        _line(s, (70, 46, 30), (0, y), (W, y), 2)
    _rect(s, (60, 20, 70), 420, 60, 440, 80, 14)
    text(s, "BIENVENIDOS", 70, (240, 210, 90), (640, 100), "center")
    for x in (400, 880):
        _ell(s, (72, 50, 34), x, 610, 280, 60)
    glow = pygame.Surface((W, H), pygame.SRCALPHA)
    for x in (400, 880):
        pygame.draw.polygon(glow, (255, 240, 180, 34), [(x - 20, 0), (x + 20, 0), (x + 190, 620), (x - 190, 620)])
    s.blit(glow, (0, 0))
    return s


def _scene_dining():
    s = pygame.Surface((W, H))
    _vgrad(s, (0, 0, W, 380), (40, 36, 54), (58, 50, 70))
    for x in (120, 520, 920):
        _rect(s, (14, 20, 40), x, 60, 240, 180, 6)
        _ell(s, (230, 230, 200), x + 190, 110, 26, 26)
        _rect(s, (70, 56, 40), x - 6, 54, 252, 8)
    pygame.draw.rect(s, (60, 52, 70), (0, 360, W, 360))
    ys = [360, 382, 410, 444, 486, 538, 600, 672, 720]
    for r in range(len(ys) - 1):
        for c in range(-10, 30):
            x0 = 640 + (c - 10) * (r + 1) * 14
            col = (74, 66, 86) if (r + c) % 2 else (46, 40, 58)
            _rect(s, col, x0, ys[r], (r + 1) * 14 + 1, ys[r + 1] - ys[r] + 1)
    for x, y in ((260, 570), (640, 500), (1020, 570)):
        _rect(s, (60, 44, 34), x - 12, y, 24, 100)
        _ell(s, (170, 40, 60), x, y, 320, 96)
        _ell(s, (200, 70, 90), x, y - 6, 300, 80)
        _poly(s, (240, 220, 80), [(x - 14, y - 6), (x + 14, y - 6), (x, y - 56)])
        _poly(s, (80, 200, 240), [(x + 70, y - 4), (x + 98, y - 4), (x + 84, y - 52)])
    for i, (bx, col) in enumerate(((90, (200, 50, 60)), (140, (60, 120, 210)), (190, (230, 200, 60)))):
        _ell(s, col, bx, 300 + i * 12, 54, 66)
        _line(s, (200, 200, 200), (bx, 334 + i * 12), (bx + 6, 420), 2)
    return s


def _scene_kitchen():
    s = pygame.Surface((W, H))
    s.fill((46, 52, 52))
    for x in range(0, W, 64):
        _line(s, (34, 40, 40), (x, 0), (x, 500), 2)
    for y in range(0, 500, 64):
        _line(s, (34, 40, 40), (0, y), (W, y), 2)
    _rect(s, (30, 30, 34), 0, 70, W, 10)
    for i, x in enumerate(range(100, W, 170)):
        _line(s, (30, 30, 34), (x, 78), (x, 130 + (i % 3) * 14), 4)
        _ell(s, (120, 120, 130), x, 160 + (i % 3) * 14, 90, 60)
        _ell(s, (70, 70, 80), x, 148 + (i % 3) * 14, 70, 22)
    _rect(s, (120, 124, 130), 0, 500, W, 220)
    _rect(s, (90, 94, 100), 0, 500, W, 18)
    _rect(s, (30, 30, 36), 140, 380, 340, 120, 8)
    for k in range(4):
        _ell(s, (70, 40, 30), 190 + k * 80, 380, 56, 18)
    _rect(s, (150, 154, 160), 900, 280, 220, 220, 10)
    _rect(s, (60, 64, 70), 930, 310, 160, 100, 6)
    return s


def _scene_hall():
    s = pygame.Surface((W, H))
    s.fill((16, 18, 22))
    _poly(s, (34, 36, 44), [(0, 0), (W, 0), (840, 250), (440, 250)])
    _poly(s, (52, 54, 62), [(0, H), (W, H), (840, 470), (440, 470)])
    _poly(s, (64, 66, 78), [(0, 0), (440, 250), (440, 470), (0, H)])
    _poly(s, (58, 60, 72), [(W, 0), (840, 250), (840, 470), (W, H)])
    _rect(s, (22, 24, 30), 440, 250, 400, 220)
    _rect(s, (6, 6, 8), 560, 300, 160, 170)

    def wall_pt(x, f):
        top = 250 * (x / 440)
        bottom = H - 250 * (x / 440)
        return (x, top + f * (bottom - top))

    for x0, x1, col in ((40, 150, (190, 60, 70)), (200, 320, (70, 120, 190))):
        _poly(s, col, [wall_pt(x0, 0.24), wall_pt(x1, 0.24), wall_pt(x1, 0.6), wall_pt(x0, 0.6)])
    for x in (100, 260, 380):
        _poly(s, (255, 244, 190), [wall_pt(x, 0.04), wall_pt(x + 30, 0.04), wall_pt(x + 30, 0.08), wall_pt(x, 0.08)])
    for k in range(1, 8):
        y = 470 + k * k * 4
        _line(s, (40, 42, 48), (440 - k * 60, y), (840 + k * 60, y), 2)
    return s


def _scene_closet():
    s = pygame.Surface((W, H))
    _vgrad(s, (0, 0, W, H), (28, 26, 24), (14, 13, 12))
    for y in (180, 330, 480):
        _rect(s, (84, 62, 40), 40, y, 440, 16)
        for k in range(4):
            col = ((140, 108, 66), (118, 90, 56), (156, 120, 76), (104, 80, 50))[k]
            _rect(s, col, 60 + k * 105, y - 90 + (k % 2) * 20, 90, 90 - (k % 2) * 20)
            _line(s, (90, 66, 40), (60 + k * 105, y - 60), (150 + k * 105, y - 60), 3)
    _line(s, (30, 30, 30), (640, 0), (640, 90), 3)
    _ell(s, (255, 230, 150), 640, 100, 34, 34)
    glow = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.polygon(glow, (255, 230, 150, 26), [(640, 100), (380, 720), (900, 720)])
    s.blit(glow, (0, 0))
    _rect(s, (50, 46, 40), 0, 600, W, 120)
    _ell(s, (90, 96, 104), 640, 640, 150, 52)
    _rect(s, (90, 96, 104), 565, 580, 150, 60)
    _line(s, (140, 110, 70), (700, 590), (790, 330), 8)
    for k in range(7):
        _line(s, (200, 200, 190), (790, 330), (772 + k * 6, 300), 3)
    return s


def _cam_scene(cam):
    sc = _scene_cache.get(cam)
    if sc is None:
        if cam == 1:
            sc = _scene_stage()
        elif cam == 2:
            sc = _scene_dining()
        elif cam == 3:
            sc = _scene_kitchen()
        elif cam == 4:
            sc = _scene_hall()
        elif cam == 5:
            sc = pygame.transform.flip(_scene_hall(), True, False)
        else:
            sc = _scene_closet()
        _scene_cache[cam] = sc
    return sc


_OCC_POS = {
    1: {"moose": (400, 270, 0.95), "penny": (880, 270, 0.95)},
    2: {"moose": (470, 230, 0.85), "penny": (800, 230, 0.85)},
    3: {"moose": (400, 250, 0.9), "penny": (760, 250, 0.9)},
    4: {"moose": (640, 285, 0.72), "penny": (640, 285, 0.72)},
    5: {"moose": (640, 285, 0.72), "penny": (640, 285, 0.72)},
}


def _draw_cam_world(s, cam, n, t):
    s.blit(_cam_scene(cam), (0, 0))
    room = logic.CAM_ROOMS[cam]
    for key in n.occupants(room):
        if key == "gus":
            _draw_gus_cam(s, cam, n, t)
            continue
        x, y, sc = _OCC_POS[cam][key]
        CHARACTERS[key](s, x, y, sc, hostile=False)


def _draw_gus_cam(s, cam, n, t):
    if cam in (4, 5):   # charging down a hallway
        for k in range(10):
            y = random.randint(120, 640)
            _line(s, (200, 200, 200), (random.randint(300, 900), y), (random.randint(300, 900), y + 4), 2)
        draw_gus(s, 640, 300, 1.35, hostile=True, scream=True)
        return
    st = n.gus_stage
    if st == 0:
        for sg in (-1, 1):
            _ell(s, (255, 230, 80), 930 + sg * 26, 430, 16, 10)
            _ell(s, (255, 255, 200), 930 + sg * 26, 430, 6, 6)
    elif st == 1:
        draw_gus(s, 930, 440, 0.55)
        _rect(s, (118, 90, 56), 840, 480, 180, 140)
        _line(s, (90, 66, 40), (840, 540), (1020, 540), 3)
    elif st == 2:
        draw_gus(s, 880, 370, 0.9, hostile=True)
    else:
        draw_gus(s, 800, 320, 1.4, hostile=True)


def draw_camera(s, n, t, glitch):
    surf = _cam_surf
    surf.fill((0, 0, 0))
    _draw_cam_world(surf, n.cam, n, t)
    surf.fill((165, 215, 175), special_flags=pygame.BLEND_RGB_MULT)
    dx = dy = 0
    if glitch > 0:
        dx = random.randint(-18, 18)
        dy = random.randint(-6, 6)
        s.fill((0, 0, 0))
    s.blit(surf, (dx, dy))
    _finish(s, t, noise=28 + glitch * 420)
    if random.random() < 0.004:      # a rare, unsettling flash
        _darken(s, 120)
        text(s, "BEHIND YOU", 90, (170, 20, 20), (640, 360), "center")
    draw_hud(s, n, t)
    text(s, f"CAM {n.cam}", 54, WHITE, (30, 24))
    text(s, logic.CAM_NAMES[n.cam], 36, (200, 230, 200), (30, 70))
    if int(t * 1.6) % 2 == 0:
        pygame.draw.circle(s, RED, (250, 44), 12)
        text(s, "REC", 30, RED, (270, 32))
    # floor map
    pygame.draw.rect(s, (10, 14, 10), MAP_BOX)
    pygame.draw.rect(s, (90, 130, 90), MAP_BOX, 2)
    for cam, r in CAM_BUTTONS.items():
        on = cam == n.cam
        pygame.draw.rect(s, (70, 150, 80) if on else (30, 60, 34), r)
        pygame.draw.rect(s, (170, 230, 170), r, 2)
        text(s, str(cam), 38, WHITE if on else (170, 220, 170), r.center, "center", shadow=False)
    you = pygame.Rect(1100, 636, 70, 44)
    pygame.draw.rect(s, (60, 60, 24), you)
    text(s, "YOU", 28, YELLOW, you.center, "center", shadow=False)
    _draw_cam_bar(s, n)


def _draw_cam_bar(s, n):
    r = OFFICE_BUTTONS["cam"]
    pygame.draw.rect(s, (24, 28, 36), r, border_radius=10)
    pygame.draw.rect(s, (130, 140, 160), r, 3, border_radius=10)
    label = "CLOSE CAMERAS  [SPACE]" if n.cam_up else "OPEN CAMERAS  [SPACE]"
    text(s, label, 34, WHITE, r.center, "center")


# ---------------------------------------------------------------- office
def _office_bg():
    if _office_cache:
        return _office_cache[0]
    s = pygame.Surface((W, H))
    _vgrad(s, (0, 0, W, 600), (58, 62, 74), (40, 43, 52))
    for x in range(0, W, 96):
        _line(s, (46, 49, 60), (x, 0), (x, 600), 2)
    _rect(s, (30, 30, 36), 0, 590, W, 16)
    _rect(s, (30, 26, 30), 0, 606, W, 114)
    # poster
    _rect(s, (210, 190, 120), 500, 90, 280, 150, 6)
    _rect(s, (190, 60, 70), 512, 102, 256, 126, 4)
    text(s, "FIESTA!", 50, (250, 230, 120), (640, 140), "center")
    text(s, "Home sweet hero home", 26, (250, 240, 220), (640, 190), "center", shadow=False)
    # desk
    _poly(s, (84, 62, 46), [(360, 548), (920, 548), (960, 720), (320, 720)])
    _rect(s, (104, 78, 58), 360, 540, 560, 14, 4)
    # monitor
    _rect(s, (20, 20, 24), 540, 440, 200, 120, 8)
    _rect(s, (16, 44, 36), 552, 452, 176, 96, 4)
    for y in range(456, 546, 6):
        _line(s, (24, 70, 56), (554, y), (726, y), 1)
    _rect(s, (30, 30, 34), 620, 560, 40, 14)
    # panels
    for x in (318, 862):
        _rect(s, (24, 24, 30), x, 252, 100, 196, 10)
        pygame.draw.rect(s, (90, 90, 100), (x, 252, 100, 196), 3, border_radius=10)
    text(s, "A", 24, GREY, (368, 350), "midtop", shadow=False)
    text(s, "Q", 24, GREY, (368, 438), "midtop", shadow=False)
    text(s, "D", 24, GREY, (912, 350), "midtop", shadow=False)
    text(s, "E", 24, GREY, (912, 438), "midtop", shadow=False)
    # cup & papers
    _rect(s, (190, 190, 200), 430, 520, 26, 30, 4)
    _rect(s, (220, 220, 210), 800, 528, 70, 12, 2)
    _office_cache.append(s)
    return s


def _draw_doorway(s, n, side, rect, slide, flicker):
    lit = n.lights[side] and not flicker
    if lit:
        _vgrad(s, rect, (150, 136, 90), (96, 86, 56))
        _rect(s, (38, 34, 26), rect.centerx - 50, rect.top + 130, 100, 150)
        _poly(s, (84, 74, 48), [(rect.left, rect.bottom), (rect.right, rect.bottom),
                                (rect.centerx + 50, rect.top + 280), (rect.centerx - 50, rect.top + 280)])
        who = n.at_door(side)
        if who:
            s.set_clip(rect)
            CHARACTERS[who](s, rect.centerx, rect.top + 175, 0.8, hostile=True)
            s.set_clip(None)
    else:
        _vgrad(s, rect, (14, 14, 20), (4, 4, 8))
    h = _i(rect.h * slide)
    if h > 0:
        pygame.draw.rect(s, (78, 82, 92), (rect.x, rect.y, rect.w, h))
        for y in range(rect.y + 10, rect.y + h, 26):
            _line(s, (56, 60, 68), (rect.x, y), (rect.right - 1, y), 3)
        pygame.draw.rect(s, (30, 32, 38), (rect.x, rect.y + h - 8, rect.w, 8))
    pygame.draw.rect(s, (20, 20, 26), rect, 12)


def _draw_fan(s, t):
    cx, cy = 840, 500
    ang = t * 7
    _rect(s, (50, 50, 58), cx - 6, cy, 12, 44)
    for k in range(3):
        a = ang + k * 2 * math.pi / 3
        _line(s, (150, 152, 162), (cx, cy), (cx + math.cos(a) * 44, cy + math.sin(a) * 44), 14)
    pygame.draw.circle(s, (90, 92, 100), (cx, cy), 9)


def _draw_office_buttons(s, n):
    for side in ("west", "east"):
        closed = n.doors[side]
        r = OFFICE_BUTTONS["door_" + side]
        pygame.draw.rect(s, (200, 50, 50) if closed else (50, 160, 70), r, border_radius=10)
        pygame.draw.rect(s, (20, 20, 20), r, 3, border_radius=10)
        text(s, "DOOR", 24, WHITE, r.center, "center")
        on = n.lights[side]
        r = OFFICE_BUTTONS["light_" + side]
        pygame.draw.rect(s, (240, 210, 70) if on else (90, 80, 40), r, border_radius=10)
        pygame.draw.rect(s, (20, 20, 20), r, 3, border_radius=10)
        text(s, "LIGHT", 24, (30, 24, 4) if on else WHITE, r.center, "center", shadow=not on)


def draw_office(s, n, t, slide, flicker):
    s.blit(_office_bg(), (0, 0))
    _draw_doorway(s, n, "west", DL, slide["west"], flicker)
    _draw_doorway(s, n, "east", DR, slide["east"], flicker)
    _draw_fan(s, t)
    _draw_office_buttons(s, n)
    _draw_cam_bar(s, n)
    if n.blackout:
        _draw_blackout(s, n, t)
    else:
        _darken(s, 40 + (20 if int(t * 9) % 7 == 0 else 0))
    _static(s, t, 14)
    s.blit(_vig, (0, 0))
    draw_hud(s, n, t)


def _draw_blackout(s, n, t):
    flick = int(t * 12) % 5 in (0, 1)
    if n.jingle_started and flick:
        draw_moose(s, 640, 330, 1.5, hostile=True)
        _darken(s, 175)
        for sg in (-1, 1):
            _ell(s, (255, 255, 230), 640 + sg * 57, 303, 22, 22)
    else:
        _darken(s, 246)
    text(s, "POWER OUT", 40, (120, 20, 20), (640, 90), "center", shadow=False)


def draw_hud(s, n, t):
    pct = n.power_percent
    col = GREEN if pct > 50 else (YELLOW if pct > 20 else RED)
    text(s, f"Power left: {pct}%", 34, col, (24, 640))
    text(s, "Usage:", 30, WHITE, (24, 676))
    cols = [GREEN, YELLOW, ORANGE, RED]
    for k in range(4):
        r = pygame.Rect(110 + k * 22, 678, 18, 26)
        if k < n.usage:
            pygame.draw.rect(s, cols[k], r)
        else:
            pygame.draw.rect(s, (50, 50, 56), r, 2)
    text(s, n.clock_label, 64, WHITE, (W - 30, 18), "topright")
    text(s, f"Night {n.night}", 30, GREY, (W - 30, 80), "topright")


def draw_subtitle(s, msg):
    if not msg:
        return
    f = font(30)
    words = msg.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if f.size(trial)[0] > 900 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    h = len(lines) * 32 + 16
    box = pygame.Surface((940, h))
    box.fill((0, 0, 0))
    box.set_alpha(150)
    y0 = 600 - h
    s.blit(box, (170, y0))
    for i, ln in enumerate(lines):
        text(s, ln, 30, (235, 235, 210), (640, y0 + 8 + i * 32), "midtop")


def office_button_at(pos):
    for name, r in OFFICE_BUTTONS.items():
        if r.collidepoint(pos):
            return name
    return None


def cam_button_at(pos):
    for cam, r in CAM_BUTTONS.items():
        if r.collidepoint(pos):
            return cam
    return None


# ---------------------------------------------------------------- screens
_EYES = [(random.Random(i).randint(80, W - 80), random.Random(i + 99).randint(60, H - 60),
          random.Random(i + 5).uniform(0, 6.28), random.Random(i + 9).uniform(0.5, 1.4))
         for i in range(14)]


def draw_title(s, t, index, items):
    s.fill((4, 4, 8))
    for x, y, ph, sp in _EYES:
        v = math.sin(t * sp + ph)
        if v > 0.82:
            for sg in (-1, 1):
                _ell(s, (255, 240, 200), x + sg * 16, y, 14, 9)
    _static(s, t, 18)
    jitter = 2 if int(t * 10) % 13 == 0 else 0
    text(s, "FIVE NIGHTS AT", 110, (200, 30, 36), (640 + jitter, 140), "center")
    text(s, "MEXICAN SUPERHERO'S HOUSE", 66, WHITE, (640, 232), "center")
    text(s, "an unofficial fan game  -  all characters are original", 26, GREY, (640, 290), "center")
    rects = []
    for i, label in enumerate(items):
        sel = i == index
        r = text(s, ("> " if sel else "  ") + label, 56, YELLOW if sel else (170, 170, 175),
                 (640, 400 + i * 70), "center")
        rects.append(r.inflate(60, 16))
    text(s, "Arrows / Enter  or  mouse", 24, (90, 90, 100), (640, 690), "center", shadow=False)
    s.blit(_scan, (0, 0))
    s.blit(_vig, (0, 0))
    return rects


def draw_night_card(s, night, t):
    s.fill((0, 0, 0))
    a = min(1.0, t / 0.8) if t < 2.4 else max(0.0, (3.2 - t) / 0.8)
    col = tuple(_i(255 * a * k) for k in (1, 1, 1))
    text(s, f"Night {night}", 70, col, (640, 280), "center", shadow=False)
    text(s, "12:00 AM", 130, col, (640, 380), "center", shadow=False)
    _static(s, t, 10)


def draw_jumpscare(s, who, t):
    s.fill((0, 0, 0) if int(t * 30) % 2 else (60, 0, 0))
    dx, dy = random.randint(-16, 16), random.randint(-16, 16)
    sc = 2.3 + min(t, 0.25) * 6
    cy = {"moose": 420, "penny": 330, "gus": 300}.get(who, 340)
    CHARACTERS[who](s, 640 + dx, cy + dy, sc, hostile=True, scream=True)
    _static(s, t, 70)
    s.blit(_scan, (0, 0))


def draw_game_over(s, t):
    s.fill((0, 0, 0))
    _static(s, t, 90)
    text(s, "GAME OVER", 140, RED, (640, 270), "center")
    text(s, "ENTER - try this night again", 40, WHITE, (640, 420), "center")
    text(s, "ESC - title screen", 34, GREY, (640, 470), "center")


def draw_win(s, t, night):
    s.fill((0, 0, 0))
    p = min(1.0, t / 3.0)
    p = p * p * (3 - 2 * p)
    text(s, "5 AM", 160, WHITE, (640, 360 - p * 520), "center", shadow=False)
    text(s, "6 AM", 160, (255, 235, 150), (640, 360 + (1 - p) * 520), "center", shadow=False)
    if t > 3.6:
        text(s, f"You survived Night {night}!", 60, GREEN, (640, 500), "center")
    if t > 6.0:
        text(s, "Press ENTER to continue", 34, GREY, (640, 580), "center")


_CONFETTI = [(random.Random(i).randint(0, W), random.Random(i + 40).randint(0, H),
              random.Random(i + 80).choice([RED, GREEN, YELLOW, (80, 150, 230), (230, 90, 180)]),
              random.Random(i + 120).uniform(40, 120)) for i in range(70)]


def draw_ending(s, t):
    s.fill((8, 8, 16))
    for x, y, col, sp in _CONFETTI:
        yy = (y + t * sp) % H
        _rect(s, col, x, yy, 10, 14)
    text(s, "YOU SURVIVED ALL 5 NIGHTS", 84, YELLOW, (640, 230), "center")
    text(s, "Thanks for playing!", 56, WHITE, (640, 320), "center")
    text(s, "Five Nights at Mexican Superhero's House  -  an unofficial fan game", 30, GREY, (640, 420), "center")
    text(s, "All characters are original. Not affiliated with any publisher or studio.", 26, GREY, (640, 456), "center")
    text(s, "ENTER - back to title", 34, WHITE, (640, 580), "center")


def draw_pause(s):
    _darken(s, 190)
    text(s, "PAUSED", 120, WHITE, (640, 290), "center")
    text(s, "ESC - resume", 40, GREY, (640, 400), "center")
    text(s, "T - quit to title", 40, GREY, (640, 450), "center")


def make_icon():
    big = pygame.Surface((128, 128), pygame.SRCALPHA)
    draw_moose(big, 64, 74, 0.42, hostile=True)
    return pygame.transform.smoothscale(big, (32, 32))
