#!/bin/bash
# Video Grabber — 安装脚本（macOS）
# 注册 launchd 服务，开机自启 daemon
set -euo pipefail

APP_NAME="Video Grabber"
SERVICE_ID="com.videograbber.daemon"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON="$PROJECT_DIR/daemon/server.py"
PLIST="$HOME/Library/LaunchAgents/${SERVICE_ID}.plist"
PORT="${GRABBER_PORT:-7789}"

# ── 检查环境 ──────────────────────────────────────────

if [[ "$(uname)" != "Darwin" ]]; then
  echo "❌ 此脚本仅支持 macOS" >&2
  exit 1
fi

PYTHON3="$(command -v python3 || true)"
if [[ -z "$PYTHON3" ]]; then
  echo "❌ 未找到 python3" >&2
  exit 1
fi

YT_DLP="$(command -v yt-dlp || true)"
if [[ -z "$YT_DLP" ]]; then
  echo "❌ 未找到 yt-dlp，请先运行: brew install yt-dlp" >&2
  exit 1
fi

echo "✅ python3: $PYTHON3"
echo "✅ yt-dlp:  $YT_DLP"
echo "✅ daemon:  $DAEMON"
echo ""

# ── 停止旧服务（如果有）────────────────────────────────

if launchctl list 2>/dev/null | grep -q "$SERVICE_ID"; then
  echo "⏹  停止旧服务..."
  launchctl unload "$PLIST" 2>/dev/null || true
fi

# ── 生成 plist ────────────────────────────────────────

mkdir -p "$(dirname "$PLIST")"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${SERVICE_ID}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON3}</string>
    <string>${DAEMON}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${HOME}/Library/Logs/video-grabber.log</string>
  <key>StandardErrorPath</key>
  <string>${HOME}/Library/Logs/video-grabber.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
</dict>
</plist>
EOF

echo "✅ plist 已写入: $PLIST"

# ── 启动服务 ──────────────────────────────────────────

launchctl load "$PLIST"
echo "✅ 服务已启动"

# ── 健康检查 ──────────────────────────────────────────

echo ""
echo "⏳ 等待 daemon 就绪..."
sleep 2

for i in 1 2 3 4 5; do
  if curl -s "http://127.0.0.1:${PORT}/health" | grep -q '"ok":true'; then
    echo "✅ daemon 运行正常 (http://127.0.0.1:${PORT})"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  下一步：加载 Chrome 扩展"
    echo ""
    echo "  1. 打开 Chrome → chrome://extensions/"
    echo "  2. 右上角打开「开发者模式」"
    echo "  3. 点「加载已解压的扩展程序」"
    echo "  4. 选择: $PROJECT_DIR/extension"
    echo "  5. 固定扩展图标到工具栏"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
  fi
  sleep 1
done

echo "⚠️  daemon 未响应，查看日志: cat ~/Library/Logs/video-grabber.log"
exit 1
