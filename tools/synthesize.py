#!/usr/bin/env python3
"""Synthesize original instrumental tracks inspired by BULLY-era aesthetics.

All audio is generated from scratch (sine/saw/triangle oscillators, noise
drums, FM keys, simple envelopes). No samples of any commercial recording
are used. Tracks are named after the moods of the BULLY tracklist.
"""
import math
import os
import struct
import wave
import random

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SND = os.path.join(ROOT, "assets", "bully_discs", "sounds")
os.makedirs(SND, exist_ok=True)

PI2 = math.pi * 2.0

# note frequency helper: midi -> Hz
def nf(m):
    return 440.0 * (2.0 ** ((m - 69) / 12.0))

def clamp(x, lo=-1.0, hi=1.0):
    return lo if x < lo else (hi if x > hi else x)

class Buf:
    def __init__(self, dur):
        self.n = int(dur * SR)
        self.d = [0.0] * self.n

    def __len__(self):
        return self.n

    def add(self, i, v):
        if 0 <= i < self.n:
            self.d[i] += v

    def normalize(self, peak=0.92):
        m = max((abs(x) for x in self.d), default=0.0)
        if m > 1e-9:
            k = peak / m
            self.d = [x * k for x in self.d]

    def write_wav(self, path):
        self.normalize()
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            frames = bytearray()
            for x in self.d:
                xi = int(clamp(x) * 32767.0)
                frames += struct.pack("<h", xi)
            w.writeframes(bytes(frames))

def env_ar(i, n, a, r):
    """attack/release envelope over [0,n) in samples."""
    if i < a and a > 0:
        return i / a
    if i >= n - r and r > 0:
        return max(0.0, (n - i) / r)
    return 1.0

def sine(p):
    return math.sin(PI2 * p)

def saw(p):
    p = p % 1.0
    return 2.0 * p - 1.0

def tri(p):
    p = p % 1.0
    if p < 0.5:
        return 4.0 * p - 1.0
    return 3.0 - 4.0 * p

def square(p, duty=0.5):
    p = p % 1.0
    return 1.0 if p < duty else -1.0

# simple 1-pole lowpass filter state helper (per-voice)
def lp_step(x, y_prev, cutoff):
    a = 1.0 - math.exp(-PI2 * cutoff / SR)
    return y_prev + a * (x - y_prev)

def render_note(buf, start, dur, freq, vol, wave_fn, a=0.004, r=0.05,
                detune=0.0, fm_depth=0.0, fm_ratio=1.0, lp=None):
    n = int(dur * SR)
    ph = 0.0
    ph2 = 0.0
    y = 0.0
    inc = freq / SR
    inc2 = freq * fm_ratio / SR
    for i in range(n):
        e = env_ar(i, n, a * SR, r * SR)
        mod = sine(ph2) * fm_depth
        v = wave_fn(ph + mod + detune * (i / SR))
        if lp:
            y = lp_step(v, y, lp)
            v = y
        buf.add(start + i, v * vol * e)
        ph += inc
        ph2 += inc2
    return

def kick(buf, start, vol=0.9, dur=0.30):
    n = int(dur * SR)
    ph = 0.0
    for i in range(n):
        t = i / SR
        f = 42.0 + 110.0 * math.exp(-t * 26.0)
        ph += f / SR
        e = math.exp(-t * 9.0)
        click = (random.random() * 2 - 1) * 0.4 * math.exp(-t * 900.0)
        buf.add(start + i, (sine(ph) * 0.95 + click) * vol * e)

def snare(buf, start, vol=0.55, dur=0.18):
    n = int(dur * SR)
    ph = 0.0
    for i in range(n):
        t = i / SR
        noise = (random.random() * 2 - 1)
        tone = sine(ph) * 0.5
        ph += (190.0 / SR)
        e = math.exp(-t * 34.0)
        buf.add(start + i, (noise * 0.8 + tone) * vol * e)

def hat(buf, start, vol=0.22, dur=0.06, hp=True):
    n = int(dur * SR)
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = (random.random() * 2 - 1)
        if hp:  # crude highpass: difference
            v = noise - prev
            prev = noise
            noise = v * 1.2
        e = math.exp(-t * 90.0)
        buf.add(start + i, noise * vol * e)

def crash(buf, start, vol=0.4, dur=2.2):
    n = int(dur * SR)
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = (random.random() * 2 - 1)
        v = noise - prev
        prev = noise
        e = math.exp(-t * 2.2)
        buf.add(start + i, v * 0.7 * vol * e)

def vinyl(buf, vol=0.012, seed=7):
    rng = random.Random(seed)
    for i in range(len(buf)):
        buf.d[i] += (rng.random() * 2 - 1) * vol
    # sparse crackle
    for _ in range(int(len(buf) / SR * 3)):
        p = rng.randrange(len(buf))
        ln = int(0.003 * SR)
        for j in range(ln):
            buf.add(p + j, (rng.random() * 2 - 1) * 0.05 * math.exp(-j / (0.001 * SR)))

def fade_out(buf, seconds):
    n = int(seconds * SR)
    for i in range(n):
        idx = len(buf) - n + i
        if 0 <= idx < len(buf):
            buf.d[idx] *= 1.0 - i / n

def fade_in(buf, seconds):
    n = int(seconds * SR)
    for i in range(min(n, len(buf))):
        buf.d[i] *= i / n

# ---------------------------------------------------------------------------
# track generators — each returns a finished Buf
# ---------------------------------------------------------------------------

