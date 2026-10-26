"""Device-aware model choice and the on-device LLM client (HTTP is mocked: no model, key or network needed)."""

from __future__ import annotations

import logging

import pytest
import requests

from src import llm_client
from src.device_profile import DeviceProfile, allowed_models, detect_device, parse_cgroup_limit, parse_nvidia_smi, select_model
from src.llm_client import (LLMBadResponse, LLMBusy, LLMConfig, LLMTimeout, LLMUnavailable, config_from_env,
                            generate_json, list_models)

RTX_5050 = DeviceProfile(ram_gb=16, cpu_threads=16, gpu_name="NVIDIA GeForce RTX 5050 Laptop GPU", gpu_vram_gb=8.0)
THIS_LAPTOP = DeviceProfile(ram_gb=15.7, cpu_threads=16)
SMALL = DeviceProfile(ram_gb=8, cpu_threads=8)
TINY = DeviceProfile(ram_gb=4, cpu_threads=4)

# ----------------------------- device profile ----------------------------- #


def test_parse_nvidia_smi_reads_name_and_vram_in_gb():
    name, vram = parse_nvidia_smi("NVIDIA GeForce RTX 5050 Laptop GPU, 8151\n")
    assert "RTX 5050" in name and vram == pytest.approx(7.96, abs=0.05)
    assert parse_nvidia_smi("garbage") is None and parse_nvidia_smi("") is None


def test_tiers_and_allowed_sizes():
    assert RTX_5050.tier == "gpu-8gb" and THIS_LAPTOP.tier == "cpu-16gb+" and SMALL.tier == "cpu-8gb" and TINY.tier == "minimal"
    assert max(m.params_b for m in allowed_models(RTX_5050)) > 7          # a 7B model fits 8 GB of VRAM
    assert max(m.params_b for m in allowed_models(THIS_LAPTOP)) <= 4.0    # CPU-only stays small and fast
    assert allowed_models(TINY) == []


@pytest.mark.parametrize("profile, installed, expected", [
    (RTX_5050, ["llama3.2:1b", "qwen2.5:7b-instruct-q4_K_M", "qwen2.5:3b"], "qwen2.5:7b-instruct-q4_K_M"),
    (THIS_LAPTOP, ["qwen2.5:7b", "qwen2.5:3b", "llama3.2:1b"], "qwen2.5:3b"),     # 7B is installed but too slow on CPU
    (SMALL, ["qwen2.5:3b", "qwen2.5:1.5b"], "qwen2.5:1.5b"),
    (RTX_5050, ["llama3.2:1b"], "llama3.2:1b"),                                   # smaller than ideal is fine
])
def test_best_installed_model_that_suits_the_hardware(profile, installed, expected):
    assert select_model(profile, installed).name == expected


def test_selection_without_a_suitable_model_gives_a_pull_hint_and_never_downloads():
    choice = select_model(RTX_5050, ["some-embedding-model"])
    assert choice.name is None and choice.pull_hint == "ollama pull qwen2.5:7b"
    assert select_model(THIS_LAPTOP, []).pull_hint == "ollama pull qwen2.5:3b"
    assert select_model(TINY, ["qwen2.5:1.5b"]).name is None


def test_explicit_override_wins_and_detection_never_raises():
    assert select_model(TINY, [], override="my-model").name == "my-model"
    profile = detect_device()
    assert profile.ram_gb > 0 and profile.cpu_threads >= 1


# ------------------------------- configuration ----------------------------- #


def test_config_defaults_and_validation():
    config = config_from_env({})
    assert config.backend == "auto" and config.enabled and config.api_key is None
    assert not config_from_env({"LLM_BACKEND": "none"}).enabled
    with pytest.raises(ValueError):
        config_from_env({"LLM_BACKEND": "cloud"})


def test_remote_servers_are_refused_unless_explicitly_allowed():
    with pytest.raises(ValueError, match="loopback"):
        config_from_env({"LLM_BASE_URL": "https://api.example.com/v1"})
    assert config_from_env({"LLM_BASE_URL": "http://localhost:11434"}).base_url == "http://localhost:11434"
    assert config_from_env({"LLM_BASE_URL": "https://api.example.com/v1", "LLM_ALLOW_REMOTE": "1"}).allow_remote


def test_api_key_is_never_shown_in_repr():
    assert "secret-value" not in repr(config_from_env({"LLM_API_KEY": "secret-value"}))


# ------------------------------- HTTP behaviour ----------------------------- #


class FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status_code, self._payload = status, payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


