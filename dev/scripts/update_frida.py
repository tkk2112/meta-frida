from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from git import Git, Repo
from git.exc import GitCommandError
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[2]

LOCK_FILE = ROOT / "conf/include/frida_lock.inc"

FRIDA_REPO_URL = "https://github.com/frida/frida.git"

FRIDA_PYPI = "https://pypi.org/pypi/frida"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

LOCK_VERSION_RE = re.compile(
    r'^\s*FRIDA_VERSION\s*=\s*"([^"]+)"\s*$',
    re.MULTILINE,
)

LOCK_ASSIGNMENT_RE = re.compile(
    r'^(FRIDA_[A-Z0-9_]+(?:\[[^]]+\])?)\s*=\s*"([^"]*)"$',
    re.MULTILINE,
)

GIT_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")

TOOLS_RECIPES = ROOT / "recipes-frida/frida-tools"
TOOLS_PYPI = "https://pypi.org/pypi/frida-tools"

TOOLS_PACKAGES = {
    "colorama": "nativesdk-python3-colorama",
    "frida": "nativesdk-frida-python",
    "prompt-toolkit": "nativesdk-python3-prompt-toolkit",
    "pygments": "nativesdk-python3-pygments",
    "websockets": "nativesdk-python3-websockets",
}

TOOLS_CHECKSUM_RE = re.compile(r'(?m)^SRC_URI\[sha256sum\]\s*=\s*"([0-9a-f]{64})"$')

TOOLS_RDEPENDS_RE = re.compile(
    r'RDEPENDS:\$\{PN\}:class-nativesdk\s*=\s*"([^"]*)"',
    re.DOTALL,
)


def parse_version(version: str) -> tuple[int, int, int]:
    match = VERSION_RE.fullmatch(version)

    if match is None:
        msg = f"invalid Frida version {version!r}; expected X.Y.Z"
        raise RuntimeError(msg)

    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def read_lock_version() -> str:
    if not LOCK_FILE.exists():
        msg = f"{LOCK_FILE.relative_to(ROOT)} does not exist"
        raise RuntimeError(msg)

    contents = LOCK_FILE.read_text(encoding="utf-8")
    match = LOCK_VERSION_RE.search(contents)

    if match is None:
        msg = f"could not find FRIDA_VERSION in {LOCK_FILE.relative_to(ROOT)}"
        raise RuntimeError(msg)

    version = match.group(1)
    parse_version(version)

    return version


def frida_python_metadata(version: str) -> dict[str, Any]:
    parse_version(version)

    url = f"{FRIDA_PYPI}/{version}/json"
    request = Request(url, headers={"User-Agent": "meta-frida-update/1"})

    try:
        with urlopen(request, timeout=20) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"failed to fetch Frida Python metadata from {url}") from exc

    if not isinstance(data, dict):
        raise TypeError(f"unexpected PyPI response from {url}")

    if data.get("info", {}).get("version") != version:
        raise RuntimeError(f"PyPI response does not match Frida {version}")

    return data


def frida_python_sdist_checksum(
    data: Mapping[str, Any],
    version: str,
) -> str:
    expected_filename = f"frida-{version}.tar.gz"

    sdists = [item for item in data["urls"] if item.get("packagetype") == "sdist"]

    if len(sdists) != 1:
        raise RuntimeError(f"expected one Frida Python {version} source archive, found {len(sdists)}")

    sdist = sdists[0]

    if sdist.get("filename") != expected_filename:
        raise RuntimeError(f"unexpected Frida Python source archive: {sdist.get('filename')!r}")

    checksum = sdist.get("digests", {}).get("sha256")

    if not isinstance(checksum, str) or not SHA256_RE.fullmatch(checksum):
        raise RuntimeError(f"invalid Frida Python {version} source checksum")

    return checksum


def check_frida_python_checksum() -> None:
    version = read_lock_version()
    contents = LOCK_FILE.read_text(encoding="utf-8")
    assignments = parse_lock_assignments(contents)

    actual = assignments.get("FRIDA_PYTHON_SHA256")

    if actual is None or not SHA256_RE.fullmatch(actual):
        raise RuntimeError(f"FRIDA_PYTHON_SHA256 missing or invalid in {LOCK_FILE.relative_to(ROOT)}")

    metadata = frida_python_metadata(version)
    expected = frida_python_sdist_checksum(metadata, version)

    if actual != expected:
        raise RuntimeError(f"Frida Python {version} checksum mismatch: locked {actual}, PyPI {expected}")

    print(f"OK: Frida Python {version} sdist SHA-256: {actual}")


