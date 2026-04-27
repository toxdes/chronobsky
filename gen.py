#!/usr/bin/env python3
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
    return dt.strftime('%B %d, %Y')


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

def render_post(post):
    is_reply = post['parent_id'] is not None
    cls = 'post' + (' reply' if is_reply else '')
    eid = _escape(post['id'])
    time_iso = post['created_at']
    time_short = format_time_short(time_iso)

    lines = [f'<article class="{cls}" id="{eid}">']
    lines.append('  <div class="post-meta">')
    lines.append(f'    <time datetime="{_escape(time_iso)}">{_escape(time_short)}</time>')
    if is_reply:
        lines.append('    <span class="reply-badge">↳ Reply</span>')
    if post.get('post_url'):
        lines.append(f'    <a href="{_escape(post["post_url"])}" class="post-link" target="_blank" rel="noopener" title="Open on Bluesky">↗</a>')
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


def render_day(date_str, posts):
    lines = [f'<section class="day" id="{date_str}">']
    lines.append(f'  <h2>{_escape(format_heading_date(date_str))}</h2>')
    for p in posts:
        lines.append(render_post(p))
    lines.append('</section>')
    return '\n'.join(lines)


def generate_html(days):
    sections = '\n'.join(render_day(d, ps) for d, ps in days.items())
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chronobsky Archive</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <div class="header-inner">
    <h1><a href="#">Chronobsky</a></h1>
    <nav>
      <a href="https://github.com/toxdes/chronobsky" class="gh-link" target="_blank" rel="noopener">Source</a>
      <button id="theme-toggle" aria-label="Toggle theme">🌚</button>
    </nav>
  </div>
</header>
<main>
<section class="intro">
  <p>Posts from <a href="https://bsky.app/profile/{_escape(HANDLE)}" target="_blank" rel="noopener">@{_escape(HANDLE)}</a> on bsky.social as a blog</p>
</section>
{sections}
</main>
<script src="theme.js"></script>
</body>
</html>'''


# ── Static assets ───────────────────────────────────────────────

STYLE_CSS = r'''/* ── Variables ────────────────────────────────────── */
:root {
  --bg: #ffffff;
  --text: #0f172a;
  --border: #e2e8f0;
  --accent: #2563eb;
  --muted: #64748b;
  --reply: #f1f5f9;
  --header: rgba(255, 255, 255, 0.85);
  --link-icon: #cbd5e1;
}

:root.dark {
  --bg: #0f172a;
  --text: #e2e8f0;
  --border: #1e293b;
  --accent: #60a5fa;
  --muted: #94a3b8;
  --reply: #1e293b;
  --header: rgba(15, 23, 42, 0.85);
  --link-icon: #475569;
}

/* ── Reset ──────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }

body {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.7;
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  transition: background .3s, color .3s;
}

/* ── Header ─────────────────────────────────────── */
header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--header);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  transition: background .3s, border-color .3s;
}

.header-inner {
  max-width: 680px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
}

header h1 { font-size: 18px; font-weight: 700; letter-spacing: -.01em; }
header h1 a { color: var(--text); text-decoration: none; }

header nav { display: flex; align-items: center; gap: 12px; }

.gh-link {
  font-size: 13px;
  font-weight: 500;
  color: var(--muted);
  text-decoration: none;
  transition: color .2s;
}
.gh-link:hover { color: var(--accent); }

#theme-toggle {
  background: none;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 18px;
  cursor: pointer;
  line-height: 1;
  transition: border-color .2s;
}
#theme-toggle:hover { border-color: var(--accent); }

/* ── Main ───────────────────────────────────────── */
main {
  max-width: 680px;
  margin: 0 auto;
  padding: 40px 24px 80px;
}

.intro {
  margin-bottom: 40px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
  color: var(--muted);
  line-height: 1.6;
  transition: border-color .3s;
}

.intro a {
  color: var(--accent);
  text-decoration: none;
  font-weight: 500;
}
.intro a:hover { text-decoration: underline; }

/* ── Day section ────────────────────────────────── */
.day { margin-bottom: 48px; }
.day h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--accent);
  margin-bottom: 24px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--border);
  transition: color .3s, border-color .3s;
}

/* ── Post card ──────────────────────────────────── */
.post {
  margin-bottom: 16px;
  padding: 16px 20px;
  border-radius: 12px;
  border: 1px solid var(--border);
  scroll-margin-top: 70px;
  transition: border-color .3s, background .3s;
}
.post.reply { background: var(--reply); }

.post-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--muted);
}
.post-meta time { font-weight: 500; }

.reply-badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  padding: 1px 6px;
  border-radius: 4px;
  background: color-mix(in srgb, var(--accent) 10%, transparent);
}

.post-link {
  margin-left: auto;
  color: var(--link-icon);
  text-decoration: none;
  font-size: 14px;
  opacity: 0;
  transition: opacity .2s;
}
.post:hover .post-link { opacity: 1; }
.post-link:hover { color: var(--accent); }

.quote-link {
  display: inline-block;
  margin-top: 10px;
  font-size: 13px;
  font-weight: 500;
  color: var(--accent);
  text-decoration: none;
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid var(--border);
  transition: background .2s, border-color .2s;
}
.quote-link:hover {
  background: color-mix(in srgb, var(--accent) 8%, transparent);
  border-color: var(--accent);
}

/* ── Content ────────────────────────────────────── */
.post-content {
  font-size: 15px;
  line-height: 1.7;
  word-wrap: break-word;
  overflow-wrap: break-word;
}
.post-content p { margin-bottom: 8px; }
.post-content p:last-child { margin-bottom: 0; }
.post-content a {
  color: var(--accent);
  word-break: break-all;
}

/* ── Images ─────────────────────────────────────── */
.post-images {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.post-images img {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid var(--border);
}

/* ── Responsive ─────────────────────────────────── */
@media (max-width: 600px) {
  main { padding: 24px 16px 60px; }
  .post { padding: 12px 14px; }
  .post-content { font-size: 14px; }
  .day h2 { font-size: 18px; }
}

/* ── Print ──────────────────────────────────────── */
@media print { header, .post-link { display: none; } }
'''

THEME_JS = r'''(function() {
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
    this.textContent = isDark ? '😎' : '🌚';
  });
})();
'''


# ── Main ────────────────────────────────────────────────────────

def main():
    posts = load_all_posts()
    if not posts:
        print('No posts found in tweets/.')
        return

    parent_lookup = build_parent_lookup(posts)
    days = group_by_date(posts)

    os.makedirs(DIST_DIR, exist_ok=True)

    with open(os.path.join(DIST_DIR, 'index.html'), 'w') as f:
        f.write(generate_html(days))

    with open(os.path.join(DIST_DIR, 'style.css'), 'w') as f:
        f.write(STYLE_CSS)

    with open(os.path.join(DIST_DIR, 'theme.js'), 'w') as f:
        f.write(THEME_JS)

    total = sum(len(v) for v in days.values())
    print(f'Generated dist/ — {len(days)} days, {total} posts.')


if __name__ == '__main__':
    main()
