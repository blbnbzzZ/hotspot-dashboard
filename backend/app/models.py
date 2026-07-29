"""数据模型定义"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Index
from app.database import Base


class HotItem(Base):
    """单条热点记录（原始数据，每次爬取产生）"""
    __tablename__ = "hot_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False, index=True, comment="平台: weibo/zhihu/baidu/bilibili")
    title = Column(String(500), nullable=False, comment="热点标题")
    url = Column(String(1000), nullable=True, comment="链接")
    rank = Column(Integer, nullable=False, comment="平台内排名")
    hot_score = Column(Float, nullable=True, comment="平台原始热度值")
    extra_data = Column(JSON, nullable=True, comment="额外数据(摘要/标签等)")
    batch_id = Column(String(50), nullable=False, index=True, comment="批次ID")
    created_at = Column(DateTime, default=datetime.now, comment="抓取时间")

    __table_args__ = (
        Index("idx_platform_batch", "platform", "batch_id"),
    )


class AggregatedHot(Base):
    """聚合后的热点（跨平台去重合并）"""
    __tablename__ = "aggregated_hots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(200), nullable=False, index=True, comment="核心关键词")
    display_title = Column(String(500), nullable=False, comment="展示标题")
    category = Column(String(50), nullable=True, index=True, comment="分类")
    platforms = Column(JSON, nullable=False, comment="出现的平台列表及详情")
    total_weight = Column(Float, nullable=False, index=True, comment="综合权重分")
    platform_count = Column(Integer, nullable=False, comment="覆盖平台数")
    max_hot_score = Column(Float, nullable=True, comment="最高单平台热度")
    is_common = Column(Integer, default=0, comment="是否跨平台共同热点")
    summary = Column(Text, nullable=True, comment="热点摘要")
    trend_data = Column(JSON, nullable=True, comment="趋势数据")
    batch_id = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)


class BatchRecord(Base):
    """爬取批次记录"""
    __tablename__ = "batch_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(String(20), default="running", comment="状态: running/completed/failed")
    platforms_success = Column(JSON, nullable=True, comment="成功爬取的平台")
    platforms_failed = Column(JSON, nullable=True, comment="失败的平台")
    total_items = Column(Integer, default=0, comment="原始条目数")
    aggregated_items = Column(Integer, default=0, comment="聚合后条目数")
    common_items = Column(Integer, default=0, comment="共同热点数")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class Setting(Base):
    """用户配置（key-value 形式存数据库）"""
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class GenerationRecord(Base):
    """AI 生成记录（持久化保存，关闭程序不丢失）"""
    __tablename__ = "generation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt = Column(Text, nullable=False, comment="用户输入的提示词/需求")
    content = Column(Text, nullable=True, comment="生成的完整内容")
    content_type = Column(String(50), default="custom", comment="类型: article/news/short/script/social/custom")
    provider = Column(String(50), nullable=True, comment="使用的 AI 提供商")
    status = Column(String(20), default="generating", comment="generating/completed/failed")
    error_msg = Column(Text, nullable=True, comment="失败原因")
    hotspot_title = Column(String(500), nullable=True, comment="关联的热点标题")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")


class Conversation(Base):
    """对话会话（多轮对话的一次完整会话）"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=True, comment="对话标题/首条消息预览")
    hotspot_title = Column(String(500), nullable=True, index=True, comment="关联热点")
    hotspot_id = Column(Integer, nullable=True, comment="关联热点ID")
    provider = Column(String(50), nullable=True, comment="使用的 AI 提供商")
    total_tokens = Column(Integer, default=0, comment="累计 token 数")
    message_count = Column(Integer, default=0, comment="消息条数")
    status = Column(String(20), default="active", comment="active/closed")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Message(Base):
    """对话中的单条消息"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, nullable=False, index=True, comment="所属对话")
    role = Column(String(20), nullable=False, comment="user/assistant")
    content = Column(Text, nullable=False, comment="消息内容")
    tokens = Column(Integer, default=0, comment="本条 token 数")
    status = Column(String(20), default="completed", comment="generating/completed/failed")
    created_at = Column(DateTime, default=datetime.now)
