#!/usr/bin/env bash
# setup-linux-gemini.sh
# Run once after git clone on Linux (Gemini CLI environment).
# Creates symlinks so Gemini CLI can find skills/workflows:
#   .gemini  -> .opencode   (directory symlink)
#   GEMINI.md -> AGENTS.md  (file symlink)
# Not needed on Windows/Antigravity (use setup-windows-antigravity.ps1 there).

set -e

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXCLUDE_FILE="$REPO/.git/info/exclude"

# ── Step 1: Add .gemini/ to local git exclude ────────────────────────────────
EXCLUDE_ENTRY_1=".gemini/"
if grep -qF "$EXCLUDE_ENTRY_1" "$EXCLUDE_FILE" 2>/dev/null; then
    echo "Step 1: .gemini/ already in .git/info/exclude, skipping"
else
    {
        echo ""
        echo "# Linux/Gemini CLI local symlinks - not tracked by git"
        echo "$EXCLUDE_ENTRY_1"
    } >> "$EXCLUDE_FILE"
    echo "Step 1: .gemini/ added to .git/info/exclude"
fi

# ── Step 2: Add GEMINI.md to local git exclude ───────────────────────────────
EXCLUDE_ENTRY_2="GEMINI.md"
if grep -qF "$EXCLUDE_ENTRY_2" "$EXCLUDE_FILE" 2>/dev/null; then
    echo "Step 2: GEMINI.md already in .git/info/exclude, skipping"
else
    echo "$EXCLUDE_ENTRY_2" >> "$EXCLUDE_FILE"
    echo "Step 2: GEMINI.md added to .git/info/exclude"
fi

# ── Step 3: Create symlink .gemini -> .opencode ───────────────────────────────
SYMLINK_DIR="$REPO/.gemini"
TARGET_DIR="$REPO/.opencode"

if [[ -e "$SYMLINK_DIR" || -L "$SYMLINK_DIR" ]]; then
    echo "Step 3: .gemini already exists, skipping"
else
    ln -s "$TARGET_DIR" "$SYMLINK_DIR"
    echo "Step 3: symlink .gemini -> .opencode created"
fi

# ── Step 4: Create symlink GEMINI.md -> AGENTS.md ────────────────────────────
SYMLINK_FILE="$REPO/GEMINI.md"
TARGET_FILE="$REPO/AGENTS.md"

if [[ -e "$SYMLINK_FILE" || -L "$SYMLINK_FILE" ]]; then
    echo "Step 4: GEMINI.md already exists, skipping"
else
    ln -s "$TARGET_FILE" "$SYMLINK_FILE"
    echo "Step 4: symlink GEMINI.md -> AGENTS.md created"
fi

# ── Verify ─────────────────────────────────────────────────────────────────────
echo ""
echo "=== Verifying git status ==="
git -C "$REPO" status

echo ""
echo "=== Verifying .gemini/skills ==="
ls "$SYMLINK_DIR/skills" 2>/dev/null || echo "(no skills directory found)"

echo ""
echo "=== Verifying GEMINI.md ==="
ls -la "$SYMLINK_FILE" 2>/dev/null || echo "(GEMINI.md not found)"

echo ""
echo "Setup complete."
