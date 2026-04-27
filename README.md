# Chronobsky

Archives your Bluesky posts and replies locally, and generates a static blog to browse them chronologically. Uses no external dependencies, just `python3`.

1. `fetch_bsky.py` - Crawls and archives your Bluesky posts and replies into local JSON files.
2. `gen.py` - Generates a static website from the archived data with chronological navigation, dark/light theme, and responsive design.
3. `deploy_vercel.py` - Deploys the generated site to Vercel as a production deployment.

## .env

```
BLUESKY_HANDLE=yourhandle.bsky.social
BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
VERCEL_TOKEN=your_vercel_api_token
```

- `BLUESKY_HANDLE` + `BLUESKY_APP_PASSWORD` -- app password from Bluesky
  Settings > App Passwords
- `VERCEL_TOKEN` -- API token from https://vercel.com/account/tokens (only needed for deploying)

#### Note
Be careful with `VERCEL_TOKEN` -- these tokens are account-level and don't have project-level granularity. Consider creating a separate Vercel account for this project so your other projects remain safe in case of a token compromise.

## Usage

```
$ python3 fetch_bsky.py     # fetch new posts from Bluesky
$ python3 gen.py            # generate static site in dist/
$ python3 deploy_vercel.py  # deploy dist/ to Vercel
$ ./run.sh                  # run all three in sequence
```

## Deployment

1. Clone the repository:
   ```
   git clone --depth=1 https://github.com/toxdes/chronobsky.git
   cd chronobsky
   ```

2. Get your Bluesky app password:
   - Go to Bluesky Settings > App Passwords
   - Click "Add App Password", give it a name, and copy the generated password
   - Your handle is your Bluesky username (e.g. `user.bsky.social` or `user.com` if you have a custom domain)

3. Get your Vercel API token:
   - Go to https://vercel.com/account/tokens
   - Create a new token with any name and copy it

4. Set up the environment:
   ```
   cp .env.example .env
   ```
   Then edit `.env` and fill in your handle, app password, and Vercel token.

5. Register a cron job to run every 48 hours:
   ```
   crontab -e
   ```
   Add this line:
   ```
   0 6 */2 * * /path/to/chronobsky/run.sh
   ```
   This runs the full pipeline (fetch, generate, deploy) at 6 AM every other day.
