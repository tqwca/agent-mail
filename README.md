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

## How It Works

```
agent-mail CLI (Python stdlib only)
    ├── mbsync     → IMAP sync from iCloud
    ├── notmuch    → Full-text search index
    ├── Maildir    → Local email storage
    └── email lib  → MIME parsing & attachment extraction
```

No external Python dependencies. Everything uses the standard library.
