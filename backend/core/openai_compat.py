"""Compatibility helpers for OpenAI-compatible clients."""

from typing import Optional

import httpx
import openai


def create_openai_client(
    api_key: str,
    base_url: Optional[str] = None,
    timeout: float = 30.0,
):
    """Create an OpenAI client across openai/httpx version combinations.

    openai 1.x before the httpx 0.28 compatibility update can fail during
    construction with: Client.__init__() got an unexpected keyword argument
    'proxies'. Supplying a plain httpx.Client bypasses that older default
    client path while remaining compatible with newer openai releases.
    """
    kwargs = {
        "api_key": api_key,
        "timeout": timeout,
        "http_client": httpx.Client(timeout=timeout),
    }
    if base_url:
        kwargs["base_url"] = base_url.rstrip("/")
    return openai.OpenAI(**kwargs)
