"""AstrBot plugin entry: register BreezeBlue TTS provider on import."""

from __future__ import annotations

import os
import sys

from astrbot.api import logger
from astrbot.api.star import Context, Star, register

# Provider 必须在模块导入时完成注册（装饰器副作用），
# 不要放到 Star.__init__ 里，否则 WebUI「服务提供商」可能看不到。
try:
    from .breezeblue_tts_provider import ProviderBreezeBlueTTS  # noqa: F401
except ImportError:  # 兼容非包方式加载
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from breezeblue_tts_provider import ProviderBreezeBlueTTS  # noqa: F401


@register(
    "astrbot_plugin_breezeblue_tts",
    "dafeiyu",
    "通过 BreezeBlue 官方 TTS API 为 AstrBot 提供文字转语音。",
    "1.0.0",
    "https://docs.breezeblue.ai/api-reference/text-to-speech/convert-text-to-speech",
)
class BreezeBlueTTSPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context, config)
        logger.info(
            "[breezeblue_tts] 插件已加载，Provider type=breezeblue_tts "
            "(provider_type=text_to_speech)"
        )
