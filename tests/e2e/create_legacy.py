"""Package the upstream production METS and an unidentified-format variant."""

import hashlib
import os
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

LEGACY_UUID = "80f077d8-2a6f-49e2-9327-903c36d6d92d"
UNKNOWN_UUID = "11111111-1111-4111-8111-111111111111"
NS = {"m": "http://www.loc.gov/METS/", "p": "info:lc/xmlns/premis-v2"}


def package_aip(parent, name, uuid, xml):
    root = parent / f"{name}-{uuid}"
    (root / "data/objects").mkdir(parents=True)
    # These bytes match the production fixture's original file size and SHA-256.
    (root / "data/objects/abc.txt").write_bytes(b"abc\n")
    (root / f"data/METS.{uuid}.xml").write_bytes(xml)
    (root / "bagit.txt").write_text(
        "BagIt-Version: 0.97\nTag-File-Character-Encoding: UTF-8\n"
    )
    (root / "manifest-sha256.txt").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root)}\n"
            for path in sorted((root / "data").rglob("*"))
            if path.is_file()
        )
    )
    archive = parent / f"{root.name}.7z"
    subprocess.run(
        ["7z", "a", "-m0=lzma", str(archive), root.name], cwd=parent, check=True
    )
    os.chown(archive, 1000, 1000)


def main():
    parent = Path("/home/archivematica/transfers")
    xml = Path("/legacy.xml").read_bytes()
    package_aip(parent, "easy_1488911181", LEGACY_UUID, xml)

    # Derive the unidentified-file case from the same real METS, leaving the
    # checked-in fixture and the first package's metadata unchanged.
    mets = ET.fromstring(xml)
    mets.find("m:structMap[@TYPE='physical']/m:div", NS).set(
        "LABEL", f"unidentified-transfer-{UNKNOWN_UUID}"
    )
    characteristics = mets.find("m:amdSec/m:techMD/.//p:objectCharacteristics", NS)
    characteristics.remove(characteristics.find("p:format", NS))
    variant = ET.tostring(mets, encoding="UTF-8", xml_declaration=True)
    package_aip(parent, "unidentified-transfer", UNKNOWN_UUID, variant)


if __name__ == "__main__":
    main()
