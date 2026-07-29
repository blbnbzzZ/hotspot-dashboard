"""热点聚合工作台 - 单文件打包入口（PyInstaller 使用）"""
import os
import sys
import time
import webbrowser
import socket
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext
from pathlib import Path

# 判断是否在 exe 中运行
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的路径
    BASE_DIR = Path(sys._MEIPASS)
    IS_EXE = True
else:
    BASE_DIR = Path(__file__).parent.resolve()
    IS_EXE = False

# ========== 单实例检查（仅 exe 模式）==========
_mutex = None
if IS_EXE and sys.platform == "win32":
    try:
        import ctypes
        from ctypes import wintypes
        # 创建命名互斥锁，全局唯一
        _mutex = ctypes.windll.kernel32.CreateMutexW(
            None, False, "Global\\HotspotDashboardMutex_v1"
        )
        ERROR_ALREADY_EXISTS = 183
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            ctypes.windll.kernel32.CloseHandle(_mutex)
            # 弹出提示后退出
            import tkinter.messagebox as mb
            try:
                root = tk.Tk()
                root.withdraw()
                mb.showwarning("已运行", "热点聚合工作台已在运行！\n请检查任务栏或系统托盘。")
                root.destroy()
            except:
                pass
            sys.exit(0)
    except Exception:
        pass

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

backend_proc = None


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return None


