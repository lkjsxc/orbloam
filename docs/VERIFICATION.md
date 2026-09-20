# Verification — Orbloam reconstruction

This records the actual reconstructed application tested on 2026-09-20, not the lost
Stillworld ZIP and not acceptance of GitHub's remote main. The game's new economic
rules use exact 10-second ticks and birth-time cohorts. Measurements must not be
represented as an unchanged-workload speedup over the predecessor.

## Exact bytes and accepted meaning

```text
Application bytes: 3290046
Application SHA-256: afd5213d7663e88d0a3fe1a13a1a8946bdd610f3f65279041536a66cae055828
Runtime: unchanged official lkjscript v0.1.38, Linux x86_64 musl target
Runtime SHA-256: 98a39bd192c1e98187a1a954f916f5ffc89ef2586317c25e1efa06c61b888c32
Accepted revision: rev_6aaf8ee080b208c3852bdbdcd1ce7aa4309ed9eca9354971d0a483969d5d713d
Artifact bundle: artifact_bundle_cd32fa3ee94e0d46443dbf5234d3516ecec2628d1d3aac068a15e59f026ce618
```

The native public `check` returned **72 passed, 0 failed, differential=equal**.
This count includes standard-package tests; it does not mean 72 independent game
journeys. Public proposal, logical-review, and apply records are retained under
`authoring/`; the actual accepted meaning is in `project/`, not in a handwritten
replacement for its storage. See [build identity](../evidence/build/identity.json),
[native check](../evidence/build/check.txt), and [build](../evidence/build/build.txt).

The separate [clean rebuild](../evidence/rebuild.json) copied the accepted project
without derived compiler caches. A clean check succeeded in 299.500 seconds. Two
subsequent native builds took 22.206 and 21.142 seconds and returned byte-identical
artifacts, also identical to the shipped artifact. None of those lifecycle
commands changed the canonical HEAD. The first build follows a clean check that
has populated compiler state; its time is not a completely cold-build measurement.
Fresh authoring allocates new identities and is not claimed to reproduce those
identities; rebuilding this same accepted graph does reproduce the delivered bytes.

## Actual native HTTP, transactions, and recovery

[Native acceptance](../evidence/acceptance.json) contains three separate groups.
The HTTP/recovery group made 66 observations against real native processes, not a
Python or JavaScript implementation of the game. It covered two distinct colonies,
registration retry after a lost response, valid and invalid credentials, strict
JSON rejection, ownership, host variation, and all nine command kinds: move,
rename, research, build, pause, recipe, transfer, repair, and dismantle.

Identical command replay after later accepted operations preserved the original
receipt without a second effect. Concurrent identical intent was applied once;
reused numbers with different intent were rejected. Restart and logical backup /
restore returned equal world values. Public world output and the logical backup
contained no plaintext recovery credential. Native data verification succeeded.
These are finite application tests, not a penetration test or public-abuse audit.

The independent-oracle group compared arithmetic cohort counts against individual
seat enumeration in **48 cases**, including 512 and 4,096 seats and lifetime
boundaries. It compared a complete two-colony world with 512 inhabitants in each
against an independently authored brute-force full-grid resource calculation.
Splitting advancement into batches preserved the complete canonical world.
The 4,096-seat observations test population arithmetic, not live capacity.

All **72 recipes** were invoked through native execution with three paths each:
completion, missing input, and full warehouse. Exact resulting inputs, products,
and factory states were compared with independent expected values. This is 216
recipe paths, not 216 separately earned progression runs. The native result was
paged through 20 bounded diagnostic invocations instead of raising output limits.

The separate [catalogue audit](../evidence/catalogue.json) read the actual served
catalogue: all 72 recipe dependencies are acyclic, all 96 research steps and 72
products are logically reachable, and facility gates are consistent. It assumes
unlimited obtainable inputs and essence. It does not prove economic balance,
earned end-to-end progression, or a reasonable completion time.

## Exact one-hour absence

The native acceptance seeded **512 inhabitants and eight workshops** in a fresh,
private fixture. It requested a 360-tick absence. The wall clock crossed another
tick during setup, so the final execution processed **361 ten-second ticks**,
not exactly 360. The independent expected and actual death totals were both **513**.
All eight processing totals and related states agreed with the oracle.

Catch-up took **3.625 seconds** of measured wall time and ended with zero backlog
ticks. A subsequent actual move and its replay succeeded. The fixture command
refused to overwrite an existing world. Seeded ranks, residents, and stock are
test setup, not player-earned progress. This is one observed hour-sized backlog,
not acceptance of arbitrary absences or arbitrary world sizes.

## Live 512-inhabitant, eight-workshop measurement

