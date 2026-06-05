// Video Grabber — 点击工具栏图标，把当前页面 URL 发给本地 daemon 下载。

const DAEMON = "http://127.0.0.1:7789";
const APP = "Video Grabber";

chrome.action.onClicked.addListener(async (tab) => {
  // 只处理 http(s) 页面
  if (!tab?.url || !/^https?:/.test(tab.url)) {
    flashBadge("✕", "#c0392b");
    notify(APP, "当前页面不是 http(s) 页面，无法下载。");
    return;
  }

  flashBadge("…", "#666");

  try {
    const res = await fetch(`${DAEMON}/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: tab.url }),
    });

    if (res.status === 202) {
      flashBadge("✓", "#27ae60");
    } else {
      const txt = await res.text();
      flashBadge("!", "#e67e22");
      notify(APP, `服务端返回 ${res.status}: ${txt.slice(0, 200)}`);
    }
  } catch (e) {
    flashBadge("✕", "#c0392b");
    notify(APP, `无法连接本地服务 (${e.message})。请确认 daemon 在运行。`);
  }
});

function flashBadge(text, color) {
  chrome.action.setBadgeText({ text });
  chrome.action.setBadgeBackgroundColor({ color });
  setTimeout(() => chrome.action.setBadgeText({ text: "" }), 3500);
}

function notify(title, message) {
  chrome.notifications.create({
    type: "basic",
    iconUrl: "icon-128.png",
    title,
    message,
  });
}
