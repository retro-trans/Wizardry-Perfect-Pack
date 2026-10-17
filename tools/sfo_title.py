#!/usr/bin/env python3
"""Preview a lossless-layout English PARAM.SFO title patch; --write creates copies.

Only TITLE/TITLE_00 data slots and their current-length fields may change. All
other bytes, including version, capacity, padding and key order, are retained.
The manifest contains reversible byte edits, with hashes checked on restoration.
Format reference: https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Loader/PSF.h
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "work/output/metadata"
TITLE = "Wizardry: Prisoners of the Lost City"
TARGETS = ("PARAM.SFO",)
HEADER = struct.Struct("<4s4I")
ENTRY = struct.Struct("<HHIII")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def parse_sfo(data):
    """Read bounded fields without canonicalizing or discarding any bytes."""
    if len(data) < HEADER.size:
        raise ValueError("Truncated SFO header")
    magic, version, keys, values, count = HEADER.unpack_from(data)
    if magic != b"\0PSF" or version != 0x101:
        raise ValueError("Unsupported SFO magic/version")
    if not HEADER.size + count * ENTRY.size <= keys <= values <= len(data):
        raise ValueError("Invalid SFO table bounds")
    result = {}
    spans = []
    for i in range(count):
        index = HEADER.size + i * ENTRY.size
        keyoff, fmt, length, capacity, offset = ENTRY.unpack_from(data, index)
        start = keys + keyoff
        end = data.find(b"\0", start, values) if start < values else -1
        if start < keys or end < 0:
            raise ValueError("Unterminated or out-of-range SFO key")
        key = data[start:end].decode("ascii")
        if not key or key in result:
            raise ValueError("Empty/duplicate SFO key")
        pos = values + offset
        if length > capacity or pos < values or pos + capacity > len(data):
            raise ValueError("Out-of-range SFO value: " + key)
        if capacity and any(pos < b and a < pos + capacity for a, b in spans):
            raise ValueError("Overlapping SFO value: " + key)
        spans.append((pos, pos + capacity))
        value = data[pos:pos + length]
        if fmt == 0x204:
            if not value or not value.endswith(b"\0") or b"\0" in value[:-1]:
                raise ValueError("Malformed SFO string: " + key)
            value[:-1].decode("utf-8")
        elif fmt == 0x404 and (length != 4 or capacity != 4):
            raise ValueError("Malformed SFO integer: " + key)
        result[key] = dict(index=index, format=fmt, length=length,
                           capacity=capacity, position=pos, value=value)
    return result


def apply_edits(data, edits, reverse=False):
    """Apply exact preimage-checked, nonoverlapping edits in either direction."""
    patched = bytearray(data)
    spans = []
    for edit in edits:
        offset = edit["offset"]
        before = bytes.fromhex(edit["after" if reverse else "before"])
        after = bytes.fromhex(edit["before" if reverse else "after"])
        if not isinstance(offset, int) or offset < 0 or len(before) != len(after):
            raise ValueError("Invalid edit bounds")
        end = offset + len(before)
        if end > len(data) or any(offset < b and a < end for a, b in spans):
            raise ValueError("Overlapping/out-of-range edit")
        if data[offset:end] != before:
            raise ValueError("Edit preimage mismatch")
        spans.append((offset, end))
        patched[offset:end] = after
    return bytes(patched)


def translate_sfo(data):
    """Return (patched_bytes, manifest_record), without writing any files."""
    entries = parse_sfo(data)
    if "TITLE" not in entries or entries["TITLE"]["format"] != 0x204:
        raise ValueError("Missing string TITLE")
    source_title = entries["TITLE"]["value"][:-1].decode("utf-8")
    # Explicit trial wording only; package location alone never implies a demo.
    trial = "\u4f53\u9a13\u7248" in source_title or bool(re.search(r"\b(?:demo|trial)\b", source_title, re.I))
    title = TITLE + (" (Demo)" if trial else "")
    encoded = title.encode("utf-8") + b"\0"
    edits = []
    for key in ("TITLE", "TITLE_00"):
        if key not in entries:
            continue
        field = entries[key]
        if field["format"] != 0x204 or len(encoded) > field["capacity"]:
            raise ValueError("English title exceeds string capacity: " + key)
        for offset, after in ((field["index"] + 4, struct.pack("<I", len(encoded))),
                              (field["position"], encoded.ljust(field["capacity"], b"\0"))):
            before = data[offset:offset + len(after)]
            if before != after:
                edits.append(dict(offset=offset, before=before.hex(), after=after.hex(), key=key))
    patched = apply_edits(data, edits)
    checked = parse_sfo(patched)
    for key, field in entries.items():
        other = checked[key]
        for attr in ("index", "format", "capacity", "position"):
            if field[attr] != other[attr]:
                raise ValueError("SFO layout changed")
        if key not in ("TITLE", "TITLE_00") and field != other:
            raise ValueError("Unrelated SFO field changed: " + key)
    if apply_edits(patched, edits, reverse=True) != data:
        raise ValueError("SFO inverse patch verification failed")
    return patched, dict(before_sha256=digest(data), after_sha256=digest(patched),
                         size=len(data), english_title=title, explicit_trial=trial,
                         changed_keys=[k for k in ("TITLE", "TITLE_00") if any(e["key"] == k for e in edits)],
                         edits=edits)


def output_path(value):
    path = Path(value).resolve()
    if path != OUTPUT and OUTPUT not in path.parents:
        raise ValueError("Output must be inside work/output/metadata")
    return path


def write_new(output, files):
    """Refuse an existing destination, including empty directories."""
    if output.exists():
        raise ValueError("Refusing to overwrite existing output: " + str(output))
    output.mkdir(parents=True, exist_ok=False)
    for relative, data in files.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "work/source/NPJB00162")
    parser.add_argument("--output", default=str(OUTPUT))
    parser.add_argument("--write", action="store_true", help="Write verified copies to a new output directory")
    parser.add_argument("--restore", type=Path, help="Reverse a generated manifest; still dry-run unless --write")
    args = parser.parse_args(argv)
    try:
        output = output_path(args.output)
        files = {}
        if args.restore:
            manifest_path = args.restore.resolve()
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("format") != "sfo-title-patch-v1" or set(manifest["files"]) != set(TARGETS):
                raise ValueError("Invalid title patch manifest")
            for relative, record in manifest["files"].items():
                data = (manifest_path.parent / relative).read_bytes()
                if digest(data) != record["after_sha256"]:
                    raise ValueError("Patched SFO hash mismatch: " + relative)
                restored = apply_edits(data, record["edits"], reverse=True)
                parse_sfo(restored)
                if digest(restored) != record["before_sha256"]:
                    raise ValueError("Restored SFO hash mismatch: " + relative)
                files[relative] = restored
            report = dict(action="restore", files=list(files), exact_original_hashes_verified=True)
        else:
            records = {}
            for relative in TARGETS:
                source = args.source / relative
                files[relative], records[relative] = translate_sfo(source.read_bytes())
                if source.resolve() == (output / relative).resolve():
                    raise ValueError("Source/output collision")
            manifest = dict(format="sfo-title-patch-v1", files=records,
                            note="Only title strings and current lengths changed; inverse edits restore original bytes.")
            files["manifest.en.json"] = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
            report = dict(action="translate", files={k: {a: v for a, v in r.items() if a != "edits"} for k, r in records.items()})
        if args.write:
            write_new(output, files)
        report.update(written=args.write, output=str(output))
        print(json.dumps(report, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, struct.error) as error:
        parser.exit(2, "Error: " + str(error) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
