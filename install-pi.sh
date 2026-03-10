#!/bin/bash
set -e

REPO_URL="https://github.com/smoldrago/kroki-diagrams.git"
SKILL_NAME="kroki-diagrams"
SKILL_DIR="$HOME/.pi/agent/skills/$SKILL_NAME"
PROMPTS_DIR="$HOME/.pi/agent/prompts"

if [ ! -f "plugins/$SKILL_NAME/SKILL.md" ]; then
    echo "Cloning $SKILL_NAME..."
    TEMP_DIR=$(mktemp -d)
    git clone --depth 1 "$REPO_URL" "$TEMP_DIR"
    cd "$TEMP_DIR"
    CLEANUP=true
else
    CLEANUP=false
fi

echo "Installing skill to $SKILL_DIR..."
mkdir -p "$(dirname "$SKILL_DIR")"
rm -rf "$SKILL_DIR"
cp -r "plugins/$SKILL_NAME" "$SKILL_DIR"

if [ -d "$SKILL_DIR/commands" ]; then
    echo "Installing prompts to $PROMPTS_DIR..."
    mkdir -p "$PROMPTS_DIR"
    cp "$SKILL_DIR/commands/"*.md "$PROMPTS_DIR/" 2>/dev/null || true
fi

if [ "$CLEANUP" = true ]; then
    rm -rf "$TEMP_DIR"
fi

echo ""
echo "Done! Restart Pi to use $SKILL_NAME."
echo "Use \$kroki-diagrams or let the agent trigger it implicitly."