def make_sample_chord_progression(dur, prog, bpm, pad_vol, keys_vol, wave_pad=sine, lp_pad=1200.0):
    buf = Buf(dur)
    beat = 60.0 / bpm
    bar = beat * 4
    # pitched-up "soul sample" pad: detuned saws behind a lowpass, vinyl
    for bi, chords in enumerate(prog):
        t0 = bi * bar
        if t0 >= dur:
            break
        for note, vel, hold in chords:
            render_note(buf, int(t0 * SR), min(hold, dur - t0), nf(note), pad_vol * vel,
                        saw, a=0.03, r=0.4, detune=0.0015, lp=lp_pad)
            # ghost octave shimmer
            render_note(buf, int(t0 * SR), min(hold, dur - t0) * 0.7, nf(note + 12) * 1.003, pad_vol * vel * 0.35,
                        sine, a=0.05, r=0.5)
    vinyl(buf, seed=11)
    return buf

def track_king():
    """Grief-laden soul loop under heavy sub — 'more love from hate' mood."""
    dur = 96
    buf = make_sample_chord_progression(
        dur,
        prog=[  # (midi, vel, hold_seconds) — minor soul changes
            [(57, 0.9, 3.4), (60, 0.7, 3.4), (64, 0.6, 3.4), (69, 0.35, 1.6)],   # Am add9-ish
            [(53, 0.9, 3.4), (57, 0.7, 3.4), (60, 0.6, 3.4), (65, 0.35, 1.6)],   # F
            [(55, 0.9, 3.4), (59, 0.7, 3.4), (62, 0.6, 3.4), (67, 0.35, 1.6)],   # G
            [(52, 0.9, 3.4), (55, 0.7, 3.4), (59, 0.6, 3.4), (64, 0.35, 1.6)],   # E
        ] * 8,
        bpm=84,
        pad_vol=0.30,
        keys_vol=0.0,
    )
    bpm = 84
    beat = 60.0 / bpm
    # heavy 808-style sub bass, gospel weight
    bassline = [33, 33, 40, 33, 29, 29, 36, 31]  # A A E A F F C B
    for bi in range(int(dur / (beat * 4)) + 1):
        t0 = bi * beat * 4
        for k, b in enumerate(bassline):
            st = t0 + k * beat
            if st + 0.1 < dur:
                render_note(buf, int(st * SR), min(beat * 1.8, dur - st), nf(b) / 2.0, 0.5,
                            sine, a=0.01, r=0.30)
    # sparse drums — half-time, funeral pace
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.85)
            snare(buf, int((t0 + beat) * SR), vol=0.4)
    for bi in range(int(dur / (beat * 0.5)) + 1):
        t0 = bi * beat * 0.5
        if t0 < dur - 0.1:
            hat(buf, int(t0 * SR), vol=0.10, dur=0.04)
    fade_in(buf, 1.2)
    fade_out(buf, 3.0)
    return buf

def track_this_a_must():
    """Rage/industrial: distorted square riff, brutal kicks, alarms."""
    dur = 84
    buf = Buf(dur)
    bpm = 146
    beat = 60.0 / bpm
    # industrial riff — minor tritone stab pattern (E, Bb)
    riff = [40, 40, 46, 40, 43, 46, 40, 47]
    for rep in range(int(dur / (beat * 2)) + 1):
        for k, note in enumerate(riff):
            st = (rep * 2 + k * 0.25) * beat
            if st < dur - 0.2:
                render_note(buf, int(st * SR), 0.22, nf(note) / 2.0, 0.34, square,
                            a=0.002, r=0.06, lp=2400.0)
                render_note(buf, int(st * SR), 0.22, nf(note) / 2.0 * 1.005, 0.30, saw,
                            a=0.002, r=0.06, lp=3000.0)
    # alarm siren layer in background
    for rep in range(int(dur / (beat * 8)) + 1):
        st = rep * beat * 8
        if st + 4 < dur:
            n = int(4.0 * SR)
            for i in range(n):
                f = 660 + 180 * sine(i / SR * 0.5)
                buf.add(int(st * SR) + i, sine(i * f / SR) * 0.05 * (0.5 + 0.5 * sine(i / SR * 2)))
    # hard trap-ish double kicks
    for bi in range(int(dur / (beat / 2)) + 1):
        t0 = bi * beat / 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.95, dur=0.22)
        if bi % 4 == 2 and t0 < dur - 0.3:
            snare(buf, int(t0 * SR), vol=0.5)
    for bi in range(int(dur / (beat / 2)) + 1):
        t0 = bi * beat / 2 + beat / 4
        if t0 < dur - 0.1:
            hat(buf, int(t0 * SR), vol=0.14, dur=0.03)
    fade_in(buf, 0.8)
    fade_out(buf, 2.0)
    return buf

