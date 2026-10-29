#!/bin/zsh
# usage: ship.sh "message"
set -e
cd /Users/vedantiwari/ENAM-FINN/app/web && npm test >/dev/null && npm run build >/dev/null
cd .. && git add -A web/src web/public docs design DESIGN.md README.md 2>/dev/null; git commit -qm "$1

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q
npx vercel --prod --yes >/tmp/vercel.log 2>&1
sleep 4
live=$(curl -s https://finn-ledger.vercel.app | grep -o 'index-[A-Za-z0-9_-]*\.js'); localjs=$(ls web/dist/assets | grep 'index-.*\.js')
echo "live=$live local=$localjs"
