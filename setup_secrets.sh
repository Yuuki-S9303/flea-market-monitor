#!/bin/bash
GDRIVE=$(find "$HOME/Library/CloudStorage" -maxdepth 1 -name "GoogleDrive-*" 2>/dev/null | head -1)
if [ -z "$GDRIVE" ]; then echo "Error: Google Drive not found"; exit 1; fi
SECRETS="$GDRIVE/マイドライブ/secrets/flea-market-monitor"
DIR="$(cd "$(dirname "$0")" && pwd)"
ln -sf "$SECRETS/.env" "$DIR/.env"
echo "Done: $DIR/.env -> $SECRETS/.env"
