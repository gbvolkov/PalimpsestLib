from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from urllib import request

import pytest
from dotenv import dotenv_values

from tests.conftest import SAMPLE_CARD, SAMPLE_PERSON, SAMPLE_PHONE


pytestmark = pytest.mark.e2e
OPENAI_MODEL = "gpt-4.1-nano"


def _gv_env_value(key: str) -> str:
    env_path = Path(__file__).resolve().parents[2] / "palimpsest" / "gv.env"
    values = dotenv_values(stream=StringIO(env_path.read_text(encoding="utf-8")))
    value = values[key]
    if not value:
        raise ValueError(f"gv.env value is empty: {key}")
    return value


def _openai_chat_completion(api_key: str, model: str, messages: list[dict[str, str]]):
    payload = json.dumps(
        {
            "model": model,
            "temperature": 0,
            "messages": messages,
        }
    ).encode("utf-8")
    req = request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def test_live_llm_roundtrip_keeps_raw_pii_out_of_model_request(monkeypatch):
    import palimpsest.fakers.fakers_funcs as fakers_funcs
    from palimpsest import Palimpsest

    monkeypatch.setattr(fakers_funcs, "fake_name", lambda value: "Jane Smith")
    monkeypatch.setattr(fakers_funcs, "fake_phone", lambda value: "+1 (303) 555-0199")
    monkeypatch.setattr(fakers_funcs, "fake_card", lambda value: "4000000000000002")

    api_key = _gv_env_value("OPENAI_API_KEY")
    text = (
        f"Client {SAMPLE_PERSON} can be reached at {SAMPLE_PHONE}. "
        f"Payment value: {SAMPLE_CARD}."
    )
    processor = Palimpsest(
        verbose=False,
        run_entities=["PERSON", "PHONE_NUMBER", "CREDIT_CARD"],
        locale="en-US",
    )
    session = processor.create_session(session_id="e2e-openai-roundtrip")

    anonymized = session.anonimize(text)
    messages = [
        {
            "role": "system",
            "content": (
                "Echo exactly the text between BEGIN_PAYLOAD and END_PAYLOAD. "
                "Do not include the markers. Do not rewrite, normalize, or "
                "reformat names, phone numbers, card numbers, punctuation, "
                "spacing, or line breaks."
            ),
        },
        {"role": "user", "content": f"BEGIN_PAYLOAD\n{anonymized}\nEND_PAYLOAD"},
    ]
    serialized_request = json.dumps(messages, ensure_ascii=False)

    assert SAMPLE_PERSON not in serialized_request
    assert SAMPLE_PHONE not in serialized_request
    assert SAMPLE_CARD not in serialized_request

    response = _openai_chat_completion(api_key, OPENAI_MODEL, messages)
    llm_answer = response["choices"][0]["message"]["content"]
    restored = session.deanonimize(llm_answer)

    assert SAMPLE_PERSON in restored
    assert SAMPLE_PHONE in restored
    assert SAMPLE_CARD in restored
