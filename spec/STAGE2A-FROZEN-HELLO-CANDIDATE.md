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

The proposed frozen Soul receipt is a DSSE-signed in-toto Statement/v1 with
one subject named `sha256-<artifact-sha256>.soul` and one bare SHA-256.
The candidate predicate type is
`https://true-line.ai/soul-contracts/package/v1/frozen-soul-build`. The
predicate has these exact fields.

| Field | Binding |
| --- | --- |
| `artifact_format` | `stage2a-frozen-hello-ustar/v1`. |
| `builder` | `repository`, `source_commit`, `source_tree`, `workflow`, `run_id`, `run_attempt` and `builder_sha256`. `builder_sha256` hashes the canonical map of builder script and workflow paths to their bare exact-file SHA-256 digests. |
| `toolchain_sha256` | SHA-256 of the canonical build toolchain report covering the Git and Python version and executable digests and the `tarfile` module digest. |
| `template` | `repository`, `source_commit`, `source_tree`, `path` and `template_tree`. The template pin is independent of the builder repository identity in the signing certificate. |
| `definition_measurement` | The prefixed SHA-256 of the exact measured frozen records. |

The ASCII-only Statement is emitted in RFC 8785 canonical form with no
trailing newline. Owner approval, the claimed revision and independent
measurements still travel through the reviewed plan. The Statement omits
the Soul ID, installed-plan identification, inventory, workspace state,
transport locations and owner approval. The existing adapter/v2
`souls-build` predicate and `.tgz` receipt remain the runtime provenance
authority. This build receipt conveys provenance only.

### Private build rehearsal and held signing

The candidate `.github/workflows/stage2a-frozen-soul-receipt.yml` runs only
on manual dispatch against protected main. Its `prepare` job checks the exact
builder commit, tree and source bytes against the checkout and the exact
conformance commit and trees. It builds and verifies twice and compares each
output inside a private runner directory. Its private runner outputs are
deleted when the job exits. The build stores the Statement and diagnostic
inputs alongside the exact archive, without storing private bytes in logs.

A separate `release_gate` job and the `sign` job both require the repository
variable `STAGE2A_FROZEN_SOUL_SIGNING_ENABLED` to equal the exact string
`true`. The variable is unset by default, so both jobs are skipped. Even if
the variable is explicitly enabled later, `release_gate` unconditionally
refuses before the `qualification-release` environment and OIDC-capable
`sign` job can start.
The staged signing job repeats the exact build on the same protected source
and controlled template. It requires owner-selected SHA-256 pins for the
Cosign v3.1.4 executable, signing configuration and trusted-root bytes;
the configuration and root arrive only as private environment-scoped inputs.
The job checks those pins before requesting a keyless signature, then compares
the signed bundle to the exact Statement and artifact and verifies it offline
with the selected log ID, pinned root, workflow certificate identity and OIDC issuer. Its
post-verification stop also refuses release while private write-once handoff,
read-back and the owner-signed v3 policy check are unavailable. The pre-sign
hold must remain until those missing steps and owner selections are reviewed;
removing it alone would create a public log entry and discard private outputs.
No signing or artifact upload runs in the current candidate.

The staged job writes a private `producer-handoff.json` sidecar after offline
verification. It records exact SHA-256 and byte length for the frozen `.soul`,
Statement, bundle and offline verifier output, plus source commit/tree,
workflow identity, certificate identity, OIDC issuer, selected log ID and
signing-material digests. These are producer claims for the release operator's
ledger; the owner-pinned Machine verifier must recheck the actual files. The
independent private release manifest must record the sidecar's own digest and
positive byte length, avoiding a self-reference in the sidecar. No
private object naming, scoped credential, write-once upload or independent
read-back is selected yet, so the sidecar and files are deleted with the
runner directory under the current hold. The existing runtime `.tgz` and
adapter archive keep separate roles and digests.

