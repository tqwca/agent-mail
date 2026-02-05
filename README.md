# agent-mail

Email CLI for Claude agents. Wraps mbsync + notmuch to give Claude (or any AI agent) search, read, and attachment extraction over IMAP email.

## Quick Start

```bash
git clone <repo-url> agent-mail
cd agent-mail
claude
> install
```

Claude reads CLAUDE.md, runs the install script, walks you through iCloud setup. Done.

## Manual Setup

```bash
# 1. Install dependencies
bash install.sh

# 2. Interactive configuration
agent-mail setup

# 3. Sync and search
agent-mail sync
agent-mail recent
agent-mail search "from:someone@example.com"
```

## Prerequisites

- Python 3.6+
- Linux or macOS
- iCloud account (iCloud+ with custom domain, or @icloud.com/@me.com)
- App-specific password from [appleid.apple.com](https://appleid.apple.com)

## Commands

| Command | Description |
|---------|-------------|
| `agent-mail setup` | Interactive first-time configuration |
| `agent-mail sync` | Sync emails from iCloud via mbsync |
| `agent-mail search <query>` | Search with notmuch query syntax |
| `agent-mail search <query> --thread` | Show full thread view |
| `agent-mail recent [--limit N]` | List recent emails |
| `agent-mail read <id>` | Display email headers + body |
| `agent-mail attachments <id>` | List attachments on an email |
| `agent-mail extract <id> <filename>` | Extract attachment to /tmp |
| `agent-mail folders` | List mail folders |

## Setup Details

### What `install.sh` does

1. Detects your OS (Debian/Ubuntu, macOS, Arch, Fedora)
2. Installs `isync` (provides `mbsync`) and `notmuch` via your package manager
3. Symlinks `agent-mail.py` to `/usr/local/bin/agent-mail`

### What `agent-mail setup` does

1. Asks for your iCloud email address
2. Generates `~/.mbsyncrc` from the template with your email
3. Prompts for your app-specific password and saves it to `~/.icloud-app-password`
4. Creates `~/Mail/` directory
5. Initializes the notmuch database

### Getting an App-Specific Password

1. Go to [appleid.apple.com](https://appleid.apple.com)
2. Sign in > **Sign-In and Security** > **App-Specific Passwords**
3. Generate a new password (name it "agent-mail" or similar)
4. Copy the `xxxx-xxxx-xxxx-xxxx` password — you'll paste it during `agent-mail setup`

### Security

Credentials are stored locally with restricted permissions:
- `~/.icloud-app-password` — chmod 600
- `~/.mbsyncrc` — chmod 600
- `~/Mail/` — your local email cache

### notmuch Query Syntax

| Goal | Query |
|------|-------|
| From someone | `from:name@example.com` |
| Subject contains | `subject:keyword` |
| Date range | `date:2025-01..2025-06` |
| Today's emails | `date:today` |
| Has attachment | `attachment:pdf` or `attachment:*` |
| In a folder | `folder:Inbox` |
| Unread | `tag:unread` |
| Combine | `from:client AND subject:invoice` |

## How It Works

```
agent-mail CLI (Python stdlib only)
    ├── mbsync     → IMAP sync from iCloud
    ├── notmuch    → Full-text search index
    ├── Maildir    → Local email storage
    └── email lib  → MIME parsing & attachment extraction
```

No external Python dependencies. Everything uses the standard library.

## Using with Claude

This repo is designed as a Claude Code agent. When you `cd agent-mail && claude`, Claude reads `CLAUDE.md` which tells it how to use every command. Just say "install" for first-time setup, or ask it to search/read emails.
