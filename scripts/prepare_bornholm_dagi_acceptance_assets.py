from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CONFIG = ROOT / "script" / "semi_manual_r9" / "config" / "bornholm_r9_geocontext_layers.csv"
BASE_REGISTRY = ROOT / "apps" / "acceptance_model" / "registry.json"
OUT_CONFIG = ROOT / "script" / "acceptance" / "generated" / "bornholm_r9_geocontext_layers_dagi_landsdel.csv"
OUT_REGISTRY = ROOT / "apps" / "acceptance_model" / "registry_bornholm.json"

D_ROOT = Path("D:/LABLAB_Energiforsk/Projekt SL01/Geodatakatalog_SL01")
BORN_OUT_ROOT = D_ROOT / "Utkommande_SL01" / "UT_Bornholm_SL01"
BORN_IN_ROOT = D_ROOT / "Inkommande_SL01" / "IN_Bornholm_SL01"
DAGI_LANDSDEL = BORN_OUT_ROOT / "Basmap_BOR" / "DAGI_Landsdel_Scale10000_BOL_33.shp"
APP_HEX_GEOJSON = (
    ROOT
    / "exports"
    / "v2_multiregion"
    / "bornholm"
    / "bornholm_lablab_landscape_r9_dagi_landsdel_app.geojson"
)

OLD_USB_ROOT = "C:/gislab/data/dataraw/SL01_from_usb/Geodatakatalog_SL01"
OLD_REPO_ROOT = "C:/gislab/landskapsanalys"

MANUAL_SOURCE_OVERRIDES = {
    "NATUR_VILDT_RESERVAT.shp": BORN_IN_ROOT
    / "DATAKALLA_INNEHALL_BOL_SL01"
    / "Danmarks_Miljportal-Arealdata"
    / "NATUR_VILDT_RESERVAT_121224_SHAPE"
    / "NATUR_VILDT_RESERVAT.shp",
    "ds_fuglekollision_wfs.shp": BORN_IN_ROOT
    / "DATAKALLA_INNEHALL_BOL_SL01"
    / "Trafikstyrelsen"
    / "Luftfart_Trafikstyrelsen"
    / "ds_fuglekollision_wfs.shp",
}


def posix(path: Path) -> str:
    return path.as_posix()


def existing_path(path: Path) -> Path | None:
    return path if path.exists() else None


def candidate_roots() -> Iterable[Path]:
    yield BORN_OUT_ROOT
    yield BORN_IN_ROOT


def find_by_name(name: str) -> Path | None:
    if not name:
        return None
    for root in candidate_roots():
        if not root.exists():
            continue
        matches = [
            item
            for item in root.rglob(name)
            if item.name == name and not item.name.startswith("._")
        ]
        if matches:
            return sorted(matches, key=lambda item: len(posix(item)))[0]
    return None


def resolve_source_path(raw_path: str) -> tuple[str, str]:
    raw = str(raw_path or "").replace("\\", "/")
    if not raw:
        return raw, "empty"

    name = Path(raw).name
    override = MANUAL_SOURCE_OVERRIDES.get(name)
    if override is not None and override.exists():
        return posix(override), "manual_override"

    if raw.startswith(OLD_USB_ROOT):
        candidate = Path(raw.replace(OLD_USB_ROOT, posix(D_ROOT), 1))
        if candidate.exists():
            return posix(candidate), "usb_root_rewrite"

    if raw.startswith(OLD_REPO_ROOT):
        candidate = Path(raw.replace(OLD_REPO_ROOT, posix(ROOT), 1))
        if candidate.exists():
            return posix(candidate), "repo_root_rewrite"

    found = find_by_name(name)
    if found is not None:
        return posix(found), "bornholm_name_search"

    return raw, "unresolved"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    if not DAGI_LANDSDEL.exists():
        raise FileNotFoundError(f"DAGI landmask source not found: {DAGI_LANDSDEL}")
    if not APP_HEX_GEOJSON.exists():
        raise FileNotFoundError(f"Bornholm DAGI app hex GeoJSON not found: {APP_HEX_GEOJSON}")

    rows = read_csv(SOURCE_CONFIG)
    fieldnames = list(rows[0].keys())
    if "resolution_status" not in fieldnames:
        fieldnames.append("resolution_status")
    if "source_path_original" not in fieldnames:
        fieldnames.append("source_path_original")

    resolution_counts: dict[str, int] = {}
    for row in rows:
        original = row.get("source_path", "")
        resolved, status = resolve_source_path(original)
        row["source_path_original"] = original
        row["source_path"] = resolved
        row["resolution_status"] = status
        resolution_counts[status] = resolution_counts.get(status, 0) + 1

    layer_keys = {row.get("layer_key", "") for row in rows}
    if "dagi_landsdel_bornholm" not in layer_keys:
        rows.append(
            {
                "include": "TRUE",
                "layer_key": "dagi_landsdel_bornholm",
                "display_name": "Bornholm DAGI Landsdel landmask",
                "source_path": posix(DAGI_LANDSDEL),
                "layer_name": "DAGI_Landsdel_Scale10000_BOL_33",
                "provider": "ogr",
                "geometry": "",
                "value_field": "",
                "aggregation_type": "landmask",
                "notes": "Active Bornholm landmask for DAGI Landsdel acceptance refresh.",
                "resolution_status": "active_landmask",
                "source_path_original": "",
            }
        )
        resolution_counts["active_landmask"] = resolution_counts.get("active_landmask", 0) + 1

    write_csv(OUT_CONFIG, rows, fieldnames)

    with BASE_REGISTRY.open("r", encoding="utf-8") as handle:
        registry = json.load(handle)

    registry["analysis_id"] = "bornholm_wind_acceptance_prototype_dagi_landsdel"
    registry["source_config_csv"] = posix(OUT_CONFIG.relative_to(ROOT))
    registry["hex_gpkg"] = posix(APP_HEX_GEOJSON.relative_to(ROOT))
    registry["asset_dir"] = "docs/geocontext/acceptance_framework/data/prototype_assets_dagi_landsdel"
    registry["native_crs_epsg"] = 25833
    registry["landmask_label"] = "Bornholm DAGI Landsdel landmass"
    registry["landmask_layer_key"] = "dagi_landsdel_bornholm"
    registry["landmask_source_path"] = posix(DAGI_LANDSDEL)
    registry["asset_method_note"] = (
        "Acceptance source GeoJSON, analysis RDS and distance tables are rebuilt from the "
        "LABLAB Bornholm raw sources and clipped to DAGI_Landsdel_Scale10000_BOL_33."
    )
    registry["created_at"] = "2026-06-23"

    OUT_REGISTRY.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    active_layer_keys = {str(item.get("layer_key", "")) for item in registry.get("layers", [])}
    active_layer_keys.add(str(registry.get("landmask_layer_key", "")))
    unresolved = [
        row
        for row in rows
        if row.get("resolution_status") == "unresolved"
        and row.get("include") == "TRUE"
        and row.get("layer_key") in active_layer_keys
    ]
    print(f"Wrote source config: {OUT_CONFIG.relative_to(ROOT)}")
    print(f"Wrote registry: {OUT_REGISTRY.relative_to(ROOT)}")
    print("Resolution counts:")
    for status, count in sorted(resolution_counts.items()):
        print(f"  {status}: {count}")
    if unresolved:
        print("Unresolved included sources:")
        for row in unresolved:
            print(f"  {row.get('layer_key')}: {row.get('source_path')}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
