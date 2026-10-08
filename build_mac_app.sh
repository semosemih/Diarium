#!/usr/bin/env bash
set -e

PROJECT_DIR="/Users/semihsengul/Desktop/notebook pipeline"
APP_NAME="Ayna"
DESKTOP_APP="/Users/semihsengul/Desktop/${APP_NAME}.app"
APPS_DIR="/Applications/${APP_NAME}.app"

echo "Building macOS Application bundle for ${APP_NAME}..."

# Remove old app bundle if exists
rm -rf "$DESKTOP_APP" "$APPS_DIR" 2>/dev/null || true

# Create directory structure
mkdir -p "${DESKTOP_APP}/Contents/MacOS"
mkdir -p "${DESKTOP_APP}/Contents/Resources"

# Create Info.plist
cat << 'EOF' > "${DESKTOP_APP}/Contents/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Ayna</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.semih.ayna</string>
    <key>CFBundleName</key>
    <string>Ayna</string>
    <key>CFBundleDisplayName</key>
    <string>Ayna</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Create executable runner
cat << EOF > "${DESKTOP_APP}/Contents/MacOS/Ayna"
#!/bin/bash
DIR="${PROJECT_DIR}"
cd "\$DIR" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:\$PATH"
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
exec python3 app.py
EOF

chmod +x "${DESKTOP_APP}/Contents/MacOS/Ayna"

# Also copy/link to /Applications so Spotlight / Raycast indexes it globally
cp -R "${DESKTOP_APP}" /Applications/ 2>/dev/null || true

echo "Ayna.app created successfully on Desktop and in /Applications!"
