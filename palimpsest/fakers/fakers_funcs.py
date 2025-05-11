import logging
logger = logging.getLogger(__name__)

from faker import Faker

from .fakers.faker_utils import validate_name

fake = Faker(locale="ru-RU")

faked_values = {}
true_values = {}
    
def fake_account(x):
    return fake.checking_account()

def fake_snils(x):
    return fake.snils()

def fake_inn(x):
    return  fake.businesses_inn()

def fake_passport(x):
    return fake.passport_number()

def fake_name(x):
    attempts = 10
    while attempts > 0:
        name = fake.first_name() + " " + fake.last_name()
        if validate_name(name):
            return name
        attempts -= 1
    logger.warning(f"NON_CASHABLE: {name}")
    return name

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

def fake_city(x):
    return fake.city()

def fake_location(x):
    return fake.address()

def fake_email(x):
    return fake.safe_email()

def fake_phone(x):
    return fake.phone_number()

def fake_card(x):
    return fake.credit_card_number()

def fake_ip(x):
    return fake.ipv4_public()

def fake_url(x):
    return fake.url()

def fake_organization(x):
    return fake.company()
