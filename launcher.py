"""热点聚合工作台 - 启动器（单窗口 GUI 版）"""
import os
import sys
import time
import webbrowser
import socket
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime

ROOT = Path(__file__).parent.resolve()
NODE_BIN = Path(r"C:\Users\blbnb\.workbuddy\binaries\node\versions\22.22.2")

# 进程句柄
backend_proc = None
frontend_proc = None

# 后端日志文件路径
LOG_DIR = ROOT / "backend" / "data"
LOG_FILE = LOG_DIR / "backend.log"


class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🔥 热点聚合工作台")
        self.root.geometry("700x550")
        self.root.minsize(600, 400)
        self.running = False

        # 创建 UI
        self.create_widgets()

        # 启动后台任务
        self.root.after(100, self.start_services)

        # 关闭时清理
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        # 顶部状态栏
        top = tk.Frame(self.root, bg="#1a1a2e", height=60)
        top.pack(fill=tk.X)
        top.pack_propagate(False)
        title = tk.Label(top, text="🔥 热点聚合工作台",
                        font=("Microsoft YaHei", 14, "bold"),
                        fg="white", bg="#1a1a2e")
        title.pack(side=tk.LEFT, padx=20, pady=15)

        # 状态文字
        self.status_label = tk.Label(top, text="🔄 启动中...",
                                     font=("Microsoft YaHei", 11),
                                     fg="#fbbf24", bg="#1a1a2e")
        self.status_label.pack(side=tk.RIGHT, padx=20)

        # 信息栏
        info_frame = tk.Frame(self.root)
        info_frame.pack(fill=tk.X, padx=15, pady=10)

        self.info_label = tk.Label(
            info_frame,
            text="",
            font=("Microsoft YaHei", 9),
            fg="#666",
            justify=tk.LEFT,
        )
        self.info_label.pack(anchor=tk.W)

        # 日志标题
        log_title = tk.Frame(self.root)
        log_title.pack(fill=tk.X, padx=15, pady=(5, 0))
        tk.Label(log_title, text="📋 后端日志",
                font=("Microsoft YaHei", 10, "bold")).pack(side=tk.LEFT)

        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(
            self.root,
            height=18,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 10))

        # 底部按钮栏
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        self.open_btn = tk.Button(
            btn_frame, text="🌐 在浏览器打开",
            command=self.open_browser,
            font=("Microsoft YaHei", 10),
            bg="#7c3aed", fg="white",
            relief=tk.FLAT, padx=20, pady=8, state=tk.DISABLED,
        )
        self.open_btn.pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_frame, text="📱 显示手机 IP",
            command=self.show_phone_ip,
            font=("Microsoft YaHei", 10),
            relief=tk.FLAT, padx=20, pady=8,
        ).pack(side=tk.LEFT, padx=8)

        tk.Button(
            btn_frame, text="🚪 退出",
            command=self.on_close,
            font=("Microsoft YaHei", 10),
            bg="#ef4444", fg="white",
            relief=tk.FLAT, padx=20, pady=8,
        ).pack(side=tk.RIGHT)

    def append_log(self, text):
        """追加日志到文本框"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def set_status(self, text, color="#fbbf24"):
        self.status_label.config(text=text, fg=color)

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
        """启动后端和前端（后台线程）"""
        self.running = True
        self.set_status("🔄 检查依赖...", "#fbbf24")
        threading.Thread(target=self._start_services_thread, daemon=True).start()

    def _start_services_thread(self):
        # 1. 配置 PATH
        if NODE_BIN.exists():
            os.environ["PATH"] = str(NODE_BIN) + os.pathsep + os.environ["PATH"]

        # 2. 检查 Python/Node
        node_v = subprocess.run(["node", "--version"], capture_output=True, text=True, shell=True).stdout.strip()
        self.append_log(f"[OK] Node.js: {node_v}")

        # 3. 安装后端依赖（静默）
        self.append_log("[INFO] 检查后端依赖...")
        subprocess.run(
            "pip install -r requirements.txt --quiet",
            cwd=ROOT / "backend", shell=True,
            capture_output=True,
        )

        # 4. 安装前端依赖
        if not (ROOT / "frontend" / "node_modules").exists():
            self.append_log("[INFO] 安装前端依赖...")
            subprocess.run("npm install", cwd=ROOT / "frontend", shell=True,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            self.append_log("[OK] 前端依赖已就绪")

        # 5. 启动后端
        self.set_status("🔄 启动后端...", "#fbbf24")
        self.append_log("[INFO] 启动后端（端口 8000）...")
        global backend_proc
        backend_proc = subprocess.Popen(
            [sys.executable, "run.py"],
            cwd=ROOT / "backend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        # 6. 等待后端就绪
        self.append_log("[INFO] 等待后端健康...")
        import urllib.request, urllib.error
        ready = False
        for i in range(30):
            time.sleep(1)
            try:
                req = urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=2)
                if req.status == 200:
                    ready = True
                    break
            except Exception:
                pass
            self.append_log(f"  ... {i+1}s")
        if ready:
            self.append_log("[OK] 后端就绪")
        else:
            self.append_log("[WARN] 后端启动超时，继续启动前端...")

        # 7. 启动前端
        self.set_status("🔄 启动前端...", "#fbbf24")
        self.append_log("[INFO] 启动前端（端口 5173）...")
        global frontend_proc
        frontend_proc = subprocess.Popen(
            ["cmd", "/c", "npm", "run", "dev", "--", "--host", "0.0.0.0"],
            cwd=ROOT / "frontend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        # 8. 等待前端就绪
        for i in range(30):
            time.sleep(1)
            try:
                req = urllib.request.urlopen("http://127.0.0.1:5173", timeout=2)
                if req.status == 200:
                    break
            except Exception:
                pass

        # 9. 全部就绪
        self.set_status("✅ 服务已就绪", "#10b981")
        self.open_btn.config(state=tk.NORMAL)

        # 显示手机 IP
        lan_ip = self.get_lan_ip()
        if lan_ip:
            phone_url = f"http://{lan_ip}:5173"
            self.info_label.config(
                text=f"💻 PC: http://localhost:5173\n📱 手机: {phone_url}\n\n日志会写入文件：{LOG_FILE}"
            )

        # 10. 自动打开浏览器
        self.append_log("[INFO] 打开浏览器...")
        webbrowser.open("http://localhost:5173")

        # 11. 启动日志监控线程
        threading.Thread(target=self._tail_log_file, daemon=True).start()

    def _tail_log_file(self):
        """实时跟踪日志文件"""
        if not LOG_FILE.exists():
            return
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(0, 2)  # 跳到末尾
            while self.running:
                line = f.readline()
                if line:
                    self.append_log(line.rstrip())
                else:
                    time.sleep(1)

    def open_browser(self):
        webbrowser.open("http://localhost:5173")

    def show_phone_ip(self):
        ip = self.get_lan_ip()
        if ip:
            import tkinter.messagebox as mb
            mb.showinfo("手机访问", f"手机浏览器打开：\nhttp://{ip}:5173\n\n确保手机和电脑在同一 WiFi。")

    def on_close(self):
        import tkinter.messagebox as mb
        if not mb.askyesno("退出", "确认退出热点聚合工作台？\n所有后台服务将被关闭。"):
            return
        self.running = False
        self.append_log("[INFO] 关闭服务...")
        try:
            if frontend_proc:
                frontend_proc.terminate()
            if backend_proc:
                # 调用后端的退出 API（会清理所有进程）
                import urllib.request
                urllib.request.urlopen("http://127.0.0.1:8000/api/system/exit", timeout=2)
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()