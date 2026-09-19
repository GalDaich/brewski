# Changelog

## 0.1.0

First public release of Brewski, a macOS Homebrew maintenance command.

- Upgrade formulae and casks, preview or remove unused dependencies, and clean up.
- Report missing dependencies, service status, diagnostics, fixable vulnerabilities,
  and remaining updates with per-step timings.
- Protect password input by checking terminal setup and restoring echo on signals.
- Preserve the sudo helper through self-upgrades with a private script snapshot.
- Coordinate concurrent runs independently of TMPDIR and clean up early failures.
- Stop ordinary child processes on interruption; retain runtime files if cancellation
  is incomplete.
- Distinguish successful runs from runs with advisory warnings.
- Respect Homebrew's no-quit setting and support `--version`.
- Include automated macOS regression tests, release archives, checksums, and MIT licensing.
