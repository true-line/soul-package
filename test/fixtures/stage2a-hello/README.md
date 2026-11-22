# Unsigned frozen hello candidate

`hello.soul` is a 10,240-byte deterministic USTAR transport fixture built by
`tools/stage2a_hello_package.py` (SHA-256
`d38931bb43ef9741868910d44f199f6ebc0733b85027a63fd0d2ed0fbdc2e96f`)
from `true-line/soul-conformance` commit
`8e82f47781e583e4b09352cbfef5ca3bfefe45aa`, tree
`5f3ab3acee16de02a38a51204fb9401c3566a6d0`, template subtree
`e944d40e5f495f6de395619b254ed890e36b53ee`.

The archive SHA-256 is
`91492287cced24a5f893fdad4516f23f4f4162df8f449a979f35ea8b70adfe47`.
`review-fields.json` is the builder's canonical output (SHA-256
`dde02c447dda8c83daa8889a549774d069d46b8f24161a25a4418151aec741d9`).
Two fresh builds matched these bytes. The test verifies the archive against
those review fields and refuses altered bytes and Soul identity.

This fixture has no owner approval, release signature, Machine installation,
or physical host evidence. Its digest can identify the candidate in a private
pilot plan; Machine must independently copy, freeze and measure the installed
source before a signed one-use reservation.
