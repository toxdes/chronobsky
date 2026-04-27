def _extract_images(embed):
    if not embed:
        return []
    if 'media' in embed:
        embed = embed['media']
    images = embed.get('images', [])
    if not images:
        return []
    return [img['fullsize'] for img in images if 'fullsize' in img]


# Both record#view and recordWithMedia#view carry the quoted post URI in the top-level record field
def _extract_quoted_id(embed):
    if not embed:
        return None
    if 'record' in embed:
        return embed['record'].get('uri')
    return None


def _rkey(uri):
    return uri.rpartition('/')[2]


def _post_url(uri, handle):
    return f'https://bsky.app/profile/{handle}/post/{_rkey(uri)}'


def fetch_feed(client, actor, cursor=None):
    params = {'actor': actor, 'limit': 100}
    if cursor:
        params['cursor'] = cursor
    data = client.get('app.bsky.feed.getAuthorFeed', params)
    return data.get('feed', []), data.get('cursor')


# getAuthorFeed returns posts AND replies by the actor, in reverse-chrono order
def transform_feed_item(item, actor):
    reason = item.get('reason')
    if reason and 'reasonRepost' in reason.get('$type', ''):
        return None

    post = item.get('post', {})
    record = post.get('record', {})
    uri = post.get('uri', '')

    is_reply = 'reply' in record
    parent_id = record['reply'].get('parent', {}).get('uri') if is_reply else None

    created_at = record.get('createdAt', '')
    content = record.get('text', '')
    if not created_at:
        return None

    embed = post.get('embed')
    image_urls = _extract_images(embed)
    quoted_post_id = _extract_quoted_id(embed)

    url = _post_url(uri, actor)

    return {
        'id': uri,
        'post_link': url,
        'content': content,
        'images': image_urls,
        'images_local_path': [],
        'created_at': created_at,
        'parent_id': parent_id,
        'quoted_post_id': quoted_post_id,
        'post_url': url,
    }
