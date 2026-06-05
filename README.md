# Video Grabber

一键下载当前页面视频到 `~/Downloads`。Chrome 扩展 + 本地 yt-dlp 服务。

支持 YouTube、Bilibili、TikTok、Twitter/X、Vimeo 等 **1800+** 网站。

## 工作原理

```
Chrome 扩展（点击图标）
    ↓ POST 当前页面 URL
本地 Python 服务（127.0.0.1:7789）
    ↓ 调用 yt-dlp
下载到 ~/Downloads + macOS 通知
```

## 前置条件

- macOS
- Chromium 内核浏览器（Chrome / Edge / Arc / Brave）
- Python 3
- yt-dlp：`brew install yt-dlp`
- ffmpeg：`brew install ffmpeg`

## 安装

```bash
git clone https://github.com/huangbin-ai/video-grabber.git
cd video-grabber
./scripts/install.sh
```

然后加载 Chrome 扩展：

1. 打开 `chrome://extensions/`
2. 右上角打开「开发者模式」
3. 点「加载已解压的扩展程序」
4. 选择本项目的 `extension` 文件夹
5. 固定扩展图标到工具栏

## 使用

在任何视频页面，点击工具栏上的 Video Grabber 图标，视频自动下载到 `~/Downloads`。

下载的文件会带 `VG_` 前缀，方便识别。

## 配置

通过环境变量配置（在运行 `install.sh` 前设置）：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `GRABBER_PORT` | 监听端口 | `7789` |
| `GRABBER_DOWNLOADS` | 下载目录 | `~/Downloads` |
| `GRABBER_MAX_HEIGHT` | 最大视频高度 | `1080` |
| `GRABBER_PREFIX` | 文件名前缀 | `VG_` |
| `GRABBER_COOKIES_BROWSER` | 从浏览器读 Cookie | 关闭 |
| `GRABBER_YT_DLP` | yt-dlp 路径 | 自动检测 |

例如下载会员视频：

```bash
export GRABBER_COOKIES_BROWSER=chrome
./scripts/install.sh
```

## 卸载

```bash
./scripts/uninstall.sh
```

Chrome 扩展在 `chrome://extensions/` 手动移除。

## 安全

- 服务只绑定 `127.0.0.1`，外部不可访问
- 拒绝带 `Origin` 头的请求，防止网页恶意触发下载
- URL 必须是 `http(s)` 协议

## 致谢

架构参考 [xiaoer-videolab](https://github.com/Jane-xiaoer/xiaoer-videolab)，底层基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp)。

## License

MIT
