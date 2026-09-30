<p align="center">
  <img src="docs/logo.jpg" alt="gacc Ice Bear logo" width="160" />
</p>

<h1 align="center">gacc</h1>

<p align="center">
  <strong>Control multiple GitHub accounts in plain English.</strong><br/>
  Login every account · switch with a sentence · never ship under the wrong one.
</p>

<p align="center">
  <em>Stay cool. ❄️</em>
</p>

```bash
gacc "login"                 # add a GitHub account (run once per account)
gacc "list my accounts"      # see all logged-in accounts
gacc "switch to myusername"  # change the active account
gacc "who am I"              # current active account
gacc "check account"         # right account for this folder?
gacc prompt                  # show active account in your shell prompt
gacc "create a public repo called my-app"
gacc ship my-app --public
```

When you run `gacc` with no arguments, Ice Bear greets you in the terminal.

Built on the official [GitHub CLI (`gh`)](https://cli.github.com/).

## Main goal: multi-account control

| You want | Plain English |
|----------|----------------|
| Add work + personal | `gacc "login"` (repeat for each account) |
| See every account | `gacc "list my accounts"` |
| Switch active account | `gacc "switch to octocat"` |
| Who is active now? | `gacc "who am I"` |
| Safe before push | `gacc "check account"` |
| Account in prompt | `gacc prompt` |

## Install

```bash
git clone https://github.com/vinyaspoojary318-cloud/gacc.git
cd gacc
pip install .
```

Requires **Python 3.9+** and **[GitHub CLI](https://cli.github.com/)**:

```bash
# Windows
winget install --id GitHub.cli
# or: scoop install gh
# or download: https://cli.github.com/

# macOS
brew install gh

# Linux (Debian/Ubuntu)
sudo apt install gh
```

Then log in each account you manage:

```bash
gacc login
gacc login          # again for your second account
gacc "list my accounts"
gacc "switch to <username>"
```

## Shell prompt (active account)

Show which GitHub account is active in every prompt:

```bash
# bash
gacc prompt --shell bash --print >> ~/.bashrc && source ~/.bashrc

# zsh
gacc prompt --shell zsh --print >> ~/.zshrc && source ~/.zshrc

# Windows PowerShell
gacc prompt --shell powershell
# paste the snippet into your $PROFILE
```

Uses `gacc status --short` under the hood. Prompt looks like: `(your-username) $`

## What makes gacc different

| Feature | What it does |
|--------|----------------|
| **Multi-account** | Login many accounts, list them, switch in plain English |
| **Shell prompt** | Active account visible in PS1 |
| **Ice Bear startup** | Distinct terminal banner |
| **Plain English** | `gacc "switch to myusername"` |
| **Account guard** | Warns before create/ship if active account ≠ remote / expected |
| **`gacc check`** | Active account vs git identity vs remote owner |
| **`gacc ship`** | Init → commit → create → push |
| **Activity summary** | After every command, a clear “What happened” table |
| **`--explain` / `--dry-run`** | Print commands without running them |

## Commands

| Command | Description |
|---------|-------------|
| `gacc` | Ice Bear banner + help |
| `gacc login` | Authenticate / add another account |
| `gacc list` | All authenticated accounts |
| `gacc use <user>` | Switch active account |
| `gacc status` | Active GitHub account |
| `gacc status --short` | Username only (for prompts) |
| `gacc check` | Account guard report |
| `gacc prompt` / `gacc init` | Shell snippet for PS1 |
| `gacc create <name>` | Create repo + push |
| `gacc ship [name]` | One-shot ship |
| `gacc version` | Version |

## License

MIT

Logo inspired by Ice Bear (We Bare Bears) — used as project mascot branding.
