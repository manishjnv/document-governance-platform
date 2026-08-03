"""ATT&CK threat-group catalog (coverage tab overlay): shape + referential
integrity of the groups baked into attack.json by build_attack_data.py."""

from app.mitre.attack_data import DEFAULT


def test_groups_present_and_sorted():
    groups = DEFAULT.groups
    assert len(groups) >= 100  # enterprise alone ships ~170 in v19.1
    names = [g["name"].lower() for g in groups]
    assert names == sorted(names)
    sample = groups[0]
    assert set(sample) == {"id", "name", "aliases", "technique_ids"}
    assert sample["id"].startswith("G")


def test_group_technique_ids_are_live():
    for g in DEFAULT.groups:
        assert g["technique_ids"], g["id"]
        for tid in g["technique_ids"]:
            tech = DEFAULT.get(tid)
            assert tech is not None, f"{g['id']} cites unknown {tid}"
            assert not tech.get("revoked"), f"{g['id']} cites revoked {tid}"
