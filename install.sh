#!/bin/bash
set -e

echo "Installing agent-mail..."

# Detect OS and install dependencies
if command -v apt-get &>/dev/null; then
    echo "Detected Debian/Ubuntu..."
    sudo apt-get update && sudo apt-get install -y isync notmuch
elif command -v brew &>/dev/null; then
    echo "Detected macOS (Homebrew)..."
    brew install isync notmuch
elif command -v pacman &>/dev/null; then
    echo "Detected Arch Linux..."
    sudo pacman -S --noconfirm isync notmuch
elif command -v dnf &>/dev/null; then
    echo "Detected Fedora/RHEL..."
    sudo dnf install -y isync notmuch
else
    echo "Could not detect package manager."
    echo "Please install isync (mbsync) and notmuch manually."
    exit 1
fi

# Make CLI executable + symlink
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chmod +x "$SCRIPT_DIR/agent-mail.py"
sudo ln -sf "$SCRIPT_DIR/agent-mail.py" /usr/local/bin/agent-mail

echo ""
echo "=========================================="
echo "agent-mail installed!"
echo ""
echo "Next: run 'agent-mail setup' to configure"
echo "=========================================="
