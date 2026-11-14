import asyncio
import math
import random
import sys

import pygame

# ----------------------------------------------------------------------------
# CONFIG & PALETTE
# ----------------------------------------------------------------------------
W, H = 1280, 720
FPS = 50  # lebih ramah untuk perangkat mobile; game tetap terasa halus
GROUND_Y = 630          # garis kaki karakter
BOARD_LIFT = 33         # tinggi badan karakter saat berdiri di atas skateboard

GIRL_X0, GIRL_X1 = -190, 540
BOY_X0, BOY_X1 = 1470, 740

MIDNIGHT = (10, 13, 42)
NAVY = (24, 28, 72)
PURPLE = (54, 36, 90)
DEEP_PURPLE = (34, 22, 62)
DUSTY_PINK = (214, 150, 172)
PINK_SOFT = (242, 192, 208)
HOT_PINK = (255, 150, 178)
CREAM = (250, 238, 214)
AMBER = (255, 196, 100)
AMBER_DEEP = (228, 152, 72)
OUTLINE = (44, 28, 64)
SKIN = (255, 225, 204)
INK = (40, 26, 54)


# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------
def clamp(v, a=0.0, b=1.0):
    return a if v < a else (b if v > b else v)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp2(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def prog(t, a, b):
    """Progress 0..1 dari t di dalam rentang [a, b]."""
    return clamp((t - a) / (b - a))


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_cubic(t):
    t = clamp(t)
    return t ** 3


def ease_in_out_sine(t):
    return -(math.cos(math.pi * clamp(t)) - 1) / 2


def ease_out_back(t, s=1.70158):
    t = clamp(t)
    c = s + 1
    return 1 + c * (t - 1) ** 3 + s * (t - 1) ** 2


def mix(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)), int(lerp(c1[2], c2[2], t)))


FONT_CANDIDATES = ("inkfree", "segoeprint", "bradleyhandittc", "kristenitc", "comicsansms",
                   "chalkboard", "markerfelt", "segoescript", "comicneue",
                   "arialroundedmtbold", "varelaround", "nunito")
_font_cache = {}


def get_font(size, bold=False):
    key = (size, bold)
    f = _font_cache.get(key)
    if f is None:
        path = None
        for name in FONT_CANDIDATES:
            path = pygame.font.match_font(name, bold=bold)
            if path:
                break
        f = pygame.font.Font(path, size) if path else pygame.font.Font(None, int(size * 1.25))
        _font_cache[key] = f
    return f


def heart_points(cx, cy, width, n=40):
    k = width / 32.0
    pts = []
    for i in range(n):
        t = i / n * math.tau
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * k, cy + (y - 2.5) * k))
    return pts


