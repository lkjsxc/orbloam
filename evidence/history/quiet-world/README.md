# Earlier test failures, not final acceptance

`standalone-inherited-sigint.json` records a launcher shutdown timeout. That verifier
was itself started asynchronously by a non-job-control shell and inherited ignored
SIGINT; the next shell inherited that state. The test now restores default INT/TERM
in its private child before modelling a foreground invocation, and terminates its
owned session on timeout rather than leaving an orphan. The final standalone run
passes Ctrl+C forwarding, joined shutdown, restart, and corruption refusal.

`earlier-browser-test-failure.png` belongs to the earlier client test, not the final
rendering evidence. The verifier initially inspected a cleared recovery-key field
synchronously after closing its dialog. It now waits for the browser's actual
asynchronous close event. The final report separately checks the field is cleared.

Final results and their artifact hashes are in `evidence/standalone.json` and
`evidence/quiet-world/browser/report.json`, not this directory.
