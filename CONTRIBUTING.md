# Contributing

Open an issue to describe a bug or discuss a proposed behavior change. Include
`brewski --version`, macOS and Homebrew versions, the command used, and relevant
output with private details removed.

Fork the repository, create a branch, and submit a pull request against `main`.
Keep changes focused and add regression coverage for behavior changes.

Before submitting:

```sh
zsh -n bin/brewski
python3 -m unittest discover -s tests -v
git diff --check
```

Tests must use simulated Homebrew commands and fake passwords. Never add tests
that upgrade a contributor's real packages or require administrator credentials.
See [DEVELOPMENT.md](DEVELOPMENT.md) for terminal requirements and release steps.
After merging, delete the source branch locally and remotely. Preserve recovery
and release tags.

Contributions are provided under the repository's [MIT license](LICENSE).
