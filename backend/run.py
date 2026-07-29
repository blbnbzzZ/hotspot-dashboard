"""启动脚本"""
import uvicorn
import logging
import sys
from pathlib import Path
from datetime import datetime

if getattr(sys, 'frozen', False):
    LOG_DIR = Path.home() / "Documents" / "HotspotDashboard" / "data"
else:
    LOG_DIR = Path(__file__).parent / "data"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "backend.log"


# 自定义日志处理器：同时输出到 stdout 和文件
class _FileAndStdoutHandler(logging.StreamHandler):
    def __init__(self):
        super().__init__()
        self._file = None

    def emit(self, record):
        super().emit(record)  # stdout
        try:
            if self._file is None:
                self._file = open(LOG_FILE, "a", encoding="utf-8")
            msg = self.format(record) + "\n"
            self._file.write(msg)
            self._file.flush()
        except Exception:
            pass


if __name__ == "__main__":
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    fmt = fmt.replace("%(asctime)s", "%(asctime)s")
    handler = _FileAndStdoutHandler()
    handler.setFormatter(logging.Formatter(fmt))

    # 配置根 logger
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]
    logging.getLogger("uvicorn.access").addHandler(handler)
    logging.getLogger("uvicorn.error").addHandler(handler)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 关闭 reload 避免重复写日志
        log_level="info",
        log_config=None,  # 使用我们自己的 logger 配置
    )