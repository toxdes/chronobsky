# Chronobsky

Archives your Bluesky posts and replies locally, and generates a static blog to browse them chronologically. Uses no external dependencies, just `python3`.

1. `fetch_bsky.py` - Crawls and archives your Bluesky posts and replies into local JSON files.
2. `gen.py` - Generates a static website from the archived data with chronological navigation, dark/light theme, and responsive design.
3. `deploy_vercel.py` - Deploys the generated site to Vercel as a production deployment.

## .env

Create a `.env` file in the project root:

```
BLUESKY_HANDLE=yourhandle.bsky.social
BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
VERCEL_TOKEN=your_vercel_api_token
```
#### Note
Be careful with `VERCEL_TOKEN` -- these tokens are account-level and don't have project-level granularity. Consider creating a separate Vercel account for this project so your other projects remain safe in case of a token compromise.

- `BLUESKY_HANDLE` + `BLUESKY_APP_PASSWORD` -- app password from Bluesky
  Settings > App Passwords
- `VERCEL_TOKEN` -- API token from https://vercel.com/account/tokens (only needed for deploying)

## Usage

```
$ python3 fetch_bsky.py     # fetch new posts from Bluesky
$ python3 gen.py            # generate static site in dist/
$ python3 deploy_vercel.py  # deploy dist/ to Vercel
```

Run `fetch_bsky.py` on a cron schedule (e.g. every 2 days). Run `gen.py` and `deploy_vercel.py` manually whenever you want to publish.
