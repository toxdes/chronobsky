# Configuration

The site generator reads `config.json` from the project root by default. A custom path can be specified via `--config`:

```
python3 gen.py --config /path/to/config.json
```

If no config file is found, built-in defaults are used. A config file only needs to specify the values you want to override -- missing keys inherit from defaults.

## Top-level keys

```json
{
  "version": 2,
  "font": { ... },
  "border_radius": "0.75rem",
  "base_font_size": "1rem",
  "layout": { ... },
  "widgets": { ... },
  "theme": { ... }
}
```

| Key | Type | Default | Description |
|---|---|---|---|
| `version` | number | `2` | Config format version. A warning is shown if the file has a higher version than the generator supports. |
| `font` | object | see below | Font family, weights, and loading method. |
| `border_radius` | string | `"0.75rem"` | Global border radius for all cards, buttons, and modals. Set to `"0"` for sharp corners. Any CSS length value. |
| `base_font_size` | string | `"1rem"` | Root font size set on `<html>`. All `rem` values in the site scale relative to this. |
| `layout` | object | see below | Defines which widgets appear in which section and their order. |
| `widgets` | object | see below | Configuration for each individual widget. |
| `theme` | object | see below | Light and dark color palettes. |

## `font`

```json
{
  "family": "Inter",
  "weights": [400, 500, 600],
  "source": "google",
  "url": null
}
```

| Key | Type | Description |
|---|---|---|
| `family` | string | Font family name (e.g. `"Inter"`, `"Funnel Sans"`). |
| `weights` | array | Font weights to load (e.g. `[400, 500, 600]`). |
| `source` | `"google"` or `"custom"` | `"google"` generates a Google Fonts `<link>` tag. `"custom"` uses the `url` field as a CSS `<link>`. |
| `url` | string or null | When `source` is `"custom"`, this should be a URL to a CSS file with `@font-face` declarations. |

## `layout`

```json
{
  "header": ["logo", "source_link", "dark_mode_toggle"],
  "sidebar": ["calendar", "quick_nav"],
  "content": ["description"]
}
```

Each key is an ordered array of widget names. A widget listed in multiple sections will appear in each. A widget not listed in any section is not rendered.

### Placement slots

| Slot | Location | Description |
|---|---|---|
| `header` | Inside `<nav>` in the sticky header | Rendered left to right in the given order. `logo` is special -- it sits outside `<nav>` but its position in the array is ignored; it always appears first. |
| `sidebar` | Right-hand sticky sidebar | Rendered top to bottom. Empty array means no sidebar wrapper is generated -- content centers naturally. |
| `content` | Above the post timeline | Rendered top to bottom above the first day's posts. |

## `widgets`

### `logo`

```json
{
  "text": "Chronobsky",
  "url": "#"
}
```

The site title in the header. Links to the given URL.

### `source_link`

```json
{
  "text": "Source",
  "url": "https://github.com/toxdes/chronobsky"
}
```

A text link in the header nav.

### `dark_mode_toggle`

```json
{}
```

A button that toggles between light and dark themes. Preference is persisted in `localStorage`. No configuration options currently.

### `calendar`

```json
{}
```

A sticky calendar widget in the sidebar showing months with posts. Days with posts are highlighted. On mobile, opens as a modal via the sidebar toggle button. No configuration options currently.

### `quick_nav`

```json
{
  "label_today": "Today",
  "label_week": "Week",
  "label_month": "Month",
  "label_year": "Year"
}
```

Shortcut links that scroll to the nearest available post for the current period. Each label is customizable.

### `description`

```json
{
  "text": "{count} posts from @{handle} on bsky.social"
}
```

A short intro text shown above the post timeline. Supports `{count}` (total post count) and `{handle}` (Bluesky handle from `.env`) placeholders.

## `theme`

Two sub-objects: `light` and `dark`. Each contains the same set of CSS custom property values.

| Key | CSS variable | Light (default) | Dark (default) | Description |
|---|---|---|---|---|
| `bg` | `--bg` | `#ffffff` | `#0f172a` | Page background |
| `text` | `--text` | `#0f172a` | `#e2e8f0` | Body text color |
| `border` | `--border` | `#e2e8f0` | `#1e293b` | Border color for cards, headers, dividers |
| `accent` | `--accent` | `#2563eb` | `#60a5fa` | Primary accent color for links, badges, headings |
| `muted` | `--muted` | `#64748b` | `#94a3b8` | Secondary/muted text color |
| `reply_bg` | `--reply-bg` | `#f1f5f9` | `#1e293b` | Background for reply cards |
| `header_bg` | `--header-bg` | `rgba(255,255,255,0.85)` | `rgba(15,23,42,0.85)` | Header background (semi-transparent for blur effect) |
| `link_icon` | `--link-icon` | `#cbd5e1` | `#475569` | Color for the external link icon on each post |

All values are standard CSS values -- hex, rgb, rgba, or any valid color syntax.
