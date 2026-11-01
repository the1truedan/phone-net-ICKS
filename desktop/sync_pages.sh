#!/usr/bin/env bash
# Prepare the bundled pages.
#   ./sync_pages.sh          public build: only the hypothetical example (ui/pages/example.html) + Mermaid
#   ADMIN=1 ./sync_pages.sh  admin build: also copies the owner's real site pages (git-ignored, never in a public release)
set -euo pipefail
cd "$(dirname "$0")"
SITE=../site
OUT=ui/pages
LIVE=https://the1truedan.github.io/phone-net-ICKS
MERMAID=10.9.1
ADMIN_PAGES=(workflow.html oct28-workflow.html)

mkdir -p "$OUT/vendor"
if [ ! -s "$OUT/vendor/mermaid.min.js" ]; then
  curl -sfL -o "$OUT/vendor/mermaid.min.js" \
    "https://cdn.jsdelivr.net/npm/mermaid@$MERMAID/dist/mermaid.min.js"
fi

if [ "${ADMIN:-0}" != "1" ]; then
  # Public build: make sure no owner-specific page is bundled.
  for p in "${ADMIN_PAGES[@]}"; do [ -f "$OUT/$p" ] && rm -- "$OUT/$p" && echo "removed admin page $OUT/$p"; done
  [ -f ui/admin.json ] && rm -- ui/admin.json && echo "removed ui/admin.json"
  echo "public pages: $(ls "$OUT"/*.html | xargs -n1 basename | tr '\n' ' ')"
  exit 0
fi

for p in "${ADMIN_PAGES[@]}"; do
  f="$OUT/$p"
  cp "$SITE/$p" "$f"
  sed -i.bak "s#https://cdn.jsdelivr.net/npm/mermaid@$MERMAID/dist/mermaid.min.js#vendor/mermaid.min.js#" "$f"
  sed -i.bak \
    -e 's#href="index.html"#href="../index.html"#g' \
    -e "s#href=\"analytics.html\"#href=\"$LIVE/analytics.html\"#g" \
    -e "s#href=\"sessions.html\"#href=\"$LIVE/sessions.html\"#g" "$f"
  sed -i.bak 's#<body>#<body><div class="example-banner" style="position:sticky;top:0;z-index:99;background:\#f0b429;color:\#1a1200;font:700 14px/1.4 system-ui,sans-serif;text-align:center;padding:.45rem 1rem">ADMIN · owner case page · not for public builds · <a style="color:\#1a1200" href="../index.html">back to the app</a></div>#' "$f"
  rm -f "$f.bak"
done
cp admin.json.example ui/admin.json
echo "admin pages synced: ${ADMIN_PAGES[*]} (git-ignored)"