def frida_release_versions(*, verbose: bool) -> set[str]:
    if verbose:
        print(f"Querying release tags from {FRIDA_REPO_URL}")

    try:
        output = Git().ls_remote(
            "--tags",
            "--refs",
            FRIDA_REPO_URL,
        )
    except GitCommandError as exc:
        msg = f"failed to query Frida release tags from {FRIDA_REPO_URL}"
        raise RuntimeError(msg) from exc

    if not isinstance(output, str):
        msg = f"git ls-remote returned unexpected type {type(output).__name__}"
        raise TypeError(msg)

    versions: set[str] = set()
    prefix = "refs/tags/"

    for line in output.splitlines():
        fields = line.split(maxsplit=1)

        if len(fields) != 2:
            continue

        _, reference = fields

        if not reference.startswith(prefix):
            continue

        tag = reference.removeprefix(prefix)

        if VERSION_RE.fullmatch(tag):
            versions.add(tag)

    if not versions:
        msg = f"no stable Frida release tags found in {FRIDA_REPO_URL}"
        raise RuntimeError(msg)

    if verbose:
        print(f"Found {len(versions)} stable release tags")

    return versions


def latest_frida_version(*, verbose: bool) -> str:
    versions = frida_release_versions(verbose=verbose)
    latest = max(versions, key=parse_version)

    if verbose:
        print(f"Latest stable release: {latest}")

    return latest


def validate_release_version(
    version: str,
    *,
    verbose: bool,
) -> None:
    parse_version(version)

    versions = frida_release_versions(verbose=verbose)

    if version not in versions:
        msg = f"Frida release {version} does not exist"
        raise RuntimeError(msg)


def validate_revision(identifier: str, revision: str) -> None:
    if not GIT_REVISION_RE.fullmatch(revision):
        msg = f"{identifier}: expected a full Git SHA, got {revision!r}"
        raise RuntimeError(msg)


def clone_tag(
    url: str,
    tag: str,
    path: Path,
    *,
    verbose: bool,
) -> Repo:
    if verbose:
        print(f"  cloning tag {tag} from {url}")

    try:
        return Repo.clone_from(
            url,
            path,
            branch=tag,
            depth=1,
            single_branch=True,
        )
    except GitCommandError as exc:
        msg = f"failed to clone {url} at tag {tag}"
        raise RuntimeError(msg) from exc


def clone_revision(
    url: str,
    revision: str,
    path: Path,
    *,
    verbose: bool,
) -> Repo:
    validate_revision(url, revision)

    if verbose:
        print(f"  fetching {revision} from {url}")

    repo = Repo.init(path)
    origin = repo.create_remote("origin", url)

    fetches = origin.fetch(
        revision,
        depth=1,
    )

    if not fetches:
        msg = f"{url}: fetching {revision} produced no result"
        raise RuntimeError(msg)

    fetched_revision = fetches[0].commit.hexsha

    repo.git.checkout(
        "--detach",
        fetched_revision,
    )

    actual = repo.head.commit.hexsha

    if actual != revision:
        msg = f"{url}: requested {revision}, checked out {actual}"
        raise RuntimeError(msg)

    return repo


def submodule_info(
    repo: Repo,
    path: str,
) -> tuple[str, str]:
    for module in repo.submodules:
        if module.path != path:
            continue

        url = module.url
        revision = module.hexsha

        validate_revision(path, revision)

        if "://" not in url:
            msg = f"{path}: relative submodule URL {url!r} is not supported; expected an absolute URL"
            raise RuntimeError(msg)

        return url, revision

    msg = f"{path!r} is not a Git submodule in {repo.working_tree_dir}"
    raise RuntimeError(msg)


def component_submodules(
    repo: Repo,
) -> dict[str, tuple[str, str]]:
    components: dict[str, tuple[str, str]] = {}

    for module in repo.submodules:
        path = module.path

        if not path.startswith("subprojects/"):
            continue

        identifier = Path(path).name
        revision = module.hexsha

        validate_revision(identifier, revision)

        if identifier in components:
            msg = f"duplicate Frida component identifier: {identifier}"
            raise RuntimeError(msg)

        if "://" not in module.url:
            msg = f"{path}: relative submodule URL {module.url!r} is not supported; expected an absolute URL"
            raise RuntimeError(msg)

        components[identifier] = (
            module.url,
            revision,
        )

    return components


