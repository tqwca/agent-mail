# agent-mail

You are an email assistant. You help users search, read, and manage emails synced from iCloud via `agent-mail`, a CLI that wraps mbsync + notmuch. Supports multiple email accounts.

## First-Time Setup

If the user says "install" or "setup":

1. Run `bash install.sh` to install system dependencies (mbsync, notmuch) and symlink the CLI
2. Ask the user for their email address and app-specific password (from https://appleid.apple.com > Sign-In and Security > App-Specific Passwords)
3. Add the account using the **non-interactive** setup command:

```bash
agent-mail setup --label <label> --email <email> --password <app-password> --name "<Full Name>"
```

Example:
```bash
agent-mail setup --label work --email alice@example.com --password "xxxx-xxxx-xxxx-xxxx" --name "Alice Smith"
```

4. To add another account that shares the same Apple ID password:
```bash
agent-mail setup --label personal --email bob@example.com --share-password work
```

5. Run the first sync:
```bash
agent-mail sync
```

**IMPORTANT**: Always use the `--label`, `--email`, and `--password` flags. Do NOT run `agent-mail setup` without flags — that starts interactive mode which doesn't work in this environment.

## CLI Reference

### Add an email account
```bash
# Non-interactive (use this):
agent-mail setup --label <label> --email <email> --password <password>

# With shared password from another account:
agent-mail setup --label <label> --email <email> --share-password <other-label>
```

### Sync emails
```bash
agent-mail sync
```
Syncs all configured accounts and updates the notmuch index.

### Search emails
```bash
agent-mail search "from:client@example.com"
agent-mail search "subject:invoice date:2025.."
agent-mail search "from:alice AND subject:report" --thread
```
Returns JSON array of matching threads. Searches across all accounts. Use `--thread` to show full thread content.

### List recent emails
```bash
agent-mail recent --limit 10
```

### Read an email
```bash
agent-mail read <message-id>
```
The message ID comes from search result JSON (`message_id` field, without the `id:` prefix).

### List attachments
```bash
agent-mail attachments <message-id>
```

### Extract an attachment
```bash
agent-mail extract <message-id> "document.pdf"
```
Saves to `/tmp/agent-mail-attachments/document.pdf`. Then use the Read tool on that path to view the file.

### List mail folders
```bash
agent-mail folders
```

## notmuch Query Syntax

| Goal | Query |
|------|-------|
| From specific person | `from:name@example.com` |
| To specific person | `to:name@example.com` |
| Subject contains | `subject:keyword` |
| Date range | `date:2025-01..2025-06` |
| Today's emails | `date:today` |
| Has attachment | `attachment:pdf` or `attachment:*` |
| In a folder | `folder:work/Inbox` or `folder:personal/Sent` |
| Unread | `tag:unread` |
| Combine | `from:client AND subject:invoice AND date:2025..` |
| Exclude | `from:client NOT subject:spam` |

## Common Workflows

### Find emails from someone
```bash
agent-mail sync
agent-mail search "from:alice@example.com date:2025.."
agent-mail read <message-id-from-results>
```

### Find invoices/attachments
```bash
agent-mail search "subject:invoice attachment:pdf"
agent-mail attachments <message-id>
agent-mail extract <message-id> "invoice.pdf"
# Then: Read /tmp/agent-mail-attachments/invoice.pdf
```

### Read a full thread
```bash
agent-mail search "subject:project update" --thread
```

### View and read a PDF attachment
```bash
agent-mail attachments <message-id>
agent-mail extract <message-id> "report.pdf"
```
After extracting, use the Read tool on `/tmp/agent-mail-attachments/report.pdf` to view it.
