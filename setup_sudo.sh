#!/bin/bash

# Get current username
USER=$(whoami)
SUDO_FILE="/etc/sudoers.d/satele_$USER"

echo "🔐 Configuring passwordless sudo for user: $USER"
echo "⚠️  You will be prompted for your password one last time."

# Check if the file already exists
if [ -f "$SUDO_FILE" ]; then
    echo "✅ Configuration already exists at $SUDO_FILE"
    exit 0
fi

# Create the config file safely
# We use a temp file and visudo to validate syntax before applying
TMP_FILE=$(mktemp)
echo "$USER ALL=(ALL) NOPASSWD: ALL" > "$TMP_FILE"

# Validate syntax
if sudo visudo -cf "$TMP_FILE"; then
    echo "✅ Syntax check passed."
    sudo cp "$TMP_FILE" "$SUDO_FILE"
    sudo chmod 0440 "$SUDO_FILE"
    echo "✅ Passwordless sudo enabled! Restart your terminal or shell."
else
    echo "❌ specific syntax error in sudoers configuration."
    rm "$TMP_FILE"
    exit 1
fi

rm "$TMP_FILE"
