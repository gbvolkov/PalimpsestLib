
from faker import Faker
from palimpsest import Palimpsest

Faker.seed(42)

#processor = Palimpsest(verbose=False, run_entities=["EMAIL_ADDRESS"], locale="en-US")
processor = Palimpsest()
session = processor.create_session("email-default-example")

input_text = "Contact john.doe@example.com for details."

anonymized = session.anonymize(input_text)
restored = session.deanonymize(anonymized)

print(input_text)
print(anonymized)
print([(e.entity_type, e.text, e.operator) for e in session._entries()])
print(restored)
