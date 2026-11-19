"""Procedurally generated sound effects (no audio files needed)."""
from __future__ import annotations

import math
import random
from array import array

import pygame

RATE = 22050
TAU = 2 * math.pi


def _tone(freq, dur, vol=0.5, decay=4.0, harmonics=(1.0,), f_end=None):
    n = int(RATE * dur)
    norm = sum(harmonics)
    out = []
    phase = 0.0
    for i in range(n):
        f = freq if f_end is None else freq + (f_end - freq) * (i / n)
        phase += TAU * f / RATE
        v = 0.0
        for k, h in enumerate(harmonics, 1):
            v += h * math.sin(phase * k)
        out.append(v / norm * vol * math.exp(-decay * i / RATE))
    return out


def _noise(dur, vol=0.5, decay=4.0):
    n = int(RATE * dur)
    rnd = random.random
    return [(rnd() * 2 - 1) * vol * math.exp(-decay * i / RATE) for i in range(n)]


def _mix(*tracks):
    length = max(len(t) for t in tracks)
    out = [0.0] * length
    for t in tracks:
        for i, v in enumerate(t):
            out[i] += v
    return out


def _place(parts, total_dur):
    """parts: [(offset_seconds, samples)] -> one track of total_dur seconds."""
    out = [0.0] * int(RATE * total_dur)
    for offset, samples in parts:
        start = int(RATE * offset)
        for i, v in enumerate(samples):
            j = start + i
            if j < len(out):
                out[j] += v
    return out


def _to_sound(samples, volume=1.0):
    buf = array("h", (max(-32767, min(32767, int(s * 32767))) for s in samples))
    snd = pygame.mixer.Sound(buffer=buf.tobytes())
    snd.set_volume(volume)
    return snd


def _loop_wave(dur, parts):
    n = int(RATE * dur)
    out = []
    for i in range(n):
        t = i / RATE
        out.append(sum(a * math.sin(TAU * f * t) for f, a in parts))
    return out


class Audio:
    def __init__(self):
        self.ok = False
        self.sounds = {}
        self.loops = {}
        try:
            try:
                pygame.mixer.init(RATE, -16, 1, 512, allowedchanges=0)
            except TypeError:
                pygame.mixer.init(RATE, -16, 1, 512)
            pygame.mixer.set_num_channels(16)
            self._build()
            self.ok = True
        except Exception as exc:  # no audio device etc. - the game still runs
            print("Audio disabled:", exc)

    # ------------------------------------------------------------ building
    def _build(self):
        s = self.sounds
        s["hum"] = _to_sound(_loop_wave(2.0, [(55, 0.10), (110, 0.05), (165, 0.03)]), 0.6)
        s["buzz"] = _to_sound(_loop_wave(0.5, [(100, 0.18), (300, 0.08)]), 0.5)
        s["door"] = _to_sound(_mix(_noise(0.15, 0.5, 22),
                                   _tone(70, 0.45, 0.9, 8)), 0.9)
        s["cam_up"] = _to_sound(_tone(500, 0.14, 0.4, 10, f_end=1100), 0.6)
        s["cam_down"] = _to_sound(_tone(1100, 0.14, 0.4, 10, f_end=500), 0.6)
        s["switch"] = _to_sound(_tone(700, 0.06, 0.4, 20), 0.5)
        s["step"] = _to_sound(_mix(_tone(60, 0.3, 0.8, 10), _noise(0.04, 0.3, 40)), 0.45)
        thump = _tone(90, 0.2, 0.9, 14)
        s["knock"] = _to_sound(_place([(0, thump), (0.22, thump), (0.44, thump)], 0.7), 0.9)
        offs = [0, 0.3, 0.55, 0.75, 0.9, 1.02, 1.12, 1.2, 1.27]
        s["run"] = _to_sound(_place([(o, _tone(70, 0.15, 0.8, 12)) for o in offs], 1.5), 0.8)
        s["power_down"] = _to_sound(_tone(420, 1.0, 0.7, 2.5, harmonics=(1, 0.4), f_end=35), 0.9)
        s["scare"] = _to_sound(_mix(_noise(1.2, 0.8, 1.4),
                                    _tone(180, 1.2, 0.8, 0.9, harmonics=(1, 0.6, 0.4), f_end=1500)), 1.0)
        # an original little music-box tune for the blackout
        notes = [392.0, 311.1, 392.0, 466.2, 392.0, 311.1, 293.7, 311.1,
                 261.6, 293.7, 311.1, 261.6]
        box = [(i * 0.36, _tone(f, 0.9, 0.7, 3.2, harmonics=(1, 0.3, 0.1)))
               for i, f in enumerate(notes)]
        s["jingle"] = _to_sound(_place(box, len(notes) * 0.36 + 0.6), 0.7)
        bell = lambda: _tone(880, 1.4, 0.7, 2.2, harmonics=(1, 0.5, 0.25, 0.12))
        s["chime"] = _to_sound(_place([(0, bell()), (1.0, bell()), (2.0, bell())], 3.6), 0.9)
        ring = _mix(_tone(440, 0.4, 0.4, 0.0), _tone(480, 0.4, 0.4, 0.0))
        s["ring"] = _to_sound(_place([(0, ring), (0.55, ring)], 1.0), 0.4)

    # ------------------------------------------------------------ playing
    def play(self, name, volume=None):
        snd = self.sounds.get(name)
        if snd is None:
            return
        if volume is not None:
            snd.set_volume(volume)
        snd.play()

    def loop(self, name):
        snd = self.sounds.get(name)
        if snd is None or name in self.loops:
            return
        self.loops[name] = snd.play(loops=-1)

    def stop_loop(self, name):
        ch = self.loops.pop(name, None)
        if ch is not None:
            ch.stop()

    def stop_all(self):
        self.loops.clear()
        if self.ok:
            pygame.mixer.stop()
