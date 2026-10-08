from __future__ import annotations

import argparse
import importlib
import re
import sys
import tempfile
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from git import Git, Repo
from git.exc import GitCommandError

ROOT = Path(__file__).resolve().parents[2]

LOCK_FILE = ROOT / "conf/include/frida-lock.inc"

FRIDA_REPO_URL = "https://github.com/frida/frida.git"

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

        return format_lock(
            version=version,
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
        help="check whether a newer stable Frida release is available",
    )

    parser.add_argument(
        "--update",
        action="store_true",
        help="update the lock to the latest stable Frida release",
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
        )
    )

    if mode_count != 1:
        parser.error("specify exactly one of VERSION, --check, or --update")

    if args.check:
        check_for_update(verbose=args.verbose)
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
