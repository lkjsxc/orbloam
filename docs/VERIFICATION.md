# Verification — Quiet World update

This report identifies the updated Orbloam bytes, not the lost Stillworld build,
not an unchanged-workload speedup, and not a remote-main publication. The previous
reconstruction report is preserved as [historical evidence](VERIFICATION-20260920.md).

## Exact accepted program

```text
Edition: quiet-world-20260921
Application bytes: 3657183
Application SHA-256: 5b925822ae0f1351d1d41efef5ccc877cd90281d2f7097d046352d30ecda6693
Runtime: unchanged official lkjscript v0.1.38 (Linux x86_64 musl)
Runtime SHA-256: 98a39bd192c1e98187a1a954f916f5ffc89ef2586317c25e1efa06c61b888c32
Accepted revision: rev_743c088998cb6d3c51e73c82591bb5b4295ef295ec797ef16deb748bce13d2f4
```

Fourteen accepted public updates follow the five original construction stages.
They retain the original world type and stable function/parameter owners. The
complete request → logical review → apply chain, including deferred intermediate
builds, is bound by [BUILD.json](../dist/BUILD.json) and retained in `authoring/`.
The source generator is not a replacement authority for `project/`.

The [clean check](../evidence/quiet-world/native-check.txt) returned
**89 passed, 0 failed, differential=equal**. This includes the standard
package's tests; it is not that many independent end-to-end game journeys.
The separate [rebuild](../evidence/rebuild.json) copied the accepted project without
derived compiler state, checked it in 196.768 seconds, then built it
twice in 14.282 and 13.738 seconds.
Both artifacts match each other and the shipped bytes. Canonical HEAD stayed
unchanged. The builds follow the clean check's compiler-state population, so those
build times are not cold-compilation measurements.

## Native gameplay, conservation, and recovery

[Acceptance](../evidence/acceptance.json) made 66 HTTP/recovery observations against
real native processes. Registration retry, identity, invalid inputs, ownership,
command sequence conflicts, identical-intent replay after later actions, concurrent
identical intent, restart, and logical backup/restore passed. Public world output
and backups contained no plaintext recovery credential. These are finite tests,
not a public-abuse or penetration audit.

An independent individual-seat enumeration matched native population arithmetic
in 48 cases, including lifetime boundaries and large diagnostic populations. All
72 recipes were compared on completion, missing-input, and full-warehouse paths:
216 recipe paths with exact input/output and factory-state checks. A two-colony,
512-residents-per-colony world matched an independently written full-grid oracle;
splitting chronological advancement preserved the complete world.

The [new native journey](../evidence/quiet-world/native.json) specifically proved:

- A child without its parent rejects; after the root, the right sibling can be
  bought before the left. Its unbought sibling stays unowned, and that sibling's
  children remain blocked. A duplicate purchase does not charge again.
- Fixed-recipe and automatic mode persist. An outsider cannot override another
  colony's workshop. Replay and process restart preserve the resulting world.
- The independently seeded 512-resident test buys two Vitality discoveries and
  reaches 608 places. This is a deliberately nonstandard fixture; normal maximum
  capacity remains 592, not 608.

[Catalogue validation](../evidence/catalogue.json) checks acyclic recipe inputs,
96 reachable discoveries, and 72 reachable products. It assumes unlimited
obtainable inputs and Essence; it is not an earned full-game playthrough, a balance
study, or a guarantee about time to completion.

## Immediate predecessor save admission

The predecessor test uses the real old application artifact with SHA-256
`afd5213d7663e88d0a3fe1a13a1a8946bdd610f3f65279041536a66cae055828` to create a typed world in a private store.
It stops that process, switches only the application artifact, and starts the new
one against the same store. Read-only admission returns an exactly equal world;
the same recovery key still works. A new discovery and a fixed-recipe override
work, and the pre-existing family ranks remain unchanged.

Native and presentation tests also check legacy-prefix ownership and the rule
that new family strength cannot retroactively unlock unbought siblings. No live
world was reset, regenerated, or rewritten to make the compatibility test pass.
This is admission of the immediately preceding **Orbloam v1** save, not migration
of the missing Stillworld format. Deferred steps run under the new lifespan rules;
already recorded totals are not recomputed. Keep a pre-update backup for rollback.

## One hour of exact catch-up with 15-minute lives

The fixture has 512 resident seats and eight workshops, with seeded stock/ranks.
It requests 360 ten-second steps of absence and actually
processes **360 steps**. Individual enumeration expects
**2048 resident returns**; native execution records
**2048**. The entire world, automatic recipe choices, eight
processing totals, and related stock/state match the independent oracle.

Measured catch-up is **2.267 seconds**, ending with
**0 backlog ticks**. A real subsequent move and its replay
succeed. The fixture command refuses to overwrite an existing world. These are
seeded tests, not player-earned progress or proof of arbitrarily long absences.

## Live 512-resident / eight-workshop observation

[Raw samples](../evidence/performance.json) use these exact final bytes with actual
wall time and native durable data for **120.003 seconds** and
**121 sync requests**. No simulation slowdown, skipped steps, reduced
population, or replacement backend was used.

