# Orbloam

**Little lives. A world of their own.**

A quiet, cooperative browser colony game. Guide a luminous core through a shared
world, let its residents gather and work, and grow a civilization through branching
discoveries. The interface stays out of the way until you choose something to inspect.

This is the **Quiet World update** to the September 2026 Orbloam reconstruction.
It is not a recovered copy of the lost Stillworld build.

## Start playing

The offline ZIP includes the game and its pinned runtime. On **Linux x86_64**,
extract the ZIP, open its `orbloam` directory, and run:

```sh
sh start.sh
```

Open **http://127.0.0.1:8080/** in your browser. Choose a colony name. Save your
private recovery key from the menu; a name alone cannot recover a colony. Keep a
server-side save backup as well: the key and the save are different things.

If your extraction tool removed executable permissions, run
`chmod +x runtime/lkjscript` first. The server is a Linux executable; the browser
may run on a different device. WSL2 is a possible Windows host but has not been
tested in this delivery. There is no native macOS/ARM server build in this package.

For a source-only checkout, acquire the pinned official runtime once, then launch:

```sh
sh tools/install-runtime.sh
sh start.sh
```

No application compilation is required. Running the game does **not** need Python,
Node.js, Cargo, an external database, a CDN, or an Internet connection after the
runtime has been acquired.

Stop with **Ctrl+C**. The default save directory is **`dist/data/`**. Existing saves
are never automatically erased, replaced, or reset when an error occurs.

```sh
# Share within a trusted network; connect using the server's LAN address.
sh start.sh --lan --port 8080
```

LAN mode binds all IPv4 interfaces and uses plaintext HTTP. Protect recovery keys
with a trusted network or a TLS reverse proxy. `0.0.0.0` is a listener setting,
not a browser destination. The launcher does not configure DNS, a firewall, or
router forwarding.

## What changed

**A quieter world.** The default HUD shows the colony, population, and Essence.
Inventory, workshops, neighbors, and object details appear only when opened.
Click empty ground to move your core; drag to pan. Selecting an object opens its
context, not a dashboard of every statistic. `H` hides the interface for observation.

**Faster generations.** Each resident lives **15 minutes**, exactly 90 ten-second
economic steps, instead of an hour. Each occupied seat then produces a new
generation and returns Essence. This shortens the wait for returns; it does not
multiply every reward or promise that all research finishes four times faster.
Research costs are unchanged.

**Real research forks.** The tree contains 96 discoveries across eight families,
with **32 branching points** and explicit prerequisites enforced by the server.
After a fork, either eligible child can be chosen first. Picking one does not
silently grant its sibling. Hover or select for details; Browse exposes every
node as an accessible button. Completed research in an immediate predecessor
Orbloam save stays owned.

**Less routine management.** Build nearby with one button, or choose an exact
placement. Workshops automatically select unlocked, feasible recipes according
to stock coverage. They finish their current batch before reconsidering. Fixed
recipes remain an explicit override; “Let residents choose” restores automation.
You still decide what to build, discover, and where to move. The game does not
spend resources on autonomous construction or research.

**Distance-aware rendering.** Close views show shaped deposits and residents;
landscape views use smaller marks; distant views aggregate all eight resource
kinds into regional summaries with tier contours. Regional stock reflects saved
depletion and regrowth. Adjacent LOD levels cross-fade rather than dropping
arbitrary deposits. Distant core markers remain visible without drawing every
individual. These are display changes, not reduced simulation populations.

**A more material core.** The orb has baked spherical lighting, a specular
highlight, colored rim light, internal filaments, and a ground shadow. Trees have
forked trunks and layered crowns. These are lightweight canvas graphics, not a
claim of a physically based 3D renderer.

## Controls and everyday play

| Action | Control |
| --- | --- |
| Move the core | Click empty ground, or right-click a destination |
| Pan / zoom | Drag / mouse wheel; touch drag and pinch are supported |
| Return to your core | Center button or `Home` |
| Research / build | Toolbar, `R` / `B` |
| Close a panel or placement | Close button or `Escape` |
| Hide / restore the HUD | `H`, or the restore button |

Residents gather automatically. Resources are shared with other colonies, so a
depleted deposit stays depleted until it regrows. Eight workshop kinds offer
72 recipes. Input shortages, full stores, workers, health, maintenance, and range
still matter. The automatic recipe policy is local, not a globally optimal
production planner. Normal Vitality research raises the population limit from
16 places to 592. The core's experience level is separate from discovery count.

When no one is connected, computation is deferred. Returning clients catch up
chronologically; long absences can delay actions. Time is not skipped and no
approximate offline reward replaces the simulation. A temporarily lost action
reply is reconciled automatically using the exact same sequence and intent.
Conflicts between devices still require review rather than blind resubmission.

## Updating an existing world

**Extract into a new directory. Do not overwrite a running installation.** Stop
the old server, make a native logical backup, and restore it into an absent save
root in the new directory. Keep the old program and pre-update backup for rollback.
The procedure is in [Operations](docs/OPERATIONS.md#updating-an-existing-orbloam-save).

The immediate predecessor Orbloam v1 save was tested with the same recovery key,
unchanged world admission, preserved research ranks, and new commands. The missing
Stillworld save format is not supported. Deferred time will use the new lifespan
rules when processed; already recorded history is not rewritten. Downgrading the
program alone does not undo changed gameplay semantics.

## Implementation and verification

One unchanged official **lkjscript v0.1.38** process serves the game, HTTP assets,
transactions, authentication, and persistence. `project/` is the accepted meaning
graph; `dist/application.lkja` is its built artifact. Python scripts author public
reviewed changes and run developer tests. Browser JavaScript displays the world
and requests actions; it never awards resources.

[Verification](docs/VERIFICATION.md) identifies the exact artifact, clean
rebuild, native action and recovery tests, independent population/production
oracles, predecessor-save admission, and rendering tests. The 512-resident stress
fixtures are seeded tests, not earned progression or proof of an unlimited MMO.

Chromium in the test environment blocked normal local navigation. The browser
review therefore used the real served code and native server through an explicitly
recorded test bridge. That review does **not** verify ordinary browser navigation,
CSP/CORS, TLS, native persistent browser storage, or a particular reverse proxy.
The bridge is not used when running the game.

See [Known limitations](docs/KNOWN-LIMITATIONS.md),
[Security](docs/SECURITY.md), and [Architecture](docs/ARCHITECTURE.md).
Historical reports retain their original hashes and language; they are not
relabelled as evidence for this update. This ZIP is not a claim that remote
GitHub `main` has been changed.

## Developer checks

From a checkout with the pinned runtime:

```sh
python3 tests/rebuild.py
python3 tests/acceptance.py
python3 tests/quiet_native.py
python3 tests/catalogue.py
node tests/presentation.mjs
python3 tests/standalone.py
```

The optional browser check requires Playwright and Chromium:
`python3 tests/quiet_browser.py`. Its explicit `--bridge-if-blocked` option records
the limitations above. `python3 tests/performance.py --seconds 120` runs the finite
native fixture. None of these commands should target a player's live save.

Continue development with public `change plan` / `change apply`, retaining actual
requests and review plans. Do not regenerate a fresh graph at startup, mutate
canonical pack bytes, or introduce an unreported helper backend.
