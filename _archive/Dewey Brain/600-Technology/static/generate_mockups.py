"""
Qbitme Product Mockup Generator
Creates 6 professional product card images for the Qbitme brand.
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
import os

# ── Paths ──────────────────────────────────────────────────────────────────────
OUT = "/home/allenai/static"
FONT_BOLD   = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_NORMAL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ── Brand colours ──────────────────────────────────────────────────────────────
BG          = (5,   6,  15)          # #05060f  dark navy
PURPLE      = (108, 99, 255)         # #6c63ff
CYAN        = (0,  229, 255)         # #00e5ff
GOLD        = (255, 200,  60)        # warm gold
WHITE       = (255, 255, 255)
LIGHT_GRAY  = (180, 185, 200)
DARK_GRAY   = ( 30,  32,  50)
GREEN_PCB   = ( 20, 100,  60)
MID_GREEN   = ( 30, 140,  80)

SIZE = (800, 800)

# ── Helpers ────────────────────────────────────────────────────────────────────

def new_canvas(bg=BG):
    img = Image.new("RGBA", SIZE, bg + (255,))
    return img, ImageDraw.Draw(img)


def font(size, bold=True):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_NORMAL, size)
    except Exception:
        return ImageFont.load_default()


def center_x(draw, text, fnt, y, color, img_w=800):
    """Draw text horizontally centred at y."""
    bb = draw.textbbox((0, 0), text, font=fnt)
    w = bb[2] - bb[0]
    x = (img_w - w) // 2
    draw.text((x, y), text, font=fnt, fill=color)
    return w


def gradient_bg(img, top_col, bot_col):
    """Apply a vertical gradient overlay."""
    w, h = img.size
    for y in range(h):
        t = y / h
        r = int(top_col[0] + (bot_col[0] - top_col[0]) * t)
        g = int(top_col[1] + (bot_col[1] - top_col[1]) * t)
        b = int(top_col[2] + (bot_col[2] - top_col[2]) * t)
        img.paste(Image.new("RGBA", (w, 1), (r, g, b, 255)), (0, y))


def radial_glow(draw, cx, cy, r, color, steps=60):
    """Soft radial glow using concentric ellipses."""
    for i in range(steps, 0, -1):
        alpha = int(50 * (i / steps) ** 2)
        rad = int(r * i / steps)
        col = color + (alpha,)
        draw.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=col)


def gradient_text(img, text, fnt, x, y, col_left, col_right):
    """Render text with a horizontal gradient colour."""
    tmp = Image.new("RGBA", img.size, (0, 0, 0, 0))
    td  = ImageDraw.Draw(tmp)
    bb  = td.textbbox((x, y), text, font=fnt)
    w   = bb[2] - bb[0]
    # draw text in white on mask
    mask = Image.new("L", img.size, 0)
    md   = ImageDraw.Draw(mask)
    md.text((x, y), text, font=fnt, fill=255)
    # build colour gradient strip
    grad = Image.new("RGBA", (w if w > 0 else 1, 1), col_left + (255,))
    gd   = ImageDraw.Draw(grad)
    for px in range(w):
        t = px / max(w - 1, 1)
        r = int(col_left[0] + (col_right[0] - col_left[0]) * t)
        g = int(col_left[1] + (col_right[1] - col_left[1]) * t)
        b = int(col_left[2] + (col_right[2] - col_left[2]) * t)
        gd.line([(px, 0), (px, 0)], fill=(r, g, b, 255))
    grad = grad.resize((w, bb[3] - bb[1] + 4), Image.NEAREST)
    col_strip = Image.new("RGBA", img.size, (0, 0, 0, 0))
    col_strip.paste(grad, (bb[0], bb[1]))
    col_strip.putalpha(mask)
    img.alpha_composite(col_strip)


def add_corner_dots(draw, color=PURPLE, r=4):
    """Decorative corner accents."""
    for cx, cy in [(30, 30), (770, 30), (30, 770), (770, 770)]:
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)


def add_scanlines(img, gap=6, alpha=12):
    """Subtle horizontal scanline texture."""
    sl = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sl)
    for y in range(0, img.size[1], gap):
        sd.line([(0, y), (img.size[0], y)], fill=(0, 0, 0, alpha))
    img.alpha_composite(sl)


def label_badge(draw, text, cx, cy, bg_col, text_col=WHITE, pad=12, r=10, fnt=None):
    if fnt is None:
        fnt = font(18)
    bb = draw.textbbox((0, 0), text, font=fnt)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]
    x0, y0 = cx - tw // 2 - pad, cy - th // 2 - pad // 2
    x1, y1 = cx + tw // 2 + pad, cy + th // 2 + pad // 2
    draw.rounded_rectangle((x0, y0, x1, y1), radius=r, fill=bg_col)
    draw.text((x0 + pad, y0 + pad // 2), text, font=fnt, fill=text_col)


def border_frame(draw, color=PURPLE, width=2, inset=18):
    i = inset
    draw.rounded_rectangle((i, i, 800 - i, 800 - i), radius=20,
                            outline=color + (120,), width=width)


# ══════════════════════════════════════════════════════════════════════════════
# 1. T-SHIRT
# ══════════════════════════════════════════════════════════════════════════════

def make_tshirt():
    img, draw = new_canvas()
    add_scanlines(img)

    # subtle gradient bg
    for y in range(800):
        t = y / 800
        r = int(5 + 10 * t)
        g = int(6 + 8 * t)
        b = int(15 + 25 * t)
        draw.line([(0, y), (799, y)], fill=(r, g, b, 255))

    # glow behind shirt
    glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    radial_glow(gd, 400, 430, 280, PURPLE, steps=80)
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    img.alpha_composite(glow)

    # ── shirt body ────────────────────────────────────────────────────────────
    shirt_col  = (18, 18, 35)
    shirt_dark = (12, 12, 24)

    # left sleeve
    draw.polygon([(160, 300), (100, 260), (80, 380), (200, 400)],
                 fill=shirt_dark)
    # right sleeve
    draw.polygon([(640, 300), (700, 260), (720, 380), (600, 400)],
                 fill=shirt_dark)
    # collar
    draw.polygon([(310, 210), (400, 250), (490, 210), (470, 190), (400, 225), (330, 190)],
                 fill=(25, 25, 45))
    # main body
    draw.polygon([(160, 300), (200, 700), (600, 700), (640, 300),
                  (490, 210), (400, 250), (310, 210)],
                 fill=shirt_col)

    # subtle seam lines
    draw.line([(400, 260), (400, 695)], fill=(28, 28, 50), width=2)

    # ── logo on chest ─────────────────────────────────────────────────────────
    # glow spot
    chest_glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    cgd = ImageDraw.Draw(chest_glow)
    radial_glow(cgd, 400, 430, 100, PURPLE, steps=40)
    chest_glow = chest_glow.filter(ImageFilter.GaussianBlur(20))
    img.alpha_composite(chest_glow)

    # Qbitme text
    fnt_logo = font(68)
    bb = draw.textbbox((0, 0), "Qbitme", font=fnt_logo)
    tw = bb[2] - bb[0]
    # shadow
    draw.text(((800 - tw) // 2 + 3, 393), "Qbitme", font=fnt_logo,
              fill=(40, 30, 80, 180))
    draw.text(((800 - tw) // 2, 390), "Qbitme", font=fnt_logo, fill=PURPLE)

    # small circuit-dot accent under Q
    for dx in range(-3, 4, 3):
        draw.ellipse((396 + dx - 2, 462, 396 + dx + 2, 466), fill=CYAN)

    # tagline
    fnt_tag = font(17, bold=False)
    center_x(draw, "AI Hardware  ·  Community  ·  Base Network",
              fnt_tag, 488, LIGHT_GRAY)

    # ── top label ─────────────────────────────────────────────────────────────
    fnt_sm = font(14)
    center_x(draw, "Q B I T M E  ORIGINALS", fnt_sm, 130, PURPLE)
    draw.line([(240, 150), (560, 150)], fill=PURPLE + (80,), width=1)

    # ── bottom price area ─────────────────────────────────────────────────────
    label_badge(draw, " Merch Drop ", 400, 745,
                DARK_GRAY, CYAN, pad=14, r=8, fnt=font(16))

    border_frame(draw, PURPLE)
    add_corner_dots(draw, PURPLE)

    img = img.convert("RGB")
    img.save(os.path.join(OUT, "qbitme_tshirt.png"), quality=95)
    print("✓  qbitme_tshirt.png")


# ══════════════════════════════════════════════════════════════════════════════
# 2. COFFEE MUG
# ══════════════════════════════════════════════════════════════════════════════

def make_mug():
    img, draw = new_canvas()
    add_scanlines(img)

    # gradient bg
    for y in range(800):
        t = y / 800
        r = int(5 + 8 * t)
        g = int(6 + 10 * t)
        b = int(15 + 30 * t)
        draw.line([(0, y), (799, y)], fill=(r, g, b, 255))

    # glow
    glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    radial_glow(gd, 390, 420, 250, CYAN, steps=80)
    glow = glow.filter(ImageFilter.GaussianBlur(45))
    img.alpha_composite(glow)

    # ── mug body ──────────────────────────────────────────────────────────────
    mug_white = (245, 245, 250)
    mug_shad  = (210, 210, 220)
    mug_base  = (230, 230, 240)

    # shadow
    draw.ellipse((230, 670, 570, 720), fill=(10, 10, 25, 160))

    # mug cylinder body
    draw.rounded_rectangle((230, 250, 560, 660), radius=22, fill=mug_white)
    # right-side shade strip
    draw.rounded_rectangle((510, 260, 560, 650), radius=18, fill=mug_shad)
    # left shine
    draw.rounded_rectangle((240, 260, 265, 500), radius=10, fill=(255, 255, 255, 200))

    # mug top ellipse
    draw.ellipse((228, 238, 562, 278), fill=mug_white, outline=mug_base, width=2)
    # inner opening
    draw.ellipse((248, 242, 542, 274), fill=(220, 220, 232))
    # coffee surface
    draw.ellipse((258, 246, 532, 270), fill=(70, 40, 20))

    # mug base plate
    draw.rounded_rectangle((220, 650, 575, 675), radius=10, fill=mug_base)

    # handle
    draw.arc((545, 370, 640, 520), start=320, end=220, fill=(200, 200, 210), width=26)
    draw.arc((545, 370, 640, 520), start=320, end=220, fill=(240, 240, 248), width=14)

    # ── logo on mug ───────────────────────────────────────────────────────────
    fnt_logo = font(52)
    bb = draw.textbbox((0, 0), "Qbitme", font=fnt_logo)
    tw = bb[2] - bb[0]
    lx = (800 - tw) // 2 - 10
    ly = 390
    gradient_text(img, "Qbitme", fnt_logo, lx, ly, PURPLE, CYAN)

    # tagline on mug
    fnt_tag = font(19, bold=False)
    bb2 = draw.textbbox((0, 0), "Run Local AI", font=fnt_tag)
    tw2 = bb2[2] - bb2[0]
    draw.text(((800 - tw2) // 2 - 10, 455),
              "Run Local AI", font=fnt_tag, fill=(80, 80, 100))

    # small dots / circuit deco on mug
    for i, (dx, dy) in enumerate([(-60, 20), (-30, 25), (0, 27), (30, 25), (60, 20)]):
        col = CYAN if i % 2 == 0 else PURPLE
        draw.ellipse((390 + dx - 3, 495 + dy - 3, 390 + dx + 3, 495 + dy + 3),
                     fill=col)

    # ── label at top ─────────────────────────────────────────────────────────
    center_x(draw, "Q B I T M E  ·  STORE", font(14), 140, CYAN)
    draw.line([(250, 160), (550, 160)], fill=CYAN + (70,), width=1)

    # ── bottom tag ────────────────────────────────────────────────────────────
    label_badge(draw, "  Run Local AI  ", 400, 745,
                DARK_GRAY, PURPLE, pad=14, r=8, fnt=font(16))

    border_frame(draw, CYAN)
    add_corner_dots(draw, CYAN)

    img = img.convert("RGB")
    img.save(os.path.join(OUT, "qbitme_mug.png"), quality=95)
    print("✓  qbitme_mug.png")


# ══════════════════════════════════════════════════════════════════════════════
# 3. CAP / HAT
# ══════════════════════════════════════════════════════════════════════════════

def make_cap():
    img, draw = new_canvas()
    add_scanlines(img)

    for y in range(800):
        t = y / 800
        r = int(5 + 5 * t)
        g = int(6 + 6 * t)
        b = int(15 + 20 * t)
        draw.line([(0, y), (799, y)], fill=(r, g, b, 255))

    glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    radial_glow(gd, 400, 380, 260, CYAN, steps=80)
    glow = glow.filter(ImageFilter.GaussianBlur(50))
    img.alpha_composite(glow)

    cap_col   = (20, 22, 38)
    cap_mid   = (28, 30, 50)
    cap_light = (35, 38, 62)
    brim_col  = (15, 16, 30)

    # ── shadow ────────────────────────────────────────────────────────────────
    draw.ellipse((180, 630, 620, 670), fill=(5, 5, 15, 180))

    # ── crown (main dome) ────────────────────────────────────────────────────
    draw.ellipse((170, 200, 630, 560), fill=cap_mid)          # wide ellipse for dome
    draw.rectangle((170, 380, 630, 560), fill=cap_mid)        # fill lower half flat

    # left panel shade
    draw.polygon([(170, 380), (210, 210), (400, 200), (400, 560), (170, 560)],
                 fill=cap_col)
    # right panel
    draw.polygon([(630, 380), (590, 210), (400, 200), (400, 560), (630, 560)],
                 fill=cap_light)
    # top highlight seam
    draw.ellipse((170, 200, 630, 560), outline=(40, 44, 70), width=2)

    # centre seam
    draw.line([(400, 205), (400, 558)], fill=(30, 33, 55), width=3)

    # side seams
    draw.line([(280, 220), (250, 555)], fill=(25, 27, 45), width=2)
    draw.line([(520, 220), (550, 555)], fill=(30, 33, 55), width=2)

    # band / sweatband
    draw.rectangle((170, 520, 630, 560), fill=(25, 27, 44))
    draw.line([(170, 522), (630, 522)], fill=(40, 42, 65), width=2)

    # ── brim ─────────────────────────────────────────────────────────────────
    draw.ellipse((130, 535, 670, 610), fill=brim_col)
    # brim top edge
    draw.arc((130, 535, 670, 570), start=180, end=0, fill=(45, 47, 70), width=3)
    # brim under-shadow
    draw.arc((145, 570, 655, 608), start=0, end=180, fill=(8, 8, 18), width=8)

    # button on top
    draw.ellipse((388, 200, 412, 224), fill=(30, 32, 55))
    draw.ellipse((392, 204, 408, 220), fill=(45, 47, 72))

    # ── embroidered Qbitme ────────────────────────────────────────────────────
    # embroidery base – slightly raised look
    fnt_emb = font(52)
    bb = draw.textbbox((0, 0), "Qbitme", font=fnt_emb)
    tw = bb[2] - bb[0]
    ex = (800 - tw) // 2
    ey = 348

    # shadow layer (embroidery depth)
    for off in [(2, 2), (3, 3), (1, 1)]:
        draw.text((ex + off[0], ey + off[1]), "Qbitme", font=fnt_emb,
                  fill=(0, 60, 80, 180))
    draw.text((ex, ey), "Qbitme", font=fnt_emb, fill=CYAN)

    # small "AI" emblem above logo
    fnt_mini = font(15)
    center_x(draw, "⬡  AI HARDWARE  ⬡", fnt_mini, 310, (0, 180, 210))

    # ── top label ─────────────────────────────────────────────────────────────
    center_x(draw, "Q B I T M E  ·  GEAR", font(14), 145, CYAN)
    draw.line([(250, 165), (550, 165)], fill=CYAN + (70,), width=1)

    # ── size tag ──────────────────────────────────────────────────────────────
    label_badge(draw, " One Size Fits All ", 400, 745,
                DARK_GRAY, CYAN, pad=14, r=8, fnt=font(16))

    border_frame(draw, CYAN)
    add_corner_dots(draw, CYAN)

    img = img.convert("RGB")
    img.save(os.path.join(OUT, "qbitme_cap.png"), quality=95)
    print("✓  qbitme_cap.png")


# ══════════════════════════════════════════════════════════════════════════════
# 4. PEN
# ══════════════════════════════════════════════════════════════════════════════

def make_pen():
    img, draw = new_canvas()
    add_scanlines(img)

    for y in range(800):
        t = y / 800
        r = int(5 + 8 * t)
        g = int(6 + 6 * t)
        b = int(15 + 25 * t)
        draw.line([(0, y), (799, y)], fill=(r, g, b, 255))

    glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    radial_glow(gd, 400, 410, 220, GOLD, steps=80)
    glow = glow.filter(ImageFilter.GaussianBlur(50))
    img.alpha_composite(glow)

    # ── pen barrel (diagonal) ─────────────────────────────────────────────────
    # pen drawn at ~30° tilt for style, then rotated
    pen_img = Image.new("RGBA", (800, 800), (0, 0, 0, 0))
    pd      = ImageDraw.Draw(pen_img)

    # barrel dimensions (vertical, to be rotated)
    BX, BY = 335, 120   # barrel top-left
    BW, BH = 130, 520   # barrel width, height

    # barrel body gradient simulation
    for x in range(BW):
        t = x / BW
        if t < 0.15:
            c = int(60 + t / 0.15 * 60)
        elif t < 0.5:
            c = int(120 + (t - 0.15) / 0.35 * 60)
        elif t < 0.7:
            c = int(180 - (t - 0.5) / 0.2 * 60)
        else:
            c = int(120 - (t - 0.7) / 0.3 * 80)
        pd.line([(BX + x, BY), (BX + x, BY + BH)], fill=(c, c, c + 5))

    # barrel outline
    pd.rounded_rectangle((BX, BY, BX + BW, BY + BH), radius=20,
                          outline=(80, 80, 100), width=2)

    # clip (side strip)
    pd.rounded_rectangle((BX + BW - 18, BY + 10, BX + BW + 4, BY + 220),
                          radius=8, fill=(90, 70, 10), outline=(120, 100, 20), width=1)
    pd.line([(BX + BW - 7, BY + 18), (BX + BW - 7, BY + 210)],
            fill=(180, 150, 40), width=2)

    # cap ring (gold band)
    pd.rectangle((BX - 2, BY + 100, BX + BW + 2, BY + 130),
                 fill=(100, 80, 10))
    for i in range(3):
        pd.rectangle((BX - 2, BY + 103 + i * 8, BX + BW + 2, BY + 107 + i * 8),
                     fill=(220, 180, 50))

    # tip section (tapered)
    pd.polygon([(BX + 30, BY + BH),
                (BX + BW - 30, BY + BH),
                (BX + BW // 2 + 6, BY + BH + 60),
                (BX + BW // 2 - 6, BY + BH + 60)],
               fill=(50, 50, 60))
    # nib
    pd.polygon([(BX + BW // 2 - 6, BY + BH + 60),
                (BX + BW // 2 + 6, BY + BH + 60),
                (BX + BW // 2, BY + BH + 90)],
               fill=(200, 170, 40))

    # end cap (top)
    pd.rounded_rectangle((BX, BY, BX + BW, BY + 30), radius=14,
                         fill=(40, 40, 55))
    pd.ellipse((BX + BW // 2 - 8, BY + 6, BX + BW // 2 + 8, BY + 22),
               fill=(80, 80, 100))

    # ── gold "Qbitme" text on barrel ─────────────────────────────────────────
    fnt_pen = font(32)
    bb = pd.textbbox((0, 0), "Qbitme", font=fnt_pen)
    tw = bb[2] - bb[0]
    tx = BX + (BW - tw) // 2
    ty = BY + 210

    # shadow
    pd.text((tx + 2, ty + 2), "Qbitme", font=fnt_pen, fill=(60, 40, 0, 200))
    pd.text((tx, ty), "Qbitme", font=fnt_pen, fill=GOLD)

    # small tagline on barrel
    fnt_sm2 = font(13, bold=False)
    bb2 = pd.textbbox((0, 0), "AI Hardware", font=fnt_sm2)
    tw2 = bb2[2] - bb2[0]
    pd.text((BX + (BW - tw2) // 2, ty + 46), "AI Hardware",
            font=fnt_sm2, fill=(180, 150, 40))

    # rotate pen
    pen_rot = pen_img.rotate(-28, resample=Image.BICUBIC, expand=False)
    img.alpha_composite(pen_rot)

    # ── reflection line ───────────────────────────────────────────────────────
    draw = ImageDraw.Draw(img)

    # ── label top ─────────────────────────────────────────────────────────────
    center_x(draw, "Q B I T M E  ·  EXEC PEN", font(14), 140, GOLD)
    draw.line([(240, 160), (560, 160)], fill=GOLD + (70,), width=1)

    # ── price badge ───────────────────────────────────────────────────────────
    label_badge(draw, "  Premium Ballpoint  ", 400, 745,
                DARK_GRAY, GOLD, pad=14, r=8, fnt=font(16))

    border_frame(draw, GOLD)
    add_corner_dots(draw, GOLD)

    img = img.convert("RGB")
    img.save(os.path.join(OUT, "qbitme_pen.png"), quality=95)
    print("✓  qbitme_pen.png")


# ══════════════════════════════════════════════════════════════════════════════
# 5. RASPBERRY PI 5 DEVICE (Qbitme Pro Pi)
# ══════════════════════════════════════════════════════════════════════════════

def make_pi_pro():
    img, draw = new_canvas()
    add_scanlines(img)

    for y in range(800):
        t = y / 800
        r = int(5 + 6 * t)
        g = int(6 + 12 * t)
        b = int(15 + 25 * t)
        draw.line([(0, y), (799, y)], fill=(r, g, b, 255))

    # glow
    glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    radial_glow(gd, 400, 420, 270, GREEN_PCB, steps=80)
    glow = glow.filter(ImageFilter.GaussianBlur(45))
    img.alpha_composite(glow)
    draw = ImageDraw.Draw(img)

    # ── PCB board ─────────────────────────────────────────────────────────────
    BX, BY = 160, 230
    BW, BH = 480, 330

    # board shadow
    shadow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((BX + 8, BY + 8, BX + BW + 8, BY + BH + 8),
                         radius=12, fill=(0, 0, 0, 130))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    img.alpha_composite(shadow)
    draw = ImageDraw.Draw(img)

    # main board
    draw.rounded_rectangle((BX, BY, BX + BW, BY + BH), radius=12, fill=GREEN_PCB)

    # PCB grid lines
    for gx in range(BX + 20, BX + BW, 20):
        draw.line([(gx, BY + 5), (gx, BY + BH - 5)],
                  fill=(25, 110, 65, 100), width=1)
    for gy in range(BY + 20, BY + BH, 20):
        draw.line([(BX + 5, gy), (BX + BW - 5, gy)],
                  fill=(25, 110, 65, 100), width=1)

    # board edge highlight
    draw.rounded_rectangle((BX, BY, BX + BW, BY + BH), radius=12,
                            outline=(50, 160, 90), width=2)

    # ── mounting holes ────────────────────────────────────────────────────────
    for hx, hy in [(BX + 18, BY + 18), (BX + BW - 18, BY + 18),
                   (BX + 18, BY + BH - 18), (BX + BW - 18, BY + BH - 18)]:
        draw.ellipse((hx - 7, hy - 7, hx + 7, hy + 7), fill=(10, 70, 40))
        draw.ellipse((hx - 4, hy - 4, hx + 4, hy + 4), fill=(180, 150, 50))

    # ── CPU / SoC chip ────────────────────────────────────────────────────────
    cx, cy = BX + 160, BY + 160
    draw.rectangle((cx - 50, cy - 50, cx + 50, cy + 50), fill=(30, 30, 50))
    draw.rectangle((cx - 46, cy - 46, cx + 46, cy + 46), fill=(50, 52, 80))
    # chip pins
    for i in range(6):
        px = cx - 50 + i * 18
        draw.rectangle((px - 3, cy - 60, px + 3, cy - 50), fill=(180, 150, 50))
        draw.rectangle((px - 3, cy + 50, px + 3, cy + 60), fill=(180, 150, 50))
    for i in range(6):
        py = cy - 50 + i * 18
        draw.rectangle((cx - 62, py - 3, cx - 50, py + 3), fill=(180, 150, 50))
        draw.rectangle((cx + 50, py - 3, cx + 62, py + 3), fill=(180, 150, 50))
    # chip label
    fnt_chip = font(13)
    draw.text((cx - 28, cy - 12), "BCM2712", font=fnt_chip, fill=(150, 160, 200))

    # ── RAM chip ──────────────────────────────────────────────────────────────
    draw.rectangle((BX + 250, BY + 110, BX + 330, BY + 175), fill=(35, 35, 55))
    draw.rectangle((BX + 253, BY + 113, BX + 327, BY + 172), fill=(55, 57, 85))
    draw.text((BX + 258, BY + 135), "LPDDR5", font=font(12), fill=(130, 140, 190))
    draw.text((BX + 263, BY + 150), "8 GB", font=font(11), fill=(100, 220, 140))

    # ── USB / HDMI ports (right edge) ─────────────────────────────────────────
    for i, label in enumerate(["USB3", "USB3", "HDMI"]):
        px = BX + BW - 10
        py = BY + 60 + i * 75
        draw.rectangle((px, py, px + 32, py + 50), fill=(40, 42, 65))
        draw.rectangle((px + 2, py + 2, px + 30, py + 48), fill=(20, 22, 40))
        draw.text((px - 26, py + 16), label, font=font(10), fill=(100, 120, 160))

    # ── GPIO pins (top edge) ──────────────────────────────────────────────────
    for i in range(20):
        draw.rectangle((BX + 20 + i * 20, BY - 8, BX + 30 + i * 20, BY + 5),
                       fill=(180, 150, 50))

    # ── SD card slot (bottom edge) ────────────────────────────────────────────
    draw.rectangle((BX + 40, BY + BH - 2, BX + 100, BY + BH + 12),
                   fill=(60, 65, 90))
    draw.text((BX + 44, BY + BH + 1), "microSD", font=font(9), fill=(120, 130, 160))

    # ── traces / connections ──────────────────────────────────────────────────
    trace_col = (35, 130, 75, 160)
    draw.line([(cx + 50, cy), (BX + 250, cy)], fill=trace_col, width=2)
    draw.line([(cx, cy + 50), (cx, BY + BH - 40)], fill=trace_col, width=2)
    draw.line([(BX + 290, BY + 175), (BX + 290, BY + 240)], fill=trace_col, width=2)

    # ── Wi-Fi / BT chip ───────────────────────────────────────────────────────
    draw.rounded_rectangle((BX + 350, BY + 200, BX + 420, BY + 280),
                            radius=6, fill=(38, 38, 58))
    draw.text((BX + 353, BY + 225), "WiFi6", font=font(12), fill=(100, 180, 240))
    draw.text((BX + 357, BY + 242), "BT5.0", font=font(12), fill=(120, 100, 240))

    # ── Qbitme branding on board ──────────────────────────────────────────────
    fnt_brand = font(18)
    draw.text((BX + 20, BY + BH - 45), "Qbitme Pro Pi", font=fnt_brand, fill=CYAN)
    draw.text((BX + 20, BY + BH - 25), "hermes.ai", font=font(12, bold=False),
              fill=(80, 200, 140))

    # ── product title ─────────────────────────────────────────────────────────
    center_x(draw, "Qbitme Pro Pi", font(40), 130, WHITE)
    center_x(draw, "Powered by Hermes AI", font(17, bold=False), 180, CYAN)

    # ── price badge ───────────────────────────────────────────────────────────
    draw.rounded_rectangle((300, 590, 500, 640), radius=14,
                            fill=(108, 99, 255))
    center_x(draw, "$249", font(32), 595, WHITE)

    # ── specs ─────────────────────────────────────────────────────────────────
    specs = [
        ("● 8GB LPDDR5 RAM",    LIGHT_GRAY),
        ("● 256GB NVMe SSD",    LIGHT_GRAY),
        ("● Hermes AI Runtime", CYAN),
        ("● WiFi 6 + BT 5.0",  LIGHT_GRAY),
    ]
    sy = 660
    for i, (spec, col) in enumerate(specs):
        col_offset = (i % 2) * 400
        x_pos = 120 + col_offset
        draw.text((x_pos, sy + (i // 2) * 28), spec, font=font(16, bold=False), fill=col)

    border_frame(draw, (50, 200, 100))
    add_corner_dots(draw, (50, 200, 100))

    img = img.convert("RGB")
    img.save(os.path.join(OUT, "qbitme_pi_pro.png"), quality=95)
    print("✓  qbitme_pi_pro.png")


# ══════════════════════════════════════════════════════════════════════════════
# 6. TECH BACKPACK
# ══════════════════════════════════════════════════════════════════════════════

def make_backpack():
    img, draw = new_canvas()
    add_scanlines(img)

    for y in range(800):
        t = y / 800
        r = int(5 + 8 * t)
        g = int(6 + 7 * t)
        b = int(15 + 28 * t)
        draw.line([(0, y), (799, y)], fill=(r, g, b, 255))

    glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    radial_glow(gd, 400, 430, 270, PURPLE, steps=80)
    glow = glow.filter(ImageFilter.GaussianBlur(50))
    img.alpha_composite(glow)
    draw = ImageDraw.Draw(img)

    bg_col    = (22, 24, 42)
    bg_mid    = (30, 32, 56)
    bg_dark   = (14, 15, 28)
    zip_col   = (60, 62, 90)
    zip_light = (100, 102, 140)

    # ── shadow ────────────────────────────────────────────────────────────────
    draw.ellipse((200, 670, 600, 720), fill=(5, 5, 12, 180))

    # ── main bag body ─────────────────────────────────────────────────────────
    draw.rounded_rectangle((200, 170, 600, 670), radius=35, fill=bg_col)

    # panel shade right
    draw.rounded_rectangle((490, 185, 600, 655), radius=28, fill=bg_dark)
    # panel shade left
    draw.rounded_rectangle((200, 185, 310, 655), radius=28, fill=bg_dark)
    # centre highlight
    draw.rounded_rectangle((305, 185, 495, 655), radius=20, fill=bg_mid)

    # top handle
    draw.rounded_rectangle((340, 160, 460, 195), radius=16, fill=bg_dark)
    draw.rounded_rectangle((348, 166, 452, 188), radius=12, fill=zip_col)

    # top zipper
    draw.arc((210, 165, 590, 230), start=200, end=340, fill=zip_col, width=5)
    draw.arc((214, 168, 586, 226), start=200, end=340, fill=zip_light, width=2)
    # zipper pull
    draw.ellipse((392, 215, 408, 231), fill=zip_light)

    # shoulder strap left
    draw.polygon([(215, 220), (175, 280), (155, 580), (210, 590), (220, 300)],
                 fill=bg_dark)
    draw.line([(185, 290), (175, 560)], fill=zip_col, width=3)

    # shoulder strap right
    draw.polygon([(585, 220), (625, 280), (645, 580), (590, 590), (580, 300)],
                 fill=bg_dark)
    draw.line([(615, 290), (625, 560)], fill=zip_col, width=3)

    # ── front pocket ──────────────────────────────────────────────────────────
    draw.rounded_rectangle((270, 420, 530, 635), radius=20, fill=bg_dark)
    draw.rounded_rectangle((273, 423, 527, 632), radius=18, outline=zip_col, width=2)

    # pocket zipper
    draw.arc((278, 416, 522, 445), start=200, end=340, fill=zip_col, width=4)
    draw.ellipse((393, 432, 407, 448), fill=zip_light)

    # ── Qbitme patch on front pocket ─────────────────────────────────────────
    # patch background
    PX, PY, PW, PH = 300, 455, 200, 120
    draw.rounded_rectangle((PX, PY, PX + PW, PY + PH), radius=12,
                            fill=(25, 20, 55))
    draw.rounded_rectangle((PX, PY, PX + PW, PY + PH), radius=12,
                            outline=PURPLE + (200,), width=2)

    # patch logo text
    fnt_patch = font(34)
    bb = draw.textbbox((0, 0), "Qbitme", font=fnt_patch)
    tw = bb[2] - bb[0]
    px_text = PX + (PW - tw) // 2
    draw.text((px_text + 2, PY + 26), "Qbitme", font=fnt_patch,
              fill=(40, 30, 100, 180))
    draw.text((px_text, PY + 24), "Qbitme", font=fnt_patch, fill=PURPLE)

    # patch tagline
    fnt_ptag = font(12, bold=False)
    bb2 = draw.textbbox((0, 0), "AI HARDWARE", font=fnt_ptag)
    tw2 = bb2[2] - bb2[0]
    draw.text((PX + (PW - tw2) // 2, PY + 74), "AI HARDWARE",
              font=fnt_ptag, fill=CYAN)

    # patch corner stitching dots
    for sx, sy in [(PX + 8, PY + 8), (PX + PW - 8, PY + 8),
                   (PX + 8, PY + PH - 8), (PX + PW - 8, PY + PH - 8)]:
        draw.ellipse((sx - 2, sy - 2, sx + 2, sy + 2), fill=PURPLE + (150,))

    # ── side mesh pocket indicator ─────────────────────────────────────────────
    for i in range(5):
        draw.line([(600, 300 + i * 40), (640, 300 + i * 40)],
                  fill=(40, 42, 70), width=2)
    draw.rounded_rectangle((598, 295, 645, 495), radius=8,
                            outline=(40, 42, 70), width=2)

    # ── USB-C charging port indicator ─────────────────────────────────────────
    draw.rounded_rectangle((380, 645, 420, 660), radius=4,
                            fill=(40, 42, 70), outline=zip_col, width=1)
    draw.text((357, 665), "USB-C Charging", font=font(11, bold=False),
              fill=(80, 85, 120))

    # ── logo + title ──────────────────────────────────────────────────────────
    center_x(draw, "Qbitme Tech Pack", font(40), 90, WHITE)
    center_x(draw, "Carry Your AI Stack", font(17, bold=False), 142, CYAN)

    # ── price ─────────────────────────────────────────────────────────────────
    label_badge(draw, "  $89  ", 400, 750,
                PURPLE, WHITE, pad=18, r=12, fnt=font(28))

    border_frame(draw, PURPLE)
    add_corner_dots(draw, PURPLE)

    img = img.convert("RGB")
    img.save(os.path.join(OUT, "qbitme_backpack.png"), quality=95)
    print("✓  qbitme_backpack.png")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Generating Qbitme product mockups …")
    make_tshirt()
    make_mug()
    make_cap()
    make_pen()
    make_pi_pro()
    make_backpack()
    print("\nAll 6 mockups saved to", OUT)
