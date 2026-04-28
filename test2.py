from palimpsest import Palimpsest

processor = Palimpsest(
    verbose=False,
    run_entities=["RU_PASSPORT"],
    locale="en-US",
)

session = processor.create_session("passport-example")

original = "Passport: 4519 345678"

anonymized = session.anonymize(original)
restored = session.deanonymize(anonymized)

print("original:", repr(original))
print("anonymized:", repr(anonymized))
print("restored:", repr(restored))
print("expected contains original passport:", "4519 345678" in restored)
