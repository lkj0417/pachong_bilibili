const $ = (selector) => document.querySelector(selector);
const openTaskLogs = new Set();
let pauseTaskRefresh = false;

function selectionInTasks() {
  const selection = window.getSelection();
  if (!selection || !selection.toString()) return false;
  const container = $("#tasks");
  return Boolean(container && selection.anchorNode && container.contains(selection.anchorNode));
}

function applyTheme(theme) {
  document.body.dataset.theme = theme;
  localStorage.setItem("theme", theme);
}

function initTheme() {
  const saved = localStorage.getItem("theme") || "dark";
  const select = $("#theme-select");
  if (select) select.value = saved;
  applyTheme(saved);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || "请求失败");
  }
  return data;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / Math.pow(1024, index)).toFixed(index ? 1 : 0)} ${units[index]}`;
}

function setPill(id, ok, text) {
  const el = $(id);
  el.textContent = text;
  el.className = `pill ${ok ? "ok" : "bad"}`;
}

function setTextIfExists(selector, text) {
  const el = $(selector);
  if (el) el.textContent = text;
}

async function loadHealth() {
  try {
    const data = await api("/api/health");
    setPill("#yt-dlp-status", data.yt_dlp_ok, `yt-dlp: ${data.yt_dlp_ok ? "已就绪" : "未找到"}`);
    setPill("#cookies-status", data.cookies_ok, `cookies: ${data.cookies_ok ? "已就绪" : "未找到"}`);
    setPill("#ffmpeg-status", data.ffmpeg_ok, `ffmpeg: ${data.ffmpeg_ok ? "已就绪" : "未配置"}`);
  } catch (error) {
    console.error(error);
  }
}

async function loadConfig() {
  try {
    const data = await api("/api/config");
    const form = $("#config-form");
    form.cookies_path.value = data.config.cookies_path || "";
    form.output_dir.value = data.config.output_dir || "";
    form.ffmpeg_location.value = data.config.ffmpeg_location || "";
    form.yt_dlp_path.value = data.config.yt_dlp_path || "";
    form.auto_organize.checked = data.config.auto_organize !== false;
  } catch (error) {
    console.error(error);
  }
}

function cookieStatusText(status) {
  if (status === "ok") return "正常";
  if (status === "expired") return "已过期";
  return "缺失";
}

function firstUrlFromTextarea() {
  const line = $("#urls")
    .value.split("\n")
    .map((item) => item.trim())
    .find(Boolean);
  return line || "";
}

async function checkCookies() {
  const msg = $("#cookies-check-msg");
  msg.textContent = "检查中…";
  msg.style.color = "var(--muted)";
  try {
    const data = await api("/api/cookies/check", {
      method: "POST",
      body: JSON.stringify({ url: firstUrlFromTextarea() }),
    });
    const parts = [`文件: ${data.exists ? "已找到" : "未找到"}`];
    if (data.count) parts.push(`共 ${data.count} 条`);
    if (data.key_cookies) {
      const detail = Object.entries(data.key_cookies)
        .map(([key, status]) => `${key}: ${cookieStatusText(status)}`)
        .join("，");
      parts.push(detail);
    }
    if (data.live) {
      if (data.live.ok) {
        parts.push(data.live.logged_in ? `在线校验: 已登录（${data.live.uname || "未知用户"}）` : "在线校验: 未登录");
      } else {
        parts.push("在线校验: 无法连接");
      }
    }
    if (data.download_check) {
      parts.push(`下载测试: ${data.download_check.message || ""}`);
    }
    msg.textContent = `${parts.join("；")}。结论: ${data.summary || ""}`;

    const usable = data.usable === true;
    msg.style.color = usable ? "var(--green)" : "var(--red)";
    setPill("#cookies-status", usable, `cookies: ${usable ? "可用" : "不可用"}`);
  } catch (error) {
    msg.textContent = error.message;
    msg.style.color = "var(--red)";
  }
}

const STATUS_TEXT = {
  pending: "等待",
  running: "下载中",
  done: "完成",
  error: "失败",
  skipped: "跳过",
};

function renderTasks(tasks) {
  const container = $("#tasks");
  const count = $("#task-count");

  const scrollPositions = {};
  container.querySelectorAll("details.task-log[open]").forEach((details) => {
    const pre = details.querySelector("pre");
    const taskId = details.dataset.taskId;
    if (pre && taskId) {
      scrollPositions[taskId] = pre.scrollTop;
    }
  });

  if (!tasks.length) {
    container.innerHTML = '<div class="empty">暂无任务</div>';
    count.textContent = "";
    setTextIfExists("#task-summary", "0");
    return;
  }

  count.textContent = `${tasks.length} 个任务`;
  setTextIfExists("#task-summary", String(tasks.length));
  container.innerHTML = tasks
    .slice()
    .reverse()
    .map((task) => {
      const status = task.status || "pending";
      const percent = Math.round(Number(task.progress) || 0);
      return `
        <div class="task ${status}">
          <div class="task-head">
            <span class="badge ${status}">${STATUS_TEXT[status] || status}</span>
            <span class="task-url" title="${escapeHtml(task.url)}">${escapeHtml(task.url)}</span>
          </div>
          <div class="progress"><div class="bar" data-progress="${percent}"></div></div>
          <div class="task-msg">${escapeHtml(task.message || "")}</div>
          ${
            task.log && task.log.length
              ? `<div class="task-log-row"><details class="task-log" data-task-id="${task.id}" ${openTaskLogs.has(task.id) ? "open" : ""}><summary>查看日志</summary><pre>${escapeHtml(task.log.join("\n"))}</pre></details><button type="button" class="copy-log" data-copy-id="${task.id}">复制日志</button></div>`
              : ""
          }
        </div>
      `;
    })
    .join("");

  container.querySelectorAll(".bar[data-progress]").forEach((bar) => {
    bar.style.width = `${bar.dataset.progress}%`;
  });

  container.querySelectorAll("details.task-log").forEach((details) => {
    const pre = details.querySelector("pre");
    const taskId = details.dataset.taskId;
    if (pre && taskId && scrollPositions[taskId] !== undefined) {
      pre.scrollTop = scrollPositions[taskId];
    }
    details.addEventListener("toggle", () => {
      if (!taskId) return;
      if (details.open) {
        openTaskLogs.add(taskId);
      } else {
        openTaskLogs.delete(taskId);
      }
    });
  });

  container.querySelectorAll(".copy-log").forEach((button) => {
    button.addEventListener("click", async () => {
      const task = tasks.find((item) => item.id === button.dataset.copyId);
      if (!task || !task.log?.length) return;
      try {
        await navigator.clipboard.writeText(task.log.join("\n"));
      } catch {
        const textarea = document.createElement("textarea");
        textarea.value = task.log.join("\n");
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
      }
      button.textContent = "已复制";
      setTimeout(() => {
        button.textContent = "复制日志";
      }, 1200);
    });
  });
}

async function loadTasks() {
  try {
    const data = await api("/api/tasks");
    renderTasks(data.tasks);
  } catch (error) {
    console.error(error);
  }
}

const KIND_TEXT = {
  video: "视频",
  audio: "音频",
  text: "文本",
  other: "其他",
};

function renderFiles(files) {
  const container = $("#files");
  setTextIfExists("#file-summary", String(files.length));
  if (!files.length) {
    container.innerHTML = '<div class="empty">暂无文件</div>';
    return;
  }

  container.innerHTML = files
    .map(
      (file) => `
        <div class="file-row">
          <span class="kind ${file.kind}">${KIND_TEXT[file.kind] || "其他"}</span>
          <span class="file-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
          <span class="file-meta">${formatBytes(file.size)} · ${escapeHtml(file.modified)}</span>
        </div>
      `
    )
    .join("");
}

async function loadFiles() {
  try {
    const data = await api("/api/files");
    renderFiles(data.files);
  } catch (error) {
    console.error(error);
  }
}

async function loadLog() {
  try {
    const data = await api("/api/log");
    const container = $("#log");
    $("#log-count").textContent = data.count ? `${data.count} 条` : "";
    setTextIfExists("#log-summary", String(data.count || 0));
    if (!data.entries.length) {
      container.innerHTML = '<div class="empty">暂无下载记录</div>';
      return;
    }
    container.innerHTML = data.entries
      .map(
        (url, index) => `
          <div class="log-row">
            <span class="file-name" title="${escapeHtml(url)}">${index + 1}. ${escapeHtml(url)}</span>
          </div>
        `
      )
      .join("");
  } catch (error) {
    console.error(error);
  }
}

async function startDownload() {
  const textarea = $("#urls");
  const quality = $("#quality").value;
  const downloadPlaylist = $("#download-playlist").checked;
  const concurrentFragments = parseInt($("#fragments").value, 10) || 8;
  const urls = textarea.value.split("\n").map((line) => line.trim()).filter(Boolean);
  if (!urls.length) {
    alert("请先填写至少一个视频 URL");
    return;
  }

  const button = $("#start-download");
  button.disabled = true;
  button.textContent = "提交中…";
  try {
    await api("/api/download", {
      method: "POST",
      body: JSON.stringify({
        urls,
        quality,
        download_playlist: downloadPlaylist,
        concurrent_fragments: concurrentFragments,
      }),
    });
    textarea.value = "";
    await loadTasks();
    await loadLog();
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "开始下载";
  }
}

async function organizeFiles() {
  const button = $("#organize");
  button.disabled = true;
  try {
    const data = await api("/api/organize", { method: "POST", body: "{}" });
    alert(data.message || "整理完成");
    await loadFiles();
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
  }
}

async function mergeMedia() {
  const button = $("#merge-media");
  button.disabled = true;
  try {
    const data = await api("/api/merge", { method: "POST", body: "{}" });
    const detail = data.results?.length
      ? data.results.map((item) => `${item.status === "done" ? "✅" : "⚠️"} ${item.name}`).join("\n")
      : "没有需要合并的文件";
    alert(`合并完成：${data.merged || 0} 个\n${detail}`);
    await loadFiles();
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
  }
}

async function clearTasks() {
  try {
    await api("/api/tasks/clear", { method: "POST", body: "{}" });
    await loadTasks();
  } catch (error) {
    alert(error.message);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initTheme();

  $("#theme-select").addEventListener("change", (event) => {
    applyTheme(event.target.value);
  });

  loadHealth();
  loadConfig();
  loadTasks();
  loadFiles();
  loadLog();

  $("#config-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = {
      cookies_path: form.cookies_path.value.trim(),
      output_dir: form.output_dir.value.trim(),
      ffmpeg_location: form.ffmpeg_location.value.trim(),
      yt_dlp_path: form.yt_dlp_path.value.trim(),
      auto_organize: form.auto_organize.checked,
    };
    try {
      await api("/api/config", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      const message = $("#config-msg");
      message.textContent = "配置已保存";
      message.style.color = "var(--green)";
      await loadHealth();
      await loadFiles();
    } catch (error) {
      const message = $("#config-msg");
      message.textContent = error.message;
      message.style.color = "var(--red)";
    }
  });

  $("#check-cookies").addEventListener("click", checkCookies);
  $("#start-download").addEventListener("click", startDownload);
  $("#refresh-files").addEventListener("click", loadFiles);
  $("#refresh-files-2").addEventListener("click", loadFiles);
  $("#organize").addEventListener("click", organizeFiles);
  $("#merge-media").addEventListener("click", mergeMedia);
  $("#clear-tasks").addEventListener("click", clearTasks);

  $("#tasks").addEventListener("mousedown", () => {
    pauseTaskRefresh = true;
  });

  document.addEventListener("mouseup", () => {
    setTimeout(() => {
      pauseTaskRefresh = false;
    }, 300);
  });

  setInterval(() => {
    if (pauseTaskRefresh || selectionInTasks()) return;
    loadTasks();
  }, 1500);
  setInterval(loadHealth, 5000);
});
