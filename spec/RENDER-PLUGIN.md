# Render plugin API (stub)

Source: draft 0.3, Section 10 "Primitives and rendering".

`soul build` turns canonical primitives under `primitives/` into each adapter's native configuration. Each adapter ships a render plugin that implements this interface; `soul-adapters` hosts the plugins, this repository hosts the interface and the build.

- Input: the candidate or accepted tree (`primitives/`, `SoulInfo.json`, `SoulLock.json`), the adapter manifest, and the role assignment.
- Primitive classes: `skill`, `helper`, `tool-guidance`, `hook`, `role-routing`. A plugin declares which classes it renders and into what (instructions-file section, configuration file, hook registrations, MCP server entry).
- Per-adapter overrides at `primitives/<name>/adapters/<adapter-id>/` take precedence over the canonical form for that adapter only.
- Output: rendered artifacts under the member's configuration root plus a rendered-output digest, recorded per adapter in `SoulLock.json` with the adapter and renderer versions.
- Determinism: the same inputs produce the same bytes; a plugin that cannot render a required class fails with `render_failed` and names the class.
- A class the adapter cannot render fails that adapter's evaluation cell unless the primitive is marked optional for it.
