# gacc – GitHub Account CLI

**Talk to GitHub in plain English — and never ship under the wrong account.**

```bash
gacc "who am I"
gacc "check account"
gacc "switch to myusername"
gacc "create a public repo called my-app"
gacc ship my-app --public
gacc create my-app --public --explain
```

Built on the official [GitHub CLI (`gh`)](https://cli.github.com/).

## What makes gacc different

| Feature | What it does |
|--------|----------------|
| **Plain English** | `gacc "create a public repo called hello"` |
| **Account guard** | Warns before create/ship if active account ≠ remote / expected |
| **`gacc check`** | Shows active account vs git identity vs remote owner |
| **`gacc ship`** | One shot: init → commit → create → push |
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
| `gacc status` | Active GitHub account |
| `gacc check` | Account guard report for this folder |
| `gacc list` | All authenticated accounts |
| `gacc use <user>` | Switch account |
| `gacc login` | Authenticate a new account |
| `gacc create <name>` | Create repo + push (with guard) |
| `gacc create <name> --public --explain` | Dry-run create |
| `gacc ship [name]` | Init → commit → create → push |
| `gacc ship my-app --public -a work` | Ship under a specific account |
| `gacc version` | Version |
| `gacc ask "..."` | Plain English |

### Create options

```bash
gacc create my-app --public
gacc create my-app -d "My app" -a myusername
gacc create my-app --no-push
gacc create my-app --force          # skip guard prompt
```

### Ship options

```bash
gacc ship                    # uses folder name
gacc ship my-app --public
gacc ship my-app -m "First commit" -a work
gacc ship my-app --explain
```

## Plain English examples

| You say | gacc does |
|--------|-----------|
| `gacc "who am I"` | status |
| `gacc "check account"` | check |
| `gacc "list accounts"` | list |
| `gacc "switch to octocat"` | use |
| `gacc "create a public repo called hello"` | create |
| `gacc "ship this as public repo demo"` | ship |

## License

MIT
