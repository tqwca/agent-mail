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


def cmd_setup(args):
    """Interactive first-time setup"""
    print("=== agent-mail setup ===\n")

    # 1. Ask for email
    email_addr = input("Your iCloud email address: ").strip()
    if not email_addr:
        print("Email required.", file=sys.stderr)
        sys.exit(1)

    # 2. Generate mbsyncrc from template
    template_path = CONFIG_DIR / "mbsyncrc.template"
    if not template_path.exists():
        print(f"Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    mbsyncrc = template_path.read_text().replace("__EMAIL__", email_addr)
    mbsyncrc_path = Path.home() / ".mbsyncrc"

    if mbsyncrc_path.exists():
        overwrite = input(f"{mbsyncrc_path} exists. Overwrite? [y/N] ").strip().lower()
        if overwrite != 'y':
            print("Keeping existing .mbsyncrc")
        else:
            mbsyncrc_path.write_text(mbsyncrc)
            mbsyncrc_path.chmod(0o600)
            print(f"Wrote {mbsyncrc_path}")
    else:
        mbsyncrc_path.write_text(mbsyncrc)
        mbsyncrc_path.chmod(0o600)
        print(f"Wrote {mbsyncrc_path}")

    # 3. App-specific password
    password_path = Path.home() / ".icloud-app-password"
    if password_path.exists():
        print(f"\n{password_path} already exists, skipping password setup.")
    else:
        print("\nYou need an app-specific password from https://appleid.apple.com")
        print("  Sign in > Sign-In and Security > App-Specific Passwords")
        app_password = input("\nPaste your app-specific password (or press Enter to skip): ").strip()
        if app_password:
            password_path.write_text(app_password + "\n")
            password_path.chmod(0o600)
            print(f"Saved to {password_path}")
        else:
            print(f"Skipped. Save it later to {password_path}")

    # 4. Create Mail directory
    MAIL_DIR.mkdir(exist_ok=True)

    # 5. Initialize notmuch
    notmuch_db = MAIL_DIR / ".notmuch"
    if not notmuch_db.exists():
        print("\nInitializing notmuch database...")
        env = os.environ.copy()
        env["NOTMUCH_DATABASE"] = str(MAIL_DIR)
        subprocess.run(
            ["notmuch", "new"],
            env=env,
            check=False
        )

    # 6. First sync
    print("\nReady to sync. Run: agent-mail sync")


def cmd_sync(args):
    """Sync emails from iCloud via mbsync"""
    subprocess.run(["mbsync", "-a"], check=True)
    subprocess.run(["notmuch", "new"], check=True)
    print("Sync complete")


def cmd_search(args):
    """Search emails with notmuch"""
    if args.thread:
        # Thread view: show full threads matching the query
        result = subprocess.run(
            ["notmuch", "search", "--format=json", "--output=summary", args.query],
            capture_output=True, text=True
        )
        threads = json.loads(result.stdout) if result.stdout.strip() else []
        for thread in threads:
            thread_id = thread.get("thread", "")
            # Show messages in this thread
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

    # Print headers
    print(f"From: {msg['from']}")
    print(f"To: {msg['to']}")
    if msg['cc']:
        print(f"Cc: {msg['cc']}")
    print(f"Date: {msg['date']}")
    print(f"Subject: {msg['subject']}")
    print("-" * 40)

    # Print body
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
                print(outpath)  # Claude reads this path
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
            # Check if it looks like a Maildir (has cur/new/tmp)
            if (entry / "cur").exists() or (entry / "new").exists():
                count_result = subprocess.run(
                    ["notmuch", "count", f"folder:{entry.name}"],
                    capture_output=True, text=True
                )
                count = count_result.stdout.strip()
                print(f"{entry.name} ({count} messages)")
            else:
                # Might be a parent folder with subfolders
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
    subparsers.add_parser('setup', help='Interactive first-time setup')

    # sync
    subparsers.add_parser('sync', help='Sync emails from iCloud via mbsync')

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
