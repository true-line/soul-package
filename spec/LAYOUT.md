# Package layout

Source: Soul Agent Platform draft 0.3, Section 11; Native Shareable Soul Packages v0.3 (https://zenodo.org/records/23547566). Class decides what travels on transfer: Definition and Life travel; Reconstructible is rebuilt from declarations; Rebuilt, Recreated, and Dropped never travel.

| Path under Example.soul/Contents/ | Holds                                                                       | Class                             |
|-----------------------------------|-----------------------------------------------------------------------------|-----------------------------------|
| SoulInfo.json                     | Accepted definition declarations                                            | Definition                        |
| SoulLock.json                     | Resolved digests, target platforms, pinned models, adapter and renderer versions, rendered-output digests per adapter                           | Definition                        |
| primitives/                       | Accepted canonical primitives with optional per-adapter overrides under primitives/\<name\>/adapters/                                                 | Definition                        |
| opt/                              | Pinned runtimes, harness binaries, local models, optional offline artifacts | Reconstructible from declarations |
| memorial/knowledge/               | Durable assertions with sources                                             | Life                              |
| memorial/retrieval/               | Indexing recipe                                                             | Life                              |
| dreams/inputs/                    | Durable note inputs awaiting consolidation                                  | Life                              |
| dreams/runs/\<run-id\>/           | Candidate changes and evaluation evidence                                   | Life                              |
| comms/                            | Mirror of tasks and dedup watermarks, outbox drafts, handoffs               | Life (mirror)                     |
| home/\<member\>/                  | Each member's private working life, including harness-native state          | Life                              |
| workspaces/                       | Explicitly selected workspace data                                          | Life                              |
| cache/retrieval/                  | Rebuildable indexes                                                         | Rebuilt                           |
| host/                             | Sockets, PIDs, host bindings                                                | Recreated per host                |
| tmp/                              | Disposable scratch                                                          | Dropped                           |

Authoritative grants, spent nonces, key material, task revisions, deduplication records, and action records live in HQ's store, never in the package. `comms/` is a mirror; HQ's store wins on divergence.
