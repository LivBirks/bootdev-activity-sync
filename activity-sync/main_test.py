import datetime as dt
import json
from pathlib import Path

import pytest

from main import HeatmapError, compute_todo, load_state, parse_heatmap, save_state

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name):
    with open(FIXTURES / name) as json_data:
        return json.load(json_data)


# parse_heatmap with the sample fixture, checking the three days from Phase 0
def test_one():
    result = parse_heatmap(load_fixture("heatmap_sample.json"))
    assert result[dt.date(2026, 8, 15)] == 24
    assert result[dt.date(2026, 8, 16)] == 82
    assert result[dt.date(2026, 8, 17)] == 17


# malformed fixture raises
def test_two():
    with pytest.raises(HeatmapError, match="invalid data"):
        parse_heatmap(load_fixture("heatmap_sample_malformed.json"))


# empty fixture raises
def test_three():
    with pytest.raises(HeatmapError, match="No calendar data"):
        parse_heatmap(load_fixture("heatmap_sample_empty.json"))


# a missing state file means nothing synced yet
def test_four(tmp_path):
    result = load_state(tmp_path / "missing.json")
    assert result == {}


# a valid state file loads with date keys
def test_five():
    result = load_state(FIXTURES / "state_sample.json")
    assert result == {
        dt.date(2026, 8, 15): 24,
        dt.date(2026, 8, 16): 82,
        dt.date(2026, 8, 17): 17,
    }


# a corrupt state file raises
def test_six():
    with pytest.raises(json.decoder.JSONDecodeError):
        load_state(FIXTURES / "state_corrupt.json")


@pytest.fixture
def sample_state():
    return {
        dt.date(2026, 10, 31): 23,
        dt.date(2026, 8, 15): 24,
        dt.date(2026, 9, 1): 5,
    }


# round trip - save a dict with dt.date keys and load it back with load_state and assert its back to the same thing
def test_seven(tmp_path, sample_state):
    path = tmp_path / "state.json"
    save_state(sample_state, path)
    assert load_state(path) == sample_state


# the file on disk has string keys, read with plain json.load so load_state can't hide a mistake
def test_eight(tmp_path, sample_state):
    path = tmp_path / "state.json"
    save_state(sample_state, path)
    with open(path) as json_data:
        raw = json.load(json_data)
    assert raw == {
        "2026-08-15": 24,
        "2026-09-01": 5,
        "2026-10-31": 23,
    }


# keys are written in date order even when the input is not
def test_nine(tmp_path, sample_state):
    path = tmp_path / "state.json"
    save_state(sample_state, path)
    with open(path) as json_data:
        raw = json.load(json_data)
    assert list(raw) == sorted(raw)


# saving twice overwrites, it does not append
def test_ten(tmp_path, sample_state):
    path = tmp_path / "state.json"
    save_state(sample_state, path)
    new_state = {dt.date(2026, 11, 1): 3}
    save_state(new_state, path)
    assert load_state(path) == new_state


# empty state round trips
def test_eleven(tmp_path):
    path = tmp_path / "state.json"
    save_state({}, path)
    assert load_state(path) == {}


# a bad key raises and leaves the existing file untouched
def test_twelve(tmp_path, sample_state):
    path = tmp_path / "state.json"
    save_state(sample_state, path)
    with pytest.raises((TypeError, AttributeError)):
        save_state({"not a date": 1}, path)
    assert load_state(path) == sample_state


# the dict passed in is not changed
def test_thirteen(tmp_path, sample_state):
    path = tmp_path / "state.json"
    before = dict(sample_state)
    save_state(sample_state, path)
    assert sample_state == before


# a date not in state yet owes its full count
def test_fourteen():
    activity = {dt.date(2026, 11, 1): 5}
    assert compute_todo(activity, {}) == {dt.date(2026, 11, 1): 5}


# a fully synced date is left out
def test_fifteen():
    activity = {dt.date(2026, 11, 1): 5}
    state = {dt.date(2026, 11, 1): 5}
    assert compute_todo(activity, state) == {}


# a partly synced date owes the difference
def test_sixteen():
    activity = {dt.date(2026, 11, 1): 5}
    state = {dt.date(2026, 11, 1): 2}
    assert compute_todo(activity, state) == {dt.date(2026, 11, 1): 3}


# boot.dev's count went down - never owe a negative, leave it out
def test_seventeen():
    activity = {dt.date(2026, 11, 1): 3}
    state = {dt.date(2026, 11, 1): 5}
    assert compute_todo(activity, state) == {}


# a day with no activity owes nothing
def test_eighteen():
    activity = {dt.date(2026, 11, 1): 0}
    assert compute_todo(activity, {}) == {}


# empty activity owes nothing
def test_nineteen():
    state = {dt.date(2026, 11, 1): 5}
    assert compute_todo({}, state) == {}


# dates only in state are not in the result
def test_twenty():
    activity = {dt.date(2026, 11, 2): 1}
    state = {dt.date(2026, 11, 1): 5}
    assert compute_todo(activity, state) == {dt.date(2026, 11, 2): 1}


# a mix of all the cases at once
def test_twenty_one():
    activity = {
        dt.date(2026, 11, 1): 5,
        dt.date(2026, 11, 2): 5,
        dt.date(2026, 11, 3): 3,
        dt.date(2026, 11, 4): 4,
    }
    state = {
        dt.date(2026, 11, 1): 5,
        dt.date(2026, 11, 2): 2,
        dt.date(2026, 11, 3): 5,
    }
    assert compute_todo(activity, state) == {
        dt.date(2026, 11, 2): 3,
        dt.date(2026, 11, 4): 4,
    }


# neither input is changed
def test_twenty_two():
    activity = {dt.date(2026, 11, 1): 5, dt.date(2026, 11, 2): 1}
    state = {dt.date(2026, 11, 1): 2}
    activity_before = dict(activity)
    state_before = dict(state)
    compute_todo(activity, state)
    assert activity == activity_before
    assert state == state_before


# dates before start_date are skipped, start_date itself is included
def test_twenty_three():
    activity = {
        dt.date(2026, 10, 31): 2,
        dt.date(2026, 11, 1): 3,
        dt.date(2026, 11, 2): 4,
    }
    result = compute_todo(activity, {}, start_date=dt.date(2026, 11, 1))
    assert result == {
        dt.date(2026, 11, 1): 3,
        dt.date(2026, 11, 2): 4,
    }


# start_date of None means no limit
def test_twenty_four():
    activity = {dt.date(2020, 1, 1): 2, dt.date(2026, 11, 1): 3}
    assert compute_todo(activity, {}, start_date=None) == activity
