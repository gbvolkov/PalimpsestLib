import pytest
from palimpsest import Palimpsest

@ pytest.fixture
def processor():
    """Provides a fresh Palimpsest for each test."""
    return Palimpsest(verbose=True)

_TEXT = """Клиент Степан Степанов (паспорт 4519345678) по поручению Ивана Иванова обратился в "НашаКомпания" с предложением купить трактор. 
Для оплаты используется его карта 4694791869619038. 
Позвоните ему 9867777777 или 9857777237.
Или можно по адресу г. Санкт-Петербург, Сенная Площадь, д1/2кв17
Посмотреть его данные можно https://infoaboutclient.ru/name=stapanov:3000 или зайти на 182.34.35.12/
"""        
_SYSTEM_PROMPT_1 = """Преобразуй текст в записку для записи в CRM. Текст должен быть хорошо структурирован и понятен с первого взгляда"""
_SYSTEM_PROMPT_2 = """Преобразуй текст в записку для передачи в отдел продаж. Текст должен быть хорошо структурирован и понятен с первого взгляда"""

def _compare_hashed_tables(t1, t2):
    """
    Compare two ctx objects by their hashes and 'true'/'fake' values.
    Returns (True, "") if they match, or (False, reason) on first discrepancy.
    """
    # 1) Compare the sets of hashes
    bresult = True
    discrepancies = []

    hashes1 = set(t1)
    hashes2 = set(t2)
    missing_in_1 = hashes2 - hashes1
    missing_in_2 = hashes1 - hashes2
    if missing_in_1 or missing_in_2:
        if missing_in_1:
            bresult = False
            discrepancies.append(f"Hashes missing in first ctx: {sorted(missing_in_1)}")
        if missing_in_2:
            bresult = False
            discrepancies.append(f"Hashes missing in second ctx: {sorted(missing_in_2)}")
    #return False, "Hash‐set mismatch: " + "; ".join(parts)

    # 2) For each hash, compare the 'true' and 'fake' values
    for h in sorted(hashes1):
        a = t1.get(h, None)
        b = t2.get(h, None)
        if a != b:
            bresult = False
            discrepancies.append(
                f"Mismatch at hash {h!r}: "
                f"first {h}={a!r}, fake={a!r}; "
                f"second(ctx2) true={b!r}, fake={b!r}"
            )

    # All good
    return bresult, "\n".join(discrepancies)