def bitbake_git_uri(url: str) -> str:
    parsed = urlparse(url)

    if parsed.scheme == "https":
        return f"git://{parsed.netloc}{parsed.path};protocol=https;nobranch=1"

    if parsed.scheme == "http":
        return f"git://{parsed.netloc}{parsed.path};protocol=http;nobranch=1"

    if parsed.scheme == "git":
        return f"{url};nobranch=1"

    msg = f"unsupported Git URL for BitBake: {url}"
    raise RuntimeError(msg)


def load_releng_packages(
    releng_repository: Path,
) -> Mapping[str, Any]:
    import_root = releng_repository.parent
    sys.path.insert(0, str(import_root))

    for name in list(sys.modules):
        if name == "releng" or name.startswith("releng."):
            del sys.modules[name]

    try:
        deps = importlib.import_module("releng.deps")

        module_file = deps.__file__

        if module_file is None:
            msg = "releng.deps has no __file__"
            raise RuntimeError(msg)

        module_path = Path(module_file).resolve()
        expected_root = releng_repository.resolve()

        if not module_path.is_relative_to(expected_root):
            msg = f"imported unexpected releng.deps from {module_path}"
            raise RuntimeError(msg)

        load_dependency_parameters = getattr(
            deps,
            "load_dependency_parameters",
            None,
        )

        if load_dependency_parameters is None:
            msg = "releng.deps has no load_dependency_parameters()"
            raise RuntimeError(msg)

        parameters = load_dependency_parameters()
        packages = parameters.packages

        if not isinstance(packages, Mapping):
            msg = "releng.deps returned an unexpected packages value"
            raise TypeError(msg)

        return packages

    finally:
        sys.path.remove(str(import_root))

        for name in list(sys.modules):
            if name == "releng" or name.startswith("releng."):
                del sys.modules[name]


def package_source(
    packages: Mapping[str, Any],
    identifier: str,
) -> tuple[str, str]:
    try:
        package = packages[identifier]
    except KeyError as exc:
        msg = f"releng dependency manifest has no {identifier!r} package"
        raise RuntimeError(msg) from exc

    url = str(package.url)
    revision = str(package.version)

    validate_revision(identifier, revision)

    return url, revision


def read_releng_meson_options(
    releng_repository: Path,
    packages: Mapping[str, Any],
) -> dict[str, list[tuple[str, str]]]:
    # Read the TOML from the same pinned releng checkout used to resolve SHAs.
    # Keep `when` predicates verbatim so BitBake can select for its target.
    manifest_path = releng_repository / "deps.toml"
    with manifest_path.open("rb") as stream:
        manifest = tomllib.load(stream)

    result: dict[str, list[tuple[str, str]]] = {}
    for identifier, package in packages.items():
        entry = manifest.get(identifier)
        if entry is None:
            msg = f"{identifier}: missing entry in pinned releng/deps.toml"
            raise RuntimeError(msg)

        if not isinstance(entry, dict):
            msg = f"{identifier}: expected a table in pinned releng/deps.toml"
            raise TypeError(msg)

        if entry.get("url") != str(package.url) or entry.get("version") != str(package.version):
            msg = f"{identifier}: releng.deps and deps.toml disagree about source pins"
            raise RuntimeError(msg)

        options = entry.get("options", [])
        if not isinstance(options, list):
            msg = f"{identifier}: expected a list of Meson options"
            raise TypeError(msg)

        parsed: list[tuple[str, str]] = []
        for option in options:
            if isinstance(option, str):
                value, when = option, ""
            elif isinstance(option, dict) and set(option) == {"value", "when"}:
                value, when = option["value"], option["when"]
                if not isinstance(value, str) or not isinstance(when, str):
                    msg = f"{identifier}: invalid conditional Meson option {option!r}"
                    raise TypeError(msg)
            else:
                msg = f"{identifier}: unsupported Meson option {option!r}"
                raise RuntimeError(msg)

            # All options are persisted, including those not applicable to Linux.
            # No shell parsing, eval, or host-side conditional selection happens here.
            parsed.append((value, " ".join(when.split())))

        result[identifier] = parsed

    return result


