#!/usr/bin/env python3
"""Assemble a cs2-dumper offline output directory into the fumetsu.cc data.json
payload shape that FUMETSU's sdk_fetch.h and tools/gen_offsets.ps1 already
consume (offsets_flat + classes + buttons + build).

cs2-dumper (run offline against the downloaded DLLs) emits:
  offsets.hpp      - module globals  (namespace client_dll / engine2_dll)
  client_dll.hpp   - schema classes  (namespace <CS2ClassName>)
  buttons.hpp      - button globals  (namespace client_dll)
  info.json        - build_number, timestamp

We parse those and emit payload.json. Fail-closed: if any global we depend on is
missing we exit non-zero so the workflow never publishes a half dump.

  python make_offsets.py --dump-dir <dir> --steam-buildid <id> --out payload.json
"""
import argparse, json, re, sys

# dwFoo (cs2-dumper global name) -> flat key gen_offsets.ps1 / sdk_fetch.h expect
GLOBAL_MAP = {
    "dwEntityList": "offsets::client::EntityList",
    "dwLocalPlayerController": "offsets::client::LocalPlayerController",
    "dwLocalPlayerPawn": "offsets::client::LocalPlayerPawn",
    "dwViewMatrix": "offsets::client::ViewMatrix",
    "dwViewAngles": "offsets::client::ViewAngles",
    "dwGlobalVars": "offsets::client::GlobalVars",
    "dwGameRules": "offsets::client::GameRules",
    "dwGameEntitySystem": "offsets::client::GameEntitySystem",
    "dwGlowManager": "offsets::client::GlowManager",
    "dwCSGOInput": "offsets::client::CSGOInput",
    "dwPlantedC4": "offsets::client::PlantedC4",
    "dwSensitivity": "offsets::client::Sensitivity",
    "dwSensitivity_sensitivity": "offsets::client::Sensitivity_sensitivity",
    "dwBuildNumber": "offsets::engine2::BuildNumber",
    "dwNetworkGameClient": "offsets::engine2::NetworkGameClient",
    "dwNetworkGameClient_deltaTick": "offsets::engine2::NetworkGameClient_deltaTick",
}

# Globals the DLL cannot run without. Missing one of these = fail, do not publish.
REQUIRED_GLOBALS = [
    "dwEntityList", "dwLocalPlayerController", "dwLocalPlayerPawn",
    "dwViewMatrix", "dwViewAngles", "dwGlobalVars", "dwBuildNumber",
]
REQUIRED_BUTTONS = ["attack", "attack2", "jump", "duck", "use", "reload"]

NS_RE = re.compile(r"namespace\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{")
FIELD_RE = re.compile(
    r"constexpr\s+std::ptrdiff_t\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(0x[0-9A-Fa-f]+)")


def parse_hpp(path):
    """-> {namespace: {field: '0x..'}}; tolerant of missing files."""
    out = {}
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return out
    cur = None
    for line in text.splitlines():
        m = NS_RE.search(line)
        if m:
            cur = m.group(1)
            out.setdefault(cur, {})
            continue
        if cur:
            m = FIELD_RE.search(line)
            if m:
                out[cur][m.group(1)] = m.group(2)
    return out


def flatten_globals(ns_map):
    """Merge every namespace in offsets.hpp/buttons.hpp into one dw* lookup."""
    flat = {}
    for fields in ns_map.values():
        flat.update(fields)
    return flat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", required=True)
    ap.add_argument("--steam-buildid", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    d = a.dump_dir.rstrip("/\\")
    globals_raw = flatten_globals(parse_hpp(f"{d}/offsets.hpp"))
    buttons_raw = flatten_globals(parse_hpp(f"{d}/buttons.hpp"))
    classes = parse_hpp(f"{d}/client_dll.hpp")

    try:
        info = json.load(open(f"{d}/info.json", encoding="utf-8"))
        build = int(info.get("build_number") or info.get("game_build") or 0)
    except (OSError, ValueError):
        build = 0

    missing = [g for g in REQUIRED_GLOBALS if g not in globals_raw]
    missing += [f"button:{b}" for b in REQUIRED_BUTTONS if b not in buttons_raw]
    if build == 0:
        missing.append("build_number")
    if missing:
        print("FAIL - dump incomplete, refusing to publish:", file=sys.stderr)
        for m in missing:
            print("  missing", m, file=sys.stderr)
        return 2

    offsets_flat = {}
    for dw, flat_key in GLOBAL_MAP.items():
        if dw in globals_raw:
            offsets_flat[flat_key] = globals_raw[dw]

    payload = {
        "build": build,
        "steam_buildid": str(a.steam_buildid),
        "offsets_flat": offsets_flat,
        "classes": classes,
        "buttons": {k: v for k, v in buttons_raw.items()},
    }
    json.dump(payload, open(a.out, "w", encoding="utf-8"),
              indent=2, sort_keys=True)
    print(f"wrote {a.out}: build {build}, "
          f"{len(offsets_flat)} globals, {len(classes)} classes, "
          f"{len(buttons_raw)} buttons")
    return 0


if __name__ == "__main__":
    sys.exit(main())
