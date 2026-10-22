# Definite Assurance — Claims Portal Design System

> **Brand Identity Guidelines v0.1** · February 2025
> Insurance Claims Management Portal for the Kenyan market
> Built with Streamlit · Python 3.11+ · SQLite / Supabase / Databricks

---

## 1. Brand Overview

| Attribute       | Value                                         |
|-----------------|-----------------------------------------------|
| **Company**     | Definite Assurance Co. Ltd.                   |
| **Tagline**     | You Are Definitely Covered                    |
| **Logo Mark**   | D✓ wordmark in Aberdare Green + Uhuru Red     |
| **Markets**     | Kenya (Nairobi, Kiambu, Kisumu, Mombasa, etc.)|
| **Regulatory**  | Insurance Act Cap 111 · DPA 2019 · IRA regs   |

---

## 2. Palette

### 2.1 Primary Colors

| Name              | Hex        | Usage                              |
|-------------------|------------|------------------------------------|
| **Aberdare Green**| `#0f4f48`  | Primary brand, trust, growth, security |
| **Uhuru Red**     | `#eb2229`  | Accent, urgency, action buttons, alerts |
| **Solid Black**   | `#000000`  | Headlines, body text               |
| **Urban White**   | `#ffffff`  | Backgrounds, card surfaces         |

### 2.2 Extended Palette (tints for charts & data-vis)

| Name           | Hex        | Usage                                  |
|----------------|------------|----------------------------------------|
| Green 70% tint | `#3e756f`  | Secondary positive data                |
| Green 30% tint | `#a8c7c4`  | Tertiary positive, background fills    |
| Green 10% tint | `#e5f0ef`  | Light backgrounds, chart backgrounds   |
| Red 70% tint   | `#f17075`  | Secondary accent, warnings             |
| Red 10% tint   | `#fce8e9`  | Alert backgrounds                      |
| Bright teal    | `#1a8f87`  | Extra accent color for charts          |
| Darker red     | `#c41e24`  | Emphasis, hover states                 |

### 2.3 Semantic Color Mapping

| Semantic Role       | Color Variable   | Hex        |
|---------------------|------------------|------------|
| Success / Positive  | `GREEN`          | `#0f4f48`  |
| Error / Alert       | `RED`            | `#eb2229`  |
| Background (page)   | `WHITE`          | `#ffffff`  |
| Background (sidebar)| `GREEN`          | `#0f4f48`  |
| Text (primary)      | `BLACK`          | `#000000`  |
| Text (secondary)    | `#777777`        | `#777777`  |
| Border / Divider    | `#e0e0e0`        | `#e0e0e0`  |
| Metric value color  | `GREEN`          | `#0f4f48`  |

### 2.4 Chart Colorways

#### Categorical (DA_COLORWAY)
Used for bar, pie, and scatter categorical charts — 8 stops:

```
#0f4f48, #eb2229, #3e756f, #f17075, #a8c7c4, #1a8f87, #c41e24, #e5f0ef
```

#### Sequential (DA_SCALE_GREEN_RED)
Used for heat maps and color-encoded data (green = good/fast, red = urgent/slow):

| Position | Color        | Meaning          |
|----------|--------------|------------------|
| 0.00     | `#0f4f48`    | Best — brand green |
| 0.40     | `#a8c7c4`    | Mid-low           |
| 0.70     | `#f17075`    | Mid-high          |
| 1.00     | `#eb2229`    | Worst — Uhuru Red |

---

## 3. Typography

| Role        | Font Family Chain                                      | Size Range | Weight      |
|-------------|--------------------------------------------------------|------------|-------------|
| Headlines   | Gotham / Roboto Black                                  | ≥ 24 pt    | 900 (Ultra) |
| Subheaders  | Gotham / Roboto Bold                                   | 16–24 pt   | 700 (Bold)  |
| Body text   | Gotham / Roboto Regular                                | 12–16 pt   | 400 (Regular)|
| UI labels   | Gotham / Roboto Medium                                 | 11–13 pt   | 500 (Medium)|
| Metric cards| Roboto                                                 | auto       | 700 (Bold)  |

**Google Fonts:** Roboto (weights 300, 400, 500, 700, 900) loaded via CSS `@import`.

---

## 4. Layout

