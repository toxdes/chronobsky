#!/usr/bin/env python3
import base64
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error

DIST_DIR = 'dist'
API_URL = 'https://api.vercel.com/v13/deployments'
PROJECT_NAME = 'chronobsky'

_TEXT_EXTS = {'.html', '.css', '.js', '.json', '.svg', '.txt', '.xml', '.map'}


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


def _is_text(path):
    return os.path.splitext(path)[1].lower() in _TEXT_EXTS


def _collect_files():
    if not os.path.isdir(DIST_DIR):
        print(f'Error: {DIST_DIR}/ not found. Run gen.py first.')
        sys.exit(1)

    files = []
    for root, _dirs, fnames in os.walk(DIST_DIR):
        for fname in sorted(fnames):
            fpath = os.path.join(root, fname)
            relpath = os.path.relpath(fpath, DIST_DIR)
            with open(fpath, 'rb') as f:
                content = f.read()
            if _is_text(fpath):
                files.append({'file': relpath, 'data': content.decode('utf-8')})
            else:
                files.append({'file': relpath, 'data': base64.b64encode(content).decode('ascii'), 'encoding': 'base64'})
    return files


def main():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    env = _load_dotenv(env_path)
    token = env.get('VERCEL_TOKEN', '')

    if not token:
        print('Error: VERCEL_TOKEN not set in .env')
        print('Create a token at https://vercel.com/account/tokens')
        sys.exit(1)

    project_name = env.get('VERCEL_PROJECT_NAME', PROJECT_NAME)
    team_id = env.get('VERCEL_TEAM_ID')

    files = _collect_files()
    if not files:
        print(f'Error: {DIST_DIR}/ is empty. Run gen.py first.')
        sys.exit(1)

    print(f'Deploying {len(files)} files from {DIST_DIR}/...')

    body = {
        'name': project_name,
        'files': files,
        'projectSettings': {'framework': None},
        'target': 'production',
    }

    payload = json.dumps(body).encode('utf-8')
    url = API_URL
    if team_id:
        url += f'?teamId={urllib.parse.quote(team_id)}'

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f'Deployment failed (HTTP {e.code}):')
        try:
            err = json.loads(body)
            print(err.get('error', {}).get('message', body))
        except json.JSONDecodeError:
            print(body)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f'Network error: {e.reason}')
        sys.exit(1)

    deploy_url = result.get('url', '')
    inspector_url = result.get('inspectorUrl', '')

    print(f'Deployed: https://{deploy_url}')
    if inspector_url:
        print(f'Inspector: {inspector_url}')


if __name__ == '__main__':
    main()
