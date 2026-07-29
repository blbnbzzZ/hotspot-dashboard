"""数据库连接与配置"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pathlib import Path

# SQLite 数据库文件存放在项目目录
import os
DB_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{DB_DIR}/hotspots.db"

# 同步engine用于创建表
sync_url = f"sqlite:///{DB_DIR}/hotspots.db"
engine = create_engine(sync_url, echo=False, connect_args={"check_same_thread": False})

# 启用 WAL 模式提升并发性能
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

def get_db():
    """获取数据库会话（同步版本，用于简单操作）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库表"""
    Base.metadata.create_all(bind=engine)
