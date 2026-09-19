# 🍻 Brewski

A Zsh command-line tool for updating, cleaning, and checking a Homebrew installation on macOS. Run one command to upgrade packages, clean up, and get a timed summary of what passed, warned, or failed.

[![CI](https://github.com/GalDaich/brewski/actions/workflows/ci.yml/badge.svg)](https://github.com/GalDaich/brewski/actions/workflows/ci.yml)

**Current version:** `0.1.0`. See [releases](https://github.com/GalDaich/brewski/releases) for source archives and SHA-256 checksums.

## What it does

A normal run:

1. Updates Homebrew metadata and reports available upgrades and pinned packages.
2. Upgrades formulae and versioned casks, including casks marked `auto_updates`.
3. Previews unused dependencies and performs normal Homebrew cleanup.
4. Cleans up unused service registrations and reports service status.
5. Checks missing dependencies, runs `brew doctor`, scans for vulnerabilities with available fixes, and reports remaining updates.

**Running Brewski changes your Homebrew installation.** Upgrade plans are approved automatically, and Homebrew may quit running cask applications. Use `--no-quit` to prevent that. Unused dependencies are only removed when you pass `--autoremove`; aggressive cache pruning is not requested.

## Requirements

- macOS with `/bin/zsh` and the standard system command-line utilities.
- [Homebrew](https://brew.sh/) available as `brew` on your `PATH`.
- Git only if you choose to install from a source checkout.

The development environment used Homebrew 7.0.4. Older Homebrew versions have not been validated and may lack flags or commands used by Brewski, including `brew vulns`. Python 3 is needed only to run the regression tests.

## Install with Homebrew

```sh
brew install GalDaich/tap/brewski
brewski --version
brewski --help
```

The formula lives in [GalDaich/homebrew-tap](https://github.com/GalDaich/homebrew-tap).
If you already have a manually installed `brewski`, back it up and remove it from
your PATH before switching; `command -v brewski` shows which copy will run.

## Run from source

Clone the repository and inspect the available options:

```sh
git clone https://github.com/GalDaich/brewski.git
cd brewski
./bin/brewski --help
./bin/brewski --version
```

Start a maintenance run when you are ready:

```sh
./bin/brewski
```

Run as your normal user, not with `sudo`. If a cask installer needs administrator authentication, Brewski prompts through the terminal.

### Optional: install the command on your PATH

From the cloned repository:

```sh
mkdir -p "$HOME/.local/bin"
install -m 755 bin/brewski "$HOME/.local/bin/brewski"
```

This replaces any existing `~/.local/bin/brewski`; back up an existing copy first if you want to retain it. Add the following to your shell configuration if `~/.local/bin` is not already on your `PATH`:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

Open a new terminal, then run `brewski --version`. You can check which copy is selected with `command -v brewski`.

## Usage

```sh
brewski
brewski --no-quit
brewski --greedy --no-quit
brewski --autoremove
brewski --diagnostics
```

If running directly from the checkout, use `./bin/brewski` instead of `brewski`.

| Option | Behavior |
| --- | --- |
| `--autoremove` | Remove dependencies Homebrew considers unused. The default is a preview. |
| `--greedy` | Also upgrade casks with `version :latest`. Versioned auto-updating casks are included by default. |
| `--no-quit` | Prevent Homebrew from quitting running cask applications. It does not defer installation. |
| `--diagnostics` | Print `brew config` at the start. |
| `--notify-test` | Request a test desktop notification without running maintenance. |
| `--version` | Show the version without running maintenance. |
| `-h`, `--help` | Show help without running maintenance. |

Options can be combined. Brewski also respects `HOMEBREW_NO_UPGRADE_QUIT_CASKS` and reflects it in the run banner. `NO_COLOR` disables Brewski's color output.

## Passwords and notifications

Brewski attempts a desktop notification when an installer requests a password. Delivery depends on your terminal, notification settings, and environment; a successful notification request does not guarantee that an alert appears.

Password input starts only after terminal echo has been disabled. If a password is required without a usable terminal, the helper fails instead of waiting for invisible input. Brewski records the failed step and continues its remaining checks.

Try notifications with:

```sh
brewski --notify-test
```

`terminal-notifier` is optional; the script also uses terminal notification sequences and an AppleScript fallback.

## Results and exit codes

The summary distinguishes passed steps, warnings, and failures. Remaining updates are advisory and may include intentionally pinned packages. A warning does not mean that all packages are up to date.

| Exit code | Meaning |
| --- | --- |
| `0` | Required steps passed; advisory warnings may remain. |
| `1` | A required step or setup failed. |
| `2` | Invalid command-line usage. |
| `130`, `143`, `129` | Interrupted by `INT`, `TERM`, or `HUP`, respectively. |

A metadata-update failure stops the run before upgrades. Other task failures are recorded while subsequent tasks continue.

Runs coordinate through a per-user lock under `~/Library/Caches/brewski`. The lock file remains on disk intentionally; its existence alone does not mean Brewski is running.

## Update or uninstall

For a Homebrew installation:

```sh
brew update
brew upgrade GalDaich/tap/brewski
# To uninstall:
brew uninstall GalDaich/tap/brewski
```

To update the source checkout:

```sh
git pull --ff-only
```

If you installed a separate copy in `~/.local/bin`, repeat the `install` command above to update that copy. Pulling the repository alone does not update it.

To uninstall that copied command:

```sh
rm "$HOME/.local/bin/brewski"
```

This removes the command, not Homebrew or its packages. The source checkout can be kept separately.

## Development and validation

See [DEVELOPMENT.md](DEVELOPMENT.md) for the test workflow and implementation details.

```sh
zsh -n bin/brewski
python3 -m unittest discover -s tests -v
```

The 15 regression tests cover simulated Homebrew operations, option combinations, failure handling, locking, cleanup, self-upgrade recovery, process interruption, and terminal password handling with fake passwords. They do not perform real package upgrades or validate desktop notification display.

The original working script is preserved at the Git tag `baseline-2026-09-19`; `main` includes the reliability fixes. Report problems through [GitHub Issues](https://github.com/GalDaich/brewski/issues), including the Brewski version, macOS/Homebrew versions, command used, and relevant output. Remove credentials or personal details from any output you share.

## License

[MIT](LICENSE) — copyright 2026 GalDaich.
