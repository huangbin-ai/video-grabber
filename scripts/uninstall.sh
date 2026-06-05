#!/bin/bash
# Video Grabber — 卸载脚本
set -euo pipefail

SERVICE_ID="com.videograbber.daemon"
PLIST="$HOME/Library/LaunchAgents/${SERVICE_ID}.plist"

echo "⏹  停止服务..."
launchctl unload "$PLIST" 2>/dev/null || true

if [[ -f "$PLIST" ]]; then
  rm "$PLIST"
  echo "✅ 已删除 $PLIST"
else
  echo "ℹ️  plist 不存在，跳过"
fi

echo "✅ 卸载完成。Chrome 扩展需手动移除。"
