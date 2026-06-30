#!/bin/sh
set -e

# Require VLESS_UUID to be set at runtime; do not fall back to a default
if [ -z "$VLESS_UUID" ]; then
  echo "ERROR: VLESS_UUID environment variable is not set." >&2
  exit 1
fi

# Inject the UUID into the config template
sed "s/__VLESS_UUID__/${VLESS_UUID}/" /app/config.json.template > /app/config.json

exec ./sing-box run -c config.json