def star_points(cx, cy, R, r, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(n * 2):
        rad = R if i % 2 == 0 else r
        a = rot + i * math.pi / n
        pts.append((cx + math.cos(a) * rad, cy + math.sin(a) * rad))
    return pts


_glow_cache = {}


def glow_surface(r, color, strength=1.0):
    """Lingkaran cahaya lembut (alpha radial)."""
    r = max(2, int(r))
    key = (r, color, round(strength, 2))
    s = _glow_cache.get(key)
    if s is None:
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for i in range(r, 0, -2):
            a = int(255 * strength * (1 - i / r) ** 2)
            pygame.draw.circle(s, (color[0], color[1], color[2], a), (r, r), i)
        _glow_cache[key] = s
    return s


_sprite_cache = {}


def make_sprite(kind, color, size=64):
    key = (kind, color, size)
    s = _sprite_cache.get(key)
    if s is not None:
        return s
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    if kind == "heart":
        pygame.draw.polygon(s, color, heart_points(c, c, size * 0.88))
        pygame.draw.circle(s, (255, 255, 255, 170), (int(c - size * 0.2), int(c - size * 0.16)), max(2, int(size * 0.07)))
    elif kind == "star":
        pygame.draw.polygon(s, color, star_points(c, c, size * 0.48, size * 0.21))
    elif kind == "sparkle":
        pygame.draw.polygon(s, color, star_points(c, c, size * 0.48, size * 0.09, 4))
    elif kind == "flower":
        for i in range(5):
            a = i * math.tau / 5 - math.pi / 2
            pygame.draw.circle(s, color, (int(c + math.cos(a) * size * 0.21), int(c + math.sin(a) * size * 0.21)), int(size * 0.17))
        pygame.draw.circle(s, AMBER, (int(c), int(c)), max(2, int(size * 0.11)))
    elif kind == "glow":
        s = glow_surface(size / 2, color, 1.0)
    _sprite_cache[key] = s
    return s


_streak_cache = {}


def streak_sprite(length, color):
    length = max(8, (int(length) // 8) * 8)
    key = (length, color)
    s = _streak_cache.get(key)
    if s is None:
        s = pygame.Surface((length, 4), pygame.SRCALPHA)
        for i in range(length):
            s.fill((color[0], color[1], color[2], int(255 * (i / length) ** 1.5)), (i, 1, 1, 2))
        _streak_cache[key] = s
    return s


def silhouette(surf, color):
    m = pygame.mask.from_surface(surf, 110)
    return m.to_surface(setcolor=(color[0], color[1], color[2], 255), unsetcolor=(0, 0, 0, 0))


def render_glow_from(fill_surf, outline, glow, pad=40, ow=3, strength=2):
    """Beri outline + glow lembut pada surface teks/bentuk."""
    w, h = fill_surf.get_size()
    out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    base = pygame.Surface(out.get_size(), pygame.SRCALPHA)
    gs = silhouette(fill_surf, glow)
    for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4), (0, 0)):
        base.blit(gs, (pad + dx, pad + dy))
    small = pygame.transform.smoothscale(base, (max(1, base.get_width() // 6), max(1, base.get_height() // 6)))
    blur = pygame.transform.smoothscale(small, base.get_size())
    for _ in range(strength):
        out.blit(blur, (0, 0))
    os_ = silhouette(fill_surf, outline)
    for dx in range(-ow, ow + 1):
        for dy in range(-ow, ow + 1):
            if dx * dx + dy * dy <= ow * ow + 1:
                out.blit(os_, (pad + dx, pad + dy))
    out.blit(fill_surf, (pad, pad))
    return out


def draw_limb(surf, pts, width, color, outline, ow=3):
    ip = [(int(p[0]), int(p[1])) for p in pts]
    for p0, p1 in zip(ip, ip[1:]):
        pygame.draw.line(surf, outline, p0, p1, width + ow * 2)
    for p in ip:
        pygame.draw.circle(surf, outline, p, (width + ow * 2) // 2)
    for p0, p1 in zip(ip, ip[1:]):
        pygame.draw.line(surf, color, p0, p1, width)
    for p in ip:
        pygame.draw.circle(surf, color, p, width // 2)


def arm_ik(S, T, L1, L2, side_sign):
    """Two-bone IK sederhana. Mengembalikan (siku, tangan)."""
    dx, dy = T[0] - S[0], T[1] - S[1]
    d = math.hypot(dx, dy)
    if d < 1e-3:
        dx, dy, d = 0.0, 1.0, 1.0
    maxd = L1 + L2 - 0.5
    if d > maxd:
        dx *= maxd / d
        dy *= maxd / d
        d = maxd
    a = (L1 * L1 - L2 * L2 + d * d) / (2 * d)
    h = math.sqrt(max(L1 * L1 - a * a, 0.0))
    ux, uy = dx / d, dy / d
    bx, by = S[0] + ux * a, S[1] + uy * a
    n1, n2 = (-uy, ux), (uy, -ux)

    def score(n):
        return n[1] + n[0] * side_sign * 0.7

    n = n1 if score(n1) >= score(n2) else n2
    return (bx + n[0] * h, by + n[1] * h), (S[0] + dx, S[1] + dy)


_blush_sprite = None


def blush_sprite():
    global _blush_sprite
    if _blush_sprite is None:
        s = pygame.Surface((46, 28), pygame.SRCALPHA)
        for i in range(10):
            k = i / 10
            w, h = 46 * (1 - k * 0.6), 28 * (1 - k * 0.6)
            pygame.draw.ellipse(s, (255, 118, 150, 40 + 14 * i), (23 - w / 2, 14 - h / 2, w, h))
        _blush_sprite = s
    return _blush_sprite


_shadow_sprite = None


def shadow_sprite():
    global _shadow_sprite
    if _shadow_sprite is None:
        _shadow_sprite = pygame.transform.smoothscale(glow_surface(60, (8, 4, 24), 1.0), (240, 44))
    return _shadow_sprite


# ----------------------------------------------------------------------------
# PARTICLE
# ----------------------------------------------------------------------------
class Particle:
    def __init__(self, kind, x, y, vx, vy, life, size, color, gravity=0.0, sway=0.0, spin=0.0,
                 fade_in=0.3, drag=0.0, peak=1.0, grow=0.0, dirx=1):
        self.kind, self.x, self.y, self.vx, self.vy = kind, x, y, vx, vy
        self.life, self.size, self.color = life, size, color
        self.gravity, self.sway, self.spin = gravity, sway, spin
        self.fade_in, self.drag, self.peak, self.grow, self.dirx = fade_in, drag, peak, grow, dirx
        self.age = 0.0
        self.phase = random.random() * math.tau
        self.rot = random.uniform(-25, 25)

    @property
    def alive(self):
        return self.age < self.life

    def update(self, dt):
        self.age += dt
        if self.drag:
            k = max(0.0, 1 - self.drag * dt)
            self.vx *= k
            self.vy *= k
        self.vy += self.gravity * dt
        self.x += (self.vx + math.sin(self.age * 2.2 + self.phase) * self.sway) * dt
        self.y += self.vy * dt
        self.rot += self.spin * dt
        self.size += self.grow * dt

    def alpha(self):
        a = min(self.age / max(self.fade_in, 1e-3), 1.0)
        a *= min((self.life - self.age) / (self.life * 0.4), 1.0)
        return clamp(a) * self.peak

    def draw(self, surf):
        a = self.alpha()
        if a <= 0.02:
            return
        if self.kind == "streak":
            img = streak_sprite(self.size, self.color)
            if self.dirx < 0:
                img = pygame.transform.flip(img, True, False)
            else:
                img = img.copy()
            img.set_alpha(int(255 * a * 0.6))
            surf.blit(img, (self.x - img.get_width() / 2, self.y))
            return
        if self.kind == "glow":
            img = make_sprite("glow", self.color, max(4, int(self.size / 4) * 4))
            img.set_alpha(int(255 * a))
            surf.blit(img, (self.x - img.get_width() / 2, self.y - img.get_height() / 2))
            return
        base = make_sprite(self.kind, self.color, 64)
        img = pygame.transform.rotozoom(base, self.rot, self.size / 64.0)
        img.set_alpha(int(255 * a))
        surf.blit(img, img.get_rect(center=(self.x, self.y)))


# ----------------------------------------------------------------------------
# BACKGROUND
# ----------------------------------------------------------------------------
class Background:
    LAMPS = ((300, 1), (1000, -1))      # (x tiang, arah lengan lampu)
    MOON = (1120, 120)

    def __init__(self):
        rnd = random.Random(11)
        self.sky = self._build_sky()
        self.city = pygame.Surface((W, H), pygame.SRCALPHA)
        self.bulbs = []
        self._build_city(rnd)
        self.stars = []
        for _ in range(115):
            self.stars.append((rnd.uniform(0, W), rnd.uniform(8, 430), rnd.choice((1, 1, 2, 2, 3)),
                               rnd.uniform(0, 6.28), rnd.uniform(1.2, 3.4), rnd.random() < 0.28))
        self.star_dots = {r: glow_surface(r * 3 + 2, (255, 244, 220), 0.9) for r in (1, 2, 3)}
        self.star_spark = make_sprite("sparkle", CREAM, 26)
        self.moon = self._build_moon()
        self.clouds = [(rnd.uniform(0, W), y, sp, self._build_cloud(rnd)) for y, sp in ((130, 7), (250, 4), (60, 5), (340, 6))]
        self.lamp_cone = self._build_cone()
        self.lamp_pool = pygame.transform.smoothscale(glow_surface(120, AMBER, 0.55), (340, 64))
        self.doodles = self._build_doodles(rnd)
        self.lamp_level = 0.0

    # ---------- static builders ----------
    def _build_sky(self):
        sky = pygame.Surface((W, H)).convert()
        top, mid, low = (9, 12, 42), (32, 24, 78), (112, 66, 120)
        for y in range(H):
            t = y / 560.0
            c = mix(top, mid, t / 0.6) if t < 0.6 else mix(mid, low, min((t - 0.6) / 0.4, 1.0))
            pygame.draw.line(sky, c, (0, y), (W, y))
        return sky

    def _build_moon(self):
        s = pygame.Surface((120, 120), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 243, 214), (60, 60), 44)
        for cx, cy, r in ((46, 48, 9), (72, 70, 12), (68, 42, 6), (44, 76, 5)):
            pygame.draw.circle(s, (238, 222, 190), (cx, cy), r)
        pygame.draw.circle(s, (255, 252, 236), (60, 60), 44, 2)
        return s

    def _build_cloud(self, rnd):
        s = pygame.Surface((300, 80), pygame.SRCALPHA)
        for _ in range(7):
            w, h = rnd.randint(70, 130), rnd.randint(22, 34)
            pygame.draw.ellipse(s, (96, 64, 126, 70), (rnd.randint(0, 170), rnd.randint(18, 44), w, h))
        return s

    def _build_cone(self):
        hgt, wid = 280, 340
        s = pygame.Surface((wid, hgt), pygame.SRCALPHA)
        for i in range(hgt):
            half = lerp(12, wid / 2, i / hgt)
            a = int(78 * (1 - i / hgt) ** 1.25)
            pygame.draw.line(s, (255, 214, 130, a), (wid / 2 - half, i), (wid / 2 + half, i))
        return s

    def _doodle_sprite(self, kind, color, size, seed):
        rnd = random.Random(seed)
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size / 2
        col = (color[0], color[1], color[2], 255)

        def wob(pts):
            return [(x + rnd.uniform(-1.3, 1.3), y + rnd.uniform(-1.3, 1.3)) for x, y in pts]

        if kind == "heart":
            pygame.draw.lines(s, col, True, wob(heart_points(c, c, size * 0.8)), 3)
        elif kind == "star":
            pygame.draw.lines(s, col, True, wob(star_points(c, c, size * 0.44, size * 0.19)), 3)
        elif kind == "flower":
            for i in range(5):
                a = i * math.tau / 5 - math.pi / 2
                pygame.draw.circle(s, col, (int(c + math.cos(a) * size * 0.23), int(c + math.sin(a) * size * 0.23)), int(size * 0.15), 3)
            pygame.draw.circle(s, col, (int(c), int(c)), int(size * 0.09), 3)
        else:  # moon
            pygame.draw.circle(s, col, (int(c), int(c)), int(size * 0.36))
            pygame.draw.circle(s, (0, 0, 0, 0), (int(c + size * 0.16), int(c - size * 0.08)), int(size * 0.32))
        return s

    def _build_doodles(self, rnd):
        spots = [(90, 80, "star"), (214, 190, "heart"), (338, 108, "flower"), (470, 60, "moon"), (566, 176, "star"),
                 (760, 84, "heart"), (904, 176, "flower"), (1010, 52, "star"), (1186, 214, "heart"),
                 (1170, 60, "flower"), (58, 330, "moon"), (160, 420, "heart"), (1234, 340, "star"),
                 (1120, 440, "flower"), (640, 230, "sparkle"), (420, 250, "heart"), (850, 250, "star")]
        cols = (CREAM, PINK_SOFT, AMBER, (214, 190, 250))
        out = []
        for i, (x, y, kind) in enumerate(spots):
            size = rnd.choice((54, 62, 70))
            if kind == "sparkle":
                kind = "star"
            out.append((self._doodle_sprite(kind, cols[i % 4], size, 100 + i), x, y, 2.0 + i * 0.26, rnd.uniform(0, 6)))
        return out

    # ---------- city ----------
    def _windows(self, c, area, rnd, cell, gap, lit, glow, far=False):
        cw, ch = cell
        gx, gy = gap
        y = area.top
        while y + ch <= area.bottom:
            x = area.left
            while x + cw <= area.right:
                if rnd.random() < lit:
                    col = mix(AMBER, (255, 218, 150), rnd.random())
                    if far:
                        col = mix(col, (150, 100, 120), 0.35)
                    if glow:
                        g = glow_surface(36, AMBER, 0.42)
                        c.blit(g, (x + cw / 2 - 36, y + ch / 2 - 36))
                    pygame.draw.rect(c, col, (x, y, cw, ch), border_radius=3)
                    if not far:
                        pygame.draw.line(c, (190, 130, 80), (x + cw // 2, y), (x + cw // 2, y + ch), 2)
                        pygame.draw.line(c, (190, 130, 80), (x, y + ch // 2), (x + cw, y + ch // 2), 2)
                else:
                    pygame.draw.rect(c, (20, 18, 54) if far else (30, 24, 66), (x, y, cw, ch), border_radius=3)
                x += cw + gx
            y += ch + gy

    def _wire(self, c, p0, p1, sag, col=(18, 14, 38), w=2):
        pts = []
        for i in range(41):
            t = i / 40
            pts.append((lerp(p0[0], p1[0], t), lerp(p0[1], p1[1], t) + 4 * sag * t * (1 - t)))
        pygame.draw.lines(c, col, False, pts, w)
        return pts

    def _tree(self, c, x, base, s):
        pygame.draw.rect(c, (40, 28, 62), (x - 7 * s, base - 90 * s, 14 * s, 90 * s), border_radius=4)
        for dx, dy, r, col in ((0, -120, 62, (28, 48, 88)), (-42, -98, 44, (32, 54, 94)), (44, -100, 46, (30, 52, 92)),
                               (-14, -150, 40, (38, 64, 106)), (26, -140, 36, (36, 60, 100))):
            pygame.draw.circle(c, col, (int(x + dx * s), int(base + dy * s)), int(r * s))
        for dx, dy, r in ((-22, -146, 16), (14, -164, 12), (-50, -112, 12)):
            pygame.draw.circle(c, (56, 88, 128), (int(x + dx * s), int(base + dy * s)), int(r * s))

    def _shop(self, c, x, w, kind, sign, awn1, awn2):
        y0 = 438
        pygame.draw.rect(c, (30, 20, 54), (x + 12, y0, w - 24, 548 - y0))
        win = pygame.Rect(x + 24, y0 + 34, w - 48, 548 - y0 - 40)
        for i in range(win.height):
            pygame.draw.line(c, mix((255, 210, 128), (236, 148, 96), i / win.height), (win.left, win.top + i), (win.right, win.top + i))
        if kind == "florist":
            for i in range(5):
                px = win.left + 22 + i * (win.width - 44) / 4
                pygame.draw.rect(c, (150, 96, 90), (px - 12, win.bottom - 26, 24, 26), border_radius=4)
                pygame.draw.circle(c, [HOT_PINK, CREAM, (190, 170, 240), AMBER, PINK_SOFT][i], (int(px), int(win.bottom - 40 - (i % 2) * 14)), 13)
                pygame.draw.line(c, (70, 130, 100), (px, win.bottom - 28), (px, win.bottom - 40 - (i % 2) * 14), 3)
            for i in range(3):
                bx = x + 30 + i * 46
                pygame.draw.polygon(c, (96, 72, 120), [(bx - 16, 548), (bx + 16, 548), (bx + 12, 520), (bx - 12, 520)])
                for k in range(3):
                    pygame.draw.circle(c, [HOT_PINK, AMBER, CREAM][(i + k) % 3], (bx - 10 + k * 10, 508 - (k % 2) * 8), 8)
        elif kind == "cafe":
            for i in range(3):
                lx = win.left + 40 + i * (win.width - 80) / 2
                pygame.draw.line(c, (60, 36, 70), (lx, win.top), (lx, win.top + 26), 2)
                pygame.draw.polygon(c, (60, 36, 70), [(lx - 14, win.top + 38), (lx + 14, win.top + 38), (lx + 6, win.top + 24), (lx - 6, win.top + 24)])
                c.blit(glow_surface(26, (255, 236, 170), 0.8), (lx - 26, win.top + 14))
            pygame.draw.rect(c, (120, 76, 80), (win.left + 10, win.bottom - 34, win.width - 20, 10), border_radius=4)
            for i in range(4):
                cx = win.left + 30 + i * (win.width - 60) / 3
                pygame.draw.rect(c, CREAM, (cx - 9, win.bottom - 52, 18, 16), border_radius=4)
        else:  # records
            for r in range(3):
                pygame.draw.rect(c, (96, 60, 100), (win.left + 8, win.top + 16 + r * 34, win.width - 16, 5))
                for i in range(6):
                    pygame.draw.rect(c, [DUSTY_PINK, CREAM, (150, 130, 220), AMBER][(i + r) % 4], (win.left + 14 + i * (win.width - 40) / 6, win.top - 6 + r * 34 + 4, 12, 22))
            pygame.draw.circle(c, (30, 22, 50), (win.right - 36, win.bottom - 30), 22)
            pygame.draw.circle(c, DUSTY_PINK, (win.right - 36, win.bottom - 30), 7)
        pygame.draw.rect(c, OUTLINE, win, 4, border_radius=3)
        # awning
        n = 8
        sw = (w - 16) / n
        for i in range(n):
            xs = x + 8 + i * sw
            col = awn1 if i % 2 == 0 else awn2
            pygame.draw.polygon(c, col, [(xs, y0 - 2), (xs + sw, y0 - 2), (xs + sw + 2, y0 + 30), (xs - 2, y0 + 30)])
            pygame.draw.circle(c, col, (int(xs + sw / 2), y0 + 30), int(sw / 2))
        pygame.draw.line(c, OUTLINE, (x + 8, y0 - 2), (x + w - 8, y0 - 2), 4)
        # sign board
        board = pygame.Rect(x + w // 2 - 70, y0 - 40, 140, 34)
        pygame.draw.rect(c, (58, 34, 84), board, border_radius=8)
        pygame.draw.rect(c, DUSTY_PINK, board, 3, border_radius=8)
        txt = get_font(24, True).render(sign, True, CREAM)
        c.blit(txt, txt.get_rect(center=board.center))

    def _build_city(self, rnd):
        c = self.city
        # far skyline
        x = -30
        while x < W:
            w, h = rnd.randint(70, 130), rnd.randint(190, 340)
            top = 560 - h
            col = mix((28, 28, 78), (48, 34, 94), rnd.random() * 0.5)
            pygame.draw.rect(c, col, (x, top, w, h))
            if rnd.random() < 0.35:
                pygame.draw.line(c, col, (x + w // 2, top), (x + w // 2, top - rnd.randint(14, 40)), 3)
            self._windows(c, pygame.Rect(x + 8, top + 10, w - 16, h - 40), rnd, (14, 20), (8, 12), 0.28, False, True)
            x += w + rnd.randint(-4, 8)
        haze = pygame.Surface((W, 160), pygame.SRCALPHA)
        for i in range(160):
            pygame.draw.line(haze, (150, 92, 140, int(70 * (i / 160) ** 1.4)), (0, i), (W, i))
        c.blit(haze, (0, 420))

        # near buildings
        near = [(-10, 262, 250, (62, 42, 104), ("FLORIST", "florist", DUSTY_PINK, CREAM)),
                (252, 236, 312, (46, 36, 92), None),
                (488, 300, 232, (68, 46, 108), ("CAFE", "cafe", AMBER_DEEP, CREAM)),
                (788, 236, 324, (48, 38, 94), None),
                (1024, 270, 262, (64, 44, 102), ("RECORDS", "records", (126, 104, 206), CREAM))]
        for x, w, top, col, shop in near:
            pygame.draw.rect(c, col, (x, top, w, 548 - top))
            pygame.draw.rect(c, mix(col, (255, 255, 255), 0.1), (x - 4, top - 8, w + 8, 12), border_radius=3)
            wy_end = 424 if shop else 440
            self._windows(c, pygame.Rect(x + 20, top + 26, w - 40, wy_end - top - 30), rnd, (30, 40), (18, 18), 0.5, True)
            if shop:
                self._shop(c, x, w, shop[1], shop[0], shop[2], shop[3])
            else:
                pygame.draw.rect(c, (30, 22, 56), (x + w // 2 - 24, 468, 48, 80), border_radius=6)
                pygame.draw.rect(c, (255, 206, 128), (x + w // 2 - 15, 478, 30, 34), border_radius=4)
                for dx in (-86, 44):
                    pygame.draw.rect(c, (255, 200, 120) if rnd.random() < 0.7 else (30, 24, 66), (x + w // 2 + dx, 474, 42, 40), border_radius=4)
                    pygame.draw.rect(c, OUTLINE, (x + w // 2 + dx, 474, 42, 40), 3, border_radius=4)
                c.blit(glow_surface(40, AMBER, 0.55), (x + w // 2 - 40, 450))

        # trees
        for tx, ts in ((255, 1.0), (795, 1.05), (1255, 0.95)):
            self._tree(c, tx, 556, ts)

        # sidewalk, curb, road
        for i in range(102):
            pygame.draw.line(c, mix((78, 60, 116), (52, 40, 90), i / 102), (0, 548 + i), (W, 548 + i))
        for i in range(-2, 18):
            px = i * 96
            pygame.draw.line(c, (96, 78, 136), (px, 548), (px + (px - 640) * 0.28, 650), 2)
        pygame.draw.line(c, (96, 78, 136), (0, 596), (W, 596), 2)
        pygame.draw.rect(c, (124, 100, 164), (0, 650, W, 8))
        pygame.draw.rect(c, (28, 22, 54), (0, 658, W, 62))
        for i in range(0, W, 130):
            pygame.draw.rect(c, (120, 104, 150), (i + 20, 692, 70, 6), border_radius=3)

        # street furniture: bench, mailbox, bin
        pygame.draw.rect(c, (46, 34, 76), (84, 562, 112, 10), border_radius=3)
        pygame.draw.rect(c, (46, 34, 76), (84, 530, 112, 8), border_radius=3)
        pygame.draw.rect(c, (46, 34, 76), (90, 538, 6, 26))
        pygame.draw.rect(c, (46, 34, 76), (184, 538, 6, 26))
        pygame.draw.rect(c, (46, 34, 76), (92, 572, 6, 30))
        pygame.draw.rect(c, (46, 34, 76), (182, 572, 6, 30))
        pygame.draw.rect(c, (150, 80, 110), (440, 508, 34, 40), border_radius=10)
        pygame.draw.rect(c, (60, 40, 80), (454, 548, 6, 26))
        pygame.draw.rect(c, (60, 44, 90), (880, 524, 28, 40), border_radius=5)
        pygame.draw.rect(c, (80, 62, 112), (876, 518, 36, 8), border_radius=3)

        # power poles + wires + birds
        for px in (150, 1150):
            pygame.draw.rect(c, (36, 26, 60), (px - 5, 150, 10, 412), border_radius=3)
            pygame.draw.rect(c, (36, 26, 60), (px - 26, 158, 52, 7), border_radius=3)
        pts = []
        for k in range(3):
            self._wire(c, (-20, 204 + k * 14), (134 + k * 16, 162), 18)
            pts = self._wire(c, (134 + k * 16, 162), (1134 + k * 16, 162), 70)
            self._wire(c, (1134 + k * 16, 162), (1300, 204 + k * 14), 18)
        for bi in (13, 14, 26):
            bx, by = pts[bi]
            pygame.draw.ellipse(c, (22, 18, 46), (bx - 7, by - 12, 15, 10))
            pygame.draw.circle(c, (22, 18, 46), (int(bx + 7), int(by - 11)), 4)
            pygame.draw.polygon(c, (22, 18, 46), [(bx - 6, by - 8), (bx - 14, by - 4), (bx - 5, by - 5)])

        # lamp posts + string lights
        for lx, s in self.LAMPS:
            pygame.draw.rect(c, (40, 30, 70), (lx - 5, 336, 10, 224), border_radius=3)
            pygame.draw.rect(c, (56, 44, 90), (lx - 11, 548, 22, 14), border_radius=3)
            pygame.draw.lines(c, (40, 30, 70), False, [(lx, 342), (lx, 328), (lx + s * 16, 320), (lx + s * 34, 322)], 6)
            hx = lx + s * 34
            pygame.draw.polygon(c, (50, 38, 84), [(hx - 17, 322), (hx + 17, 322), (hx + 11, 335), (hx - 11, 335)])
        a, b = (self.LAMPS[0][0], 340), (self.LAMPS[1][0], 340)
        pts = self._wire(c, a, b, 64, (24, 18, 44), 2)
        cols = (AMBER, HOT_PINK, CREAM, (190, 170, 240))
        for i in range(1, 17):
            bx, by = pts[int(i / 17 * 40)]
            self.bulbs.append((bx, by + 6, cols[i % 4], rnd.uniform(0, 6.28)))

    # ---------- dynamic ----------
    def draw(self, surf, t):
        surf.blit(self.sky, (0, 0))
        sl = smooth(prog(t, 0.0, 3.0))
        for x, y, r, ph, sp, spark in self.stars:
            tw = 0.5 + 0.5 * math.sin(t * sp + ph)
            a = int(255 * sl * (0.25 + 0.75 * tw))
            if a < 8:
                continue
            img = self.star_spark if (spark and r >= 2) else self.star_dots[r]
            img.set_alpha(a)
            surf.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2))
        ml = smooth(prog(t, 0.3, 2.8))
        if ml > 0.01:
            mx, my = self.MOON
            halo = glow_surface(150, (255, 226, 190), 0.5)
            halo.set_alpha(int(255 * ml * (0.8 + 0.2 * math.sin(t * 1.2))))
            surf.blit(halo, (mx - 150, my - 150))
            self.moon.set_alpha(int(255 * ml))
            surf.blit(self.moon, (mx - 60, my - 60))
        for x0, y, sp, img in self.clouds:
            surf.blit(img, (((x0 + t * sp) % (W + 500)) - 330, y))
        surf.blit(self.city, (0, 0))

        # lamp turn-on with flicker
        lt = prog(t, 1.0, 2.8)
        lvl = smooth(lt)
        if lt < 0.85:
            lvl *= 1.0 if math.sin(t * 53) * math.sin(t * 37) > 0.15 else 0.45
        else:
            lvl *= 0.96 + 0.04 * math.sin(t * 3)
        self.lamp_level = lvl
        if lvl > 0.01:
            for lx, s in self.LAMPS:
                hx, hy = lx + s * 34, 336
                halo = glow_surface(175, AMBER, 0.62)
                halo.set_alpha(int(255 * lvl))
                surf.blit(halo, (hx - 175, hy - 175))
                self.lamp_cone.set_alpha(int(255 * lvl))
                surf.blit(self.lamp_cone, (hx - 170, hy))
                self.lamp_pool.set_alpha(int(255 * lvl))
                surf.blit(self.lamp_pool, (hx - 170, 566))
                core = glow_surface(20, (255, 242, 210), 1.0)
                core.set_alpha(int(255 * lvl))
                surf.blit(core, (hx - 20, hy - 6))
            for bx, by, col, ph in self.bulbs:
                g = glow_surface(15, col, 0.9)
                g.set_alpha(int(255 * lvl * (0.65 + 0.35 * math.sin(t * 2.4 + ph))))
                surf.blit(g, (bx - 15, by - 15))
                pygame.draw.circle(surf, mix(col, (255, 255, 255), 0.5), (int(bx), int(by)), 3)

        for img, x, y, t0, ph in self.doodles:
            a = smooth(prog(t, t0, t0 + 1.6))
            if a <= 0.01:
                continue
            img.set_alpha(int(215 * a))
            surf.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2 + math.sin(t * 1.1 + ph) * 5 + (1 - a) * 12))
        self._draw_cat(surf, t)

    def _draw_cat(self, surf, t):
        x, y = 1212, 612
        col = (26, 20, 48)
        pts = []
        for i in range(9):
            k = i / 8
            pts.append((x + 14 + k * 30 + math.sin(t * 2.4 - k * 3) * 7 * k, y - 8 - math.sin(k * math.pi * 0.85) * 40))
        for p in pts:
            pygame.draw.circle(surf, col, (int(p[0]), int(p[1])), 4)
        pygame.draw.ellipse(surf, col, (x - 19, y - 46, 38, 50))
        pygame.draw.circle(surf, col, (x, y - 58), 16)
        pygame.draw.polygon(surf, col, [(x - 14, y - 66), (x - 10, y - 84), (x - 2, y - 70)])
        pygame.draw.polygon(surf, col, [(x + 14, y - 66), (x + 10, y - 84), (x + 2, y - 70)])
        blink = (t % 4.0) < 0.12
        for ex in (-6, 6):
            if blink:
                pygame.draw.line(surf, AMBER, (x + ex - 3, y - 58), (x + ex + 3, y - 58), 2)
            else:
                pygame.draw.circle(surf, AMBER, (x + ex, y - 58), 3)
        pygame.draw.ellipse(surf, (40, 32, 66), (x - 12, y - 8, 10, 8))
        pygame.draw.ellipse(surf, (40, 32, 66), (x + 2, y - 8, 10, 8))


# ----------------------------------------------------------------------------
# SKATEBOARD
# ----------------------------------------------------------------------------
class Skateboard:
    WHEEL_R = 10

    def __init__(self, x, y, deck, stripe, wheel):
        self.x, self.y = x, y
        self.deck, self.stripe, self.wheel = deck, stripe, wheel
        self.prev_x = x
        self.vx = 0.0
        self.rot = 0.0
        self.tilt = 0.0     # derajat, positif = berputar CCW (visual)

    def update(self, dt):
        if dt > 0:
            self.vx = lerp(self.vx, (self.x - self.prev_x) / dt, min(1.0, dt * 14))
            self.rot += self.vx * dt / self.WHEEL_R
        self.prev_x = self.x

    def _p(self, lx, ly):
        a = math.radians(self.tilt)
        rx, ry = lx, ly + 14
        return (self.x + rx * math.cos(a) + ry * math.sin(a),
                self.y - 14 - rx * math.sin(a) + ry * math.cos(a))

    def draw(self, surf):
        P = self._p
        top = [(-72, -40), (-62, -33), (62, -33), (72, -40)]
        bot = [(70, -34), (60, -26), (-60, -26), (-70, -34)]
        poly = [P(*p) for p in top + bot]
        pygame.draw.polygon(surf, self.deck, poly)
        pygame.draw.polygon(surf, OUTLINE, poly, 3)
        pygame.draw.line(surf, self.stripe, P(-44, -29), P(44, -29), 3)
        pygame.draw.lines(surf, (60, 48, 78), False, [P(*p) for p in top], 3)
        for sx in (-40, 40):
            tr = [P(sx - 7, -26), P(sx + 7, -26), P(sx + 5, -18), P(sx - 5, -18)]
            pygame.draw.polygon(surf, (150, 140, 176), tr)
            pygame.draw.polygon(surf, OUTLINE, tr, 2)
            cx, cy = P(sx, -10)
            r = self.WHEEL_R
            pygame.draw.circle(surf, OUTLINE, (int(cx), int(cy)), r + 2)
            pygame.draw.circle(surf, self.wheel, (int(cx), int(cy)), r)
            for k in range(3):
                a = self.rot + k * math.tau / 3
                pygame.draw.line(surf, mix(self.wheel, (60, 40, 80), 0.55), (cx, cy), (cx + math.cos(a) * (r - 2), cy + math.sin(a) * (r - 2)), 2)
            pygame.draw.circle(surf, OUTLINE, (int(cx + math.cos(self.rot) * 6), int(cy + math.sin(self.rot) * 6)), 2)
            pygame.draw.circle(surf, OUTLINE, (int(cx), int(cy)), 3)


# ----------------------------------------------------------------------------
# CHARACTER
# ----------------------------------------------------------------------------
GIRL_PAL = dict(top=(214, 150, 172), top_dark=(174, 108, 136), pants=(238, 226, 204), pants_dark=(190, 178, 160),
                shoe=CREAM, accent=(214, 120, 150), hair=(62, 38, 74), hair_hi=(108, 72, 124))
BOY_PAL = dict(top=(232, 166, 86), top_dark=(194, 124, 58), tee=CREAM, pants=(112, 122, 188), pants_dark=(80, 88, 146),
               shoe=CREAM, accent=(228, 152, 72), hair=(92, 60, 50), cap=(40, 48, 112), cap_dark=(26, 32, 84))


class Character:
    ARM = (36, 34)

    def __init__(self, name, facing, pal, x, y, is_girl):
        self.name, self.dir, self.p, self.is_girl = name, facing, pal, is_girl
        self.x, self.y = x, y
        self.prev_x = x
        self.vx = 0.0
        self.speed = 0.0
        self.lean = 0.0
        self.stance = 0.0      # 0 = di atas papan, 1 = berdiri di tanah
        self.hop = 0.0
        self.turn = 0.35       # 0 = hadap kamera, 1 = menoleh ke pasangan
        self.expr = "shy"
        self.blush = 0.45
        self.wink = 0.0
        self.sway = 0.0
        self.head_tilt = 0.0
        self.carry = False     # laki-laki: memegang buket di tangan dalam
        self.hands_clasped = False
        self.t = random.random() * 10
        self.blink_cd = random.uniform(1.5, 3.5)
        self.blink = 0.0
        self.breath = 0.0
        self.torso_dx = 0.0
        self.head_dx = 0.0
        self.hand_targets = {"inner": None, "outer": None}
        self.hand_pos = {"inner": None, "outer": None}
        self.arm = {}
        self.hand_draw = {"inner": (x, y), "outer": (x, y)}

    # ---------- geometry ----------
    def base_y(self):
        return self.y - BOARD_LIFT * (1 - self.stance) - self.hop

    def head_top(self):
        return self.base_y() - (238 if self.is_girl else 258)

    def shoulder(self, side):
        s = self.dir if side == "inner" else -self.dir
        return (self.x + s * 36 + self.torso_dx, self.base_y() - 112)

    def idle_hand(self, side, hold=None):
        hold = self.carry if hold is None else hold
        s = self.dir if side == "inner" else -self.dir
        S = self.shoulder(side)
        sw = math.sin(self.t * 2.0 + (0.0 if side == "inner" else 1.7))
        if hold and side == "inner":
            return (S[0] + s * 28, S[1] + 58 + sw * 2)
        return (S[0] + s * (16 + 22 * self.speed), S[1] + 54 - 14 * self.speed + sw * 3)

    # ---------- update ----------
    def update(self, dt):
        self.t += dt
        if dt > 0:
            self.vx = lerp(self.vx, (self.x - self.prev_x) / dt, min(1.0, dt * 12))
        self.prev_x = self.x
        self.speed = clamp(abs(self.vx) / 500)
        self.lean = clamp(self.vx / 600, -1, 1)
        self.breath = math.sin(self.t * 2.3) * 1.5 * (1 - self.speed * 0.7)
        self.torso_dx = self.lean * 12 + self.sway
        self.head_dx = self.lean * 22 + self.sway * 1.6 + self.dir * self.head_tilt * 7
        self.blink_cd -= dt
        if self.blink_cd <= 0:
            self.blink = 0.13
            self.blink_cd = random.uniform(2.0, 4.5)
        if self.blink > 0:
            self.blink -= dt
        for side in ("inner", "outer"):
            S = self.shoulder(side)
            S = (S[0], S[1] + self.breath)
            tgt = self.hand_targets[side] or self.idle_hand(side)
            cur = self.hand_pos[side] or tgt
            k = min(1.0, dt * 22)
            cur = (cur[0] + (tgt[0] - cur[0]) * k, cur[1] + (tgt[1] - cur[1]) * k)
            self.hand_pos[side] = cur
            s = self.dir if side == "inner" else -self.dir
            E, Hd = arm_ik(S, cur, self.ARM[0], self.ARM[1], s)
            self.arm[side] = (S, E, Hd)
            self.hand_draw[side] = Hd

    # ---------- drawing ----------
    def draw(self, surf):
        by = self.base_y() + self.breath
        self._draw_legs(surf, by)
        self._draw_arm(surf, "outer")
        self._draw_torso(surf, by)
        self._draw_arm(surf, "inner")
        self._draw_head(surf, by)

    def _draw_legs(self, surf, by):
        d, p, x, tdx = self.dir, self.p, self.x, self.torso_dx
        ff, fb = lerp(26, 18, self.stance), lerp(22, 18, self.stance)
        lx, rx = (x - fb, x + ff) if d > 0 else (x - ff, x + fb)
        top = by - 58
        flutter = math.sin(self.t * 9) * self.speed * 3
        for fx, a0, a1 in ((lx, x - 34, x - 2), (rx, x + 2, x + 34)):
            pts = [(a0 + tdx * 0.5, top), (a1 + tdx * 0.5, top), (fx + 18 + flutter, by - 12), (fx - 18 + flutter, by - 12)]
            pygame.draw.polygon(surf, p["pants"], pts)
            pygame.draw.polygon(surf, OUTLINE, pts, 3)
            pygame.draw.line(surf, p["pants_dark"], (fx - 17 + flutter, by - 17), (fx + 17 + flutter, by - 17), 3)
            pygame.draw.line(surf, p["pants_dark"], ((a0 + a1) / 2 + tdx * 0.5, top + 6), ((fx + flutter), by - 22), 2)
        for fx in (lx, rx):
            cx, cy = fx + d * 5, by - 9
            pygame.draw.ellipse(surf, (236, 226, 208), (cx - 22, cy - 2, 44, 15))
            pygame.draw.ellipse(surf, p["shoe"], (cx - 20, cy - 12, 40, 18))
            pygame.draw.circle(surf, p["accent"], (int(cx + d * 12), int(cy - 3)), 6)
            pygame.draw.line(surf, p["accent"], (cx - d * 6, cy - 9), (cx + d * 2, cy - 8), 2)
            pygame.draw.ellipse(surf, OUTLINE, (cx - 20, cy - 12, 40, 18), 3)
            pygame.draw.ellipse(surf, OUTLINE, (cx - 22, cy - 2, 44, 15), 3)
            pygame.draw.ellipse(surf, p["shoe"], (cx - 18, cy - 10, 36, 14))

    def _draw_arm(self, surf, side):
        S, E, Hd = self.arm[side]
        draw_limb(surf, [S, E, Hd], 20, self.p["top"], OUTLINE)
        pygame.draw.circle(surf, OUTLINE, (int(Hd[0]), int(Hd[1])), 11)
        pygame.draw.circle(surf, SKIN, (int(Hd[0]), int(Hd[1])), 8)

    def _draw_torso(self, surf, by):
        p, x, tdx = self.p, self.x, self.torso_dx
        tl, tt = x + tdx - 41, by - 122
        flap = -self.lean * 7 + math.sin(self.t * 8) * self.speed * 3
        if self.is_girl:
            pygame.draw.ellipse(surf, p["top_dark"], (x + tdx - 44, tt - 10, 88, 36))
            pygame.draw.ellipse(surf, OUTLINE, (x + tdx - 44, tt - 10, 88, 36), 3)
        rect = pygame.Rect(int(tl), int(tt), 82, 70)
        pygame.draw.rect(surf, p["top"], rect, 0, border_radius=22)
        pygame.draw.rect(surf, OUTLINE, rect, 3, border_radius=22)
        if self.is_girl:
            pygame.draw.rect(surf, p["top_dark"], (tl + 15, tt + 38, 52, 22), 0, border_radius=10)
            pygame.draw.rect(surf, OUTLINE, (tl + 15, tt + 38, 52, 22), 2, border_radius=10)
            for sx in (-9, 9):
                pygame.draw.line(surf, CREAM, (x + tdx + sx, tt + 6), (x + tdx + sx * 1.2, tt + 28), 3)
                pygame.draw.circle(surf, CREAM, (int(x + tdx + sx * 1.2), int(tt + 30)), 3)
            surf.blit(make_sprite("heart", CREAM, 20), (x + tdx - 10 + 22, tt + 16))
        else:
            pygame.draw.ellipse(surf, p["tee"], (x + tdx - 18, tt - 3, 36, 24))
            pygame.draw.ellipse(surf, OUTLINE, (x + tdx - 18, tt - 3, 36, 24), 2)
            pygame.draw.line(surf, p["top_dark"], (x + tdx, tt + 14), (x + tdx, tt + 68), 3)
            pygame.draw.polygon(surf, p["top_dark"], [(x + tdx - 20, tt + 2), (x + tdx - 4, tt + 20), (x + tdx - 24, tt + 22)])
            pygame.draw.polygon(surf, p["top_dark"], [(x + tdx + 20, tt + 2), (x + tdx + 4, tt + 20), (x + tdx + 24, tt + 22)])
            surf.blit(make_sprite("star", CREAM, 20), (tl + 52, tt + 22))
        pygame.draw.rect(surf, p["top_dark"], (tl + 2 + flap, tt + 58, 78, 14), 0, border_radius=6)
        pygame.draw.rect(surf, OUTLINE, (tl + 2 + flap, tt + 58, 78, 14), 2, border_radius=6)

    # ----- face -----
    def _draw_eyes(self, surf, fx, ey):
        d, t = self.dir, self.turn
        sep = 20 * (1 - 0.18 * t)
        for sgn in (-1, 1):
            ex = fx + sgn * sep
            closed = self.expr == "happy"
            winking = self.wink > 0.5 and sgn == -d
            if closed or winking:
                pygame.draw.arc(surf, INK, (ex - 10, ey - 7, 20, 16), 0.45, math.pi - 0.45, 4)
            elif self.blink > 0:
                pygame.draw.line(surf, INK, (ex - 8, ey), (ex + 8, ey), 3)
            else:
                oy = 2 if self.expr == "shy" else 0
                pygame.draw.ellipse(surf, INK, (ex - 7, ey - 10 + oy, 14, 20))
                pygame.draw.circle(surf, (255, 255, 255), (int(ex - 2), int(ey - 4 + oy)), 4)
                pygame.draw.circle(surf, (255, 255, 255), (int(ex + 3), int(ey + 4 + oy)), 2)
            if self.is_girl and not closed:
                pygame.draw.line(surf, INK, (ex + sgn * 7, ey - 6), (ex + sgn * 12, ey - 10), 2)
            by_ = ey - 20
            raise_ = 4 if self.expr == "shy" else 0
            if not self.is_girl and self.expr == "playful" and sgn == d:
                by_ -= 4
            col = self.p["hair"]
            pygame.draw.line(surf, col, (ex + sgn * 9, by_ + 2), (ex - sgn * 8, by_ - 2 - raise_), 3)

    def _draw_mouth(self, surf, mx, my):
        e = self.expr
        if e == "shy":
            pygame.draw.arc(surf, INK, (mx - 7, my - 6, 14, 10), math.pi + 0.5, 2 * math.pi - 0.5, 3)
        elif e == "sweet":
            pygame.draw.arc(surf, INK, (mx - 9, my - 8, 18, 13), math.pi + 0.4, 2 * math.pi - 0.4, 3)
        else:
            rx, ry = (11, 9) if e == "playful" else (9, 8)
            pts = [(mx + rx * math.cos(a * math.pi / 10), my - 2 + ry * math.sin(a * math.pi / 10)) for a in range(11)]
            pygame.draw.polygon(surf, (140, 56, 82), pts)
            pygame.draw.circle(surf, (240, 120, 140), (int(mx + 1), int(my + ry - 6)), 4)
            pygame.draw.polygon(surf, INK, pts, 2)

    def _draw_head(self, surf, by):
        d, p, t = self.dir, self.p, self.turn
        hx = self.x + self.head_dx
        hy = by - 176 + math.sin(self.t * 2.3 + 1.0) * 1.2
        fx = hx + d * t * 13
        ey = hy + 8
        flow = -self.lean * 12 + math.sin(self.t * 7) * self.speed * 3
        if self.is_girl:
            R = 62
            pts = [(hx + math.cos(math.pi + i * math.pi / 16) * R, hy - 4 + math.sin(math.pi + i * math.pi / 16) * (R + 2)) for i in range(17)]
            pts += [(hx + R + 3 + flow * 0.6, hy + 30), (hx + R - 2 + flow, hy + 56), (hx + 30 + flow, hy + 61),
                    (hx + flow, hy + 58), (hx - 30 + flow, hy + 61), (hx - R + 2 + flow, hy + 56), (hx - R - 3 + flow * 0.6, hy + 30)]
            pygame.draw.polygon(surf, p["hair"], pts)
            pygame.draw.polygon(surf, OUTLINE, pts, 3)
        else:
            pygame.draw.ellipse(surf, p["hair"], (hx - 58, hy - 44, 116, 94))
            for sx in (-57, 57):
                pygame.draw.circle(surf, OUTLINE, (int(hx + sx), int(hy + 10)), 11)
                pygame.draw.circle(surf, SKIN, (int(hx + sx), int(hy + 10)), 8)
        face = (hx - 58, hy - 54, 116, 108)
        pygame.draw.ellipse(surf, SKIN, face)
        pygame.draw.ellipse(surf, OUTLINE, face, 3)
        # pipi
        bl = blush_sprite()
        bl.set_alpha(int(255 * clamp(self.blush)))
        for sgn in (-1, 1):
            surf.blit(bl, (fx + sgn * 33 - 23, ey + 12))
        self._draw_eyes(surf, fx, ey)
        pygame.draw.arc(surf, (214, 160, 140), (fx + d * t * 4 - 4, ey + 10, 8, 6), math.pi + 0.5, 2 * math.pi - 0.5, 2)
        self._draw_mouth(surf, fx + d * t * 2, ey + 25)

        if self.is_girl:
            # rambut depan: poni + sisi
            for sgn in (-1, 1):
                lock = [(hx + sgn * 63, hy - 8), (hx + sgn * 42, hy - 16), (hx + sgn * 45, hy + 22 + flow * 0.2),
                        (hx + sgn * 55 + flow * 0.5, hy + 54), (hx + sgn * 63 + flow * 0.6, hy + 30)]
                pygame.draw.polygon(surf, p["hair"], lock)
                pygame.draw.polygon(surf, OUTLINE, lock, 3)
            R = 60
            bangs = [(hx + math.cos(math.pi + i * math.pi / 16) * R, hy + math.sin(math.pi + i * math.pi / 16) * (R + 4) - 2) for i in range(17)]
            bangs += [(hx + R, hy + 4), (hx + 38, hy - 22), (hx + 24, hy - 12), (hx + 8, hy - 26), (hx - 10, hy - 14),
                      (hx - 26, hy - 26), (hx - 42, hy - 12), (hx - R, hy + 4)]
            pygame.draw.polygon(surf, p["hair"], bangs)
            pygame.draw.polygon(surf, OUTLINE, bangs, 3)
            pygame.draw.arc(surf, p["hair_hi"], (hx - 44, hy - 62, 88, 50), 0.7, 2.3, 4)
            surf.blit(make_sprite("star", AMBER, 24), (hx - d * 38 - 12, hy - 42))
        else:
            cy = hy - 18
            crown = [(hx + math.cos(math.pi + i * math.pi / 16) * 61, cy + math.sin(math.pi + i * math.pi / 16) * 62) for i in range(17)]
            crown += [(hx + 30, cy + 3), (hx, cy + 5), (hx - 30, cy + 3)]
            pygame.draw.polygon(surf, p["cap"], crown)
            pygame.draw.polygon(surf, OUTLINE, crown, 3)
            seam = hx + d * t * 18
            pygame.draw.arc(surf, p["cap_dark"], (seam - 26, cy - 62, 52, 66), math.pi / 2 - 0.3, math.pi * 1.5 + 0.3, 3)
            pygame.draw.circle(surf, CREAM, (int(seam + d * 12), int(cy - 28)), 8)
            pygame.draw.polygon(surf, AMBER, star_points(seam + d * 12, cy - 28, 6, 2.6))
            bx = hx + d * (26 + 24 * t)
            pygame.draw.ellipse(surf, p["cap_dark"], (bx - 33, cy - 8, 66, 16))
            pygame.draw.ellipse(surf, OUTLINE, (bx - 33, cy - 8, 66, 16), 3)


# ----------------------------------------------------------------------------
# BOUQUET
# ----------------------------------------------------------------------------
def build_bouquet_sprite():
    s = pygame.Surface((150, 190), pygame.SRCALPHA)
    base = (75, 170)
    dgreen, green = (58, 112, 98), (88, 156, 122)
    tips = [(38, 62), (75, 38), (112, 62), (56, 88), (94, 88)]
    for tx, ty in tips:
        pygame.draw.line(s, dgreen, base, (tx, ty + 10), 4)
    pygame.draw.ellipse(s, green, (16, 96, 34, 15))
    pygame.draw.ellipse(s, green, (100, 96, 34, 15))
    cols = [HOT_PINK, AMBER, CREAM, (190, 170, 240), PINK_SOFT]
    for (tx, ty), col in zip(tips, cols):
        for i in range(5):
            a = i * math.tau / 5 - math.pi / 2
            pygame.draw.circle(s, OUTLINE, (int(tx + math.cos(a) * 11), int(ty + math.sin(a) * 11)), 13)
        for i in range(5):
            a = i * math.tau / 5 - math.pi / 2
            pygame.draw.circle(s, col, (int(tx + math.cos(a) * 11), int(ty + math.sin(a) * 11)), 11)
        pygame.draw.circle(s, AMBER if col != AMBER else HOT_PINK, (tx, ty), 6)
    for dx, dy in ((26, 40), (126, 44), (70, 14), (50, 114), (100, 112), (14, 76), (136, 78)):
        pygame.draw.circle(s, CREAM, (dx, dy), 4)
    cone = [(75, 178), (28, 110), (122, 110)]
    pygame.draw.polygon(s, CREAM, cone)
    pygame.draw.polygon(s, OUTLINE, cone, 3)
    fold = [(75, 178), (52, 110), (98, 110)]
    pygame.draw.polygon(s, DUSTY_PINK, fold)
    pygame.draw.polygon(s, OUTLINE, fold, 3)
    pygame.draw.ellipse(s, AMBER, (46, 120, 28, 16))
    pygame.draw.ellipse(s, AMBER, (76, 120, 28, 16))
    pygame.draw.circle(s, AMBER_DEEP, (75, 128), 6)
    return pygame.transform.smoothscale(s, (117, 148))


class Bouquet:
    PIVOT = (58.5, 132.6)

    def __init__(self):
        self.sprite = build_bouquet_sprite()
        self.hand = (-300.0, 0.0)
        self.tilt = 14.0
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        ang = self.tilt + math.sin(self.t * 2.3) * 3
        a = math.radians(ang)
        img = pygame.transform.rotozoom(self.sprite, ang, 1.0)
        vx, vy = self.sprite.get_width() / 2 - self.PIVOT[0], self.sprite.get_height() / 2 - self.PIVOT[1]
        rx = vx * math.cos(a) + vy * math.sin(a)
        ry = -vx * math.sin(a) + vy * math.cos(a)
        px, py = self.hand[0], self.hand[1] + 8
        surf.blit(img, img.get_rect(center=(px + rx, py + ry)))
        pygame.draw.circle(surf, OUTLINE, (int(self.hand[0]), int(self.hand[1])), 11)
        pygame.draw.circle(surf, SKIN, (int(self.hand[0]), int(self.hand[1])), 8)


# ----------------------------------------------------------------------------
# SPEECH BUBBLE
# ----------------------------------------------------------------------------
class SpeechBubble:
    def __init__(self, text, width=380, tail_frac=0.5, font_size=32):
        self.state, self.age, self.anchor = "hidden", 0.0, (0, 0)
        font = get_font(font_size)
        lines, cur = [], ""
        for word in text.split(" "):
            test = (cur + " " + word).strip()
            if font.size(test)[0] <= width - 52 or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
        lh = font.get_linesize()
        h = len(lines) * lh + 38
        pad, tail_h = 10, 32
        self.surf = pygame.Surface((width + pad * 2, h + tail_h + pad * 2), pygame.SRCALPHA)
        s = self.surf
        body = pygame.Rect(pad, pad, width, h)
        pygame.draw.rect(s, DUSTY_PINK, body.move(5, 6), 0, border_radius=28)
        pygame.draw.rect(s, CREAM, body, 0, border_radius=28)
        pygame.draw.rect(s, OUTLINE, body, 4, border_radius=28)
        tx = pad + int(width * tail_frac)
        tip = (tx + 2, body.bottom + tail_h - 2)
        tail = [(tx - 17, body.bottom - 3), (tx + 19, body.bottom - 3), tip]
        pygame.draw.polygon(s, CREAM, tail)
        pygame.draw.line(s, OUTLINE, (tx - 17, body.bottom - 2), tip, 4)
        pygame.draw.line(s, OUTLINE, (tx + 19, body.bottom - 2), tip, 4)
        pygame.draw.line(s, CREAM, (tx - 14, body.bottom - 2), (tx + 16, body.bottom - 2), 6)
        for i, ln in enumerate(lines):
            img = font.render(ln, True, INK)
            s.blit(img, img.get_rect(center=(body.centerx, body.top + 19 + lh / 2 + i * lh)))
        s.blit(make_sprite("heart", HOT_PINK, 30), (body.right - 24, body.top - 14))
        s.blit(make_sprite("sparkle", AMBER, 22), (body.left - 8, body.top - 8))
        self.tip = tip
        self.body_center = body.center

    def show(self):
        self.state, self.age = "in", 0.0

    def hide(self):
        if self.state in ("in", "shown"):
            self.state, self.age = "out", 0.0

    def update(self, dt):
        self.age += dt

    def center(self):
        return (self.anchor[0] - self.tip[0] + self.body_center[0], self.anchor[1] - self.tip[1] + self.body_center[1])

    def draw(self, surf):
        if self.state == "hidden":
            return
        wob = 0.0
        if self.state == "in":
            p = self.age / 0.6
            s = ease_out_back(p, 2.6)
            wob = math.sin(self.age * 20) * 0.07 * math.exp(-self.age * 4.5)
            if p >= 1:
                self.state = "shown"
        elif self.state == "out":
            p = self.age / 0.3
            s = 1 - ease_in_cubic(p)
            if p >= 1:
                self.state = "hidden"
                return
        if self.state == "shown":
            s = 1.0 + math.sin(self.age * 2.4) * 0.008
        sx, sy = max(0.02, s * (1 + wob)), max(0.02, s * (1 - wob))
        w, h = self.surf.get_size()
        img = pygame.transform.smoothscale(self.surf, (max(2, int(w * sx)), max(2, int(h * sy))))
        bob = math.sin(self.age * 2.0) * 3 if self.state == "shown" else 0
        surf.blit(img, (self.anchor[0] - self.tip[0] * sx, self.anchor[1] - self.tip[1] * sy + bob))


# ----------------------------------------------------------------------------
# SCENES
# ----------------------------------------------------------------------------
class Scene:
    duration = 1.0

    def __init__(self, am):
        self.am = am
        self.events = set()

    def enter(self):
        self.events.clear()

    def once(self, name, cond):
        if cond and name not in self.events:
            self.events.add(name)
            return True
        return False

    def update(self, lt, dt):
        pass

    def draw_overlay(self, screen, lt):
        pass


class OpeningScene(Scene):
    """SCENE 1 - kota malam, lampu menyala, doodle muncul, judul fade-in."""
    duration = 7.0

    def enter(self):
        super().enter()
        self.am.cam_target = (1.10, 640, 330)
        self.am.cam = list(self.am.cam_target)

    def update(self, lt, dt):
        am = self.am
        p = prog(lt, 0, 7)
        am.cam_target = (lerp(1.10, 1.03, smooth(p)), 640, lerp(330, 370, p))
        am.fade = 255 * (1 - smooth(prog(lt, 0, 1.6)))
        if self.once("twinkle", lt > 3.0):
            am.burst(640, 260, 10, 260, ("sparkle", "star"))

    def draw_overlay(self, screen, lt):
        am = self.am
        out = 1 - smooth(prog(lt, 6.1, 6.95))
        for i, (img, x, y) in enumerate(am.title_letters):
            p = prog(lt, 2.4 + i * 0.17, 3.5 + i * 0.17)
            a = smooth(p) * out
            if a <= 0.01:
                continue
            img.set_alpha(int(255 * a))
            screen.blit(img, (x, y + (1 - ease_out_back(p)) * 46))
        p = prog(lt, 4.5, 5.9)
        a = smooth(p) * out
        if a > 0.01:
            am.subtitle.set_alpha(int(255 * a))
            screen.blit(am.subtitle, am.subtitle.get_rect(center=(W // 2, 428 + (1 - p) * 12)))


class EntranceScene(Scene):
    """SCENE 2 - dua karakter meluncur dari kiri & kanan, berhenti di tengah."""
    duration = 8.0

    def update(self, lt, dt):
        am = self.am
        e = ease_out_cubic(prog(lt, 0.2, 7.4))
        am.girl.x = lerp(GIRL_X0, GIRL_X1, e)
        am.boy.x = lerp(BOY_X0, BOY_X1, e)
        am.girl_board.x, am.boy_board.x = am.girl.x, am.boy.x
        am.girl.turn = am.boy.turn = 0.35
        am.girl.expr, am.boy.expr = "shy", "playful"
        p = prog(lt, 0, 8)
        am.cam_target = (lerp(1.03, 1.0, smooth(p)), 640, lerp(370, 400, p))


class BoyDialogueScene(Scene):
    """SCENE 3 - speech bubble laki-laki."""
    duration = 5.6

    def update(self, lt, dt):
        am = self.am
        g, b = am.girl, am.boy
        b.turn = lerp(0.35, 1.0, smooth(prog(lt, 0.2, 1.0)))
        g.blush = lerp(0.45, 0.8, smooth(prog(lt, 0.8, 3.5)))
        g.turn = lerp(0.35, 0.5, smooth(prog(lt, 3.0, 4.2)))
        b.wink = math.sin(math.pi * prog(lt, 2.4, 2.9))
        if self.once("pop", lt >= 0.5):
            am.boy_bubble.show()
            am.burst(am.boy_bubble.anchor[0], am.boy_bubble.anchor[1] - 90, 4, 150, ("heart",))
        if lt > 1.0:
            am.bubble_hearts(am.boy_bubble, dt, 3.0)
        p = prog(lt, 0, 5.6)
        am.cam_target = (lerp(1.0, 1.05, smooth(p)), 640, lerp(400, 410, p))


class GirlResponseScene(Scene):
    """SCENE 4 - speech bubble perempuan."""
    duration = 5.2

    def update(self, lt, dt):
        am = self.am
        g, b = am.girl, am.boy
        b.turn = 1.0
        b.wink = 0.0
        b.expr = "sweet" if lt > 1.0 else "playful"
        if self.once("hide_boy", lt >= 0.15):
            am.boy_bubble.hide()
        if self.once("pop", lt >= 0.8):
            am.girl_bubble.show()
        g.turn = lerp(0.5, 1.0, smooth(prog(lt, 0.8, 1.5)))
        if lt >= 1.7:
            g.expr = "happy"
        g.blush = lerp(0.8, 1.0, smooth(prog(lt, 1.0, 2.4)))
        for i, tm in enumerate((1.9, 2.5, 3.1)):
            if self.once("burst%d" % i, lt >= tm):
                am.burst(640, GROUND_Y - 190, 7, 220)
        if lt > 1.2:
            am.bubble_hearts(am.girl_bubble, dt, 3.0)
        p = prog(lt, 0, 5.2)
        am.cam_target = (lerp(1.05, 1.08, smooth(p)), 640, lerp(410, 410, p))


class SweetMomentScene(Scene):
    """SCENE 5 - turun skateboard, kasih buket, bergandengan tangan."""
    duration = 11.5
    CLASP_T = 6.3

    def update(self, lt, dt):
        am = self.am
        g, b = am.girl, am.boy
        am.cam_target = (lerp(1.08, 1.22, ease_in_out_sine(prog(lt, 0, 11.5))), 640,
                         lerp(410, 470, smooth(prog(lt, 0, 8))))
        if self.once("hide_girl", lt >= 0.3):
            am.girl_bubble.hide()

        # --- turun dari papan ---
        for ch, bd, x1 in ((g, am.girl_board, GIRL_X1), (b, am.boy_board, BOY_X1)):
            p = prog(lt, 0.3, 1.9)
            ch.x = lerp(x1, x1 + ch.dir * 35, ease_in_out_sine(p))
            ch.hop = math.sin(math.pi * p) * 26
            ch.stance = smooth(prog(lt, 0.55, 1.5))
            bd.x = lerp(x1, x1 - ch.dir * 50, ease_out_cubic(prog(lt, 0.45, 3.0)))
            bd.tilt = -ch.dir * math.sin(math.pi * prog(lt, 0.35, 1.7)) * 9
        g.turn = b.turn = 1.0
        g.expr, b.expr = "happy", "sweet"
        g.blush = 1.0
        b.blush = lerp(0.35, 0.8, smooth(prog(lt, 2.5, 6)))

        # --- posisi tangan ---
        gS, bS = g.shoulder("inner"), b.shoulder("inner")
        M = ((gS[0] + bS[0]) / 2, gS[1] + 36)
        bi_hold, bi_free = b.idle_hand("inner", True), b.idle_hand("inner", False)
        gi_idle, go_idle = g.idle_hand("inner"), g.idle_hand("outer")

        O_b = (M[0] + 14, M[1] - 4)
        if lt < 5.4:
            tgt = lerp2(bi_hold, O_b, smooth(prog(lt, 2.3, 3.3)))
            b_t = lerp2(tgt, bi_free, smooth(prog(lt, 4.0, 5.0)))
        else:
            b_t = lerp2(bi_free, M, smooth(prog(lt, 5.4, 6.3)))

        G_reach = (M[0] - 10, M[1] + 4)
        P_swap = (g.x - 10, GROUND_Y - 60)
        if lt < 4.2:
            g_t = lerp2(gi_idle, G_reach, smooth(prog(lt, 2.8, 3.6)))
        elif lt < 5.3:
            g_t = lerp2(G_reach, P_swap, smooth(prog(lt, 4.2, 5.0)))
        else:
            g_t = lerp2(P_swap, M, smooth(prog(lt, 5.3, 6.3)))

        Q_out = (g.shoulder("outer")[0] - 4, GROUND_Y - 66)
        if lt < 4.4:
            o_t = go_idle
        elif lt < 5.0:
            o_t = lerp2(go_idle, P_swap, smooth(prog(lt, 4.4, 5.0)))
        else:
            o_t = lerp2(P_swap, Q_out, smooth(prog(lt, 5.0, 5.7)))

        b.hand_targets["inner"] = b_t
        b.hand_targets["outer"] = None
        g.hand_targets["inner"] = g_t
        g.hand_targets["outer"] = o_t
        b.carry = lt < 4.2

        # --- buket ---
        if lt < 3.6:
            am.bouquet_mode = ("boy",)
        elif lt < 4.2:
            am.bouquet_mode = ("xfer", smooth(prog(lt, 3.6, 4.2)))
        elif lt < 4.9:
            am.bouquet_mode = ("girl_in",)
        elif lt < 5.2:
            am.bouquet_mode = ("xfer2", smooth(prog(lt, 4.9, 5.2)))
        else:
            am.bouquet_mode = ("girl_out",)
        base_in = -b.dir * 14
        if lt < 2.3:
            tilt = base_in
        elif lt < 3.3:
            tilt = lerp(base_in, 0, smooth(prog(lt, 2.3, 3.3)))
        elif lt < 4.2:
            tilt = 0.0
        else:
            tilt = lerp(0.0, g.dir * 16, smooth(prog(lt, 4.2, 5.7)))
        am.bouquet.tilt = tilt

        # --- bergandengan tangan ---
        clasped = lt >= self.CLASP_T
        g.hands_clasped = b.hands_clasped = clasped
        if self.once("clasp", clasped):
            am.burst(M[0], M[1] - 30, 9, 120, ("heart", "sparkle", "star"))
        sw = smooth(prog(lt, 6.3, 7.5))
        g.sway = math.sin(lt * 1.7) * 3 * sw
        b.sway = math.sin(lt * 1.7) * 3 * sw
        g.head_tilt = b.head_tilt = sw
        if lt > 2.2:
            am.float_fx(640, GROUND_Y - 150, 140, 1.6 if lt < 6.3 else 4.5, dt)


class EndingScene(Scene):
    """SCENE 6 - slow zoom-out, teks penutup."""
    duration = 10.0

    def update(self, lt, dt):
        am = self.am
        g, b = am.girl, am.boy
        p = ease_in_out_sine(prog(lt, 0, 8.5))
        am.cam_target = (lerp(1.22, 1.0, p), 640, lerp(470, 360, p))
        g.sway = b.sway = math.sin((lt + 11.5) * 1.7) * 3
        g.head_tilt = b.head_tilt = 1.0
        gS, bS = g.shoulder("inner"), b.shoulder("inner")
        M = ((gS[0] + bS[0]) / 2, gS[1] + 36)
        g.hand_targets["inner"] = b.hand_targets["inner"] = M
        g.hand_targets["outer"] = (g.shoulder("outer")[0] - 4, GROUND_Y - 66)
        am.bouquet_mode = ("girl_out",)
        am.bouquet.tilt = g.dir * 16
        am.float_fx(640, GROUND_Y - 150, 260, 3.5 + 4 * smooth(prog(lt, 2, 6)), dt)
        if self.once("sparkles", lt >= 4.5):
            am.burst(640, 140, 12, 380, ("sparkle", "star", "heart"))

    def draw_overlay(self, screen, lt):
        am = self.am
        p = prog(lt, 2.2, 4.8)
        if p <= 0.01:
            return
        img = am.end_text
        a = smooth(p) * (0.93 + 0.07 * math.sin(lt * 2.0))
        sc = lerp(0.94, 1.0, smooth(p))
        if sc < 0.999:
            img = pygame.transform.smoothscale(img, (int(img.get_width() * sc), int(img.get_height() * sc)))
        else:
            img = img.copy()
        img.set_alpha(int(255 * a))
        screen.blit(img, img.get_rect(center=(W // 2, 118)))


# ----------------------------------------------------------------------------
# ANIMATION MANAGER
# ----------------------------------------------------------------------------
class AnimationManager:
    def __init__(self, screen):
        self.screen = screen
        self.world = pygame.Surface((W, H)).convert()
        self.shadow_cache = {}
        self.mobile_mode = sys.platform == "emscripten"
        self.max_particles = 240 if self.mobile_mode else 420
        self.bg = Background()
        self._build_overlays()
        self.reset()

    # ---------- setup ----------
    def _build_overlays(self):
        rnd = random.Random(3)
        self.grain = []
        # Kurangi jumlah titik grain di browser/mobile agar waktu render lebih ringan.
        grain_points = 2400 if sys.platform == "emscripten" else 5200
        for _ in range(5):
            g = pygame.Surface((W, H), pygame.SRCALPHA)
            for _ in range(grain_points):
                a = rnd.randint(8, 26)
                col = (255, 240, 220, a) if rnd.random() < 0.55 else (10, 0, 30, a + 8)
                g.set_at((rnd.randrange(W), rnd.randrange(H)), col)
            self.grain.append(g)
        small = pygame.Surface((64, 36), pygame.SRCALPHA)
        for yy in range(36):
            for xx in range(64):
                dx, dy = (xx + 0.5) / 64 - 0.5, (yy + 0.5) / 36 - 0.5
                d = math.sqrt(dx * dx + (dy * 1.25) ** 2) * 2
                small.set_at((xx, yy), (8, 4, 28, int(255 * clamp((d - 0.55) / 0.75) ** 1.7 * 0.62)))
        self.vignette = pygame.transform.smoothscale(small, (W, H))
        self.black = pygame.Surface((W, H))
        self.black.fill((0, 0, 0))

        # judul PANASEA (per huruf)
        font = get_font(132, True)
        spacing = 12
        word = "PANASEA"
        widths = [font.size(ch)[0] for ch in word]
        x = (W - (sum(widths) + spacing * (len(word) - 1))) / 2
        self.title_letters = []
        for ch, w in zip(word, widths):
            img = render_glow_from(font.render(ch, True, CREAM), OUTLINE, HOT_PINK, pad=44, ow=4)
            self.title_letters.append((img, x - 44, 262 - 44))
            x += w + spacing
        sub = get_font(38).render("a little cure, a little comfort", True, CREAM)
        self.subtitle = render_glow_from(sub, OUTLINE, DUSTY_PINK, pad=30, ow=3)

        # teks ending: "I will be a panasea for you <3"
        size = 66
        f = get_font(size, True)
        while f.size("I will be a panasea for you")[0] > 840 and size > 40:
            size -= 4
            f = get_font(size, True)
        txt = f.render("I will be a panasea for you", True, CREAM)
        hw = int(txt.get_height() * 0.8)
        comp = pygame.Surface((txt.get_width() + hw + 18, txt.get_height()), pygame.SRCALPHA)
        comp.blit(txt, (0, 0))
        pygame.draw.polygon(comp, HOT_PINK, heart_points(txt.get_width() + 18 + hw / 2, txt.get_height() / 2 + 2, hw))
        self.end_text = render_glow_from(comp, OUTLINE, HOT_PINK, pad=50, ow=4, strength=3)

    def reset(self):
        self.t = 0.0
        self.lt = 0.0
        self.idx = 0
        self.fade = 255.0
        self.cam = [1.1, 640.0, 330.0]
        self.cam_target = (1.1, 640, 330)
        self.particles = []
        self._fx_acc = 0.0
        self._amb_acc = 0.0
        self._bub_acc = {}
        self.girl = Character("girl", +1, GIRL_PAL, GIRL_X0, GROUND_Y, True)
        self.boy = Character("boy", -1, BOY_PAL, BOY_X0, GROUND_Y, False)
        self.boy.carry = True
        self.girl.expr, self.boy.expr = "shy", "playful"
        self.girl_board = Skateboard(GIRL_X0, GROUND_Y, (226, 160, 182), CREAM, CREAM)
        self.boy_board = Skateboard(BOY_X0, GROUND_Y, (92, 84, 160), AMBER, AMBER)
        self.bouquet = Bouquet()
        self.bouquet_mode = ("boy",)
        self.boy_bubble = SpeechBubble("In a world full of sandiwara semu, I'll be your panasea.", 410, 0.62)
        self.girl_bubble = SpeechBubble("I will do the same for you.", 340, 0.38)
        self.scenes = [OpeningScene(self), EntranceScene(self), BoyDialogueScene(self),
                       GirlResponseScene(self), SweetMomentScene(self), EndingScene(self)]
        for _ in range(45):
            p = self._ambient_particle()
            p.age = random.uniform(0, p.life * 0.8)
            self.particles.append(p)
        self.scenes[0].enter()
        self.scenes[0].update(0.0, 0.0)

    # ---------- particle helpers ----------
    def _ambient_particle(self):
        kind = random.choice(("glow", "glow", "glow", "sparkle"))
        col = random.choice((AMBER, CREAM, PINK_SOFT))
        return Particle(kind, random.uniform(0, W), random.uniform(260, H), random.uniform(-6, 6),
                        random.uniform(-24, -8), random.uniform(6, 11),
                        random.uniform(14, 28) if kind == "glow" else random.uniform(8, 14), col,
                        sway=10, fade_in=1.0, peak=0.55 if kind == "glow" else 0.9)

    def burst(self, x, y, n=8, spread=70, kinds=("heart", "flower", "star", "sparkle")):
        palette = {"heart": (HOT_PINK, DUSTY_PINK, PINK_SOFT), "flower": (PINK_SOFT, CREAM, AMBER, (200, 180, 240)),
                   "star": ((255, 226, 140),), "sparkle": (CREAM,)}
        for _ in range(n):
            kind = random.choice(kinds)
            ang = random.uniform(-math.pi, 0)
            sp = random.uniform(40, 130)
            self.particles.append(Particle(kind, x + random.uniform(-spread, spread) * 0.5, y + random.uniform(-20, 20),
                                           math.cos(ang) * sp, math.sin(ang) * sp - 20, random.uniform(2.2, 3.6),
                                           random.uniform(18, 34), random.choice(palette[kind]), gravity=-10, sway=8,
                                           spin=random.uniform(-60, 60), fade_in=0.15, drag=0.9))

    def float_fx(self, cx, cy, spread_x, rate, dt, kinds=("heart", "heart", "flower", "star", "sparkle")):
        self._fx_acc += dt * rate
        palette = {"heart": (HOT_PINK, DUSTY_PINK, PINK_SOFT), "flower": (PINK_SOFT, CREAM, AMBER, (200, 180, 240)),
                   "star": ((255, 226, 140),), "sparkle": (CREAM,)}
        while self._fx_acc >= 1.0:
            self._fx_acc -= 1.0
            kind = random.choice(kinds)
            self.particles.append(Particle(kind, cx + random.uniform(-spread_x, spread_x), cy + random.uniform(-30, 30),
                                           random.uniform(-12, 12), random.uniform(-55, -25), random.uniform(3.0, 5.0),
                                           random.uniform(16, 30), random.choice(palette[kind]), sway=14,
                                           spin=random.uniform(-40, 40), fade_in=0.5))

    def bubble_hearts(self, bubble, dt, rate):
        acc = self._bub_acc.get(id(bubble), 0.0) + dt * rate
        cx, cy = bubble.center()
        while acc >= 1.0:
            acc -= 1.0
            side = random.choice((-1, 1))
            self.particles.append(Particle("heart", cx + side * random.uniform(120, 230), cy + random.uniform(-70, 70),
                                           side * random.uniform(4, 20), random.uniform(-45, -20), random.uniform(1.8, 2.8),
                                           random.uniform(14, 24), random.choice((HOT_PINK, DUSTY_PINK, PINK_SOFT)),
                                           sway=10, fade_in=0.2))
        self._bub_acc[id(bubble)] = acc

    def _motion_fx(self, dt):
        for ch, bd in ((self.girl, self.girl_board), (self.boy, self.boy_board)):
            v = bd.vx
            if abs(v) < 70:
                continue
            s = 1 if v > 0 else -1
            if random.random() < dt * min(16, abs(v) / 22):
                self.particles.append(Particle("streak", bd.x - s * random.uniform(80, 130), GROUND_Y - random.uniform(10, 240),
                                               -s * 40, 0, 0.5, random.uniform(50, 110), CREAM, fade_in=0.08, dirx=s, peak=0.9))
            if random.random() < dt * 9:
                self.particles.append(Particle("glow", bd.x - s * 50, GROUND_Y - 4, -s * random.uniform(10, 40),
                                               random.uniform(-30, -8), 0.9, 12, CREAM, fade_in=0.1, grow=45, peak=0.28))

    def _bouquet_follow(self):
        m = self.bouquet_mode
        g, b = self.girl, self.boy
        if m[0] == "boy":
            hnd = b.hand_draw["inner"]
        elif m[0] == "xfer":
            hnd = lerp2(b.hand_draw["inner"], g.hand_draw["inner"], m[1])
        elif m[0] == "girl_in":
            hnd = g.hand_draw["inner"]
        elif m[0] == "xfer2":
            hnd = lerp2(g.hand_draw["inner"], g.hand_draw["outer"], m[1])
        else:
            hnd = g.hand_draw["outer"]
        self.bouquet.hand = hnd

    # ---------- update ----------
    def update(self, dt):
        self.t += dt
        self.lt += dt
        sc = self.scenes[self.idx]
        if self.idx < len(self.scenes) - 1 and self.lt >= sc.duration:
            sc.update(sc.duration, 0.0)          # snap ke state akhir scene
            self.lt -= sc.duration
            self.idx += 1
            sc = self.scenes[self.idx]
            sc.enter()
        sc.update(self.lt, dt)

        k = 1 - math.exp(-dt * 2.6)
        for i in range(3):
            self.cam[i] += (self.cam_target[i] - self.cam[i]) * k

        for ch in (self.girl, self.boy):
            ch.update(dt)
        for bd in (self.girl_board, self.boy_board):
            bd.update(dt)
        self._bouquet_follow()
        self.bouquet.update(dt)
        self._motion_fx(dt)
        for bub, ch in ((self.girl_bubble, self.girl), (self.boy_bubble, self.boy)):
            bub.anchor = (ch.x + ch.dir * -4 + 6, ch.head_top() - 16)
            bub.update(dt)

        self._amb_acc += dt * 6
        while self._amb_acc >= 1.0:
            self._amb_acc -= 1.0
            self.particles.append(self._ambient_particle())
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive][-self.max_particles:]

    # ---------- draw ----------
    def _shadow(self, surf, x, width, alpha):
        if alpha <= 0.02:
            return
        # Cache hasil scaling bayangan agar tidak dihitung ulang setiap frame.
        key = int(width)
        img = self.shadow_cache.get(key)
        if img is None:
            img = pygame.transform.smoothscale(
                shadow_sprite(), (key, max(1, int(key * 0.2)))
            )
            self.shadow_cache[key] = img
        img.set_alpha(int(255 * alpha * 0.8))
        surf.blit(img, (x - img.get_width() / 2, GROUND_Y - 4))

    def draw(self):
        w = self.world
        self.bg.draw(w, self.t)
        for bd in (self.girl_board, self.boy_board):
            self._shadow(w, bd.x, 170, 1.0)
        for ch in (self.girl, self.boy):
            self._shadow(w, ch.x, 120, ch.stance * (1 - clamp(ch.hop / 40)))
        self.girl_board.draw(w)
        self.boy_board.draw(w)
        self.girl.draw(w)
        self.boy.draw(w)
        self.bouquet.draw(w)
        for p in self.particles:
            p.draw(w)
        self.girl_bubble.draw(w)
        self.boy_bubble.draw(w)

        # kamera
        z, cx, cy = max(1.0, self.cam[0]), self.cam[1] + math.sin(self.t * 0.5) * 5, self.cam[2] + math.cos(self.t * 0.4) * 3
        if z <= 1.0005:
            self.screen.blit(w, (0, 0))
        else:
            sw, sh = int(W * z), int(H * z)
            img = pygame.transform.smoothscale(w, (sw, sh))
            self.screen.blit(img, (int(clamp(W / 2 - cx * z, W - sw, 0)), int(clamp(H / 2 - cy * z, H - sh, 0))))

        self.scenes[self.idx].draw_overlay(self.screen, self.lt)
        self.screen.blit(self.grain[int(self.t * 18) % len(self.grain)], (0, 0))
        self.screen.blit(self.vignette, (0, 0))
        if self.fade > 1:
            self.black.set_alpha(int(self.fade))
            self.screen.blit(self.black, (0, 0))


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
async def main():
    pygame.init()
    try:
        screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
    except pygame.error:
        screen = pygame.display.set_mode((W, H))

    # Pygbag menampilkan canvas di browser. Ikuti viewport HP ketika orientasi
    # diputar dan ketika tinggi address bar browser berubah.
    if sys.platform == "emscripten":
        try:
            import platform
            canvas = platform.window.canvas
            body = platform.window.document.body
            body.style.margin = "0"
            body.style.padding = "0"
            body.style.overflow = "hidden"
            body.style.background = "#0a0d2a"
            canvas.style.display = "block"
            canvas.style.width = "100vw"
            canvas.style.height = "100dvh"
            canvas.style.objectFit = "contain"
            canvas.style.touchAction = "none"
        except Exception:
            # Fallback: mode SCALED | RESIZABLE tetap digunakan oleh Pygame.
            pass

    pygame.display.set_caption("PANASEA - a little cure, a little comfort")
    clock = pygame.time.Clock()
    am = AnimationManager(screen)
    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 1 / 20)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_r:
                    am.reset()
                elif e.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()
        am.update(dt)
        am.draw()
        pygame.display.flip()
        # Wajib agar event loop browser/Pygbag tetap mendapat giliran.
        await asyncio.sleep(0)
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
