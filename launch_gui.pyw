"""热点聚合工作台 - 启动器（高清单窗口 GUI 版，无控制台）"""
import os
import sys
import time
import webbrowser
import socket
import subprocess
import threading
from pathlib import Path
from datetime import datetime

# ====== 高 DPI 支持（防模糊）======
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

import tkinter as tk
from tkinter import scrolledtext

ROOT = Path(__file__).parent.resolve()
NODE_BIN = Path(r"C:\Users\blbnb\.workbuddy\binaries\node\versions\22.22.2")

backend_proc = None
frontend_proc = None


class LauncherApp:
    BG = "#0f0f1a"
    CARD = "#1a1a2e"
    ACCENT = "#7c3aed"
    TEXT = "#e0e0e0"
    MUTED = "#888899"
    GREEN = "#10b981"
    YELLOW = "#fbbf24"
    FONT = ("Microsoft YaHei", 10)
    FONT_SM = ("Microsoft YaHei", 9)
    FONT_MONO = ("Consolas", 9)

    def __init__(self, root):
        self.root = root
        self.root.title("🔥 热点聚合工作台")
        self.root.geometry("800x620")
        self.root.minsize(680, 500)
        self.running = False

        self._setup_style()
        self.create_widgets()
        self.root.after(200, self.start_services)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_style(self):
        self.root.configure(bg=self.BG)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

    def create_widgets(self):
        # === 顶部标题栏 ===
        header = tk.Frame(self.root, bg=self.BG)
        header.pack(fill=tk.X, padx=24, pady=(24, 0))

        tk.Label(header, text="🔥", font=("Microsoft YaHei", 28),
                 bg=self.BG, fg=self.ACCENT).pack(side=tk.LEFT, padx=(0, 8))

        title_frame = tk.Frame(header, bg=self.BG)
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(title_frame, text="热点聚合工作台",
                font=("Microsoft YaHei", 16, "bold"),
                bg=self.BG, fg="white", anchor=tk.W).pack(fill=tk.X)
        tk.Label(title_frame, text="多平台热点聚合 · AI 内容生成 · 本地存储",
                font=self.FONT_SM, bg=self.BG, fg=self.MUTED,
                anchor=tk.W).pack(fill=tk.X, pady=(2, 0))

        # 状态指示灯
        self.status_dot = tk.Canvas(header, width=14, height=14,
                                     bg=self.BG, highlightthickness=0)
        self.status_dot.pack(side=tk.RIGHT, padx=(0, 6))
        self.dot = self.status_dot.create_oval(2, 2, 12, 12,
                                                fill=self.YELLOW, outline="")

        self.status_label = tk.Label(header, text="启动中...",
                                     font=self.FONT,
                                     bg=self.BG, fg=self.YELLOW)
        self.status_label.pack(side=tk.RIGHT, padx=(0, 8))

        # === 信息卡片 ===
        info_frame = tk.Frame(self.root, bg=self.CARD,
                              highlightbackground="#2a2a3e",
                              highlightthickness=1)
        info_frame.pack(fill=tk.X, padx=24, pady=(16, 0))

        self.info_text = tk.Text(info_frame, height=3,
                                  font=self.FONT_MONO,
                                  bg=self.CARD, fg=self.TEXT,
                                  relief=tk.FLAT, bd=0,
                                  padx=14, pady=12)
        self.info_text.pack(fill=tk.X)
        self.info_text.insert(tk.END, "等待启动...")
        self.info_text.config(state=tk.DISABLED)

        # === 日志标题栏 ===
        log_header = tk.Frame(self.root, bg=self.BG)
        log_header.pack(fill=tk.X, padx=24, pady=(12, 4))
        tk.Label(log_header, text="📋 运行日志",
                font=("Microsoft YaHei", 11, "bold"),
                bg=self.BG, fg=self.TEXT).pack(side=tk.LEFT)

        # === 日志区域 ===
        self.log_text = scrolledtext.ScrolledText(
            self.root,
            font=self.FONT_MONO,
            bg="#0a0a14",
            fg="#c0c0d0",
            insertbackground="white",
            state=tk.DISABLED,
            relief=tk.FLAT,
            bd=0,
            highlightbackground="#2a2a3e",
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 12))

        # === 底部按钮栏 ===
        btn_bar = tk.Frame(self.root, bg=self.BG)
        btn_bar.pack(fill=tk.X, padx=24, pady=(0, 20))

        tk.Button(btn_bar, text="🌐 在浏览器打开",
                  command=self.open_browser,
                  font=self.FONT, bg=self.ACCENT, fg="white",
                  relief=tk.FLAT, padx=22, pady=8, cursor="hand2",
                  ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(btn_bar, text="📱 手机访问",
                  command=self.show_phone_ip,
                  font=self.FONT, bg="#2a2a3e", fg=self.TEXT,
                  relief=tk.FLAT, padx=22, pady=8, cursor="hand2",
                  ).pack(side=tk.LEFT, padx=8)

        tk.Button(btn_bar, text="🚪 退出",
                  command=self.on_close,
                  font=self.FONT, bg="#dc2626", fg="white",
                  relief=tk.FLAT, padx=22, pady=8, cursor="hand2",
                  ).pack(side=tk.RIGHT)

    def update_info(self, text):
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert(tk.END, text)
        self.info_text.config(state=tk.DISABLED)

    def append_log(self, text):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def set_status(self, text, color=YELLOW):
        self.status_label.config(text=text, fg=color)
        color_map = {self.GREEN: self.GREEN, self.YELLOW: self.YELLOW, "#10b981": self.GREEN}
        fill = color_map.get(color, self.YELLOW)
        self.status_dot.itemconfig(self.dot, fill=fill)

    def get_lan_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None

    def start_services(self):
        self.running = True
        self.append_log("[INFO] 开始启动服务...")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        # 1. PATH
        if NODE_BIN.exists():
            os.environ["PATH"] = str(NODE_BIN) + os.pathsep + os.environ["PATH"]

        # 2. Python/Node
        node_v = subprocess.run(["node", "--version"], capture_output=True,
                                 text=True, shell=True).stdout.strip()
        self.append_log(f"[OK] Node.js {node_v}")
        self.append_log(f"[OK] Python {sys.version.split()[0]}")

        # 3. 后端依赖
        self.append_log("[INFO] 检查后端依赖...")
        subprocess.run("pip install -r requirements.txt --quiet",
                       cwd=ROOT / "backend", shell=True, capture_output=True)

        # 4. 前端依赖
        if not (ROOT / "frontend" / "node_modules").exists():
            self.append_log("[INFO] 安装前端依赖...")
            subprocess.run("npm install", cwd=ROOT / "frontend", shell=True,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            self.append_log("[OK] 前端依赖已就绪")

        # 5. 启动后端
        self.set_status("启动后端...")
        self.append_log("[INFO] 后端启动中（端口 8000）...")
        global backend_proc
        backend_proc = subprocess.Popen(
            [sys.executable, "run.py"],
            cwd=ROOT / "backend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        # 6. 等待后端
        self.append_log("[INFO] 等待后端就绪...")
        import urllib.request, urllib.error
        ready = False
        for i in range(30):
            time.sleep(1)
            try:
                r = urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=2)
                if r.status == 200:
                    ready = True
                    break
            except Exception:
                pass
            if i % 5 == 0:
                self.append_log(f"  ... {i+1}s")

        if ready:
            self.append_log("[OK] 后端就绪")
        else:
            self.append_log("[WARN] 后端启动超时，继续启动前端")

        # 7. 启动前端
        self.set_status("启动前端...")
        self.append_log("[INFO] 前端启动中（端口 5173）...")
        global frontend_proc
        frontend_proc = subprocess.Popen(
            ["cmd", "/c", "npm", "run", "dev", "--", "--host", "0.0.0.0"],
            cwd=ROOT / "frontend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        # 8. 等待前端
        for i in range(30):
            time.sleep(1)
            try:
                r = urllib.request.urlopen("http://127.0.0.1:5173", timeout=2)
                if r.status == 200:
                    break
            except Exception:
                pass

        # 9. 完成
        self.set_status("服务已就绪 🚀", self.GREEN)
        self.update_info("💻 PC:  http://localhost:5173")
        lan_ip = self.get_lan_ip()
        if lan_ip:
            self.update_info(f"💻 PC:  http://localhost:5173\n📱 手机: http://{lan_ip}:5173\n📋 日志: 设置页 → 后端日志")

        webbrowser.open("http://localhost:5173")

        # 10. 日志尾随
        self._tail_log()

    def _tail_log(self):
        log_file = ROOT / "backend" / "data" / "backend.log"
        if not log_file.exists():
            return
        def tail():
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, 2)
                while self.running:
                    line = f.readline()
                    if line:
                        self.root.after(0, self.append_log, line.rstrip())
                    else:
                        time.sleep(1)
        threading.Thread(target=tail, daemon=True).start()

    def open_browser(self):
        webbrowser.open("http://localhost:5173")

    def show_phone_ip(self):
        ip = self.get_lan_ip()
        if ip:
            import tkinter.messagebox as mb
            mb.showinfo("手机访问", f"手机浏览器打开：\nhttp://{ip}:5173\n\n确保手机和电脑在同一 WiFi。")

    def on_close(self):
        import tkinter.messagebox as mb
        if not mb.askyesno("确认退出", "确认退出热点聚合工作台？"):
            return
        self.running = False
        self.append_log("[INFO] 正在关闭服务...")
        try:
            if frontend_proc:
                frontend_proc.terminate()
            if backend_proc:
                import urllib.request
                urllib.request.urlopen("http://127.0.0.1:8000/api/system/exit", timeout=2)
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    LauncherApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()