def track_father():
    """Church organ + gospel chords + heavy synth bass momentum."""
    dur = 108
    buf = Buf(dur)
    bpm = 76
    beat = 60.0 / bpm
    bar = beat * 4
    # organ: stacked fifths/octaves, slow sweep
    prog = [
        [(53, 1.0), (60, 0.8), (65, 0.6), (69, 0.5)],  # F
        [(55, 1.0), (62, 0.8), (67, 0.6), (71, 0.5)],  # G
        [(48, 1.0), (60, 0.8), (64, 0.6), (67, 0.5)],  # C
        [(53, 1.0), (60, 0.8), (65, 0.6), (69, 0.5)],  # F
    ] * 9
    for bi, chord in enumerate(prog):
        t0 = bi * bar
        if t0 >= dur:
            break
        for (note, vel) in chord:
            render_note(buf, int(t0 * SR), min(bar, dur - t0), nf(note), 0.16 * vel,
                        sine, a=0.25, r=0.8)
            render_note(buf, int(t0 * SR), min(bar, dur - t0), nf(note) * 0.5, 0.12 * vel,
                        tri, a=0.30, r=0.8)
            # organ chiff
            render_note(buf, int(t0 * SR), 0.30, nf(note + 12), 0.06 * vel, sine, a=0.02, r=0.2)
    # heavy synth bass on roots
    roots = [29, 31, 24, 29]
    for bi in range(int(dur / bar) + 1):
        t0 = bi * bar
        root = roots[bi % 4]
        for k in range(8):
            st = t0 + k * beat * 0.5
            if st < dur - 0.2:
                render_note(buf, int(st * SR), beat * 0.45, nf(root) / 2.0, 0.55, sine, a=0.008, r=0.12)
                render_note(buf, int(st * SR), beat * 0.45, nf(root) / 2.0 * 1.007, 0.35, saw, a=0.008, r=0.12, lp=380.0)
    kick(buf, 0, vol=0.0)  # no-op warm
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        if t0 < dur - 0.5:
            kick(buf, int(t0 * SR), vol=0.8)
        if t0 + beat < dur - 0.3 and bi % 2 == 1:
            snare(buf, int((t0 + beat) * SR), vol=0.34)
    crash(buf, 0, vol=0.35)
    crash(buf, int(bar * 4 * SR), vol=0.3)
    fade_in(buf, 2.0)
    fade_out(buf, 4.0)
    return buf

def track_all_the_love():
    """Synth-ballad with talkbox-like formant wobble lead."""
    dur = 100
    buf = make_sample_chord_progression(
        dur,
        prog=[
            [(52, 0.9, 3.2), (55, 0.7, 3.2), (59, 0.6, 3.2), (64, 0.3, 1.5)],
            [(50, 0.9, 3.2), (53, 0.7, 3.2), (57, 0.6, 3.2), (62, 0.3, 1.5)],
            [(55, 0.9, 3.2), (58, 0.7, 3.2), (62, 0.6, 3.2), (66, 0.3, 1.5)],
            [(48, 0.9, 3.2), (52, 0.7, 3.2), (55, 0.6, 3.2), (60, 0.3, 1.5)],
        ] * 9,
        bpm=80, pad_vol=0.22, keys_vol=0.0,
    )
    bpm = 80
    beat = 60.0 / bpm
    # talkbox-ish lead: triangle with vibrato + formant-ish AM
    lead_notes = [76, 74, 71, 69, 71, 74, 76, 79, 76, 74, 71, 67, 69, 71, 74, 76]
    for rep in range(3):
        t0 = 8 + rep * 32
        for k, m in enumerate(lead_notes):
            st = t0 + k * beat
            if st < dur - 0.5:
                n = int(beat * 1.2 * SR)
                f = nf(m)
                for i in range(n):
                    e = env_ar(i, n, 0.02 * SR, 0.3 * SR)
                    vib = 0.004 * sine(i / SR * 5.5)
                    formant = 0.6 + 0.4 * sine(i / SR * 3.0)  # vowel wobble
                    v = tri((i * (f * (1 + vib)) / SR) * 1.0) * formant
                    buf.add(int(st * SR) + i, v * 0.20 * e)
    bpm2 = bpm
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.7)
            snare(buf, int((t0 + beat) * SR), vol=0.30)
    for bi in range(int(dur / beat) + 1):
        hat(buf, int(bi * beat * SR), vol=0.08, dur=0.03)
    fade_in(buf, 1.5)
    fade_out(buf, 3.0)
    return buf

def track_punch_drunk():
    """Gospel-chops: stuttered chord stabs, swung hats, sub thumps."""
    dur = 88
    buf = Buf(dur)
    bpm = 138
    beat = 60.0 / bpm
    chords = [
        [(49, 0.9), (52, 0.7), (56, 0.6), (61, 0.4)],  # C#m-ish
        [(54, 0.9), (57, 0.7), (61, 0.6), (66, 0.4)],
        [(47, 0.9), (50, 0.7), (54, 0.6), (59, 0.4)],
        [(49, 0.9), (52, 0.7), (56, 0.6), (63, 0.4)],
    ]
    # chopped stabs with swing
    for bi in range(int(dur / (beat * 2)) + 1):
        chord = chords[bi % 4]
        t0 = bi * beat * 2
        if t0 >= dur:
            break
        for (note, vel) in chord:
            # main stab
            render_note(buf, int(t0 * SR), 0.16, nf(note) * 2, 0.22 * vel, saw, a=0.003, r=0.10, lp=1800.0)
            # echo
            render_note(buf, int((t0 + beat * 0.75) * SR), 0.12, nf(note) * 2 * 0.998, 0.10 * vel, saw, a=0.003, r=0.10, lp=1500.0)
        # sub
        root = chord[0][0] - 24
        render_note(buf, int(t0 * SR), beat * 0.9, nf(root), 0.5, sine, a=0.01, r=0.2)
    # swung hats
    sw = 0.08
    for bi in range(int(dur / (beat / 2)) + 1):
        t0 = bi * beat / 2
        if bi % 2 == 1:
            t0 += beat * sw
        if t0 < dur - 0.1:
            hat(buf, int(t0 * SR), vol=0.12, dur=0.035)
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.85)
            snare(buf, int((t0 + beat) * SR), vol=0.42)
    vinyl(buf, vol=0.010, seed=31)
    fade_in(buf, 0.6)
    fade_out(buf, 2.0)
    return buf

