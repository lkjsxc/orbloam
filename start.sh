#!/bin/sh
# Launcher/configuration only. One unmodified lkjscript process serves all gameplay.
set -eu
umask 077
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PORT=8080
HOST=127.0.0.1
DATA=data
while [ "$#" -gt 0 ]; do
  case "$1" in
    --port) [ "$#" -ge 2 ] || exit 2; PORT=$2; shift 2 ;;
    --lan) HOST=0.0.0.0; shift ;;
    --data) [ "$#" -ge 2 ] || exit 2; DATA=$2; shift 2 ;;
    --help|-h) printf '%s\n' 'Usage: sh start.sh [--port 8080] [--lan] [--data data-restored]' \
      'Data paths are canonical relative paths underneath dist/. Existing saves are never reset.'; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
case "$PORT" in ''|*[!0-9]*) echo 'Port must be an integer 1..65535.' >&2; exit 2 ;; esac
[ "${#PORT}" -le 5 ] && [ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ] || { echo 'Port must be 1..65535.' >&2; exit 2; }
case "$DATA" in ''|/*|*/|*//*|*[!A-Za-z0-9_./-]*) echo 'Use a canonical relative data path, e.g. data or saves/world-1.' >&2; exit 2 ;; esac
case "/$DATA/" in */../*|*/./*) echo 'Dot/parent path segments are not allowed.' >&2; exit 2 ;; esac
BINARY=${LKJSCRIPT:-"$ROOT/runtime/lkjscript"}
case "$BINARY" in /*) ;; *) echo 'LKJSCRIPT must be an absolute path.' >&2; exit 2 ;; esac
[ -x "$BINARY" ] || { echo 'Runtime missing. Run: sh tools/install-runtime.sh' >&2; exit 1; }
printf '%s  %s\n' 98a39bd192c1e98187a1a954f916f5ffc89ef2586317c25e1efa06c61b888c32 "$BINARY" | sha256sum -c - >/dev/null
[ -f "$ROOT/dist/application.lkja" ] && [ -f "$ROOT/dist/SHA256SUMS" ] || { echo 'Accepted application artifact is missing.' >&2; exit 1; }
(cd "$ROOT/dist" && sha256sum -c SHA256SUMS >/dev/null)
SAVE="$ROOT/dist/$DATA"
# The native engine rejects symlink components. Never remove, reset, or migrate a save.
if [ ! -e "$SAVE" ] && [ ! -L "$SAVE" ]; then
  "$BINARY" data initialize --root "$SAVE"
fi
DEPLOYMENT=$(mktemp "$ROOT/dist/.run.XXXXXXXX.json")
CHILD=
cleanup() { rm -f -- "$DEPLOYMENT"; }
stop() {
  trap '' HUP INT TERM
  if [ -n "$CHILD" ]; then kill -INT "$CHILD" 2>/dev/null || :; wait "$CHILD" || :; fi
  exit 0
}
trap cleanup 0
trap stop HUP INT TERM
# DATA and listener are validated above, so no JSON or sed metacharacters enter substitution.
sed -e "s/\"listen\": \"127.0.0.1:8080\"/\"listen\": \"$HOST:$PORT\"/" \
    -e "s|\"root\": \"data\"|\"root\": \"$DATA\"|" \
    "$ROOT/dist/service.deployment.json" > "$DEPLOYMENT"
printf 'Orbloam: http://127.0.0.1:%s/\nSave: %s\n' "$PORT" "$SAVE"
if [ "$HOST" = 0.0.0.0 ]; then
  echo 'LAN mode exposes plaintext HTTP on all IPv4 interfaces. Protect recovery keys; use TLS or a trusted network.' >&2
fi
"$BINARY" serve --deployment "$DEPLOYMENT" &
CHILD=$!
set +e
wait "$CHILD"
STATUS=$?
set -e
CHILD=
exit "$STATUS"
