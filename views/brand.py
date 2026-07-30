"""Brand identity module Ã¢ÂÂ Definite Assurance Co. Ltd.

Injects CSS and provides branded Streamlit components aligned to the
official Brand Identity Guidelines v0.1 (February 2025).

Palette
-------
Aberdare Green  #0f4f48   primary Ã¢ÂÂ trust, growth, security
Uhuru Red       #eb2229   primary Ã¢ÂÂ urgency, assurance tick
Solid Black     #000000
Urban White     #ffffff

Typography
----------
Primary : Gotham (clean, modern sans-serif)
Fallback: Roboto (served via Google Fonts)
Headlines   : Gotham Ultra / Roboto Black   Ã¢ÂÂ¥24 pt
Subheaders  : Gotham Bold  / Roboto Bold    16-24 pt
Body        : Gotham Book  / Roboto Regular 12-16 pt
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
BLACK    = "#000000"
WHITE    = "#ffffff"
GREEN_70 = "#3e756f"   # Aberdare Green 70 % tint
GREEN_30 = "#a8c7c4"   # Aberdare Green 30 % tint
GREEN_10 = "#e5f0ef"   # Aberdare Green 10 % tint
RED_70   = "#f17075"   # Uhuru Red 70 % tint
RED_10   = "#fce8e9"   # Uhuru Red 10 % tint

# ---------------------------------------------------------------------------
# Extended palette Ã¢ÂÂ tints for charts and data-vis
# ---------------------------------------------------------------------------
# Ordered brand colorway (categorical charts Ã¢ÂÂ 8 stops)
DA_COLORWAY: list[str] = [
    GREEN,       # Aberdare Green       Ã¢ÂÂ primary positive
    RED,         # Uhuru Red            Ã¢ÂÂ primary accent / alert
    GREEN_70,    # Green 70 %           Ã¢ÂÂ secondary positive
    RED_70,      # Red 70 %             Ã¢ÂÂ secondary accent
    GREEN_30,    # Green 30 %           Ã¢ÂÂ tertiary positive
    "#1a8f87",   # Bright teal          Ã¢ÂÂ extra accent
    "#c41e24",   # Darker red           Ã¢ÂÂ emphasis
    GREEN_10,    # Green 10 %           Ã¢ÂÂ background tint
]

# Sequential scale: Aberdare Green Ã¢ÂÂ neutral Ã¢ÂÂ Uhuru Red
# Low = good/fast (green), high = urgent/slow (red)
DA_SCALE_GREEN_RED: list[list] = [
    [0.00, GREEN],    # best Ã¢ÂÂ brand green
    [0.40, GREEN_30], # mid-low
    [0.70, RED_70],   # mid-high
    [1.00, RED],      # worst Ã¢ÂÂ Uhuru Red
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


# Auto-register on import Ã¢ÂÂ any module importing brand gets the theme for free
register_plotly_theme()


# ---------------------------------------------------------------------------
# Logo HTML component
# ---------------------------------------------------------------------------

def _logo_html(size_px: int = 56, variant: str = "color") -> str:
    """Return self-contained HTML for the Definite Assurance wordmark.

    Renders the stylised D-with-checkmark + Ã¢ÂÂefiniteÃ¢ÂÂ in Aberdare Green
    and Ã¢ÂÂASSURANCEÃ¢ÂÂ in Uhuru Red below, matching the official logo mark.

    Args:
        size_px : Cap-height in px for the Ã¢ÂÂDefiniteÃ¢ÂÂ wordmark.
        variant : Ã¢ÂÂcolorÃ¢ÂÂ for the full-colour version;
                  Ã¢ÂÂwhiteÃ¢ÂÂ for all-white on dark/green backgrounds.
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
        # Ã¢ÂÂ Row 1: DÃ¢ÂÂ + efinite Ã¢ÂÂ
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
        # Ã¢ÂÂ Row 2: ASSURANCE Ã¢ÂÂ
        f'<div style="font-size:{assure_px}px;font-weight:700;color:{assure_col};'
        f'letter-spacing:0.38em;margin-top:{gap_top}px;padding-left:2px;">'
        f'ASSURANCE</div>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
