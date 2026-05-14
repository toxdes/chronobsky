#!/usr/bin/env python3
from bsky.config import PDS_URL, HANDLE, APP_PASSWORD, TWEETS_DIR, validate, COUNTER_API_TENANT_ID, COUNTER_API_COUNTER_ID
from bsky.client import Client, HTTPError
from bsky.auth import login
from bsky.feed import fetch_feed, transform_feed_item
from bsky.storage import save_posts
from bsky.media import download_images
from bsky.state import load, save
import argparse
import os
import sys
import urllib.request


def _ping_counter():
    if not COUNTER_API_TENANT_ID or not COUNTER_API_COUNTER_ID:
        return
    url = (
        f'https://counter-api.toxdes.com/tenants/{COUNTER_API_TENANT_ID}'
        f'/counters/{COUNTER_API_COUNTER_ID}/inc'
    )
    try:
        req = urllib.request.Request(url, method='POST')
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


# getAuthorFeed returns items newest-first; the cutoff prevents re-processing old items
def _fetch_posts(client, handle, cutoff=None):
    posts = []
    cursor = None
    page = 0
    done = False
    while not done:
        page += 1
        print(f'Fetching page {page}...')
        try:
            items, cursor = fetch_feed(client, handle, cursor=cursor)
        except HTTPError as e:
            print(f'  Feed fetch error: {e}')
            break
        if not items:
            break
        for item in items:
            post = transform_feed_item(item, handle)
            if not post:
                continue
            if cutoff and post['created_at'] <= cutoff:
                done = True
                break
            posts.append(post)
        if not cursor:
            break
    return posts


def _download_and_save(posts, tweets_dir):
    for post in posts:
        if post['images']:
            parts = post['created_at'].split('T')[0].split('-')
            media_dir = os.path.join(tweets_dir, parts[0], parts[1])
            post['images_local_path'] = download_images(
                post['images'], post['id'], media_dir,
            )
    print('Saving posts...')
    save_posts(posts)


def _fetch_all(client, handle):
    import bsky.config as cfg_mod
    import bsky.media as media_mod
    import bsky.storage as storage_mod
    import shutil

    temp_dir = os.path.join(cfg_mod.ROOT, 'tweets_new')
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    old_tweets_dir = cfg_mod.TWEETS_DIR
    cfg_mod.TWEETS_DIR = temp_dir
    media_mod.TWEETS_DIR = temp_dir
    storage_mod.TWEETS_DIR = temp_dir

    try:
        posts = _fetch_posts(client, handle, cutoff=None)
        if not posts:
            print('No posts found.')
            return

        print(f'Fetched {len(posts)} posts/replies.')

        for post in posts:
            if post['images']:
                parts = post['created_at'].split('T')[0].split('-')
                media_dir = os.path.join(temp_dir, parts[0], parts[1])
                post['images_local_path'] = download_images(
                    post['images'], post['id'], media_dir,
                )

        print('Saving posts...')
        save_posts(posts)

        # Success — swap temp into place
        if os.path.exists(old_tweets_dir):
            shutil.rmtree(old_tweets_dir)
        os.rename(temp_dir, old_tweets_dir)

        newest = max(p['created_at'] for p in posts)
        state = load()
        state['latest_created_at'] = newest
        save(state)
        print(f'Done. Archived {len(posts)} posts.')
    except BaseException:
        # Failure — clean up temp, keep originals intact
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise
    finally:
        cfg_mod.TWEETS_DIR = old_tweets_dir
        media_mod.TWEETS_DIR = old_tweets_dir
        storage_mod.TWEETS_DIR = old_tweets_dir


def main():
    parser = argparse.ArgumentParser(description='Fetch Bluesky posts and archive them locally.')
    parser.add_argument('--all', action='store_true', help='Fetch all posts from scratch (destructive, replaces existing archive)')
    args = parser.parse_args()

    validate()

    client = Client(PDS_URL)

    print('Logging in...')
    try:
        token, did = login(client, HANDLE, APP_PASSWORD)
        client.set_token(token)
    except HTTPError as e:
        print(f'Auth failed: {e}')
        sys.exit(1)

    if args.all:
        _fetch_all(client, HANDLE)
        _ping_counter()
        return

    state = load()
    cutoff = state.get('latest_created_at')

    new_posts = _fetch_posts(client, HANDLE, cutoff=cutoff)

    if not new_posts:
        print('No new posts.')
        _ping_counter()
        return

    print(f'Fetched {len(new_posts)} new posts/replies.')

    _download_and_save(new_posts, TWEETS_DIR)

    newest = max(p['created_at'] for p in new_posts)
    state = load()
    state['latest_created_at'] = newest
    save(state)
    print('Done.')
    _ping_counter()


if __name__ == '__main__':
    main()
