```markdown
# Palimpsest

Palimpsest is a Python library, based on presidio framework, designed for reversable data anonimization and deanonimization. It can deanonimize after anonimized data processing by LLM.

## Features

- **Palimsest:** Implements anonimization and deanonimization.

## Installation

You can install Palimsest directly from PyPI once it is published:

```bash
pip install PalimpsestLib
```

If you are installing from source (assuming you have the `pyproject.toml` file in the root directory):

```bash
cd PalimpsestLib
pip install .
```

Additionally you have to install
SpaCY ru_core_news_lg
python -m spacy download ru_core_news_lg

OPTIONAL: for natasha and/or slovnet please download 
(1) SpaCY ru_core_news_sm
(2) navec_news_v1_1B_250K_300d_100q.tar and navec_news_v1_1B_250K_300d_100q.tar from https://github.com/natasha/navec
(3) slovnet_ner_news_v1.tar from https://github.com/natasha/slovnet

## Usage

```python
text = """Клиент Степан Степанов (паспорт 4519345678) по поручению Ивана Иванова обратился в "НашаКомпания" с предложением купить трактор. 
Для оплаты используется его карта 4694791869619038. 
Позвоните ему 9867777777 или 9857777237.
Или можно по адресу г. Санкт-Петербург, Сенная Площадь, д1/2кв17
Посмотреть его данные можно https://infoaboutclient.ru/name=stapanov:3000 или зайти на 182.34.35.12/
"""    
system_prompt = """Преобразуй текст в записку для записи в CRM. Текст должен быть хорошо структурирован и понятен с первого взгляда"""

processor = Palimpsest()
anon = processor.anonimize(text)

answer = generate_answer(system_prompt, anon)

deanon = processor.deanonimize(answer)

```

## Configuration & Logging

The library sets some environment variables in `config.py`.

## Contributing

Contributions are welcome! If you find bugs, have ideas, or would like to add new features:

1. Fork the repository.
2. Create a new branch: `git checkout -b my-feature`.
3. Make your changes.
4. Commit your changes: `git commit -m 'Add my feature'`.
5. Push to your branch: `git push origin my-feature`.
6. Create a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.
```