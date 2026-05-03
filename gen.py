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
    "version": 1,
    "font": {
        "family": "Inter",
        "weights": [400, 500, 600],
        "source": "google",
        "url": None,
    },
    "logo": {
        "visible": True,
        "text": "Chronobsky",
        "url": "#",
    },
    "description": {
        "visible": True,
        "text": "{count} posts from @{handle} on bsky.social",
    },
    "source_link": {
        "visible": True,
        "text": "Source",
        "url": "https://github.com/toxdes/chronobsky",
    },
    "dark_mode_toggle": {
        "visible": True,
    },
    "calendar": {
        "visible": True,
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
    if cfg.get('version', 1) > 1:
        print(f'Warning: config version {cfg["version"]} is newer than generator version 1')
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
    s = iso_str.replace('Z', '') if iso_str.endswith('Z') else iso_str
    if '.' in s:
        return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')


def format_heading_date(date_str):
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return dt.strftime('%A, %B %d, %Y')


def format_time_short(iso_str):
    dt = _parse_time(iso_str)
    h = dt.hour % 12 or 12
    return f'{h}:{dt.minute:02d} {"AM" if dt.hour < 12 else "PM"}'


def _escape(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def _linkify(text):
    return re.sub(r'(https?://[^\s<]+)', r'<a href="\1" rel="nofollow">\1</a>', text)


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

    lines = [f'<article class="{cls}" id="{eid}">']
    lines.append('  <div class="post-meta">')
    lines.append(f'    <time datetime="{_escape(time_iso)}">{_escape(time_short)}</time>')
    if is_reply:
        pid = post['parent_id']
        if pid in known_ids:
            lines.append(f'    <a href="#{_escape(pid)}" class="reply-badge">↳ Reply</a>')
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
        lines.append(f'  <a href="#{eq}" class="quote-link">Quoted post</a>')

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
    return '''<aside class="cal-sidebar">
  <div id="calendar">
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
  </div>
</aside>'''


def _render_font_link(cfg):
    font = cfg['font']
    if font['source'] == 'google':
        weights = ';'.join(str(w) for w in (font['weights'] or [400]))
        family = font['family'].replace(' ', '+')
        return f'<link href="https://fonts.googleapis.com/css2?family={family}:wght@{weights}&display=swap" rel="stylesheet">'
    if font['source'] == 'custom' and font.get('url'):
        return f'<link rel="stylesheet" href="{_escape(font["url"])}">'
    return ''


def generate_html(days, known_ids, total, cfg):
    sections = '\n'.join(render_day(d, ps, known_ids) for d, ps in days.items())
    dates_json = json.dumps(sorted(days.keys()))
    font_link = _render_font_link(cfg)

    # Widget: logo
    logo = ''
    if cfg['logo']['visible']:
        logo = f'<h1><a href="{_escape(cfg["logo"]["url"])}">{_escape(cfg["logo"]["text"])}</a></h1>'

    # Widget: source link
    source_link = ''
    if cfg['source_link']['visible']:
        sl = cfg['source_link']
        source_link = f'<a href="{_escape(sl["url"])}" class="gh-link" target="_blank" rel="noopener">{_escape(sl["text"])}</a>'

    # Widget: dark mode toggle
    toggle = ''
    if cfg['dark_mode_toggle']['visible']:
        toggle = '<button id="theme-toggle" aria-label="Toggle theme">🌚</button>'

    # Widget: calendar toggle button (mobile)
    cal_toggle = ''
    cal_sidebar = ''
    cal_modal = ''
    if cfg['calendar']['visible']:
        cal_toggle = '<button id="cal-toggle" class="cal-toggle">Cal</button>'
        cal_sidebar = render_calendar_sidebar()
        cal_modal = '''<div id="cal-modal" class="cal-modal-overlay" hidden>
  <div class="cal-modal-box">
    <div class="cal-modal-header">
      <span class="cal-modal-title">Calendar</span>
      <button id="cal-modal-close" class="cal-modal-close">&times;</button>
    </div>
    <div id="cal-modal-body"></div>
  </div>
</div>'''

    # Widget: description
    desc = ''
    if cfg['description']['visible']:
        desc_text = cfg['description']['text']
        desc_text = desc_text.replace('{count}', f'<span class="post-count">{total}</span>').replace('{handle}', HANDLE)
        desc = f'<section class="intro"><p>{desc_text}</p></section>'

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
      {source_link}
      {cal_toggle}
      {toggle}
    </nav>
  </div>
</header>
<div class="page-wrap">
<main>
{desc}
{sections}
</main>
{cal_sidebar}
</div>
<div id="image-modal" class="modal-overlay" hidden>
  <button id="modal-close" class="modal-close">&times;</button>
  <img id="modal-img" src="" alt="">
</div>
{cal_modal}
<script>
var ACTIVE_DATES = {dates_json};
</script>
<script src="theme.js"></script>
</body>
</html>'''


# ── Static assets ───────────────────────────────────────────────

def _theme_vars(cfg):
    t = cfg['theme']
    out = ['/* ── Variables ────────────────────────────────────── */',
           ':root {']
    for k, v in t['light'].items():
        out.append(f'  --{k.replace("_", "-")}: {v};')
    out.append('}')
    out.append('')
    out.append(':root.dark {')
    for k, v in t['dark'].items():
        out.append(f'  --{k.replace("_", "-")}: {v};')
    out.append('}')
    return '\n'.join(out)


def _reset_css(family):
    return f'''/* ── Reset ──────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; }}

body {{
  font-family: '{family}', system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.7;
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  transition: background .3s, color .3s;
}}'''


def _header_css():
    return '''/* ── Header ─────────────────────────────────────── */
header {
  position: sticky; top: 0; z-index: 100;
  background: var(--header-bg);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  transition: background .3s, border-color .3s;
}
.header-inner {
  max-width: 980px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 24px;
}
header h1 { font-size: 18px; font-weight: 600; letter-spacing: -.01em; }
header h1 a { color: var(--text); text-decoration: none; }
header nav { display: flex; align-items: center; gap: 12px; }
.gh-link {
  font-size: 13px; font-weight: 500; color: var(--muted);
  text-decoration: none; transition: color .2s;
}
.gh-link:hover { color: var(--accent); }
#theme-toggle {
  background: none; border: 1px solid var(--border); border-radius: 8px;
  padding: 6px 10px; font-size: 18px; cursor: pointer; line-height: 1;
  transition: border-color .2s;
}
#theme-toggle:hover { border-color: var(--accent); }'''


def _cal_toggle_css():
    return '''.cal-toggle {
  background: none; border: 1px solid var(--border); border-radius: 8px;
  padding: 6px 10px; font-size: 13px; font-weight: 500; cursor: pointer;
  color: var(--muted); line-height: 1; display: none;
  transition: color .2s, border-color .2s;
}
.cal-toggle:hover { color: var(--accent); border-color: var(--accent); }'''


def _layout_css():
    return '''/* ── Page layout ──────────────────────────────────── */
.page-wrap {
  max-width: 980px; margin: 0 auto; padding: 40px 24px 80px;
  display: flex; gap: 40px; align-items: flex-start;
}
main { flex: 0 0 680px; max-width: 680px; }
.intro {
  margin-bottom: 40px; padding-bottom: 24px;
  border-bottom: 1px solid var(--border);
  font-size: 14px; color: var(--muted); line-height: 1.6;
  transition: border-color .3s;
}
.intro a { color: var(--accent); text-decoration: none; font-weight: 500; }
.intro a:hover { text-decoration: underline; }
.post-count { font-weight: 500; color: var(--text); }'''


def _day_css():
    return '''/* ── Day section ────────────────────────────────── */
.day { margin-bottom: 48px; scroll-margin-top: 80px; }
.day h2 {
  font-size: 20px; font-weight: 600; color: var(--accent);
  margin-bottom: 24px; padding-bottom: 8px;
  border-bottom: 2px solid var(--border);
  transition: color .3s, border-color .3s;
}'''


def _post_css():
    return '''/* ── Post card ──────────────────────────────────── */
.post {
  margin-bottom: 16px; padding: 16px 20px; border-radius: 12px;
  border: 1px solid var(--border); scroll-margin-top: 70px;
  transition: border-color .3s, background .3s;
}
.post.reply { background: var(--reply-bg); }
.post-meta {
  display: flex; align-items: center; gap: 6px;
  margin-bottom: 8px; font-size: 13px; color: var(--muted);
}
.post-meta time { font-weight: 500; }
.reply-badge {
  font-size: 11px; font-weight: 600; color: var(--accent);
  padding: 1px 6px; border-radius: 4px;
  background: color-mix(in srgb, var(--accent) 10%, transparent);
}
a.reply-badge { text-decoration: none; transition: background .2s; }
a.reply-badge:hover { background: color-mix(in srgb, var(--accent) 20%, transparent); }
.post-link {
  margin-left: auto; color: var(--link-icon); text-decoration: none;
  font-size: 12px; opacity: 0; transition: opacity .2s;
}
.post:hover .post-link { opacity: 1; }
.post-link:hover { color: var(--accent); }
.quote-link {
  display: inline-block; margin-top: 10px; font-size: 13px; font-weight: 500;
  color: var(--accent); text-decoration: none; padding: 3px 10px;
  border-radius: 6px; border: 1px solid var(--border);
  transition: background .2s, border-color .2s;
}
.quote-link:hover {
  background: color-mix(in srgb, var(--accent) 8%, transparent);
  border-color: var(--accent);
}'''


def _content_css():
    return '''/* ── Content ────────────────────────────────────── */
.post-content {
  font-size: 15px; line-height: 1.7;
  word-wrap: break-word; overflow-wrap: break-word;
}
.post-content p { margin-bottom: 8px; }
.post-content p:last-child { margin-bottom: 0; }
.post-content a { color: var(--accent); word-break: break-all; }'''


def _image_css():
    return '''/* ── Images ─────────────────────────────────────── */
.post-images { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.post-images img {
  max-width: 100%; height: auto; border-radius: 8px;
  border: 1px solid var(--border);
}'''


def _calendar_sidebar_css():
    return '''/* ── Calendar sidebar ────────────────────────────── */
.cal-sidebar { flex: 0 0 220px; position: sticky; top: 70px; }
#calendar {
  border: 1px solid var(--border); border-radius: 10px;
  padding: 12px; overflow: hidden; transition: border-color .3s;
}
.cal-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.cal-label { font-size: 13px; font-weight: 600; color: var(--text); }
.cal-nav {
  background: none; border: 1px solid var(--border); border-radius: 6px;
  padding: 0 8px; font-size: 14px; cursor: pointer; color: var(--muted);
  line-height: 1; height: 26px;
  display: flex; align-items: center; justify-content: center;
  transition: color .2s, border-color .2s;
}
.cal-nav:hover { color: var(--accent); border-color: var(--accent); }
.cal-nav:disabled { opacity: 0.25; cursor: default; pointer-events: none; }
.cal-grid { width: 100%; border-collapse: collapse; font-size: 12px; }
.cal-grid th { font-weight: 500; color: var(--muted); padding: 2px 0; text-align: center; font-size: 11px; }
.cal-grid td { text-align: center; padding: 3px 0; color: var(--muted); font-size: 12px; }
.cal-grid td a {
  display: inline-block; width: 24px; height: 24px; line-height: 24px;
  border-radius: 50%; text-decoration: none; color: var(--text);
  font-weight: 500; font-size: 12px; transition: background .2s, color .2s;
}
.cal-grid td a:hover { background: color-mix(in srgb, var(--accent) 12%, transparent); color: var(--accent); }
.cal-grid td a.active { color: var(--accent); font-weight: 600; }'''


def _cal_modal_css():
    return '''/* ── Calendar modal (mobile) ────────────────────── */
.cal-modal-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0, 0, 0, 0.5);
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.cal-modal-overlay[hidden] { display: none; }
.cal-modal-box {
  background: var(--bg); border-radius: 14px; padding: 20px;
  width: 300px; cursor: default; transition: background .3s;
}
.cal-modal-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.cal-modal-title { font-size: 15px; font-weight: 600; color: var(--text); }
.cal-modal-close {
  background: none; border: none; font-size: 22px; cursor: pointer;
  color: var(--muted); padding: 0; line-height: 1;
}
.cal-modal-close:hover { color: var(--text); }'''


def _lightbox_css():
    return '''/* ── Image lightbox ─────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0, 0, 0, 0.85);
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.modal-overlay[hidden] { display: none; }
.modal-overlay img { max-width: 90vw; max-height: 90vh; object-fit: contain; border-radius: 4px; cursor: default; }
.modal-close {
  position: fixed; top: 16px; right: 16px;
  background: none; border: none; font-size: 32px; color: #fff;
  cursor: pointer; opacity: 0.6; z-index: 201; line-height: 1;
  transition: opacity .2s;
}
.modal-close:hover { opacity: 1; }'''


def _responsive_css(cal_visible):
    parts = ['/* ── Responsive ─────────────────────────────────── */',
             '@media (max-width: 800px) {']
    if cal_visible:
        parts.append('  .cal-sidebar { display: none; }')
        parts.append('  .cal-toggle { display: inline-flex; align-items: center; }')
    parts.extend([
        '  .page-wrap { padding: 24px 16px 60px; }',
        '  main { flex: none; max-width: none; }',
        '  .page-wrap { display: block; }',
        '  .post { padding: 12px 14px; }',
        '  .post-content { font-size: 14px; }',
        '  .day h2 { font-size: 18px; }',
        '}',
    ])
    return '\n'.join(parts)


def _print_css(cal_visible):
    hide = 'header, .post-link'
    if cal_visible:
        hide += ', .cal-sidebar, .cal-toggle'
    return f'/* ── Print ──────────────────────────────────────── */\n@media print {{ {hide} {{ display: none; }} }}'


def generate_style_css(cfg):
    parts = [
        _theme_vars(cfg),
        _reset_css(cfg['font']['family']),
        _header_css(),
        _layout_css(),
        _day_css(),
        _post_css(),
        _content_css(),
        _image_css(),
    ]
    if cfg['calendar']['visible']:
        parts.append(_cal_toggle_css())
        parts.append(_calendar_sidebar_css())
        parts.append(_cal_modal_css())
    parts.append(_lightbox_css())
    parts.append(_responsive_css(cfg['calendar']['visible']))
    parts.append(_print_css(cfg['calendar']['visible']))
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


CALENDAR_MODAL_JS = '''(function() {
  var calModal = document.getElementById('cal-modal');
  var calBody = document.getElementById('cal-modal-body');
  var calToggle = document.getElementById('cal-toggle');
  var calClose = document.getElementById('cal-modal-close');
  if (!calToggle || !calModal) return;

  function openCal() {
    var src = document.getElementById('calendar');
    if (!src) return;
    var clone = src.cloneNode(true);
    calBody.innerHTML = '';
    calBody.appendChild(clone);
    calModal.removeAttribute('hidden');
    clone.querySelectorAll('a[href^="#"]').forEach(function(a) {
      a.addEventListener('click', function() { calModal.setAttribute('hidden', ''); });
    });
  }

  calToggle.addEventListener('click', openCal);
  calModal.addEventListener('click', function(e) {
    if (e.target === calModal || e.target === calClose) calModal.setAttribute('hidden', '');
  });
})();'''


def generate_theme_js(cfg):
    parts = []
    if cfg['dark_mode_toggle']['visible']:
        parts.append(THEME_TOGGLE_JS)
    if cfg['calendar']['visible']:
        parts.append(CALENDAR_JS)
        parts.append(CALENDAR_MODAL_JS)
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
