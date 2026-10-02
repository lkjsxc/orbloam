# Quiet World recovery and integration verification

This change restores the delivered `quiet-world-20260921` program on top of
GitHub `main` commit `08594a09ca26568d820da1ae9a8a6f38fbed8d79`. It does not
reimplement the missing delivery, regenerate its canonical graph, or upgrade
the language/runtime. No live player save was used by this verification.

## Provenance and preservation

- Recovered ZIP: `orbloam-quiet-world.zip`, 57,489,849 bytes,
  SHA-256 `5470d9082853ba85431a3d997d8731375ebddc3f4dad3adbcc51e76424a53513`
- Delivery source commit recorded by the package:
  `31683760ac49a304b9ff09527aef1c578cc1cf91`
- Restored application SHA-256:
  `5b925822ae0f1351d1d41efef5ccc877cd90281d2f7097d046352d30ecda6693`
- Pinned official lkjscript v0.1.38 runtime SHA-256:
  `98a39bd192c1e98187a1a954f916f5ffc89ef2586317c25e1efa06c61b888c32`
- Accepted revision:
  `rev_743c088998cb6d3c51e73c82591bb5b4295ef295ec797ef16deb748bce13d2f4`

All 380 entries in the delivered package checksum list and all three dist
checksum entries matched. The 14 accepted update receipts form a contiguous
chain from main's exact accepted revision to the restored revision. Their
request, logical-plan and apply-receipt hashes matched the build manifest.
All 83 pre-existing canonical packs are byte-identical; 107 packs are added.

The original authoring receipts and delivered evidence remain unchanged.
Fresh results are recorded separately under `evidence/integration-20261002/`.
The existing `RECOVER-SOURCE.txt`, `orbloam-reconstructed.bundle`, and two
main-only catalogue segments remain unchanged in the repository. The recovery
note and historical bundle are excluded from newly generated playable and
source ZIPs; optional Git history is still packaged separately. Downloaded
runtime binaries, temporary stores, package-output metadata and caches are not
part of the source change.

## Restored differences from main

- Resident lifetime changes from 360 to 90 exact 10-second ticks (15 minutes)
- The 96 discoveries use actual parent prerequisites, with 32 structural forks
- Existing rank prefixes remain owned; new node ownership is recorded independently
- Workshops select recipes natively by stock coverage, with explicit manual overrides
- The English interface defaults to an unobstructed world, with selection details,
  collision-checked research labels and continuous world-anchored rendering LOD
- Client writes are serialized, and an uncertain action retains its exact intent

The typed world schema, transport identities, service descriptor, startup path
and pinned runtime are unchanged. This does not mean gameplay semantics are
unchanged: unprocessed elapsed time uses the 90-tick lifetime rule, and older
workshops without `manual:<id>` overrides become automatic when eligible.
Re-select a fixed recipe where that behavior is desired.

Use the new-directory, logical-backup and absent-root restore procedure in
[OPERATIONS.md](OPERATIONS.md). Rollback requires the pre-update backup and old
program together; changing only the executable does not reverse newly written
research meaning or previously processed game time. Missing Stillworld saves
remain outside the compatibility claim.

## Integration-only corrections

1. CI retrieves the exact predecessor from commit `08594a09...`, verifies its
   SHA-256 `afd5213d7663e88d0a3fe1a13a1a8946bdd610f3f65279041536a66cae055828`,
   and passes it explicitly to the native upgrade test. Without that argument,
   the test's old-save section is skipped. The exact fetch/hash command was
   verified during this integration.
2. The protocol guide now describes `auto`, parent-gated discovery ownership,
   legacy prefixes and explicit fixed-recipe overrides.
3. Packaging excludes the two exact historical recovery files without removing
   them from Git. Matching `export-ignore` rules apply to the source archive.

These corrections do not change the delivered application or browser assets.

## Fresh verification

- Shell syntax, Python compilation, JavaScript syntax and `git diff --check`: passed
- Package/dist integrity and authoring-chain hashes: passed
- Native upgrade against the exact main artifact: passed; initial world and key
  unchanged, old rank prefixes retained, new discovery and workshop override accepted
- Native fork ownership, replay, foreign-owner rejection and restart persistence: passed
- HTTP/input validation, embedded bytes, native persistence and logical recovery: passed
- Independent population, scarcity and production oracles: passed
- Exact 360-tick catch-up with 512 residents/eight workshops: passed, 2,048
  independently calculated deaths, exact full-world agreement and zero final backlog
- All 72 recipes/products and 96 discoveries reachable under the stated unlimited-input
  graph assumption; 88 explicit parent edges: passed
- Independent presentation checks: 96 nodes, 32 forks, 63 regions and 3,980
  continuous-LOD samples: passed
- Copied standalone launch, restart, joined shutdown, corrupt-store refusal and
  parent-path rejection: passed
- Clean graph check: 89 tests, zero failures, equal differential execution; canonical
  HEAD unchanged. Both builds exactly reproduce the delivered artifact: passed
- Bounded 120-second native run, 512 residents/eight workshops: passed, 121
  requests, zero sampled backlog, 13.34 ms p95 sync and 23,986,176-byte peak sampled
  resident memory. All eight workshops produced goods; post-load move/replay and
  data verification passed. These measurements apply only to the recorded fixture
- Packaging: playable/source ZIP construction and content checks passed in an
  isolated local packaging checkout. Its temporary commit and ZIPs were not published.
  Packaging used the preserved artifact-bound delivery reports; fresh observations
  are identified separately in this directory of evidence

### Browser boundary

A fresh browser run was attempted, but Chromium failed before navigation because
its local process-singleton socket could not be created (`Operation not permitted`).
One approved environment retry had the same result. No bypass bridge was used and
no fresh browser-acceptance pass is claimed. The unchanged historical browser
report uses a declared blank-document/native-HTTP bridge; it does not establish
normal navigation, native storage permission/persistence, CSP/CORS enforcement,
clipboard, TLS or an external reverse proxy.

See [the fresh browser observation](../evidence/integration-20261002/browser-blocked.json)
and the original [verification scope](VERIFICATION.md). This integration does not
claim a deployment, many-player capacity, an indefinite soak test, or old Stillworld
save migration.
