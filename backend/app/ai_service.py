"""AI 内容生成模块
支持多种免费/付费 LLM 服务，统一接口。
API Key 优先从数据库读取，其次从 .env 文件读取。
未配置任何 Key 时自动降级到模板生成。
"""
import os
import httpx
from typing import Optional, Dict, Any
from pathlib import Path

from app.database import SessionLocal
from app.models import Setting


def _load_env():
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_env()


PROVIDER_CONFIG = {
    "zhipu": {
        "name": "智谱AI (GLM-4-Flash)",
        "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "model": "glm-4-flash",
        "env_key": "ZHIPU_API_KEY",
        "docs": "https://open.bigmodel.cn/  注册送 2000万 tokens 免费额度",
    },
    "qwen": {
        "name": "通义千问 (Qwen-Turbo)",
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "model": "qwen-turbo",
        "env_key": "QWEN_API_KEY",
        "docs": "https://dashscope.aliyun.com/  有免费额度",
    },
    "deepseek": {
        "name": "DeepSeek (超低价)",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "docs": "https://platform.deepseek.com/  新用户送额度",
    },
    "doubao": {
        "name": "豆包 (字节)",
        "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "model": "doubao-lite-32k",
        "env_key": "DOUBAO_API_KEY",
        "docs": "https://www.volcengine.com/product/doubao  有免费试用",
    },
    "openai": {
        "name": "OpenAI 兼容",
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-3.5-turbo",
        "env_key": "OPENAI_API_KEY",
        "docs": "需要付费",
    },
}


def _read_key_from_db(env_key: str) -> Optional[str]:
    """从数据库读取 API Key"""
    try:
        db = SessionLocal()
        setting = db.query(Setting).filter_by(key=env_key).first()
        if setting and setting.value:
            return setting.value.strip()
    except Exception:
        pass
    finally:
        try:
            db.close()
        except Exception:
            pass
    return None


def save_key(env_key: str, value: str) -> None:
    """保存 API Key 到数据库"""
    db = SessionLocal()
    try:
        setting = db.query(Setting).filter_by(key=env_key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.now()
        else:
            setting = Setting(key=env_key, value=value)
            db.add(setting)
        db.commit()
    finally:
        db.close()


def delete_key(env_key: str) -> None:
    """删除数据库中的 API Key"""
    db = SessionLocal()
    try:
        db.query(Setting).filter_by(key=env_key).delete()
        db.commit()
    finally:
        db.close()


def get_api_key(env_key: str) -> Optional[str]:
    """获取 API Key：先查数据库，再查环境变量"""
    # 数据库优先
    val = _read_key_from_db(env_key)
    if val:
        return val
    # 环境变量次之
    return os.environ.get(env_key)


def get_configured_provider() -> Optional[str]:
    """检测用户配置了哪个 provider"""
    for key, cfg in PROVIDER_CONFIG.items():
        if get_api_key(cfg["env_key"]):
            return key
    return None


def get_status() -> Dict[str, Any]:
    """获取 AI 配置状态"""
    configured = get_configured_provider()
    return {
        "enabled": configured is not None,
        "current_provider": configured,
        "current_name": PROVIDER_CONFIG[configured]["name"] if configured else None,
        "providers": [
            {
                "key": k,
                "name": cfg["name"],
                "env_key": cfg["env_key"],
                "configured": bool(get_api_key(cfg["env_key"])),
                "docs": cfg["docs"],
            }
            for k, cfg in PROVIDER_CONFIG.items()
        ],
    }


async def ai_generate(prompt: str, system: str = "你是一个专业的内容创作助手。") -> str:
    """调用 AI 生成内容"""
    provider_key = get_configured_provider()
    if not provider_key:
        raise ValueError("未配置 AI API Key")

    cfg = PROVIDER_CONFIG[provider_key]
    api_key = get_api_key(cfg["env_key"])
    if not api_key:
        raise ValueError(f"无法获取 {cfg['env_key']}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 1500,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(cfg["url"], headers=headers, json=payload)
            # 检查返回内容是否是 JSON
            ct = resp.headers.get("content-type", "")
            text = resp.text
            if "application/json" not in ct:
                raise ValueError(f"API 返回非 JSON 响应: {text[:200]}")
            try:
                data = resp.json()
            except Exception as e:
                raise ValueError(f"API 返回无法解析的 JSON: {text[:200]}") from e
        except httpx.HTTPStatusError as e:
            # 提取返回的错误信息
            err_text = e.response.text[:300] if hasattr(e, 'response') else str(e)
            raise ValueError(f"API HTTP {e.response.status_code}: {err_text}") from e
        except Exception as e:
            raise ValueError(str(e))

    # 验证响应结构
    if not isinstance(data, dict) or "choices" not in data or not data["choices"]:
        raise ValueError(f"API 返回格式异常: {str(data)[:200]}")

    try:
        content = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"API 响应缺少内容字段: {str(data)[:200]}") from e

    tokens = data.get("usage", {}).get("total_tokens", 0)
    return {
        "content": content,
        "tokens": tokens,
        "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
        "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
    }


async def ai_chat(messages: list, system: str = "你是一个专业的内容创作助手。") -> dict:
    """多轮对话"""
    provider_key = get_configured_provider()
    if not provider_key:
        raise ValueError("未配置 AI API Key")

    cfg = PROVIDER_CONFIG[provider_key]
    api_key = get_api_key(cfg["env_key"])
    if not api_key:
        raise ValueError(f"无法获取 {cfg['env_key']}")

    full_messages = [{"role": "system", "content": system}] + messages

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": cfg["model"],
        "messages": full_messages,
        "temperature": 0.7,
        "max_tokens": 1500,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(cfg["url"], headers=headers, json=payload)
            ct = resp.headers.get("content-type", "")
            text = resp.text
            if "application/json" not in ct:
                raise ValueError(f"API 返回非 JSON 响应: {text[:200]}")
            try:
                data = resp.json()
            except Exception as e:
                raise ValueError(f"API 返回无法解析的 JSON: {text[:200]}") from e
        except httpx.HTTPStatusError as e:
            err_text = e.response.text[:300] if hasattr(e, 'response') else str(e)
            raise ValueError(f"API HTTP {e.response.status_code}: {err_text}") from e
        except Exception as e:
            raise ValueError(str(e))

    if not isinstance(data, dict) or "choices" not in data or not data["choices"]:
        raise ValueError(f"API 返回格式异常: {str(data)[:200]}")

    try:
        content = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"API 响应缺少内容字段: {str(data)[:200]}") from e

    tokens = data.get("usage", {}).get("total_tokens", 0)
    return {
        "content": content,
        "tokens": tokens,
    }


# 延迟导入避免循环依赖
from datetime import datetime