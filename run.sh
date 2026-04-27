#!/bin/bash
set -e
cd "$(dirname "$0")"

python3 fetch_bsky.py
python3 gen.py
python3 deploy_vercel.py
