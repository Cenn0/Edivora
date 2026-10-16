# Edivora branding and UI design references

## Brand banners

The README shows the matching banner for the viewer's light or dark color scheme. Both banners contain the established Edivora symbol and slogan; neither is a product screenshot.

- [Light banner](banner-light.svg)
- [Dark banner](banner-dark.svg)

Use the compact [logo](logo.svg) where a banner would be unsuitable (for example favicons and application icons). The banners are self-contained SVGs with no external assets. Their mark is embedded from the existing brand logo; the desktop application's compact icon stays unchanged.

**Status:** visual design concepts, not screenshots, shipped features, or evidence of product readiness.

| Asset | Purpose |
| --- | --- |
| [Logo](logo.svg) | Shared self-contained SVG brand mark |
| [Light design](design-light.svg) | Light-theme palette, layout and component reference |
| [Dark design](design-dark.svg) | Dark-theme palette, layout and component reference |

![Edivora light theme design concept](design-light.svg)

![Edivora dark theme design concept](design-dark.svg)

## Design tokens

| Token | Color |
| --- | --- |
| Primary | `#3B82F6` |
| Secondary | `#8B5CF6` |
| Accent | `#EC4899` |
| Highlight | `#FF9D25` |
| Support | `#25CDB6` |
| Dark surface | `#0C1A35` |
| Light surface | `#F7FAFF` |
| Light text | `#111D39` |
| Dark text | `#F4F8FF` |

Typeface: Inter with operating-system fallbacks. Base spacing grid: 8 px. Text, action and status colors require contrast testing. Never use color alone to convey status.

**Product-specific focus:** Photo, video and audio editing with local AI. The mock interface is **illustrative** and can contain workflows that are not yet implemented. Read the product README, architecture, roadmap, tests and security documentation before treating an element as supported.

## Integration contract

- Keep the existing build/runtime asset locations functional; the logo at the canonical location is shared by README, app and desktop/browser icon where applicable.
- Keep the light and dark SVGs as standalone design references; do not embed them as functional application UI.
- Use self-contained SVG with no remote fonts, scripts, images, tracking, or private details.
- Do not put access tokens, personal email addresses, real user records or internal infrastructure in public design assets.
- Validate accessibility (keyboard navigation, readable contrast, legible minimum size), localized text, mobile breakpoints and actual screenshots separately.
- **Trademark note:** these are project design assets; trademark distinctiveness and registration have not been legally verified. Do not claim exclusivity.

Only Edivora is covered here; designs from other projects are not licensed or imported by this directory.
