
from faker import Faker
from palimpsest import EntityReplacement, Palimpsest

Faker.seed(42)

processor = Palimpsest(
    verbose=False,
    run_entities=["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS"],
    locale="en-US",
)
session = processor.create_session(
    session_id="typed-placeholder-example",
    entity_replacements=[
        EntityReplacement("PERSON", "typed_placeholder"),
        EntityReplacement("PHONE_NUMBER", "typed_placeholder"),
        EntityReplacement("EMAIL_ADDRESS", "typed_placeholder"),
    ],
)

input_text = "Contact John Williams at 445856786 or john.williams@example.com."

anonymized = session.anonymize(input_text)
llm_output = anonymized.replace("Contact", "The CRM note says")
restored = session.deanonymize(llm_output)

print(input_text)
print(anonymized)
print(llm_output)
print(session.entity_replacements)
print([(e.entity_type, e.text, e.operator) for e in session._entries()])
print(restored)