### 4.1 Page Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Brand Strip (logo + tagline)                               │
│  ──────────────────────────────────────────────────────     │
│  Sidebar (Aberdare Green bg)                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Role label • User email                               │  │
│  │ Sign Out button                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  Main Content Area (white bg)                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Title + status badges + action buttons                │  │
│  │ Tabs / expanders / forms                              │  │
│  │ Data tables, charts, metrics                          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Spacing

| Token     | Value | Usage                                  |
|-----------|-------|----------------------------------------|
| spacing-xs| 4px   | Icon spacing, tight badges             |
| spacing-sm| 8px   | Form field gaps, small padding         |
| spacing-md| 16px  | Section gaps, card padding              |
| spacing-lg| 24px  | Between major sections                  |
| spacing-xl| 32px  | Top/bottom page margins, hero spacing   |

### 4.3 Border Radius

| Element                  | Radius |
|--------------------------|--------|
| Primary buttons          | 4px     |
| Input fields             | 4px     |
| Card / expander headers  | 6px     |
| Metric cards             | 8px     |
| Logo container           | 12px    |

---

## 5. Components

### 5.1 Buttons

| Variant    | Background       | Text     | Border  | Hover                  |
|------------|------------------|----------|---------|------------------------|
| Primary    | `#eb2229` (Uhuru)| `#ffffff`| none    | `#c41e24` dark red     |
| Secondary  | `#ffffff`        | `#0f4f48`| none    | `#e5f0ef` green tint   |
| Ghost      | transparent       | `#0f4f48`| none    | `#e5f0ef` green tint   |

Primary buttons: `font-weight: 700`, `letter-spacing: 0.03em`, hover shadow `0 2px 6px rgba(235,34,41,0.35)`.

Form submit buttons use the same primary styling via `data-testid="baseButton-primaryFormSubmit"`.

### 5.2 Metric Cards

- Value text in **Aberdare Green** (`#0f4f48`), bold 700
- Label text in `#777777`, muted
- Background: white with subtle shadow

### 5.3 Data Tables

- Column headers: bold, `#555555`
- Row hover: `#e5f0ef` (green-10 tint)
- Borders: `#f0f0f0` (light gray)
- Numeric columns right-aligned

### 5.4 Tabs

- Active tab: 3px solid `#eb2229` (Uhuru Red), bold, red color
- Inactive tab: default styling
- Used in: Claims Officer (7 tabs), Finance (6 tabs), Service Provider (variable)

### 5.5 Expanders

- Header: bold, green text
- Body: white background with subtle border
- Used for: permission matrix, dispute details, timeline events

### 5.6 Status Badges

| Status                  | Color           | Style              |
|-------------------------|-----------------|--------------------|
| Submitted / FNOL        | `#0f4f48` Green | Solid green badge  |
| Assigned / Assessment   | `#1a8f87` Teal  | Solid teal badge   |
| Investigation           | `#f17075` Red tint | Solid badge       |
| Approved                | `#0f4f48` Green | Solid green badge  |
| Settled / Paid          | `#0f4f48` Green | Solid green badge  |
| Rejected / Repudiated   | `#eb2229` Red   | Solid red badge    |
| Pending                 | `#777777` Gray  | Solid gray badge   |

### 5.7 Alerts & Toasts

| Type   | Background   | Text Color | Icon |
|--------|--------------|------------|------|
| Success| `#e5f0ef`    | `#0f4f48`  | ✅    |
| Warning| `#fce8e9`    | `#eb2229`  | ⚠️    |
| Error  | `#fce8e9`    | `#c41e24`  | ❌    |
| Info   | `#e5f0ef`    | `#0f4f48`  | ℹ️    |

### 5.8 Forms

- Required fields marked with `*`
- Submit button: primary (Uhuru Red), full-width where appropriate
- Input fields: 4px border radius, `#cccccc` borders
- Disabled inputs: grayed out, `#f0f0f0` background

---

## 6. Charting

### 6.1 Plotly Theme

The `register_plotly_theme()` function creates a `definite_assurance` template:

- **Colorway**: `DA_COLORWAY` (primary green → red sequence)
- **Font**: Gotham/Roboto, `#333333`, size 12
- **Title**: Gotham Bold, `#0f4f48`, left-aligned
- **Grid**: `#f0f0f0` gridlines, `#cccccc` axis lines
- **Hover**: Aberdare Green background, white text
- **Paper/plot bg**: White (`#ffffff`)
- **Bar**: No marker lines
- **Scatter**: 2.5px lines, 6px markers
- **Pie**: White text on segments, green hover labels

