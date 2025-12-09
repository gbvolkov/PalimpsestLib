from typing import Tuple, Any, Dict
import json
from functools import lru_cache
import os
import palimpsest.config as config


os.environ["LANGCHAIN_ENDPOINT"]="https://api.smith.langchain.com"
os.environ["LANGCHAIN_TRACING_V2"] = "true"

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


from palimpsest import Palimpsest

import logging
logger = logging.getLogger(__name__)

# Setting up LLM
#llm = ChatMistralAI(model="mistral-small-latest", temperature=1, frequency_penalty=0.3)
"""
model_name=f'gpt://{config.YA_FOLDER_ID}/yandexgpt-32k/rc'
llm = ChatYandexGPT(
    #iam_token = None,
    api_key = config.YA_API_KEY, 
    folder_id=config.YA_FOLDER_ID, 
    model_uri=model_name,
    temperature=0.4
    )
"""
#llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.4, frequency_penalty=0.3)


anon_entities = [
    "RU_PERSON"
    ,"RU_ADDRESS"
    ,"PERSON"
    ,"CREDIT_CARD"
    ,"PHONE_NUMBER"
    ,"IP_ADDRESS"
    ,"URL"
    ,"RU_PASSPORT"
    ,"SNILS"
    ,"INN"
    ,"RU_BANK_ACC"
    ,"TICKET_NUMBER"
]

processor = Palimpsest(verbose=True, run_entities=anon_entities, locale="en-US")

def anonymize(text: str, language = "en") -> str:
    resulting_text = processor.anonimize(text)
    return resulting_text

def deanonymize(text: str, language = "en") -> str:
    resulting_text = processor.deanonimize(text)
    return resulting_text


@lru_cache(maxsize=32)
def _make_llm_cache(provider: str, params_json: str):
    """Internal helper: instantiate and cache an LLM client based on JSON-encoded parameters."""
    params = json.loads(params_json)
    defaults = get_llm_parameters(provider)
    # Merge defaults with overrides
    merged = {**defaults, **params}

    # Instantiate provider-specific LLM
    if provider == 'OpenAI':
        temperature = float(merged['temperature'])
        frequency_penalty = float(merged['frequency_penalty'])

        return ChatOpenAI(
            api_key=merged.get('api_key'),
            model=merged['model_spec'],
            temperature=temperature,
            frequency_penalty=frequency_penalty
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

def make_llm(provider: str, llm_parameters: Dict[str, Any]):
    """
    Public factory: returns a cached LLM client instance for the given provider and parameters.
    """
    # JSON-serialize parameters with sorted keys for stable caching
    params_json = json.dumps(llm_parameters or {}, sort_keys=True)
    return _make_llm_cache(provider, params_json)

def generate_answer(system_prompt: str, user_request: str, llm_provider: str = "OpenAI", llm_parameters: Dict[str, Any] = {}) -> Tuple[str, str, str]:
    """
    Dummy LLM call. Replace with real API integration.
    Returns (llm_response, deanonymized_response).
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "{user_request}"),
        ]
    )
    processor.reset_context()
    anonymized_request = anonymize(user_request, language="en")
    llm = make_llm(llm_provider, llm_parameters)
    chain = prompt | llm
    #chain = {"user_request": lambda txt: anonymize(txt, language="en")} | prompt | llm | (lambda ai_message: deanonymize(ai_message.content))
    response = chain.invoke(anonymized_request)
    llm_answer = response.content
    deanonymized_answer = deanonymize(llm_answer)
    return deanonymized_answer, anonymized_request, llm_answer

def get_llm_parameters(provider: str) -> Dict[str, str]:
    """
    Return default parameter names → values for each supported LLM provider.
    Update this dict when provider parameter sets change.
    """
    defaults = {
        "OpenAI": {
            "api_key": "",
            "model_spec": "gpt-4.1-nano",
            "temperature": "0.4",
            "frequency_penalty": "0.3"
        },
        "Mistral": {
            "api_key": "",
            "model_spec": "mistral-large-latest",
            "temperature": "0.4",
            "frequency_penalty": "0.3"
        },
        "Yandex": {
            "api_key": "",
            "model_spec": "yandexgpt-32k",
            "temperature": "0.4",
            "folder_id": ""
        },
        "SberGIGA": {
            "credentials": "",
            "scope": "",
            "model_spec": "GigaChat-Pro",
            "temperature": "0.4",
            "repetition_penalty": "0.3",
            "max_tockens": "4096",
            "timeout": "300"
        },
    }
    return defaults.get(provider, {}) if provider else defaults

if __name__ == "__main__":
    import palimpsest.config as config
    
    text = """Client John Doe (4519227557), on behalf of William Scheffler (4519227557), contacted “Interleasing” with a proposal to buy a tractor.
Payment will be made using his card 4095260993934932.
Call him at 986-777-7777 or 985-777-7237.
Or visit him at London, City, str Queen Elisabeth, building 1/2, apt. 17.
You can view his data at https://client.ileasing.com/name=doe:3000
 or go to 182.34.35.12/
    """

    system_prompt = """Convert the text into a note for entry into the CRM. The note should be well-structured and immediately clear at a glance."""

    #from palimpsest.utils.addr_unifier import unify_address
    #from pprint import pprint
    #unified_addr = unify_address(text)
    #text = "111127, Moscow, Russia, 3 Vladimirskaya str. 3-3-24"
    #pprint(unified_addr)
    #text = "111127, Russia, Moscow, 3 Vladimirskaya str. 3-3-24"
    #unified_addr = unify_address(text)
    #pprint(unified_addr)


    print(generate_answer(system_prompt, text, llm_parameters={"api_key": config.OPENAI_API_KEY})[0])
