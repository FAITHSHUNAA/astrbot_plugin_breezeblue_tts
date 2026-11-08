# astrbot_plugin_breezeblue_tts

**BreezeBlue TTS（官方 API）** —— AstrBot 文字转语音 Provider 插件。

直接调用 BreezeBlue：

```http
POST https://api.breeze.blue/v1/text-to-speech/{voice_id}?output_format=wav
Header: xi-api-key: <API Key>
```

**不是** OpenAI `/v1/audio/speech` 兼容代理。可开启「唱歌模式」：自动在文本前加 `[唱歌]`，并带演唱口吻 `instructions`，听感像在唱（仍是 TTS 唱腔，不是按谱 SVS）。

兼容 AstrBot **≥ 4.29.0**（含 Launcher ~4.29.x）。

官方文档：

- [Convert text to speech](https://docs.breezeblue.ai/api-reference/text-to-speech/convert-text-to-speech)
- [Audio tags（含 `[唱歌]`）](https://docs.breezeblue.ai/guides/audio-tags)

---

## 安装（Windows / AstrBot Launcher）

### 1. 找到实例目录

Launcher 实例一般在：

```text
C:\Users\Administrator\.astrbot_launcher\instances\<实例UUID>\
```

插件目录：

```text
C:\Users\Administrator\.astrbot_launcher\instances\<实例UUID>\data\plugins\
```

若你的数据目录自定义过，以面板「数据路径」为准，最终仍是该实例下的 `data\plugins\`。

### 2. 拷贝插件

把本文件夹（或解压 zip 后的文件夹）整份放到：

```text
...\data\plugins\astrbot_plugin_breezeblue_tts\
```

目录内至少要有：

```text
astrbot_plugin_breezeblue_tts\
  ├── main.py
  ├── breezeblue_tts_provider.py
  ├── metadata.yaml
  ├── requirements.txt
  ├── __init__.py
  └── README_ZH.md
```

也可用 AstrBot WebUI →「插件」→ 从本地 zip 安装 `astrbot_plugin_breezeblue_tts.zip`。

### 3. 重启 AstrBot 实例

Launcher 里重启该实例，或关掉再开。日志中应出现类似：

```text
[breezeblue_tts] Provider 注册成功 type=breezeblue_tts
[breezeblue_tts] 插件已加载
```

### 4. 添加服务提供商

1. 打开 AstrBot WebUI → **服务提供商** → **文字转语音**。
2. 新建提供商，类型选 **`breezeblue_tts`** / **BreezeBlue TTS**。
3. 填写：

| 配置项 | 说明 | 示例 / 默认 |
|---|---|---|
| `api_key` | BreezeBlue API Key（请求头 `xi-api-key`） | `brz_...` |
| `voice_id` | 控制台里的音色 ID（肥鱼克隆声） | `voc_...` |
| `api_base` | API 根地址 | `https://api.breeze.blue` |
| `language_code` | ISO 639-1 | `zh` |
| `instructions` | 表演说明（与正文同语言） | 默认演唱口吻中文 |
| `guidance_scale` | 1.0–10.0 | `3.5` |
| `model_id` | 可选；空则由服务端自动选 | 如 `breeze-tts-2` |
| `timeout` | 秒 | `120` |
| `enable_sing_mode` | 唱歌模式 | `true` |
| `auto_sing_tag` | 无 `[唱歌]` 时自动前置 | `true` |
| `proxy` | 可选 HTTP 代理 | 空 |

4. **启用**该提供商并保存。
5. 在 TTS 总设置里：**启用文字转语音**，并把默认 TTS 提供商选成刚建的这个（`id` 默认是 `breezeblue_tts`，也可改名）。

### 5. 验收

- 在提供商页点「测试连接」应成功（会调一次合成）。
- QQ 私聊让机器人回复一段带「唱」的短句，应收到 **语音条**（wav）。
- 若要更像唱：人设可写「唱的时候正文前加 `[唱歌]`」；插件在 `enable_sing_mode`+`auto_sing_tag` 开启时也会自动加。

---

## 行为说明

- `get_audio(text)` → 本地临时 **`.wav` 路径**（AstrBot TTSProvider 约定），NapCat / aiocqhttp 按现有通道发 record。
- `enable_sing_mode=true` 且 `auto_sing_tag=true`，且文本中没有 `[唱歌]` / `(singing)` 时，自动变成：`[唱歌] 原文`。
- 文本超过 **1000** 字符会截断并打日志（BreezeBlue 默认上限）。
- 鉴权只用 `xi-api-key`，**不要**再配 OpenAI TTS 或本机 18080 代理。

---

## 常见问题

**WebUI 看不到 breezeblue_tts**  
确认插件已启用、实例已重启；`metadata.yaml` / `main.py` 路径正确。Provider 在 **导入时** 注册，不是点启用才注册。

**热重载报「适配器已注册」**  
本插件用幂等注册，正常不应报错。若仍失败，整实例重启一次。

**401 / 403**  
Key 错误或无权；检查控制台 Key 与余额。

**404**  
`voice_id` 错误，或 `api_base` 写成了带错误路径的地址。应只填 `https://api.breeze.blue`。

**听起来仍像念**  
打开 `enable_sing_mode`，确认 `instructions` 是演唱口吻，正文尽量短句歌词；也可手动写 `[唱歌] 歌词…`。这不是按谱真唱，只是「像在唱」。

**依赖**  
需要 `httpx`（AstrBot 通常自带）。缺依赖时按 `requirements.txt` 装到实例的 `data/site-packages`。

---

## 文件说明

| 文件 | 作用 |
|---|---|
| `main.py` | 插件入口；导入时触发 Provider 注册 |
| `breezeblue_tts_provider.py` | `TTSProvider` 实现 + `register_provider_adapter` |
| `metadata.yaml` | 插件元数据 |
| `requirements.txt` | 依赖声明 |
| `__init__.py` | 包标记 |

Provider `type` 名：`breezeblue_tts`  
Provider 分类：`ProviderType.TEXT_TO_SPEECH` / `provider_type: text_to_speech`

---

## License

仅供个人 AstrBot 实例使用。调用 [BreezeBlue](https://breezeblue.ai) 公开 API；不包含其 SDK 源码。基于 AstrBot Provider 插件接口（`register_provider_adapter` / `TTSProvider`）。
