# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]

ASSIGNMENT = re.compile(
    r'^([A-Za-z_][A-Za-z_0-9-]*(?:\[[^]]+\])?)\s*=\s*"([^"]*)"$',
    re.MULTILINE,
)
LICENSE = re.compile(r"file://([^;\s]+)((?:;[^;\s]+)*)")
REVISION = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class LicenseIssue:
    recipe: Path
    source: str
    message: str


def assignments(contents: str) -> dict[str, str]:
    return dict(ASSIGNMENT.findall(contents))


def source_uri(uri: str) -> str:
    """Convert a BitBake Git URI to a Git HTTP(S) URL."""
    fields = uri.split(";")
    address = fields[0]

    if not address.startswith("git://"):
        raise ValueError(f"Unsupported source URI: {uri}")

    protocol = next(
        (field.removeprefix("protocol=") for field in fields[1:] if field.startswith("protocol=")),
        "git",
    )

    if protocol not in {"https", "http"}:
        raise ValueError(f"Unsupported Git protocol: {protocol}")

    return f"{protocol}://{address.removeprefix('git://')}"


def license_checksum(
    data: bytes,
    *,
    beginline: int | None = None,
    endline: int | None = None,
) -> str:
    lines = data.splitlines(keepends=True)

    if beginline is not None or endline is not None:
        start = 1 if beginline is None else beginline
        stop = len(lines) if endline is None else endline

        if start < 1 or stop < start or stop > len(lines):
            raise ValueError("Invalid license line range")

        data = b"".join(lines[start - 1 : stop])

    return hashlib.md5(data).hexdigest()


def git_source(
    url: str,
    revision: str,
    directory: Path,
) -> Path:
    if not REVISION.fullmatch(revision):
        raise ValueError(f"Invalid Git revision: {revision}")

    parsed = urlsplit(url)

    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError(f"Invalid repository URL: {url}")

    subprocess.run(
        ["git", "init", "-q", str(directory)],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(directory),
            "fetch",
            "-q",
            "--depth=1",
            url,
            revision,
        ],
        check=True,
    )

    actual = subprocess.check_output(
        [
            "git",
            "-C",
            str(directory),
            "rev-parse",
            "FETCH_HEAD",
        ],
        text=True,
    ).strip()

    if actual != revision:
        raise RuntimeError(f"Fetched {actual}, expected {revision} from {url}")

    return directory


def git_blob(
    repository: Path,
    revision: str,
    path: str,
) -> bytes | None:
    if path.startswith("/") or ".." in Path(path).parts:
        raise ValueError(f"Invalid license path: {path}")

    result = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "show",
            f"{revision}:{path}",
        ],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    return result.stdout


def audit_recipe(
    recipe: Path,
    repository: Path,
    revision: str,
) -> list[LicenseIssue]:
    contents = recipe.read_text(encoding="utf-8")
    values = assignments(contents)

    declaration = values.get("LIC_FILES_CHKSUM")

    if declaration is None:
        return [
            LicenseIssue(
                recipe,
                "",
                "Missing or unsupported LIC_FILES_CHKSUM",
            )
        ]

    issues: list[LicenseIssue] = []

    for match in LICENSE.finditer(declaration):
        filename = match.group(1)
        parameters = dict(part.split("=", 1) for part in match.group(2).split(";") if "=" in part)

        expected = parameters.get("md5")

        if expected is None:
            issues.append(
                LicenseIssue(
                    recipe,
                    filename,
                    "Missing md5 parameter",
                )
            )
            continue

        blob = git_blob(repository, revision, filename)

        if blob is None:
            issues.append(
                LicenseIssue(
                    recipe,
                    filename,
                    "License file missing at pinned revision",
                )
            )
            continue

        try:
            actual = license_checksum(
                blob,
                beginline=(int(parameters["beginline"]) if "beginline" in parameters else None),
                endline=(int(parameters["endline"]) if "endline" in parameters else None),
            )
        except ValueError as exc:
            issues.append(LicenseIssue(recipe, filename, str(exc)))
            continue

        if actual != expected:
            issues.append(
                LicenseIssue(
                    recipe,
                    filename,
                    f"Checksum changed: {expected} -> {actual}",
                )
            )

    return issues