[Raw samples and report](../evidence/performance.json) bind the same final artifact.
A real native HTTP process handled one sync request per second for **120.005
seconds**, for **121 requests**, with its actual wall clock and durable data.
There was no separate game backend, hidden clock slowdown, skipped economic tick,
or reduction in the fixture's population.

| Observation | Measured result |
|---|---:|
| Maximum sampled backlog | 0 ticks |
| Final backlog | 0 ticks |
| Median sync latency | 3.87 ms |
| p95 sync latency | 25.46 ms |
| Maximum sync latency | 39.86 ms |
| Native server CPU time during the interval | 0.58 s |
| Peak sampled resident memory | 20,525,056 bytes, approximately 19.6 MiB |
| Post-load sync plus acknowledged move | 8.90 ms |
| Gathered units during measurement | 1,856 |

All eight workshops produced real outputs; the first seven produced 24 units each
and the eighth produced 12. Replaying the final move returned an equal receipt.
The server was joined and its native data verified after the interval.

**Most sync requests do not have a new economic tick due.** These request latencies
must not be labelled as full-world tick times. Resident-memory samples do not prove
an absolute transient maximum. The post-load figure includes the helper's sync
and action, not just one isolated native instruction or visual animation.

Host observations: Intel Xeon Platinum 8573C, Linux 6.18.44 x86_64, five CPUs in the
process affinity mask, cgroup CPU setting `400000 100000` (four-CPU quota), and a
4-GiB cgroup memory limit. No other CPU-heavy test/build was run during the timed
interval; a shared container host is not a guarantee of exclusive hardware.
This does not establish indefinite real time, 64 busy colonies, every CPU, or
browser frame rate. The one-world typed-value representation and other capacity
limits remain documented in [known limitations](KNOWN-LIMITATIONS.md).

## Standalone application boundary

[Standalone acceptance](../evidence/standalone.json) copied only the launcher,
matching runtime, application artifact, descriptor, and manifest into a directory
whose path contained spaces. It launched from an unrelated working directory.
There was no `project/`, `web/`, `tools/`, or test checkout in that copy. A process
observation found only the native server child, not a Python or Node game server.

Embedded assets, registration, shutdown, restart, and the same colony were
verified. The all-IPv4 profile was exercised through the distinct loopback address
`127.0.0.2`; this is not a separate-device LAN or Internet-reachability test.
Unsafe parent traversal was rejected. A deliberately damaged private test store
was rejected without reset or overwrite. Temporary runtime descriptors were
removed after joined shutdown. The application artifact remained unchanged.

## Browser review and its important boundary

The [browser report](../evidence/browser/report.json) records Chromium
144.0.7559.96, desktop 1440 x 960, and mobile 390 x 844. Normal navigation to the
local server was attempted and rejected by the environment with
`ERR_BLOCKED_BY_ADMINISTRATOR`.

The explicitly selected fallback loaded the actual native-served client bytes
into a blank document, using a development-only bridge that forwarded requests
to the real native server. Module URLs were adapted for that document, and an
in-memory test storage adapter was declared. There was **no canned world, mock
reward system, or replacement game simulation**. The bridge is absent from the
production launcher and shipped game's execution path.

The tested controls performed actual registration, research, construction,
movement, second-identity entry, and same-key recovery on a mobile layout.
Untrusted colony names remained text. Extreme zoom remained finite; the mobile
layout had no horizontal overflow. The game request lane reached a maximum of
one simultaneous request. No client page exception was recorded. A response was
deliberately discarded after native command commit; retrying the stored same
intent did not double-execute it.

This review **does not verify ordinary browser navigation, CSP/CORS enforcement,
TLS, native persistent localStorage, clipboard permissions, or an external
reverse proxy**. Screenshots show this bridge-based review, not proof that those
boundaries passed:
[world](../evidence/browser/screenshots/world.png),
[research](../evidence/browser/screenshots/research.png), and
[mobile](../evidence/browser/screenshots/mobile.png).

## Retained failures and delivery status

`evidence/history/unpaged-diagnostics-failure.json` retains the earlier verification
request that exceeded the native output limit. The final diagnostic-page targets
fixed the test-output design; the limit was not raised. `evidence/browser-pilot/`
is an earlier, differently hashed candidate and is not final-artifact acceptance.
One derived-cache update failed during retired-owner admission; the accepted
revision remained valid and the later clean checks/builds above passed. These
observations are not hidden behind a relabelled successful historic report.

The revised GitHub workflow is source configuration only: it was **not executed
remotely for this final reconstruction**. Local tests above do not imply a green
remote CI run. The read-only [remote observation](../evidence/remote.json) still
found main at `9b3d8db72e2483bcf083aeb604d5366848417bf9`. A local commit or Git bundle
is not remote main integration. Follow the non-force handoff in
[operations](OPERATIONS.md) only after saving the complete bundle locally.