| Observation | Result |
| --- | ---: |
| Maximum sampled backlog | 0 ticks |
| Final backlog | 0 ticks |
| Median sync latency | 2.46 ms |
| p95 sync latency | 9.31 ms |
| Maximum sync latency | 26.31 ms |
| Native server CPU time | 0.29 s |
| Peak sampled resident memory | 23,715,840 bytes |
| Post-load sync plus acknowledged move | 6.20 ms |
| Gathered units during observation | 1856 |

Workshop output totals were `[12, 18, 12, 18, 18, 18, 18, 9]`. Post-load replay was equal,
shutdown was joined, and native data verification passed.

**Most sync requests have no new ten-second economic step due.** These latencies
are not full-world-step execution times. RSS samples are not absolute transient
maxima. The post-load figure includes the helper's synchronization and action.
This finite test does not establish indefinite real time, many busy colonies,
every CPU, or browser frame rate.

Host: AMD EPYC 9V74 80-Core Processor; `Linux-6.18.44-x86_64-with-glibc2.41`; 5 CPUs in the
affinity mask; CPU quota `400000 100000` and memory limit
`4294967296`. The clean rebuild and browser tests completed
before this interval. The shared host was not claimed to be exclusive hardware.

## Rendering and interface checks

[Presentation tests](../evidence/quiet-world/presentation.json) compare analytical
regional totals with exhaustive cell-by-cell enumeration for 63 combinations of
strides and coordinates, including negative coordinates and resource-tier
boundaries. All eight resource-kind counts and capacities agree. They test
3,980 adjacent zoom samples for continuity. This checks
render aggregation, not a lower-fidelity economic model.

The tree has **96 nodes and 32 structural forks**, is acyclic, and has no center
separation below 54.36 world units. Native parent gates and
client ownership projection are tested separately. Browser label-placement checks
record zero label-box overlaps at desktop fit, selected fork, and mobile fit.
Low-priority labels yield rather than shrinking indefinitely or overlapping.

The [browser report](../evidence/quiet-world/browser/report.json) uses Chromium
144.0.7559.96, desktop 1440 × 960, mobile 390 × 844, and a reduced-motion viewport.
It confirms that every served HTML/CSS/JavaScript asset is exactly the committed
web source. Controls exercise native registration, an actual canvas research
purchase, explicit fork navigation, one-click paid building, persistent fixed/auto
recipes, and an automatically reconciled response deliberately dropped **after
native commit**. The action runs once; no manual retry button is needed.

Dragging and touch pinching change the camera without issuing a move. Four LOD
views remain finite; distant views draw aggregate regions, no resident sprites,
and no full resource sprites. Regional details, cinematic mode, safe untrusted
names, mobile recovery, no horizontal overflow, reduced-motion repainting, and a
single game-request lane pass. No client page exception was recorded.

**Important browser boundary:** normal local navigation was attempted and blocked
with `ERR_BLOCKED_BY_ADMINISTRATOR`. The explicitly selected fallback executes the
real served client in a blank document, forwarding calls to the real native server.
There is no mock world, client-awarded resource system, or replacement simulation.
The declared test storage adapter and module-URL adaptation do **not** verify
normal navigation, CSP/CORS, TLS, native persistent browser storage, clipboard
permissions, or an external reverse proxy. The production launcher does not use
the bridge. Screenshots show that test environment, not proof of those boundaries.

[World](../evidence/quiet-world/browser/screenshots/world.png) ·
[Close-up](../evidence/quiet-world/browser/screenshots/close-up.png) ·
[Research](../evidence/quiet-world/browser/screenshots/research-tree.png) ·
[Fork](../evidence/quiet-world/browser/screenshots/research-fork.png) ·
[Atlas](../evidence/quiet-world/browser/screenshots/atlas.png) ·
[Mobile](../evidence/quiet-world/browser/screenshots/mobile-world.png)

## Copied application, retained failures, and ZIP delivery

[Standalone acceptance](../evidence/standalone.json) copies only the runtime,
launcher, artifact, descriptor, and manifests into a path containing spaces. It
runs from an unrelated directory with no `project/`, `web/`, `tools/`, or tests
present. Only the native server is the launcher's child. Assets, registration,
Ctrl+C, joined shutdown, restart, and equal world admission pass. The all-IPv4
listener is exercised through `127.0.0.2`, not a separate LAN device. A damaged
private test store is rejected without reset; parent traversal rejects and
ephemeral descriptors are removed.

Rejected authoring attempts are retained under `authoring/rejected/`; they are not
accepted revisions. Earlier test failures and their corrections are described in
[evidence/history/quiet-world](../evidence/history/quiet-world/README.md). Historical
baseline/pilot reports keep their original hashes and are not final-build proof.

`tools/package.py` refuses a dirty checkout, missing or differently hashed final
reports, wrong runtime, mismatched web source, or tracked saves/caches. Its ZIP
contains the accepted graph, source, artifact, runtime, and licenses, with a full
payload checksum manifest. A source ZIP is also produced; Git history is optional
and separate. The final delivery inspection is performed on a newly extracted ZIP
and recorded alongside that ZIP, not asserted merely because packaging completed.

The updated GitHub workflow is configuration, not evidence of a remote CI run.
Neither these tests, a local commit, nor a ZIP implies publication to remote main.
