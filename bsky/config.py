import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(ROOT, '.env')
TWEETS_DIR = os.path.join(ROOT, 'tweets')

PDS_URL = 'https://bsky.social'


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


_env = _load_dotenv(_ENV_PATH)
HANDLE = _env.get('BLUESKY_HANDLE', '')
APP_PASSWORD = _env.get('BLUESKY_APP_PASSWORD', '')
COUNTER_API_TENANT_ID = _env.get('COUNTER_API_TENANT_ID', '')
COUNTER_API_COUNTER_ID = _env.get('COUNTER_API_COUNTER_ID', '')


def validate():
    if not HANDLE:
        print('Error: BLUESKY_HANDLE not set in .env')
        exit(1)
    if not APP_PASSWORD:
        print('Error: BLUESKY_APP_PASSWORD not set in .env')
        exit(1)