For the proposed Cosign v3.1.4 `--statement` path, the input to the signature
is the exact local Statement. Cosign does not itself recompute the artifact
digest in this mode; the bundle checker and offline verifier must bind the
Statement's subject to the actual `.soul` bytes.
[Pinned Cosign source](https://github.com/sigstore/cosign/blob/v3.1.4/cmd/cosign/cli/attest/attest_blob.go).

```sh
cosign attest-blob --yes --new-bundle-format --rekor-entry-type dsse \
  --signing-config "$reviewed_signing_config" \
  --trusted-root "$reviewed_trusted_root" \
  --statement "$private_dir/statement.json" \
  --bundle "$private_dir/frozen-soul-build-receipt.bundle.json" "$artifact"
```

### Exact public-good signing material proposed for owner review

The following is a **candidate selection, not approval to submit to a public
log or release a package**. It uses the published Sigstore
[root-signing target set at commit `6f637ea189df60b5ea9ed5f454b4623bd3a7b3aa`](https://github.com/sigstore/root-signing/tree/6f637ea189df60b5ea9ed5f454b4623bd3a7b3aa/targets),
with the legacy Rekor v1 `dsse/0.0.1` entry selected by the held workflow.
The target files' byte lengths and SHA-256 values agree with that commit's
signed `targets.json` metadata. This source review did not independently
verify the TUF metadata signatures; the release operator must obtain and
verify the approved exact files before setting the environment inputs.

| Input | Exact review value |
| --- | --- |
| `trusted_root.json` | 6,787 bytes; SHA-256 `6494e21ea73fa7ee769f85f57d5a3e6a08725eae1e38c755fc3517c9e6bc0b66` |
| `signing_config.v0.2.json` | 1,034 bytes; SHA-256 `9711a6d5375706957a4859af31c5866a4474f81f0544f9f4b76c9c4f4c8a539c` |
| Fulcio | `https://fulcio.sigstore.dev`, API v1, as recorded in that signing config |
| Rekor | `https://rekor.sigstore.dev`, API v1, `dsse/0.0.1` |
| Rekor log ID | `c0d23d6ad406973f9559f3ba2d1ca01f84147d8ffc5b8445c224f98b9591801d` (32 decoded bytes in the trusted root) |
| Timestamp authority | `https://timestamp.sigstore.dev/api/v1/timestamp`, API v1, as recorded in that signing config |
| Cosign | v3.1.4 Linux amd64 [release asset](https://github.com/sigstore/cosign/releases/tag/v3.1.4), SHA-256 `424e2c97d0b45fd7a6b608a87f090f35633f4c23ece5f092d48bba11aaf4bbfa` |

The approved files would become `FROZEN_SOUL_TRUSTED_ROOT_B64` and
`FROZEN_SOUL_SIGNING_CONFIG_B64` in the protected GitHub environment; their
listed digests, the Cosign executable digest, and log ID would become its
matching nonsecret variables. The owner must review the exact files and
public disclosure before these values are used. The public log may disclose
the repository and workflow certificate identity, source commit, signature,
time and digest commitments. The `.soul` archive, Statement, bundle and host
evidence require a separately selected private release handoff.

This command is a held review proposal for `dsse/0.0.1`. For the selected pinned configuration,
the owner approves the actual Fulcio, Rekor and timestamp inputs and log body
disclosure before any submission. Public logs can disclose the certificate
identity, build provenance extensions, signatures, timestamps and digest
commitments. The exact package, Statement, bundle, approval and host
evidence remain private. A signed entry timestamp can provide authenticated
signing time for the applicable Rekor v1 configuration. Rekor v2 requires
a separately verified RFC 3161 timestamp for this keyless signing path.
The candidate does not choose a production log type, version or key.
[Sigstore signer implementation](https://github.com/sigstore/sigstore-go/blob/v1.3.0/pkg/sign/signer.go).

After an approved build signs, `check-bundle` compares a Sigstore v0.3
bundle's top-level `dsseEnvelope` exact payload with the prepared Statement,
and compares the Statement subject and definition measurement with the
verified archive and review fields. The checker requires an explicitly
selected log kind and version, one signature, leaf certificate, inclusion
checkpoint and signing-time material. Its result is labeled
`shape-checked-only`. It validates byte bindings and shape while Machine
must authenticate the receipt independently.
[Sigstore bundle wire format](https://docs.sigstore.dev/about/bundle/#dsse-bundle).

```sh
python3 tools/stage2a_hello_receipt.py check-bundle \
  "$artifact" "$private_dir/review-fields.json" "$private_dir/statement.json" \
  "$private_dir/frozen-soul-build-receipt.bundle.json" \
  --log-kind "$reviewed_log_kind" --log-version "$reviewed_log_version" \
  --log-id "$reviewed_log_id"
```

Machine verifies the exact receipt bundle locally under owner-signed
policy. Require the reviewed trust-root digest, certificate workflow
identity, OIDC issuer and source repo/commit, protected source and authorized
builder/toolchain and template pins, exact approved log ID/type/version,
Fulcio chain and signature, authenticated signing time, and signed Rekor
inclusion proof/checkpoint anchored in that root. Match the actual archive
digest, exact Statement provenance and receipt byte digest to the separately
approved candidate and enforce policy expiry, revocation and the Stage 2a
one-hour revocation freshness rule. The bundle supplies no trust root.

The operator can provide the exact local files directly. The separate private
R2 handoff proposal reserves five versioned roles:
`frozen-soul-archive-v1`, `frozen-soul-statement-v1`,
`frozen-soul-build-bundle-v1`, `frozen-soul-verification-log-v1`, and
`frozen-soul-producer-handoff-v1`. Each would use a create-once
`v1/<role>/<lowercase-sha256>` key in the locked private bucket and a
`qualification://stage2a/<role>/<lowercase-sha256>` locator. The first four
carry their own exact SHA-256 and positive byte length in the private sidecar;
the independent release manifest would record the sidecar's digest and size.
The sidecar would be uploaded last, followed by full-byte read-back through
a distinct reader and offline verification of the downloaded bundle and
`.soul`. This route still needs a reviewed private-fetcher contract, separate
soul-package scoped credentials, current lock evidence and owner approval;
the held workflow does not upload any of these files. It does not alter the
published six-input qualification index or reuse the `souls-package` runtime
`.tgz` role and its bundle. The builder names the archive
`sha256-<artifact-sha256>.soul`; the held signer uses a private temporary
bundle path until handoff is defined. HQ and Machine use already delivered
local inputs for installation, launch and verification, independent of R2,
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
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s test -p 'stage2a_*_test.py' -v
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
