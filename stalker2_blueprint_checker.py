#!/usr/bin/env python3
"""Check which of the 77 counted STALKER 2 upgrade blueprints are missing.

The script is intentionally read-only: it decompresses CampaignsSave.sav in
memory and never modifies the save. It uses only Python's standard library,
plus oo2core_9_win64.dll for the game's Oodle-compressed save format.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import io
import json
import os
import struct
import sys
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


OODLE_ARCHIVE_URL = (
    "https://github.com/vaibhavpandeyvpz/unpaker/releases/download/"
    "v1.1.0/Unpaker.CLI-v1.1.0.zip"
)
OODLE_ARCHIVE_SHA256 = "cf9475f6f1da4c025d43ea0a9bd51bd5ae21947666f4fc21aff0922d06d25e2b"
OODLE_DLL_SHA256 = "6f5d41a7892ea6b2db420f2458dad2f84a63901c9a93ce9497337b16c195f457"
OODLE_DLL_NAME = "oo2core_9_win64.dll"
MAX_ARCHIVE_SIZE = 20 * 1024 * 1024
MAX_UNCOMPRESSED_SAVE_SIZE = 256 * 1024 * 1024
SPAWN_COMMAND = "XSpawnItemNearPlayerBySID"

# Source: Blueprints.Items in the game's Statistics.cfg (77 entries).
# Blueprint_FaustPsyResist_Quest_1_1 is deliberately absent: it is a quest
# blueprint and does not increment the PDA's upgrade-flash-drive statistic.
COUNTED_BLUEPRINTS = (
    "Blueprint_APB_Upgrade_1",
    "Blueprint_APB_Upgrade_2",
    "Blueprint_BattleExoskeleton_Varta_Armor_Upgrade_1",
    "Blueprint_BattleExoskeleton_Varta_Armor_Upgrade_2",
    "Blueprint_BattleExoskeleton_Varta_Armor_Upgrade_3",
    "Blueprint_BattleExoskeleton_Varta_Armor_Upgrade_4",
    "Blueprint_Battle_Military_Helmet_Upgrade_1",
    "Blueprint_D12_Upgrade_1",
    "Blueprint_D12_Upgrade_2",
    "Blueprint_Dnipro_Upgrade_1",
    "Blueprint_Dnipro_Upgrade_2",
    "Blueprint_Exoskeleton_Dolg_Armor_Upgrade_1",
    "Blueprint_Exoskeleton_Dolg_Armor_Upgrade_2",
    "Blueprint_Exoskeleton_Dolg_Armor_Upgrade_3",
    "Blueprint_Exoskeleton_Dolg_Armor_Upgrade_4",
    "Blueprint_Exoskeleton_Mercenaries_Armor_Upgrade_1",
    "Blueprint_Exoskeleton_Mercenaries_Armor_Upgrade_2",
    "Blueprint_Exoskeleton_Mercenaries_Armor_Upgrade_3",
    "Blueprint_Exoskeleton_Mercenaries_Armor_Upgrade_4",
    "Blueprint_Exoskeleton_Neutral_Armor_Upgrade_1",
    "Blueprint_Exoskeleton_Neutral_Armor_Upgrade_2",
    "Blueprint_Exoskeleton_Neutral_Armor_Upgrade_3",
    "Blueprint_Exoskeleton_Neutral_Armor_Upgrade_4",
    "Blueprint_Exoskeleton_Svoboda_Armor_Upgrade_1",
    "Blueprint_Exoskeleton_Svoboda_Armor_Upgrade_2",
    "Blueprint_Exoskeleton_Svoboda_Armor_Upgrade_3",
    "Blueprint_Exoskeleton_Svoboda_Armor_Upgrade_4",
    "Blueprint_Grim_Upgrade_1",
    "Blueprint_Gvintar_Upgrade_1",
    "Blueprint_Gvintar_Upgrade_2",
    "Blueprint_Heavy2_Military_Armor_Upgrade_1",
    "Blueprint_Heavy2_Military_Armor_Upgrade_2",
    "Blueprint_HeavyAnomaly_Scientific_Armor_Upgrade_1",
    "Blueprint_HeavyAnomaly_Scientific_Armor_Upgrade_2",
    "Blueprint_HeavyBattle_Spark_Armor_Upgrade_1",
    "Blueprint_HeavyBattle_Spark_Armor_Upgrade_2",
    "Blueprint_HeavyExoskeleton_Dolg_Armor_Upgrade_1",
    "Blueprint_HeavyExoskeleton_Dolg_Armor_Upgrade_2",
    "Blueprint_HeavyExoskeleton_Dolg_Armor_Upgrade_3",
    "Blueprint_HeavyExoskeleton_Dolg_Armor_Upgrade_4",
    "Blueprint_HeavyExoskeleton_Svoboda_Armor_Upgrade_1",
    "Blueprint_HeavyExoskeleton_Svoboda_Armor_Upgrade_2",
    "Blueprint_HeavyExoskeleton_Svoboda_Armor_Upgrade_3",
    "Blueprint_HeavyExoskeleton_Svoboda_Armor_Upgrade_4",
    "Blueprint_Heavy_Dolg_Armor_Upgrade_1",
    "Blueprint_Heavy_Dolg_Armor_Upgrade_2",
    "Blueprint_Heavy_Duty_Helmet_Upgrade_1",
    "Blueprint_Heavy_Military_Helmet_Upgrade_1",
    "Blueprint_Heavy_Svoboda_Armor_Upgrade_1",
    "Blueprint_Heavy_Svoboda_Armor_Upgrade_2",
    "Blueprint_Heavy_Svoboda_Helmet_Upgrade_1",
    "Blueprint_Integral_Upgrade_1",
    "Blueprint_Kharod_Upgrade_1",
    "Blueprint_Kharod_Upgrade_2",
    "Blueprint_Lavina_Upgrade_1",
    "Blueprint_Lavina_Upgrade_2",
    "Blueprint_M10_Upgrade_1",
    "Blueprint_M701_Upgrade_1",
    "Blueprint_M701_Upgrade_2",
    "Blueprint_M860_Upgrade_1",
    "Blueprint_MG_Upgrade_1",
    "Blueprint_MG_Upgrade_2",
    "Blueprint_Ram2_Upgrade_1",
    "Blueprint_Ram2_Upgrade_2",
    "Blueprint_Rhino_Upgrade_1",
    "Blueprint_SEVA_Dolg_Armor_Upgrade_1",
    "Blueprint_SEVA_Dolg_Armor_Upgrade_2",
    "Blueprint_SEVA_Neutral_Armor_Upgrade_1",
    "Blueprint_SEVA_Neutral_Armor_Upgrade_2",
    "Blueprint_SEVA_Spark_Armor_Upgrade_1",
    "Blueprint_SEVA_Spark_Armor_Upgrade_2",
    "Blueprint_SEVA_Svoboda_Armor_Upgrade_1",
    "Blueprint_SEVA_Svoboda_Armor_Upgrade_2",
    "Blueprint_SVU_Upgrade_1",
    "Blueprint_SVU_Upgrade_2",
    "Blueprint_Zubr_Upgrade_1",
    "Blueprint_Zubr_Upgrade_2",
)

# Known Blueprint IDs that can be present in Analytics but are intentionally not
# part of the PDA counter. Using an explicit list matters here: the byte directly
# after a serialized ID is binary metadata and can itself look like an ASCII
# letter or digit, so a generic regex can accidentally treat it as part of the ID.
NON_COUNTED_BLUEPRINTS = ("Blueprint_FaustPsyResist_Quest_1_1",)
ANALYTICS_END_MARKERS = (b"CampaignExtension", b"SaveSlotStorage", b"CampaignDifficulties")


class CheckerError(RuntimeError):
    """An expected, user-facing checker error."""


@dataclass(frozen=True)
class CheckResult:
    save: str
    found_count: int
    total_count: int
    missing: list[str]
    ignored_blueprint_ids: list[str]
    royal_flush_current: int | None
    royal_flush_goal: int | None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def default_oodle_cache_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "stalker2-blueprint-checker" / OODLE_DLL_NAME
    return Path(__file__).resolve().parent / ".stalker2-blueprint-checker" / OODLE_DLL_NAME


def download_oodle_dll(destination: Path) -> Path:
    print(f"Скачиваю Oodle-декодер из {OODLE_ARCHIVE_URL}", file=sys.stderr)
    request = urllib.request.Request(OODLE_ARCHIVE_URL, headers={"User-Agent": "stalker2-blueprint-checker/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            archive = response.read(MAX_ARCHIVE_SIZE + 1)
    except OSError as exc:
        raise CheckerError(f"не удалось скачать Oodle-декодер: {exc}") from exc

    if len(archive) > MAX_ARCHIVE_SIZE:
        raise CheckerError("архив Oodle оказался неожиданно большим")
    archive_hash = sha256_bytes(archive)
    if archive_hash != OODLE_ARCHIVE_SHA256:
        raise CheckerError(
            "SHA-256 скачанного архива Oodle не совпал с ожидаемым "
            f"({archive_hash} != {OODLE_ARCHIVE_SHA256})"
        )

    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            member = next(
                (name for name in zip_file.namelist() if Path(name).name.lower() == OODLE_DLL_NAME.lower()),
                None,
            )
            if member is None:
                raise CheckerError(f"в архиве не найден {OODLE_DLL_NAME}")
            dll_data = zip_file.read(member)
    except zipfile.BadZipFile as exc:
        raise CheckerError("скачанный архив Oodle повреждён") from exc

    dll_hash = sha256_bytes(dll_data)
    if dll_hash != OODLE_DLL_SHA256:
        raise CheckerError(
            "SHA-256 Oodle DLL не совпал с ожидаемым "
            f"({dll_hash} != {OODLE_DLL_SHA256})"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_bytes(dll_data)
    temporary.replace(destination)
    return destination


def oodle_candidates(explicit_path: Path | None) -> list[Path]:
    candidates: list[Path] = []
    if explicit_path is not None:
        candidates.append(explicit_path)

    env_path = os.environ.get("STALKER2_OODLE_DLL")
    if env_path:
        candidates.append(Path(env_path))

    script_dir = Path(__file__).resolve().parent
    candidates.extend((script_dir / OODLE_DLL_NAME, Path.cwd() / OODLE_DLL_NAME, default_oodle_cache_path()))

    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    if program_files_x86:
        game_root = (
            Path(program_files_x86)
            / "Steam"
            / "steamapps"
            / "common"
            / "S.T.A.L.K.E.R. 2 Heart of Chornobyl"
        )
        candidates.extend(
            (
                game_root / "Stalker2" / "Binaries" / "Win64" / OODLE_DLL_NAME,
                game_root / "Stalker2" / "Content" / "Paks" / OODLE_DLL_NAME,
                game_root / "Engine" / "Binaries" / "ThirdParty" / "Oodle" / "Win64" / OODLE_DLL_NAME,
            )
        )

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.expanduser().resolve(strict=False)).lower()
        if key not in seen:
            unique.append(candidate.expanduser())
            seen.add(key)
    return unique


def resolve_oodle_dll(explicit_path: Path | None, allow_download: bool) -> Path:
    for candidate in oodle_candidates(explicit_path):
        if candidate.is_file():
            return candidate.resolve()

    if allow_download:
        return download_oodle_dll(default_oodle_cache_path()).resolve()

    raise CheckerError(
        f"не найден {OODLE_DLL_NAME}. Положите DLL рядом со скриптом, укажите "
        "--oodle-dll ПУТЬ или разрешите проверенную загрузку флагом --download-oodle"
    )


def find_campaign_save(explicit_path: Path | None) -> Path:
    if explicit_path is not None:
        path = explicit_path.expanduser().resolve(strict=False)
        if not path.is_file():
            raise CheckerError(f"файл сейва не найден: {path}")
        return path

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise CheckerError("переменная LOCALAPPDATA не задана; укажите сейв явно через --save")

    saved_root = Path(local_app_data) / "Stalker2" / "Saved"
    candidates = list(saved_root.glob("*/SaveGames/CampaignsSave.sav"))
    candidates.extend(saved_root.glob("SaveGames/CampaignsSave.sav"))
    candidates = [candidate for candidate in candidates if candidate.is_file()]
    if not candidates:
        raise CheckerError(
            f"CampaignsSave.sav не найден внутри {saved_root}. Укажите путь явно через --save"
        )
    return max(candidates, key=lambda candidate: candidate.stat().st_mtime).resolve()


def decompress_campaign_save(save_path: Path, oodle_dll_path: Path) -> bytes:
    if os.name != "nt":
        raise CheckerError("автоматическая распаковка сейчас поддерживается только в Windows")

    packed = save_path.read_bytes()
    if len(packed) < 5:
        raise CheckerError("файл сейва слишком короткий")

    expected_size = struct.unpack_from("<I", packed)[0]
    if expected_size <= 0 or expected_size > MAX_UNCOMPRESSED_SAVE_SIZE:
        raise CheckerError(f"подозрительный размер распакованного сейва: {expected_size} байт")

    compressed = packed[4:]
    try:
        library = ctypes.WinDLL(str(oodle_dll_path))
    except OSError as exc:
        raise CheckerError(f"не удалось загрузить {oodle_dll_path}: {exc}") from exc

    decompress = library.OodleLZ_Decompress
    decompress.restype = ctypes.c_ssize_t
    decompress.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ssize_t,
        ctypes.c_void_p,
        ctypes.c_ssize_t,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_ssize_t,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_ssize_t,
        ctypes.c_int,
    ]

    source_buffer = ctypes.create_string_buffer(compressed)
    destination_buffer = ctypes.create_string_buffer(expected_size)
    result = decompress(
        source_buffer,
        len(compressed),
        destination_buffer,
        expected_size,
        1,
        0,
        0,
        None,
        0,
        None,
        None,
        None,
        0,
        3,
    )
    if result != expected_size:
        raise CheckerError(
            f"Oodle не смог распаковать сейв: ожидалось {expected_size} байт, получено {result}"
        )
    return destination_buffer.raw


def analytics_segment(raw_save: bytes) -> bytes:
    start = raw_save.find(b"Analytics")
    if start < 0:
        raise CheckerError("в CampaignsSave.sav не найден раздел Analytics")

    end_positions = [
        position
        for marker in ANALYTICS_END_MARKERS
        if (position := raw_save.find(marker, start + len(b"Analytics"))) >= 0
    ]
    end = min(end_positions) if end_positions else len(raw_save)
    return raw_save[start:end]


def collected_blueprint_ids(raw_save: bytes) -> set[str]:
    segment = analytics_segment(raw_save)
    known_blueprints = (*COUNTED_BLUEPRINTS, *NON_COUNTED_BLUEPRINTS)
    return {
        blueprint
        for blueprint in known_blueprints
        if blueprint.encode("ascii") in segment
    }


def royal_flush_progress(raw_save: bytes) -> tuple[int | None, int | None]:
    marker = b"RoyalFlush"
    position = raw_save.find(marker)
    if position < 0:
        return None, None
    value_position = position + len(marker)
    if value_position + 8 > len(raw_save):
        return None, None
    current, goal = struct.unpack_from("<II", raw_save, value_position)
    if current > 1000 or goal > 1000:
        return None, None
    return current, goal


def check_raw_save(raw_save: bytes, save_path: Path) -> CheckResult:
    collected = collected_blueprint_ids(raw_save)
    required = set(COUNTED_BLUEPRINTS)
    missing = [blueprint for blueprint in COUNTED_BLUEPRINTS if blueprint not in collected]
    ignored = sorted(collected - required)
    royal_flush_current, royal_flush_goal = royal_flush_progress(raw_save)
    return CheckResult(
        save=str(save_path),
        found_count=len(required & collected),
        total_count=len(COUNTED_BLUEPRINTS),
        missing=missing,
        ignored_blueprint_ids=ignored,
        royal_flush_current=royal_flush_current,
        royal_flush_goal=royal_flush_goal,
    )


def spawn_commands(blueprints: Sequence[str]) -> list[str]:
    return [f"{SPAWN_COMMAND} {blueprint}" for blueprint in blueprints]


def print_human_report(result: CheckResult) -> None:
    print(f"Сейв: {result.save}")
    print(f"Засчитываемые флешки: {result.found_count}/{result.total_count}")
    if result.royal_flush_current is not None and result.royal_flush_goal is not None:
        print(f"RoyalFlush: {result.royal_flush_current}/{result.royal_flush_goal}")

    if result.missing:
        print(f"\nНе найдено: {len(result.missing)}")
        for index, blueprint in enumerate(result.missing, start=1):
            print(f"  {index}. {blueprint}")
        print("\nКоманды для физического спавна (предметы нужно подобрать с земли):")
        for command in spawn_commands(result.missing):
            print(command)
    else:
        print("\nВсе 77 засчитываемых флешек найдены.")

    if result.ignored_blueprint_ids:
        print("\nНезасчитываемые Blueprint-ID в Analytics (это нормально):")
        for blueprint in result.ignored_blueprint_ids:
            print(f"  {blueprint}")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Проверяет 77 засчитываемых флешек улучшений в STALKER 2 CampaignsSave.sav."
    )
    parser.add_argument(
        "--save",
        type=Path,
        help="путь к CampaignsSave.sav; без параметра сейв ищется в %%LOCALAPPDATA%%\\Stalker2\\Saved",
    )
    parser.add_argument("--oodle-dll", type=Path, help=f"явный путь к {OODLE_DLL_NAME}")
    parser.add_argument(
        "--download-oodle",
        action="store_true",
        help="если DLL не найдена, скачать закреплённый архив Unpaker v1.1.0 с проверкой SHA-256",
    )
    parser.add_argument("--json", action="store_true", help="вывести результат в JSON")
    parser.add_argument(
        "--write-commands",
        type=Path,
        metavar="FILE",
        help="записать команды спавна недостающих флешек в указанный текстовый файл",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    save_path = find_campaign_save(args.save)
    oodle_dll_path = resolve_oodle_dll(args.oodle_dll, args.download_oodle)
    raw_save = decompress_campaign_save(save_path, oodle_dll_path)
    result = check_raw_save(raw_save, save_path)

    if args.write_commands is not None:
        output_path = args.write_commands.expanduser().resolve(strict=False)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        commands = spawn_commands(result.missing)
        output_path.write_text("\n".join(commands) + ("\n" if commands else ""), encoding="utf-8")

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print_human_report(result)
        if args.write_commands is not None:
            print(f"\nКоманды записаны в: {args.write_commands.expanduser().resolve(strict=False)}")
    return 0


def configure_output_encoding() -> None:
    """Keep Russian output readable in Windows terminals and redirected logs."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_output_encoding()
    try:
        return run()
    except (CheckerError, OSError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
