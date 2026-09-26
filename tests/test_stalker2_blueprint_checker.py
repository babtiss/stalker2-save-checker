from pathlib import Path

import stalker2_blueprint_checker as checker


def make_raw_save(
    collected: list[str],
    outside_analytics: str | None = None,
    metadata_suffix: bytes = b"\x00",
) -> bytes:
    outside = outside_analytics.encode() if outside_analytics else b""
    analytics = b"\x00".join(
        blueprint.encode() + metadata_suffix for blueprint in collected
    )
    return (
        b"RoyalFlush"
        + (0).to_bytes(4, "little")
        + (1).to_bytes(4, "little")
        + outside
        + b"Analytics"
        + analytics
        + b"CampaignExtension"
        + outside
    )


def test_official_blueprint_list_has_77_unique_entries() -> None:
    assert len(checker.COUNTED_BLUEPRINTS) == 77
    assert len(set(checker.COUNTED_BLUEPRINTS)) == 77
    assert "Blueprint_Exoskeleton_Neutral_Armor_Upgrade_3" in checker.COUNTED_BLUEPRINTS
    assert "Blueprint_FaustPsyResist_Quest_1_1" not in checker.COUNTED_BLUEPRINTS


def test_checker_reports_one_missing_and_ignores_faust() -> None:
    missing = "Blueprint_Exoskeleton_Neutral_Armor_Upgrade_3"
    collected = [blueprint for blueprint in checker.COUNTED_BLUEPRINTS if blueprint != missing]
    collected.append("Blueprint_FaustPsyResist_Quest_1_1")

    result = checker.check_raw_save(make_raw_save(collected), Path("CampaignsSave.sav"))

    assert result.found_count == 76
    assert result.total_count == 77
    assert result.missing == [missing]
    assert result.ignored_blueprint_ids == ["Blueprint_FaustPsyResist_Quest_1_1"]
    assert result.royal_flush_current == 0
    assert result.royal_flush_goal == 1


def test_ascii_metadata_after_id_is_not_treated_as_part_of_id() -> None:
    result = checker.check_raw_save(
        make_raw_save(list(checker.COUNTED_BLUEPRINTS), metadata_suffix=b"H"),
        Path("CampaignsSave.sav"),
    )

    assert result.found_count == 77
    assert result.missing == []


def test_blueprint_ids_outside_analytics_are_not_counted() -> None:
    missing = checker.COUNTED_BLUEPRINTS[0]
    collected = list(checker.COUNTED_BLUEPRINTS[1:])

    result = checker.check_raw_save(
        make_raw_save(collected, outside_analytics=missing),
        Path("CampaignsSave.sav"),
    )

    assert result.found_count == 76
    assert result.missing == [missing]


def test_spawn_commands_use_physical_spawn_command() -> None:
    blueprint = "Blueprint_D12_Upgrade_1"
    assert checker.spawn_commands([blueprint]) == [f"XSpawnItemNearPlayerBySID {blueprint}"]