class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🔥 热点聚合工作台")
        self.root.geometry("800x620")
        self.root.minsize(680, 500)
        self.running = True
        self._setup_style()
        self._create_widgets()
        self.root.after(200, self._start)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_style(self):
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except:
                pass
        self.root.configure(bg=BG)

    def _create_widgets(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill=tk.X, padx=24, pady=(24, 0))

        tk.Label(header, text="🔥", font=("Microsoft YaHei", 28),
                 bg=BG, fg=ACCENT).pack(side=tk.LEFT, padx=(0, 8))

        tf = tk.Frame(header, bg=BG)
        tf.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(tf, text="热点聚合工作台",
                font=("Microsoft YaHei", 16, "bold"),
                bg=BG, fg="white", anchor=tk.W).pack(fill=tk.X)
        tk.Label(tf, text="多平台热点聚合 · AI 内容生成 · 本地存储",
                font=FONT_SM, bg=BG, fg=MUTED, anchor=tk.W).pack(fill=tk.X, pady=(2, 0))

        # ✕ 关闭按钮
        tk.Button(header, text="✕", command=self._on_close,
                  font=("Arial", 14, "bold"),
                  bg=BG, fg=MUTED, relief=tk.FLAT, cursor="hand2",
                  activebackground="#dc2626", activeforeground="white",
                  width=3, height=1, bd=0
                  ).pack(side=tk.RIGHT, padx=(0, 8), pady=12)

        self.status_dot = tk.Canvas(header, width=14, height=14,
                                     bg=BG, highlightthickness=0)
        self.status_dot.pack(side=tk.RIGHT, padx=(0, 6))
        self.dot = self.status_dot.create_oval(2, 2, 12, 12, fill=YELLOW, outline="")
        self.status_label = tk.Label(header, text="启动中...",
                                     font=FONT, bg=BG, fg=YELLOW)
        self.status_label.pack(side=tk.RIGHT, padx=(0, 8))

        # 信息卡片
        iframe = tk.Frame(self.root, bg=CARD, highlightbackground="#2a2a3e", highlightthickness=1)
        iframe.pack(fill=tk.X, padx=24, pady=(16, 0))
        self.info_text = tk.Text(iframe, height=3, font=FONT_MONO,
                                  bg=CARD, fg=TEXT, relief=tk.FLAT, bd=0, padx=14, pady=12)
        self.info_text.pack(fill=tk.X)
        self.info_text.insert(tk.END, "正在准备...")
        self.info_text.config(state=tk.DISABLED)

        # 日志
        lh = tk.Frame(self.root, bg=BG)
        lh.pack(fill=tk.X, padx=24, pady=(12, 4))
        tk.Label(lh, text="📋 运行日志", font=("Microsoft YaHei", 11, "bold"),
                bg=BG, fg=TEXT).pack(side=tk.LEFT)

        self.log_text = scrolledtext.ScrolledText(
            self.root, font=FONT_MONO, bg="#0a0a14", fg="#c0c0d0",
            insertbackground="white", state=tk.DISABLED,
            relief=tk.FLAT, bd=0, highlightbackground="#2a2a3e",
            highlightthickness=1, padx=12, pady=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 12))

        # 底部按钮
        btn_bar = tk.Frame(self.root, bg=BG)
        btn_bar.pack(fill=tk.X, padx=24, pady=(0, 20))
        tk.Button(btn_bar, text="🌐 在浏览器打开",
                  command=lambda: webbrowser.open("http://localhost:8000"),
                  font=FONT, bg=ACCENT, fg="white",
                  relief=tk.FLAT, padx=22, pady=8, cursor="hand2"
                  ).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(btn_bar, text="📱 手机访问",
                  command=self._show_phone,
                  font=FONT, bg="#2a2a3e", fg=TEXT,
                  relief=tk.FLAT, padx=22, pady=8, cursor="hand2"
                  ).pack(side=tk.LEFT, padx=8)
        tk.Button(btn_bar, text="🚪 退出",
                  command=self._on_close,
                  font=FONT, bg="#dc2626", fg="white",
                  relief=tk.FLAT, padx=22, pady=8, cursor="hand2"
                  ).pack(side=tk.RIGHT)

    def log(self, text):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def status(self, text, color=YELLOW):
        self.status_label.config(text=text, fg=color)
        self.status_dot.itemconfig(self.dot, fill=color)

    def info(self, text):
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert(tk.END, text)
        self.info_text.config(state=tk.DISABLED)

    def _start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        self.status("启动后端...")
        self.log("[INFO] 启动中...")

        # 如果端口 8000 被占用，先尝试杀掉占用者（防止之前的残留进程锁住端口）
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", 8000)) == 0:
                self.log("[WARN] 端口 8000 被占用，尝试清理...")
                subprocess.run(
                    'for /f "tokens=5" %%a in (\'netstat -aon ^| findstr :8000\') do taskkill /F /PID %%a',
                    shell=True, capture_output=True, timeout=5
                )
                time.sleep(1)
            sock.close()
        except:
            pass

        backend_dir = BASE_DIR / "backend" if not IS_EXE else BASE_DIR

        # auto-install deps (only in dev mode)
        if not IS_EXE:
            self.log("[INFO] 安装后端依赖...")
            subprocess.run("pip install -r requirements.txt --quiet",
                           cwd=BASE_DIR / "backend", shell=True, capture_output=True)

        global backend_proc
        self.log("[INFO] 启动后端（端口 8000）")
        python_exe = sys.executable if not IS_EXE else sys.executable
        backend_proc = subprocess.Popen(
            [python_exe, "-m", "uvicorn", "app.main:app",
             "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"],
            cwd=backend_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        # 等待后端
        import urllib.request, urllib.error
        for i in range(30):
            time.sleep(1)
            try:
                r = urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=2)
                if r.status == 200:
                    break
            except:
                pass
            if i % 5 == 0:
                self.log(f"  ... {i+1}s")

        self.status("服务已就绪 🚀", GREEN)
        ip = get_lan_ip()
        phone = f"📱 手机: http://{ip}:8000" if ip else ""
        self.info(f"💻 PC:  http://localhost:8000\n{phone}")
        webbrowser.open("http://localhost:8000")

        # 尾随日志文件
        self._tail_log()

    def _tail_log(self):
        log_file = BASE_DIR / "backend" / "data" / "backend.log"
        if not log_file.exists():
            return
        def tail():
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, 2)
                while self.running:
                    line = f.readline()
                    if line:
                        self.root.after(0, self.log, line.rstrip())
                    else:
                        time.sleep(1)
        threading.Thread(target=tail, daemon=True).start()

    def _show_phone(self):
        ip = get_lan_ip()
        if ip:
            import tkinter.messagebox as mb
            mb.showinfo("手机访问", f"手机浏览器打开：\nhttp://{ip}:8000\n\n确保在同一 WiFi。")

    def _on_close(self):
        import tkinter.messagebox as mb
        if not mb.askyesno("确认退出", "确认退出热点聚合工作台？\n所有服务将被关闭。"):
            return
        self.running = False
        self.log("[INFO] 正在关闭服务...")
        # 关闭浏览器
        for browser in ["chrome", "msedge"]:
            subprocess.run(
                f'taskkill /F /IM {browser}.exe /FI "WINDOWTITLE eq *localhost*"',
                shell=True, capture_output=True, timeout=3
            )
        # 强杀后端（含所有子进程）
        global backend_proc
        if backend_proc:
            try:
                # 在 exe 模式下用 taskkill 杀整棵进程树
                if IS_EXE and sys.platform == "win32":
                    subprocess.run(
                        f'taskkill /F /T /PID {backend_proc.pid}',
                        shell=True, capture_output=True, timeout=5
                    )
                else:
                    backend_proc.terminate()
                    backend_proc.wait(3)
            except Exception:
                pass
        # 等待 1 秒确保进程完全释放
        time.sleep(1)
        # 释放互斥锁
        if _mutex and sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(_mutex)
            except:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    LauncherApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()