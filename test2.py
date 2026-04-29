from faker import Faker
from palimpsest import Palimpsest

#Faker.seed(12345)

text = "Клиент Иван Иванов оформил заявку."

#text = """Клиент Джон Доу (4519227557) от имени Вильяма Шеффлера (4519227557) связался с Интерлизинг с предложением купить трактор.  
#Оплата будет произведена с использованием его карты 4095260993934932 или его карты Maestro 675944116713.  
#Позвоните ему по номеру 986-777-7777 или 985-777-7237.  
#Или посетите его по адресу Москва, Красная площадь, д1к2кв15.  
#Вы можете просмотреть его данные по адресу https://client.ileasing.com/name=doe:3000  
# или перейти по адресу 182.34.35.12/
#    """

processor = Palimpsest(
    verbose=False,
    run_entities=["RU_PERSON", "PERSON"],
    locale="ru-RU",
)
session = processor.create_session("ru-person-demo")

anonymized = session.anonimize(text)
restored = session.deanonimize(anonymized)

print("original:", text)
print("anonymized:", anonymized)
print("restored:", restored)

fake_name = anonymized.replace("Клиент ", "").replace(" оформил заявку.\n", "")
print("stored mapping says:", session._ctx.defake(fake_name))
print("restored contains original name:", "Иван Иванов" in restored)
