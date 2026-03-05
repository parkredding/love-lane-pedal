#!/usr/bin/env bash
# Bump the StemStomp version.
#
# Usage:  bash scripts/bump-version.sh 0.2.0
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 0.2.0"
    exit 1
fi

VERSION="$1"
TAG="v${VERSION}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VERSION_FILE="$REPO_DIR/version.txt"

echo "$TAG" > "$VERSION_FILE"
echo "Updated version.txt to $TAG"

git add "$VERSION_FILE"
git commit -m "Bump version to $TAG"
git tag -a "$TAG" -m "Release $TAG"

echo "Created tag $TAG"
echo "Run 'git push origin main --tags' to trigger the release workflow."
