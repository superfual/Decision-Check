---
name: decision-check-deweb
description: Package or review Decision Check public releases for TapeKit on X Layer, including manifests, viewer compatibility, and artifact verification.
---

Read the distribution section of [the Hybrid architecture](../../../docs/HYBRID_DEWEB.vi.md) and verify the target viewer against the linked TAP-10 draft and previewer.

Build a deterministic manifest from a pinned revision and a public asset allowlist. Compare its bytes with the candidate readback. Keep portfolio files, local database contents and private commitments out of the manifest. Check relative paths, EN/VI/ZH, viewer sandbox behavior and any CDN, WASM, worker or storage dependencies on each page in scope. Keep an HTTPS entry point for flows that rely on unavailable viewer capabilities.

Record the build revision, manifest, viewer version, network, container identity, read block and applicable upgrade assumptions. Use read-only checks for review. Treat a paid release or container update as a separate deployment action.
