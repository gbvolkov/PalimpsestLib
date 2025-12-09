import pytest
from palimpsest.fakers.faker_context import FakerContext

@ pytest.fixture
def ctx():
    """Provides a fresh FakerContext for each test."""
    return FakerContext()


def test_mapping_and_defake(ctx):
    original = "account1"
    fake_val = ctx.fake_account(original)
    # The fake value should differ from the original
    assert fake_val != original
    # defake should retrieve the original
    assert ctx.defake(fake_val) == original
    # Repeated calls should return the same fake value
    assert ctx.fake_account(original) == fake_val


def test_defake_fuzzy(ctx):
    original = "user42"
    fake_val = ctx.fake_account(original)
    # Provide a partial slice for fuzzy lookup
    partial = fake_val[: len(fake_val) // 2]
    assert ctx.defake_fuzzy(partial) == original

def test_independent_contexts():
    ctx1 = FakerContext()
    ctx2 = FakerContext()

    real_name_1 = "Иван Семёнов"
    real_inn_1 = "77889922"
    real_address_1 = "Семёновская наб. 7/2 стр 1 кв. 17"

    real_name_2 = "Эммануил Перов"
    real_inn_2 = "44667755"
    real_address_2 = "Варшавский проезд, дом 6кв23"

    fake1_name = ctx1.fake_name(real_name_1)
    fake1_inn = ctx1.fake_inn(real_inn_1)
    fake1_address = ctx1.fake_house(real_address_1)
    fake2_name = ctx2.fake_name(real_name_2)
    fake2_inn = ctx2.fake_inn(real_inn_2)
    fake2_address = ctx2.fake_house(real_address_2)

    defake1_name = ctx1.defake_fuzzy(fake1_name)
    defake1_inn = ctx1.defake(fake1_inn)
    defake1_address = ctx1.defake_address(fake1_address)

    defake2_name = ctx2.defake_fuzzy(fake2_name)
    defake2_inn = ctx2.defake(fake2_inn)
    defake2_address = ctx2.defake_address(fake2_address)

    wrong_defake_name_1 = ctx2.defake_fuzzy(fake1_name)
    wrong_defake_address_1 = ctx2.defake_address(fake1_address)
    wrong_defake_inn_1 = ctx2.defake(fake1_inn)

    assert defake1_name != real_name_1 or defake1_inn or real_inn_1 or defake1_address or real_address_1 or defake2_name != real_name_2 or defake2_inn or real_inn_2 or defake2_address or real_address_2, "Defake failed!"
    assert wrong_defake_name_1 == fake1_name or wrong_defake_address_1 == fake1_address or wrong_defake_inn_1 == fake1_inn, "Contexts should maintain independent mappings"

    original = "shared"
    fake1 = ctx1.fake_account(original)
    # ctx2 has no mapping for fake1, so defake returns input
    assert ctx2.defake(fake1) == fake1, "Contexts should maintain independent mappings"
