# Orbloam reconstruction architecture

## A new economic model, not an old save conversion

The delivered program replaces the missing Stillworld application with a new accepted graph. It preserves the cooperative colony/industry direction but changes the simulation representation and rules. There is no claim that its output is byte-equivalent to a missing predecessor, or that timings form a valid before/after speedup ratio.

The authoritative simulation has one 10-second economic tick. Core motion has an authored start, destination and duration; the native simulation samples the integer trajectory at each tick. The browser interpolates that same movement for display. Cosmetic resident paths are not persistent individual navigation or carried-item state. Resource deposits occur under the tick rules, not on a client-reported arrival.

## Population without a per-person economic loop

A cohort is `(first, count, start)`. Seat `i` has stable role `(first + i) modulo 10`, and first birth at tick `start + i`. Its successive lives last exactly 360 ticks. Roles 0–7 gather the eight raw materials; 8–9 supply workshop labor. At a death boundary a life returns essence and the next generation occupies that seat immediately.

The accepted graph counts births, deaths and role occupancy with integer formulas. A test-only independent Python oracle enumerates every seat instead, including populations up to 4,096 and boundary ticks. These observations establish equality for the stated fixtures, not a proof for every future code change. The browser may enumerate visible seats to draw them; that does not move economic authority into JavaScript.

Normal population is initially 16 seats, 4 already born. Each of the 12 vitality ranks adds 48 seats. Multiple purchased cohorts can be filling simultaneously. The current normal maximum is 592 seats; 4,096-person values are explicitly operator/test fixtures, not an undocumented player unlock.

## Shared procedural resources

The terrain is generated from signed 128-unit grid coordinates using integer arithmetic. A cell owns one circular deposit, a material, position and tier. Distant tiers increase with coordinate magnitude. There are no natural seas, lakes, enemy agents or combat in this version.

At each tick and gathering role, the native graph searches the entire researched circular reach, checks tier eligibility and actual stock, and chooses the nearest available matching deposit. Its row scan skips columns that cannot match the role. An independent oracle visits every grid cell instead and compares the complete two-colony world.

A request-local scan never awards unavailable material. Demand is constrained by live role counts, harvesting research, deposit tier, shared availability and per-item storage capacity. Each role uses at most one selected deposit per tick. Core contribution adds a small baseline even when that role has no born worker. This is a deliberate new-version rule.

Only deposits whose stock changed need persistent entries; availability is derived exactly from the last stock and tick. Every 36 ticks, fully regrown entries may be removed because they equal procedural defaults. Depleted entries are never evicted to make room. At 4,096 tracked entries, existing entries continue; previously untracked deposits wait until an exactly redundant entry can be removed. This bound is disclosed rather than disguised as depletion-free infinity.

Colony processing order rotates each tick so a single fixed registration index does not always receive first access. The canonical stored colony order does not rotate. All colony effects use the same evolving shared deposit map.

## Industry and progression

The catalogue has 8 facilities, 9 recipes per facility and 8 research branches with 12 ranks each. Recipe dependency edges go from earlier-tier products to later-tier products; high-rank research consumes prior processing output. Research, product quantities, experience and currency are native game values.

Workshops receive available craft workers in construction order. They retain progress while waiting for input, output capacity or workers. A completed cycle debits all inputs and credits output together. Verification compares all 72 recipes against independent material-balance calculations, for successful completion, missing input and a full output warehouse.

Every sixth tick a workshop attempts maintenance. Nearby core, available labor and one timber plus one stone permit upkeep; otherwise condition falls by two points. Healthy upkeep restores one point up to 100. Stopped machines still need upkeep. At zero health production stops. Range applies to automatic operation and maintenance; owner commands for repair, settings and demolition are remote. Inputs and labor waiting are observable statuses, not silent production.

## Native ownership and persistence

One HTTP task at a time owns world mutations. A typed transaction reads auth/world state and commits a new world plus any changed authentication fact. Success is returned only from `TransactionOutcome.Committed`; conflicts do not expose an uncommitted candidate.

The native store is local, deployment-selected and transactional. The world is one typed value; authentication is separate digest-indexed data. This still encodes and persists the whole world when it changes. It is not a segmented world database, a lock-free parallel simulation, distributed ownership or replication. The persistent engine retains history; operator backup/restore is the available explicit compaction boundary.

The descriptor admits one active task, a finite queue, finite HTTP/stream/data limits and the unchanged resident instruction allowance. Failed admission is not fixed by silently inflating every runtime quota.

## Time and request work

`GET /api/view` is a read-only projection. `POST /api/sync` advances at most `max(1, floor(12 / colony_count))` ticks per call. If no request arrives, work is deferred. Long absence is retained as real backlog and is processed in chronological batches. A gameplay command waits until the world reaches the sampled server wall tick; there is no catch-up reward formula or simulation speed change.

The browser keeps one ordered game request in flight. Uncertain actions retain their exact payload and sequence. Foreground or background tabs are not extra game authorities. Hidden pages stop scheduling unnecessary work. The native service has no background worker in this release.

## Public authoring and accepted bytes

The unchanged v0.1.38 executable creates and validates a graph. `tools/build.py` generates public compact proposals, emits full review plans and applies their exact tokens. Five stages keep each impact summary within the public review bound. Prior accepted aliases are resolved only from real apply receipts; quoted asset bytes are not token-rewritten.

The first bulk diagnostics command exceeded the runtime's 65,536-byte compact-output record bound. A reviewed body replacement changed it into a guide to bounded diagnostic pages; a separate local command emits small pages. The failed pilot evidence is retained. No runtime format limit was bypassed.

`project/` retains the accepted graph, `authoring/` retains the actual proposal/review evidence, and `dist/` contains the tested artifact and operator descriptor. Fresh generator runs allocate fresh graph identities. Rebuilding the retained accepted graph is the reproducible artifact boundary.
