#!/bin/bash

# Satele Installer
# This script helps you make 'satele' a global command.

SATELE_PATH="/Users/dcaric/Working/ml/AntigravityMessages/satele"

echo "🪐 Satele Installation Helper"
echo "----------------------------"

if [[ ":$PATH:" == *":$HOME/bin:"* ]]; then
    echo "✅ Home bin directory found in PATH."
else
    echo "⚠️  Home bin directory (~/bin) not found in PATH."
fi

echo ""
echo "Option 1: Add a shell alias (Recommended for your environment)"
echo "Run this command:"
echo "echo \"alias satele='$SATELE_PATH'\" >> ~/.zshrc && source ~/.zshrc"

echo ""
echo "Option 2: Create a symlink in /usr/local/bin (Requires sudo)"
echo "Run this command:"
echo "sudo ln -sf $SATELE_PATH /usr/local/bin/satele"

echo ""
echo "Which one would you like to do? Copy and paste the command above."
