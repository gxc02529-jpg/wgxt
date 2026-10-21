# -*- coding: utf-8 -*-
"""全局配置：数据库连接、JWT、文件上传等。
可通过环境变量或 backend/.env 文件覆盖默认值。
"""
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env 固定放在 backend 目录下，与启动目录无关，保证从任意位置运行都能读到
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

# 项目根目录（backend/app/config.py 向上三级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 本地已下载的 multilingual-e5-small 模型目录，相对项目根目录，优先于 Hugging Face 在线加载
LOCAL_EMBEDDING_MODEL_PATH = "backend/app/multilingual-e5-small"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")

    # 数据库连接（可按部署环境覆盖）
    DB_HOST: str = "192.168.14.216"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "password!"
    DB_NAME: str = "wengaofabu"

    # 运行环境与跨域来源。生产环境会在启动时执行强校验，拒绝弱密钥和通配来源。
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # JWT 安全配置（生产环境务必修改 SECRET_KEY）
    SECRET_KEY: str = "wengaofabu-dev-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 天

    # 文件上传
    UPLOAD_DIR: str = "uploads"           # 上传文件保存目录
    MAX_UPLOAD_SIZE: int = 20 * 1024 * 1024  # 单文件最大 20MB
    BASE_URL: str = "http://localhost:8000"  # 静态资源完整 URL 前缀

    # Dify 工作流（预留）：默认接入配置，可用环境变量或 .env 覆盖。
    # 也可在后台通过 /api/dify/workflows 在数据库登记多个工作流，优先级高于此处。
    DIFY_API_BASE: str = ""                # Dify API 地址，如 https://api.dify.ai/v1 或自建域名
    DIFY_API_KEY: str = ""                 # Dify 应用 API Key（app-xxx）
    DIFY_TIMEOUT: int = 30                 # 调用超时（秒）

    # Tavily 新闻搜索：Key 只从后端环境变量或 backend/.env 读取，不下发前端。
    TAVILY_API_KEY: str = ""
    TAVILY_TIMEOUT: int = 15

    # AI 大模型 API（OpenAI 兼容接口，如 DeepSeek / Groq / 硅基流动等）
    AI_API_BASE: str = "https://api.openai.com/v1"
    AI_API_KEY: str = "sk-your-api-key-here"
    AI_MODEL: str = "gpt-4o"
    AI_TIMEOUT: int = 60

    # 本地Embedding：默认加载相对项目根目录的 backend/app/multilingual-e5-small，可用 .env 覆盖
    EMBEDDING_MODEL_NAME: str = LOCAL_EMBEDDING_MODEL_PATH
    EMBEDDING_DEVICE: str = "auto"

    # Grounded事件整理LLM：真实Key只允许来自环境变量或backend/.env。
    # 兼容本机已有OPENAI_API_KEY；项目显式LLM_API_KEY具有更高优先级。
    LLM_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices(
            "LLM_API_KEY",
            "OPENAI_API_KEY",
        ),
    )
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_MODEL: str = "qwen3.7-plus"
    LLM_TIMEOUT: int = 90


settings = Settings()


def get_cors_origins(config: Settings = settings) -> list[str]:
    """把英文逗号分隔的跨域配置转换为 Starlette 所需列表。"""
    return [item.strip() for item in config.CORS_ORIGINS.split(",") if item.strip()]


def validate_runtime_settings(config: Settings = settings) -> None:
    """生产环境启动保护：在连接数据库前拒绝明显不安全的默认配置。"""
    if config.APP_ENV.strip().casefold() in {"development", "dev", "test"}:
        return

    errors: list[str] = []
    if not config.DB_PASSWORD.strip() or config.DB_PASSWORD == "password!":
        errors.append("数据库密码仍为开发默认值")
    if config.SECRET_KEY == "wengaofabu-dev-secret-change-me" or len(config.SECRET_KEY.strip()) < 32:
        errors.append("SECRET_KEY 必须使用至少 32 位的随机字符串")
    origins = get_cors_origins(config)
    if not origins or "*" in origins:
        errors.append("CORS_ORIGINS 必须明确列出允许的前端来源")
    if errors:
        raise RuntimeError("生产配置校验失败：" + "；".join(errors))
