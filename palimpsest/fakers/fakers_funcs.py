import logging
logger = logging.getLogger(__name__)

from faker import Faker

from .faker_utils import validate_name

fake = None
_fake_by_locale = {}

def fake_factory(locale: str = "ru-RU", set_default: bool = True)-> Faker:
    global fake
    if locale not in _fake_by_locale:
        _fake_by_locale[locale] = Faker(locale=locale)
    locale_fake = _fake_by_locale[locale]
    if set_default or fake is None:
        fake = locale_fake
    return locale_fake

faked_values = {}
true_values = {}
    
def fake_account(x):
    return fake.checking_account()

def fake_ru_bank_account(x):
    return fake_factory("ru_RU", set_default=False).checking_account()

def fake_snils(x):
    return fake.snils()

def fake_inn(x):
    return  fake.businesses_inn()

def fake_passport(x):
    return fake.passport_number()

def fake_ru_passport(x):
    return fake_factory("ru_RU", set_default=False).numerify("#### ######")

def fake_name(x):
    attempts = 10
    while attempts > 0:
        name = fake.first_name() + " " + fake.last_name()
        if validate_name(name):
            return name
        attempts -= 1
    logger.warning(f"NON_CASHABLE: {name}")
    return name

def fake_ru_name(x):
    ru_fake = fake_factory("ru_RU", set_default=False)
    return ru_fake.first_name() + " " + ru_fake.last_name()

def fake_first_name(x):
    attempts = 10
    while attempts > 0:
        name = fake.first_name()
        if validate_name(name):
            return name
        attempts -= 1
    logger.warning(f"NON_CASHABLE: {name}")
    return name
def fake_middle_name(x):
    return fake.middle_name()

def fake_last_name(x):
    attempts = 10
    while attempts > 0:
        name = fake.last_name()
        if validate_name(name):
            return name
        attempts -= 1
    logger.warning(f"NON_CASHABLE: {name}")
    return name

def fake_city(x):
    return fake.city()

def fake_street(x):
    return fake.street_name()

def fake_district(x):
    return fake.district()

def fake_region(x):
    return fake.region_code()

def fake_house(x):
    return fake.street_address()

def fake_ru_address(x):
    return fake_factory("ru_RU", set_default=False).street_address()

def fake_city(x):
    return fake.city()

def fake_location(x):
    return fake.address()

def fake_email(x):
    return fake.safe_email()

def fake_phone(x):
    if hasattr(fake, "basic_phone_number"):
        return fake.basic_phone_number()
    return fake.phone_number()

def fake_card(x):
    return fake_factory("en_US", set_default=False).credit_card_number(card_type="visa16")

def fake_ip(x):
    return fake.ipv4_public()

def fake_url(x):
    return fake.url()

def fake_organization(x):
    return fake.company()
