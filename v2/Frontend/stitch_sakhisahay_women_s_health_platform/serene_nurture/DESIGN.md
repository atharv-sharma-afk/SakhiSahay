---
name: Serene Nurture
colors:
  surface: '#fff7fd'
  surface-dim: '#e3d6e7'
  surface-bright: '#fff7fd'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fcefff'
  surface-container: '#f7e9fb'
  surface-container-high: '#f2e4f5'
  surface-container-highest: '#ecdef0'
  on-surface: '#201925'
  on-surface-variant: '#534246'
  inverse-surface: '#362d3b'
  inverse-on-surface: '#faecfe'
  outline: '#867276'
  outline-variant: '#d8c1c5'
  surface-tint: '#94445b'
  primary: '#914259'
  on-primary: '#ffffff'
  primary-container: '#af5a71'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb1c3'
  secondary: '#5f5d69'
  on-secondary: '#ffffff'
  secondary-container: '#e5e0ef'
  on-secondary-container: '#65636f'
  tertiary: '#525f57'
  on-tertiary: '#ffffff'
  tertiary-container: '#6b786f'
  on-tertiary-container: '#f5fff6'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffd9e0'
  primary-fixed-dim: '#ffb1c3'
  on-primary-fixed: '#3f0119'
  on-primary-fixed-variant: '#772d44'
  secondary-fixed: '#e5e0ef'
  secondary-fixed-dim: '#c9c4d3'
  on-secondary-fixed: '#1c1a25'
  on-secondary-fixed-variant: '#474551'
  tertiary-fixed: '#d8e6db'
  tertiary-fixed-dim: '#bccabf'
  on-tertiary-fixed: '#121e17'
  on-tertiary-fixed-variant: '#3d4a42'
  background: '#fff7fd'
  on-background: '#201925'
  surface-variant: '#ecdef0'
typography:
  headline-xl:
    fontFamily: Manrope
    fontSize: 40px
    fontWeight: '600'
    lineHeight: 52px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Manrope
    fontSize: 30px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.015em
  headline-lg:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.015em
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 34px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Manrope
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 28px
  body-lg:
    fontFamily: Manrope
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
  body-sm:
    fontFamily: Manrope
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  label-lg:
    fontFamily: Manrope
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Manrope
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Manrope
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.025em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2.5rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system expresses a sanctuary of digital healthcare: calm, empathetic, trustworthy, and subtly empowering. Blending clinical precision with holistic wellness sensibilities, it balances clinical authority with tactile, organic softness.

The aesthetic philosophy centers on warm minimalism accented by soft wellness tones. Rather than cold, sterile hospital whites and rigid lines, interfaces feature comforting, grounded surfaces, deep plum typographic clarity, and restorative botanical undertones. The visual mood evokes deep exhale, quiet support, and intuitive health autonomy.

## Colors

The palette balances warmth, restorative care, and clinical reliability:

- **Primary Accent (`#C96F87`)**: Muted rose, driving key actions, vital cycle markers, and brand focus without aggressive urgency.
- **Primary Tint / Soft Blush (`#F9E9ED`)**: Used for supportive backdrops, active tab pills, and subtle highlights.
- **Secondary Accent (`#EDE8F7`)**: Calming lavender, representing reflection, mental wellness, and nocturnal/hormonal context.
- **Tertiary Accent / Restorative Status (`#DDEBE0`)**: Sage green, used for positive health milestones, safe clinical indicators, and fertility windows.
- **Surfaces & Canvases**: The foundational canvas rests on `#FAF8F7`, with raised cards elevated in `#FFFFFF`, and resting sections tinted in `#FFFBF7` (warm cream).
- **Text & Details**: High-contrast legibility is maintained with deep plum (`#332B38`) for headlines and body text, anchored by soft muted plum-gray (`#77717B`) for secondary metadata and soft rose-gray (`#EFE7EB`) for borders.

## Typography

Manrope provides geometric balance softened by open apertures, evoking clinical clarity and warmth. 

