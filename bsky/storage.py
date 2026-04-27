import json
import os
import tempfile

from .config import TWEETS_DIR


def _split_date(created_at):
    parts = created_at.split('T')[0].split('-')
    return int(parts[0]), int(parts[1]), int(parts[2])


def _read_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath) as f:
        return json.load(f)


# Atomic write to avoid corrupting files on partial writes
def _write_json_atomic(filepath, data):
    dirpath = os.path.dirname(filepath)
    os.makedirs(dirpath, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dirpath, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, filepath)
    except BaseException:
        os.unlink(tmp)
        raise


def _dedup(posts):
    seen = {}
    for p in posts:
        seen[p['id']] = p
    return list(seen.values())


def save_posts(posts):
    if not posts:
        return

    grouped = {}
    for p in posts:
        y, m, d = _split_date(p['created_at'])
        grouped.setdefault((y, m, d), []).append(p)

    for (y, m, d), day_posts in grouped.items():
        filepath = os.path.join(TWEETS_DIR, str(y), f'{m:02d}', f'{d:02d}.json')
        existing = _read_json(filepath)
        merged = _dedup(existing + day_posts)
        merged.sort(key=lambda p: p['created_at'])
        _write_json_atomic(filepath, merged)