def managed_dependencies(
    root: Path,
) -> tuple[list[tuple[Path, str, str, str]], list[LicenseIssue]]:
    lock = assignments((root / "conf/include/frida_lock.inc").read_text(encoding="utf-8"))

    issues: list[LicenseIssue] = []
    managed: list[tuple[Path, str, str, str]] = []

    recipes = sorted((root / "recipes-frida").glob("frida-*/*.bb"))
    recipes += sorted((root / "recipes-devtools").glob("frida-*/*.bb"))

    for recipe in recipes:
        identifier = recipe.parent.name.removeprefix("frida-")
        uri = lock.get(f"FRIDA_DEP_URI[{identifier}]")
        revision = lock.get(f"FRIDA_DEP_SRCREV[{identifier}]")

        if uri is None and revision is None:
            continue

        if not uri or not revision:
            issues.append(
                LicenseIssue(
                    recipe,
                    "",
                    f"Incomplete source pin for {identifier}",
                )
            )
            continue

        managed.append((recipe, identifier, uri, revision))

    return managed, issues


def print_audit_progress(
    root: Path,
    recipe: Path,
    found: list[LicenseIssue],
    completed: int,
    total: int,
    elapsed: float,
) -> None:
    relative = recipe.relative_to(root)
    status = "REVIEW" if found else "OK"

    print(
        f"  [{completed:02d}/{total:02d}] {status:<7} {relative} ({elapsed:.1f}s)",
        flush=True,
    )

    for issue in found:
        print(
            f"      {issue.source}: {issue.message}",
            flush=True,
        )


def check_one(
    recipe: Path,
    identifier: str,
    uri: str,
    revision: str,
    cache: Path,
) -> tuple[list[LicenseIssue], float]:
    start = time.monotonic()
    repository = cache / identifier

    try:
        git_source(
            source_uri(uri),
            revision,
            repository,
        )
        found = audit_recipe(
            recipe,
            repository,
            revision,
        )
    except (
        OSError,
        RuntimeError,
        ValueError,
        subprocess.CalledProcessError,
    ) as exc:
        found = [
            LicenseIssue(
                recipe,
                "",
                f"Audit failed: {exc}",
            )
        ]

    return found, time.monotonic() - start


def audit_locked_dependencies(
    root: Path = ROOT,
    *,
    verbose: bool = False,
) -> list[LicenseIssue]:
    managed, issues = managed_dependencies(root)

    total = len(managed)
    workers = min(total, os.cpu_count() or 1) if total else 1
    started = time.monotonic()

    if verbose:
        print(
            f"\nFrida license audit: {total} dependencies, {workers} parallel workers",
            flush=True,
        )

    with tempfile.TemporaryDirectory(prefix="frida-license-") as temporary:
        cache = Path(temporary)

        with ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="frida-license",
        ) as executor:
            futures = {}

            for recipe, identifier, uri, revision in managed:
                future = executor.submit(
                    check_one,
                    recipe,
                    identifier,
                    uri,
                    revision,
                    cache,
                )
                futures[future] = recipe

                if verbose:
                    print(
                        f"  QUEUED  {recipe.relative_to(root)} ({revision[:12]})",
                        flush=True,
                    )

            for completed, future in enumerate(
                as_completed(futures),
                start=1,
            ):
                recipe = futures[future]
                found, elapsed = future.result()
                issues.extend(found)

                if verbose:
                    print_audit_progress(root, recipe, found, completed, total, elapsed)

    duration = time.monotonic() - started

    issues.sort(
        key=lambda issue: (
            str(issue.recipe),
            issue.source,
            issue.message,
        )
    )

    if verbose:
        print(
            f"\nLicense audit finished: {total} dependencies, {len(issues)} issue(s), {duration:.1f}s",
            flush=True,
        )

    return issues


def check_licenses(root: Path = ROOT, *, verbose: bool = False) -> None:
    issues = audit_locked_dependencies(root, verbose=verbose)

    if not issues:
        print("PASS: Frida dependency license checksums", flush=True)
        return

    print("\nFrida license audit: REVIEW REQUIRED\n", flush=True)

    for issue in issues:
        print(f"  {issue.recipe.relative_to(root)}", flush=True)
        print(f"    {issue.source}: {issue.message}", flush=True)

    raise RuntimeError(f"{len(issues)} license metadata issue(s); review required")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify license checksums against pinned Frida dependency sources",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="show per-dependency progress",
    )
    args = parser.parse_args()

    try:
        check_licenses(verbose=args.verbose)
    except RuntimeError as exc:
        raise SystemExit(f"error: {exc}") from None
