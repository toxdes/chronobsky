#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from datetime import datetime

TWEETS_DIR = 'tweets'
DIST_DIR = 'dist'


def _load_dotenv(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        lines = f.readlines()
    env = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            continue
        key, _, val = line.partition('=')
        env[key.strip()] = val.strip()
    return env


_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
HANDLE = _load_dotenv(_ENV_PATH).get('BLUESKY_HANDLE', 'yourhandle.bsky.social')

# ── Config ────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "version": 2,
    "font": {
        "family": "Inter",
        "weights": [400, 500, 600],
        "source": "google",
        "url": None,
    },
    "border_radius": "0.75rem",
    "base_font_size": "1rem",
    "layout": {
        "header": ["logo", "source_link", "dark_mode_toggle"],
        "sidebar": ["calendar", "quick_nav"],
        "content": ["description"],
    },
    "widgets": {
        "logo": {
            "text": "Chronobsky",
            "url": "#",
        },
        "source_link": {
            "text": "Source",
            "url": "https://github.com/toxdes/chronobsky",
        },
        "dark_mode_toggle": {},
        "calendar": {},
        "description": {
            "text": "{count} posts from @{handle} on bsky.social",
        },
        "quick_nav": {
            "label_today": "Today",
            "label_week": "Week",
            "label_month": "Month",
            "label_year": "Year",
        },
    },
    "theme": {
        "light": {
            "bg": "#ffffff",
            "text": "#0f172a",
            "border": "#e2e8f0",
            "accent": "#2563eb",
            "muted": "#64748b",
            "reply_bg": "#f1f5f9",
            "header_bg": "rgba(255, 255, 255, 0.85)",
            "link_icon": "#cbd5e1",
        },
        "dark": {
            "bg": "#0f172a",
            "text": "#e2e8f0",
            "border": "#1e293b",
            "accent": "#60a5fa",
            "muted": "#94a3b8",
            "reply_bg": "#1e293b",
            "header_bg": "rgba(15, 23, 42, 0.85)",
            "link_icon": "#475569",
        },
    },
}


