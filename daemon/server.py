#!/usr/bin/env python3
"""Video Grabber daemon — 接收浏览器扩展发来的 URL，调 yt-dlp 下载。

纯标准库，零第三方依赖。只监听 localhost。

环境变量配置（全部可选）：
    GRABBER_PORT              监听端口          (默认 7789)
    GRABBER_DOWNLOADS         下载目录          (默认 ~/Downloads)
    GRABBER_YT_DLP            yt-dlp 路径       (默认 自动检测)
    GRABBER_MAX_HEIGHT        最大视频高度       (默认 1080)
    GRABBER_COOKIES_BROWSER   从浏览器读 Cookie  (默认 关闭)
                              可选: "chrome", "firefox", "safari", "edge"
"""

import json
import os
import shlex
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

# ── 配置 ──────────────────────────────────────────────

PORT = int(os.environ.get("GRABBER_PORT", "7789"))
HOST = "127.0.0.1"
DOWNLOADS = Path(os.environ.get("GRABBER_DOWNLOADS", str(Path.home() / "Downloads")))
MAX_HEIGHT = int(os.environ.get("GRABBER_MAX_HEIGHT", "1080"))
PREFIX = os.environ.get("GRABBER_PREFIX", "VG_")  # 文件名前缀，方便识别工具下载的文件
COOKIES_BROWSER = os.environ.get("GRABBER_COOKIES_BROWSER", "").strip()
APP_NAME = "Video Grabber"
LOG_FILE = Path.home() / "Library" / "Logs" / "video-grabber.log"


def _detect_yt_dlp() -> str:
    """按优先级查找 yt-dlp。"""
    # 优先 nightly：视频站改接口时 nightly 修复最快
    for candidate in [
        shutil.which("yt-dlp-nightly"),
        str(Path.home() / ".local" / "bin" / "yt-dlp-nightly"),
        shutil.which("yt-dlp"),
        "/opt/homebrew/bin/yt-dlp",
        "/usr/local/bin/yt-dlp",
    ]:
        if candidate and Path(candidate).is_file():
            return candidate
    return "yt-dlp"


YT_DLP = os.environ.get("GRABBER_YT_DLP") or _detect_yt_dlp()


# ── 日志 & 通知 ───────────────────────────────────────

def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as f:
        f.write(f"{msg}\n")
    print(msg, flush=True)


def notify(title: str, message: str) -> None:
    """macOS 桌面通知。"""
    if not shutil.which("osascript"):
        return
    safe_title = title.replace('"', "'")
    safe_msg = message.replace('"', "'").replace("\n", " ")
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{safe_msg}" with title "{safe_title}"'],
            check=False, timeout=5,
        )
    except Exception as e:
        log(f"notify error: {e}")


# ── 下载核心 ──────────────────────────────────────────

def download(url: str) -> None:
    log(f"[start] {url}")
    notify(APP_NAME, f"开始下载: {url[:80]}")
    DOWNLOADS.mkdir(parents=True, exist_ok=True)

    output_tpl = str(DOWNLOADS / f"{PREFIX}%(title).160s [%(id)s].%(ext)s")
    fmt = (
        f"bv*[height<={MAX_HEIGHT}][ext=mp4]+ba[ext=m4a]/"
        f"b[height<={MAX_HEIGHT}][ext=mp4]/"
        f"bv*[height<={MAX_HEIGHT}]+ba/"
        f"b[height<={MAX_HEIGHT}]/best"
    )
    cmd = [
        YT_DLP,
        "--no-playlist",
        "--no-mtime",
        "-N", "4",
        "-f", fmt,
        "--merge-output-format", "mp4",
        "--replace-in-metadata", "title", r'[\\/:*?"<>|]', "_",
        "--output", output_tpl,
    ]
    if COOKIES_BROWSER:
        cmd += ["--cookies-from-browser", COOKIES_BROWSER]
    cmd.append(url)

    log("$ " + " ".join(shlex.quote(c) for c in cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        tail = (result.stdout + result.stderr).strip().splitlines()

        if result.returncode == 0:
            log(f"[done] {url}")
            # 尝试提取文件名
            filename = ""
            for line in reversed(tail):
                if "[download] Destination:" in line:
                    filename = line.split("Destination:", 1)[1].strip()
                    break
                if "has already been downloaded" in line:
                    filename = line.split("]", 1)[1].split(" has already")[0].strip()
                    break
                if "[Merger]" in line and '"' in line:
                    filename = line.split('"')[-2]
                    break
            short = Path(filename).name if filename else "下载完成"
            notify(f"{APP_NAME} ✅", short)
        else:
            log(f"[fail] {url} rc={result.returncode}")
            for line in tail[-10:]:
                log("  " + line)
            err = tail[-1] if tail else f"rc={result.returncode}"
            notify(f"{APP_NAME} ❌", err[:120])

    except subprocess.TimeoutExpired:
        log(f"[timeout] {url}")
        notify(f"{APP_NAME} ⏱", "下载超时（1小时）")
    except Exception as e:
        log(f"[error] {url}: {e}")
        notify(f"{APP_NAME} ❌", str(e)[:120])


# ── HTTP 服务 ─────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true,"service":"video-grabber"}')
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/download":
            self.send_response(404)
            self._cors()
            self.end_headers()
            return

        # 安全：拒绝网页 Origin 发起的请求
        origin = self.headers.get("Origin", "")
        if origin.startswith(("http://", "https://")):
            self.send_response(403)
            self._cors()
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"forbidden: web origins blocked")
            log(f"[blocked] origin={origin}")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8", "replace")
        try:
            data = json.loads(raw)
            url = data["url"]
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                raise ValueError("url must start with http(s)")
        except Exception as e:
            self.send_response(400)
            self._cors()
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"bad request: {e}".encode())
            return

        threading.Thread(target=download, args=(url,), daemon=True).start()

        self.send_response(202)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"queued":true}')

    def log_message(self, fmt, *args) -> None:
        log("http: " + (fmt % args))


# ── 启动 ──────────────────────────────────────────────

def main() -> None:
    log(f"{APP_NAME} daemon on http://{HOST}:{PORT}  (yt-dlp: {YT_DLP})")
    server = HTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("daemon stopped")
        server.shutdown()


if __name__ == "__main__":
    main()
