"""
title: CometAPI Pipe
author: Stylishseahorse
version: 2.22.14
description: CometAPI manifold pipe for Open WebUI with provider logos, cost display, model type filtering, and built-in Exa neural web search tool.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from typing import Any, AsyncGenerator, Callable, Awaitable, Literal, Optional

import aiohttp
from pydantic import BaseModel, Field

# Pattern list: (prefix_or_substring, provider_key).  First match wins.
_MODEL_PROVIDER_PATTERNS: list[tuple[str, str]] = [
    # OpenAI
    ("gpt-", "openai"),
    ("o1", "openai"),
    ("o3", "openai"),
    ("o4", "openai"),
    ("dall-e", "openai"),
    ("dalle", "openai"),
    ("sora", "openai"),
    ("whisper", "openai"),
    ("tts-", "openai"),
    # Anthropic
    ("claude-", "anthropic"),
    # Google
    ("gemini-", "google"),
    ("gemma-", "google"),
    ("imagen-", "google"),
    ("veo", "google"),
    ("palm", "google"),
    # Meta
    ("llama", "meta"),
    ("meta-llama", "meta"),
    # Mistral
    ("mistral", "mistral"),
    ("mixtral", "mistral"),
    ("codestral", "mistral"),
    ("pixtral", "mistral"),
    # DeepSeek
    ("deepseek", "deepseek"),
    # Qwen / Alibaba
    ("qwen", "qwen"),
    # xAI
    ("grok", "xai"),
    # Cohere
    ("command", "cohere"),
    # Perplexity
    ("sonar", "perplexity"),
    ("pplx", "perplexity"),
    # NVIDIA
    ("nemotron", "nvidia"),
    # Together / open models via Together
    ("togethercomputer", "together"),
    # Stability AI
    ("stable-diffusion", "stability"),
    ("sdxl", "stability"),
    ("stable-cascade", "stability"),
    # Black Forest Labs
    ("flux", "blackforestlabs"),
    # Ideogram
    ("ideogram", "ideogram"),
    # Recraft
    ("recraft", "recraft"),
    # Luma
    ("luma", "luma"),
    ("dream-machine", "luma"),
    # Kling
    ("kling", "kling"),
    # MiniMax (abab series)
    ("abab", "minimax"),
    # MiniMax
    ("minimax", "minimax"),
    # Pika
    ("pika", "pika"),
    # Runway
    ("runway", "runway"),
    ("gen-", "runway"),
    ("act_two", "runway"),
    ("act-two", "runway"),
    ("act_one", "runway"),
    # Haiper
    ("haiper", "haiper"),
    # Wan
    ("wan", "wan"),
    # HunyuanVideo
    ("hunyuan", "hunyuan"),
    # CogVideo
    ("cogvideo", "cogvideo"),
    # Mochi
    ("mochi", "mochi"),
    # Playground
    ("playground", "playground"),
    # HuggingFace
    ("huggingface", "huggingface"),
    # Microsoft
    ("phi-", "microsoft"),
    ("wizard", "microsoft"),
    # Amazon
    ("titan", "amazon"),
    ("nova-", "amazon"),
    # Doubao / ByteDance
    ("doubao", "doubao"),
    ("bytedance", "bytedance"),
    # Zhipuai / GLM
    ("glm-", "zhipuai"),
    ("chatglm", "zhipuai"),
    # Moonshot / Kimi
    ("moonshot", "moonshot"),
    ("kimi", "moonshot"),
    # Yi / 01.ai
    ("yi-", "yi"),
    # Baichuan
    ("baichuan", "baichuan"),
    # InternLM
    ("internlm", "internlm"),
    # Stepfun
    ("step-", "stepfun"),
    ("step1", "stepfun"),
    # iFlytek Spark
    ("spark", "spark"),
    # Sensetime / Sense Nova
    ("nova-ptx", "sensetime"),
    ("sensenova", "sensetime"),
    # 360
    ("360gpt", "360"),
    # Lingyiwanwu
    ("lingyi", "lingyi"),
]


# Direct provider logo URLs — GitHub organisation avatars (https://github.com/<org>.png)
# serve the company's official profile picture and are stable, free, and full-colour.
# Clearbit is kept only where no reliable GitHub org is available.
_PROVIDER_LOGOS: dict[str, str] = {
    # ── Major western AI labs ──────────────────────────────────────────────────
    "openai": "https://github.com/openai.png",
    "anthropic": "https://github.com/anthropics.png",
    "google": "https://github.com/google.png",
    "meta": "https://github.com/meta-llama.png",
    "mistral": "https://github.com/mistralai.png",
    "cohere": "https://github.com/cohere-ai.png",
    "perplexity": "https://github.com/perplexity-ai.png",
    "deepseek": "https://github.com/deepseek-ai.png",
    "xai": "https://github.com/xai-org.png",
    "nvidia": "https://github.com/NVIDIA.png",
    "microsoft": "https://github.com/microsoft.png",
    "amazon": "https://github.com/aws.png",
    "inflection": "https://github.com/inflection-ai.png",
    # ── Cloud / infrastructure AI providers ───────────────────────────────────
    "groq": "https://github.com/groq.png",
    "together": "https://github.com/togethercomputer.png",
    "fireworks": "https://github.com/fw-ai.png",
    "replicate": "https://github.com/replicate.png",
    "huggingface": "https://github.com/huggingface.png",
    # ── Image / video generation studios ─────────────────────────────────────
    "stability": "https://github.com/Stability-AI.png",
    "blackforestlabs": "https://github.com/black-forest-labs.png",
    "runway": "https://github.com/runwayml.png",
    "luma": "https://github.com/lumalabs-ai.png",
    "playground": "https://github.com/playgroundai.png",
    "mochi": "https://github.com/genmoai.png",
    "pika": "https://logo.clearbit.com/pika.art",
    "haiper": "https://logo.clearbit.com/haiper.ai",
    "ideogram": "https://logo.clearbit.com/ideogram.ai",
    "recraft": "https://logo.clearbit.com/recraft.ai",
    "kling": "https://logo.clearbit.com/kling.ai",
    "wan": "https://logo.clearbit.com/wanvideo.ai",
    "sora": "https://github.com/openai.png",
    # ── Chinese AI providers ───────────────────────────────────────────────────
    "qwen": "https://github.com/QwenLM.png",
    "zhipuai": "https://github.com/THUDM.png",
    "cogvideo": "https://github.com/THUDM.png",
    "minimax": "https://github.com/MiniMax-AI.png",
    "doubao": "https://github.com/volcengine.png",
    "bytedance": "https://github.com/bytedance.png",
    "hunyuan": "https://github.com/Tencent.png",
    "baidu": "https://github.com/baidu.png",
    "moonshot": "https://logo.clearbit.com/moonshot.cn",
    "yi": "https://github.com/01-ai.png",
    "baichuan": "https://github.com/baichuan-inc.png",
    "internlm": "https://github.com/InternLM.png",
    "stepfun": "https://logo.clearbit.com/stepfun.com",
    "spark": "https://logo.clearbit.com/xfyun.cn",
    "sensetime": "https://logo.clearbit.com/sensetime.com",
    "360": "https://logo.clearbit.com/360.cn",
    "lingyi": "https://logo.clearbit.com/lingyiwanwu.com",
}


def _model_provider(model_id: str) -> str:
    """Return the provider key for a model ID using pattern matching."""
    lower = model_id.lower()
    for prefix, provider in _MODEL_PROVIDER_PATTERNS:
        if lower.startswith(prefix) or prefix in lower:
            return provider
    # Fallback: first dash-segment (e.g. "myco-large" → "myco")
    return lower.split("-")[0]


def _provider_logo(provider: str) -> str:
    """Return a hardcoded logo URL for the given provider key, or empty string if unknown."""
    return _PROVIDER_LOGOS.get(provider, "")


# Auto-detect our own function ID from the module name OWU assigns at load time.
# OWU loads pipes as module "function_{id}", so __name__ == "function_comet_api_pipe" etc.
_SELF_ID: str = __name__.removeprefix("function_") if __name__.startswith("function_") else "comet_api_pipe"

# Module-level cache so we only write each model's logo to the DB once per process restart.
_IMAGE_SYNCED: set[str] = set()

# Prevents re-running the Exa tool registration check on every pipes() call.
_EXA_TOOL_REGISTERED: bool = False


_IMAGE_KEYWORDS = (
    "dall-e",
    "dalle",
    "stable-diffusion",
    "sdxl",
    "flux",
    "ideogram",
    "recraft",
    "imagen",
    "midjourney",
    "kandinsky",
    "playground",
    "stable-cascade",
    "auraflow",
    "hidream",
)
_VIDEO_KEYWORDS = (
    "video",
    "veo",
    "kling",
    "luma",
    "wan",
    "sora",
    "runway",
    "pika",
    "haiper",
    "mochi",
    "cogvideo",
    "animatediff",
    "i2vgen",
    "ltx-video",
    "hunyuan-video",
    "minimax-video",
)


def _model_type(model_id: str) -> Literal["text", "image", "video"]:
    lower = model_id.lower()
    # kling_image contains "kling" (a video keyword) but is actually an image model
    if "kling" in lower and "image" in lower:
        return "image"
    for kw in _VIDEO_KEYWORDS:
        if kw in lower:
            return "video"
    for kw in _IMAGE_KEYWORDS:
        if kw in lower:
            return "image"
    return "text"


# Matches bare URLs in model responses so we can linkify them.
_URL_RE = re.compile(r'https?://[^\s\)\]>"]+', re.ASCII)


def _format_media_response(content: str, model_type: str) -> str:
    """
    Replace raw URLs in video/image model responses with markdown links.
    - video: [▶ Download Video](url)
    - image: ![Generated Image](url)  — Open WebUI renders these inline
    Returns content unchanged for text models.
    """
    if model_type not in ("video", "image"):
        return content

    def _replace(m: re.Match) -> str:
        url = m.group(0).rstrip(".,;:")
        if model_type == "video":
            return f"[\u25b6 Download Video]({url})"
        return f"![Generated Image]({url})"

    return _URL_RE.sub(_replace, content)


def _format_cost(cost: Any) -> Optional[str]:
    if isinstance(cost, str):
        try:
            cost = float(cost.strip())
        except Exception:
            return None
    if isinstance(cost, (int, float)) and cost > 0:
        return "$" + f"{cost:.6f}".rstrip("0").rstrip(".")
    return None


# ── Pretty display names ──────────────────────────────────────────────────────
_PROVIDER_DISPLAY: dict[str, str] = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
    "meta": "Meta",
    "mistral": "Mistral",
    "deepseek": "DeepSeek",
    "qwen": "Qwen",
    "xai": "xAI",
    "cohere": "Cohere",
    "perplexity": "Perplexity",
    "nvidia": "NVIDIA",
    "microsoft": "Microsoft",
    "amazon": "Amazon",
    "blackforestlabs": "Black Forest Labs",
    "stability": "Stability AI",
    "ideogram": "Ideogram",
    "recraft": "Recraft",
    "runway": "Runway",
    "pika": "Pika",
    "luma": "Luma",
    "kling": "Kling",
    "minimax": "MiniMax",
    "hunyuan": "Hunyuan",
    "doubao": "Doubao",
    "zhipuai": "ZhipuAI",
    "moonshot": "Moonshot",
    "yi": "Yi",
    "baichuan": "Baichuan",
    "internlm": "InternLM",
    "stepfun": "Stepfun",
    "spark": "iFlytek",
    "sensetime": "SenseTime",
    "groq": "Groq",
    "together": "Together AI",
    "fireworks": "Fireworks AI",
    "replicate": "Replicate",
    "huggingface": "Hugging Face",
}


def _smart_title(s: str) -> str:
    """Title-case a string while preserving known acronyms and version numbers."""
    # Tokens that should stay in their canonical form
    _KEEP = {"gpt", "ai", "llm", "api", "ui", "ux", "sdk", "gpu", "cpu", "hd", "sd"}
    parts = []
    for word in s.replace("-", " ").replace("_", " ").split():
        low = word.lower()
        if low in _KEEP:
            parts.append(low.upper())
        elif word[0].isdigit():
            parts.append(word)  # keep "3.5", "4o" as-is
        else:
            parts.append(word.capitalize())
    return " ".join(parts)


def _pretty_model_name(
    catalog_name: str,
    model_id: str,
    fmt: str,
    prefix: str,
) -> str:
    """Return a display name for a model based on the chosen format."""
    name = (catalog_name or model_id or "").strip()
    if fmt == "title_case":
        name = _smart_title(name)
    elif fmt == "provider_prefix":
        provider = _model_provider(model_id)
        provider_label = _PROVIDER_DISPLAY.get(provider, provider.title())
        name = f"{provider_label} \u2022 {name}"
    if prefix:
        name = f"{prefix.rstrip()} {name}"
    return name


# ── Shared TCP connector for connection keepalive and pooling ─────────────────
# Created lazily; reused across all requests within a process to avoid the
# overhead of DNS + TCP + TLS handshakes on every streamed response.
_CONNECTOR: Optional[aiohttp.TCPConnector] = None


def _get_connector() -> aiohttp.TCPConnector:
    global _CONNECTOR
    if _CONNECTOR is None or _CONNECTOR.closed:
        _CONNECTOR = aiohttp.TCPConnector(
            limit=100,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
        )
    return _CONNECTOR


class Pipe:
    class Valves(BaseModel):
        BASE_URL: str = Field(
            default="https://api.cometapi.com",
            description="CometAPI base URL.",
        )
        API_KEY: str = Field(
            default="",
            description="Your CometAPI API key.",
        )
        MODEL_FILTER: Literal["all", "text", "image", "video", "image_video"] = Field(
            default="all",
            description=(
                "Which model types to expose:\n"
                "  all         - every model in the catalog\n"
                "  text        - chat / completion models only\n"
                "  image       - image generation models only\n"
                "  video       - video generation models only\n"
                "  image_video - image and video generation models combined"
            ),
        )
        FUNCTION_ID: str = Field(
            default=_SELF_ID,
            description=(
                "The function ID of this pipe in Open WebUI (the filename without .py). "
                "Auto-detected from the module name — only change this if the pipe was installed with a custom ID."
            ),
        )
        SYNC_MODEL_ICONS: bool = Field(
            default=True,
            description="Sync provider logo icons and descriptions to the Open WebUI models DB so they appear in the model list.",
        )
        SHOW_USAGE_STATUS: bool = Field(
            default=True,
            description="Show token count, elapsed time, and cost in the status bar after each reply.",
        )
        RESPONSES_API_MODELS: str = Field(
            default="",
            description=(
                "Comma-separated list of model IDs that should use /v1/responses "
                "instead of /v1/chat/completions. Partial matches are supported "
                "(e.g. 'sora' matches 'sora-2'). Leave empty to use chat completions for all models."
            ),
        )
        REQUEST_TIMEOUT: int = Field(
            default=300,
            description="HTTP request timeout in seconds.",
        )
        VIDEO_JOB_TIMEOUT: int = Field(
            default=900,
            description="Maximum seconds to wait for a video generation job to complete before giving up.",
        )
        VIDEO_POLL_INTERVAL: int = Field(
            default=5,
            description="Seconds between status checks when polling a video generation job.",
        )
        KLING_VIDEO_MODEL: str = Field(
            default="kling-v2-master",
            description=(
                "Kling model version to use when kling_video is selected. "
                "Options: kling-v1, kling-v1-5, kling-v1-6, kling-v2-master"
            ),
        )
        KLING_IMAGE_MODEL: str = Field(
            default="kling-v2",
            description=(
                "Kling model version to use for image generation (kling_image). "
                "Options: kling-v1, kling-v2, kling-v2-new"
            ),
        )
        # ── Display names ──────────────────────────────────────────────────────
        MODEL_NAME_PREFIX: str = Field(
            default="",
            description=(
                "Text prepended to every model name in Open WebUI (e.g. '\u26a1 ' or 'CometAPI \u2014 '). "
                "Leave empty to use the name exactly as returned by the catalog."
            ),
        )
        MODEL_NAME_FORMAT: Literal["raw", "title_case", "provider_prefix"] = Field(
            default="provider_prefix",
            description=(
                "How to format model names shown in Open WebUI.\n"
                "  raw            - use the catalog name unchanged (default)\n"
                "  title_case     - capitalise each word (e.g. 'GPT 4o Mini')\n"
                "  provider_prefix - prepend the provider label (e.g. 'OpenAI \u2022 GPT-4o')"
            ),
        )
        # ── Image overrides ────────────────────────────────────────────────────
        RESET_MODEL_IMAGES: bool = Field(
            default=False,
            description=(
                "When True, clears the image-sync cache and re-applies all model images on the "
                "next pipes() call. Flip to True, reload the pipe once, then set back to False. "
                "Useful after changing CUSTOM_MODEL_IMAGES or switching logo sources."
            ),
        )
        PURGE_STALE_MODELS: bool = Field(
            default=True,
            description=(
                "When True, automatically deletes models from the Open WebUI DB that no longer "
                "appear in the CometAPI catalog. This keeps the model list clean and prevents "
                "old/renamed models from lingering. Runs on every pipes() call."
            ),
        )
        CUSTOM_MODEL_IMAGES: str = Field(
            default="",
            description=(
                "JSON object mapping model IDs to custom image URLs. Each key is a model ID "
                "(or a substring it contains) and each value is an https:// or data:image/... URL. "
                "Custom entries override the automatically-fetched provider logo for those models only. "
                'Example: {"gpt-4o": "https://cdn.example.com/gpt4o.png", "claude": "https://cdn.example.com/claude.png"}. '
                "Requires SYNC_MODEL_ICONS=True. Leave empty to use auto-fetched logos for all models."
            ),
        )
    def __init__(self):
        self.valves = self.Valves()
        self.type = "manifold"
        self.name = ""

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.valves.API_KEY}",
            "Content-Type": "application/json",
        }

    def _session(self) -> aiohttp.ClientSession:
        timeout = aiohttp.ClientTimeout(
            total=self.valves.REQUEST_TIMEOUT,
            connect=10,  # fail fast on connection refused
        )
        return aiohttp.ClientSession(
            headers=self._headers(),
            timeout=timeout,
            connector=_get_connector(),
            connector_owner=False,  # keep the shared connector alive
            read_bufsize=2**16,  # 64 KB read buffer — reduces per-chunk overhead
        )

    def _should_include(self, model_id: str) -> bool:
        f = self.valves.MODEL_FILTER
        if f == "all":
            return True
        t = _model_type(model_id)
        if f == "text":
            return t == "text"
        if f == "image":
            return t == "image"
        if f == "video":
            return t == "video"
        if f == "image_video":
            return t in ("image", "video")
        return True

    async def _sync_exa_tool(self) -> None:
        """Auto-register the bundled Exa search tool in Open WebUI's tools DB (OWU v0.8.5+)."""
        global _EXA_TOOL_REGISTERED
        if _EXA_TOOL_REGISTERED:
            return
        try:
            import inspect
            from open_webui.models.tools import Tools as OWUTools, ToolForm, ToolMeta
            from open_webui.models.users import Users
        except ImportError:
            _EXA_TOOL_REGISTERED = True  # not in OWU, skip forever
            return

        TOOL_ID = "exa_search"
        try:
            if OWUTools.get_tool_by_id(TOOL_ID):
                _EXA_TOOL_REGISTERED = True
                return  # already exists
        except Exception:
            pass

        try:
            admin = Users.get_first_user()
            if not admin:
                return
        except Exception as e:
            print(f"[CometAPI] _sync_exa_tool: failed to get admin user: {e}", flush=True)
            return

        # Build standalone source: required imports + the Tools class body.
        tool_imports = (
            "from __future__ import annotations\n"
            "import asyncio\n"
            "import aiohttp\n"
            "from typing import Any, Awaitable, Callable, Optional\n"
            "from pydantic import BaseModel, Field\n\n"
        )
        try:
            tool_source = inspect.getsource(Tools)
        except Exception as e:
            print(f"[CometAPI] Could not extract Tools source for auto-registration: {e}", flush=True)
            return

        content = tool_imports + tool_source

        try:
            OWUTools.insert_new_tool(
                admin.id,
                ToolForm(
                    id=TOOL_ID,
                    name="Exa Neural Web Search",
                    content=content,
                    meta=ToolMeta(
                        description=(
                            "Neural web search powered by Exa.ai. "
                            "Set EXA_API_KEY in the tool valves to activate."
                        ),
                        manifest={},
                    ),
                ),
            )
            print("[CometAPI] Auto-registered Exa search tool (id=exa_search)", flush=True)
            _EXA_TOOL_REGISTERED = True
        except Exception as e:
            print(f"[CometAPI] Failed to auto-register Exa tool: {e}", flush=True)

    async def _sync_model_images(self, models: list[dict[str, Any]]) -> None:
        """Write provider logo URLs and descriptions into Open WebUI's models DB (requires OWU v0.8.5+)."""
        try:
            from open_webui.models.models import Models, ModelForm
            from open_webui.models.users import Users
        except ImportError:
            return  # Running outside Open WebUI

        force_reset = bool(self.valves.RESET_MODEL_IMAGES)
        cache_buster = f"?t={int(time.time())}" if force_reset else ""
        if force_reset:
            _IMAGE_SYNCED.clear()
            print("[CometAPI] RESET_MODEL_IMAGES=True — force-refreshing all model images", flush=True)

        # Parse per-model custom image overrides (JSON: id-substring → url).
        _custom_map: dict[str, str] = {}
        _raw_custom = (getattr(self.valves, "CUSTOM_MODEL_IMAGES", "") or "").strip()
        if _raw_custom:
            try:
                parsed = json.loads(_raw_custom)
                if isinstance(parsed, dict):
                    _custom_map = {
                        k.strip(): v.strip()
                        for k, v in parsed.items()
                        if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip()
                    }
                    if _custom_map:
                        print(f"[CometAPI] CUSTOM_MODEL_IMAGES: {len(_custom_map)} override(s) loaded", flush=True)
            except Exception:
                print("[CometAPI] CUSTOM_MODEL_IMAGES is not valid JSON — skipping", flush=True)

        try:
            admin = Users.get_first_user()
            if not admin:
                print("[CometAPI] _sync_model_images: no admin user found", flush=True)
                return
        except Exception as e:
            print(f"[CometAPI] _sync_model_images: failed to get admin user: {e}", flush=True)
            return

        updates = 0
        inserts = 0

        for m in models:
            full_id = f"{self.valves.FUNCTION_ID}.{m['id']}"
            if full_id in _IMAGE_SYNCED:
                continue

            model_meta = m.get("meta") or {}
            model_id_lower = m["id"].lower()

            # Custom logo: longest matching key wins.
            custom_logo = ""
            if _custom_map:
                best_key = max(
                    (k for k in _custom_map if k.lower() in model_id_lower),
                    key=len,
                    default="",
                )
                if best_key:
                    custom_logo = _custom_map[best_key]

            logo_url = custom_logo or model_meta.get("profile_image_url", "")
            if logo_url and cache_buster and "?" not in logo_url:
                logo_url += cache_buster
            description = model_meta.get("description", "")

            try:
                existing = Models.get_model_by_id(full_id)
                if existing:
                    new_meta = existing.meta.model_dump() if existing.meta else {}
                    existing_params = existing.params.model_dump() if existing.params else {}

                    changed = False
                    if logo_url and (force_reset or new_meta.get("profile_image_url") != logo_url):
                        new_meta["profile_image_url"] = logo_url
                        changed = True
                    if description and new_meta.get("description") != description:
                        new_meta["description"] = description
                        changed = True
                    if "exa_search" not in (new_meta.get("toolIds") or []):
                        new_meta["toolIds"] = list(set((new_meta.get("toolIds") or []) + ["exa_search"]))
                        changed = True

                    if changed:
                        Models.update_model_by_id(
                            full_id,
                            ModelForm(**{**existing.model_dump(), "meta": new_meta, "params": existing_params}),
                        )
                        updates += 1
                        print(f"[CometAPI] Updated {full_id}: icon={logo_url[:80] if logo_url else '(none)'}", flush=True)
                else:
                    insert_meta: dict[str, Any] = {}
                    if logo_url:
                        insert_meta["profile_image_url"] = logo_url
                    if description:
                        insert_meta["description"] = description
                    insert_meta["toolIds"] = ["exa_search"]
                    Models.insert_new_model(
                        ModelForm(id=full_id, name=m["name"], meta=insert_meta, params={}),
                        admin.id,
                    )
                    inserts += 1
                    print(f"[CometAPI] Inserted {full_id}: icon={logo_url[:80] if logo_url else '(none)'}", flush=True)
                _IMAGE_SYNCED.add(full_id)
            except Exception as e:
                print(f"[CometAPI] sync failed for {full_id}: {e}", flush=True)

        if updates or inserts:
            print(f"[CometAPI] icon/desc sync: {updates} updated, {inserts} inserted", flush=True)

        # ── Purge stale models no longer in the catalog ──
        if self.valves.PURGE_STALE_MODELS:
            prefix = f"{self.valves.FUNCTION_ID}."
            current_ids = {f"{self.valves.FUNCTION_ID}.{m['id']}" for m in models}
            deleted = 0
            try:
                for db_model in Models.get_all_models():
                    if db_model.id.startswith(prefix) and db_model.id not in current_ids:
                        Models.delete_model_by_id(db_model.id)
                        _IMAGE_SYNCED.discard(db_model.id)
                        deleted += 1
            except Exception as e:
                print(f"[CometAPI] stale model purge failed: {e}", flush=True)
            if deleted:
                print(f"[CometAPI] purged {deleted} stale model(s) from DB", flush=True)

    async def pipes(self) -> list[dict[str, Any]]:
        if not self.valves.API_KEY:
            return [{"id": "no_key", "name": "Set API_KEY in valve settings"}]

        catalog_url = f"{self.valves.BASE_URL.rstrip('/')}/v1/models"
        try:
            async with self._session() as session:
                async with session.get(catalog_url) as resp:
                    resp.raise_for_status()
                    payload = await resp.json()
        except Exception as exc:
            return [{"id": "error", "name": f"Catalog fetch failed: {exc}"}]

        models: list[dict[str, Any]] = []
        has_descriptions = 0
        for item in payload.get("data", []):
            mid = item.get("id", "")
            if not mid or not self._should_include(mid):
                continue
            provider = _model_provider(mid)
            catalog_desc = (
                item.get("description")
                or (item.get("meta") or {}).get("description")
                or ""
            )
            if catalog_desc:
                has_descriptions += 1
            description = catalog_desc

            # ── Per-model image resolution (most-specific source wins) ────────
            # 1. Catalog item may carry its own icon/image field
            catalog_icon: str = ""
            for _field in (
                "icon",
                "icon_url",
                "image",
                "image_url",
                "logo",
                "logo_url",
                "thumbnail",
            ):
                _candidate = (
                    item.get(_field) or (item.get("meta") or {}).get(_field) or ""
                )
                if isinstance(_candidate, str) and _candidate.startswith(
                    ("http", "data:image")
                ):
                    catalog_icon = _candidate
                    break
            # 2. Always fall back to Clearbit per-provider logo (independent of DB sync)
            icon_url = catalog_icon or _provider_logo(provider)

            # ── Pretty display name ───────────────────────────────────────────
            raw_name = item.get("name") or mid
            display_name = _pretty_model_name(
                raw_name,
                mid,
                getattr(self.valves, "MODEL_NAME_FORMAT", "raw"),
                getattr(self.valves, "MODEL_NAME_PREFIX", ""),
            )

            models.append(
                {
                    "id": mid,
                    "name": display_name,
                    "meta": {
                        "profile_image_url": icon_url,
                        "description": description,
                    },
                }
            )

        models.sort(key=lambda m: m["id"])
        print(
            f"[CometAPI] pipes(): {len(models)} models, {has_descriptions} with catalog descriptions",
            flush=True,
        )
        # Log a sample of model icons for debugging image source issues
        if models:
            sample_size = min(5, len(models))
            for sample_m in models[:sample_size]:
                icon = sample_m["meta"].get("profile_image_url", "")
                print(f"[CometAPI] pipes() sample: {sample_m['id']:<30} -> icon={icon[:80]}", flush=True)
        if self.valves.SYNC_MODEL_ICONS:
            try:
                await self._sync_exa_tool()
            except Exception as e:
                print(f"[CometAPI] WARNING: _sync_exa_tool failed: {e}", flush=True)
            try:
                await self._sync_model_images(models)
            except Exception as sync_err:
                print(f"[CometAPI] WARNING: _sync_model_images failed: {sync_err}", flush=True)
                print(f"[CometAPI] Consider disabling SYNC_MODEL_ICONS if this persists", flush=True)
        return models

    async def _image_pipe(
        self,
        model: str,
        body: dict[str, Any],
        __event_emitter__: Callable[[dict[str, Any]], Awaitable[Any]] | None,
    ) -> AsyncGenerator[str, None]:
        """Submit a Kling image generation job, poll until done, yield inline image(s)."""

        prompt = ""
        for msg in reversed(body.get("messages", [])):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    prompt = content
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            prompt = part.get("text", "")
                            break
                break

        if not prompt:
            yield "Could not extract a prompt from your message."
            return

        base = self.valves.BASE_URL.rstrip("/")
        kling_model = self.valves.KLING_IMAGE_MODEL
        kling_payload: dict[str, Any] = {"prompt": prompt, "model_name": kling_model}
        for key in ("negative_prompt", "image", "image_fidelity", "n", "aspect_ratio"):
            if key in body:
                kling_payload[key] = body[key]

        create_url = f"{base}/kling/v1/images/generations"

        async def _emit(desc: str, done: bool = False) -> None:
            if __event_emitter__:
                await __event_emitter__(
                    {"type": "status", "data": {"description": desc, "done": done}}
                )

        await _emit(f"Submitting image job ({model})...")

        try:
            async with self._session() as session:
                async with session.post(create_url, json=kling_payload) as resp:
                    if resp.status >= 400:
                        err = await resp.text()
                        yield f"Submit failed ({resp.status}): {err}"
                        return
                    job = await resp.json()
        except Exception as exc:
            yield f"Submit request failed: {exc}"
            return

        data = job.get("data") or {}
        task_id = data.get("task_id")
        kling_status = data.get("task_status", "")

        if not task_id:
            yield f"No task_id in response: {job}"
            return

        poll_url = f"{base}/kling/v1/images/generations/{task_id}"
        poll_timeout = aiohttp.ClientTimeout(total=90)
        start = time.time()
        poll_fails = 0
        MAX_POLL_FAILS = 5

        while True:
            elapsed = time.time() - start

            if kling_status in ("succeed", "completed", "success"):
                result = data.get("task_result") or {}
                images = result.get("images") or []
                img_lines = [
                    f"![Generated Image]({img['url']})"
                    for img in images
                    if img.get("url")
                ]
                if not img_lines:
                    img_lines = [f"Image ready but no URL found. Task ID: `{task_id}`"]
                await _emit(f"Image completed! ({elapsed:.0f}s)", done=True)
                yield (
                    f"**Image ready!** *(job `{task_id}`, {elapsed:.0f}s, model `{kling_model}`)*\n\n"
                    + "\n\n".join(img_lines)
                )
                return

            if kling_status in ("failed", "error", "cancelled"):
                msg = data.get("task_status_msg") or data
                await _emit("Image generation failed.", done=True)
                yield f"Image generation failed.\n\n- Task ID: `{task_id}`\n- Details: {msg}"
                return

            if elapsed >= self.valves.VIDEO_JOB_TIMEOUT:
                await _emit(
                    f"Timed out after {self.valves.VIDEO_JOB_TIMEOUT}s.", done=True
                )
                yield (
                    f"Image timed out after {self.valves.VIDEO_JOB_TIMEOUT}s.\n\n"
                    f"- Task ID: `{task_id}`\n"
                    f"- Last status: `{kling_status}`\n\n"
                    f"Check manually: `GET {poll_url}`"
                )
                return

            await _emit(f"Status: {kling_status or 'submitted'}... ({elapsed:.0f}s)")
            await asyncio.sleep(self.valves.VIDEO_POLL_INTERVAL)

            try:
                async with aiohttp.ClientSession(
                    headers=self._headers(), timeout=poll_timeout
                ) as session:
                    async with session.get(poll_url) as resp:
                        if resp.status >= 400:
                            err = await resp.text()
                            yield f"Poll failed ({resp.status}): {err}"
                            return
                        job = await resp.json()
                        data = job.get("data") or {}
                        kling_status = data.get("task_status", "")
                poll_fails = 0  # reset on success
            except Exception as exc:
                poll_fails += 1
                if poll_fails >= MAX_POLL_FAILS:
                    yield f"Poll failed {MAX_POLL_FAILS} times in a row: {exc}"
                    return
                await _emit(f"Poll error (retry {poll_fails}/{MAX_POLL_FAILS}): {exc}")
                await asyncio.sleep(self.valves.VIDEO_POLL_INTERVAL * poll_fails)

    async def _video_pipe(
        self,
        model: str,
        body: dict[str, Any],
        __event_emitter__: Callable[[dict[str, Any]], Awaitable[Any]] | None,
    ) -> AsyncGenerator[str, None]:
        """Submit a video generation job to /v1/videos, poll until done, yield a download link."""

        # Extract prompt from the last user message (handles plain string & multimodal content)
        prompt = ""
        for msg in reversed(body.get("messages", [])):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    prompt = content
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            prompt = part.get("text", "")
                            break
                break

        if not prompt:
            yield "Could not extract a prompt from your message."
            return

        payload: dict[str, Any] = {"model": model, "prompt": prompt}
        # Forward optional video params if the caller included them in body
        for key in ("seconds", "size", "image"):
            if key in body:
                payload[key] = body[key]

        base = self.valves.BASE_URL.rstrip("/")
        submit_url = f"{base}/v1/videos"

        async def _emit(desc: str, done: bool = False) -> None:
            if __event_emitter__:
                await __event_emitter__(
                    {"type": "status", "data": {"description": desc, "done": done}}
                )

        await _emit(f"Submitting video job ({model})...")

        # ── Kling: uses its own /kling/v1/videos/text2video endpoint ──────────
        if "kling" in model.lower():
            kling_model = self.valves.KLING_VIDEO_MODEL
            kling_payload: dict[str, Any] = {
                "prompt": prompt,
                "model_name": kling_model,
            }
            if "image" in body:
                kling_payload["image"] = body["image"]
            if "duration" in body:
                kling_payload["duration"] = body["duration"]
            if "aspect_ratio" in body:
                kling_payload["aspect_ratio"] = body["aspect_ratio"]
            if "mode" in body:
                kling_payload["mode"] = body["mode"]

            kling_create_url = f"{base}/kling/v1/videos/text2video"
            try:
                async with self._session() as session:
                    async with session.post(
                        kling_create_url, json=kling_payload
                    ) as resp:
                        if resp.status >= 400:
                            err = await resp.text()
                            yield f"Submit failed ({resp.status}): {err}"
                            return
                        job = await resp.json()
            except Exception as exc:
                yield f"Submit request failed: {exc}"
                return

            # Kling wraps the result under "data"
            data = job.get("data") or {}
            task_id = data.get("task_id")
            kling_status = (
                data.get("task_status")
                or data.get("status")
                or job.get("task_status")
                or job.get("status")
                or ""
            )
            print(
                f"[CometAPI] Kling video submit response: {json.dumps(job)[:500]}",
                flush=True,
            )

            if not task_id:
                yield f"No task_id in response: {job}"
                return

            kling_poll_url = f"{base}/kling/v1/videos/text2video/{task_id}"
            poll_timeout = aiohttp.ClientTimeout(total=90)
            start = time.time()
            poll_fails = 0
            MAX_POLL_FAILS = 5

            while True:
                elapsed = time.time() - start

                if kling_status in ("succeed", "completed", "success"):
                    result = data.get("task_result") or {}
                    videos = result.get("videos") or []
                    video_url = videos[0].get("url") if videos else ""
                    if not video_url:
                        video_url = f"{base}/kling/v1/videos/text2video/{task_id}"
                    await _emit(f"Video completed! ({elapsed:.0f}s)", done=True)
                    yield (
                        f"**Video ready!** *(job `{task_id}`, {elapsed:.0f}s, model `{kling_model}`)*\n\n"
                        f"[\u25b6 Download Video]({video_url})"
                    )
                    return

                if kling_status in ("failed", "error", "cancelled"):
                    msg = data.get("task_status_msg") or data
                    await _emit("Video generation failed.", done=True)
                    yield f"Video generation failed.\n\n- Task ID: `{task_id}`\n- Details: {msg}"
                    return

                if elapsed >= self.valves.VIDEO_JOB_TIMEOUT:
                    await _emit(
                        f"Timed out after {self.valves.VIDEO_JOB_TIMEOUT}s.", done=True
                    )
                    yield (
                        f"Video timed out after {self.valves.VIDEO_JOB_TIMEOUT}s.\n\n"
                        f"- Task ID: `{task_id}`\n"
                        f"- Last status: `{kling_status}`\n\n"
                        f"Check manually: `GET {kling_poll_url}`"
                    )
                    return

                await _emit(
                    f"Status: {kling_status or 'submitted'}... ({elapsed:.0f}s)"
                )
                await asyncio.sleep(self.valves.VIDEO_POLL_INTERVAL)

                try:
                    async with aiohttp.ClientSession(
                        headers=self._headers(), timeout=poll_timeout
                    ) as session:
                        async with session.get(kling_poll_url) as resp:
                            if resp.status >= 400:
                                err = await resp.text()
                                yield f"Poll failed ({resp.status}): {err}"
                                return
                            job = await resp.json()
                            print(
                                f"[CometAPI] Kling video poll response: {json.dumps(job)[:500]}",
                                flush=True,
                            )
                            data = job.get("data") or {}
                            kling_status = (
                                data.get("task_status")
                                or data.get("status")
                                or job.get("task_status")
                                or job.get("status")
                                or ""
                            )
                    poll_fails = 0  # reset on success
                except Exception as exc:
                    poll_fails += 1
                    if poll_fails >= MAX_POLL_FAILS:
                        yield f"Poll failed {MAX_POLL_FAILS} times in a row: {exc}"
                        return
                    await _emit(
                        f"Poll error (retry {poll_fails}/{MAX_POLL_FAILS}): {exc}"
                    )
                    await asyncio.sleep(self.valves.VIDEO_POLL_INTERVAL * poll_fails)
        # ── end Kling ──────────────────────────────────────────────────────────

        else:
            # Generic /v1/videos flow (Sora, Veo, etc.)
            try:
                async with self._session() as session:
                    async with session.post(submit_url, json=payload) as resp:
                        if resp.status >= 400:
                            err = await resp.text()
                            yield f"Submit failed ({resp.status}): {err}"
                            return
                        job = await resp.json()
            except Exception as exc:
                yield f"Submit request failed: {exc}"
                return

            video_id = job.get("id")
            status = job.get("status", "")

            if not video_id:
                yield f"No video ID in response: {job}"
                return

            poll_url = f"{base}/v1/videos/{video_id}"
            poll_timeout = aiohttp.ClientTimeout(total=90)
            start = time.time()
            poll_fails = 0
            MAX_POLL_FAILS = 5

            while True:
                elapsed = time.time() - start

                if status == "completed":
                    video_url = (
                        job.get("url")
                        or job.get("video_url")
                        or job.get("output_url")
                        or job.get("content_url")
                        or job.get("result")
                        or job.get("download_url")
                        or (job.get("output") or {}).get("url")
                        or (job.get("data") or [{}])[0].get("url")
                        if isinstance(job.get("data"), list)
                        else None or f"{base}/v1/videos/{video_id}/content"
                    )
                    await _emit(f"Video completed! ({elapsed:.0f}s)", done=True)
                    needs_auth = str(video_url).startswith(base) and "/content" in str(
                        video_url
                    )
                    if needs_auth:
                        # Fetch the video using Bearer auth so the key never appears in the URL.
                        # Return the data URL as text for the user to copy and paste into browser.
                        try:
                            async with self._session() as dl_session:
                                async with dl_session.get(str(video_url)) as vresp:
                                    if vresp.status >= 400:
                                        err = await vresp.text()
                                        yield f"Video download failed ({vresp.status}): {err}"
                                        return
                                    content_type = vresp.headers.get(
                                        "Content-Type", "video/mp4"
                                    ).split(";")[0]
                                    video_bytes = await vresp.read()
                            b64 = base64.b64encode(video_bytes).decode()
                            data_url = f"data:{content_type};base64,{b64}"
                            yield (
                                f"**Video ready!** *(job `{video_id}`, {elapsed:.0f}s)*\n\n"
                                f"Video URL: `{data_url}`\n\n"
                                f"Copy and paste this URL into your browser to view the video."
                            )
                        except Exception as exc:
                            yield f"Video fetch failed: {exc}"
                        return
                    yield (
                        f"**Video ready!** *(job `{video_id}`, {elapsed:.0f}s)*\n\n"
                        f"[\u25b6 Download Video]({video_url})"
                    )
                    return

                if status == "failed":
                    err = job.get("error") or job
                    await _emit("Video generation failed.", done=True)
                    yield f"Video generation failed.\n\n- Job ID: `{video_id}`\n- Details: {err}"
                    return

                if elapsed >= self.valves.VIDEO_JOB_TIMEOUT:
                    await _emit(
                        f"Timed out after {self.valves.VIDEO_JOB_TIMEOUT}s.", done=True
                    )
                    yield (
                        f"Video timed out after {self.valves.VIDEO_JOB_TIMEOUT}s.\n\n"
                        f"- Job ID: `{video_id}`\n"
                        f"- Last status: `{status}`\n\n"
                        f"Check manually: `GET {poll_url}`"
                    )
                    return

                await _emit(f"Status: {status or 'processing'}... ({elapsed:.0f}s)")
                await asyncio.sleep(self.valves.VIDEO_POLL_INTERVAL)

                try:
                    async with aiohttp.ClientSession(
                        headers=self._headers(), timeout=poll_timeout
                    ) as session:
                        async with session.get(poll_url) as resp:
                            if resp.status >= 400:
                                err = await resp.text()
                                yield f"Poll failed ({resp.status}): {err}"
                                return
                            job = await resp.json()
                            status = job.get("status", "")
                    poll_fails = 0  # reset on success
                except Exception as exc:
                    poll_fails += 1
                    if poll_fails >= MAX_POLL_FAILS:
                        yield f"Poll failed {MAX_POLL_FAILS} times in a row: {exc}"
                        return
                    await _emit(
                        f"Poll error (retry {poll_fails}/{MAX_POLL_FAILS}): {exc}"
                    )
                    await asyncio.sleep(self.valves.VIDEO_POLL_INTERVAL * poll_fails)

    async def pipe(
        self,
        body: dict[str, Any],
        __user__: dict[str, Any] | None = None,
        __event_emitter__: Callable[[dict[str, Any]], Awaitable[Any]] | None = None,
        **_kwargs: Any,
    ) -> AsyncGenerator[str, None] | str:
        if not self.valves.API_KEY:
            yield "API key not set. Configure API_KEY in valve settings."
            return

        model: str = body.get("model", "")
        if "." in model:
            model = model.split(".", 1)[1]

        start_time = time.time()
        usage: dict[str, Any] = {}

        # For image/video models we linkify URLs in each chunk as it arrives.
        model_type = _model_type(model)
        linkify = model_type in ("video", "image")

        # Route video models through the dedicated /v1/videos polling path.
        if model_type == "video":
            async for chunk in self._video_pipe(model, body, __event_emitter__):
                yield chunk
            return

        # Route Kling image models through the dedicated polling path.
        if model_type == "image" and "kling" in model.lower():
            async for chunk in self._image_pipe(model, body, __event_emitter__):
                yield chunk
            return

        # Determine endpoint: per-model responses API or default chat completions
        responses_models = [
            m.strip().lower()
            for m in self.valves.RESPONSES_API_MODELS.split(",")
            if m.strip()
        ]
        use_responses = (
            any(r in model.lower() for r in responses_models)
            if responses_models
            else False
        )

        if use_responses:
            # ── /v1/responses (Responses API) ─────────────────────────────────
            url = f"{self.valves.BASE_URL.rstrip('/')}/v1/responses"
            # Responses API uses "input" instead of "messages"
            messages = body.get("messages", [])
            payload: dict[str, Any] = {
                "model": model,
                "input": messages,
                "stream": True,
            }
            for key in (
                "temperature",
                "max_tokens",
                "max_output_tokens",
                "top_p",
                "frequency_penalty",
                "presence_penalty",
                "store",
            ):
                if key in body:
                    payload[key] = body[key]

            try:
                async with self._session() as session:
                    async with session.post(url, json=payload) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            yield f"API error {resp.status}: {error_text}"
                            return

                        current_event = ""
                        async for raw_line in resp.content:
                            line = raw_line.decode("utf-8", errors="replace").strip()
                            if not line:
                                current_event = ""
                                continue
                            if line.startswith("event: "):
                                current_event = line[7:].strip()
                                continue
                            if not line.startswith("data: "):
                                continue
                            raw = line[6:]
                            if raw == "[DONE]":
                                continue
                            try:
                                chunk = json.loads(raw)
                            except json.JSONDecodeError:
                                continue

                            # Named-event style (OpenAI Responses API)
                            event_type = current_event or chunk.get("type", "")
                            if event_type == "response.output_text.delta":
                                delta = chunk.get("delta", "")
                                yield (
                                    _format_media_response(delta, model_type)
                                    if linkify
                                    else delta
                                )
                            elif event_type == "response.completed":
                                usage = chunk.get("response", {}).get("usage", {})

            except asyncio.TimeoutError:
                yield "\n\nRequest timed out."
                return
            except Exception as exc:
                yield f"\n\nRequest failed: {exc}"
                return

        else:
            # ── /v1/chat/completions (default) ────────────────────────────────
            url = f"{self.valves.BASE_URL.rstrip('/')}/v1/chat/completions"
            payload = {**body, "model": model, "stream": True}

            try:
                async with self._session() as session:
                    async with session.post(url, json=payload) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            yield f"API error {resp.status}: {error_text}"
                            return

                        async for raw_line in resp.content:
                            line = raw_line.decode("utf-8", errors="replace").strip()
                            if not line or line == "data: [DONE]":
                                continue
                            if not line.startswith("data: "):
                                continue
                            try:
                                chunk = json.loads(line[6:])
                            except json.JSONDecodeError:
                                continue

                            if chunk.get("usage"):
                                usage = chunk["usage"]

                            for choice in chunk.get("choices", []):
                                # In streaming mode only read delta.content.
                                # Some APIs (including CometAPI) also include a
                                # message.content field in the final chunk that
                                # contains the full text — reading it would
                                # duplicate the entire response.
                                content = (choice.get("delta") or {}).get(
                                    "content"
                                ) or ""
                                if content:
                                    yield (
                                        _format_media_response(content, model_type)
                                        if linkify
                                        else content
                                    )

            except asyncio.TimeoutError:
                yield "\n\nRequest timed out."
                return
            except Exception as exc:
                yield f"\n\nRequest failed: {exc}"
                return

        elapsed = time.time() - start_time

        # Log full usage dict so we can see exactly what CometAPI returns
        if usage:
            print(f"[CometAPI] usage dict: {usage}", flush=True)

        input_tok = usage.get("prompt_tokens") or usage.get("input_tokens")
        output_tok = usage.get("completion_tokens") or usage.get("output_tokens")
        # Try every known field name CometAPI might use for cost
        _cost_fields = (
            "cost",
            "total_cost",
            "price",
            "total_price",
            "required_cost",
            "estimated_cost",
            "charge",
            "amount",
            "total_amount",
            "fee",
            "credit",
            "credits_used",
            "usage_cost",
            "billing_cost",
            "tokens_cost",
            "token_cost",
        )
        cost_val: Any = None
        for _cf in _cost_fields:
            _v = usage.get(_cf)
            if _v is not None and _v != 0 and _v != "0" and _v != "0.0":
                cost_val = _v
                break
        # Fallback: sum split cost fields
        if cost_val is None:
            _pc = usage.get("prompt_cost") or usage.get("input_cost") or 0
            _cc = usage.get("completion_cost") or usage.get("output_cost") or 0
            if _pc or _cc:
                cost_val = _pc + _cc
        cost_str = _format_cost(cost_val)

        # ── Status-bar indicator ───────────────────────────────────────────────
        if __event_emitter__ and self.valves.SHOW_USAGE_STATUS:
            status_parts: list[str] = [f"Time: {elapsed:.2f}s"]
            if input_tok is not None or output_tok is not None:
                tok_str = ""
                if input_tok is not None:
                    tok_str += f"In: {input_tok}"
                if output_tok is not None:
                    tok_str += f" Out: {output_tok}"
                status_parts.append(tok_str.strip())
            if cost_str:
                status_parts.append(f"Cost {cost_str}")
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "  |  ".join(status_parts), "done": True},
                }
            )