def bitbake_literal(value: str) -> str:
    if any(character in value for character in ('"', "\\", "\n", "\r")):
        msg = f"cannot serialize Meson option safely in BitBake: {value!r}"
        raise RuntimeError(msg)
    return f'"{value}"'


def format_lock(
    *,
    version: str,
    python_sha256: str,
    release_revision: str,
    releng_url: str,
    releng_revision: str,
    components: Mapping[str, tuple[str, str]],
    packages: Mapping[str, Any],
    meson_options: Mapping[str, list[tuple[str, str]]],
    gvdb_url: str,
    gvdb_revision: str,
) -> str:
    lines = [
        "# SPDX-License-Identifier: MIT",
        "#",
        "# Generated by dev/scripts/update-frida.",
        "# Do not edit manually.",
        "",
        f'FRIDA_VERSION = "{version}"',
        f'FRIDA_PYTHON_SHA256 = "{python_sha256}"',
        "",
        f'FRIDA_RELEASE_URI = "{bitbake_git_uri(FRIDA_REPO_URL)}"',
        f'FRIDA_RELEASE_SRCREV = "{release_revision}"',
        "",
        f'FRIDA_RELENG_URI = "{bitbake_git_uri(releng_url)}"',
        f'FRIDA_RELENG_SRCREV = "{releng_revision}"',
        "",
    ]

    for identifier in sorted(components):
        url, revision = components[identifier]

        lines.extend(
            [
                f'FRIDA_COMPONENT_URI[{identifier}] = "{bitbake_git_uri(url)}"',
                f'FRIDA_COMPONENT_SRCREV[{identifier}] = "{revision}"',
            ]
        )

    lines.append("")

    for identifier in sorted(packages):
        package = packages[identifier]

        url = str(package.url)
        revision = str(package.version)

        validate_revision(identifier, revision)

        lines.extend(
            [
                f'FRIDA_DEP_URI[{identifier}] = "{bitbake_git_uri(url)}"',
                f'FRIDA_DEP_SRCREV[{identifier}] = "{revision}"',
            ]
        )

    # Stable indexed entries retain the exact upstream ordering and predicates.
    # The recipe class resolves predicates using Yocto target metadata.
    lines.append("")
    for identifier in sorted(meson_options):
        options = meson_options[identifier]
        lines.append(f'FRIDA_DEP_MESON_COUNT[{identifier}] = "{len(options)}"')
        for index, (value, when) in enumerate(options):
            key = f"{identifier}-{index:03d}"
            lines.append(f"FRIDA_DEP_MESON_ARG[{key}] = {bitbake_literal(value)}")
            if when:
                lines.append(f"FRIDA_DEP_MESON_WHEN[{key}] = {bitbake_literal(when)}")

    lines.extend(
        [
            "",
            f'FRIDA_GLIB_GVDB_URI = "{bitbake_git_uri(gvdb_url)}"',
            f'FRIDA_GLIB_GVDB_SRCREV = "{gvdb_revision}"',
            "",
        ]
    )

    return "\n".join(lines)


def parse_lock_assignments(
    contents: str,
) -> dict[str, str]:
    return {match.group(1): match.group(2) for match in LOCK_ASSIGNMENT_RE.finditer(contents)}


def print_changes(
    old: str,
    new: str,
) -> None:
    if not old:
        print("\nLock file")
        print("  creating initial lock")
        return

    old_values = parse_lock_assignments(old)
    new_values = parse_lock_assignments(new)

    changes: list[tuple[str, str | None, str | None]] = []

    for key in sorted(set(old_values) | set(new_values)):
        old_value = old_values.get(key)
        new_value = new_values.get(key)

        if old_value != new_value:
            changes.append(
                (
                    key,
                    old_value,
                    new_value,
                )
            )

    print("\nChanges")

    if not changes:
        print("  none")
        return

    for key, old_value, new_value in changes:
        print(f"  {key}")

        if old_value is not None:
            print(f"    - {old_value}")

        if new_value is not None:
            print(f"    + {new_value}")


