#!/usr/bin/env python3
from bsky.config import PDS_URL, HANDLE, APP_PASSWORD, TWEETS_DIR, validate, COUNTER_API_TENANT_ID, COUNTER_API_COUNTER_ID
from bsky.client import Client, HTTPError
from bsky.auth import login
from bsky.feed import fetch_feed, transform_feed_item
from bsky.storage import save_posts
from bsky.media import download_images
from bsky.state import load, save
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
def main():
    validate()

    client = Client(PDS_URL)

    print('Logging in...')
    try:
        token, did = login(client, HANDLE, APP_PASSWORD)
        client.set_token(token)
    except HTTPError as e:
        print(f'Auth failed: {e}')
        sys.exit(1)

    state = load()
    cutoff = state.get('latest_created_at')

    new_posts = []
    cursor = None
    page = 0
    done = False

    while not done:
        page += 1
        print(f'Fetching page {page}...')
        try:
            items, cursor = fetch_feed(client, HANDLE, cursor=cursor)
        except HTTPError as e:
            print(f'  Feed fetch error: {e}')
            break

        if not items:
            break

        for item in items:
            post = transform_feed_item(item, HANDLE)
            if not post:
                continue
            if cutoff and post['created_at'] <= cutoff:
                done = True
                break
            new_posts.append(post)

        if not cursor:
            break

    if not new_posts:
        print('No new posts.')
        _ping_counter()
        return

    print(f'Fetched {len(new_posts)} new posts/replies.')

    for post in new_posts:
        if post['images']:
            parts = post['created_at'].split('T')[0].split('-')
            media_dir = os.path.join(TWEETS_DIR, parts[0], parts[1])
            post['images_local_path'] = download_images(
                post['images'], post['id'], media_dir,
            )

    print('Saving posts...')
    save_posts(new_posts)

    newest = max(p['created_at'] for p in new_posts)
    save({'latest_created_at': newest})
    print('Done.')
    _ping_counter()


if __name__ == '__main__':
    main()
