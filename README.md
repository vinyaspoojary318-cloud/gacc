# gacc – GitHub Account CLI

**Make multiple GitHub accounts and creating repos from the terminal painless.**

`gacc` helps you:

- Switch between multiple GitHub accounts easily
- Create a new GitHub repository directly from the terminal
- Push your local code in one command

Built on top of the official [GitHub CLI (`gh`)](https://cli.github.com/).

## Why gacc?

If you have more than one GitHub account (personal + work, or multiple personal accounts), the usual flow is painful:

1. Go to GitHub website
2. Create the repository
3. Come back to terminal
4. Add remote
5. Push
6. Hope you used the correct account

With `gacc` it becomes:

```bash
gacc create my-new-project
```

## Requirements

- Python 3.9+
- GitHub CLI (`gh`) installed and authenticated

```bash
# Install gh (example)
brew install gh          # macOS
# or see https://cli.github.com/

# Login with your accounts
gh auth login
```

## Installation

```bash
pip install -e .          # from source
# or later
pip install gacc
```

## Usage

```bash
# Check current account
gacc status

# List all accounts
gacc list

# Switch account
gacc use your-username

# Create repo + push current folder (private by default)
gacc create my-awesome-project

# Create public repo
gacc create my-awesome-project --public

# Create with description + specific account
gacc create my-tool --account personal -d "A cool CLI tool"

# Add a new GitHub account
gacc login
```

## How it works

- Uses `gh auth status` and `gh auth switch` for account management
- Uses `gh repo create --source=. --remote=origin --push` for creating + pushing
- Offers to run `git init` if you’re not in a git repository

## License

MIT
