#!/bin/zsh
# usage: ship.sh "message"            test, build, commit, push, deploy to finn-ledger-next
#        ship.sh "message" --live     the same, then deploy to the live finn-ledger (only after the stage 4 comparison)
# finn-ledger-v2..v5 are backups: nothing here touches them.
set -e
cd /Users/vedantiwari/ENAM-FINN/app/web && npm test >/dev/null && npm run build >/dev/null
cd .. && git add -A web/src web/public web/test docs design DESIGN.md README.md 2>/dev/null; git commit -qm "$1

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" || true; git push -q
# The next project deploys from a detached worktree linked to it, so app/ stays linked to finn-ledger
cd ../next-deploy && git checkout -q --detach main && npx vercel deploy --prod --yes >/tmp/vercel-next.log 2>&1
grep -E "Aliased" /tmp/vercel-next.log
if [[ "$2" == "--live" ]]; then
  cd ../app && npx vercel --prod --yes >/tmp/vercel.log 2>&1
  sleep 4
  live=$(curl -s https://finn-ledger.vercel.app | grep -o 'index-[A-Za-z0-9_-]*\.js'); localjs=$(ls web/dist/assets | grep 'index-.*\.js')
  echo "live=$live local=$localjs"
fi
