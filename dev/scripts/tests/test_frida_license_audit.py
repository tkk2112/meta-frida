# SPDX-License-Identifier: MIT

import hashlib
import subprocess

from frida_license_audit import (
    audit_recipe,
    git_blob,
    license_checksum,
    source_uri,
)


def test_bitbake_git_uri():
    assert (
        source_uri("git://github.com/frida/glib.git;protocol=https;nobranch=1") == "https://github.com/frida/glib.git"
    )


def test_whole_license_checksum():
    contents = b"Copyright 2026\nMIT license\n"
    assert license_checksum(contents) == hashlib.md5(contents).hexdigest()


def test_selected_license_lines():
    contents = b"header\nlicense line 1\nlicense line 2\nfooter\n"
    expected = hashlib.md5(b"license line 1\nlicense line 2\n").hexdigest()

    assert license_checksum(contents, beginline=2, endline=3) == expected


def test_detects_changed_license(tmp_path):
    repo = tmp_path / "source"
    repo.mkdir()

    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True,
    )

    (repo / "LICENSE").write_text("Updated license text\n")
    subprocess.run(["git", "-C", str(repo), "add", "LICENSE"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-qm", "Initial"],
        check=True,
    )

    revision = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
    ).strip()

    recipe = tmp_path / "test.bb"
    recipe.write_text('LIC_FILES_CHKSUM = "file://LICENSE;md5=' + "a" * 32 + '"\n')

    issues = audit_recipe(recipe, repo, revision)

    assert len(issues) == 1
    assert "Checksum changed" in issues[0].message


def test_detects_missing_license(tmp_path):
    repo = tmp_path / "source"
    repo.mkdir()

    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True,
    )
    (repo / "README").write_text("Source\n")
    subprocess.run(["git", "-C", str(repo), "add", "README"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-qm", "Initial"],
        check=True,
    )

    revision = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
    ).strip()

    recipe = tmp_path / "test.bb"
    recipe.write_text('LIC_FILES_CHKSUM = "file://LICENCE;md5=' + "a" * 32 + '"\n')

    issues = audit_recipe(recipe, repo, revision)

    assert len(issues) == 1
    assert "missing" in issues[0].message.lower()


def test_git_blob_resolves_license_symlink(tmp_path):
    repository = tmp_path / "source"
    repository.mkdir()

    subprocess.run(["git", "init", "-q", str(repository)], check=True)

    licenses = repository / "LICENSES"
    licenses.mkdir()

    contents = b"Actual license contents\n"
    (licenses / "LGPL-2.1-or-later.txt").write_bytes(contents)
    (repository / "COPYING").symlink_to("LICENSES/LGPL-2.1-or-later.txt")

    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-q",
            "-m",
            "test",
        ],
        check=True,
    )

    revision = subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        text=True,
    ).strip()

    assert git_blob(repository, revision, "COPYING") == contents
