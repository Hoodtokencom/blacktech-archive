"""
Dual-Model AI Pipeline — Professional Architecture Diagram
Blacktech Solutions / Think Energy Automation System
Generated with ReportLab
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_CENTER
import math

# ── Color Palette ────────────────────────────────────────────────────────────
BG_DARK       = HexColor("#0d0d0d")
BG_PANEL      = HexColor("#111827")
NAVY          = HexColor("#002244")
GREEN         = HexColor("#69BE28")
SILVER        = HexColor("#A5ACAF")
SILVER_DIM    = HexColor("#6b7280")
WHITE         = HexColor("#f1f5f9")
GOLD          = HexColor("#f59e0b")
RED_WARN      = HexColor("#ef4444")
CYAN          = HexColor("#06b6d4")
PURPLE        = HexColor("#7c3aed")
DARK_NAVY     = HexColor("#001533")
MID_GRAY      = HexColor("#1e293b")
BORDER_GRAY   = HexColor("#334155")
GREEN_DIM     = HexColor("#2d5a0e")
NAVY_DIM      = HexColor("#001133")

PAGE_W, PAGE_H = letter   # 612 x 792 pt

OUTPUT_PATH = "/home/allenai/data/dual-model-pipeline-schematic.pdf"


# ── Helpers ──────────────────────────────────────────────────────────────────

def hex_blend(c1: HexColor, c2: HexColor, t: float) -> HexColor:
    r = c1.red   + (c2.red   - c1.red)   * t
    g = c1.green + (c2.green - c1.green) * t
    b = c1.blue  + (c2.blue  - c1.blue)  * t
    return HexColor(f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}")


def draw_rounded_rect(c, x, y, w, h, r=6, fill=None, stroke=None, stroke_width=1):
    if fill:
        c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(stroke_width)
    p = c.beginPath()
    p.moveTo(x + r, y)
    p.lineTo(x + w - r, y)
    p.arcTo(x + w - 2*r, y, x + w, y + 2*r, -90, 90)
    p.lineTo(x + w, y + h - r)
    p.arcTo(x + w - 2*r, y + h - 2*r, x + w, y + h, 0, 90)
    p.lineTo(x + r, y + h)
    p.arcTo(x, y + h - 2*r, x + 2*r, y + h, 90, 90)
    p.lineTo(x, y + r)
    p.arcTo(x, y, x + 2*r, y + 2*r, 180, 90)
    p.close()
    c.drawPath(p, fill=1 if fill else 0, stroke=1 if stroke else 0)


def draw_arrow(c, x1, y1, x2, y2, color=GREEN, width=2, head=8):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)
    # arrowhead
    dx, dy = x2 - x1, y2 - y1
    length = math.sqrt(dx*dx + dy*dy)
    if length == 0:
        return
    ux, uy = dx/length, dy/length
    px, py = -uy, ux
    tip = (x2, y2)
    left  = (x2 - head*ux + head*0.4*px, y2 - head*uy + head*0.4*py)
    right = (x2 - head*ux - head*0.4*px, y2 - head*uy - head*0.4*py)
    path = c.beginPath()
    path.moveTo(*tip)
    path.lineTo(*left)
    path.lineTo(*right)
    path.close()
    c.drawPath(path, fill=1, stroke=0)


def center_text(c, text, cx, y, font="Helvetica-Bold", size=10, color=WHITE):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawCentredString(cx, y, text)


def left_text(c, text, x, y, font="Helvetica", size=9, color=SILVER):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawString(x, y, text)


def draw_badge(c, x, y, label, bg=NAVY, fg=WHITE, size=7.5, r=4):
    c.setFont("Helvetica-Bold", size)
    tw = c.stringWidth(label, "Helvetica-Bold", size)
    pad = 5
    draw_rounded_rect(c, x, y - size + 1, tw + pad*2, size + pad, r=r, fill=bg, stroke=None)
    c.setFillColor(fg)
    c.drawString(x + pad, y + 1, label)
    return tw + pad*2


def draw_section_label(c, x, y, label, color=SILVER_DIM):
    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(color)
    c.drawString(x, y, label)


# ── Box drawing helper ────────────────────────────────────────────────────────

class Box:
    def __init__(self, c, x, y, w, h, title, title_color=WHITE,
                 bg=MID_GRAY, border=BORDER_GRAY, border_w=1.2,
                 accent=None, radius=8):
        self.c = c
        self.x, self.y, self.w, self.h = x, y, w, h
        self.cx = x + w/2
        self.cy = y + h/2
        self.top = y + h
        self.bottom = y
        self.left = x
        self.right = x + w

        # shadow
        draw_rounded_rect(c, x+3, y-3, w, h, r=radius,
                          fill=HexColor("#000000"), stroke=None)
        # body
        draw_rounded_rect(c, x, y, w, h, r=radius, fill=bg, stroke=border, stroke_width=border_w)

        # accent stripe at top
        if accent:
            draw_rounded_rect(c, x, y+h-18, w, 18, r=radius, fill=accent, stroke=None)
            draw_rounded_rect(c, x, y+h-9, w, 9, r=0, fill=accent, stroke=None)

        # title
        if title:
            ty = y + h - 12 if accent else y + h - 12
            center_text(c, title, x + w/2, ty, size=9, color=WHITE if accent else title_color)

    @property
    def mid_right(self):
        return (self.right, self.cy)

    @property
    def mid_left(self):
        return (self.left, self.cy)

    @property
    def mid_top(self):
        return (self.cx, self.top)

    @property
    def mid_bottom(self):
        return (self.cx, self.bottom)


# ── Main drawing function ─────────────────────────────────────────────────────

def build_pdf():
    c = canvas.Canvas(OUTPUT_PATH, pagesize=letter)
    c.setTitle("Dual-Model AI Pipeline — Blacktech Solutions")
    c.setAuthor("Derrell Black / Blacktech Solutions")

    W, H = PAGE_W, PAGE_H

    # ═══════════════════════════════════════════════════════════
    # PAGE BACKGROUND
    # ═══════════════════════════════════════════════════════════
    draw_rounded_rect(c, 0, 0, W, H, r=0, fill=BG_DARK, stroke=None)

    # subtle grid lines
    c.setStrokeColor(HexColor("#1a1a2e"))
    c.setLineWidth(0.4)
    for gx in range(0, int(W), 30):
        c.line(gx, 0, gx, H)
    for gy in range(0, int(H), 30):
        c.line(0, gy, W, gy)

    # ═══════════════════════════════════════════════════════════
    # HEADER BANNER
    # ═══════════════════════════════════════════════════════════
    hdr_h = 62
    draw_rounded_rect(c, 0, H - hdr_h, W, hdr_h, r=0, fill=DARK_NAVY, stroke=None)
    # green accent bar
    c.setFillColor(GREEN)
    c.rect(0, H - hdr_h, W, 3, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.rect(0, H - hdr_h + hdr_h - 3, W, 3, fill=1, stroke=0)

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(WHITE)
    c.drawString(18, H - 30, "Dual-Model AI Pipeline")

    c.setFont("Helvetica", 10)
    c.setFillColor(SILVER)
    c.drawString(18, H - 48, "Blacktech Solutions  /  Think Energy Automation System")

    # right-side badges
    bx = W - 14
    for label, bg in [("v1.0", NAVY), ("PRODUCTION", GREEN_DIM), ("Pi 5 + Cloud", NAVY)]:
        c.setFont("Helvetica-Bold", 7.5)
        tw = c.stringWidth(label, "Helvetica-Bold", 7.5) + 10
        bx -= tw + 4
        draw_rounded_rect(c, bx, H - 44, tw, 16, r=4, fill=bg, stroke=None)
        c.setFillColor(WHITE)
        c.drawCentredString(bx + tw/2, H - 35, label)

    # ═══════════════════════════════════════════════════════════
    # LEGEND (top right)
    # ═══════════════════════════════════════════════════════════
    leg_x, leg_y = W - 118, H - hdr_h - 80
    draw_rounded_rect(c, leg_x, leg_y, 108, 68, r=6, fill=MID_GRAY, stroke=BORDER_GRAY, stroke_width=0.8)
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(SILVER)
    c.drawString(leg_x + 6, leg_y + 54, "LEGEND")
    items = [
        (GREEN,  "Data Flow (primary)"),
        (GOLD,   "Async Queue"),
        (RED_WARN, "Fallback Path"),
        (CYAN,   "Output Delivery"),
    ]
    for i, (col, lbl) in enumerate(items):
        ly = leg_y + 40 - i*13
        c.setFillColor(col)
        c.rect(leg_x + 6, ly + 1, 18, 4, fill=1, stroke=0)
        # arrowhead mini
        ah = c.beginPath()
        ah.moveTo(leg_x + 26, ly + 3)
        ah.lineTo(leg_x + 23, ly + 5.5)
        ah.lineTo(leg_x + 23, ly + 0.5)
        ah.close()
        c.setFillColor(col)
        c.drawPath(ah, fill=1, stroke=0)
        c.setFont("Helvetica", 7)
        c.setFillColor(SILVER)
        c.drawString(leg_x + 30, ly, lbl)

    # ═══════════════════════════════════════════════════════════
    # LAYER BANDS (background swim lanes)
    # ═══════════════════════════════════════════════════════════
    # Layout: bottom=18pt margin, top = below header
    content_top = H - hdr_h - 8
    content_bot = 18
    content_h   = content_top - content_bot

    band_labels = ["OUTPUT LAYER", "LOCAL AI LAYER (Pi 5)", "CLOUD AI LAYER", "INPUT LAYER"]
    band_colors = [
        HexColor("#0a1628"),   # output
        HexColor("#0d1f0d"),   # local
        HexColor("#0a0f28"),   # cloud
        HexColor("#1a1208"),   # input
    ]
    band_h = content_h / 4.0
    band_borders = [CYAN, GREEN, NAVY, GOLD]

    for i, (lbl, col, bcol) in enumerate(zip(band_labels, band_colors, band_borders)):
        by = content_bot + i * band_h
        # fill
        c.setFillColor(col)
        c.rect(0, by, W - 120, band_h, fill=1, stroke=0)
        # left accent stripe
        c.setFillColor(bcol)
        c.rect(0, by, 4, band_h, fill=1, stroke=0)
        # top border line
        c.setStrokeColor(HexColor("#2a2a3e"))
        c.setLineWidth(0.5)
        c.line(0, by + band_h, W - 120, by + band_h)
        # label
        c.saveState()
        c.translate(12, by + band_h/2)
        c.rotate(90)
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(bcol)
        c.drawCentredString(0, 0, lbl)
        c.restoreState()

    # ═══════════════════════════════════════════════════════════
    # HELPER: row center Y positions (from bottom)
    # ═══════════════════════════════════════════════════════════
    def row_cy(row_idx):
        """0=output, 1=local, 2=cloud, 3=input"""
        return content_bot + (row_idx + 0.5) * band_h

    # ═══════════════════════════════════════════════════════════
    # ROW 3 — INPUT LAYER
    # ═══════════════════════════════════════════════════════════
    icy = row_cy(3)
    box_h_sm = 56
    box_h_md = 64

    # --- Telegram ---
    tg = Box(c, 28, icy - box_h_sm/2, 90, box_h_sm,
             "TELEGRAM", bg=HexColor("#1a237e"), border=HexColor("#3949ab"),
             accent=HexColor("#1565c0"), radius=8)
    center_text(c, "Bot Webhook", tg.cx, icy - 4, size=7.5, color=SILVER)
    center_text(c, "port 443", tg.cx, icy - 14, size=7, color=SILVER_DIM)

    # --- n8n Webhook ---
    nw = Box(c, 136, icy - box_h_sm/2, 90, box_h_sm,
             "n8n WEBHOOK", bg=HexColor("#1a1208"), border=GOLD,
             accent=HexColor("#92400e"), radius=8)
    center_text(c, "port 5678", nw.cx, icy - 4, size=7.5, color=SILVER)
    center_text(c, "HTTP / REST", nw.cx, icy - 14, size=7, color=SILVER_DIM)

    # --- API ---
    api = Box(c, 244, icy - box_h_sm/2, 90, box_h_sm,
              "API / REST", bg=HexColor("#1a0a28"), border=PURPLE,
              accent=PURPLE, radius=8)
    center_text(c, "Anthropic SDK", api.cx, icy - 4, size=7.5, color=SILVER)
    center_text(c, "Custom Integrations", api.cx, icy - 14, size=7, color=SILVER_DIM)

    # Merge arrow from inputs → cloud
    merge_x = 370
    merge_y = icy
    # lines from each box to merge point
    for bx_obj in [tg, nw, api]:
        draw_arrow(c, bx_obj.right, bx_obj.cy, merge_x - 8, merge_y, color=GOLD, width=1.5, head=6)

    # label
    center_text(c, "USER REQUEST", merge_x - 40, icy + 14, size=7.5, color=GOLD)

    # ═══════════════════════════════════════════════════════════
    # ROW 2 — CLOUD AI LAYER
    # ═══════════════════════════════════════════════════════════
    ccy = row_cy(2)
    cloud_box_w = 220
    cloud_box_h = 78

    cb = Box(c, 60, ccy - cloud_box_h/2, cloud_box_w, cloud_box_h,
             "EXECUTIVE ORCHESTRATOR", bg=HexColor("#0a0f28"),
             border=HexColor("#3b5fc0"), border_w=2,
             accent=HexColor("#1e3a8a"), radius=10)

    # inner detail text
    lines_cloud = [
        ("Claude 4  (Anthropic API)", WHITE, 8.5, "Helvetica-Bold"),
        ("Model:  claude-sonnet-4 / claude-opus-4", SILVER, 7.5, "Helvetica"),
        ("Role:  Planning · Reasoning · Creativity", SILVER, 7.5, "Helvetica"),
        ("Output:  RawBlock  (free-form text)", GREEN, 7.5, "Helvetica-Oblique"),
        ("Schema:  None forced — free to think", SILVER_DIM, 7, "Helvetica"),
    ]
    for j, (txt, col, sz, font) in enumerate(lines_cloud):
        left_text(c, txt, cb.x + 10, ccy + 20 - j*11, font=font, size=sz, color=col)

    # cloud icon (simple)
    c.setFillColor(HexColor("#1e3a8a"))
    c.setStrokeColor(HexColor("#3b5fc0"))
    c.setLineWidth(1)
    c.circle(cb.right - 22, ccy + cloud_box_h/2 - 10, 9, fill=1, stroke=1)

    # Badge: CLOUD
    draw_badge(c, cb.x + 8, ccy - cloud_box_h/2 + 6, "☁  CLOUD", bg=HexColor("#1e3a8a"), fg=WHITE, size=7.5)

    # Vertical arrow: INPUT → CLOUD
    draw_arrow(c, merge_x, merge_y, merge_x, ccy + cloud_box_h/2 + 4,
               color=GOLD, width=2, head=8)
    center_text(c, "Request", merge_x + 12, (merge_y + ccy + cloud_box_h/2)/2, size=7, color=GOLD)

    # Arrow from cloud box to queue
    queue_x = 310
    queue_cy = ccy
    draw_arrow(c, cb.right, ccy, queue_x - 4, queue_cy, color=GREEN, width=2, head=8)
    center_text(c, "RawBlock", (cb.right + queue_x)/2, ccy + 6, size=7.5, color=GREEN)

    # ── ASYNC QUEUE ─────────────────────────────────────────────
    q_w, q_h = 92, 56
    qb = Box(c, queue_x, queue_cy - q_h/2, q_w, q_h,
             "ASYNC QUEUE", bg=HexColor("#1c1000"), border=GOLD,
             border_w=1.5, radius=8)
    lines_q = [
        ("Feeder: Claude 4", SILVER, 7),
        ("Workers: Phi3 pool", SILVER, 7),
        ("Collector: ordered", SILVER, 7),
    ]
    for j, (txt, col, sz) in enumerate(lines_q):
        left_text(c, txt, qb.x + 6, queue_cy + 8 - j*10, size=sz, color=col)

    # ═══════════════════════════════════════════════════════════
    # ROW 1 — LOCAL AI LAYER
    # ═══════════════════════════════════════════════════════════
    lcy = row_cy(1)
    local_box_w = 220
    local_box_h = 86

    lb = Box(c, 60, lcy - local_box_h/2, local_box_w, local_box_h,
             "CLEANING MACHINE", bg=HexColor("#0d1f0d"),
             border=GREEN, border_w=2,
             accent=GREEN_DIM, radius=10)

    lines_local = [
        ("Phi 3  via Ollama  (Local Pi 5)", WHITE, 8.5, "Helvetica-Bold"),
        ("Model:  phi3  (2.2 GB)  |  temp = 0.0", SILVER, 7.5, "Helvetica"),
        ("Input:   RawBlock  →  strict parsing", SILVER, 7.5, "Helvetica"),
        ("Output: CleanedBlock  (JSON / schema)", GREEN, 7.5, "Helvetica-Oblique"),
        ("Mode:   Deterministic — no creativity", SILVER_DIM, 7, "Helvetica"),
    ]
    for j, (txt, col, sz, font) in enumerate(lines_local):
        left_text(c, txt, lb.x + 10, lcy + 24 - j*11, font=font, size=sz, color=col)

    draw_badge(c, lb.x + 8, lcy - local_box_h/2 + 6, "Pi 5  LOCAL", bg=GREEN_DIM, fg=WHITE, size=7.5)

    # ── Backup model box ────────────────────────────────────────
    bk_w, bk_h = 96, 50
    bkb = Box(c, queue_x, lcy - bk_h/2, bk_w, bk_h,
              "BACKUP MODEL", bg=HexColor("#1a0f00"), border=RED_WARN,
              border_w=1.2, radius=8)
    lines_bk = [
        ("qwen2.5:1.5b", WHITE, 7.5),
        ("Size: 1 GB", SILVER, 7),
        ("Temp: 0.0", SILVER, 7),
    ]
    for j, (txt, col, sz) in enumerate(lines_bk):
        left_text(c, txt, bkb.x + 6, lcy + 10 - j*10, size=sz, color=col)

    # Arrow: queue → local (main)
    draw_arrow(c, qb.mid_bottom[0], qb.bottom, lb.mid_top[0] + 10, lb.top,
               color=GOLD, width=2, head=8)
    center_text(c, "RawBlock", qb.mid_bottom[0] + 16, (qb.bottom + lb.top)/2, size=7, color=GOLD)

    # Fallback arrow: queue → backup (dashed style via segments)
    c.setStrokeColor(RED_WARN)
    c.setLineWidth(1.2)
    dash_x1, dash_y1 = qb.right, queue_cy
    dash_x2, dash_y2 = bkb.left, lcy
    # draw dashed
    segs = 8
    for seg in range(segs):
        t1 = seg / segs
        t2 = (seg + 0.55) / segs
        x1s = dash_x1 + (dash_x2 - dash_x1)*t1
        y1s = dash_y1 + (dash_y2 - dash_y1)*t1
        x2s = dash_x1 + (dash_x2 - dash_x1)*t2
        y2s = dash_y1 + (dash_y2 - dash_y1)*t2
        c.line(x1s, y1s, x2s, y2s)

    # draw arrow tip on fallback
    draw_arrow(c, dash_x1 + (dash_x2-dash_x1)*0.95, dash_y1 + (dash_y2-dash_y1)*0.95,
               dash_x2, dash_y2, color=RED_WARN, width=0, head=6)
    center_text(c, "FALLBACK", (dash_x1+dash_x2)/2 + 8, (dash_y1+dash_y2)/2 + 6, size=6.5, color=RED_WARN)

    # Fallback arrow: backup → local
    c.setStrokeColor(RED_WARN)
    c.setLineWidth(1.0)
    c.line(bkb.cx, bkb.bottom, lb.right, lcy)
    draw_arrow(c, bkb.cx, bkb.bottom, lb.right, lcy, color=RED_WARN, width=1, head=5)

    # Arrow: cloud → local (direct, for Claude fallback)
    # thin dashed line on right edge
    c.setStrokeColor(RED_WARN)
    c.setLineWidth(0.8)
    fx1, fy1 = cb.right + 16, ccy - cloud_box_h/2
    fx2, fy2 = lb.right + 16, lcy + local_box_h/2
    segs2 = 6
    for seg in range(segs2):
        t1 = seg/segs2; t2 = (seg+0.5)/segs2
        c.line(fx1+(fx2-fx1)*t1, fy1+(fy2-fy1)*t1, fx1+(fx2-fx1)*t2, fy1+(fy2-fy1)*t2)

    # ── PI 5 HARDWARE SPECS PANEL ──────────────────────────────
    hw_x = queue_x + bk_w + 6
    hw_y = lcy - local_box_h/2
    hw_w = 88
    hw_h = local_box_h
    draw_rounded_rect(c, hw_x, hw_y, hw_w, hw_h, r=8,
                      fill=HexColor("#0a1a0a"), stroke=GREEN, stroke_width=1)
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(GREEN)
    c.drawCentredString(hw_x + hw_w/2, hw_y + hw_h - 10, "Pi 5 HARDWARE")
    hw_lines = [
        "CPU: ARM Cortex-A76",
        "RAM: 8 GB LPDDR4X",
        "SSD: External USB 3.0",
        "OS:  Raspberry Pi OS",
        "phi3:  2.2 GB",
        "qwen2.5:  1.0 GB",
        "Docker:  n8n :5678",
    ]
    for j, txt in enumerate(hw_lines):
        left_text(c, txt, hw_x + 5, hw_y + hw_h - 22 - j*10, size=6.5, color=SILVER)

    # ═══════════════════════════════════════════════════════════
    # ROW 0 — OUTPUT LAYER
    # ═══════════════════════════════════════════════════════════
    ocy = row_cy(0)
    out_box_w = 98
    out_box_h = 58

    outputs = [
        ("n8n WORKFLOWS",    "Automation Engine\nport 5678",       HexColor("#1a1208"), GOLD,                    28),
        ("DASHBOARDS",       "Money / Budget\nport 8091",          HexColor("#0a1a2a"), CYAN,                   140),
        ("JOB TRACKER",      "jobs.json\n/home/allenai/data/",     HexColor("#0d1f0d"), GREEN,                  252),
        ("EMAIL ALERTS",     "leads@blacktech\nsolutionscorp.com", HexColor("#1a0a28"), PURPLE,                 364),
    ]

    for title, detail, bg, border, ox in outputs:
        ob = Box(c, ox, ocy - out_box_h/2, out_box_w, out_box_h,
                 title, bg=bg, border=border, border_w=1.5, radius=8)
        d_lines = detail.split("\n")
        for j, dl in enumerate(d_lines):
            center_text(c, dl, ox + out_box_w/2, ocy - 2 - j*12, size=7, color=SILVER)

    # Arrows: local → each output
    out_boxes_cx = [28 + out_box_w/2, 140 + out_box_w/2, 252 + out_box_w/2, 364 + out_box_w/2]
    for ox_cx in out_boxes_cx:
        # find where the arrow comes from (lb bottom, spread)
        src_x = lb.cx + (ox_cx - lb.cx) * 0.3
        src_y = lb.bottom
        dst_y = ocy + out_box_h/2 + 2
        # two-segment bent arrow
        mid_y = (src_y + dst_y) / 2
        c.setStrokeColor(CYAN)
        c.setLineWidth(1.5)
        c.line(src_x, src_y, src_x, mid_y)
        c.line(src_x, mid_y, ox_cx, mid_y)
        draw_arrow(c, ox_cx, mid_y, ox_cx, dst_y, color=CYAN, width=1.5, head=6)

    # Label over output arrows
    center_text(c, "CleanedBlock  →  delivery", lb.cx, lb.bottom - 6, size=7, color=CYAN)

    # ═══════════════════════════════════════════════════════════
    # RIGHT-SIDE PANEL: USE CASES
    # ═══════════════════════════════════════════════════════════
    rp_x = W - 118
    rp_y = content_bot
    rp_w = 110
    rp_h = content_h - 90   # leave room for legend above

    draw_rounded_rect(c, rp_x, rp_y, rp_w, rp_h, r=8,
                      fill=HexColor("#0d1117"), stroke=SILVER_DIM, stroke_width=0.8)

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(GREEN)
    c.drawCentredString(rp_x + rp_w/2, rp_y + rp_h - 12, "USE CASES")

    use_cases = [
        ("BLACKTECH SOLUTIONS", SILVER, "Helvetica-Bold", 7),
        ("Electrical estimates", SILVER, "Helvetica", 7),
        ("Invoice formatting", SILVER, "Helvetica", 7),
        ("Job data to JSON", SILVER, "Helvetica", 7),
        ("", None, None, 0),
        ("THINK ENERGY", SILVER, "Helvetica-Bold", 7),
        ("Lead qualification", SILVER, "Helvetica", 7),
        ("Energy audit reports", SILVER, "Helvetica", 7),
        ("Marketing cleanup", SILVER, "Helvetica", 7),
        ("", None, None, 0),
        ("ASYNC PIPELINE", SILVER, "Helvetica-Bold", 7),
        ("Feeder: Claude 4", SILVER, "Helvetica", 7),
        ("Workers: Phi3 pool", SILVER, "Helvetica", 7),
        ("Collector: ordered", SILVER, "Helvetica", 7),
    ]
    uy = rp_y + rp_h - 26
    for (txt, col, font, sz) in use_cases:
        if not txt:
            uy -= 4
            continue
        if sz == 0:
            uy -= 4
            continue
        if font == "Helvetica-Bold":
            c.setFont("Helvetica-Bold", sz)
            c.setFillColor(GREEN if col == SILVER else col)
        else:
            c.setFont("Helvetica", sz)
            c.setFillColor(SILVER)
            c.drawString(rp_x + 8, uy, "• " + txt)
            uy -= 11
            continue
        c.drawString(rp_x + 6, uy, txt)
        uy -= 11

    # ─── Fallback note box ───────────────────────────────────────
    fb_y = rp_y + 6
    fb_h = 52
    draw_rounded_rect(c, rp_x, fb_y, rp_w, fb_h, r=6,
                      fill=HexColor("#1a0505"), stroke=RED_WARN, stroke_width=0.8)
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(RED_WARN)
    c.drawCentredString(rp_x + rp_w/2, fb_y + fb_h - 11, "⚠  FALLBACK CHAIN")
    fallbacks = [
        "phi3 fails → qwen2.5:1.5b",
        "qwen fails → Claude + schema",
        "All local down → cloud only",
    ]
    for j, txt in enumerate(fallbacks):
        left_text(c, txt, rp_x + 7, fb_y + fb_h - 23 - j*10, size=6.5, color=SILVER)

    # ═══════════════════════════════════════════════════════════
    # MAIN VERTICAL FLOW ARROW (center spine)
    # ═══════════════════════════════════════════════════════════
    # Already drawn per-section. Add a subtle vertical centerline guide.
    spine_x = merge_x
    c.setStrokeColor(HexColor("#1a2a1a"))
    c.setLineWidth(0.5)
    c.setDash(4, 4)
    c.line(spine_x, content_bot + band_h, spine_x, content_bot + 3*band_h)
    c.setDash()

    # ── Local → Output spine label ─────────────────────────────
    # already have arrows above

    # ═══════════════════════════════════════════════════════════
    # DATA TYPE LABELS (floating chips)
    # ═══════════════════════════════════════════════════════════
    chips = [
        (merge_x + 16, row_cy(3) + band_h*0.3, "Request", GOLD),
        (cb.right + 4,  ccy,                    "RawBlock → Queue", GREEN),
        (lb.cx,         lb.bottom + 6,           "CleanedBlock", CYAN),
    ]
    for cx_chip, cy_chip, label, col in chips:
        c.setFont("Helvetica-Oblique", 7)
        c.setFillColor(col)
        c.drawString(cx_chip, cy_chip, label)

    # ═══════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════
    c.setFillColor(DARK_NAVY)
    c.rect(0, 0, W, 16, fill=1, stroke=0)
    c.setFont("Helvetica", 6.5)
    c.setFillColor(SILVER_DIM)
    c.drawString(8, 5, "Derrell Black  |  Blacktech Solutions  |  leads@blacktechsolutionscorp.com")
    c.drawRightString(W - 8, 5, "CONFIDENTIAL — Internal Architecture Document  |  June 2026")

    c.save()
    print(f"PDF saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
