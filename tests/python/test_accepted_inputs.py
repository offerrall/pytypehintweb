import functools
from dataclasses import dataclass
from typing import Annotated

import pytest

from pytypehint import Label, Min, signature_of, struct_of
from pytypehintweb import plan_of

REJECTED = "expected a plain function, a dataclass type, a Signature or a Struct"


def create_user(
    username: Annotated[str, Min(3), Label("Username")],
    age: Annotated[int, Min(0)],
) -> None:
    """Create a user account."""


@dataclass
class User:
    username: Annotated[str, Min(3)]
    age: int


class Service:
    def method(self, value: str) -> None: ...

    @classmethod
    def from_name(cls, value: str) -> None: ...

    @staticmethod
    def helper(value: str) -> None: ...


class CallableObject:
    def __call__(self, value: str) -> None: ...


class Plain:
    pass


class TestAccepted:
    def test_a_plain_named_function(self):
        plan = plan_of(create_user)

        assert plan["kind"] == "form"
        assert plan["name"] == "create_user"

    def test_a_dataclass_type(self):
        plan = plan_of(User)

        assert plan["name"] == "User"
        assert [f["name"] for f in plan["fields"]] == ["username", "age"]

    def test_an_already_compiled_signature(self):
        assert plan_of(signature_of(create_user))["name"] == "create_user"

    def test_an_already_compiled_struct(self):
        assert plan_of(struct_of(User))["name"] == "User"

    def test_a_staticmethod_is_a_plain_function(self):
        assert plan_of(Service.helper)["name"] == "helper"

    def test_keyword_only_parameters(self):
        def example(*, value: str) -> None: ...

        assert [f["name"] for f in plan_of(example)["fields"]] == ["value"]

    def test_parameters_with_defaults(self):
        def example(value: str = "x") -> None: ...

        assert plan_of(example)["fields"][0]["default"] == "x"


class TestSameResult:
    def test_a_function_and_its_signature_produce_the_same_plan(self):
        assert plan_of(create_user) == plan_of(signature_of(create_user))

    def test_a_dataclass_and_its_struct_produce_the_same_plan(self):
        assert plan_of(User) == plan_of(struct_of(User))

    def test_a_compiled_schema_honours_the_same_config(self):
        from pytypehintweb import WebConfig

        config = WebConfig(str_min_message="Al menos {value}")

        assert (plan_of(create_user, config=config)
                == plan_of(signature_of(create_user), config=config))


class TestRejected:
    def test_a_lambda(self):
        with pytest.raises(TypeError, match="lambdas have no usable name"):
            plan_of(lambda value: value)

    def test_a_partial(self):
        partial = functools.partial(create_user, age=1)

        with pytest.raises(TypeError, match=REJECTED):
            plan_of(partial)

    def test_a_bound_method(self):
        with pytest.raises(TypeError, match=REJECTED):
            plan_of(Service().method)

    def test_a_classmethod(self):
        with pytest.raises(TypeError, match=REJECTED):
            plan_of(Service.from_name)

    def test_an_unbound_method(self):
        with pytest.raises(TypeError, match="unbound method"):
            plan_of(Service.method)

    def test_a_callable_object(self):
        with pytest.raises(TypeError, match=REJECTED):
            plan_of(CallableObject())

    def test_an_ordinary_class(self):
        with pytest.raises(TypeError, match=REJECTED):
            plan_of(Plain)

    def test_a_dataclass_instance(self):
        with pytest.raises(TypeError, match="expected a dataclass type"):
            plan_of(User(username="ada", age=36))

    def test_an_unrelated_object(self):
        with pytest.raises(TypeError, match=REJECTED):
            plan_of(123)

    def test_none(self):
        with pytest.raises(TypeError, match=REJECTED):
            plan_of(None)

    def test_a_builtin(self):
        with pytest.raises(TypeError, match=REJECTED):
            plan_of(len)


class TestSignatureRestrictions:
    def test_variadic_positional(self):
        def example(*args: str) -> None: ...

        with pytest.raises(TypeError, match="variadic parameters"):
            plan_of(example)

    def test_variadic_keyword(self):
        def example(**kwargs: str) -> None: ...

        with pytest.raises(TypeError, match="variadic parameters"):
            plan_of(example)

    def test_positional_only(self):
        def example(value: str, /) -> None: ...

        with pytest.raises(TypeError, match="positional-only"):
            plan_of(example)

    def test_missing_annotation(self):
        def example(value) -> None: ...

        with pytest.raises(TypeError, match="missing type hint"):
            plan_of(example)


class TestDocumentedWrapping:
    def test_wrapping_a_bound_method_in_a_plain_function_works(self):
        service = Service()

        def run(query: str) -> None:
            service.method(query)

        plan = plan_of(run)

        assert plan["name"] == "run"
        assert [f["name"] for f in plan["fields"]] == ["query"]

    def test_plan_of_never_calls_the_function(self):
        calls = []

        def run(value: str) -> None:
            calls.append(value)

        plan_of(run)

        assert calls == []
