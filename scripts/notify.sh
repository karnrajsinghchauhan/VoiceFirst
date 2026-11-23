#!/usr/bin/env bash
# Posts a 3-5 line milestone summary (read from stdin) to Telegram when
# TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID exist. Otherwise prints it and exits 0:
# notification is not part of the product (brief 0.4).
set -euo pipefail
summary="$(cat)"
if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
  curl -fsS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" --data-urlencode "text=${summary}" >/dev/null
  echo "notify: sent to Telegram"
else
  echo "notify: no Telegram credentials; summary follows"
  echo "$summary"
fi