def _deep_merge(base, overrides):
    result = dict(base)
    for k, v in overrides.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _load_config(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    if not os.path.exists(path):
        if path != os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'):
            print(f'Error: config file not found: {path}')
            sys.exit(1)
        return DEFAULT_CONFIG
    with open(path) as f:
        overrides = json.load(f)
    cfg = _deep_merge(DEFAULT_CONFIG, overrides)
    if cfg.get('version', 2) > 2:
        print(f'Warning: config version {cfg["version"]} is newer than generator version 2')
    return cfg


# ── Data loading ────────────────────────────────────────────────

def load_all_posts():
    posts = []
    for root, _dirs, files in os.walk(TWEETS_DIR):
        for fname in sorted(files):
            if not fname.endswith('.json'):
                continue
            path = os.path.join(root, fname)
            with open(path) as f:
                posts.extend(json.load(f))
    posts.sort(key=lambda p: p['created_at'])
    return posts


def group_by_date(posts):
    groups = {}
    for p in posts:
        groups.setdefault(p['created_at'][:10], []).append(p)
    return dict(sorted(groups.items()))


def build_parent_lookup(posts):
    return {p['id']: p for p in posts}


# ── Formatting ──────────────────────────────────────────────────

def _parse_time(iso_str):
    s = iso_str.replace('Z', '+00:00') if iso_str.endswith('Z') else iso_str
    dt = datetime.fromisoformat(s)
    # Convert from UTC to local timezone, fixing time mismatch
    return dt.astimezone()


def format_heading_date(date_str):
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return dt.strftime('%A, %B %d, %Y')


def format_time_short(iso_str):
    dt = _parse_time(iso_str)
    h = dt.hour % 12 or 12
    return f'{h}:{dt.minute:02d} {"AM" if dt.hour < 12 else "PM"}'


def format_time_full(iso_str):
    dt = _parse_time(iso_str)
    return dt.strftime('%B %d, %Y at %I:%M %p').lstrip('0').replace(' 0', ' ')


def _escape(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


import re
_TRAILING_PUNCT = re.compile(r'[.,!?:;\'\")\]}]+$')

def _linkify(text):
    def _wrap(m):
        url = m.group(1)
        url = _TRAILING_PUNCT.sub('', url)
        if not url.startswith(('http://', 'https://')):
            return m.group(0)
        return f'<a href="{url}" rel="nofollow">{url}</a>'
    return re.sub(r'(https?://[^\s<]+)', _wrap, text)


def content_to_html(text):
    parts = []
    for p in text.split('\n'):
        p = p.strip()
        if not p:
            continue
        parts.append(f'<p>{_linkify(_escape(p))}</p>')
    return '\n'.join(parts)


# ── HTML generation ─────────────────────────────────────────────

def render_post(post, known_ids):
    is_reply = post['parent_id'] is not None
    cls = 'post' + (' reply' if is_reply else '')
    eid = _escape(post['id'])
    time_iso = post['created_at']
    time_short = format_time_short(time_iso)
    time_full = format_time_full(time_iso)

    lines = [f'<article class="{cls}" id="{eid}">']
    lines.append('  <div class="post-meta">')
    lines.append(f'    <time datetime="{_escape(time_iso)}" title="{_escape(time_full)}">{_escape(time_short)}</time>')
    if is_reply:
        pid = post['parent_id']
        if pid in known_ids:
            lines.append(f'    <a href="#{_escape(pid)}" class="reply-badge" title="Go to parent post">↳ Reply</a>')
        else:
            lines.append('    <span class="reply-badge">↳ Reply</span>')
    if post.get('post_url'):
        lines.append(f'    <a href="{_escape(post["post_url"])}" class="post-link" target="_blank" rel="noopener">↗ view on bsky</a>')
    lines.append('  </div>')
    lines.append(f'  <div class="post-content">{content_to_html(post["content"])}</div>')

    images = post.get('images')
    if images:
        lines.append('  <div class="post-images">')
        for url in images:
            if url:
                lines.append(f'    <img src="{_escape(url)}" alt="" loading="lazy">')
        lines.append('  </div>')

    quoted_id = post.get('quoted_post_id')
    if quoted_id:
        eq = _escape(quoted_id)
        lines.append(f'  <a href="#{eq}" class="quote-link" title="Go to quoted post">Quoted post</a>')

    lines.append('</article>')
    return '\n'.join(lines)


def render_day(date_str, posts, known_ids):
    lines = [f'<section class="day" id="{date_str}">']
    lines.append(f'  <h2>{_escape(format_heading_date(date_str))}</h2>')
    for p in posts:
        lines.append(render_post(p, known_ids))
    lines.append('</section>')
    return '\n'.join(lines)


def render_calendar_sidebar():
    return '''  <div id="calendar">
    <div class="cal-header">
      <button id="cal-prev" class="cal-nav">&lt;</button>
      <span id="cal-label" class="cal-label"></span>
      <button id="cal-next" class="cal-nav">&gt;</button>
    </div>
    <table class="cal-grid">
      <thead>
        <tr><th>Mo</th><th>Tu</th><th>We</th><th>Th</th><th>Fr</th><th>Sa</th><th>Su</th></tr>
      </thead>
      <tbody id="cal-body"></tbody>
    </table>
  </div>'''


def render_sidebar_modal():
    return '''<div id="sidebar-modal" class="sidebar-modal-overlay" hidden>
  <div class="sidebar-modal-box">
    <div class="sidebar-modal-header">
      <span class="sidebar-modal-title">Navigate</span>
      <button id="sidebar-modal-close" class="sidebar-modal-close">&times;</button>
    </div>
    <div id="sidebar-modal-body"></div>
  </div>
</div>'''


def _render_font_link(cfg):
    font = cfg['font']
    if font['source'] == 'google':
        weights = ';'.join(str(w) for w in (font['weights'] or [400]))
        family = font['family'].replace(' ', '+')
        return f'<link href="https://fonts.googleapis.com/css2?family={family}:wght@{weights}&display=swap" rel="stylesheet">'
    if font['source'] == 'custom' and font.get('url'):
        return f'<link rel="stylesheet" href="{_escape(font["url"])}">'
    return ''


def _nav_item_html(name, cfg, all_dates=None):
    w = cfg['widgets']
    if name == 'source_link':
        sl = w['source_link']
        return f'<a href="{_escape(sl["url"])}" class="gh-link" target="_blank" rel="noopener">{_escape(sl["text"])}</a>'
    if name == 'dark_mode_toggle':
        return '<button id="theme-toggle" aria-label="Toggle theme">🌚</button>'
    if name == 'calendar':
        return '<button id="sidebar-toggle" class="sidebar-toggle">&#8942;</button>'
    if name == 'quick_nav' and all_dates:
        return _quick_nav_html(cfg, all_dates)
    return ''


def _sidebar_html(name, cfg, all_dates=None):
    if name == 'calendar':
        return render_calendar_sidebar()
    if name == 'quick_nav' and all_dates:
        return _quick_nav_html(cfg, all_dates)
    return ''


def _content_html(name, cfg, total, all_dates=None):
    if name == 'description':
        desc_text = cfg['widgets']['description'].get('text', '')
        desc_text = desc_text.replace('{count}', f'<span class="post-count">{total}</span>').replace('{handle}', HANDLE)
        return f'<section class="intro"><p>{desc_text}</p></section>'
    if name == 'quick_nav' and all_dates:
        return _quick_nav_html(cfg, all_dates)
    return ''


def _resolve_quick_nav_dates(all_dates):
    from datetime import date, timedelta
    today = date.today()
    today_str = today.isoformat()
    monday = (today - timedelta(days=today.weekday())).isoformat()
    month_start = today.replace(day=1).isoformat()
    year_start = today.replace(month=1, day=1).isoformat()

    def nearest(target, forward=True):
        if target in all_dates:
            return target
        if forward:
            for d in all_dates:
                if d >= target:
                    return d
            return all_dates[-1]
        for d in reversed(all_dates):
            if d <= target:
                return d
        return all_dates[0]

    return (
        nearest(today_str, forward=False),
        nearest(monday, forward=True),
        nearest(month_start, forward=True),
        nearest(year_start, forward=True),
    )


def _quick_nav_html(cfg, all_dates):
    w = cfg['widgets']['quick_nav']
    t, wd, m, y = _resolve_quick_nav_dates(all_dates)
    return f'''<p class="quick-nav">
  Jump to: <a href="#{t}" class="qn-btn">{_escape(w.get('label_today', 'Today'))}</a>,
  <a href="#{wd}" class="qn-btn">{_escape(w.get('label_week', 'Week'))}</a>,
  <a href="#{m}" class="qn-btn">{_escape(w.get('label_month', 'Month'))}</a>,
  <a href="#{y}" class="qn-btn">{_escape(w.get('label_year', 'Year'))}</a>
</p>'''


def generate_html(days, known_ids, total, cfg):
    sections = '\n'.join(render_day(d, ps, known_ids) for d, ps in days.items())
    dates_json = json.dumps(sorted(days.keys()))
    all_dates = sorted(days.keys())
    font_link = _render_font_link(cfg)
    layout = cfg['layout']
    w = cfg['widgets']

    # Logo (special: outside <nav>)
    logo = ''
    if 'logo' in layout.get('header', []) and 'logo' in w:
        l = w['logo']
        logo = f'<h1><a href="{_escape(l["url"])}">{_escape(l["text"])}</a></h1>'

    # Header nav items
    nav_items = []
    has_calendar = any('calendar' in layout.get(slot, []) for slot in layout)
    for name in layout.get('header', []):
        if name == 'logo':
            continue
        html = _nav_item_html(name, cfg, all_dates)
        if html:
            nav_items.append(html)
    if has_calendar:
        nav_items.append(_nav_item_html('calendar', cfg, all_dates))
    nav_html = '\n      '.join(nav_items)

    # Sidebar — wrap all widgets in a single column
    sidebar_html = ''
    for name in layout.get('sidebar', []):
        html = _sidebar_html(name, cfg, all_dates)
        if html:
            sidebar_html += html
    if sidebar_html:
        sidebar_html = f'<aside class="sidebar">\n{sidebar_html}\n</aside>'

    # Content above posts
    content_top = ''
    for name in layout.get('content', []):
        html = _content_html(name, cfg, total, all_dates)
        if html:
            content_top += html

    # Modals
    modals = '''<div id="image-modal" class="modal-overlay" hidden>
  <button id="modal-close" class="modal-close">&times;</button>
  <img id="modal-img" src="" alt="">
</div>'''
    if sidebar_html:
        modals += render_sidebar_modal()

    wrap_open = f'<div class="page-wrap">' if sidebar_html else ''
    wrap_close = '</div>' if sidebar_html else ''
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chronobsky Archive</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{font_link}
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <div class="header-inner">
    {logo}
    <nav>
      {nav_html}
    </nav>
  </div>
</header>
{wrap_open}
<main>
{content_top}
{sections}
</main>
{sidebar_html}
{wrap_close}
{modals}
<script>
var ACTIVE_DATES = {dates_json};
</script>
<script src="theme.js"></script>
</body>
</html>'''


# ── Static assets ───────────────────────────────────────────────

def _theme_vars(cfg):
    t = cfg['theme']
    radius = str(cfg.get('border_radius', '0.75rem'))
    out = ['/* ── Variables ────────────────────────────────────── */',
           ':root {']
    out.append(f'  --radius: {radius};')
    for k, v in t['light'].items():
        out.append(f'  --{k.replace("_", "-")}: {v};')
    out.append('}')
    out.append('')
    out.append(':root.dark {')
    for k, v in t['dark'].items():
        out.append(f'  --{k.replace("_", "-")}: {v};')
    out.append('}')
    return '\n'.join(out)


def _reset_css(family, base_size):
    return f'''/* ── Reset ──────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; font-size: {base_size}; }}

body {{
  font-family: '{family}', system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
  transition: background .3s, color .3s;
}}'''


def _header_css():
    return '''/* ── Header ─────────────────────────────────────── */
header {
  position: sticky; top: 0; z-index: 100;
  background: var(--header-bg);
  backdrop-filter: blur(0.75rem);
  border-bottom: 1px solid var(--border);
  transition: background .3s, border-color .3s;
}
.header-inner {
  max-width: 980px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 1.5rem;
}
header h1 { font-size: 1.125rem; font-weight: 600; letter-spacing: -.01em; }
header h1 a { color: var(--text); text-decoration: none; }
header nav { display: flex; align-items: center; gap: 0.75rem; }
.gh-link {
  font-size: 0.8125rem; font-weight: 500; color: var(--muted);
  text-decoration: none; transition: color .2s;
}
.gh-link:hover { color: var(--accent); }
#theme-toggle {
  background: none; border: 1px solid var(--border); border-radius: var(--radius);
  padding: 0.375rem 0.625rem; font-size: 1.125rem; cursor: pointer; line-height: 1;
  transition: border-color .2s;
}
#theme-toggle:hover { border-color: var(--accent); }'''


def _sidebar_toggle_css():
    return '''.sidebar-toggle {
  background: none; border: 1px solid var(--border); border-radius: var(--radius);
  padding: 0.375rem 0.625rem; font-size: 1.125rem; cursor: pointer;
  color: var(--muted); line-height: 1; display: none;
  transition: color .2s, border-color .2s;
}
.sidebar-toggle:hover { color: var(--accent); border-color: var(--accent); }'''

def _layout_css():
    return '''/* ── Page layout ──────────────────────────────────── */
.page-wrap {
  max-width: 980px; margin: 0 auto; padding: 2.5rem 1.5rem 5rem;
  display: flex; gap: 2.5rem; align-items: flex-start;
}
main {
  max-width: 680px; margin: 0 auto; padding: 2.5rem 1.5rem 5rem;
}
.page-wrap > main { flex: 0 0 680px; margin: 0; padding: 0; }
.intro {
  margin-bottom: 2.5rem; padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--border);
  font-size: 0.875rem; color: var(--muted); line-height: 1.6;
  transition: border-color .3s;
}
.intro a { color: var(--accent); text-decoration: none; font-weight: 500; }
.intro a:hover { text-decoration: underline; }
.post-count { font-weight: 500; color: var(--text); }'''

def _day_css():
    return '''/* ── Day section ────────────────────────────────── */
.day { margin-bottom: 3rem; scroll-margin-top: 5rem; }
.day h2 {
  font-size: 1.25rem; font-weight: 600; color: var(--accent);
  margin-bottom: 1.5rem; padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--border);
  transition: color .3s, border-color .3s;
}'''

def _post_css():
    return '''/* ── Post card ──────────────────────────────────── */
.post {
  margin-bottom: 1rem; padding: 1rem 1.25rem; border-radius: var(--radius);
  border: 1px solid var(--border); scroll-margin-top: 4.375rem;
  transition: border-color .3s, background .3s;
}
.post.reply { background: var(--reply-bg); }
.post-meta {
  display: flex; align-items: center; gap: 0.375rem;
  margin-bottom: 0.5rem; font-size: 0.8125rem; color: var(--muted);
}
.post-meta time { font-weight: 500; }
.reply-badge {
  font-size: 0.6875rem; font-weight: 600; color: var(--accent);
  padding: 0.0625rem 0.375rem; border-radius: var(--radius);
  background: color-mix(in srgb, var(--accent) 10%, transparent);
}
a.reply-badge { text-decoration: none; transition: background .2s; }
a.reply-badge:hover { background: color-mix(in srgb, var(--accent) 20%, transparent); }
.post-link {
  margin-left: auto; color: var(--link-icon); text-decoration: none;
  font-size: 0.75rem; opacity: 0; transition: opacity .2s;
}
.post:hover .post-link { opacity: 1; }
.post-link:hover { color: var(--accent); }
.quote-link {
  display: inline-block; margin-top: 0.625rem; font-size: 0.8125rem; font-weight: 500;
  color: var(--accent); text-decoration: none; padding: 0.1875rem 0.625rem;
  border-radius: var(--radius); border: 1px solid var(--border);
  transition: background .2s, border-color .2s;
}
.quote-link:hover {
  background: color-mix(in srgb, var(--accent) 8%, transparent);
  border-color: var(--accent);
}'''

def _content_css():
    return '''/* ── Content ────────────────────────────────────── */
.post-content {
  font-size: 0.9375rem; line-height: 1.7;
  word-wrap: break-word; overflow-wrap: break-word;
}
.post-content p { margin-bottom: 0.5rem; }
.post-content p:last-child { margin-bottom: 0; }
.post-content a { color: var(--accent); word-break: break-all; }'''

def _image_css():
    return '''/* ── Images ─────────────────────────────────────── */
.post-images { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.75rem; }
.post-images img {
  max-width: 100%; height: auto; border-radius: var(--radius);
  border: 1px solid var(--border);
}'''

def _quick_nav_css():
    return '''/* ── Quick nav ──────────────────────────────────── */
.quick-nav { font-size: 0.75rem; color: var(--muted); }
.qn-btn { font-weight: 500; color: var(--accent); text-decoration: none; }
.qn-btn:hover { text-decoration: underline; }'''

def _calendar_sidebar_css():
    return '''/* ── Calendar ──────────────────────────────────── */
.sidebar { flex: 0 0 220px; position: sticky; top: 4.375rem; display: flex; flex-direction: column; gap: 0.75rem; }
#calendar {
  border: 1px solid var(--border); border-radius: var(--radius);
  padding: 0.75rem; overflow: hidden; transition: border-color .3s;
}
.cal-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.625rem; }
.cal-label { font-size: 0.8125rem; font-weight: 600; color: var(--text); }
.cal-nav {
  background: none; border: 1px solid var(--border); border-radius: var(--radius);
  padding: 0 0.5rem; font-size: 0.875rem; cursor: pointer; color: var(--muted);
  line-height: 1; height: 1.625rem;
  display: flex; align-items: center; justify-content: center;
  transition: color .2s, border-color .2s;
}
.cal-nav:hover { color: var(--accent); border-color: var(--accent); }
.cal-nav:disabled { opacity: 0.25; cursor: default; pointer-events: none; }
.cal-grid { width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 0.75rem; }
.cal-grid th { font-weight: 500; color: var(--muted); padding: 0.125rem 0; text-align: center; font-size: 0.6875rem; width: calc(100% / 7); }
.cal-grid td { text-align: center; padding: 0.1875rem 0; color: var(--muted); font-size: 0.75rem; width: calc(100% / 7); }
.cal-grid td a {
  display: flex; align-items: center; justify-content: center;
  width: 1.5rem; height: 1.5rem; margin: 0 auto;
  border-radius: 50%; text-decoration: none; color: var(--text);
  font-weight: 500; font-size: 0.75rem; transition: background .2s, color .2s;
}
.cal-grid td a:hover { background: color-mix(in srgb, var(--accent) 12%, transparent); color: var(--accent); }
.cal-grid td a.active { color: var(--accent); font-weight: 600; }'''

def _sidebar_modal_css():
    return '''/* ── Sidebar modal (mobile) ────────────────────── */
.sidebar-modal-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0, 0, 0, 0.5);
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.sidebar-modal-overlay[hidden] { display: none; }
.sidebar-modal-box {
  background: var(--bg); border-radius: var(--radius); padding: 1.25rem;
  width: 300px; cursor: default; transition: background .3s;
}
.sidebar-modal-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.sidebar-modal-title { font-size: 0.9375rem; font-weight: 600; color: var(--text); }
.sidebar-modal-close {
  background: none; border: none; font-size: 1.375rem; cursor: pointer;
  color: var(--muted); padding: 0; line-height: 1;
}
.sidebar-modal-close:hover { color: var(--text); }
#sidebar-modal .sidebar { display: flex; }'''

def _lightbox_css():
    return '''/* ── Image lightbox ─────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0, 0, 0, 0.85);
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.modal-overlay[hidden] { display: none; }
.modal-overlay img { max-width: 90vw; max-height: 90vh; object-fit: contain; border-radius: var(--radius); cursor: default; }
.modal-close {
  position: fixed; top: 1rem; right: 1rem;
  background: none; border: none; font-size: 2rem; color: #fff;
  cursor: pointer; opacity: 0.6; z-index: 201; line-height: 1;
  transition: opacity .2s;
}
.modal-close:hover { opacity: 1; }'''

def _responsive_css(cal_visible):
    parts = ['/* ── Responsive ─────────────────────────────────── */',
             '@media (max-width: 800px) {']
    if cal_visible:
        parts.append('  .sidebar { display: none; }')
        parts.append('  .sidebar-toggle { display: inline-flex; align-items: center; }')
    parts.extend([
        '  .page-wrap, main { padding: 1.5rem 1rem 3.75rem; }',
        '  main { flex: none; max-width: none; }',
        '  .page-wrap { display: block; }',
        '  .post { padding: 0.75rem 0.875rem; }',
        '  .post-content { font-size: 0.875rem; }',
        '  .day h2 { font-size: 1.125rem; }',
        '}',
    ])
    return '\n'.join(parts)


def _print_css(cal_visible):
    hide = 'header, .post-link'
    if cal_visible:
        hide += ', .sidebar, .sidebar-toggle'
    return f'/* ── Print ──────────────────────────────────────── */\n@media print {{ {hide} {{ display: none; }} }}'


def generate_style_css(cfg):
    has_cal = 'calendar' in cfg['layout'].get('sidebar', [])
    has_qn = 'quick_nav' in cfg['layout'].get('sidebar', []) or 'quick_nav' in cfg['layout'].get('content', [])
    parts = [
        _theme_vars(cfg),
        _reset_css(cfg['font']['family'], cfg['base_font_size']),
        _header_css(),
        _layout_css(),
        _day_css(),
        _post_css(),
        _content_css(),
        _image_css(),
    ]
    if has_cal:
        parts.append(_sidebar_toggle_css())
        parts.append(_calendar_sidebar_css())
        parts.append(_sidebar_modal_css())
    if has_qn:
        parts.append(_quick_nav_css())
    parts.append(_lightbox_css())
    parts.append(_responsive_css(has_cal))
    parts.append(_print_css(has_cal))
    return '\n\n'.join(parts) + '\n'

THEME_TOGGLE_JS = '''(function() {
  var key = 'theme';
  var stored = localStorage.getItem(key);
  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

  if (stored === 'dark' || (!stored && prefersDark)) {
    document.documentElement.classList.add('dark');
  }

  document.getElementById('theme-toggle').addEventListener('click', function() {
    document.documentElement.classList.toggle('dark');
    var isDark = document.documentElement.classList.contains('dark');
    localStorage.setItem(key, isDark ? 'dark' : 'light');
    this.textContent = isDark ? '\U0001f60e' : '\U0001f31a';
  });
})();'''


CALENDAR_JS = '''(function() {
  var dates = typeof ACTIVE_DATES !== 'undefined' ? ACTIVE_DATES : [];
  var months = {};
  dates.forEach(function(d) {
    var p = d.split('-');
    var k = p[0] + '-' + p[1];
    if (!months[k]) months[k] = [];
    months[k].push(parseInt(p[2], 10));
  });

  var sortedMonths = Object.keys(months).sort();
  var today = new Date();
  var lastKey = sortedMonths.length ? sortedMonths[sortedMonths.length - 1] : null;
  var curKey = lastKey || (today.getFullYear() + '-' + (today.getMonth() < 9 ? '0' : '') + (today.getMonth() + 1));
  var curParts = curKey.split('-');
  var curYear = parseInt(curParts[0], 10);
  var curMonth = parseInt(curParts[1], 10);

  var label = document.getElementById('cal-label');
  var body = document.getElementById('cal-body');
  var prevBtn = document.getElementById('cal-prev');
  var nextBtn = document.getElementById('cal-next');

  function pad(n) { return n < 10 ? '0' + n : '' + n; }
  function adjKey(year, month, delta) {
    var m = month + delta;
    var y = year;
    if (m < 1) { m = 12; y--; }
    if (m > 12) { m = 1; y++; }
    return y + '-' + pad(m);
  }

  function render(year, month) {
    var first = new Date(year, month - 1, 1);
    var startDay = (first.getDay() + 6) % 7;
    var daysInMonth = new Date(year, month, 0).getDate();
    var now = new Date();
    var isCurrentMonth = year === now.getFullYear() && month === now.getMonth() + 1;
    var todayDate = now.getDate();

    var monthNames = ['January','February','March','April','May','June',
                      'July','August','September','October','November','December'];
    label.textContent = monthNames[month - 1] + ' ' + year;

    var key = year + '-' + pad(month);
    var activeDays = months[key] || [];
    var activeSet = {};
    activeDays.forEach(function(d) { activeSet[d] = true; });

    var html = '<tr>';
    for (var i = 0; i < startDay; i++) html += '<td></td>';
    for (var day = 1; day <= daysInMonth; day++) {
      var idx = startDay + day - 1;
      if (idx > 0 && idx % 7 === 0) html += '</tr><tr>';
      if (activeSet[day]) {
        html += '<td><a href="#' + year + '-' + pad(month) + '-' + pad(day) + '" class="active">' + day + '</a></td>';
      } else {
        html += '<td' + (isCurrentMonth && day === todayDate ? ' style="font-weight:600"' : '') + '>' + day + '</td>';
      }
    }
    html += '</tr>';
    body.innerHTML = html;
    prevBtn.disabled = !months[adjKey(year, month, -1)];
    nextBtn.disabled = !months[adjKey(year, month, 1)];
  }

  function goTo(d) { curMonth += d; if (curMonth < 1) { curMonth = 12; curYear--; } if (curMonth > 12) { curMonth = 1; curYear++; } render(curYear, curMonth); }

  if (prevBtn) prevBtn.addEventListener('click', function() { goTo(-1); });
  if (nextBtn) nextBtn.addEventListener('click', function() { goTo(1); });
  render(curYear, curMonth);
})();'''


LIGHTBOX_JS = '''(function() {
  var modal = document.getElementById('image-modal');
  var modalImg = document.getElementById('modal-img');
  var modalClose = document.getElementById('modal-close');

  document.addEventListener('click', function(e) {
    if (e.target.tagName === 'IMG' && e.target.closest('.post-images')) {
      modal.removeAttribute('hidden');
      modalImg.src = e.target.src;
    }
  });

  function close() { modal.setAttribute('hidden', ''); modalImg.src = ''; }

  modal.addEventListener('click', function(e) {
    if (e.target === modal || e.target === modalClose) close();
  });

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && !modal.hasAttribute('hidden')) close();
  });
})();'''


SIDEBAR_MODAL_JS = '''(function() {
  var calModal = document.getElementById('sidebar-modal');
  var calBody = document.getElementById('sidebar-modal-body');
  var calToggle = document.getElementById('sidebar-toggle');
  var calClose = document.getElementById('sidebar-modal-close');
  if (!calToggle || !calModal) return;

  function refreshClone() {
    var sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;
    var clone = sidebar.cloneNode(true);
    calBody.innerHTML = '';
    calBody.appendChild(clone);

    var prevOrig = document.getElementById('cal-prev');
    var nextOrig = document.getElementById('cal-next');
    clone.querySelector('#cal-prev').addEventListener('click', function() {
      if (prevOrig) { prevOrig.click(); setTimeout(refreshClone, 30); }
    });
    clone.querySelector('#cal-next').addEventListener('click', function() {
      if (nextOrig) { nextOrig.click(); setTimeout(refreshClone, 30); }
    });

    clone.querySelectorAll('a[href^="#"]').forEach(function(a) {
      a.addEventListener('click', function() { calModal.setAttribute('hidden', ''); });
    });
  }

  calToggle.addEventListener('click', function() { refreshClone(); calModal.removeAttribute('hidden'); });
  calModal.addEventListener('click', function(e) {
    if (e.target === calModal || e.target === calClose) calModal.setAttribute('hidden', '');
  });
})();'''


def generate_theme_js(cfg):
    parts = []
    if 'dark_mode_toggle' in cfg['layout'].get('header', []):
        parts.append(THEME_TOGGLE_JS)
    if 'calendar' in cfg['layout'].get('sidebar', []):
        parts.append(CALENDAR_JS)
        parts.append(SIDEBAR_MODAL_JS)
    parts.append(LIGHTBOX_JS)
    return '\n\n'.join(parts) + '\n'


# ── Main ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Generate static site from archived Bluesky posts.')
    parser.add_argument('--config', help='Path to config JSON file (defaults to config.json in project root)')
    args = parser.parse_args()

    cfg = _load_config(args.config)
    posts = load_all_posts()
    if not posts:
        print('No posts found in tweets/.')
        return

    parent_lookup = build_parent_lookup(posts)
    known_ids = set(parent_lookup.keys())
    days = group_by_date(posts)
    total = sum(len(v) for v in days.values())

    os.makedirs(DIST_DIR, exist_ok=True)

    with open(os.path.join(DIST_DIR, 'index.html'), 'w') as f:
        f.write(generate_html(days, known_ids, total, cfg))

    with open(os.path.join(DIST_DIR, 'style.css'), 'w') as f:
        f.write(generate_style_css(cfg))

    with open(os.path.join(DIST_DIR, 'theme.js'), 'w') as f:
        f.write(generate_theme_js(cfg))

    print(f'Generated dist/ — {len(days)} days, {total} posts.')


if __name__ == '__main__':
    main()
