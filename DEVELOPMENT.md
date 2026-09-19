# Developing Brewski

The original working script is preserved at the annotated tag
`baseline-2026-09-19`. The reliability fixes have been merged into `main`.
The separate executable in `~/.local/bin/brewski` is not updated by this checkout.

## Checks

On macOS with system Zsh and Python 3:

```sh
zsh -n bin/brewski
python3 -m unittest discover -s tests -v
git diff --check
```

The tests substitute a simulated `brew` executable, use temporary directories,
and change only the lock-directory assignment in a temporary script copy.
They never upgrade packages or request actual administrator credentials.
Python is a test dependency, not a runtime dependency.

The process and PTY tests require normal access to macOS subprocesses and
controlling terminals. A sandbox that denies those operations cannot fully
validate them. The password tests send only a fixed fake password, check that
it is absent from terminal output, and check echo restoration.

## Behavior of the fixes

- Password input refuses to start if terminal settings cannot be saved or echo
  cannot be disabled. Signal handlers restore settings and exit.
- Each run retains a private script snapshot for sudo's askpass helper, so
  upgrading or removing the installed version does not break later prompts.
- Cancellation stops and enumerates the child tree, sends TERM, allows up to
  three seconds for shutdown, then uses KILL on survivors and waits for the
  immediate child. SIGINT, SIGTERM, and SIGHUP return 130, 143, and 129.
  Privileged installers and detached processes are outside the guarantees of
  ordinary user-process cancellation. If discovery or termination fails,
  Brewski retains its runtime directory and reports its location.
- A per-user lock under `~/Library/Caches/brewski` coordinates runs regardless
  of TMPDIR. The lock file persists intentionally; the kernel releases the lock.
- Runtime cleanup is registered before helper setup.
- The final outdated report distinguishes command failure, nonempty results,
  and no remaining updates. Nonempty results remain advisory and may include
  intentionally pinned packages. Only emptiness is interpreted; human-readable
  package/version text is not parsed, so no JSON parser dependency is required.
- Advisory failures and remaining updates produce a completed-with-warnings
  summary while preserving exit status 0 if required tasks passed.
- `HOMEBREW_NO_UPGRADE_QUIT_CASKS` is respected and reflected in the banner.
  `--no-quit` does not promise deferred installation.
- `--version` reports `0.1.0`. Notifications are described as best-effort.

The suite validates simulated maintenance and actual PTY behavior. Real Homebrew
upgrades and desktop notification display are not automated acceptance tests.


## Releases

1. Update `VERSION` in `bin/brewski`, its version assertion in the tests, and
   `CHANGELOG.md`. Submit and merge the change after CI passes.
2. On the updated `main`, create an annotated `vMAJOR.MINOR.PATCH` tag and push
   that tag. The Release workflow reruns both macOS test jobs, checks the version
   and ancestry, and publishes a source archive plus `SHA256SUMS`.
3. Download the release archive and verify its SHA-256. Update the URL and checksum
   in `GalDaich/homebrew-tap/Formula/brewski.rb`, run its CI checks, and merge.
4. Delete merged working branches locally and remotely; keep release tags.

The tap is updated through ordinary commits. Release automation needs only the
source repository's built-in token, with write access confined to the publish job.
It has no cross-repository token. Do not move published tags or replace release
assets; issue a new patch release for corrections.