_CSS = f"""
<style>
/* Ã¢ÂÂÃ¢ÂÂ Google Fonts: Roboto (Gotham system fallback) Ã¢ÂÂÃ¢ÂÂ */
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap');

/* Ã¢ÂÂÃ¢ÂÂ Global font Ã¢ÂÂÃ¢ÂÂ */
html, body, [class*="css"] {{
  font-family: 'Gotham', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
}}

/* Ã¢ÂÂÃ¢ÂÂ Sidebar Ã¢ÂÂ Aberdare Green background Ã¢ÂÂÃ¢ÂÂ */
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
}}

/* Ã¢ÂÂÃ¢ÂÂ Primary action buttons Ã¢ÂÂ Uhuru Red Ã¢ÂÂÃ¢ÂÂ */
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

/* Ã¢ÂÂÃ¢ÂÂ Form submit button (also primary intent) Ã¢ÂÂÃ¢ÂÂ */
button[data-testid="baseButton-secondaryFormSubmit"],
button[data-testid="baseButton-primaryFormSubmit"] {{
  background-color: {RED} !important;
  color: {WHITE} !important;
  border: none !important;
  font-weight: 700 !important;
}}

/* Ã¢ÂÂÃ¢ÂÂ Metric cards Ã¢ÂÂÃ¢ÂÂ */
[data-testid="stMetricValue"] {{
  color: {GREEN} !important;
  font-weight: 700 !important;
}}

/* Ã¢ÂÂÃ¢ÂÂ Active tab indicator Ã¢ÂÂÃ¢ÂÂ */
button[data-baseweb="tab"][aria-selected="true"] {{
  border-bottom: 3px solid {RED} !important;
  color: {RED} !important;
  font-weight: 700 !important;
}}

/* Ã¢ÂÂÃ¢ÂÂ Page headings Ã¢ÂÂÃ¢ÂÂ */
h1 {{ color: {GREEN} !important; font-weight: 900 !important; }}
h2 {{ color: {GREEN} !important; font-weight: 700 !important; }}
h3 {{ color: {BLACK} !important; font-weight: 700 !important; }}

/* Ã¢ÂÂÃ¢ÂÂ Horizontal divider tinted red Ã¢ÂÂÃ¢ÂÂ */
hr {{
  border-top: 2px solid {RED} !important;
  opacity: 0.35;
}}

/* Ã¢ÂÂÃ¢ÂÂ Brand strip (top-of-page header) Ã¢ÂÂÃ¢ÂÂ */
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

/* Ã¢ÂÂÃ¢ÂÂ Login page Ã¢ÂÂÃ¢ÂÂ */
.da-login-wrap {{
  text-align: center;
  padding: 20px 0 4px 0;
}}
.da-login-tick {{
  font-size: 3.5rem;
  color: {RED};
  line-height: 1;
}}
.da-login-name {{
  font-size: 1.6rem;
  font-weight: 900;
  color: {GREEN};
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-top: 6px;
}}
.da-login-tagline {{
  font-size: 0.82rem;
  color: {RED};
  font-weight: 500;
  margin-top: 2px;
  margin-bottom: 18px;
  font-style: italic;
}}
</style>
"""


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def inject_brand_css() -> None:
    """Inject Definite Assurance brand styles. Call once after st.set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Logo image Ã¢ÂÂ SVG assets loaded once and encoded as base64 data URIs
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
        <div class="da-login-wrap">
          {_logo_img(variant="color", width_px=250)}
          <div class="da-login-tagline">You Are Definitely Covered</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def brand_sidebar_header() -> None:
    """Render the sidebar brand block (logo on Aberdare Green background)."""
    st.markdown(
        f"""
        <div style="padding: 8px 0 4px 0; text-align:center;">
          <div style="display:inline-block;">{_logo_img(variant="white", width_px=155)}</div>
          <div style="font-size:0.7rem; color:rgba(255,255,255,0.7); font-style:italic; margin-top:4px;">
            You Are Definitely Covered
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
