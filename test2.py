from palimpsest import Palimpsest

processor = Palimpsest(
    verbose=False,
    run_entities=["CREDIT_CARD"],
    locale="en-US",
)

original = "Payment card: 675944116714"
print("original:", original)

for i in range(1, 51):
    session = processor.create_session(session_id=f"card-{i}")

    anonymized = session.anonymize(original)
    restored = session.deanonymize(anonymized)

    print(f"attempt={i}")
    print("anonymized:", anonymized.strip())
    print("restored:", restored.strip())
    print("ok:", restored.strip() == original)

    if restored.strip() != original:
        break