def track_whatever_works():
    """Dusty soul loop; laid-back, Cissy-style warmth."""
    dur = 92
    buf = make_sample_chord_progression(
        dur,
        prog=[
            [(50, 0.9, 3.6), (53, 0.7, 3.6), (57, 0.6, 3.6), (62, 0.35, 1.8)],
            [(52, 0.9, 3.6), (55, 0.7, 3.6), (59, 0.6, 3.6), (64, 0.35, 1.8)],
            [(48, 0.9, 3.6), (52, 0.7, 3.6), (55, 0.6, 3.6), (59, 0.35, 1.8)],
            [(50, 0.9, 3.6), (53, 0.7, 3.6), (57, 0.6, 3.6), (60, 0.35, 1.8)],
        ] * 8,
        bpm=78, pad_vol=0.32, keys_vol=0.0, lp_pad=900.0,
    )
    bpm = 78
    beat = 60.0 / bpm
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.65)
            snare(buf, int((t0 + beat) * SR), vol=0.35)
            hat(buf, int((t0 + beat * 1.5) * SR), vol=0.08)
    fade_in(buf, 1.0)
    fade_out(buf, 3.0)
    return buf

def track_mamas_favorite():
    """Vulnerable keys ballad — music-box piano, sparse sub, no drums at first."""
    dur = 102
    buf = Buf(dur)
    bpm = 70
    beat = 60.0 / bpm
    # music-box piano: FM bell-ish (sine carrier + 2x modulator)
    melody = [
        (64, 0), (67, 1), (71, 2), (69, 3), (67, 4), (64, 5), (62, 6), (60, 7),
        (64, 8), (67, 9), (72, 10), (71, 11), (69, 12), (67, 13), (64, 14), (62, 15),
    ]
    for rep in range(3):
        t0 = 4 + rep * 33
        for (m, k) in melody:
            st = t0 + k * beat
            if st < dur - 0.5:
                render_note(buf, int(st * SR), beat * 1.5, nf(m), 0.20, sine,
                            a=0.002, r=0.6, fm_depth=0.35, fm_ratio=2.01)
                render_note(buf, int(st * SR), beat * 1.5, nf(m + 12), 0.07, sine,
                            a=0.002, r=0.9, fm_depth=0.3, fm_ratio=3.0)
    # warm pad under
    prog = [
        [(52, 0.8), (59, 0.5), (64, 0.4)],
        [(50, 0.8), (57, 0.5), (62, 0.4)],
        [(48, 0.8), (55, 0.5), (60, 0.4)],
        [(53, 0.8), (60, 0.5), (65, 0.4)],
    ] * 9
    bar = beat * 4
    for bi, chord in enumerate(prog):
        t0 = bi * bar
        if t0 >= dur:
            break
        for (note, vel) in chord:
            render_note(buf, int(t0 * SR), min(bar * 1.1, dur - t0), nf(note), 0.10 * vel, sine, a=0.4, r=1.0)
    # heartbeat sub, enters late
    for bi in range(int((dur - 40) / beat) + 1):
        t0 = 40 + bi * beat * 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.45, dur=0.25)
    fade_in(buf, 2.5)
    fade_out(buf, 5.0)
    return buf

def track_sisters_and_brothers():
    """Warm soul-funk; clav stabs, walking sub, live-ish hats."""
    dur = 96
    buf = Buf(dur)
    bpm = 96
    beat = 60.0 / bpm
    # clav (square with fast decay)
    riff = [52, 52, 59, 56, 52, 64, 59, 56, 52, 52, 59, 56, 57, 56, 52, 47]
    for rep in range(int(dur / (beat * 4)) + 1):
        for k, m in enumerate(riff):
            st = rep * beat * 4 + k * beat * 0.5
            if st < dur - 0.2:
                render_note(buf, int(st * SR), 0.14, nf(m), 0.20, square, a=0.002, r=0.07, lp=2600.0)
                render_note(buf, int(st * SR), 0.14, nf(m + 12), 0.06, square, a=0.002, r=0.06, lp=3200.0)
    # walking sub
    bass = [28, 28, 35, 33, 31, 31, 38, 36, 28, 28, 35, 33, 31, 33, 35, 38]
    for rep in range(int(dur / (beat * 4)) + 1):
        for k, b in enumerate(bass):
            st = rep * beat * 4 + k * beat * 0.5
            if st < dur - 0.2:
                render_note(buf, int(st * SR), beat * 0.42, nf(b), 0.5, sine, a=0.006, r=0.10)
                render_note(buf, int(st * SR), beat * 0.42, nf(b) * 2.0 * 1.002, 0.10, tri, a=0.006, r=0.10, lp=500)
    for bi in range(int(dur / (beat * 0.5)) + 1):
        t0 = bi * beat * 0.5
        if t0 < dur - 0.1:
            hat(buf, int(t0 * SR), vol=0.10 if bi % 2 else 0.16, dur=0.03)
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.75)
            snare(buf, int((t0 + beat) * SR), vol=0.40)
    fade_in(buf, 0.8)
    fade_out(buf, 2.5)
    return buf