def generate_lock(
    version: str,
    *,
    verbose: bool,
) -> str:
    parse_version(version)

    print(f"Frida version: {version}")

    with tempfile.TemporaryDirectory(prefix="meta-frida-update-") as temporary_directory:
        workdir = Path(temporary_directory)

        print("\nResolving release")
        print(f"  repository: {FRIDA_REPO_URL}")
        print(f"  tag:        {version}")

        frida = clone_tag(
            FRIDA_REPO_URL,
            version,
            workdir / "frida",
            verbose=verbose,
        )

        release_revision = frida.head.commit.hexsha

        validate_revision(
            "frida",
            release_revision,
        )

        print(f"  commit:     {release_revision}")

        releng_url, releng_revision = submodule_info(
            frida,
            "releng",
        )

        components = component_submodules(frida)

        print("\nRelease snapshot")
        print(f"  releng               {releng_revision}")

        for identifier in sorted(components):
            _, revision = components[identifier]
            print(f"  {identifier:<20} {revision}")

        releng = clone_revision(
            releng_url,
            releng_revision,
            workdir / "releng",
            verbose=verbose,
        )

        print("\nLoading dependency manifest")
        print("  implementation: releng.deps.load_dependency_parameters()")
        print(f"  releng:         {releng_revision}")

        releng_worktree = releng.working_tree_dir

        if releng_worktree is None:
            msg = "releng repository has no working tree"
            raise RuntimeError(msg)

        packages = load_releng_packages(
            Path(releng_worktree),
        )

        print(f"  packages:       {len(packages)}")
        meson_options = read_releng_meson_options(
            Path(releng_worktree),
            packages,
        )

        if verbose:
            print("\nDependency pins")

            for identifier in sorted(packages):
                package = packages[identifier]
                print(f"  {identifier:<20} {package.version}  {package.url}")

        glib_url, glib_revision = package_source(
            packages,
            "glib",
        )

        glib = clone_revision(
            glib_url,
            glib_revision,
            workdir / "glib",
            verbose=verbose,
        )

        gvdb_url, gvdb_revision = submodule_info(
            glib,
            "subprojects/gvdb",
        )

        print("\nNested dependencies")
        print(f"  glib/gvdb            {gvdb_revision}")

        print("\nResolving Frida Python source")
        python_metadata = frida_python_metadata(version)
        python_sha256 = frida_python_sdist_checksum(
            python_metadata,
            version,
        )
        print(f"  sdist SHA-256: {python_sha256}")

        return format_lock(
            version=version,
            python_sha256=python_sha256,
            release_revision=release_revision,
            releng_url=releng_url,
            releng_revision=releng_revision,
            components=components,
            packages=packages,
            meson_options=meson_options,
            gvdb_url=gvdb_url,
            gvdb_revision=gvdb_revision,
        )


def write_lock(
    version: str,
    *,
    verbose: bool,
) -> None:
    validate_release_version(
        version,
        verbose=verbose,
    )

    generated = generate_lock(
        version,
        verbose=verbose,
    )

    current = LOCK_FILE.read_text(encoding="utf-8") if LOCK_FILE.exists() else ""

    print_changes(
        current,
        generated,
    )

    LOCK_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    LOCK_FILE.write_text(
        generated,
        encoding="utf-8",
    )

    print(f"\nWrote {LOCK_FILE.relative_to(ROOT)}")


def check_for_update(*, verbose: bool) -> None:
    current = read_lock_version()

    check_frida_python_checksum()

    latest = latest_frida_version(verbose=verbose)

    current_key = parse_version(current)
    latest_key = parse_version(latest)

    print(f"Current Frida version: {current}")
    print(f"Latest Frida version:  {latest}")

    if current_key == latest_key:
        print("\nFrida is up to date.")
        return

    if current_key < latest_key:
        print(f"\nUpdate available: {current} -> {latest}")
        return

    print(f"\nLocked version {current} is newer than latest upstream release {latest}.")


def tools_recipe() -> tuple[str, Path]:
    matches = sorted(TOOLS_RECIPES.glob("frida-tools_*.bb"))

    if len(matches) != 1:
        msg = f"expected one versioned frida-tools recipe, found {len(matches)}"
        raise RuntimeError(msg)

    path = matches[0]
    version = path.stem.removeprefix("frida-tools_")
    parse_version(version)

    return version, path


