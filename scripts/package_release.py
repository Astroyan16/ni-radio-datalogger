"""Assemble la distribution portable, ses notices et ses empreintes SHA-256."""
from __future__ import annotations

import hashlib
import csv
import io
from importlib.metadata import distributions
from pathlib import Path, PurePosixPath
import platform
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
NAME = "NI-Radio-Datalogger-0.1.0-windows-x64"


def main() -> None:
    executable = DIST / f"{NAME}.exe"
    if not executable.is_file():
        raise FileNotFoundError(executable)
    staging = ROOT / "build" / "release-package"
    staging.mkdir(parents=True, exist_ok=True)
    notices = staging / "THIRD_PARTY_NOTICES.txt"
    lines = [
        "NI Radio Datalogger 0.1.0 — composants de l'environnement de compilation",
        f"Python {sys.version.split()[0]} — {platform.platform()}",
        "Les notices de licence disponibles sont incluses dans licenses/.",
        "Le pilote système NI-DAQmx doit être installé séparément.",
        "",
    ]
    license_paths = []
    for dist in sorted(distributions(), key=lambda item: item.metadata['Name'].lower()):
        name = dist.metadata["Name"]
        license_name = dist.metadata.get("License-Expression") or dist.metadata.get("License") or "Voir les notices du paquet."
        lines.append(f"{name}=={dist.version}\n{license_name}\n")
        # Filtrer RECORD avant tout accès disque : les autres fichiers du paquet
        # peuvent être des espaces réservés OneDrive et sont inutiles aux notices.
        for row in csv.reader(io.StringIO(dist.read_text("RECORD") or "")):
            file = PurePosixPath(row[0])
            if not any(part.lower().startswith(("license", "copying", "copyright", "notice")) for part in file.parts):
                continue
            source = Path(dist.locate_file(file))
            if not source.is_file() or ".." in file.parts:
                continue
            relative = Path("licenses") / name / Path(str(file))
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            license_paths.append(relative)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        relative = Path("licenses/Python/LICENSE.txt")
        destination = staging / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(python_license, destination)
        license_paths.append(relative)
    notices.write_text("\n".join(lines), encoding="utf-8")
    archive = DIST / f"{NAME}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        bundle.write(executable, executable.name)
        for relative in ("README.md", "CHANGELOG.md", "docs/RELEASE-0.1.0.md", "requirements-build.lock.txt"):
            bundle.write(ROOT / relative, relative)
        bundle.write(notices, notices.name)
        for relative in license_paths:
            bundle.write(staging / relative, str(relative))
    shutil.copyfile(notices, DIST / notices.name)
    artifacts = [executable, archive, DIST / notices.name]
    checksums = []
    for path in artifacts:
        with path.open("rb") as source:
            checksums.append(f"{hashlib.file_digest(source, 'sha256').hexdigest()}  {path.name}\n")
    (DIST / "SHA256SUMS.txt").write_text("".join(checksums), encoding="ascii")
    for path in artifacts:
        print(f"{path.name}: {path.stat().st_size:,} octets")


if __name__ == "__main__":
    main()
