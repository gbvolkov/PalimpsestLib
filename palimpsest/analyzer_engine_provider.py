from typing import Tuple, List, Optional

from presidio_analyzer import (
    AnalyzerEngine,
    RecognizerResult,
    RecognizerRegistry,
    PatternRecognizer,
    Pattern,
)
from presidio_analyzer.nlp_engine import (
    NlpEngine,
    NlpEngineProvider,
)
import spacy
from recognizers.regex_recognisers import (
    ru_internal_passport_recognizer, 
    ru_phone_recognizer,
    SNILSRecognizer,
    INNRecognizer,
    RUBankAccountRecognizer,
    RUCreditCardRecognizer
)


def create_nlp_engine_with_transformers(
    model_path: str,
) -> Tuple[NlpEngine, RecognizerRegistry]:
    """
    Instantiate an NlpEngine with a TransformersRecognizer and a small spaCy model.
    The TransformersRecognizer would return results from Transformers models, the spaCy model
    would return NlpArtifacts such as POS and lemmas.
    :param model_path: HuggingFace model path.
    """
    print(f"Loading Transformers model: {model_path} of type {type(model_path)}")

    nlp_configuration = {
        "nlp_engine_name": "transformers",
        "models": [
            {
                "lang_code": "en",
                #"model_name": {"spacy": "en_core_web_sm", "transformers": model_path},
                "model_name": {"spacy": "ru_core_news_sm", "transformers": model_path},
            }
        ],
        "ner_model_configuration": {
            "model_to_presidio_entity_mapping": {
                "FIRST_NAME": "FIRST_NAME",
                "MIDDLE_NAME": "MIDDLE_NAME",
                "LAST_NAME": "LAST_NAME",
                #"CITY": "CITY",
                #"DISTRICT": "DISTRICT",
                "STREET": "STREET",
                "HOUSE": "HOUSE",
                #"PER": "PERSON",
                #"PERSON": "PERSON",
                "LOC": "LOCATION",
                "LOCATION": "LOCATION",
                "GPE": "LOCATION",
                "ORG": "ORGANIZATION",
                "ORGANIZATION": "ORGANIZATION",
                "NORP": "NRP",
                "AGE": "AGE",
                "ID": "ID",
                "EMAIL": "EMAIL",
                "PATIENT": "PERSON",
                "STAFF": "PERSON",
                "HOSP": "ORGANIZATION",
                "PATORG": "ORGANIZATION",
                "DATE": "DATE_TIME",
                "TIME": "DATE_TIME",
                "PHONE": "PHONE_NUMBER",
                "HCW": "PERSON",
                "HOSPITAL": "ORGANIZATION",
                "FACILITY": "LOCATION",
            },
            "low_confidence_score_multiplier": 0.4,
            "low_score_entity_names": ["ID"],
            "labels_to_ignore": [
                "CARDINAL",
                "EVENT",
                "LANGUAGE",
                "LAW",
                "MONEY",
                "ORDINAL",
                "PERCENT",
                "PRODUCT",
                "QUANTITY",
                "WORK_OF_ART",
            ],
        },
    }

    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(nlp_engine=nlp_engine)
    ## Руcская модель распознаёт URL, у которого внутри фамилия, как LAST_NAME - повышаем приоритет распознавателю URL
    # 1) Удаляем встроенный URL-распознаватель (если он уже был загружен)
    #recogniser = registry.get_recognizers("en", ["URL"])[0]
    #registry.remove_recognizer(recogniser.name)
    #for pattern in recogniser.patterns:
    #    pattern.score = pattern.score + 0.36   # bump to near‐max confidence

    ## 3) Регистрируем его в том же Registry
    #registry.add_recognizer(recogniser)

    return nlp_engine, registry


def create_nlp_engine_with_flair(
    model_path: str,
) -> Tuple[NlpEngine, RecognizerRegistry]:
    """
    Instantiate an NlpEngine with a FlairRecognizer and a small spaCy model.
    The FlairRecognizer would return results from Flair models, the spaCy model
    would return NlpArtifacts such as POS and lemmas.
    :param model_path: Flair model path.
    """
    from recognizers.flair_recognizer import FlairRecognizer

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers()

    # there is no official Flair NlpEngine, hence we load it as an additional recognizer

    if not spacy.util.is_package("en_core_web_sm"):
        spacy.cli.download("en_core_web_sm")
    # Using a small spaCy model + a Flair NER model
    flair_recognizer = FlairRecognizer(model_path=model_path)
    nlp_configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    }
    registry.add_recognizer(flair_recognizer)
    registry.remove_recognizer("SpacyRecognizer")

    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()

    return nlp_engine, registry

