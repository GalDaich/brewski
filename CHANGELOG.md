# Changelog

## 0.1.2

- Require the password signal regression test to reach the prompt, deliver the
  signal, and verify its exact exit status; reject an early helper failure.
- Accept Homebrew-compatible Boolean values for safety policy settings while
  preserving cask-list and private password-helper safeguards.
- Respect effective no-quit configuration, explicit command-line precedence,
  and configuration changes after the metadata update.
- Clarify autoremove preview and document the configuration fixture's provenance.

## 0.1.1

- Stop before maintenance when Homebrew configuration overrides autoremove,
  cask upgrade scope, or the private password helper; check again after updating
  Homebrew metadata.
- Keep sudo password responses free of user Zsh startup output, including when
  the installed Brewski copy changes during upgrades.

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
