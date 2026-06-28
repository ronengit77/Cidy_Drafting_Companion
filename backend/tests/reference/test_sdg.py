from cidy.reference.sdg import SDGFramework, load_sdg_framework

DATA = {
    "goals": [
        {
            "goal": 8,
            "title": "Decent Work and Economic Growth",
            "targets": [
                {"target": "8.5", "text": "Full and productive employment..."},
                {"target": "8.6", "text": "Reduce youth not in employment..."},
            ],
        }
    ]
}


def test_load_and_lookup():
    fw = load_sdg_framework(DATA)
    assert isinstance(fw, SDGFramework)
    assert fw.has_target("8.5") is True
    assert fw.get_target("8.6").text.startswith("Reduce youth")


def test_unknown_target():
    fw = load_sdg_framework(DATA)
    assert fw.has_target("99.9") is False
    assert fw.get_target("99.9") is None


def test_all_target_codes():
    fw = load_sdg_framework(DATA)
    assert fw.all_target_codes() == {"8.5", "8.6"}
