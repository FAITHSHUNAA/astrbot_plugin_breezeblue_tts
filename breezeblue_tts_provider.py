"""BreezeBlue TTS Provider for AstrBot (direct official API, not OpenAI-compatible)."""

from __future__ import annotations

import os
import uuid
from typing import Any
from urllib.parse import urlencode

import httpx

from astrbot.api import logger
from astrbot.core.provider.entities import ProviderType
from astrbot.core.provider.provider import TTSProvider
from astrbot.core.provider.register import (
    provider_cls_map,
    register_provider_adapter,
)
from astrbot.core.utils.astrbot_path import get_astrbot_temp_path

PROVIDER_TYPE_NAME = "breezeblue_tts"
PROVIDER_DESC = "BreezeBlue TTS（官方 API，支持 [唱歌] 标签）"
PROVIDER_DISPLAY_NAME = "BreezeBlue TTS"

DEFAULT_API_BASE = "https://api.breeze.blue"
DEFAULT_LANGUAGE = "zh"
DEFAULT_GUIDANCE = 3.5
DEFAULT_SPEED = 1.0
DEFAULT_TIMEOUT = 120
DEFAULT_INSTRUCTIONS = (
    "用正常聊天语速说话，自然口语，不要拖腔，不要唱。"
)
DEFAULT_SING_INSTRUCTIONS = (
    "用轻柔演唱口吻唱出歌词，有一点旋律起伏，不要念白播报腔。"
)
SING_TAG = "[唱歌]"

# AstrBot 4.29.x WebUI 用 template.provider_type 匹配「文字转语音」标签页。
DEFAULT_CONFIG_TMPL: dict[str, Any] = {
    "provider_type": "text_to_speech",
    "provider": "breezeblue",
    "api_key": "",
    "voice_id": "",
    "api_base": DEFAULT_API_BASE,
    "language_code": DEFAULT_LANGUAGE,
    "instructions": DEFAULT_INSTRUCTIONS,
    "guidance_scale": DEFAULT_GUIDANCE,
    "speed": DEFAULT_SPEED,
    "model_id": "",
    "timeout": DEFAULT_TIMEOUT,
    "enable_sing_mode": False,
    "auto_sing_tag": False,
    "proxy": "",
}

# 注入到 CONFIG_METADATA_2 的自定义字段（仅 type；description 会被替换成无翻译的 i18n key）
_SCHEMA_FIELDS: dict[str, dict[str, Any]] = {
    "voice_id": {"type": "string"},
    "api_base": {"type": "string"},
    "language_code": {"type": "string"},
    "instructions": {"type": "text"},
    "guidance_scale": {"type": "float"},
    "speed": {"type": "float"},
    "model_id": {"type": "string"},
    "timeout": {"type": "int"},
    "enable_sing_mode": {"type": "bool"},
    "auto_sing_tag": {"type": "bool"},
}


