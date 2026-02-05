#!/usr/bin/env python3
"""
agent-mail - Lean email CLI for Claude agents
Wraps mbsync + notmuch + attachment extraction
"""

import argparse
import json
import subprocess
import email
import sys
import os
import re
from pathlib import Path
from email import policy

MAIL_DIR = Path.home() / "Mail"
TMP_DIR = Path("/tmp/agent-mail-attachments")
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR / "config"


def get_email_filepath(message_id):
    """Get file path for a message ID from notmuch"""
    result = subprocess.run(
        ["notmuch", "search", "--output=files", f"id:{message_id}"],
        capture_output=True, text=True
    )
    filepath = result.stdout.strip()
    if not filepath:
        print(f"Email not found: {message_id}", file=sys.stderr)
        sys.exit(1)
    return filepath


def parse_email_file(filepath):
    """Parse an email file and return the message object"""
    with open(filepath, 'rb') as f:
        return email.message_from_binary_file(f, policy=policy.default)


def existing_accounts():
    """Parse ~/.mbsyncrc to find existing account labels"""
    mbsyncrc_path = Path.home() / ".mbsyncrc"
    if not mbsyncrc_path.exists():
        return []
    content = mbsyncrc_path.read_text()
    return re.findall(r'^IMAPAccount\s+(\S+)', content, re.MULTILINE)


def init_notmuch(email_addr, name=""):
    """Initialize notmuch database non-interactively"""
    notmuch_db = MAIL_DIR / ".notmuch"
    if notmuch_db.exists():
        return

    MAIL_DIR.mkdir(parents=True, exist_ok=True)

    # Create the database with notmuch new
    env = os.environ.copy()
    env["NOTMUCH_DATABASE"] = str(MAIL_DIR)
    subprocess.run(["notmuch", "new"], env=env, check=False)

    # Configure via notmuch config set (works without interactive setup)
    config_cmds = [
        ["notmuch", "config", "set", "database.path", str(MAIL_DIR)],
        ["notmuch", "config", "set", "user.primary_email", email_addr],
        ["notmuch", "config", "set", "new.tags", "unread;inbox"],
        ["notmuch", "config", "set", "search.exclude_tags", "deleted;spam"],
        ["notmuch", "config", "set", "maildir.synchronize_flags", "true"],
    ]
    if name:
        config_cmds.append(["notmuch", "config", "set", "user.name", name])

    for cmd in config_cmds:
        subprocess.run(cmd, check=False)

    print(f"Initialized notmuch database at {MAIL_DIR}")


