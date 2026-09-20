# Running and preserving a world

## Keep the three independent assets

Keep the accepted program (repository/Git bundle), the matching official runtime, and the live data backup. A recovery key identifies a colony; it does not contain the colony's save. A screenshot, temporary chat link, or expiring Actions artifact is not source control or a server backup.

The launcher uses `runtime/lkjscript` by default, and accepts an absolute `LKJSCRIPT` override only when its bytes match the pinned runtime. Startup checks `dist/SHA256SUMS`. It starts one native server, forwards shutdown to it, and does not need the authoring checkout, Python, Node or Cargo. Serving from another working directory is supported.

`sh start.sh --port 8080` binds loopback. Add `--lan` for all IPv4 interfaces on a trusted network. The launcher does not configure firewall, DNS, TLS, router forwarding or an external proxy. If a desired port is occupied, choose a different one; do not kill unrelated processes.

The save is relative to the artifact directory: default `dist/data/`. `sh start.sh --data data-restored` explicitly selects `dist/data-restored/`. Parent traversal and dot segments reject. The native store also rejects symbolic-link components. Nonexistent parent directories should be created by the operator as ordinary owned directories. Existing roots are never initialized over, wiped or silently converted.

## Logical backup and absent-root restore

Stop the game with Ctrl+C first. Use unused output/root names and retain the original until recovery is verified. From the application directory:

```sh
runtime/lkjscript data verify --root "$PWD/dist/data"
runtime/lkjscript data backup --root "$PWD/dist/data" --output "$PWD/orbloam-backup.lkjd"
runtime/lkjscript data restore --backup "$PWD/orbloam-backup.lkjd" --root "$PWD/dist/data-restored"
runtime/lkjscript data verify --root "$PWD/dist/data-restored"
sh start.sh --data data-restored
```

After checking the actual world and private recovery keys, the operator may archive the predecessor root offline. Restore creates a new root; it neither overwrites the old root nor switches a running process. It is not schema conversion. The native engine retains immutable history; periodic logical backup/restore can reduce obsolete physical history, not current live game facts. No online compaction or automatic deletion is supplied.

Do not modify `dist/service.deployment.json` or `dist/application.lkja` while the process is running. Build into absent temporary paths, verify the accepted graph/asset hash, back up data, stop the process and deliberately switch compatible files. Update the artifact manifest only for an accepted and verified change. Keep prior compatible bytes for rollback; switching a binary alone does not reverse new data meaning.

## Reverse proxies

Serve HTML, JavaScript and API from the same external origin. A prefix deployment should redirect `/orbloam` to `/orbloam/`, then strip `/orbloam/` before forwarding to the native root. All relative asset/import/API paths are authored for that arrangement. Do not inject a different API origin or use `file://`.

A reverse proxy must preserve Authorization, restrict request-body logging, and supply protected transport. The application is ordinary HTTP polling, not WebSocket. Browser-bridge tests do not establish that a specific external proxy, CSP policy, DNS setup or TLS deployment works.

## Native verification and fixtures

`python3 tests/acceptance.py` creates fresh private temporary stores under `.test-state/`, exercises real native commands and HTTP, and writes a redacted report. It does not use a Python game server. `python3 tests/performance.py --seconds 120` is an explicit 512-person/8-workshop fixture, not earned progress or proof of 64 busy colonies.

`python3 tests/browser.py` requires Playwright and Chromium and prefers real navigation. `--bridge-if-blocked` permits an explicitly recorded blank-document bridge only when navigation reports `ERR_BLOCKED_BY_ADMINISTRATOR`. The bridge uses the real HTTP application and a declared test storage adapter; it does not validate native browser storage/security. Never include that bridge in the launch path.

Fixtures contain private generated credentials and are excluded from distribution/version control. Leave user-owned data alone. Tests must not run against a player's live save.

## Remote integration handoff

The reconstruction bundle is based on the exact public initial commit `9b3d8db72e2483bcf083aeb604d5366848417bf9`. It includes that actual signed ancestor, not a replacement orphan history. The continuation environment offered read-only GitHub operations and no usable authenticated CLI, so local reconstruction is **not** a remote-main completion claim.

To inspect without touching an existing checkout:

```sh
git clone --branch main orbloam-reconstructed.bundle orbloam-recovered
cd orbloam-recovered
git remote set-url origin https://github.com/lkjsxc/orbloam.git
git fetch origin
git merge-base --is-ancestor origin/main main && git push origin main
```

Run the push only if the ancestry check succeeded. Do not use `--force`. If remote main has advanced, reconcile that work in a normal branch/review before integration. The bundle/source files must first be saved locally; the bundle does not need the expired ZIP or a ChatGPT session to reconstruct its Git history. Once accepted source is on GitHub, future retrieval should use that repository rather than temporary chat links.
