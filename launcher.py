"""
热点聚合工作台 - 启动器 (Python版)
绕过 Windows .bat 兼容性问题
"""
import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
NODE_BIN = Path(r"C:\Users\blbnb\.workbuddy\binaries\node\versions\22.22.2")

def setup_path():
    """把 Node.js 加到当前进程 PATH"""
    if NODE_BIN.exists():
        os.environ["PATH"] = str(NODE_BIN) + os.pathsep + os.environ["PATH"]
        print(f"[OK] Added Node.js to PATH: {NODE_BIN}")

def check_deps():
    """检查依赖"""
    print("\n[1/3] Checking dependencies...")

    # Python
    print(f"  Python: {sys.version.split()[0]}")

    # Node
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, shell=True)
        print(f"  Node:   {result.stdout.strip()}")
    except Exception as e:
        print(f"  [FAIL] Node not found: {e}")
        return False

    # npm
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True, shell=True)
        print(f"  npm:    {result.stdout.strip()}")
    except Exception as e:
        print(f"  [FAIL] npm not found: {e}")
        return False

    # Frontend deps
    nm = ROOT / "frontend" / "node_modules"
    if not nm.exists():
        print("  [INFO] Installing frontend dependencies...")
        subprocess.run("npm install", cwd=ROOT / "frontend", shell=True)

    return True

def get_lan_ip():
    """获取本机局域网 IP（手机访问用）"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 不需要真正连接，只用来获取本机 IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def start_service(name, cwd, cmd, port):
    """在新窗口中启动一个服务"""
    print(f"\n[Start] {name} on port {port}...")
    # 构建命令 - 在新窗口运行，保持窗口打开以便看错误
    full_cmd = f'start "{name}-{port}" cmd /k "cd /d {cwd} && {cmd}"'
    subprocess.Popen(full_cmd, shell=True)
    return True

def main():
    print("=" * 60)
    print("  Hotspot Dashboard - One-Click Starter")
    print("=" * 60)

    setup_path()

    if not check_deps():
        print("\n[FAIL] Dependencies missing. See errors above.")
        input("\nPress Enter to exit...")
        return 1

    # 启动后端
    backend_dir = ROOT / "backend"
    start_service("Backend", str(backend_dir), "python run.py", 8000)

    # 等待后端真正就绪（健康检查）
    print("\n[等待] 检查后端健康状态...")
    import urllib.request, urllib.error
    ready = False
    for i in range(20):
        time.sleep(1)
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=2)
            if req.status == 200:
                print(f"  ✓ 后端就绪 ({i+1}秒)")
                ready = True
                break
        except (urllib.error.URLError, ConnectionError):
            pass
    if not ready:
        print("  ⚠ 后端 20 秒内未就绪，仍继续启动前端")

    # 启动前端 - 添加 --host 0.0.0.0 让手机/局域网设备可以访问
    frontend_dir = ROOT / "frontend"
    start_service("Frontend", str(frontend_dir), "npm run dev -- --host 0.0.0.0", 5173)

    print("\n" + "=" * 60)
    print("  Both services launched in new windows!")
    print("=" * 60)
    print()
    print("  Windows opened:")
    print("    - Backend-8000  (FastAPI)")
    print("    - Frontend-5173 (Vue)")
    print()
    print("  Wait ~10 seconds for frontend to compile,")
    print("  then your browser will open automatically.")
    print()
    print("  URL (PC): http://localhost:5173")

    # 获取局域网 IP，供手机访问用
    lan_ip = get_lan_ip()
    if lan_ip:
        print()
        print("  ─────────────── 手机访问 ───────────────")
        print(f"  📱 手机浏览器打开: http://{lan_ip}:5173")
        print("  (确保手机和电脑在同一个 WiFi 网络)")
        print()
        print("  💡 添加到桌面 (像 App 一样):")
        print("     Safari (iOS): 分享按钮 → 添加到主屏幕")
        print("     Chrome (安卓): 菜单 → 添加到主屏幕")
        print("  ────────────────────────────────────────")
    print()

    # 等待并打开浏览器
    time.sleep(8)
    print("Opening browser...")
    try:
        webbrowser.open("http://localhost:5173")
    except Exception as e:
        print(f"  Could not open browser automatically: {e}")
        print("  Please visit http://localhost:5173 manually")

    print()
    print("Done. You can close this window.")
    input("Press Enter to close this launcher...")
    return 0

if __name__ == "__main__":
    sys.exit(main())