# Runtime provenance

Orbloam is built and tested with the unchanged official **lkjscript v0.1.38**, public target `x86_64-unknown-linux-musl`. The ZIP predecessor used a different supplied GNU-libc binary; its provenance/performance claims are not transferred here.

Exact acquisition:

```text
https://github.com/lkjsxc/lkjscript/releases/download/v0.1.38/lkjscript-x86_64-unknown-linux-musl.tar.gz
archive SHA-256: fa10e7afb09c06e4a243f421050a0497ca9acd331cdf34c046650c85aef377aa
executable SHA-256: 98a39bd192c1e98187a1a954f916f5ffc89ef2586317c25e1efa06c61b888c32
published source: 7083f9a6d56ed702017942e100c3696fc6f35308
capabilities: 53e66b5dae2b5c8c08b20ca7272b9e15d36564ae521f2d9af39d15f4b66a17d5
```

The runtime was first downloaded and archive-verified on the previous reconstruction branch's GitHub Actions runner, then recovered from that runner's artifact into this continuation. The same pinned archive and executable hashes were checked locally. `tools/install-runtime.sh` supports that exact local archive for offline installation, or acquisition from the exact release URL; it does not follow a mutable latest tag.

`runtime/RELEASE-MANIFEST.json`, `runtime/LICENSE`, and `runtime/THIRD-PARTY-LICENSES.html` are carried through from the verified official package in the offline playable distribution. Source-only Git history excludes downloaded runtime bytes; the installer preserves an existing installation rather than silently replacing it. No fonts are bundled.

The launcher verifies the exact executable as well as the local application manifest. Checksums bind selected bytes; they are not an independent publisher-signature authority. Trust in the original GitHub HTTPS acquisition and pinned hash must be distinguished from application acceptance.

The checked artifact identity and accepted graph revision appear in `dist/BUILD.json` and the verification records. A runtime version switch does not migrate application data or convert a graph to a predecessor generation. Keep the matching old executable, artifact and data for rollback. Linux x86_64 was exercised; native Windows/macOS/ARM support is not claimed.
