import os
import urllib.parse
import urllib.request
import urllib.error

from .config import TWEETS_DIR


def _guess_extension(url):
    path = urllib.parse.urlparse(url).path.lower()
    # Bluesky CDN appends @jpeg, @png etc.
    at_suffix = path.rpartition('@')[2]
    if at_suffix in ('jpeg', 'jpg', 'png', 'gif', 'webp'):
        return '.' + at_suffix
    for ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
        if ext in path:
            return ext
    return '.jpg'


# One image download — returns relative path from TWEETS_DIR, or None on failure
def _download_one(url, post_uri, index, dest_dir):
    ext = _guess_extension(url)
    rkey = post_uri.rpartition('/')[2]
    filename = f'{rkey}_{index}{ext}'
    filepath = os.path.join(dest_dir, filename)
    if os.path.exists(filepath):
        return os.path.relpath(filepath, TWEETS_DIR)
    try:
        urllib.request.urlretrieve(url, filepath)
    except (urllib.error.URLError, OSError) as e:
        print(f'  Warning: failed to download {url}: {e}')
        return None
    return os.path.relpath(filepath, TWEETS_DIR)


def download_images(image_urls, post_uri, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    return [
        _download_one(url, post_uri, i, dest_dir)
        for i, url in enumerate(image_urls)
    ]
