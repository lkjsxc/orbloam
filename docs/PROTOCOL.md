# HTTP and command protocol

All routes are exact relative paths beneath the application's origin/prefix. A proxy serving a prefix must preserve a trailing slash for the home URL and strip that prefix before forwarding. The app does not enable wildcard CORS. Requests with bodies use `Content-Type: application/json`; the body limit is 4,096 bytes. Duplicate keys, unknown fields, trailing content and incompatible typed shapes reject.

| Route | Method | Authority | Meaning |
|---|---|---|---|
| `/`, `/index.html` | GET | Public | Embedded client |
| `/styles.css`, `/api.js`, `/world.js`, `/research.js`, `/client.js` | GET | Public | Embedded static bytes |
| `/health` | GET | Public | Application/runtime identity |
| `/api/catalog` | GET | Public | Items, facilities, recipes and research |
| `/api/join` | POST | Body recovery key | Idempotent registration |
| `/api/view` | GET | Bearer recovery key | Read-only current state |
| `/api/sync` | POST | Bearer recovery key | Bounded chronological catch-up |
| `/api/action` | POST | Bearer recovery key | Validated sequenced command |

Unknown routes return the native empty 404. There is no HTTP fixture, operator, export, filesystem or developer-execution endpoint.

Registration body: `{"name":"Colony","token":"64 lowercase hexadecimal characters"}`. The client generates 32 cryptographically random bytes before its first registration request. The same key returns the same identity on repeated registration; changing the accompanying name on a retry does not rename the colony. A successful first response is 201; a recognized replay is 200. The response includes the key, so it must not be logged as public evidence. The server stores a BLAKE3 digest lookup rather than plaintext recovery keys.

Authenticated calls use `Authorization: Bearer KEY`. There are no login cookies. These are permanent recovery/bearer keys, not the predecessor's 24-hour sessions. No automatic expiration or revocation is implemented. Protect both transport and saved keys.

A state envelope has `me`, `now_ms`, `backlog_ticks`, and `world`. `world` has `version`, `tick`, `next_id`, `colonies`, and `nodes`. All integer simulation ticks correspond to 10,000 milliseconds. **The native JSON codec encodes maps as ordered `[key,value]` pairs**, not JSON objects. The UI has an explicit map decoding adapter. It rejects malformed/duplicate entries rather than pretending they are empty inventory.

Actions require all of the following fields:

```json
{"op":"move","sequence":1,"index":0,"value":0,"x":-200,"y":20,"text":""}
```

`sequence` is the owner's last accepted sequence plus one. Bounds are checked before operation dispatch. Coordinates are integers in `[-1000000,1000000]`. `index` is 0..1,000,000, `value` is 0..1,000,000,000, `sequence` is 1..1,000,000,000,000, and text/op have finite lengths. Fields unused by a command still participate in its exact intent digest.

| op | Parameters |
|---|---|
| `move` | `x`,`y`: core destination |
| `rename` | `text`: nonempty name, at most 32 characters |
| `research` | `index`: catalogue research ID 0..95, in branch order |
| `build` | `index`: facility kind 0..7; `value`: its recipe ID; `x`,`y`: placement |
| `recipe` | `index`: owned building ID; `value`: compatible unlocked recipe ID |
| `pause` | `index`: owned building ID; `value`: 0 paused, 1 enabled |
| `repair` | `index`: owned building ID |
| `dismantle` | `index`: owned building ID |
| `transfer` | `index`: other core ID; `value`: positive amount; `text`: inventory item key |

Accepted intents use a 64-slot receipt ring. A retained identical old sequence returns the current snapshot without applying its action again, even after later actions. Different content or an expired old receipt yields 409 `sequence_conflict`. A retry acknowledgement is not a promise to return the original response bytes; other accepted state may have changed.

409 `catchup_required` is not a successful action. Poll `/api/sync` and retry the *same* action. Other business failures are typed 400 errors without an accepted sequence increment. Transaction conflicts return 409. Network/5xx failures may follow publication; never fabricate a new sequence just to bypass an uncertain result. The browser retains the old intent and exposes an explicit retry and operator-confirmed discard.

## Local native commands

Command targets are artifact-local, never HTTP routes. `authoring-ready` returns true. `population-probe` takes count/tick. `diagnostic-page` takes one integer: 0 for population cases; 1 for the complete shared-world oracle fixture; 2..19 for four recipe cases per page. `diagnostics` explains this pagination.

`fixture-create` takes population 1..4,096 and age-in-ticks 0..8,640. It is explicitly a seeded test/operator fixture, has ample material/research and prints a secret recovery key. It refuses an existing world and must never be exposed as an HTTP handler. Tests create a fresh private store and temporary command descriptor, remove resident execution limits only for that local command, and retain the actual service's original limits.