def create_nlp_engine_with_natasha(
    model_path: str,
) -> Tuple[NlpEngine, RecognizerRegistry]:
    """
    Instantiate an NlpEngine with a FlairRecognizer and a small spaCy model.
    The FlairRecognizer would return results from Flair models, the spaCy model
    would return NlpArtifacts such as POS and lemmas.
    :param model_path: Flair model path.
    """
    from recognizers.natasha_recogniser import NatashaSlovnetRecognizer

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers()

    # there is no official Flair NlpEngine, hence we load it as an additional recognizer
    #spacy_model = "en_core_web_sm"
    spacy_model = "ru_core_news_sm"
    if not spacy.util.is_package(spacy_model):
        spacy.cli.download(spacy_model)
    # Using a small spaCy model + a Flair NER model
    natasha_recognizer = NatashaSlovnetRecognizer()
    nlp_configuration = {
        "nlp_engine_name": "spacy",
        #"models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        "models": [{"lang_code": "en", "model_name": "ru_core_news_sm"}],
    }
    registry.add_recognizer(natasha_recognizer)
    registry.remove_recognizer("SpacyRecognizer")

    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()

    return nlp_engine, registry

def create_nlp_engine_with_gliner(
    model_path: str,
) -> Tuple[NlpEngine, RecognizerRegistry]:
    """
    Instantiate an NlpEngine with a FlairRecognizer and a small spaCy model.
    The FlairRecognizer would return results from Flair models, the spaCy model
    would return NlpArtifacts such as POS and lemmas.
    :param model_path: Flair model path.
    """
    from recognizers.gliner_recogniser import GlinerRecognizer

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers()

    # there is no official Flair NlpEngine, hence we load it as an additional recognizer

    spacy_model = "ru_core_news_sm"
    if not spacy.util.is_package(spacy_model):
        spacy.cli.download(spacy_model)
    # Using a small spaCy model + a Flair NER model
    gliner_recognizer = GlinerRecognizer()
    nlp_configuration = {
        "nlp_engine_name": "spacy",
        #"models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        "models": [{"lang_code": "en", "model_name": "ru_core_news_lg"}],
    }
    registry.add_recognizer(gliner_recognizer)
    registry.remove_recognizer("SpacyRecognizer")

    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()

    return nlp_engine, registry

def nlp_engine_and_registry(
    model_family: str,
    model_path: str,
    ta_key: Optional[str] = None,
    ta_endpoint: Optional[str] = None,
) -> Tuple[NlpEngine, RecognizerRegistry]:
    """Create the NLP Engine instance based on the requested model.
    :param model_family: Which model package to use for NER.
    :param model_path: Which model to use for NER. E.g.,
        "StanfordAIMI/stanford-deidentifier-base",
        "obi/deid_roberta_i2b2",
        "en_core_web_lg"
    :param ta_key: Key to the Text Analytics endpoint (only if model_path = "Azure Text Analytics")
    :param ta_endpoint: Endpoint of the Text Analytics instance (only if model_path = "Azure Text Analytics")
    """

    # Set up NLP Engine according to the model of choice
    if "flair" in model_family.lower():
        engine, registry = create_nlp_engine_with_flair(model_path)
    elif "huggingface" in model_family.lower():
        engine, registry = create_nlp_engine_with_transformers(model_path)
    elif "natasha" in model_family.lower():
        engine, registry = create_nlp_engine_with_natasha(model_path)
    elif "gliner" in model_family.lower():
        engine, registry = create_nlp_engine_with_gliner(model_path)
    else:
        raise ValueError(f"Model family {model_family} not supported")
    
    return engine, registry


def analyzer_engine(
    model_family: str,
    model_path: str,
    ta_key: Optional[str] = None,
    ta_endpoint: Optional[str] = None,
) -> AnalyzerEngine:
    """Create the NLP Engine instance based on the requested model.
    :param model_family: Which model package to use for NER.
    :param model_path: Which model to use for NER:
        "StanfordAIMI/stanford-deidentifier-base",
        "obi/deid_roberta_i2b2",
        "en_core_web_lg"
    :param ta_key: Key to the Text Analytics endpoint (only if model_path = "Azure Text Analytics")
    :param ta_endpoint: Endpoint of the Text Analytics instance (only if model_path = "Azure Text Analytics")
    """
    nlp_engine, registry = nlp_engine_and_registry(
        model_family, model_path, ta_key, ta_endpoint
    )
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, registry=registry)
    analyzer.registry.add_recognizer(ru_internal_passport_recognizer)
    analyzer.registry.add_recognizer(ru_phone_recognizer)
    analyzer.registry.add_recognizer(SNILSRecognizer())
    analyzer.registry.add_recognizer(INNRecognizer())
    analyzer.registry.add_recognizer(RUBankAccountRecognizer())
    analyzer.registry.add_recognizer(RUCreditCardRecognizer())
    
    return analyzer

def get_supported_entities(
    model_family: str, model_path: str, ta_key: str, ta_endpoint: str
):
    """Return supported entities from the Analyzer Engine."""
    return analyzer_engine(
        model_family, model_path, ta_key, ta_endpoint
    ).get_supported_entities()
