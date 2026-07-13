from pathlib import Path

import pytest

from replus import Replus

from .test_models.date import date
from .test_models.repeated import repeated
from .test_models.tests import tests

HERE = Path(__file__).parent.absolute()


@pytest.fixture(scope="session")
def engine() -> Replus:
    return Replus({"date": date, "repeated": repeated, "tests": tests})


@pytest.fixture(scope="session")
def models_dir() -> Path:
    return HERE / "test_models"


@pytest.fixture(scope="session")
def invalid_models_dir() -> Path:
    return HERE / "invalid_models"
