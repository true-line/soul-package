# soul-package

The `.soul` package format: manifest and digests, import validation, the `soul build` renderer and its plugin API, and life transfer and export. A library consumed on both sides of the trust boundary: HQ validates with it, the Soul runtime builds with it.

Source of record: Native Shareable Soul Packages v0.3 (Zenodo 10.5281/zenodo.23547566) and Soul Agent Platform draft 0.3, Sections 10 and 11 (`soul-contracts/papers/`).

## Owns

- `spec/` — layout, data classes, manifest rules, render-plugin interface.
- `src/manifest/` — SHA-256 manifest build and verification; definition-digest byte rules; dependency graph and cycle check.
- `src/validate/` — import validation: path traversal, absolute paths, symlink escapes, expansion limits, platform match, host requirements, cycles.
- `src/render/` — `soul build`: deterministic rendering through adapter plugins; rendered digests into `SoulLock.json`.
- `src/transfer/` — life selection, offline artifacts, template and fork derivation, transfer record assembly (no secrets, no reusable grants).
- `templates/` — package templates, including `hello.soul` once `soul-conformance` defines its task.

## Depends on

`soul-contracts` only. Render plugins live in `soul-adapters` and depend on this repository's interface, not the reverse.

## Never contains

Credentials, grants, nonces, task ledgers, receipts, runtime supervision, or a vendor name outside a plugin interface. Those belong to HQ (`managed-machine`), the runtime (`agent-bot-identity`), and `soul-adapters`.

## Work package

WP5 Memory and packages — portability implementer. Deliverables here: manifests, transfer selection, renderer, candidate tree staging support.