# ── Exa Neural Web Search Tool ────────────────────────────────────────────────
# Bundled alongside the CometAPI manifold so users only need to install one file.
# In Open WebUI: Workspace → Tools → Import this file, then set EXA_API_KEY.
class Tools:
    class Valves(BaseModel):
        EXA_API_KEY: str = Field(
            default="",
            description="Your Exa API key. Get one free at https://dashboard.exa.ai",
        )
        MAX_RESULTS: int = Field(
            default=5,
            description="Number of search results to return (1–10).",
        )
        USE_AUTOPROMPT: bool = Field(
            default=True,
            description="Let Exa automatically optimise your query for neural search.",
        )
        INCLUDE_CONTENTS: bool = Field(
            default=True,
            description="Fetch and include page text content in each result.",
        )
        CONTENTS_MAX_CHARS: int = Field(
            default=1500,
            description="Maximum characters of page content to include per result.",
        )
        SEARCH_TYPE: str = Field(
            default="auto",
            description=(
                "Search mode:\n"
                "  auto    - Exa chooses the best type automatically (recommended)\n"
                "  neural  - semantic / meaning-based search\n"
                "  keyword - traditional keyword search"
            ),
        )
        INCLUDE_DOMAINS: str = Field(
            default="",
            description=(
                "Comma-separated list of domains to restrict results to "
                "(e.g. 'arxiv.org, github.com'). Leave empty for unrestricted search."
            ),
        )
        EXCLUDE_DOMAINS: str = Field(
            default="",
            description=(
                "Comma-separated list of domains to exclude from results "
                "(e.g. 'pinterest.com, quora.com'). Leave empty to exclude nothing."
            ),
        )

    def __init__(self):
        self.valves = self.Valves()

    async def search(
        self,
        query: str,
        __event_emitter__: Optional[Callable[[dict[str, Any]], Awaitable[Any]]] = None,
    ) -> str:
        """
        Search the web using Exa's neural search API and return rich results.

        :param query: The search query or question to look up.
        :return: Formatted search results with titles, URLs, dates, and content snippets.
        """
        exa_key = self.valves.EXA_API_KEY
        if not exa_key:
            return (
                "\u26a0\ufe0f Exa API key is not set. Enter it in the **EXA_API_KEY** valve "
                "in the Exa Search tool settings. "
                "Get a free key at https://dashboard.exa.ai"
            )

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"Searching Exa: {query}", "done": False},
                }
            )

        headers = {
            "x-api-key": exa_key,
            "Content-Type": "application/json",
        }

        exa_payload: dict[str, Any] = {
            "query": query,
            "numResults": max(1, min(10, self.valves.MAX_RESULTS)),
            "useAutoprompt": self.valves.USE_AUTOPROMPT,
        }

        if self.valves.SEARCH_TYPE and self.valves.SEARCH_TYPE != "auto":
            exa_payload["type"] = self.valves.SEARCH_TYPE

        include_domains = [
            d.strip() for d in self.valves.INCLUDE_DOMAINS.split(",") if d.strip()
        ]
        exclude_domains = [
            d.strip() for d in self.valves.EXCLUDE_DOMAINS.split(",") if d.strip()
        ]
        if include_domains:
            exa_payload["includeDomains"] = include_domains
        if exclude_domains:
            exa_payload["excludeDomains"] = exclude_domains

        if self.valves.INCLUDE_CONTENTS:
            exa_payload["contents"] = {
                "text": {"maxCharacters": self.valves.CONTENTS_MAX_CHARS},
                "highlights": {"numSentences": 2, "highlightsPerUrl": 1},
            }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.exa.ai/search",
                    headers=headers,
                    json=exa_payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        error_body = await resp.text()
                        if __event_emitter__:
                            await __event_emitter__(
                                {
                                    "type": "status",
                                    "data": {
                                        "description": "Exa search failed.",
                                        "done": True,
                                    },
                                }
                            )
                        return f"Exa search failed (HTTP {resp.status}): {error_body}"
                    exa_data = await resp.json()
        except asyncio.TimeoutError:
            return "Exa search timed out after 30 seconds."
        except Exception as exc:
            return f"Exa search error: {exc}"

        results = exa_data.get("results", [])

        if not results:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "No results found.", "done": True},
                    }
                )
            return f'No results found for "{query}".'

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Found {len(results)} result(s) for: {query}",
                        "done": True,
                    },
                }
            )

        lines: list[str] = [f"## Exa Search Results\n**Query:** {query}\n"]

        for i, r in enumerate(results, 1):
            title = r.get("title") or "Untitled"
            url = r.get("url") or ""
            published = r.get("publishedDate") or r.get("published_date") or ""
            author = r.get("author") or ""
            score = r.get("score")

            highlights = r.get("highlights") or []
            text = " \u2026 ".join(highlights) if highlights else (r.get("text") or "")
            if text and len(text) > self.valves.CONTENTS_MAX_CHARS:
                text = text[: self.valves.CONTENTS_MAX_CHARS] + " \u2026"

            header = f"### {i}. [{title}]({url})"
            meta_parts: list[str] = []
            if published:
                meta_parts.append(f"\U0001f4c5 {published[:10]}")
            if author:
                meta_parts.append(f"\u270d\ufe0f {author}")
            if score is not None:
                meta_parts.append(f"relevance: {score:.3f}")
            meta = (
                "  \n" + " &nbsp;\u00b7&nbsp; ".join(meta_parts) if meta_parts else ""
            )

            entry = header + meta
            if text:
                entry += f"\n\n{text}"

            lines.append(entry)

        return "\n\n---\n\n".join(lines)
