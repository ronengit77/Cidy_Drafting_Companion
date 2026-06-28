from pathlib import Path

from cidy.reference.sdg import load_sdg_framework_file

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "sdg_framework.json"


def test_framework_loads_all_goals():
    fw = load_sdg_framework_file(DATA_PATH)
    goals = {g.goal for g in fw.goals}
    assert goals == set(range(1, 18))  # goals 1..17


def test_framework_has_169_targets():
    fw = load_sdg_framework_file(DATA_PATH)
    assert len(fw.all_target_codes()) == 169


def test_known_targets_present():
    fw = load_sdg_framework_file(DATA_PATH)
    assert fw.has_target("8.5")
    assert fw.has_target("1.1")
    assert fw.has_target("17.1")
