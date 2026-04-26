from __future__ import annotations

from copy import copy
from dataclasses import dataclass

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.consumer_contract, pytest.mark.state]


@dataclass
class Message:
    content: object


def anonymize_message_content(content, anonymizer):
    if isinstance(content, str):
        return anonymizer.anonymize(content)
    if isinstance(content, list):
        out = []
        for part in content:
            if isinstance(part, dict):
                copied = dict(part)
                for key in (
                    "text",
                    "content",
                    "input",
                    "title",
                    "caption",
                    "markdown",
                    "explanation",
                ):
                    if isinstance(copied.get(key), str):
                        copied[key] = anonymizer.anonymize(copied[key])
                out.append(copied)
            else:
                out.append(part)
        return out
    return content


class SDAgentLikeAnonymizationMiddleware:
    def __init__(self, anonymizer):
        self._anonymizer = anonymizer

    def modify_messages(self, messages):
        anon_messages = []
        for message in messages:
            anon_message = copy(message)
            anon_message.content = anonymize_message_content(
                message.content,
                self._anonymizer,
            )
            anon_messages.append(anon_message)
        return anon_messages


class SessionScopedAnonymizer:
    def __init__(self):
        self.calls = []

    def anonymize(self, text):
        self.calls.append(text)
        return f"ANON::{len(self.calls)}"


def test_consumer_middleware_anonymizes_all_text_parts_before_model_boundary():
    anonymizer = SessionScopedAnonymizer()
    middleware = SDAgentLikeAnonymizationMiddleware(anonymizer)
    messages = [
        Message(
            content=[
                {"type": "text", "text": "user John Doe"},
                {"type": "tool", "input": "tool John Doe"},
                {"type": "metadata", "title": "title John Doe"},
            ]
        )
    ]

    result = middleware.modify_messages(messages)

    assert "John Doe" not in str(result[0].content)
    assert anonymizer.calls == ["user John Doe", "tool John Doe", "title John Doe"]


def test_consumer_contract_requires_tool_outputs_to_use_same_anonymizer():
    anonymizer = SessionScopedAnonymizer()

    tool_output = "Tool result contains John Doe"
    protected_output = anonymizer.anonymize(tool_output)

    assert protected_output == "ANON::1"


def test_long_lived_shared_palimpsest_must_not_restore_with_stale_mapping(
    lightweight_palimpsest_factory,
):
    from palimpsest import Palimpsest

    processor = Palimpsest()
    user_one = processor.create_session(session_id="user-one")
    user_two = processor.create_session(session_id="user-two")

    user_one_fake = user_one.anonimize("user-one secret")
    user_two.anonimize("user-two secret")

    with pytest.raises(Exception):
        user_two.deanonimize(user_one_fake)

    assert user_one.deanonimize(user_one_fake) == "user-one secret"


def test_one_session_can_keep_mappings_across_multiple_turns(
    lightweight_palimpsest_factory,
):
    from palimpsest import Palimpsest

    processor = Palimpsest()
    session = processor.create_session(session_id="conversation")

    first = session.anonymize("first secret")
    second = session.anonymize("second secret")

    assert session.deanonymize(first) == "first secret"
    assert session.deanonymize(second) == "second secret"
