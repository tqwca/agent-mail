# agent-mail

Email CLI for Claude agents. Wraps mbsync + notmuch to give Claude (or any AI agent) search, read, and attachment extraction over IMAP email. Supports multiple accounts.

## Quick Start

```bash
git clone https://github.com/tqwca/agent-mail.git
cd agent-mail
claude
> install
```

Claude reads CLAUDE.md, runs the install script, walks you through account setup. Done.

## Manual Setup

```bash
# 1. Install system dependencies (mbsync + notmuch)
bash install.sh

# 2. Add your first email account
agent-mail setup --label work --email you@example.com --password "xxxx-xxxx-xxxx-xxxx" --name "Your Name"

# 3. Add another account (optional — shares password if same Apple ID)
agent-mail setup --label personal --email other@example.com --share-password work

# 4. Sync and search
agent-mail sync
agent-mail recent
agent-mail search "from:someone@example.com"
```

Setup also works interactively (just run `agent-mail setup` with no flags).

## Prerequisites

- Python 3.6+
- Linux or macOS
- An iCloud email account (iCloud+ custom domain, @icloud.com, or @me.com)
- An [app-specific password](https://appleid.apple.com) for each account

## Commands

| Command | Description |
|---------|-------------|
| `agent-mail setup --label <l> --email <e> --password <p>` | Add an email account |
| `agent-mail sync` | Sync all accounts via mbsync |
| `agent-mail search <query>` | Search with notmuch query syntax |
| `agent-mail search <query> --thread` | Show full thread view |
| `agent-mail recent [--limit N]` | List recent emails (across all accounts) |
| `agent-mail read <id>` | Display email headers + body |
| `agent-mail attachments <id>` | List attachments on an email |
| `agent-mail extract <id> <filename>` | Extract attachment to /tmp |
| `agent-mail folders` | List mail folders |

## Multiple Accounts

Run `agent-mail setup` once per account. Each account gets:
- A label (e.g. `work`, `personal`)
- Its own IMAP config block in `~/.mbsyncrc`
- Its own password file (`~/.icloud-app-password-<label>`)
- Its own mail directory (`~/Mail/<label>/`)

If two accounts share the same Apple ID (e.g. two addresses on the same custom domain), setup will offer to share the password file.

`agent-mail sync` syncs all accounts. `agent-mail search` searches across all accounts.

## Setup Details

### What `install.sh` does

1. Detects your OS (Debian/Ubuntu, macOS/Homebrew, Arch, Fedora)
2. Installs `isync` (provides `mbsync`) and `notmuch`
3. Symlinks `agent-mail.py` to `/usr/local/bin/agent-mail`

### What `agent-mail setup` does

1. Takes an account label, email address, and password (via flags or interactive prompts)
2. Generates an account block from `config/mbsyncrc.template` and appends it to `~/.mbsyncrc`
3. Saves the app-specific password to `~/.icloud-app-password-<label>` (or symlinks to another account's password with `--share-password`)
4. Creates the account's mail directory under `~/Mail/<label>/`
5. Initializes the notmuch database and configures it non-interactively (first run only)

### Getting an App-Specific Password

1. Go to [appleid.apple.com](https://appleid.apple.com)
2. Sign in > **Sign-In and Security** > **App-Specific Passwords**
3. Generate a new password (name it "agent-mail" or similar)
4. Copy the `xxxx-xxxx-xxxx-xxxx` password — you'll paste it during setup

### Security

Credentials are stored locally with restricted permissions:
- `~/.icloud-app-password-*` — chmod 600
- `~/.mbsyncrc` — chmod 600
- `~/Mail/` — local email cache

## notmuch Query Syntax

| Goal | Query |
|------|-------|
| From someone | `from:name@example.com` |
| Subject contains | `subject:keyword` |
| Date range | `date:2025-01..2025-06` |
| Today's emails | `date:today` |
| Has attachment | `attachment:pdf` or `attachment:*` |
| In a folder | `folder:work/Inbox` |
| Unread | `tag:unread` |
| Combine | `from:client AND subject:invoice` |

## How It Works

```
agent-mail CLI (Python stdlib only)
    ├── mbsync     → IMAP sync (one channel per account)
    ├── notmuch    → Full-text search index (across all accounts)
    ├── Maildir    → Local email storage (~/Mail/<account>/)
    └── email lib  → MIME parsing & attachment extraction
```

No external Python dependencies. Standard library only.

## Using with Claude

This repo is a Claude Code agent. `cd agent-mail && claude`, then:
- Say **"install"** for first-time setup
- Say **"setup"** to add another email account
- Ask it to search, read, or extract attachments from your email
