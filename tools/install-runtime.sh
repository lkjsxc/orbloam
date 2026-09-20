#!/bin/sh
# Exact official runtime acquisition. No root, package manager, or floating latest.
set -eu
umask 077
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
DEST="$ROOT/runtime"
ARCHIVE_SHA=fa10e7afb09c06e4a243f421050a0497ca9acd331cdf34c046650c85aef377aa
BINARY_SHA=98a39bd192c1e98187a1a954f916f5ffc89ef2586317c25e1efa06c61b888c32
if [ "$(uname -s)" != Linux ] || [ "$(uname -m)" != x86_64 ]; then
  echo 'The pinned runtime requires Linux x86_64 (Windows: use WSL2).' >&2; exit 1
fi
if [ -e "$DEST" ] || [ -L "$DEST" ]; then
  if [ -x "$DEST/lkjscript" ] && [ ! -L "$DEST" ] && [ ! -L "$DEST/lkjscript" ]; then
    printf '%s  %s\n' "$BINARY_SHA" "$DEST/lkjscript" | sha256sum -c -
    "$DEST/lkjscript" --version
    exit 0
  fi
  echo 'Existing runtime directory is not an intact installation; preserve it and use a clean checkout.' >&2; exit 1
fi
STAGE=$(mktemp -d "$ROOT/.install-runtime.XXXXXXXX")
trap 'rm -rf -- "$STAGE"' 0
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
if [ "$#" -gt 1 ]; then echo 'Usage: sh tools/install-runtime.sh [local-exact-runtime.tar.gz]' >&2; exit 2; fi
if [ "$#" -eq 1 ]; then
  cp -- "$1" "$STAGE/archive.tar.gz"
else
  curl -q --fail --location --silent --show-error --proto '=https' --proto-redir '=https' \
    --connect-timeout 15 --max-time 180 --max-filesize 20000000 --retry 2 \
    --output "$STAGE/archive.tar.gz" \
    https://github.com/lkjsxc/lkjscript/releases/download/v0.1.38/lkjscript-x86_64-unknown-linux-musl.tar.gz
fi
printf '%s  %s\n' "$ARCHIVE_SHA" "$STAGE/archive.tar.gz" | sha256sum -c -
tar -xzf "$STAGE/archive.tar.gz" -C "$STAGE"
printf '%s  %s\n' "$BINARY_SHA" "$STAGE/lkjscript/lkjscript" | sha256sum -c -
"$STAGE/lkjscript/lkjscript" --version
# Refuse replacement, including a concurrently appearing directory.
[ ! -e "$DEST" ] && [ ! -L "$DEST" ] || { echo 'Destination appeared during installation; refusing replacement.' >&2; exit 1; }
mv -T -n -- "$STAGE/lkjscript" "$DEST"
[ ! -e "$STAGE/lkjscript" ] || { echo 'Installation lost a destination race; existing runtime preserved.' >&2; exit 1; }
printf 'Installed: %s/lkjscript\n' "$DEST"
