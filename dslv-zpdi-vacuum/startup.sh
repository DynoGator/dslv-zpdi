#!/bin/sh
set -eu
if curl -fsS -o /dev/null --max-time 1 http://127.0.0.1:8080/; then
  exit 0
fi
cd /workspace
npm run dev > /tmp/dev-server.log 2>&1 &