def track_bully():
    """Title cut: toy-mallet music-box over swelling industrial; Saint's theme."""
    dur = 104
    buf = Buf(dur)
    bpm = 88
    beat = 60.0 / bpm
    # music-box mallet motif (bright FM bells)
    motif = [(76, 0), (79, 0.5), (83, 1), (81, 1.5), (79, 2), (76, 2.5), (74, 3), (76, 3.5)]
    for rep in range(int(dur / (beat * 4)) + 1):
        t0 = rep * beat * 4
        for (m, k) in motif:
            st = t0 + k * beat
            if st < dur - 0.3:
                render_note(buf, int(st * SR), beat * 1.2, nf(m), 0.16, sine, a=0.001, r=0.4, fm_depth=0.5, fm_ratio=2.0)
                render_note(buf, int(st * SR), beat * 0.8, nf(m + 12), 0.05, sine, a=0.001, r=0.3, fm_depth=0.4, fm_ratio=3.5)
    # industrial bed grows
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        inten = min(1.0, t0 / (dur * 0.6))
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.5 + 0.4 * inten)
            snare(buf, int((t0 + beat) * SR), vol=(0.2 + 0.3 * inten))
    # dark drone
    n = int(dur * SR)
    for i in range(n):
        t = i / SR
        d = (sine(i * nf(28) / SR) + 0.5 * sine(i * nf(28) * 1.008 / SR)) * 0.10
        swell = 0.4 + 0.6 * min(1.0, t / 30.0)
        buf.d[i] += d * swell
    fade_in(buf, 2.0)
    fade_out(buf, 4.0)
    return buf

def track_highs_and_lows():
    """Emotional two-chord swell; sub-bass heartbeat, yearning lead."""
    dur = 98
    buf = make_sample_chord_progression(
        dur,
        prog=[
            [(57, 0.9, 3.8), (60, 0.7, 3.8), (64, 0.6, 3.8)],
            [(53, 0.9, 3.8), (57, 0.7, 3.8), (60, 0.6, 3.8)],
        ] * 13,
        bpm=74, pad_vol=0.30, keys_vol=0.0, lp_pad=800.0,
    )
    bpm = 74
    beat = 60.0 / bpm
    lead = [69, 72, 76, 74, 72, 69, 67, 69, 71, 69, 67, 64]
    for rep in range(2):
        t0 = 10 + rep * 45
        for k, m in enumerate(lead):
            st = t0 + k * beat * 2
            if st < dur - 1:
                render_note(buf, int(st * SR), beat * 1.6, nf(m), 0.14, sine,
                            a=0.05, r=0.8, fm_depth=0.15, fm_ratio=1.5, detune=0.001)
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.6)
            snare(buf, int((t0 + beat) * SR), vol=0.26)
    fade_in(buf, 2.0)
    fade_out(buf, 4.0)
    return buf

def track_i_cant_wait():
    """Melancholic nostalgia: Supremes-era bounce, strings-ish pad."""
    dur = 94
    buf = make_sample_chord_progression(
        dur,
        prog=[
            [(50, 0.85, 3.5), (54, 0.7, 3.5), (57, 0.6, 3.5), (66, 0.3, 1.7)],
            [(45, 0.85, 3.5), (52, 0.7, 3.5), (57, 0.6, 3.5), (64, 0.3, 1.7)],
            [(50, 0.85, 3.5), (53, 0.7, 3.5), (57, 0.6, 3.5), (62, 0.3, 1.7)],
            [(48, 0.85, 3.5), (55, 0.7, 3.5), (59, 0.6, 3.5), (64, 0.3, 1.7)],
        ] * 8,
        bpm=82, pad_vol=0.28, keys_vol=0.0, lp_pad=1000.0,
    )
    bpm = 82
    beat = 60.0 / bpm
    # string-ish lead (detuned saws, slow attack)
    lead = [74, 72, 69, 67, 69, 72, 74, 77, 74, 72, 69, 65, 67, 69, 72, 74]
    for rep in range(2):
        t0 = 8 + rep * 44
        for k, m in enumerate(lead):
            st = t0 + k * beat
            if st < dur - 0.5:
                render_note(buf, int(st * SR), beat * 1.3, nf(m), 0.10, saw, a=0.15, r=0.5, detune=0.002, lp=1600.0)
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.7)
            snare(buf, int((t0 + beat) * SR), vol=0.32)
    for bi in range(int(dur / (beat * 0.5)) + 1):
        hat(buf, int(bi * beat * 0.5 * SR), vol=0.07, dur=0.025)
    fade_in(buf, 1.5)
    fade_out(buf, 3.0)
    return buf

