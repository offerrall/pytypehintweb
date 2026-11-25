from dataclasses import dataclass
from typing import Annotated

from pytypehint import Label, signature_of, struct_of

from pytypehintweb import plan_of


@dataclass
class Address:
    street_name: str


@dataclass
class Contact:
    contact_person: str
    phone: Annotated[str, Label("phone number")]
    address: Address


def labels(fields):
    return {field["name"]: field for field in fields}


def test_a_field_without_label_reads_as_words_with_a_capital():
    fields = labels(plan_of(struct_of(Contact))["fields"])

    assert fields["contact_person"]["label"] == "Contact person"
    assert fields["contact_person"]["name"] == "contact_person"


def test_an_explicit_label_is_kept_letter_for_letter():
    fields = labels(plan_of(struct_of(Contact))["fields"])

    assert fields["phone"]["label"] == "phone number"


def test_a_nested_dataclass_and_its_fields_get_the_same_rule():
    address = labels(plan_of(struct_of(Contact))["fields"])["address"]

    assert address["label"] == "Address"
    assert address["node"]["fields"][0]["label"] == "Street name"


def test_a_function_parameter_gets_the_same_rule():
    def edit(shop_id: int, shop: Contact) -> None: ...

    fields = labels(plan_of(signature_of(edit))["fields"])

    assert fields["shop_id"]["label"] == "Shop id"
    assert fields["shop"]["label"] == "Shop"


def test_a_name_of_only_underscores_keeps_its_name():
    @dataclass
    class Odd:
        __: int

    assert plan_of(struct_of(Odd))["fields"][0]["label"] == "__"