def write_account_config(label, email_addr, password=None, share_password=None):
    """Write mbsync config and password for an account (non-interactive)"""
    # Generate account block from template
    template_path = CONFIG_DIR / "mbsyncrc.template"
    if not template_path.exists():
        print(f"Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    block = template_path.read_text()
    block = block.replace("__LABEL__", label).replace("__EMAIL__", email_addr)

    # Write to ~/.mbsyncrc
    mbsyncrc_path = Path.home() / ".mbsyncrc"
    accounts = existing_accounts()

    if label in accounts:
        # Remove existing block and replace
        content = mbsyncrc_path.read_text()
        pattern = rf'(# iCloud IMAP account: {re.escape(label)}\n)?IMAPAccount {re.escape(label)}\n.*?(?=\n# iCloud IMAP account:|\nIMAPAccount |\Z)'
        content = re.sub(pattern, '', content, flags=re.DOTALL).strip()
        if content:
            content += "\n\n"
        content += block
        mbsyncrc_path.write_text(content)
    elif mbsyncrc_path.exists():
        with open(mbsyncrc_path, 'a') as f:
            f.write("\n" + block)
    else:
        mbsyncrc_path.write_text(block)

    mbsyncrc_path.chmod(0o600)
    print(f"Wrote account '{label}' to {mbsyncrc_path}")

    # Handle password
    password_path = Path.home() / f".icloud-app-password-{label}"
    if password_path.exists():
        print(f"{password_path} already exists, keeping it.")
    elif share_password:
        # Symlink to another account's password
        source = Path.home() / f".icloud-app-password-{share_password}"
        if source.exists():
            password_path.symlink_to(source.name)
            print(f"Linked {password_path.name} -> {source.name}")
        else:
            print(f"Warning: {source} not found, skipping password link", file=sys.stderr)
    elif password:
        password_path.write_text(password + "\n")
        password_path.chmod(0o600)
        print(f"Saved password to {password_path}")
    # else: no password provided, user must create it manually

    # Create Mail directory for this account
    account_mail = MAIL_DIR / label
    account_mail.mkdir(parents=True, exist_ok=True)


def cmd_setup(args):
    """Add an email account"""
    # Non-interactive mode: all required args provided via flags
    if args.label and args.email:
        label = re.sub(r'[^a-z0-9-]', '-', args.label.lower())
        write_account_config(label, args.email, password=args.password, share_password=args.share_password)
        init_notmuch(args.email, name=args.name or "")
        print(f"\nAccount '{label}' ready. Run: agent-mail sync")
        return

    # Interactive mode: prompt for everything
    print("=== agent-mail setup ===\n")

    accounts = existing_accounts()
    if accounts:
        print(f"Existing accounts: {', '.join(accounts)}\n")

    default_label = "icloud" if not accounts else ""
    label_prompt = f"Account label [{default_label}]: " if default_label else "Account label (e.g. work, personal): "
    label = input(label_prompt).strip() or default_label
    if not label:
        print("Label required.", file=sys.stderr)
        sys.exit(1)
    label = re.sub(r'[^a-z0-9-]', '-', label.lower())

    if label in accounts:
        print(f"Account '{label}' already exists in ~/.mbsyncrc.")
        overwrite = input("Replace it? [y/N] ").strip().lower()
        if overwrite != 'y':
            print("Aborted.")
            return

    email_addr = input("iCloud email address: ").strip()
    if not email_addr:
        print("Email required.", file=sys.stderr)
        sys.exit(1)

    # Prompt for password
    password = None
    other_passwords = list(Path.home().glob(".icloud-app-password-*"))
    password_path = Path.home() / f".icloud-app-password-{label}"

    if password_path.exists():
        print(f"\n{password_path} already exists, keeping it.")
    elif other_passwords:
        share = input(f"\nUse same password as {other_passwords[0].name}? [Y/n] ").strip().lower()
        if share != 'n':
            write_account_config(label, email_addr, share_password=other_passwords[0].stem.replace("icloud-app-password-", ""))
            init_notmuch(email_addr)
            print(f"\nAccount '{label}' ready. Run: agent-mail sync")
            return
        else:
            print("\nYou need an app-specific password from https://appleid.apple.com")
            print("  Sign in > Sign-In and Security > App-Specific Passwords")
            password = input("\nPaste your app-specific password (or Enter to skip): ").strip() or None
    else:
        print("\nYou need an app-specific password from https://appleid.apple.com")
        print("  Sign in > Sign-In and Security > App-Specific Passwords")
        password = input("\nPaste your app-specific password (or Enter to skip): ").strip() or None

    write_account_config(label, email_addr, password=password)
    init_notmuch(email_addr)
    print(f"\nAccount '{label}' ready. Run: agent-mail sync")


def cmd_sync(args):
    """Sync emails from iCloud via mbsync"""
    subprocess.run(["mbsync", "-a"], check=True)
    subprocess.run(["notmuch", "new"], check=True)
    print("Sync complete")


def cmd_search(args):
    """Search emails with notmuch"""
    if args.thread:
        result = subprocess.run(
            ["notmuch", "search", "--format=json", "--output=summary", args.query],
            capture_output=True, text=True
        )
        threads = json.loads(result.stdout) if result.stdout.strip() else []
        for thread in threads:
            thread_id = thread.get("thread", "")
            msg_result = subprocess.run(
                ["notmuch", "show", "--format=json", f"thread:{thread_id}"],
                capture_output=True, text=True
            )
            print(msg_result.stdout)
    else:
        result = subprocess.run(
            ["notmuch", "search", "--format=json", args.query],
            capture_output=True, text=True
        )
        print(result.stdout)


def cmd_recent(args):
    """List recent emails"""
    limit = args.limit or 20
    result = subprocess.run(
        ["notmuch", "search", "--format=json", f"--limit={limit}", "*"],
        capture_output=True, text=True
    )
    print(result.stdout)


def cmd_read(args):
    """Read email content"""
    filepath = get_email_filepath(args.id)
    msg = parse_email_file(filepath)

    print(f"From: {msg['from']}")
    print(f"To: {msg['to']}")
    if msg['cc']:
        print(f"Cc: {msg['cc']}")
    print(f"Date: {msg['date']}")
    print(f"Subject: {msg['subject']}")
    print("-" * 40)

    body = msg.get_body(preferencelist=('plain', 'html'))
    if body:
        content = body.get_content()
        print(content)


def cmd_attachments(args):
    """List attachments on an email"""
    filepath = get_email_filepath(args.id)
    msg = parse_email_file(filepath)

    found = False
    for part in msg.walk():
        if part.get_content_disposition() == 'attachment':
            filename = part.get_filename()
            payload = part.get_payload(decode=True)
            size = len(payload) if payload else 0
            print(f"{filename} ({size} bytes)")
            found = True

    if not found:
        print("No attachments")


def cmd_extract(args):
    """Extract attachment to temp file"""
    filepath = get_email_filepath(args.id)
    msg = parse_email_file(filepath)

    TMP_DIR.mkdir(exist_ok=True)

    for part in msg.walk():
        if part.get_content_disposition() == 'attachment':
            filename = part.get_filename()
            if filename == args.filename:
                outpath = TMP_DIR / filename
                with open(outpath, 'wb') as out:
                    out.write(part.get_payload(decode=True))
                print(outpath)
                return

    print(f"Attachment not found: {args.filename}", file=sys.stderr)
    sys.exit(1)


def cmd_folders(args):
    """List mail folders"""
    if not MAIL_DIR.exists():
        print("Mail directory not found. Run: agent-mail sync", file=sys.stderr)
        sys.exit(1)

    for entry in sorted(MAIL_DIR.iterdir()):
        if entry.is_dir() and not entry.name.startswith('.'):
            if (entry / "cur").exists() or (entry / "new").exists():
                count_result = subprocess.run(
                    ["notmuch", "count", f"folder:{entry.name}"],
                    capture_output=True, text=True
                )
                count = count_result.stdout.strip()
                print(f"{entry.name} ({count} messages)")
            else:
                print(f"{entry.name}/")
                for sub in sorted(entry.iterdir()):
                    if sub.is_dir() and not sub.name.startswith('.'):
                        count_result = subprocess.run(
                            ["notmuch", "count", f"folder:{entry.name}/{sub.name}"],
                            capture_output=True, text=True
                        )
                        count = count_result.stdout.strip()
                        print(f"  {sub.name} ({count} messages)")


def main():
    parser = argparse.ArgumentParser(
        prog='agent-mail',
        description='Email CLI for Claude agents - wraps mbsync + notmuch'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # setup
    p_setup = subparsers.add_parser('setup', help='Add an email account (re-run to add more)')
    p_setup.add_argument('--label', help='Account label (e.g. work, personal)')
    p_setup.add_argument('--email', help='iCloud email address')
    p_setup.add_argument('--password', help='App-specific password')
    p_setup.add_argument('--share-password', metavar='LABEL', help='Share password with another account label')
    p_setup.add_argument('--name', help='Your name (for notmuch config)')

    # sync
    subparsers.add_parser('sync', help='Sync all accounts via mbsync')

    # search
    p_search = subparsers.add_parser('search', help='Search emails with notmuch query')
    p_search.add_argument('query', help='notmuch search query')
    p_search.add_argument('--thread', action='store_true', help='Show full thread view')

    # recent
    p_recent = subparsers.add_parser('recent', help='List recent emails')
    p_recent.add_argument('--limit', type=int, default=20, help='Number of emails to show')

    # read
    p_read = subparsers.add_parser('read', help='Read email content')
    p_read.add_argument('id', help='Message ID from search results')

    # attachments
    p_attach = subparsers.add_parser('attachments', help='List attachments on an email')
    p_attach.add_argument('id', help='Message ID from search results')

    # extract
    p_extract = subparsers.add_parser('extract', help='Extract attachment to temp file')
    p_extract.add_argument('id', help='Message ID from search results')
    p_extract.add_argument('filename', help='Attachment filename to extract')

    # folders
    subparsers.add_parser('folders', help='List mail folders')

    args = parser.parse_args()

    commands = {
        'setup': cmd_setup,
        'sync': cmd_sync,
        'search': cmd_search,
        'recent': cmd_recent,
        'read': cmd_read,
        'attachments': cmd_attachments,
        'extract': cmd_extract,
        'folders': cmd_folders,
    }
    commands[args.command](args)


if __name__ == '__main__':
    main()