def track_white_lines():
    """Detached, isolated: icy FM keys, wide space, half-time drums."""
    dur = 100
    buf = Buf(dur)
    bpm = 72
    beat = 60.0 / bpm
    prog = [
        [(57, 0.7), (64, 0.5), (69, 0.4)],
        [(55, 0.7), (62, 0.5), (67, 0.4)],
        [(53, 0.7), (60, 0.5), (65, 0.4)],
        [(55, 0.7), (62, 0.5), (67, 0.4)],
    ] * 10
    bar = beat * 4
    for bi, chord in enumerate(prog):
        t0 = bi * bar
        if t0 >= dur:
            break
        for (note, vel) in chord:
            render_note(buf, int(t0 * SR), min(bar, dur - t0), nf(note), 0.13 * vel, sine,
                        a=0.02, r=0.5, fm_depth=0.6, fm_ratio=2.0)
    # icy arps
    arp = [81, 84, 88, 86, 84, 81, 79, 81]
    for rep in range(int(dur / (beat * 4)) + 1):
        for k, m in enumerate(arp):
            st = rep * beat * 4 + k * beat
            if st < dur - 0.2:
                render_note(buf, int(st * SR), 0.4, nf(m), 0.06, sine, a=0.01, r=0.35, fm_depth=0.3, fm_ratio=4.0)
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.55)
            snare(buf, int((t0 + beat) * SR), vol=0.22)
    for bi in range(int(dur / (beat / 2)) + 1):
        t0 = bi * beat / 2
        if t0 < dur - 0.1:
            hat(buf, int(t0 * SR), vol=0.06, dur=0.05)
    fade_in(buf, 2.0)
    fade_out(buf, 4.0)
    return buf

def track_circles():
    """Cortex-style Rhodes loop; lofi swing, head-nod drums."""
    dur = 92
    buf = Buf(dur)
    bpm = 92
    beat = 60.0 / bpm
    # rhodes-ish: sine + slight FM, bell partials
    prog = [
        [(52, 0.9), (55, 0.7), (59, 0.6), (62, 0.35)],
        [(50, 0.9), (53, 0.7), (57, 0.6), (60, 0.35)],
        [(55, 0.9), (59, 0.7), (62, 0.6), (66, 0.35)],
        [(53, 0.9), (56, 0.7), (60, 0.6), (63, 0.35)],
    ] * 10
    bar = beat * 4
    for bi, chord in enumerate(prog):
        t0 = bi * bar
        if t0 >= dur:
            break
        for (note, vel) in chord:
            render_note(buf, int(t0 * SR), min(beat * 3.6, dur - t0), nf(note), 0.20 * vel, sine,
                        a=0.004, r=0.5, fm_depth=0.25, fm_ratio=1.004)
            render_note(buf, int(t0 * SR), min(beat * 2.5, dur - t0), nf(note + 12), 0.06, sine,
                        a=0.004, r=0.6, fm_depth=0.3, fm_ratio=2.02)
    # bass walks
    roots = [40, 38, 43, 41]
    for bi in range(int(dur / bar) + 1):
        t0 = bi * bar
        r = roots[bi % 4]
        for k, off in enumerate([0, 1.5, 2.5, 3]):
            st = t0 + off * beat
            if st < dur - 0.2:
                render_note(buf, int(st * SR), beat * 0.9, nf(r - 12), 0.45, sine, a=0.008, r=0.25)
    # head-nod drums with swing
    sw = 0.10
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.72)
            snare(buf, int((t0 + beat * (1 + sw)) * SR), vol=0.36)
            hat(buf, int((t0 + beat * (1.5 + sw)) * SR), vol=0.09)
            hat(buf, int((t0 + beat * (0.5 + sw)) * SR), vol=0.07)
    vinyl(buf, vol=0.012, seed=101)
    fade_in(buf, 1.0)
    fade_out(buf, 3.0)
    return buf

def track_preacher_man():
    """Minimalist soul: sped-up feel, sparse, defiant rhodes stabs."""
    dur = 106
    buf = Buf(dur)
    bpm = 84
    beat = 60.0 / bpm
    chords = [
        [(49, 0.9), (56, 0.7), (61, 0.5)],
        [(47, 0.9), (54, 0.7), (59, 0.5)],
        [(49, 0.9), (56, 0.7), (64, 0.5)],
        [(45, 0.9), (52, 0.7), (57, 0.5)],
    ] * 11
    bar = beat * 4
    for bi, chord in enumerate(chords):
        t0 = bi * bar
        if t0 >= dur:
            break
        for (note, vel) in chord:
            # sped-up-sample feel: pitch +2 semitones-ish, short
            render_note(buf, int(t0 * SR), 0.9, nf(note + 2), 0.20 * vel, saw, a=0.003, r=0.4, lp=1500.0, detune=0.001)
            render_note(buf, int(t0 * SR), 0.9, nf(note + 14), 0.07 * vel, sine, a=0.003, r=0.5)
        root = chord[0][0] - 12
        render_note(buf, int(t0 * SR), beat * 1.8, nf(root), 0.48, sine, a=0.006, r=0.3)
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.7)
            snare(buf, int((t0 + beat) * SR), vol=0.3)
    hat_pat = [0, 0.75, 1.5, 1.75]
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        for off in hat_pat:
            st = t0 + off * beat
            if st < dur - 0.1:
                hat(buf, int(st * SR), vol=0.07, dur=0.03)
    fade_in(buf, 1.5)
    fade_out(buf, 3.5)
    return buf

