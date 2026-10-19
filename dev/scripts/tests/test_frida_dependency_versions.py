# SPDX-License-Identifier: MIT

import pytest
import update_frida as updater


@pytest.mark.parametrize(
    ("name", "project", "expected"),
    [
        ("glib", "project('glib', 'c', version : '2.90.0')", "2.90.0"),
        ("json-glib", "project('json-glib', 'c', version: '1.10.9')", "1.10.9"),
        ("libdwarf", "project('libdwarf', ['c', 'cpp'], version: '2.3.4')", "2.3.4"),
        ("libffi", "project('libffi', 'c', version : '3.8.0')", "3.8.0"),
        ("libgee", "project('libgee', 'vala', 'c', version: '0.20.8')", "0.20.8"),
        ("vala", "project('vala', 'c', 'vala', version: '0.58.0-frida')", "0.58.0-frida"),
    ],
)
def test_dependency_version(tmp_path, name, project, expected):
    source = tmp_path / name
    source.mkdir()
    (source / "meson.build").write_text(project + "\n", encoding="utf-8")

    assert updater.dependency_version(source) == expected


@pytest.mark.parametrize(
    "declaration",
    [
        "project('example', 'c')",
        "project('example', 'c', version: get_version())",
        "project('example', 'c', version: 'invalid')",
    ],
)
def test_rejects_unknown_version(tmp_path, declaration):
    (tmp_path / "meson.build").write_text(declaration + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Cannot determine"):
        updater.dependency_version(tmp_path)


def test_generated_lock_contains_dependency_versions():
    versions = {
        "glib": "2.90.0",
        "json-glib": "1.10.9",
        "libdwarf": "2.3.4",
        "libffi": "3.8.0",
        "libgee": "0.20.8",
        "vala": "0.58.0-frida",
    }

    contents = updater.format_lock(
        version="17.24.3",
        python_sha256="a" * 64,
        release_revision="b" * 40,
        releng_url="https://github.com/frida/releng.git",
        releng_revision="c" * 40,
        components={},
        packages={},
        dependency_versions=versions,
        meson_options={},
        gvdb_url="https://github.com/GNOME/gvdb.git",
        gvdb_revision="d" * 40,
    )

    assignments = updater.parse_lock_assignments(contents)

    assert assignments["FRIDA_VERSION"] == "17.24.3"

    for name, version in versions.items():
        assert assignments[f"FRIDA_DEP_VERSION[{name}]"] == version
