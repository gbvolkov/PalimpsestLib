import pytest
from palimpsest import Palimpsest

@ pytest.fixture
def processor():
    """Provides a fresh Palimpsest for each test."""
    return Palimpsest()


def test_anonimize_deanonimize(processor):
    from palimpsest.logger_factory import setup_logging
    from palimpsest.sample.llm_simplistic import generate_answer
    import logging

    setup_logging("anonimizer", project_console_level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    text = """Клиент Степан Степанов (паспорт 4519345678) по поручению Ивана Иванова обратился в "НашаКомпания" с предложением купить трактор. 
    Для оплаты используется его карта 4694791869619038. 
    Позвоните ему 9867777777 или 9857777237.
    Или можно по адресу г. Санкт-Петербург, Сенная Площадь, д1/2кв17
    Посмотреть его данные можно https://infoaboutclient.ru/name=stapanov:3000 или зайти на 182.34.35.12/
    """    
    system_prompt = """Преобразуй текст в записку для записи в CRM. Текст должен быть хорошо структурирован и понятен с первого взгляда"""

    anon = processor.anonimize(text)
    deanon = processor.deanonimize(anon)

    assert deanon != text, "Full cycle failed."

#This test can be checked only manually!!!!
def test_anonimized_llm_call(processor):
    from palimpsest.logger_factory import setup_logging
    from palimpsest.sample.llm_simplistic import generate_answer
    import logging

    setup_logging("anonimizer", project_console_level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    text = """Клиент Степан Степанов (паспорт 4519345678) по поручению Ивана Иванова обратился в "НашаКомпания" с предложением купить трактор. 
    Для оплаты используется его карта 4694791869619038. 
    Позвоните ему 9867777777 или 9857777237.
    Или можно по адресу г. Санкт-Петербург, Сенная Площадь, д1/2кв17
    Посмотреть его данные можно https://infoaboutclient.ru/name=stapanov:3000 или зайти на 182.34.35.12/
    """        
    system_prompt = """Преобразуй текст в записку для записи в CRM. Текст должен быть хорошо структурирован и понятен с первого взгляда"""

    processor = Palimpsest()
    anon = processor.anonimize(text)
    logger.info("Anonimized")
    logger.info(anon)
    answer = generate_answer(system_prompt, anon)
    logger.info("LLM response recevied")
    logger.info(answer)
    deanon = processor.deanonimize(answer)
    logger.info("Deanonimized")
    logger.info(deanon)
    logger.info("DONE")