def tools_metadata(version: str | None = None) -> dict[str, Any]:
    url = f"{TOOLS_PYPI}/{version}/json" if version else f"{TOOLS_PYPI}/json"
    request = Request(url, headers={"User-Agent": "meta-frida-update/1"})

    try:
        with urlopen(request, timeout=20) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        msg = f"failed to fetch PyPI metadata from {url}"
        raise RuntimeError(msg) from exc

    if not isinstance(data, dict):
        raise TypeError(f"unexpected PyPI response from {url}")

    return data


def tools_requirements(data: Mapping[str, Any]) -> dict[str, Requirement]:
    result: dict[str, Requirement] = {}

    for item in data["info"]["requires_dist"] or []:
        requirement = Requirement(item)

        if requirement.marker is not None:
            raise RuntimeError(f"review conditional frida-tools dependency: {item}")

        name = canonicalize_name(requirement.name)

        if name not in TOOLS_PACKAGES:
            raise RuntimeError(f"review new frida-tools dependency: {item}")

        if name in result:
            raise RuntimeError(f"duplicate frida-tools dependency: {name}")

        result[name] = requirement

    if "frida" not in result:
        raise RuntimeError("frida-tools release lacks a Frida requirement")

    return result


def tools_sdist_checksum(data: Mapping[str, Any]) -> str:
    sdists = [item for item in data["urls"] if item["packagetype"] == "sdist"]

    if len(sdists) != 1:
        raise RuntimeError(f"expected one frida-tools source archive, found {len(sdists)}")

    return str(sdists[0]["digests"]["sha256"])


def validate_tools_recipe(
    contents: str,
    data: Mapping[str, Any],
) -> None:
    expected = tools_sdist_checksum(data)
    actual = TOOLS_CHECKSUM_RE.search(contents)

    if actual is None or actual.group(1) != expected:
        raise RuntimeError(f"frida-tools source checksum differs from PyPI: {expected}")

    deps = TOOLS_RDEPENDS_RE.search(contents)

    if deps is None:
        raise RuntimeError("frida-tools recipe lacks SDK-host RDEPENDS")

    declared = " ".join(deps.group(1).replace("\\", " ").split())

    for name, requirement in tools_requirements(data).items():
        package = TOOLS_PACKAGES[name]

        for constraint in requirement.specifier:
            if constraint.operator not in {"<", "<=", "=", "==", ">", ">="}:
                raise RuntimeError(f"unsupported BitBake constraint: {constraint}")

            operator = "=" if constraint.operator == "==" else constraint.operator

            expected_dep = f"{package} ({operator} {constraint.version})"

            if expected_dep not in declared:
                raise RuntimeError(f"frida-tools recipe lacks RDEPENDS: {expected_dep}")


def selected_version(recipe: str) -> tuple[str, str]:
    # BitBake must use the kas container's Python, not the updater venv.
    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)

    venv_bin = (Path(sys.prefix) / "bin").resolve()

    environment["PATH"] = os.pathsep.join(
        entry for entry in environment["PATH"].split(os.pathsep) if Path(entry).resolve() != venv_bin
    )

    # BitBake uses /usr/bin/env python3. Keep the system interpreter
    # available even when the development venv was first in PATH.
    system_python = Path("/usr/bin/python3")

    if not system_python.is_file():
        raise RuntimeError("the kas container does not provide /usr/bin/python3")

    environment["PATH"] = f"{system_python.parent}{os.pathsep}{environment['PATH']}"

    values = []

    for variable in ("PV", "FILE"):
        command = [
            "bitbake-getvar",
            "--value",
            "-r",
            recipe,
            variable,
        ]

        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )
        except subprocess.CalledProcessError as exc:
            details = (exc.stderr or exc.stdout or "").strip()
            raise RuntimeError(
                f"bitbake-getvar failed for {recipe} {variable} (exit {exc.returncode}):\n{details}"
            ) from exc
        except OSError as exc:
            raise RuntimeError(f"failed to execute bitbake-getvar: {exc}") from exc

        value = result.stdout.strip()

        if not value:
            raise RuntimeError(f"bitbake-getvar returned empty {variable} for {recipe}")

        values.append(value)

    return values[0], values[1]