def _patch(monkeypatch, *, get=None, post=None):
    calls = {"post": 0}

    def fake_post(url, **kwargs):
        calls["post"] += 1
        result = post[min(calls["post"], len(post)) - 1] if isinstance(post, list) else post
        if isinstance(result, Exception):
            raise result
        return result

    def fake_get(url, **kwargs):
        if isinstance(get, Exception):
            raise get
        return get

    monkeypatch.setattr(llm_client.requests, "post", fake_post)
    monkeypatch.setattr(llm_client.requests, "get", fake_get)
    monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)
    return calls


CFG = LLMConfig()
OLLAMA_OK = FakeResponse(200, {"message": {"content": '{"ok": true}'}})


def test_list_models_for_ollama_and_openai_compatible(monkeypatch):
    _patch(monkeypatch, get=FakeResponse(200, {"models": [{"name": "qwen2.5:3b"}]}))
    assert list_models(CFG) == ("ollama", "http://127.0.0.1:11434", ["qwen2.5:3b"])
    _patch(monkeypatch, get=FakeResponse(200, {"data": [{"id": "local-model"}]}))
    assert list_models(LLMConfig(backend="openai_compat"))[2] == ["local-model"]


def test_no_server_running_is_reported_as_unavailable(monkeypatch):
    _patch(monkeypatch, get=requests.ConnectionError("refused"))
    with pytest.raises(LLMUnavailable):
        list_models(CFG)


def test_successful_generation_for_both_backends(monkeypatch):
    _patch(monkeypatch, post=OLLAMA_OK)
    assert generate_json(CFG, "ollama", "http://127.0.0.1:11434", "m", "sys", "user", {"type": "object"}) == '{"ok": true}'
    _patch(monkeypatch, post=FakeResponse(200, {"choices": [{"message": {"content": "{}"}}]}))
    assert generate_json(CFG, "openai_compat", "http://127.0.0.1:1234/v1", "m", "s", "u") == "{}"


@pytest.mark.parametrize("post, error", [
    (requests.Timeout("slow"), LLMTimeout),
    (requests.ConnectionError("down"), LLMUnavailable),
    (FakeResponse(404, {}), LLMUnavailable),
    (FakeResponse(500, {}), LLMBadResponse),
    (FakeResponse(200, ValueError("not json")), LLMBadResponse),
    (FakeResponse(200, {"unexpected": 1}), LLMBadResponse),
    (FakeResponse(200, {"message": {"content": "   "}}), LLMBadResponse),
])
def test_every_failure_becomes_a_typed_error(monkeypatch, post, error):
    _patch(monkeypatch, post=post)
    with pytest.raises(error):
        generate_json(CFG, "ollama", "http://127.0.0.1:11434", "m", "s", "u")


def test_one_retry_after_a_transient_server_error(monkeypatch):
    calls = _patch(monkeypatch, post=[FakeResponse(503, {}), OLLAMA_OK])
    assert generate_json(CFG, "ollama", "http://127.0.0.1:11434", "m", "s", "u") == '{"ok": true}'
    assert calls["post"] == 2


def test_a_second_generation_while_busy_is_refused_and_the_lock_is_released(monkeypatch):
    _patch(monkeypatch, post=OLLAMA_OK)
    assert llm_client._BUSY.acquire(blocking=False)
    try:
        with pytest.raises(LLMBusy):
            generate_json(CFG, "ollama", "http://127.0.0.1:11434", "m", "s", "u")
    finally:
        llm_client._BUSY.release()
    assert generate_json(CFG, "ollama", "http://127.0.0.1:11434", "m", "s", "u")


def test_logs_never_contain_prompts_responses_or_keys(monkeypatch, caplog):
    _patch(monkeypatch, post=FakeResponse(200, {"message": {"content": "SECRET-ANSWER"}}))
    config = LLMConfig(api_key="KEY-123")
    with caplog.at_level(logging.DEBUG, logger="signal_studio.llm"):
        generate_json(config, "ollama", "http://127.0.0.1:11434", "m", "SECRET-SYSTEM", "SECRET-USER-DRAFT")
    text = caplog.text
    assert "status=ok" in text
    assert not any(secret in text for secret in ("SECRET-ANSWER", "SECRET-SYSTEM", "SECRET-USER-DRAFT", "KEY-123"))


def test_container_memory_limit_is_parsed_so_hosted_instances_are_not_mistaken_for_big_machines():
    assert parse_cgroup_limit("536870912") == pytest.approx(0.5)
    assert parse_cgroup_limit("max") is None and parse_cgroup_limit("9223372036854771712") is None
