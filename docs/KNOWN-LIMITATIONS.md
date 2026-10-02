# Known limitations — reconstructed Orbloam

## Reconstructed rules, not a missing binary restored

The newest predecessor ZIP/save bytes were unavailable. The original Orbloam reconstruction introduced its own accepted program and save schema; it did not recover those exact Stillworld bytes. The Quiet World update retains that Orbloam schema. It retains the intended cooperative colony/industry direction but uses 10-second economic ticks, cohort life schedules and cosmetic resident travel. It does not reproduce an individual resident's previous pathfinding/carrying state. The missing Stillworld save remains unsupported. The immediately preceding Orbloam v1 typed save is tested separately for unchanged admission in this update. Keep old programs and saves intact.

The current 15-minute lifespan means 90 simulation ticks per life. A new generation immediately replaces each dead seat, and multiple purchased cohorts may fill concurrently. This differs from an individual-agent simulation with independent spatial journeys and potentially delayed replacement births. The UI does not award goods for a drawn arrival.

## Finite local capacity

The HTTP descriptor has one active authoritative task, a queue of 64 and a 30-second request deadline. Performance evidence is for the stated CPU/quota and fixture only. Registration admits at most 64 cores; this does not prove that 64 busy large colonies sustain real time. Normal research permits 592 seats per colony. Larger fixture values are tests, not normal gameplay claims.

The world is still one typed persisted value, with a configured 1 MiB per-value limit. Its size depends on colonies, workshops, cohorts, maps and retained command receipts. Large combinations of individually allowed counts may exhaust that value/adapter/codec limit before the registration count does. This combination has not been certified. A runtime rejection is not permission to reset the world or raise all limits without measurement. World partitioning and size-aware admission remain future engineering work.

At most 4,096 depleted/non-default resource entries are retained. Exactly fully-regrown entries can be pruned every 36 ticks. When the map is full, never-before-tracked deposits are temporarily unavailable; existing depleted deposits are not discarded. The procedural coordinate range is finite: core orders stay within ±1,000,000 on each axis. The browser combines every resource kind into exact regional totals at distant zoom; it does not display every deposit or resident individually. Resident visual thinning and core clustering affect presentation only.

## Request-driven time and disk growth

When nobody is polling, calculation is deferred. Catch-up processes a bounded number of exact ticks per request and can take time after a long absence. There is no background tick worker, automatic offline approximation, parallel game writer, distributed scheduler or multi-server replication. An action can wait for catch-up and must retain its exact intent across uncertain communication.

The local store retains immutable physical history. Whole-world commits and live authentication/receipt data cause disk use. There is no automatic online compaction. A verified native logical backup/restore into a new absent root is an explicit operator procedure, not a deletion of current game facts or a schema conversion. The launcher does not silently remove old data.

## Account and deployment scope

Recovery keys are permanent bearer credentials, not 24-hour sessions. They have no UI revocation, expiration, email reset or comprehensive public abuse protection. The browser stores a key only according to the visible remember option; that storage is not an encrypted vault. Server-side digest lookup does not encrypt the login transport or protect a compromised client.

Plain HTTP is loopback by default. `--lan` exposes all IPv4 interfaces and needs a trusted network or protected proxy. Relative URLs accommodate host/port changes and properly stripped path prefixes, not arbitrary cross-origin requests or `file://` play. There is no inbound TLS or public-service availability guarantee.

## Verification boundaries

Native acceptance establishes the specifically recorded command, HTTP, conservation, shared-world, restart, backup/restore, copied-package and corruption-refusal observations. A seeded 512-person fixture is not earned progression, an indefinite soak test, or many-player acceptance. Timings exclude human playability judgments and do not establish the old engine's speedup.

Chromium denied normal navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`. The recorded fallback executed actual served client bytes in a blank document and forwarded only that server's HTTP calls. It used an explicitly declared test storage adapter. This validates those UI actions against the real native game, but not normal navigation, CSP/CORS enforcement, browser-native persistent storage, TLS, clipboard or a particular reverse proxy. The bridge is not a production backend and is never used by `start.sh`.

The first oversized diagnostic result failed the native 65,536-byte compact output-record bound. The current local diagnostic-page command divides results into bounded pages. The unpaged failure is retained in `evidence/history/`, not relabelled as a passing final test. An earlier incremental compiler cache update reported `compilation_incremental_owner_domain`; the accepted revision remained valid and a subsequent public clean check/build succeeded. No canonical pack was edited to bypass this.

## Delivery scope

This update is delivered as a ZIP containing the accepted graph, matching artifact, source, runtime, and licenses. Packaging is not evidence that GitHub main was updated. Preserve concurrent repository work during any later integration; do not force-push an older local history.

## Automatic recipes and research balance

Automatic production is a local stock-coverage policy, not a globally optimal planner. Construction order still allocates workers, and recipes can wait for inputs, storage, health or range. It does not build facilities, buy research, or move the core without your input. Independent forks preserve each discovery's original costs and identifiers. Choosing a higher-numbered sibling can require more resources than its neighbor. Fifteen-minute lives accelerate return opportunities; research prices were not silently discounted and the update has not been play-tested through all 96 discoveries.
