# Changelog — Project Kandang

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses a practical versioning scheme for its development milestones.

## [Unreleased]

### Added
- Initial project documentation structure with `README.md` and `PROJECT_CONTEXT.md`.

### Notes
- This entry records the establishment of the documentation baseline on 2026-11-07.
- It does not represent the original creation date or release date of the application.
- Historical application changes have not yet been reconstructed from Git history.

---

## Changelog Guidelines

Use the following categories when recording changes:

- **Added** — new features, modules, endpoints, or capabilities.
- **Changed** — changes to existing behavior, configuration, or implementation.
- **Deprecated** — features that are planned for removal.
- **Removed** — features, modules, or behavior that have been removed.
- **Fixed** — bug fixes.
- **Security** — security-related improvements or fixes.

### Entry Rules

1. Record meaningful changes, not every minor code edit.
2. Describe the user-visible or system-level impact.
3. Mention affected modules or interfaces when useful.
4. Do not include passwords, API keys, tokens, connection strings, or other secrets.
5. Do not claim a change is deployed until it has been verified on the target system.
6. Keep unreleased changes under `[Unreleased]`.
7. When creating a release, move the relevant entries into a dated version section.

### Example

```markdown
## [Unreleased]

### Added
- Added a health-check endpoint for the application.

### Changed
- Reduced the interval of a non-critical background task.

### Fixed
- Fixed handling of a device timeout.
```
