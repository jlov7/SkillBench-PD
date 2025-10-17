from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderResult:
    output: str
    tokens_in: Optional[int]
    tokens_out: Optional[int]
    latency_ms: float


class BaseProvider(ABC):
    """Abstract provider interface so the harness can call different backends."""

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def infer(self, prompt: str) -> ProviderResult:
        raise NotImplementedError


class MockProvider(BaseProvider):
    """Deterministic mock provider that fabricates outputs for repeatable tests."""

    def __init__(self, model: str = "mock-model"):
        super().__init__(model)

    def infer(self, prompt: str) -> ProviderResult:
        t0 = time.perf_counter()
        output = self._craft_output(prompt)
        latency_ms = (time.perf_counter() - t0) * 1000
        tokens_in = self._estimate_tokens(prompt)
        tokens_out = self._estimate_tokens(output)
        return ProviderResult(output=output, tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=latency_ms)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        # Simple heuristic: 1 token ≈ 4 characters, but keep >=1
        return max(1, len(text.strip()) // 4)

    @staticmethod
    def _craft_output(prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "rewrite the sentence" in prompt_lower or "brand voice" in prompt_lower:
            return (
                "We are announcing a focused feature that improves daily workflows. "
                "It is reliable, practical, and ready for teams."
            )
        if "reformat the following policy text" in prompt_lower or "policy" in prompt_lower:
            return (
                "Policy: data handling\n"
                "- Store customer data securely.\n"
                "- Never share customer information.\n"
                "- Use exact numbers when they are provided."
            )
        if "summarize the following quarterly metrics" in prompt_lower or "metrics" in prompt_lower:
            return (
                "Product engagement rose 8% quarter over quarter while stability improved.\n"
                "- Active users increased 8% QoQ driven by new onboarding flows.\n"
                "- Churn fell 2 points as support SLAs stabilized.\n"
                "- Response time dropped from 480 ms to 410 ms after the caching rollout."
            )
        return "Mock response generated for benchmarking."


class AnthropicProvider(BaseProvider):
    """Proxy to Anthropic's Messages API with graceful fallback when no key is present."""

    def __init__(self, model: str):
        super().__init__(model)
        try:
            import anthropic  # type: ignore

            self.client = anthropic.Anthropic()
            self._has_client = True
        except Exception:
            self.client = None
            self._has_client = False

    def infer(self, prompt: str) -> ProviderResult:
        t0 = time.perf_counter()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self._has_client or not api_key:
            latency_ms = (time.perf_counter() - t0) * 1000
            message = "[no-key] " + prompt[:160]
            tokens = MockProvider._estimate_tokens  # reuse heuristic for placeholder
            return ProviderResult(
                output=message,
                tokens_in=tokens(prompt),
                tokens_out=tokens(message),
                latency_ms=latency_ms,
            )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        output = self._normalise_response(response)
        usage = getattr(response, "usage", None)
        tokens_in = getattr(usage, "input_tokens", None)
        tokens_out = getattr(usage, "output_tokens", None)
        return ProviderResult(output=output, tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=latency_ms)

    @staticmethod
    def _normalise_response(response: object) -> str:
        content = getattr(response, "content", None)
        if isinstance(content, list):
            # anthropic responses contain content blocks
            joined = " ".join(block.text for block in content if hasattr(block, "text"))
            if joined:
                return joined
        return str(response)


class ProviderFactory:
    """Utility to construct providers while keeping harness configuration simple."""

    @staticmethod
    def create(provider_name: str, model: str) -> BaseProvider:
        name = provider_name.lower()
        if name == "anthropic":
            return AnthropicProvider(model)
        if name == "mock":
            return MockProvider(model)
        raise ValueError(f"Unknown provider '{provider_name}'")