class ProviderBreezeBlueTTS(TTSProvider):
    """Call BreezeBlue POST /v1/text-to-speech/{voice_id}?output_format=wav."""

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config, provider_settings)
        self.api_key = str(provider_config.get("api_key") or "").strip()
        self.voice_id = str(provider_config.get("voice_id") or "").strip()
        raw_base = str(provider_config.get("api_base") or DEFAULT_API_BASE).strip()
        self.api_base = raw_base.rstrip("/") or DEFAULT_API_BASE
        self.language_code = (
            str(provider_config.get("language_code") or DEFAULT_LANGUAGE).strip()
            or DEFAULT_LANGUAGE
        )
        self.instructions = str(provider_config.get("instructions") or "").strip()
        self.model_id = str(provider_config.get("model_id") or "").strip()
        try:
            self.guidance_scale = float(
                provider_config.get("guidance_scale", DEFAULT_GUIDANCE)
            )
        except (TypeError, ValueError):
            self.guidance_scale = DEFAULT_GUIDANCE
        try:
            self.speed = float(provider_config.get("speed", DEFAULT_SPEED))
        except (TypeError, ValueError):
            self.speed = DEFAULT_SPEED
        self.speed = max(0.5, min(2.0, self.speed))
        try:
            self.timeout = int(provider_config.get("timeout", DEFAULT_TIMEOUT))
        except (TypeError, ValueError):
            self.timeout = DEFAULT_TIMEOUT
        self.enable_sing_mode = bool(provider_config.get("enable_sing_mode", False))
        self.auto_sing_tag = bool(provider_config.get("auto_sing_tag", False))
        self.proxy = str(provider_config.get("proxy") or "").strip()

        client_kwargs: dict[str, Any] = {"timeout": self.timeout}
        if self.proxy:
            client_kwargs["proxy"] = self.proxy
            logger.info("[breezeblue_tts] 使用代理: %s", self.proxy)
        self._client = httpx.AsyncClient(**client_kwargs)

        if self.model_id:
            self.set_model(self.model_id)

        logger.info(
            "[breezeblue_tts] 初始化: base=%s voice_id=%s speed=%s sing=%s auto_tag=%s",
            self.api_base,
            self.voice_id or "(empty)",
            self.speed,
            self.enable_sing_mode,
            self.auto_sing_tag,
        )

    def _prepare_text(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            raise ValueError("TTS 输入文本为空")
        if (
            self.enable_sing_mode
            and self.auto_sing_tag
            and SING_TAG not in text
            and "(singing)" not in text.lower()
        ):
            text = f"{SING_TAG} {text}"
        # BreezeBlue 默认可到 1000 字符；超长时截断并打日志，避免 422
        if len(text) > 1000:
            logger.warning(
                "[breezeblue_tts] 文本长度 %d > 1000，已截断",
                len(text),
            )
            text = text[:1000]
        return text

    def _build_url(self) -> str:
        if not self.voice_id:
            raise ValueError("未配置 BreezeBlue voice_id")
        qs = urlencode({"output_format": "wav"})
        return f"{self.api_base}/v1/text-to-speech/{self.voice_id}?{qs}"

    def _build_body(self, text: str) -> dict[str, Any]:
        body: dict[str, Any] = {
            "text": text,
            "language_code": self.language_code,
            "voice_settings": {
                "guidance_scale": self.guidance_scale,
                "speed": self.speed,
            },
        }
        # 自定义 instructions 优先；唱歌模式用演唱口吻，否则用正常语速口语
        if self.instructions:
            body["instructions"] = self.instructions
        elif self.enable_sing_mode:
            body["instructions"] = DEFAULT_SING_INSTRUCTIONS
        else:
            body["instructions"] = DEFAULT_INSTRUCTIONS
        if self.model_id:
            body["model_id"] = self.model_id
        return body

    async def get_audio(self, text: str) -> str:
        if not self.api_key:
            raise ValueError("未配置 BreezeBlue api_key（Header: xi-api-key）")

        prepared = self._prepare_text(text)
        url = self._build_url()
        body = self._build_body(prepared)
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/wav, application/octet-stream, */*",
        }

        temp_dir = get_astrbot_temp_path()
        os.makedirs(temp_dir, exist_ok=True)
        path = os.path.join(temp_dir, f"breezeblue_tts_{uuid.uuid4()}.wav")

        try:
            resp = await self._client.post(url, headers=headers, json=body)
        except httpx.HTTPError as e:
            raise RuntimeError(
                f"BreezeBlue TTS 网络错误: {e} (url={url})"
            ) from e

        if resp.status_code != 200:
            detail = (resp.text or "")[:800]
            raise RuntimeError(
                f"BreezeBlue TTS 失败 HTTP {resp.status_code}: {detail}"
            )

        content_type = (resp.headers.get("content-type") or "").lower()
        audio = resp.content
        if not audio:
            raise RuntimeError("BreezeBlue TTS 返回空音频")
        # 偶发返回 JSON 错误却带 200
        if "application/json" in content_type or audio[:1] == b"{":
            raise RuntimeError(
                f"BreezeBlue TTS 返回非音频: {audio[:500]!r}"
            )

        with open(path, "wb") as f:
            f.write(audio)
        logger.info(
            "[breezeblue_tts] 合成成功 %d bytes -> %s",
            len(audio),
            path,
        )
        return path

    async def terminate(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None  # type: ignore[assignment]


def _inject_schema_fields() -> None:
    """把自定义配置字段注入 AstrBot provider schema，便于 WebUI 编辑。"""
    try:
        from astrbot.core.config.default import CONFIG_METADATA_2
    except Exception as e:  # pragma: no cover
        logger.warning("[breezeblue_tts] 无法读取 CONFIG_METADATA_2: %s", e)
        return
    try:
        items = CONFIG_METADATA_2["provider_group"]["metadata"]["provider"]["items"]
        for key, meta in _SCHEMA_FIELDS.items():
            item = items.setdefault(key, {})
            item.setdefault("type", meta["type"])
        logger.info(
            "[breezeblue_tts] 已注入 schema 字段: %s",
            ", ".join(_SCHEMA_FIELDS),
        )
    except Exception as e:  # pragma: no cover
        logger.warning("[breezeblue_tts] 注入 schema 失败: %s", e)


def register() -> None:
    """幂等注册 Provider（热重载时不因「已注册」抛错）。"""
    tmpl = dict(DEFAULT_CONFIG_TMPL)
    tmpl.setdefault("type", PROVIDER_TYPE_NAME)
    tmpl.setdefault("enable", False)
    tmpl.setdefault("id", PROVIDER_TYPE_NAME)

    _inject_schema_fields()

    existing = provider_cls_map.get(PROVIDER_TYPE_NAME)
    if existing is not None:
        existing.desc = PROVIDER_DESC
        existing.provider_type = ProviderType.TEXT_TO_SPEECH
        existing.cls_type = ProviderBreezeBlueTTS
        existing.default_config_tmpl = tmpl
        existing.provider_display_name = PROVIDER_DISPLAY_NAME
        logger.info("[breezeblue_tts] Provider 已存在，已刷新注册元数据")
        return

    register_provider_adapter(
        PROVIDER_TYPE_NAME,
        PROVIDER_DESC,
        provider_type=ProviderType.TEXT_TO_SPEECH,
        default_config_tmpl=tmpl,
        provider_display_name=PROVIDER_DISPLAY_NAME,
    )(ProviderBreezeBlueTTS)
    logger.info("[breezeblue_tts] Provider 注册成功 type=%s", PROVIDER_TYPE_NAME)


register()
