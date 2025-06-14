from typing import Tuple, Any

from palimpsest.config import *

from langchain_mistralai import ChatMistralAI
from langchain_community.chat_models import ChatYandexGPT
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from palimpsest.fakers import *

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
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.4, frequency_penalty=0.3)


def generate_answer(system_prompt: str, user_request: str) -> Tuple[str, str]:
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

    chain = prompt | llm
    response = chain.invoke(user_request)

    llm_resp = response.content
    return llm_resp

if __name__ == "__main__":
    import logging
    from palimpsest.logger_factory import setup_logging

    setup_logging("anonimizer_web", other_console_level=logging.DEBUG, project_console_level=logging.DEBUG)

    with open("data/text.txt", encoding="utf-8") as f:
        text = f.read()
    with open("data/prompt.txt", encoding="utf-8") as f:
        system_prompt = f.read()
    print(generate_answer(system_prompt, text))