import pytest
from palimpsest import Palimpsest

@ pytest.fixture
def processor():
    """Provides a fresh Palimpsest for each test."""
    return Palimpsest(verbose=True)

with open("./data/text.txt", encoding="utf-8") as f:
    _TEXT = f.read()
with open("./data/prompt.txt", encoding="utf-8") as f:
    _SYSTEM_PROMPT_1 = f.read()


def test_comlext_text(processor):
    from collections.abc import Mapping, Sequence, Set

    from palimpsest.logger_factory import setup_logging
    from sample.llm_simplistic import generate_answer
    import logging

    setup_logging("anonimizer", project_console_level=logging.DEBUG, other_console_level=logging.ERROR)
    logger = logging.getLogger(__name__)

    from copy import deepcopy
    processor.reset_context()
    anon = processor.anonimize(_TEXT)
    print(anon)
    answer = generate_answer(_SYSTEM_PROMPT_1, anon)
    # 1. LLM response recevied

    deanon = processor.deanonimize(answer) #check deanonimized results in logs
    print(deanon)
    # 1. Deanonimized
