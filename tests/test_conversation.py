"""Tests of the conversation engine: provider order, fallbacks and comparison.
Network calls are mocked, so no API key is needed."""
import os, sys, urllib.error
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import conversation as conv


def _env(**keys):
    base = {"GROQ_API_KEY": "", "GEMINI_API_KEY": ""}
    base.update(keys)
    return mock.patch.dict(os.environ, base)


def _no_ollama():
    return mock.patch.object(conv, "ollama_model", return_value=None)


def _rate_limited(*_a, **_k):
    raise urllib.error.HTTPError("https://api", 429, "Too Many Requests", {}, None)


def test_rules_only_without_any_key():
    with _env(), _no_ollama():
        assert conv.available_providers() == ["auto", "rules"]
        r = conv.respond("HELLO")
    assert r.provider == "rules" and r.text.startswith("Hello") and r.lang == "en-US"
    assert r.note == ""


def test_french_sentence_gets_french_reply():
    with _env(), _no_ollama():
        r = conv.respond("BONJOUR")
    assert r.lang == "fr-FR" and r.text.startswith("Bonjour")


def test_auto_uses_groq_first():
    with _env(GROQ_API_KEY="k", GEMINI_API_KEY="k"), _no_ollama(), \
         mock.patch.object(conv, "_openai_compatible", return_value="Hi there!") as call:
        r = conv.respond("HOW ARE YOU")
    assert r.provider == "groq" and r.model == "openai/gpt-oss-120b" and r.text == "Hi there!"
    assert call.call_args[0][0] == conv.GROQ_URL


def test_rate_limit_falls_back_to_the_next_brain():
    def fake(url, key, model, messages, extra):
        if url == conv.GROQ_URL:
            _rate_limited()
        return "From Gemini"
    with _env(GROQ_API_KEY="k", GEMINI_API_KEY="k"), _no_ollama(), \
         mock.patch.object(conv, "_openai_compatible", side_effect=fake):
        r = conv.respond("HELLO")
    assert r.provider == "gemini" and r.text == "From Gemini"
    assert "Groq" in r.note and "Gemini replied" in r.note


def test_everything_down_ends_with_local_rules():
    with _env(GROQ_API_KEY="k", GEMINI_API_KEY="k"), _no_ollama(), \
         mock.patch.object(conv, "_openai_compatible", side_effect=_rate_limited):
        r = conv.respond("THANK YOU")
    assert r.provider == "rules" and r.text == "You're welcome!"


def test_session_limit_skips_cloud_providers():
    with _env(GROQ_API_KEY="k"), _no_ollama(), \
         mock.patch.object(conv, "_openai_compatible", return_value="cloud") as call:
        r = conv.respond("HELLO", allow_cloud=False)
    assert r.provider == "rules" and not call.called


def test_chosen_provider_is_tried_first():
    with _env(GROQ_API_KEY="k", GEMINI_API_KEY="k"), _no_ollama(), \
         mock.patch.object(conv, "_openai_compatible", return_value="ok") as call:
        r = conv.respond("HELLO", provider="gemini")
    assert r.provider == "gemini" and call.call_args[0][0] == conv.GEMINI_URL


def test_model_names_come_from_settings():
    with _env(GROQ_API_KEY="k", GROQ_MODEL="my-model"), _no_ollama():
        assert conv.model_for("groq") == "my-model"
        assert conv.model_for("gemini") == conv.DEFAULT_MODELS["gemini"]


def test_compare_returns_one_reply_per_provider():
    def fake(url, key, model, messages, extra):
        if url == conv.GEMINI_URL:
            _rate_limited()
        return "From Groq"
    with _env(GROQ_API_KEY="k", GEMINI_API_KEY="k"), _no_ollama(), \
         mock.patch.object(conv, "_openai_compatible", side_effect=fake):
        out = conv.compare("HELLO")
    assert [r.provider for r in out] == ["groq", "gemini"]
    assert out[0].text == "From Groq"
    assert out[1].text == "" and "rate limit" in out[1].note


def test_history_is_sent_with_the_system_prompt():
    msgs = conv._messages("AND YOU", "en", [("HELLO", "Hi!")])
    assert msgs[0]["role"] == "system" and "English" in msgs[0]["content"]
    assert [m["role"] for m in msgs[1:]] == ["user", "assistant", "user"]