def check_tools(*, bitbake: bool) -> None:
    current, path = tools_recipe()
    data = tools_metadata(current)
    latest = str(tools_metadata()["info"]["version"])

    validate_tools_recipe(path.read_text(encoding="utf-8"), data)

    if bitbake:
        selected, origin = selected_version("nativesdk-frida-tools")

        if selected != current:
            raise RuntimeError(f"BitBake selected frida-tools {selected}, but meta-frida pins {current}: {origin}")

        print(f"OK: selected frida-tools {selected} ({origin})")

    print(f"Current Frida Tools: {current}")
    print(f"Latest Frida Tools:  {latest}")

    if parse_version(current) < parse_version(latest):
        print(f"Update available: {current} -> {latest}")

    for name, requirement in tools_requirements(data).items():
        package = TOOLS_PACKAGES[name]

        if bitbake:
            version, origin = selected_version(package)
        elif name == "frida":
            version = read_lock_version()
            origin = str(LOCK_FILE.relative_to(ROOT))
        else:
            print(f"UNCHECKED: {package} {requirement.specifier} (use --bitbake)")
            continue

        if version not in requirement.specifier:
            raise RuntimeError(f"{package} {version} does not satisfy {requirement.specifier} ({origin})")

        print(f"OK: {package} {version} satisfies {requirement.specifier} ({origin})")


def update_tools(version: str | None) -> None:
    data = tools_metadata(version)
    target_version = str(data["info"]["version"])
    parse_version(target_version)

    current_version, path = tools_recipe()
    original = path.read_text(encoding="utf-8")

    checksum_match = TOOLS_CHECKSUM_RE.search(original)

    if checksum_match is None:
        raise RuntimeError(f"missing source checksum in {path}")

    checksum = tools_sdist_checksum(data)

    updated = original[: checksum_match.start(1)] + checksum + original[checksum_match.end(1) :]

    validate_tools_recipe(updated, data)

    frida_req = tools_requirements(data)["frida"]
    frida_version = read_lock_version()

    if frida_version not in frida_req.specifier:
        raise RuntimeError(
            f"frida-tools {target_version} requires frida {frida_req.specifier}, but Frida is locked to {frida_version}"
        )

    dest = path.with_name(f"frida-tools_{target_version}.bb")

    if dest != path and dest.exists():
        raise RuntimeError(f"destination recipe already exists: {dest}")

    dest.write_text(updated, encoding="utf-8")

    if dest != path:
        path.unlink()

    print(f"Frida Tools: {current_version} -> {target_version}")
    print(f"Updated: {dest.relative_to(ROOT)}")
    print("Review runtime dependencies and validate the SDK with --check-tools --bitbake")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update meta-frida source pins from Frida releases",
    )

    parser.add_argument(
        "version",
        nargs="?",
        help="generate the lock for a specific Frida X.Y.Z release",
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="check Frida Core and Tools releases",
    )

    parser.add_argument(
        "--update",
        action="store_true",
        help="update the Core lock to the latest stable Frida release",
    )

    parser.add_argument(
        "--check-tools",
        action="store_true",
        help="check Frida Tools release and SDK dependency requirements",
    )

    parser.add_argument(
        "--update-tools",
        nargs="?",
        const="latest",
        metavar="VERSION",
        help="update Frida Tools independently (default: latest)",
    )

    parser.add_argument(
        "--bitbake",
        action="store_true",
        help="check versions selected by BitBake (use inside a kas shell)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="show release discovery, source fetches, and dependency pins",
    )

    args = parser.parse_args()

    mode_count = sum(
        (
            args.version is not None,
            args.check,
            args.update,
            args.check_tools,
            args.update_tools is not None,
        )
    )

    if mode_count != 1:
        parser.error("select VERSION, --check, --update, --check-tools, or --update-tools")

    if args.bitbake and not (args.check or args.check_tools):
        parser.error("--bitbake requires --check or --check-tools")

    if args.check:
        check_for_update(verbose=args.verbose)
        return

    if args.check_tools:
        check_tools(bitbake=args.bitbake)
        return

    if args.update_tools is not None:
        update_tools(None if args.update_tools == "latest" else args.update_tools)
        return

    if args.update:
        latest = latest_frida_version(verbose=args.verbose)

        print(f"Latest Frida version: {latest}\n")

        write_lock(
            latest,
            verbose=args.verbose,
        )
        return

    if args.version is None:
        raise RuntimeError("missing Frida version")

    write_lock(
        args.version,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        raise SystemExit(f"error: {exc}") from exc
