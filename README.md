# gacc – GitHub Account CLI

**Switch accounts. Create repos. Push code. In plain English if you want.**

```bash
gacc "who am I"
gacc "list my accounts"
gacc "switch to myusername"
gacc "create a public repo called my-app"
```

Or classic commands:

```bash
gacc status
gacc list
gacc use myusername
gacc create my-app --public
```

Built on the official [GitHub CLI (`gh`)](https://cli.github.com/).

## Install (global)

```bash
# From the repo
git clone https://github.com/vinyaspoojary318-cloud/gacc.git
cd gacc
pip install -e .

# Later, when published on PyPI:
# pip install gacc
```

Requires **Python 3.9+** and **[GitHub CLI](https://cli.github.com/)**:

```bash
brew install gh          # macOS
gh auth login            # log in with each account you use
```

> **Why not npm?** `gacc` is a Python tool. Global install is via **pip** (PyPI), which works on every OS the same way `npm install -g` does for Node tools.

## Plain English

| You say | gacc does |
|--------|-----------|
| `gacc "who am I"` | Show active account |
| `gacc "list accounts"` | List all accounts |
| `gacc "switch to octocat"` | Switch account |
| `gacc "login"` | Add / authenticate account |
| `gacc "create a public repo called hello"` | Create + push public repo |
| `gacc "create private project named secret"` | Create private repo |

Same thing with the `ask` subcommand:

```bash
gacc ask "create a public repo called hello"
```

## Commands

| Command | Description |
|---------|-------------|
| `gacc status` | Active GitHub account |
| `gacc list` | All authenticated accounts |
| `gacc use <username>` | Switch account |
| `gacc login` | Authenticate a new account |
| `gacc create <name>` | Create repo + push (private by default) |
| `gacc create <name> --public` | Public repo |
| `gacc create <name> -d "desc" -a user` | Description + specific account |
| `gacc version` | Version |
| `gacc ask "..."` | Plain-English request |

## Why gacc?

Without it: browser → create repo → hope it’s the right account → copy remote → terminal → push.

With it:

```bash
gacc use work
gacc create my-project
# or
gacc "create a repo called my-project"
```

## License

MIT
