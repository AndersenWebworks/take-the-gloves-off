#!/usr/bin/env bash
# Baut die öffentliche Seite aus dem zuletzt committeten Stand und
# veröffentlicht sie über den Branch gh-pages auf GitHub Pages:
#   /            Landingpage
#   /styleguide/ Styleguide
# Solange der Entwurf nicht freigegeben ist, steht auf beiden Seiten noindex.
# Arbeitet nur mit Git-Objekten, der Projektordner bleibt unberührt.
set -euo pipefail
cd "$(dirname "$0")"

export GIT_INDEX_FILE="$(git rev-parse --git-dir)/index-gh-pages"
trap 'rm -f "$GIT_INDEX_FILE"' EXIT

git read-tree HEAD:03_unsere_arbeit/landingpage
git read-tree --prefix=styleguide/ HEAD:03_unsere_arbeit/styleguide
for p in index.html styleguide/index.html; do
  blob=$(git show ":$p" | sed 's#<head>#<head>\n<meta name="robots" content="noindex, nofollow">#' | git hash-object -w --stdin)
  git update-index --cacheinfo "100644,$blob,$p"
done
git update-index --add --cacheinfo "100644,$(git hash-object -w --stdin </dev/null),.nojekyll"
TREE=$(git write-tree)

git fetch -q origin gh-pages 2>/dev/null || true
PARENT=$(git rev-parse -q --verify refs/remotes/origin/gh-pages || true)
if [ -n "$PARENT" ] && [ "$(git rev-parse "$PARENT^{tree}")" = "$TREE" ]; then
  echo "Keine Änderungen gegenüber der veröffentlichten Fassung."
  exit 0
fi
COMMIT=$(git commit-tree "$TREE" ${PARENT:+-p "$PARENT"} \
  -m "Veröffentlichung aus $(git rev-parse --short HEAD)" \
  -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
git push -q origin "$COMMIT:refs/heads/gh-pages"
echo "Veröffentlicht: $COMMIT"