def track_beauty_and_the_beast():
    """Downtempo; dusty guitar-ish pluck over slowed pad."""
    dur = 108
    buf = make_sample_chord_progression(
        dur,
        prog=[
            [(57, 0.85, 4.0), (61, 0.7, 4.0), (64, 0.6, 4.0)],
            [(53, 0.85, 4.0), (57, 0.7, 4.0), (60, 0.6, 4.0)],
            [(55, 0.85, 4.0), (59, 0.7, 4.0), (62, 0.6, 4.0)],
            [(50, 0.85, 4.0), (53, 0.7, 4.0), (57, 0.6, 4.0)],
        ] * 8,
        bpm=68, pad_vol=0.34, keys_vol=0.0, lp_pad=700.0,
    )
    bpm = 68
    beat = 60.0 / bpm
    # guitar-ish pluck (triangle + fast decay, slight vibrato)
    pluck_notes = [(64, 0), (67, 0.75), (69, 1.5), (64, 2.5), (62, 3), (64, 3.5)]
    for rep in range(int(dur / (beat * 4)) + 1):
        t0 = rep * beat * 4
        for (m, k) in pluck_notes:
            st = t0 + k * beat
            if st < dur - 0.3:
                render_note(buf, int(st * SR), 0.5, nf(m), 0.16, tri, a=0.003, r=0.35, fm_depth=0.08, fm_ratio=1.5)
                render_note(buf, int(st * SR), 0.35, nf(m - 12), 0.10, tri, a=0.003, r=0.3)
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.5)
            snare(buf, int((t0 + beat) * SR), vol=0.2)
    fade_in(buf, 2.5)
    fade_out(buf, 5.0)
    return buf

def track_damn():
    """Stripped, reflective: single piano motif, tape wobble, no drums."""
    dur = 96
    buf = Buf(dur)
    bpm = 66
    beat = 60.0 / bpm
    motif = [(57, 0), (61, 1), (64, 2), (66, 2.5), (64, 3), (61, 4), (57, 5), (54, 6)]
    for rep in range(int(dur / (beat * 7)) + 2):
        t0 = rep * beat * 7
        # tape wobble: slight pitch drift per rep
        drift = 1.0 + 0.002 * ((rep % 3) - 1)
        for (m, k) in motif:
            st = t0 + k * beat
            if st < dur - 0.5:
                render_note(buf, int(st * SR), beat * 1.8, nf(m) * drift, 0.18, sine,
                            a=0.002, r=0.8, fm_depth=0.22, fm_ratio=2.0)
                render_note(buf, int(st * SR), beat * 2.2, nf(m + 12) * drift, 0.06, sine, a=0.002, r=1.0)
    # low drone
    for i in range(len(buf)):
        buf.d[i] += sine(i * nf(33) / SR) * 0.06 * (0.5 + 0.5 * sine(i / SR * 0.1))
    vinyl(buf, vol=0.014, seed=55)
    fade_in(buf, 3.0)
    fade_out(buf, 5.0)
    return buf

def track_last_breath():
    """Salsa-tinged: montuno piano, clave, congas-ish toms, brass stab."""
    dur = 100
    buf = Buf(dur)
    bpm = 98
    beat = 60.0 / bpm
    # montuno piano (octave-displaced tumbao)
    montuno = [61, 64, 67, 72, 67, 64, 62, 65, 69, 74, 69, 65, 57, 61, 64, 69]
    for rep in range(int(dur / (beat * 2)) + 1):
        for k, m in enumerate(montuno):
            st = rep * beat * 2 + k * beat * 0.5
            if st < dur - 0.15:
                render_note(buf, int(st * SR), 0.16, nf(m), 0.16, tri, a=0.002, r=0.08, lp=3000.0)
                render_note(buf, int(st * SR), 0.12, nf(m + 12), 0.05, square, a=0.002, r=0.06, lp=4000.0)
    # clave pattern (3-2)
    clave = [0, 0.75, 1.5, 2.5, 3]  # in beats within 2-beat*2
    for rep in range(int(dur / (beat * 4)) + 1):
        t0 = rep * beat * 4
        for off in clave:
            st = t0 + off * beat
            if st < dur - 0.1:
                # woodblock-ish
                render_note(buf, int(st * SR), 0.08, 1750.0, 0.16, square, a=0.001, r=0.05, lp=6000.0)
    # conga-ish toms
    for bi in range(int(dur / (beat * 0.5)) + 1):
        t0 = bi * beat * 0.5
        if bi % 4 == 2 and t0 < dur - 0.2:
            # low conga: pitch sweep sine
            n = int(0.16 * SR)
            ph = 0.0
            for i in range(n):
                t = i / SR
                f = 180 * math.exp(-t * 8) + 90
                ph += f / SR
                buf.add(int(t0 * SR) + i, sine(ph) * 0.28 * math.exp(-t * 18))
    # salsa brass stab
    for rep in range(int(dur / (beat * 8)) + 1):
        t0 = rep * beat * 8 + beat * 4
        if t0 < dur - 1:
            for note in [61, 64, 67]:
                render_note(buf, int(t0 * SR), beat * 0.9, nf(note), 0.13, saw, a=0.01, r=0.2, detune=0.003, lp=2200.0)
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.6)
            snare(buf, int((t0 + beat) * SR), vol=0.3)
    fade_in(buf, 1.0)
    fade_out(buf, 3.0)
    return buf