### 6.2 Chart Types in Portal

| Chart                  | Type          | Color Scale          |
|------------------------|---------------|----------------------|
| Claims by Type         | Bar (categorical)| Set2                  |
| Status Distribution    | Donut (pie)   | Pastel               |
| Settlement Trend       | Line (multi)  | Green/Red mapping    |
| Avg Cycle Time         | Horizontal bar| RdYlGn reverse       |
| Reserve vs Actual      | Stacked bar   | Brand colorway       |
| Payments by Type       | Bar           | Brand colorway       |

---

## 7. Iconography

Icons are Unicode emojis embedded directly in Streamlit UI strings:

| Purpose                | Icon |
|------------------------|------|
| Claims list            | 📋    |
| My Claims (officer)    | 📥    |
| Assign Experts         | 👥    |
| Reserve Management     | 💼    |
| Settlement             | ✅    |
| Payment Authorisation  | 💸    |
| Correspondence         | 📨    |
| Bid Comparison         | 🏷️   |
| Dashboard              | 📊    |
| Analytics              | 📈    |
| Reports                | 📑    |
| RFQ Bids               | 🛒    |
| Legal / Litigation     | ⚖️    |
| Disputes               | ⚠️    |
| Payment Status         | 🔄    |
| Reconciliation         | 🔍    |

---

## 8. Logo Usage

### 8.1 Clear Space

The logo requires a minimum clear space of 1× the height of the "D" character (≈ 56px).

### 8.2 Variants

| Variant | File                          | Use Case                          |
|---------|-------------------------------|-----------------------------------|
| Color   | `Definite Assurance Logo new-01.svg` | Light backgrounds, default   |
| White   | `Definite Assurance Logo new-07.svg` | Aberdare Green sidebar bg    |
| Color   | `logo_color.svg`              | Fallback / alternate             |
| White   | `logo_white.svg`              | Fallback / alternate             |

### 8.3 Placement

- **Brand strip** (top of page): color logo on white background, width 190px
- **Sidebar header**: white logo on Aberdare Green background, width 155px
- **Login page**: color logo centered, width 250px

### 8.4 CSS Wordmark Fallback

When SVG assets are unavailable, a CSS-based wordmark renders the "D✓" + "efinite" + "ASSURANCE" using the brand colors and Gotham/Roboto font stack.

---

## 9. Kenya-Specific Domain Elements

### 9.1 Currency
- All monetary values in **Kenyan Shillings (KES)**
- Format: `KES {amount:,.0f}` (comma-separated thousands, no decimals for whole amounts)

### 9.2 Regulatory References
| Regulation               | Reference                          |
|--------------------------|------------------------------------|
| Insurance Act (Cap 111)  | Section 75: 14-day acknowledgment   |
|                          | Section 76: 30-day settlement       |
| Data Protection Act 2019 | Consent required for communications |
| IRA Regulations           | WHT rates by service provider type  |

### 9.3 WHT Rates (Kenya Revenue Authority)

| Provider Type   | Rate |
|-----------------|------|
| Assessor        | 5%   |
| Garage          | 5%   |
| Investigator    | 5%   |
| Spare Parts     | 10%  |
| Third Party     | 0%   |
| Insured         | 0%   |

---

## 10. Design Token Mapping (CSS → Streamlit → Code)

| Token                  | CSS Variable          | Streamlit / Python         | Hex     |
|------------------------|-----------------------|----------------------------|---------|
| color-primary          | var(--da-green)       | `GREEN` in code            | `#0f4f48` |
| color-accent           | var(--da-red)         | `RED` in code              | `#eb2229` |
| color-text-primary     | var(--da-black)       | `BLACK` in code            | `#000000` |
| color-text-secondary   | var(--da-gray)        | `"#777777"`                | `#777777` |
| color-background       | var(--da-white)       | `WHITE` in code            | `#ffffff` |
| color-border           | var(--da-border)      | `"#e0e0e0"` / `#e5f0ef`    | `#e0e0e0` |

---

## 11. Accessibility Notes

- Sidebar text uses white (`#ffffff`) on Aberdare Green background — WCAG AA compliant
- Primary buttons use Uhuru Red (`#eb2229`) on white — WCAG AA compliant
- Form inputs have visible borders (`#cccccc`)
- All interactive elements use `use_container_width=True` for touch targets
- Tables are scrollable within Streamlit containers
