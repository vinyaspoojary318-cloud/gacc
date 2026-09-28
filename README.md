<p align="center">
  <img src="docs/logo.jpg" alt="gacc Ice Bear logo" width="160" />
</p>

<h1 align="center">gacc</h1>

<p align="center">
  <strong>Talk to GitHub in plain English — and never ship under the wrong account.</strong>
</p>

<p align="center">
  <em>Stay cool. ❄️</em>
</p>

```bash
gacc "who am I"
gacc "check account"
gacc "switch to myusername"
gacc "create a public repo called my-app"
gacc ship my-app --public
gacc create my-app --public --explain
```

When you run `gacc` with no arguments, Ice Bear greets you in the terminal.

Built on the official [GitHub CLI (`gh`)](https://cli.github.com/).

## What makes gacc different

| Feature | What it does |
|--------|----------------|
| **Ice Bear startup** | Distinct terminal banner every time you open `gacc` |
| **Plain English** | `gacc "create a public repo called hello"` |
| **Account guard** | Warns before create/ship if active account ≠ remote / expected |
| **`gacc check`** | Active account vs git identity vs remote owner |
| **`gacc ship`** | Init → commit → create → push |
| **Activity summary** | After every command, a clear “What happened” table |
| **`--explain` / `--dry-run`** | Print commands without running them |

## Install

```bash
git clone https://github.com/vinyaspoojary318-cloud/gacc.git
cd gacc
pip install -e .
```

Requires **Python 3.9+** and **[GitHub CLI](https://cli.github.com/)**:

```bash
brew install gh   # macOS
gh auth login     # for each account
```

## Commands

| Command | Description |
|---------|-------------|
| `gacc` | Ice Bear banner + help |
| `gacc status` | Active GitHub account |
| `gacc check` | Account guard report |
| `gacc list` | All authenticated accounts |
| `gacc use <user>` | Switch account |
| `gacc login` | Authenticate a new account |
| `gacc create <name>` | Create repo + push (with guard + summary) |
| `gacc ship [name]` | One-shot ship |
| `gacc version` | Version |
| `gacc ask "..."` | Plain English |

## License

MIT

Logo inspired by Ice Bear (We Bare Bears) — used as project mascot branding.
