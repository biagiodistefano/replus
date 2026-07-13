from pathlib import Path
from typing import TypeVar

import pytest

from replus import Replus

from .test_models.date import date
from .test_models.repeated import repeated
from .test_models.tests import tests

_T = TypeVar("_T")

HERE = Path(__file__).parent.absolute()


def found(value: _T | None) -> _T:
    """Assert an Optional lookup succeeded, narrowing its type for the type checker."""
    assert value is not None
    return value


@pytest.fixture(scope="session")
def engine() -> Replus:
    return Replus({"date": date, "repeated": repeated, "tests": tests})


@pytest.fixture(scope="session")
def models_dir() -> Path:
    return HERE / "test_models"


@pytest.fixture(scope="session")
def invalid_models_dir() -> Path:
    return HERE / "invalid_models"
