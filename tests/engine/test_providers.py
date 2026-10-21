import asyncio
import json

import httpx
import pytest

from scripts.contracts import Contracts
from services.engine.providers import OllamaProvider, ProviderError, get_provider, validate_usage
from services.engine.state import build_agent_view, create_initial_state


def settings():
    return {**Contracts().fixture("RunCreate")["model_settings"], "model_id": "ollama:qwen2.5:7b"}


@pytest.mark.parametrize(
    "origin",
    [
        "https://localhost:11434",
        "http://example.com",
        "http://localhost.evil",
        "http://user:password@localhost",
        "http://127.0.0.1/path",
    ],
)
def test_local_provider_rejects_nonloopback_origin(origin):
    with pytest.raises(ValueError):
        OllamaProvider(settings(), base_url=origin)


def test_external_provider_model_rejected():
    with pytest.raises(ProviderError):
        get_provider({**settings(), "model_id": "groq:unapproved"})


def test_live_inference_requires_reliable_tokenizer():
    provider = OllamaProvider(settings())
    with pytest.raises(ProviderError, match="tokenizer"):
        provider.reserve_tokens(None, [], {})


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        {},
        {"input_tokens": True, "output_tokens": 1, "total_tokens": 2},
        {"input_tokens": 1, "output_tokens": 1, "total_tokens": 0},
    ],
)
def test_usage_is_never_invented(invalid):
    with pytest.raises(ProviderError):
        validate_usage(invalid)


def test_local_provider_honors_snapshot_and_accounts_malformed_json():
    calls = []

    async def transport(request):
        calls.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "message": {"content": "not valid json"},
                "prompt_eval_count": 11,
                "eval_count": 2,
            },
        )

    async def invoke():
        frozen = settings()
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            provider = OllamaProvider(frozen, tokenizer=lambda messages: 50, client=client)
            view = build_agent_view(
                create_initial_state(
                    run_id="r", scenario_id="scn_secret_001", target_version="vulnerable-v1"
                )
            )
            assert provider.reserve_tokens(view, [], {}) == 50 + frozen["max_output_tokens"]
            with pytest.raises(json.JSONDecodeError):
                await provider.choose_probe(view, [], {})
            assert provider.last_usage == {
                "input_tokens": 11,
                "output_tokens": 2,
                "total_tokens": 13,
            }
            assert len(calls) == 1
            assert calls[0]["model"] == "qwen2.5:7b"
            assert calls[0]["options"] == {
                "temperature": frozen["temperature"],
                "num_predict": frozen["max_output_tokens"],
                "seed": frozen["seed"],
            }

    asyncio.run(invoke())