def track_this_one_here():
    """Brazilian-jazz fusion: Cortex-adjacent samba-jazz keys and bass."""
    dur = 104
    buf = track_circles().__class__(dur)  # placeholder replaced below
    buf = Buf(dur)
    bpm = 104
    beat = 60.0 / bpm
    prog = [
        [(50, 0.9), (54, 0.7), (57, 0.6), (61, 0.4)],
        [(52, 0.9), (55, 0.7), (59, 0.6), (62, 0.4)],
        [(48, 0.9), (52, 0.7), (55, 0.6), (59, 0.4)],
        [(53, 0.9), (56, 0.7), (60, 0.6), (64, 0.4)],
    ] * 11
    bar = beat * 4
    for bi, chord in enumerate(prog):
        t0 = bi * bar
        if t0 >= dur:
            break
        # comping on 2 and 4
        for off in [1, 2.5, 3.5]:
            st = t0 + off * beat
            if st < dur - 0.2:
                for (note, vel) in chord:
                    render_note(buf, int(st * SR), 0.22, nf(note), 0.16 * vel, sine,
                                a=0.003, r=0.15, fm_depth=0.3, fm_ratio=2.0)
    # walking samba bass
    bass = [38, 40, 42, 43, 45, 43, 42, 40, 38, 40, 41, 42, 43, 42, 40, 38]
    for rep in range(int(dur / (beat * 4)) + 1):
        for k, b in enumerate(bass):
            st = rep * beat * 4 + k * beat * 0.5 + (beat * 0.5 if k % 2 == 1 else 0) * 0
            st = rep * beat * 4 + k * beat * 0.5
            if st < dur - 0.15:
                render_note(buf, int(st * SR), beat * 0.45, nf(b), 0.42, sine, a=0.005, r=0.12)
    # bossa percussion: shaker pattern (eighth notes, accents)
    for bi in range(int(dur / (beat * 0.5)) + 1):
        t0 = bi * beat * 0.5
        if t0 < dur - 0.08:
            hat(buf, int(t0 * SR), vol=0.09 if bi % 2 else 0.13, dur=0.04)
    for bi in range(int(dur / (beat * 2)) + 1):
        t0 = bi * beat * 2
        if t0 < dur - 0.4:
            kick(buf, int(t0 * SR), vol=0.5, dur=0.2)
            snare(buf, int((t0 + beat) * SR), vol=0.3)
    vinyl(buf, vol=0.008, seed=77)
    fade_in(buf, 1.0)
    fade_out(buf, 3.5)
    return buf

def track_losing_your_mind():
    """Krautrock-creep: motorik pulse, 'Vitamin C' tension, anxiety build."""
    dur = 112
    buf = Buf(dur)
    bpm = 118
    beat = 60.0 / bpm
    # motorik pulse bass
    for bi in range(int(dur / (beat * 0.5)) + 1):
        t0 = bi * beat * 0.5
        if t0 < dur - 0.2:
            render_note(buf, int(t0 * SR), 0.24, nf(33), 0.42, square, a=0.002, r=0.08, lp=700.0)
            render_note(buf, int(t0 * SR), 0.24, nf(45), 0.10, saw, a=0.002, r=0.08, lp=1200.0)
    # hypnotic two-note riff
    riff = [69, 69, 72, 69, 71, 69, 74, 72]
    for rep in range(int(dur / (beat * 2)) + 1):
        for k, m in enumerate(riff):
            st = rep * beat * 2 + k * beat * 0.25
            if st < dur - 0.1:
                render_note(buf, int(st * SR), 0.16, nf(m), 0.12 * (0.6 + 0.4 * min(1.0, st / dur)),
                            saw, a=0.003, r=0.07, detune=0.004, lp=2600.0)
    # drums building
    for bi in range(int(dur / (beat * 0.5)) + 1):
        t0 = bi * beat * 0.5
        inten = min(1.0, t0 / dur)
        if t0 < dur - 0.3 and bi % 2 == 0:
            kick(buf, int(t0 * SR), vol=0.5 + 0.35 * inten)
            snare(buf, int(t0 * SR), vol=0.25 + 0.2 * inten)
        if t0 < dur - 0.1:
            hat(buf, int(t0 * SR), vol=0.10 + 0.05 * inten, dur=0.03)
    # dissonant swarm at end
    for i in range(int(len(buf) * 0.3)):
        idx = len(buf) - int(len(buf) * 0.3) + i
        t = i / SR
        a = min(1.0, t / 20.0) * 0.06
        v = (sine(idx * nf(69) / SR) + sine(idx * nf(70) / SR) * 0.8 + sine(idx * nf(75.5) / SR) * 0.5)
        buf.d[idx] += v * a
    fade_in(buf, 3.0)
    fade_out(buf, 5.0)
    return buf

def track_bully_instrumental():
    # alias used by manifest
    return track_bully()

TRACKS = {
    "king": track_king,
    "this_a_must": track_this_a_must,
    "father": track_father,
    "all_the_love": track_all_the_love,
    "punch_drunk": track_punch_drunk,
    "whatever_works": track_whatever_works,
    "mamas_favorite": track_mamas_favorite,
    "sisters_and_brothers": track_sisters_and_brothers,
    "bully": track_bully,
    "highs_and_lows": track_highs_and_lows,
    "i_cant_wait": track_i_cant_wait,
    "white_lines": track_white_lines,
    "circles": track_circles,
    "preacher_man": track_preacher_man,
    "beauty_and_the_beast": track_beauty_and_the_beast,
    "damn": track_damn,
    "last_breath": track_last_breath,
    "this_one_here": track_this_one_here,
    "losing_your_mind": track_losing_your_mind,
}

def main():
    only = os.environ.get("BULLY_TRACK")
    for name, fn in TRACKS.items():
        if only and name != only:
            continue
        path = os.path.join(SND, f"bully_discs_{name}.wav")
        if os.path.exists(path):
            print(f"skip {name} (exists)")
            continue
        print(f"rendering {name} ...", flush=True)
        buf = fn()
        buf.write_wav(path)
        print(f"  -> {path} ({len(buf)/SR:.1f}s)")

if __name__ == "__main__":
    main()
