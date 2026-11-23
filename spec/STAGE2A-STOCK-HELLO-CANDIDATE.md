# Unsigned stock Claude `hello.soul` candidate

The `stock-claude-v1` profile in `tools/stage2a_hello_package.py` builds only
the additive source proposed in
[soul-conformance PR #48](https://github.com/true-line/soul-conformance/pull/48).
It preserves the original fake-adapter profile and its signed-release hold.
This is an **unsigned, unqualified** artifact for an owner-reviewed Stage 2a
install plan. It is not physical host evidence or a protected launch rule.

The source is conformance commit
`068f5dd4d6f17691e66ea6cb3d126a0e40971f9a`, tree
`e6ea2ae8783b26fa2b0e36ee6348c137ce0aff1e`, under
`templates/stage2a-stock-hello.soul` (subtree
`cb56d82fb28965a6e26ef0ab70d475c38af2eb69`). The builder reads only
exact Git blobs from that commit and refuses any missing or extra path under
`Contents/`. The frozen inventory has these entries in sorted order:

| Entry | Kind | Mode |
| --- | --- | --- |
| `Contents` | Directory | `0555` |
| `Contents/SoulInfo.json` | Regular | `0444` |
| `Contents/SoulLock.json` | Regular | `0444` |
| `Contents/opt` | Directory | `0555` |
| `Contents/opt/stock-claude.json` | Regular | `0444` |
| `Contents/primitives` | Directory | `0555` |
| `Contents/primitives/qualification-task.json` | Regular | `0444` |

The canonical stream uses the USTAR byte profile and independent digest roles
defined in [the original frozen candidate](STAGE2A-FROZEN-HELLO-CANDIDATE.md).
The profile adds `candidate_profile: stock-claude-v1` to its public review
fields, and verification requires that profile explicitly. The source has no
Life, host state, executable, credential, or workspace seed in the frozen
archive. Machine must separately verify the installed stock ACP executable,
its adjacent CLI, the Souls runtime release and all host launch inputs.

Build and verify with the exact conformance commit available in the local
checkout. Use a fresh private directory and a new output path; the command
refuses an existing artifact or review-copy path.

```sh
python3 -B tools/stage2a_hello_package.py build CONFORMANCE_CHECKOUT OUTPUT.soul --profile stock-claude-v1 > review-fields.json
python3 -B tools/stage2a_hello_package.py verify OUTPUT.soul review-fields.json --profile stock-claude-v1 --stage-review-copy STAGED_COPY
```

At the pinned source and current builder, the unsigned stream is 7,168 bytes
with SHA-256 `7bdf79046dfcc6df4402d2f9b675a30ed0228036ecdb135c27c0064b5c4d4b23`.
The claimed revision is
`sha256:dbcd8ffca1accef3a0dd8227093e7cb77f99374de1c88b0b9164739d041cdb1a`;
the separate frozen definition measurement is
`sha256:ac02cde4a9d996d8702178d0feae1270401eeee087defd96ee830a280244bb3b`.
These values are reproducibility checks, not owner authorization. The actual
one-use plan must bind the complete inventory, installed paths and the exact
stock request and header digests obtained from those paths. The existing
signing workflow remains pinned to the original template and must not sign
this new profile without its own reviewed release gate.
