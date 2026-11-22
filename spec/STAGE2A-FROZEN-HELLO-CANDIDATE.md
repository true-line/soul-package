# Frozen `hello.soul` transport candidate

This proposal carries the exact controlled Stage 2a definition supported by
[PDR-0102](https://github.com/true-line/agent-bot-platform/blob/e9ea3b805e2babe44d7a693f45277362c353321a/docs/04-decisions/PDR-0102-protected-adapter-qualification.md)
and the [measurement contract](https://github.com/true-line/soul-contracts/blob/6f4392b5e0c42d68d2c6a216dd25b6f6edfde5bd/schemas/machine/v1/stage2a-measurement.md).
The candidate builder intentionally recognizes one template revision. General
Soul transfer continues to use the layout in [LAYOUT.md](LAYOUT.md).

## Canonical file bytes

The proposed delivery is one uncompressed POSIX USTAR stream named
`sha256-<lowercase-hex-sha256>.soul`, where the digest covers the entire
delivered stream, including headers, padding and end markers. The archive
root represents the frozen snapshot. Entries appear in this exact order.

| Entry | Kind | Mode |
| --- | --- | --- |
| `Contents` | Directory | `0555` |
| `Contents/SoulInfo.json` | Regular | `0444` |
| `Contents/SoulLock.json` | Regular | `0444` |
| `Contents/opt` | Directory | `0555` |
| `Contents/opt/quickstart-adapter.mjs` | Regular | `0444` |
| `Contents/opt/quickstart-check.mjs` | Regular | `0444` |
| `Contents/primitives` | Directory | `0555` |
| `Contents/primitives/quickstart-task.json` | Regular | `0444` |

The Git source is `true-line/soul-conformance` commit
`8e82f47781e583e4b09352cbfef5ca3bfefe45aa`, tree
`5f3ab3acee16de02a38a51204fb9401c3566a6d0`, under
`templates/hello.soul` (subtree `e944d40e5f495f6de395619b254ed890e36b53ee`).
The builder uses exact Git blob bytes and removes write bits from source
modes. It uses `0444` for regular non-executables and `0555` for regular
executables. Node loads both measured `opt/` scripts as regular files.
Source conversion carries no Git-worktree timestamps or ownership.

Each header is 512 bytes, using USTAR magic `ustar\0`, version `00`,
ASCII paths confined to the 100-byte name field, and an empty prefix.
Directory names append one slash and use typeflag `5`. Regular files use
typeflag `0`. The header has zero uid, gid and mtime, empty uname, gname
and linkname, and empty device fields. Ordinary numeric fields are
zero-padded ASCII octal terminated by NUL. The checksum is six octal digits,
NUL and space. It sums all header bytes with the eight checksum bytes
temporarily set to spaces. Unused bytes are NUL. File data follows its
header, with NUL padding to the next 512-byte boundary. Two final all-NUL
blocks end the stream. The verifier requires byte-identical headers and
padding and exact EOF. PAX, GNU extensions, compression, alternate encodings,
links and other file kinds cannot enter this candidate.

The two mutable seeds `issue.md` and `answer.txt` travel separately
as reviewed conformance inputs and are placed in the runner-owned
scratch workspace. Writable Life and recreated host state never contribute
code, policy or configuration to this closure. The host projection and
selected runtime inputs use the separate launch-input measurement from the
platform contract.

## Byte verification and admission

Keep these independent digests through build, install and evidence.

| Value | Bytes measured |
| --- | --- |
| Adapter package SHA-256 | Exact installed adapter archive. Existing `adapter.package_sha256`. |
| Souls runtime SHA-256 | Delivered `agent-bot-souls` npm `.tgz`. Existing `souls_build.package_sha256` and v2 runtime build receipt. |
| Frozen Soul artifact SHA-256 | Exact delivered `.soul` USTAR. Candidate new bare-hex `soul_artifact_sha256` field at the Machine wire boundary. |
| Definition measurement | Domain-separated SHA-256 of the JCS frozen definition records, from the exact decoded file bytes, paths and modes, and independently remeasured on the installed snapshot. |
| Claimed definition digest | Exact string in `SoulLock.json.definition_digest`, an input to the owner-approved mapping. |
| Launch-input measurement | Domain-separated SHA-256 of the distinct measured host projection, runtime files and effective invocation. |

The reviewed one-use plan binds the separately authenticated frozen Soul
artifact digest and the exact tuple `(soul_id, claimed_definition_digest,
definition_measurement)`, plus the complete ordered inventory. The verifier
compares `SoulInfo.json` and `SoulLock.json` fields with that mapping after
verifying their raw bytes. The local fixture's review-fields JSON only
records build output. An operator must separately authenticate the plan and
compare the returned fields with it. Copying generated fields into a plan
does not convey authorization.

Machine installs from locally available, independently verified archive and
receipt bytes, stages the decoded files under the Machine custody rule, and
remeasures the opened, sealed contents and host projection before launch.
Preserve the authenticated original digest after extraction. Carry the new
typed digest through the per-start pre-Hello reservation, post-Hello
finalization, immutable completed-run record and signed host report. HQ
compares the exact mapping with authenticated Hello before admitting IDs.
Approval and separate durable start reservations still come from the
existing qualification procedure.

The currently generic `measurement_binding.package_sha256` requires an
explicit migration. Draft Machine #654's v3 report compares it to the
adapter SHA-256, while the Souls start assignment sources its
`PackageSHA256` from the installed runner. A reviewed contract revision
must compare all three typed fields to their independent sources. The
`.soul` proposal cannot reinterpret either existing digest or use the
portable definition measurement as its archive SHA-256.

## Receipt and optional transport

The proposed frozen Soul receipt is an in-toto Statement/v1 with one subject
named `sha256-<artifact-sha256>.soul` and one bare SHA-256. Use a new
dedicated predicate and versioned verifier. The subject and typed predicate
bind the exact artifact, source template repo/commit/tree and path, exact
builder/workflow repo/commit/tree, toolchain digest, workflow, run ID and
attempt, and definition measurement. The existing adapter/v2 `souls-build`
predicate and `.tgz` receipt remain the runtime provenance authority.
This build receipt does not authorize a launch or replace host evidence.

Machine verifies the exact receipt bundle locally under owner-signed policy
with the reviewed trust-root file digest, workflow certificate identity,
OIDC issuer, protected source and authorized builder/toolchain and template
pins. Require the expected DSSE/in-toto format, Fulcio chain, authenticated
signing-time evidence and signed Rekor inclusion/checkpoint anchored in that
root. Enforce policy expiry, revocation and the Stage 2a one-hour revocation
freshness rule. Review the precise log entry type and body for the pinned
signing tool before public submission. Public Rekor may expose signing
certificate identity, timestamps and hash commitments. The package, signed
Statement/bundle and approval and host evidence remain private. The workflow
must exclude paths, data and identifiers that the approved signing and log
services may not receive.

The operator can provide those exact local files directly. If using private
R2 for handoff, add distinct proposed roles `frozen-soul-artifact` and
`frozen-soul-build-bundle` to a versioned manifest. They carry the exact
`.soul` and its detached bundle, each with its own digest. Preserve the
existing `souls-package` / `souls-package.tgz` and runtime bundle roles.
The adapter #29 six-role index and its exact-set verifier need a coordinated
versioned update to carry the two new roles when the release uses R2. The
private transport lane must verify write-once/read-back and lock evidence
under its reviewed rules. HQ and Machine use already delivered local
inputs for installation, launch and verification, independent of R2,
Harbor and internet availability at runtime.

## Local reproduction

Run from the `soul-package` checkout with Python 3.9 or later, Git, and a
local `soul-conformance` checkout containing the pinned source commit.
Create the output in a private writable directory.

```sh
python3 tools/stage2a_hello_package.py build /path/to/soul-conformance hello.soul > review-fields.json
python3 tools/stage2a_hello_package.py build /path/to/soul-conformance repeat.soul > repeat-fields.json
cmp hello.soul repeat.soul
cmp review-fields.json repeat-fields.json
python3 tools/stage2a_hello_package.py verify hello.soul review-fields.json --stage-review-copy readback.soul
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s test -p 'stage2a_hello_package_test.py' -v
```

The current candidate is 10,240 bytes. Its archive SHA-256 is
`91492287cced24a5f893fdad4516f23f4f4162df8f449a979f35ea8b70adfe47`.
Its definition measurement is
`sha256:68651e0685e0267f343e8b500d4af764a882c4ee56f0d1b4d2c775538317a621`.
The local copy is a staging/read-back exercise without Machine root custody,
privileged snapshot publication, signing or a physical test.

The decisions pending review are the USTAR transport version and exact
recipe, the three-digest schema migration and predicate, signer/workflow and
trust-root pins, and the public Rekor disclosure for the exact tool and
receipt. The private handoff and production signing holds apply until those
decisions and a real signed artifact verify. The physical qualification
hold depends separately on the approved installation, completed T01–T03
and T21 results, and authenticated evidence.