def test_anonimize_deanonimize(processor):
    from palimpsest.logger_factory import setup_logging
    from sample.llm_simplistic import generate_answer
    import logging

    setup_logging("anonimizer", project_console_level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    processor.reset_context()
    anon = processor.anonimize(_TEXT)
    deanon = processor.deanonimize(anon)

    assert deanon != _TEXT, "Full cycle failed."

#This test can be checked only manually!!!!
def test_anonimized_llm_call(processor):
    from palimpsest.logger_factory import setup_logging
    from sample.llm_simplistic import generate_answer
    import logging

    setup_logging("anonimizer", project_console_level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    processor.reset_context()
    anon = processor.anonimize(_TEXT)
    #logger.info("Anonimized")
    #logger.info(anon)
    answer = generate_answer(_SYSTEM_PROMPT_1, anon)
    #logger.info("LLM response recevied")
    #logger.info(answer)
    deanon = processor.deanonimize(answer)
    #logger.info("Deanonimized")
    #logger.info(deanon)
    #logger.info("DONE")

def test_multi_deanonimization_stability(processor):
    from palimpsest.logger_factory import setup_logging
    from sample.llm_simplistic import generate_answer
    import logging

    setup_logging("anonimizer", project_console_level=logging.DEBUG, other_console_level=logging.ERROR)
    logger = logging.getLogger(__name__)

    processor.reset_context()
    anon = processor.anonimize(_TEXT)
    #logger.info("Anonimized")
    #logger.info(anon)
    answer = generate_answer(_SYSTEM_PROMPT_1, anon)
    #logger.info("1. LLM response recevied")
    #logger.info(answer)
    deanon = processor.deanonimize(answer)
    #logger.info("1. Deanonimized")
    #logger.info(deanon)
    answer = generate_answer(_SYSTEM_PROMPT_2, anon)
    #logger.info("2LLM response recevied")
    #logger.info(answer)
    deanon = processor.deanonimize(answer)
    #logger.info("2. Deanonimized")
    #logger.info(deanon)
    #logger.info("DONE")


def test_context_stability_positive(processor):
    from collections.abc import Mapping, Sequence, Set

    from palimpsest.logger_factory import setup_logging
    from sample.llm_simplistic import generate_answer
    import logging

    logging.basicConfig(level=logging.DEBUG)
    setup_logging("anonimizer", project_console_level=logging.DEBUG, other_console_level=logging.ERROR)
    logger = logging.getLogger(__name__)

    from copy import deepcopy
    processor.reset_context()
    anon = processor.anonimize(_TEXT)
    #"Anonimized"
    true1 = deepcopy(processor._ctx._true)
    fake1 = deepcopy(processor._ctx._faked)

    answer = generate_answer(_SYSTEM_PROMPT_1, anon)
    # 1. LLM response recevied

    deanon = processor.deanonimize(answer) #check deanonimized results in logs
    # 1. Deanonimized

    answer = generate_answer(_SYSTEM_PROMPT_2, anon)
    # 2. LLM response recevied

    deanon = processor.deanonimize(answer) #check deanonimized results in logs
    # 2. Deanonimized 

    # second anonimization the same text should not change hash tables
    anon = processor.anonimize(_TEXT) 

    true2 = processor._ctx._true
    fake2 = processor._ctx._faked
    comp_res_true, comp_message_true = _compare_hashed_tables(true1, true2)
    comp_res_fake, comp_message_fake = _compare_hashed_tables(fake1, fake2)
    assert comp_res_true and comp_res_fake, f"Context muted after repeated anonimization!\nTRUES: \n{comp_message_true}\nFAKES: \n{comp_message_fake}"


def test_context_stability_with_changed_text(processor):
    from collections.abc import Mapping, Sequence, Set

    from palimpsest.logger_factory import setup_logging
    from sample.llm_simplistic import generate_answer
    import logging

    logging.basicConfig(level=logging.DEBUG)
    setup_logging("anonimizer", project_console_level=logging.DEBUG, other_console_level=logging.ERROR)
    logger = logging.getLogger(__name__)

    from copy import deepcopy
    processor.reset_context()
    anon = processor.anonimize(_TEXT)
    #"Anonimized"
    true1 = deepcopy(processor._ctx._true)
    fake1 = deepcopy(processor._ctx._faked)

    answer = generate_answer(_SYSTEM_PROMPT_1, anon)
    # 1. LLM response recevied

    deanon = processor.deanonimize(answer) #check deanonimized results in logs
    # 1. Deanonimized

    # anonimization of the text with the same entities the different text should not change hash tables as well!!!
    anon = processor.anonimize(deanon) 

    true2 = processor._ctx._true
    fake2 = processor._ctx._faked
    comp_res_true, comp_message_true = _compare_hashed_tables(true1, true2)
    comp_res_fake, comp_message_fake = _compare_hashed_tables(fake1, fake2)
    assert comp_res_true and comp_res_fake, f"Context muted after anonimization of deanonimized results!\nTRUES: \n{comp_message_true}\nFAKES: \n{comp_message_fake}"


def test_context_stability_negative(processor):
    from collections.abc import Mapping, Sequence, Set

    from palimpsest.logger_factory import setup_logging
    from sample.llm_simplistic import generate_answer
    import logging

    logging.basicConfig(level=logging.DEBUG)
    setup_logging("anonimizer", project_console_level=logging.DEBUG, other_console_level=logging.ERROR)
    logger = logging.getLogger(__name__)


    from copy import deepcopy
    processor.reset_context()
    anon = processor.anonimize(_TEXT)
    true1 = deepcopy(processor._ctx._true)
    fake1 = deepcopy(processor._ctx._faked)

    processor.reset_context()
    anon = processor.anonimize(_TEXT) #after reset hash tables will be different

    true2 = processor._ctx._true
    fake2 = processor._ctx._faked

    comp_res_true, comp_message_true = _compare_hashed_tables(true1, true2)
    comp_res_fake, comp_message_fake = _compare_hashed_tables(fake1, fake2)
    assert not (comp_res_true or comp_res_fake), f"Context supposed to mute!!!\nTRUES: \n{comp_message_true}\nFAKES: \n{comp_message_fake}"
