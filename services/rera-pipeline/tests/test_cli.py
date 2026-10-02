import pytest

from rera_pipeline.__main__ import main


def test_stages_are_stubbed_until_their_session():
    assert main(["fetch"]) == 2


def test_unknown_stage_is_an_error():
    with pytest.raises(SystemExit):
        main(["bogus"])
