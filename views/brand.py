"""Brand identity module — Definite Assurance Co. Ltd.

Injects CSS and provides branded Streamlit components aligned to the
official Brand Identity Guidelines v0.1 (February 2025).

Palette
-------
Aberdare Green  #0f4f48   primary — trust, growth, security
Uhuru Red       #eb2229   primary — urgency, assurance tick
Institutional Blue #00567a  secondary — corporate, trust, governance
Solid Black     #000000
Urban White     #ffffff

Typography
----------
Primary : Gotham (clean, modern sans-serif)
Fallback: Roboto (served via Google Fonts)
Headlines   : Gotham Ultra / Roboto Black        >=24 pt
Subheaders  : Gotham Bold  / Roboto Bold         16-24 pt
Body        : Gotham Book  / Roboto Regular      12-16 pt
"""
from __future__ import annotations

import base64
import os

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ---------------------------------------------------------------------------
# Brand palette
# ---------------------------------------------------------------------------
GREEN    = "#0f4f48"   # Aberdare Green
RED      = "#eb2229"   # Uhuru Red
BLUE     = "#00567a"   # Institutional Blue (corporate / governance)
BLACK    = "#000000"
WHITE    = "#ffffff"
GREEN_70 = "#3e756f"   # Aberdare Green 70 % tint
GREEN_30 = "#a8c7c4"   # Aberdare Green 30 % tint
GREEN_10 = "#e5f0ef"   # Aberdare Green 10 % tint
RED_70   = "#f17075"   # Uhuru Red 70 % tint
RED_10   = "#fce8e9"   # Uhuru Red 10 % tint
BLUE_70  = "#3a8db5"   # Institutional Blue 70 % tint
BLUE_30  = "#7fc6dc"   # Institutional Blue 30 % tint
BLUE_10  = "#e8f4fb"   # Institutional Blue 10 % tint

# ---------------------------------------------------------------------------
# Extended palette — tints for charts and data-vis
# ---------------------------------------------------------------------------
# Ordered brand colorway (categorical charts — 8 stops)
DA_COLORWAY: list[str] = [
    GREEN,       # Aberdare Green       — primary positive
    RED,         # Uhuru Red            — primary accent / alert
    GREEN_70,    # Green 70 %           — secondary positive
    RED_70,      # Red 70 %             — secondary accent
    GREEN_30,    # Green 30 %           — tertiary positive
    "#1a8f87",   # Bright teal          — extra accent
    "#c41e24",   # Darker red           — emphasis
    GREEN_10,    # Green 10 %           — background tint
]

# Sequential scale: Aberdare Green → neutral → Uhuru Red
# Low = good/fast (green), high = urgent/slow (red)
DA_SCALE_GREEN_RED: list[list] = [
    [0.00, GREEN],    # best — brand green
    [0.40, GREEN_30], # mid-low
    [0.70, RED_70],   # mid-high
    [1.00, RED],      # worst — Uhuru Red
]

_FONT_FAMILY = "'Gotham', 'Roboto', 'Helvetica Neue', Arial, sans-serif"


# ---------------------------------------------------------------------------
# Plotly theme
# ---------------------------------------------------------------------------

def register_plotly_theme() -> None:
    """Build and register the 'definite_assurance' Plotly template.

    Combines with plotly_white for a clean baseline, then overlays brand
    colors, font, and hover style. Safe to call multiple times (idempotent).
    Auto-called at module import time.
    """
    template = go.layout.Template(
        layout=go.Layout(
            colorway=DA_COLORWAY,
            font=dict(family=_FONT_FAMILY, color="#333333", size=12),
            title=dict(
                font=dict(family=_FONT_FAMILY, color=GREEN, size=15),
                x=0.0,
                xanchor="left",
            ),
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            xaxis=dict(
                gridcolor="#f0f0f0",
                linecolor="#cccccc",
                zerolinecolor="#e0e0e0",
                tickfont=dict(family=_FONT_FAMILY, size=11),
                title_font=dict(family=_FONT_FAMILY, color="#555555"),
            ),
            yaxis=dict(
                gridcolor="#f0f0f0",
                linecolor="#cccccc",
                zerolinecolor="#e0e0e0",
                tickfont=dict(family=_FONT_FAMILY, size=11),
                title_font=dict(family=_FONT_FAMILY, color="#555555"),
            ),
            legend=dict(
                bgcolor="rgba(255,255,255,0.92)",
                bordercolor="#e0e0e0",
                borderwidth=1,
                font=dict(family=_FONT_FAMILY, size=11),
            ),
            hoverlabel=dict(
                bgcolor=GREEN,
                font_color=WHITE,
                font_family=_FONT_FAMILY,
                bordercolor=GREEN,
            ),
            coloraxis=dict(
                colorbar=dict(
                    tickfont=dict(family=_FONT_FAMILY, size=10),
                    title_font=dict(family=_FONT_FAMILY, size=11),
                )
            ),
        ),
        data=go.layout.template.Data(
            bar=[go.Bar(marker=dict(line=dict(width=0)))],
            scatter=[go.Scatter(line=dict(width=2.5), marker=dict(size=6))],
            pie=[
                go.Pie(
                    textfont=dict(color=WHITE, family=_FONT_FAMILY),
                    hoverlabel=dict(
                        bgcolor=GREEN, font_color=WHITE, bordercolor=GREEN,
                    ),
                )
            ],
        ),
    )
    pio.templates["definite_assurance"] = template
    pio.templates.default = "plotly_white+definite_assurance"