Headings rely on medium to semi-bold weights (`500` and `600`) to remain authoritative without appearing aggressive or heavy. Generous line heights ensure readability for sensitive medical tracking, symptom journals, and clinical consultation recaps across viewports.

## Layout & Spacing

A 12-column responsive fluid grid anchors desktop experiences, collapsing to an 8-column layout on tablet and a 4-column layout on mobile viewports.

Layout rhythms lean on generous spacing to avoid visual fatigue:
- **Desktop (≥1024px)**: 40px outer canvas margins, 24px column gutters, max content container width of 1280px centered.
- **Tablet (768px - 1023px)**: 24px margins, 16px column gutters.
- **Mobile (<768px)**: 16px margins, 16px gutters, allowing cycle dial visualizations and quick-log tiles to take comfortable thumb-reach priority.

## Elevation & Depth

Visual hierarchy uses warm, ambient diffusion and subtle outlines rather than harsh shadows:

- **Surface Level 0 (Base Canvas)**: `#FAF8F7`, completely flat.
- **Surface Level 1 (Resting Cards & Tiles)**: Pure white `#FFFFFF` or `#FFFBF7` with a delicate 1px border (`#EFE7EB`) and an ultra-soft tinted ambient shadow (`box-shadow: 0 4px 20px -2px rgba(51, 43, 56, 0.04)`).
- **Surface Level 2 (Floating Modals, Flyouts & Action Sheets)**: Elevated `#FFFFFF` with `box-shadow: 0 12px 32px -4px rgba(51, 43, 56, 0.08)`, reinforced by 1px `#EFE7EB` hairline borders.
- **Depth Layers**: Circular dial trackers and nested symptom filters use warm blush (`#F9E9ED`) and lavender (`#EDE8F7`) background fills at 0px elevation to indicate categorization without layering physical shadows.

## Shapes

The interface embraces organic curvature to foster an approachable, human atmosphere:
- Standard content cards feature 16px to 24px radius corners (`rounded-lg` to `rounded-xl`).
- Buttons, badge chips, and navigation segments use full pill radiuses (`rounded-full` / `9999px`) to soften interaction points.
- Circular tracker components (such as ovulation/period phase rings) maintain pure 1:1 circular proportions with soft cap ends.

## Components

### Buttons
- **Primary Button**: Solid `#C96F87` background, `#FFFFFF` text, pill shape, height 48px (mobile 44px), subtle shadow on hover (`0 4px 14px rgba(201, 111, 135, 0.25)`).
- **Secondary Button**: Soft blush background `#F9E9ED`, `#C96F87` text, no shadow, subtle `#C96F87` opacity border on active/hover.
- **Ghost/Tertiary**: Transparent background, `#332B38` text, hover fills with `#FFFBF7`.

### Chips & Badges
- Pill-shaped (`rounded-full`), padding 6px 14px, typography `label-md`.
- **Status/Cycle Badges**: Sage green `#DDEBE0` with dark sage text for fertile/safe indicators; Lavender `#EDE8F7` for luteal/mood logs; Muted Rose `#F9E9ED` for period phase alerts.

### Cards & Panels
- Primary cards: 1px hairline border in `#EFE7EB`, pure white background, 20px corner radius, internal padding of 20px to 28px.
- Consultation or alert cards: Cream background `#FFFBF7`, soft border, integrated primary accent icons.

### Inputs & Form Controls
- Text Inputs: 48px height, rounded 12px corners, `#FFFFFF` background, 1px `#EFE7EB` border. Focus state shifts to 1.5px `#C96F87` ring with `rgba(201, 111, 135, 0.15)` outer glow.
- Checkboxes & Radios: Rounded corners (4px for checkboxes, full circle for radios), `#C96F87` active fill with crisp `#FFFFFF` check/dot icons.

### Circular Cycle Tracker & Symptom Rings
- Dynamic concentric SVG rings with 8px to 12px stroke widths, rounded caps, tracking follicular, ovulatory, and luteal phases using `#C96F87`, `#DDEBE0`, and `#EDE8F7`. Center displays day count in `headline-xl` (`#332B38`) with phase label in `label-md` (`#77717B`).