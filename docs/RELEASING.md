# Publishing Edivora source releases

Edivora's tracked source is public. **Standalone Windows executables and bundled binaries are NOT cleared for public redistribution**; see [PUBLIC_RELEASE_CHECKLIST.md](PUBLIC_RELEASE_CHECKLIST.md). Do not enable the legacy binary alpha publishing workflow.

## Version and release process

1. Complete review and merge into protected `main`. Change `[project].version` in `pyproject.toml` in the same reviewed change.
2. Start Actions → **Release verified source (no redistributable binaries)** → Run workflow on `main` and enter the matching tag. Python `0.4.0a1` maps to SemVer tag `v0.4.0-alpha.1`.
3. The workflow refuses non-main commits, existing tags/releases, mismatched versions, or failed source tests. Only Git-tracked source is archived and SHA-256 checks are attached.
4. Read and verify the created GitHub Release; no standalone installation package or PyPI artifact is published. A source archive is **not** a validated end-user binary.
5. Only after verifying all redistributed components, licenses, model rights and offline Windows acceptance may a **separate, reviewed** Windows packaging/release workflow be proposed. The source-release workflow must never start that binary flow.

The release tag is created by the same workflow **after tests**, because GitHub does not trigger a new tag-push workflow for tags created with its `GITHUB_TOKEN`. Restrict Git tag mutation using repository tag rules and enable release immutability in Settings when available.