# Auto-register on import — any module importing brand gets the theme for free
register_plotly_theme()


# ---------------------------------------------------------------------------
# Logo HTML component
# ---------------------------------------------------------------------------

def _logo_html(size_px: int = 56, variant: str = "color") -> str:
    """Return self-contained HTML for the Definite Assurance wordmark.

    Renders the stylised D-with-checkmark + 'Definite' in Aberdare Green
    and 'ASSURANCE' in Uhuru Red below, matching the official logo mark.

    Args:
        size_px : Cap-height in px for the 'Definite' wordmark.
        variant : 'color' for the full-colour version;
                  'white' for all-white on dark/green backgrounds.
    """
    if variant == "white":
        word_col   = "#ffffff"
        check_col  = "#ffffff"
        assure_col = "rgba(255,255,255,0.88)"
    else:
        word_col   = GREEN   # Aberdare Green
        check_col  = RED     # Uhuru Red
        assure_col = RED

    check_px  = round(size_px * 0.60)
    assure_px = round(size_px * 0.27)
    top_off   = round(size_px * 0.06)
    left_off  = round(size_px * 0.03)
    gap_top   = round(size_px * 0.07)

    return (
        f'<div style="display:inline-flex;flex-direction:column;line-height:1;'
        f'font-family:\'Gotham\',\'Roboto\',\'Arial Black\',Arial,sans-serif;">'
        # Row 1: D✓ + efinite
        f'<div style="display:inline-flex;align-items:baseline;line-height:0.95;">'
        # D with red checkmark overlay
        f'<div style="position:relative;display:inline-block;line-height:1;">'
        f'<span style="font-size:{size_px}px;font-weight:900;color:{word_col};'
        f'line-height:1;display:block;">D</span>'
        f'<span style="position:absolute;top:{top_off}px;left:{left_off}px;'
        f'font-size:{check_px}px;font-weight:900;color:{check_col};line-height:1;">'
        f'&#10003;</span>'
        f'</div>'
        # rest of wordmark
        f'<span style="font-size:{size_px}px;font-weight:900;color:{word_col};'
        f'line-height:1;margin-left:-1px;">efinite</span>'
        f'</div>'
        # Row 2: ASSURANCE
        f'<div style="font-size:{assure_px}px;font-weight:700;color:{assure_col};'
        f'letter-spacing:0.38em;margin-top:{gap_top}px;padding-left:2px;">'
        f'ASSURANCE</div>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Status badge helper (color + explicit text label — never color-only)
# ---------------------------------------------------------------------------

# Map each semantic variant -> (css class suffix, label text). The label
# guarantees status is communicated without relying on colour perception,
# satisfying the WCAG "no colour-only status" rule.
_BADGE_LABELS: dict[str, str] = {
    "green":  "Active",
    "red":    "Blocked",
    "blue":   "Review",
    "amber":  "Pending",
    "gray":   "Neutral",
    "muted":  "Unknown",
}


def status_badge(variant: str = "green", label: str | None = None) -> str:
    """Return HTML for a branded status badge.

    Badges always render BOTH a coloured dot and an explicit text label so
    that status is perceivable without colour (WCAG 2.1 success criterion
    1.4.1). Pass ``label`` to override the default semantic text.

    Args:
        variant : One of green | red | blue | amber | gray | muted.
        label   : Optional override text shown after the dot.

    Returns:
        Marked-up <span> using the ``.da-badge`` CSS classes from _CSS.
    """
    variant = (variant or "green").lower()
    if variant not in _BADGE_LABELS:
        variant = "green"
    text = label if label is not None else _BADGE_LABELS[variant]
    cls = f"da-badge da-badge--{variant}"
    return f'<span class="{cls}">{text}</span>'


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
_CSS = f"""
<style>
/* ---- Institutional colour variables (CSS custom properties) ---- */
:root {{
  --da-green:       {GREEN};
  --da-green-70:    {GREEN_70};
  --da-green-30:    {GREEN_30};
  --da-green-10:    {GREEN_10};
  --da-red:         {RED};
  --da-red-70:      {RED_70};
  --da-red-10:      {RED_10};
  --da-blue:        {BLUE};
  --da-blue-70:     {BLUE_70};
  --da-blue-30:     {BLUE_30};
  --da-blue-10:     {BLUE_10};
  --da-black:       {BLACK};
  --da-white:       {WHITE};
  --da-border:      #d0d7de;
  --da-border-dark: #b0becc;
  --da-text:        #2b2b2b;
  --da-text-muted:  #6b6b6b;
  --da-bg:          #ffffff;
  --da-bg-subtle:   #f7f8f9;
  --da-shadow-sm:   0 1px 2px rgba(0,0,0,0.04);
  --da-shadow:      0 1px 4px rgba(0,0,0,0.08);
}}

/* ---- Google Fonts: Poppins (futuristic modern) ---- */
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap');

/* ---- Animated subtle background gradient ---- */
.stApp {{
  background: radial-gradient(circle at 20% 50%, rgba(235, 34, 41, 0.03) 0%, transparent 50%),
              radial-gradient(circle at 80% 20%, rgba(15, 79, 56, 0.03) 0%, transparent 50%),
              var(--da-bg);
  background-size: 200% 200%;
  animation: da-bg-shift 20s ease infinite;
}}

@keyframes da-bg-shift {{
  0%   {{ background-position: 0% 50%; }}
  50%  {{ background-position: 100% 50%; }}
  100% {{ background-position: 0% 50%; }}
}}

/* ---- Global font — Poppins primary, Roboto secondary, Gotham fallback ---- */
html, body, [class*="css"] {{
  font-family: 'Poppins', 'Gotham', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
}}

/* ---- Sidebar — Aberdare Green background ---- */
section[data-testid="stSidebar"] {{
  background-color: {GREEN} !important;
}}
section[data-testid="stSidebar"] * {{
  color: {WHITE} !important;
}}
section[data-testid="stSidebar"] hr {{
  border-color: rgba(255,255,255,0.25) !important;
}}
section[data-testid="stSidebar"] .stButton > button {{
  background-color: {RED} !important;
  color: {WHITE} !important;
  border: none !important;
  border-radius: 4px !important;
  font-weight: 700 !important;
  letter-spacing: 0.03em;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
  background-color: #c41e24 !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  transform: translateY(-1px);
}}

/* ---- Enhanced sidebar nav — glassmorphism + neon hover ---- */
section[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] {{
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(8px);
  border-radius: 12px;
  padding: 8px;
  margin: 4px 0;
  border: 1px solid rgba(255, 255, 255, 0.15);
}}
section[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] label {{
  font-weight: 600;
  letter-spacing: 0.02em;
  border-radius: 6px;
  padding: 6px 12px !important;
  transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1) !important;
}}
section[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] label:hover {{
  color: var(--da-white) !important;
  background: rgba(235, 34, 41, 0.20) !important;
  transform: translateX(4px) !important;
  box-shadow: 0 0 10px rgba(235, 34, 41, 0.30) !important;
}}
section[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] input[type="radio"]:checked + label {{
  background: rgba(235, 34, 41, 0.35) !important;
  box-shadow: 0 0 12px rgba(235, 34, 41, 0.50) !important;
  color: var(--da-white) !important;
}}

/* ---- Sidebar accent border: gradient glow ---- */
section[data-testid="stSidebar"] {{
  border-right: 3px solid;
  border-right: 3px solid var(--da-green);
  box-shadow: 3px 0 8px rgba(15, 79, 56, 0.15);
}}

/* ---- Primary action buttons — Uhuru Red ---- */
.stButton > button[kind="primary"] {{
  background-color: {RED} !important;
  color: {WHITE} !important;
  border: none !important;
  border-radius: 4px !important;
  font-weight: 700 !important;
}}
.stButton > button[kind="primary"]:hover {{
  background-color: #c41e24 !important;
  box-shadow: 0 2px 6px rgba(235,34,41,0.35);
}}

/* ---- Form submit button (primary intent) ---- */
button[data-testid="baseButton-secondaryFormSubmit"],
button[data-testid="baseButton-primaryFormSubmit"] {{
  background-color: {RED} !important;
  color: {WHITE} !important;
  border: none !important;
  font-weight: 700 !important;
}}

/* ---- Branded button component (utility classes) ---- */
.da-btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-weight: 700;
  letter-spacing: 0.02em;
  cursor: pointer;
  text-decoration: none;
  transition: background-color 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}}
.da-btn--primary {{
  background: var(--da-red);
  color: var(--da-white);
}}
.da-btn--primary:hover {{
  background: #c41e24;
  box-shadow: 0 2px 8px rgba(235,34,41,0.35);
}}
.da-btn--secondary {{
  background: var(--da-green);
  color: var(--da-white);
}}
.da-btn--secondary:hover {{
  background: #0b3d37;
}}
.da-btn--outline {{
  background: transparent;
  color: var(--da-blue);
  border: 1px solid var(--da-blue);
}}
.da-btn--outline:hover {{
  background: var(--da-blue-10);
}}
.da-btn--small  {{ padding: 5px 12px; font-size: 0.78rem; }}
.da-btn--large  {{ padding: 11px 20px; font-size: 0.92rem; }}

/* ---- Metric cards — KPI cards with coloured left accent ---- */
[data-testid="stMetricValue"] {{
  color: var(--da-green) !important;
  font-weight: 700 !important;
}}
[data-testid="stMetricLabel"] {{
  color: var(--da-text-muted) !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
}}
.da-metric {{
  background: var(--da-bg);
  border: 1px solid var(--da-border);
  border-left: 4px solid var(--da-green);
  border-radius: 8px;
  padding: 14px 18px;
  box-shadow: var(--da-shadow-sm);
}}
.da-metric.da-metric--accent-red  {{ border-left-color: var(--da-red); }}
.da-metric.da-metric--accent-blue {{ border-left-color: var(--da-blue); }}
.da-metric .da-metric-label {{
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--da-text-muted);
  font-weight: 600;
}}
.da-metric .da-metric-value {{
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--da-text);
  margin-top: 2px;
}}
.da-metric .da-metric-delta {{
  font-size: 0.8rem;
  font-weight: 600;
}}
.da-metric .da-metric-delta.pos {{ color: var(--da-green); }}
.da-metric .da-metric-delta.neg {{ color: var(--da-red); }}

/* ---- Status badges: colour + text label (never colour-only) ---- */
.da-badge {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  line-height: 1.6;
  border: 1px solid transparent;
}}
.da-badge::before {{
  content: "";
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}}
.da-badge--green  {{ background: #e6f4f1; color: #0f4f48; border-color: #0f4f48; }}
.da-badge--green::before  {{ background: #0f4f48; }}
.da-badge--red    {{ background: #fce8e9; color: #c41e24; border-color: #c41e24; }}
.da-badge--red::before    {{ background: #c41e24; }}
.da-badge--blue   {{ background: #e8f4fb; color: #00567a; border-color: #00567a; }}
.da-badge--blue::before   {{ background: #00567a; }}
.da-badge--amber  {{ background: #fff4e5; color: #b05a00; border-color: #b05a00; }}
.da-badge--amber::before  {{ background: #b05a00; }}
.da-badge--gray   {{ background: #f0f2f5; color: #425161; border-color: #425161; }}
.da-badge--gray::before   {{ background: #425161; }}
.da-badge--muted  {{ background: #f7f8f9; color: #6b6b6b; border-color: var(--da-border); }}

/* ---- Data tables: header accent + zebra striping ---- */
.da-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  color: var(--da-text);
  background: var(--da-bg);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--da-border);
}}
.da-table thead th {{
  background: var(--da-blue);
  color: var(--da-white);
  font-weight: 700;
  text-align: left;
  padding: 8px 10px;
  border: none;
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}}
.da-table tbody td {{
  padding: 7px 10px;
  border-bottom: 1px solid var(--da-border);
}}
.da-table tbody tr:nth-child(even) td {{
  background: var(--da-bg-subtle);
}}
.da-table tbody tr:hover td {{
  background: var(--da-blue-10);
}}
.da-table td.da-cell--green {{ color: var(--da-green); font-weight: 700; }}
.da-table td.da-cell--red   {{ color: var(--da-red);   font-weight: 700; }}
.da-table td.da-cell--blue  {{ color: var(--da-blue);  font-weight: 700; }}

/* ---- Tabs: branded active indicator ---- */
[data-baseweb="tab-list"] {{
  border-bottom: 2px solid var(--da-border);
  background: var(--da-bg-subtle);
  border-radius: 8px 8px 0 0;
}}
button[data-baseweb="tab"] {{
  border-radius: 0;
  border-bottom: 3px solid transparent;
  color: var(--da-text-muted);
  font-weight: 600;
  padding: 10px 18px;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
  border-bottom: 3px solid var(--da-red);
  color: var(--da-red);
}}
button[data-baseweb="tab"]:hover {{
  background: var(--da-bg-subtle);
}}

/* ---- Forms: field accent + focus ring ---- */
.stTextInput input,
.stTextArea textarea,
.stSelectbox [data-baseweb="select"] input,
.stNumberInput input {{
  border: 1px solid var(--da-border) !important;
  border-radius: 6px !important;
  background: var(--da-bg) !important;
}}
.stTextInput input:focus,
.stTextArea textarea:focus,
.stSelectbox [data-baseweb="select"] input:focus,
.stNumberInput input:focus {{
  outline: 2px solid var(--da-green);
  outline-offset: 1px;
  border-color: var(--da-green);
}}
label[data-baseweb="label"] {{
  color: var(--da-text-muted) !important;
  font-weight: 600 !important;
}}

/* ---- Active tab indicator (defensive, matches earlier rule) ---- */
button[data-baseweb="tab"][aria-selected="true"] {{
  border-bottom: 3px solid {RED} !important;
  color: {RED} !important;
  font-weight: 700 !important;
}}

/* ---- Page headings ---- */
h1 {{ color: {GREEN} !important; font-weight: 900 !important; }}
h2 {{ color: {GREEN} !important; font-weight: 700 !important; }}
h3 {{ color: {BLACK} !important; font-weight: 700 !important; }}

/* ---- Horizontal divider tinted red ---- */
hr {{
  border-top: 2px solid {RED} !important;
  opacity: 0.35;
}}

/* ---- Brand strip (top-of-page header) ---- */
.da-strip {{
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 2px 0 12px 0;
  border-bottom: 3px solid {RED};
  margin-bottom: 16px;
}}
.da-strip-tick {{
  font-size: 2.4rem;
  color: {RED};
  line-height: 1;
  font-weight: 900;
}}
.da-strip-name {{
  font-size: 1.15rem;
  font-weight: 900;
  color: {GREEN};
  letter-spacing: 0.06em;
  text-transform: uppercase;
  line-height: 1.1;
}}
.da-strip-tagline {{
  font-size: 0.73rem;
  color: #777;
  font-style: italic;
  margin-top: 2px;
}}

/* ---- Login page ---- */
.da-login-wrap {{
  text-align: center;
  padding: 20px 0 4px 0;
}}

/* ---- Login page gradient background ---- */
[data-testid="stApp"] .main {{
  background: radial-gradient(circle at 30% 30%, rgba(235, 34, 41, 0.05) 0%, transparent 50%),
              radial-gradient(circle at 80% 70%, rgba(15, 79, 56, 0.05) 0%, transparent 50%);
}}

/* ---- Login form glass container ---- */
.da-login-form {{
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(14px) saturate(180%);
  -webkit-backdrop-filter: blur(14px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.30);
  border-radius: 16px;
  padding: 28px 28px 32px;
  box-shadow:
    0 12px 40px rgba(0, 0, 0, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.50);
  margin: 16px 0;
}}

/* ---- Login form accent bar ---- */
.da-login-form::before {{
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: linear-gradient(90deg, {GREEN}, {RED}, {BLUE});
  border-radius: 3px 3px 0 0;
}}

/* ---- Login form fields ---- */
.da-login-form .stTextInput input {{
  background: rgba(255, 255, 255, 0.70);
  border: 1px solid rgba(0, 86, 122, 0.20);
  border-radius: 8px;
  transition: all 0.20s ease;
}}
.da-login-form .stTextInput input:focus {{
  background: rgba(255, 255, 255, 0.90);
  box-shadow: 0 0 0 3px {GREEN_10}, 0 0 12px rgba(15, 79, 56, 0.25);
  border-color: {GREEN};
}}

/* ---- Neon login button glow ---- */
.da-login-form .stButton > button[type="primary"] {{
  background: linear-gradient(135deg, {RED}, {BLUE});
  border: none;
  border-radius: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  transition: all 0.20s ease;
}}
.da-login-form .stButton > button[type="primary"]:hover {{
  transform: translateY(-2px);
  box-shadow: 0 0 20px rgba(235, 34, 41, 0.40), 0 4px 16px rgba(0, 0, 0, 0.15);
  filter: brightness(1.1);
}}

/* ---- Login brand tick ---- */
.da-login-tick {{
  font-size: 3.5rem;
  color: {RED};
  line-height: 1;
  filter: drop-shadow(0 0 8px rgba(235, 34, 41, 0.30));
}}

/* ---- Login brand name with gradient ---- */
.da-login-name {{
  font-size: 1.8rem;
  font-weight: 900;
  background: linear-gradient(135deg, {GREEN}, {RED});
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-top: 6px;
}}

/* ---- Login tagline with subtle glow ---- */
.da-login-tagline {{
  font-size: 0.85rem;
  color: {RED};
  font-weight: 500;
  margin-top: 4px;
  margin-bottom: 18px;
  font-style: italic;
  text-shadow: 0 0 4px rgba(235, 34, 41, 0.20);
}}

/* ---- Enhanced login tagline: neon pill badge ---- */
.da-login-tagline.da-neon-badge {{
  display: inline-block;
  padding: 4px 16px;
  background: rgba(235, 34, 41, 0.15);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(235, 34, 41, 0.30);
  border-radius: 20px;
  box-shadow: 0 0 12px rgba(235, 34, 41, 0.25);
  animation: da-pulse 3s ease-in-out infinite;
}}

/* ---- Login page gradient header ---- */
.da-login-header {{
  background: linear-gradient(135deg, {GREEN} 0%, {RED} 50%, {BLUE} 100%);
  padding: 16px 24px;
  border-radius: 14px;
  margin-bottom: 16px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.15);
  text-align: center;
}}
.da-login-header h1 {{
  color: {WHITE} !important;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.30);
  font-size: 1.6rem;
}}
.da-login-header .da-accent-line {{
  margin: 12px auto;
  opacity: 0.7;
}}

/* ---- Login page full gradient background ---- */
[data-testid="stApp"] .main {{
  background: radial-gradient(circle at 30% 30%, rgba(235, 34, 41, 0.06) 0%, transparent 50%),
              radial-gradient(circle at 80% 70%, rgba(15, 79, 56, 0.06) 0%, transparent 50%);
}}

/* ---- Login form glass card: neon border on hover ---- */
.da-login-form {{
  transition: box-shadow 0.25s ease, border-color 0.25s ease;
}}
.da-login-form:hover {{
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.16), inset 0 1px 0 rgba(255, 255, 255, 0.50);
  border-color: rgba(235, 34, 41, 0.40);
}}

/* ---- Enhanced status badges: focus ring + transition ---- */
.da-badge {{
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}}
.da-badge:focus-visible {{
  outline: 2px solid var(--da-blue);
  outline-offset: 2px;
}}
.da-badge--green:focus-visible  {{ outline-color: {GREEN}; }}
.da-badge--red:focus-visible    {{ outline-color: {RED}; }}
.da-badge--blue:focus-visible   {{ outline-color: {BLUE}; }}
.da-badge--amber:focus-visible  {{ outline-color: #b05a00; }}

/* ---- Enhanced metric cards: trend indicator + hover ---- */
.da-metric {{
  transition: box-shadow 0.15s ease, transform 0.05s ease;
  cursor: default;
}}
.da-metric:hover {{
  box-shadow: var(--da-shadow);
}}
.da-metric .da-metric-trend {{
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-top: 4px;
}}
.da-metric .da-metric-trend.pos {{ color: var(--da-green); }}
.da-metric .da-metric-trend.neg {{ color: var(--da-red); }}
.da-metric .da-metric-trend.neutral {{ color: var(--da-text-muted); }}
.da-metric .da-metric-trend svg {{
  width: 10px;
  height: 10px;
  fill: currentColor;
}}
.da-metric--accent-green {{ border-left-color: var(--da-green); }}
.da-metric--accent-yellow {{ border-left-color: #d97706; }}
.da-metric--accent-gray {{ border-left-color: #6b7280; }}

/* ---- Enhanced data tables: sticky header + responsive ---- */
.da-table-wrap {{
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid var(--da-border);
}}
.da-table {{
  width: 100%;
  min-width: 600px;
  border-collapse: separate;
  border-spacing: 0;
}}
.da-table thead th {{
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--da-blue);
  color: var(--da-white);
  font-weight: 700;
  text-align: left;
  padding: 9px 10px;
  border: none;
  font-size: 0.76rem;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}}
.da-table tbody td {{
  padding: 8px 10px;
  border-bottom: 1px solid var(--da-border);
  vertical-align: middle;
}}
.da-table tbody tr:hover td {{
  background: var(--da-blue-10);
}}
.da-table tbody tr:last-child td {{
  border-bottom: none;
}}
.da-table td.da-cell--green {{ color: var(--da-green); font-weight: 700; }}
.da-table td.da-cell--red   {{ color: var(--da-red);   font-weight: 700; }}
.da-table td.da-cell--blue  {{ color: var(--da-blue);  font-weight: 700; }}
.da-table td.da-cell--amber {{ color: #b05a00; font-weight: 700; }}
.da-table td.da-cell--muted {{ color: var(--da-text-muted); font-weight: 500; }}
.da-table .da-table-action {{
  white-space: nowrap;
  text-align: center;
}}
.da-table .da-metric--inline {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
}}

/* ---- Enhanced tabs: pill variant + hover + focus ---- */
button[data-baseweb="tab"] {{
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}}
button[data-baseweb="tab"]:hover {{
  background: var(--da-bg-subtle);
}}
button[data-baseweb="tab"]:focus-visible {{
  outline: 2px solid var(--da-blue);
  outline-offset: -1px;
}}
.da-tabs-pill button[data-baseweb="tab"] {{
  border-radius: 6px 6px 0 0;
  margin-right: 4px;
}}
.da-tabs-pill button[data-baseweb="tab"][aria-selected="true"] {{
  background: var(--da-blue);
  color: var(--da-white);
  border-bottom-color: var(--da-blue);
}}

/* ---- Enhanced forms: multiselect, checkbox, radio, toggle ---- */
.stMultiselect [data-baseweb="select"] {{
  border-radius: 6px !important;
}}
.stMultiselect [data-baseweb="select"]:focus-within {{
  outline: 2px solid var(--da-green);
  outline-offset: 1px;
}}
.stCheckbox [data-baseweb="checkbox"] {{
  margin-bottom: 6px;
}}
.stCheckbox [data-baseweb="checkbox"] focus {{
  outline: 2px solid var(--da-green);
  outline-offset: 2px;
}}
.stRadio [data-baseweb="radio"] {{
  gap: 8px;
}}
.stRadio [data-baseweb="radio"] input:checked {{
  accent-color: var(--da-green);
}}
.da-toggle {{
  position: relative;
  display: inline-block;
  width: 42px;
  height: 22px;
}}
.da-toggle input {{
  opacity: 0;
  width: 0;
  height: 0;
}}
.da-toggle .da-toggle-slider {{
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--da-border);
  transition: 0.25s;
  border-radius: 999px;
}}
.da-toggle .da-toggle-slider:before {{
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background-color: var(--da-white);
  transition: 0.25s;
  border-radius: 50%;
}}
.da-toggle input:checked + .da-toggle-slider {{
  background-color: var(--da-green);
}}
.da-toggle input:checked + .da-toggle-slider:before {{
  transform: translateX(20px);
}}

/* ---- Enhanced buttons: disabled, icon, loading states ---- */
.da-btn:disabled {{
  opacity: 0.5;
  cursor: not-allowed;
}}
.da-btn:disabled:hover {{
  transform: none;
}}
.da-btn--icon {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 0.8rem;
  border-radius: 6px;
}}
.da-btn--icon.da-btn--primary {{
  background: var(--da-red);
  color: var(--da-white);
}}
.da-btn--icon.da-btn--secondary {{
  background: var(--da-green);
  color: var(--da-white);
}}
.da-btn--sm  {{ padding: 4px 10px; font-size: 0.72rem; }}
.da-btn--md  {{ padding: 8px 16px; font-size: 0.82rem; }}
.da-btn--lg  {{ padding: 11px 22px; font-size: 0.92rem; }}
.da-btn--block {{
  display: block;
  width: 100%;
  justify-content: center;
}}

/* ---- Enhanced form fields: select dropdown + focus ---- */
.stSelectbox [data-baseweb="select"] input:focus,
.stMultiSelect [data-baseweb="select"] input:focus {{
  outline: 2px solid var(--da-green) !important;
  outline-offset: 1px !important;
}}
.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus {{
  outline: 2px solid var(--da-green);
  outline-offset: 1px;
  border-color: var(--da-green);
  box-shadow: 0 0 0 2px var(--da-green-10);
}}

/* ---- Enhanced tabs: focus-visible ---- */
button[data-baseweb="tab"][aria-selected="true"]:focus-visible {{
  outline: 2px solid var(--da-red);
  outline-offset: -1px;
}}

/* ---- Enhanced data tables: focus ---- */
.da-table td:focus-visible,
.da-table th:focus-visible {{
  outline: 2px solid var(--da-blue);
  outline-offset: -1px;
}}

/* ================================================================
   FUTURISTIC / GLASSMORPHISM ENHANCEMENTS
   ================================================================ */

/* ---- Glassmorphism container ---- */
.da-glass {{
  background: rgba(255, 255, 255, 0.18);
  border-radius: 14px;
  backdrop-filter: blur(12px) saturate(180%);
  -webkit-backdrop-filter: blur(12px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.24);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.10);
}}

/* ---- Gradient section backgrounds ---- */
.da-gradient-header {{
  background: linear-gradient(135deg, {GREEN} 0%, {BLUE} 50%, {RED} 100%);
  padding: 18px 24px;
  border-radius: 14px;
  margin-bottom: 16px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.15);
}}
.da-gradient-header h1,
.da-gradient-header h2 {{
  color: {WHITE} !important;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.30);
}}

/* ---- Floating metric cards ---- */
.da-metric {{
  background: rgba(255, 255, 255, 0.42);
  backdrop-filter: blur(10px);
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.30);
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.40);
  transform: translateY(0);
  transition:
    transform 0.20s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.20s cubic-bezier(0.4, 0, 0.2, 1),
    border-color 0.20s ease;
}}
.da-metric:hover {{
  transform: translateY(-3px);
  box-shadow:
    0 12px 32px rgba(0, 0, 0, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.50);
}}
.da-metric--accent-green {{
  border-left: 4px solid {GREEN};
  box-shadow: 0 0 12px rgba(15, 79, 56, 0.12);
}}
.da-metric--accent-red {{
  border-left: 4px solid {RED};
  box-shadow: 0 0 12px rgba(235, 34, 41, 0.12);
}}
.da-metric--accent-blue {{
  border-left: 4px solid {BLUE};
  box-shadow: 0 0 12px rgba(0, 86, 122, 0.12);
}}

/* ---- Neon badge glow ---- */
.da-badge {{
  box-shadow: 0 0 0 0px rgba(0, 0, 0, 0);
  transition: box-shadow 0.25s ease, transform 0.15s ease;
}}
.da-badge:hover {{
  transform: translateY(-1px);
}}
.da-badge--green:hover {{ box-shadow: 0 0 8px rgba(15, 79, 56, 0.40); }}
.da-badge--red:hover   {{ box-shadow: 0 0 8px rgba(235, 34, 41, 0.40); }}
.da-badge--blue:hover  {{ box-shadow: 0 0 8px rgba(0, 86, 122, 0.40); }}
.da-badge--amber:hover {{ box-shadow: 0 0 8px rgba(176, 90, 0, 0.40); }}

/* ---- Neon button hover ---- */
.da-btn:hover {{
  transform: translateY(-1px);
}}
.da-btn--primary:hover {{
  box-shadow: 0 0 16px rgba(235, 34, 41, 0.35), 0 4px 12px rgba(0, 0, 0, 0.12);
}}
.da-btn--secondary:hover {{
  box-shadow: 0 0 16px rgba(15, 79, 56, 0.25), 0 4px 12px rgba(0, 0, 0, 0.10);
}}

/* ---- Animated tab underline ---- */
button[data-baseweb="tab"][aria-selected="true"] {{
  border-bottom: 3px solid var(--da-red);
  color: var(--da-red);
  font-weight: 700;
  position: relative;
}}
button[data-baseweb="tab"][aria-selected="true"]::after {{
  content: '';
  position: absolute;
  bottom: -3px;
  left: 8px;
  right: 8px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--da-red), transparent);
}}

/* ---- Pulse animation for alerts ---- */
@keyframes da-pulse {{
  0%   {{ opacity: 1; transform: scale(1); }}
  50%  {{ opacity: 0.7; transform: scale(1.03); }}
  100% {{ opacity: 1; transform: scale(1); }}
}}
.da-pulse {{
  animation: da-pulse 2s ease-in-out infinite;
}}

/* ---- Gradient data table header ---- */
.da-table thead th {{
  background: linear-gradient(135deg, {BLUE} 0%, {GREEN} 100%);
}}

/* ---- Chart container glass frame ---- */
.da-chart-frame {{
  background: rgba(255, 255, 255, 0.35);
  backdrop-filter: blur(8px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  padding: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}}

/* ---- Expander header styling ---- */
.streamlit-expander:not(.summary) > .da-glass {{
  background: rgba(250, 250, 252, 0.50);
}}

/* ---- Status badges with neon pulse for critical ---- */
.da-badge--red.da-pulse {{
  animation: da-pulse 1.2s ease-in-out infinite;
}}

/* ---- Form field focus glow ---- */
.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus {{
  box-shadow: 0 0 0 3px {GREEN_10}, 0 0 8px rgba(15, 79, 56, 0.20);
}}

/* ---- Sidebar nav hover glow ---- */
section[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] label:hover {{
  color: {RED} !important;
  transform: x-offset 4px;
}}

/* ---- Decorative accent line ---- */
.da-accent-line {{
  height: 3px;
  background: linear-gradient(90deg, {GREEN}, {RED}, {BLUE});
  border-radius: 2px;
  margin: 12px 0;
}}

/* ---- Metric value gradient text ---- */
[data-testid="stMetricValue"] {{
  background: linear-gradient(135deg, {GREEN}, {BLUE});
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}

/* ---- Hover lift for dataframes ---- */
.stDataFrame {{
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  transition: box-shadow 0.20s ease;
}}
.stDataFrame:hover {{
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.10);
}}

/* ---- Decorative corner accents ---- */
.da-card {{
  position: relative;
  border-radius: 12px;
  overflow: hidden;
}}
.da-card::before {{
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
  background: linear-gradient(to bottom, {GREEN}, {RED});
}}
.da-card::after {{
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: linear-gradient(90deg, {GREEN}, {RED}, {BLUE});
}}

</style>"""



# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def inject_brand_css() -> None:
    """Inject Definite Assurance brand styles. Call once after st.set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Logo image — SVG assets loaded once and encoded as base64 data URIs
# ---------------------------------------------------------------------------

_LOGO_URIS: dict[str, str] = {}


def _load_logos() -> None:
    """Read SVG logo files from assets/ and cache as base64 data URIs."""
    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for variant, fname in (
        ("color", "Definite Assurance Logo new-01.svg"),
        ("white", "Definite Assurance Logo new-07.svg"),
    ):
        path = os.path.join(app_root, "assets", fname)
        try:
            with open(path, "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode()
                _LOGO_URIS[variant] = f"data:image/svg+xml;base64,{b64}"
        except OSError:
            pass  # CSS wordmark fallback used when asset is missing


_load_logos()


def _logo_img(variant: str = "color", width_px: int = 220) -> str:
    """Return an <img> tag embedding the SVG logo as a base64 data URI.

    Falls back to the CSS HTML wordmark (_logo_html) when the SVG asset
    is not present in assets/.
    """
    uri = _LOGO_URIS.get(variant, "")
    if not uri:
        return _logo_html(size_px=round(width_px * 0.25), variant=variant)
    return (
        f'<img src="{uri}" width="{width_px}" '
        f'alt="Definite Assurance" '
        f'style="display:inline-block;max-width:100%;vertical-align:middle;">'
    )


def brand_strip() -> None:
    """Render the top-of-page brand strip with the Definite Assurance logo."""
    st.markdown(
        f'<div class="da-strip">{_logo_img(variant="color", width_px=190)}</div>',
        unsafe_allow_html=True,
    )


def brand_login_header() -> None:
    """Render the branded heading on the login / landing page."""
    st.markdown(
        f"""
        <div class="da-login-header da-glass">
          <div style="display:flex; align-items:center; justify-content:center; gap:10px;">
            {_logo_img(variant="color", width_px=200)}
          </div>
          <h1 style="margin: 12px 0 4px 0; font-size: 1.8rem;">Definite Assurance</h1>
          <div class="da-accent-line"></div>
          <div class="da-login-tagline da-neon-badge">You Are Definitely Covered</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def brand_sidebar_header() -> None:
    """Render the sidebar brand block (logo on Aberdare Green background)."""
    st.markdown(
        f"""
        <div class="da-glass" style="padding: 12px 8px; text-align: center; border-radius: 12px; margin-bottom: 12px;">
          <div style="display: inline-block;">{_logo_img(variant="white", width_px=155)}</div>
          <div class="da-accent-line" style="margin: 8px 0; opacity: 0.5;"></div>
          <div class="da-login-tagline da-neon-badge" style="font-size:0.75rem; padding:3px 12px; margin-top:4px;">
            You Are Definitely Covered
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
