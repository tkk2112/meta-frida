# SPDX-License-Identifier: MIT

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import update_frida as updater


class TestFridaToolsUpdate(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)

        self.root = Path(temporary.name)
        self.recipes = self.root / "recipes-frida/frida-tools"
        self.recipes.mkdir(parents=True)

        self.lock = self.root / "conf/include/frida_lock.inc"
        self.lock.parent.mkdir(parents=True)
        self.lock.write_text('FRIDA_VERSION = "17.23.0"\n')

        self.recipe = self.recipes / "frida-tools_14.11.0.bb"

        self.data = {
            "info": {
                "version": "14.11.0",
                "requires_dist": [
                    "colorama<1.0.0,>=0.2.7",
                    "frida<18.0.0,>=17.10.0",
                    "prompt-toolkit<4.0.0,>=2.0.0",
                    "pygments<3.0.0,>=2.0.2",
                    "websockets<14.0.0,>=13.0.0",
                ],
            },
            "urls": [
                {
                    "packagetype": "sdist",
                    "digests": {"sha256": "a" * 64},
                }
            ],
        }

        text = f'SRC_URI[sha256sum] = "{"a" * 64}"\n'
        text += 'RDEPENDS:${PN}:class-nativesdk = "\\\n'

        for name, requirement in updater.tools_requirements(self.data).items():
            package = updater.TOOLS_PACKAGES[name]

            for specifier in requirement.specifier:
                text += f"    {package} ({specifier.operator} {specifier.version}) \\\n"

        text += '"\n'
        self.recipe.write_text(text)

        for name, value in (
            ("ROOT", self.root),
            ("LOCK_FILE", self.lock),
            ("TOOLS_RECIPES", self.recipes),
        ):
            context = patch.object(updater, name, value)
            context.start()
            self.addCleanup(context.stop)

        metadata = patch.object(
            updater,
            "tools_metadata",
            side_effect=lambda _version=None: self.data,
        )
        metadata.start()
        self.addCleanup(metadata.stop)

    def test_current_release(self):
        updater.check_tools(bitbake=False)

    def test_missing_runtime_constraint(self):
        contents = self.recipe.read_text()
        contents = contents.replace(
            "nativesdk-python3-websockets (< 14.0.0)",
            "",
        )
        self.recipe.write_text(contents)

        with pytest.raises(RuntimeError, match="nativesdk-python3-websockets"):
            updater.check_tools(bitbake=False)

    def test_incompatible_selected_websockets(self):
        versions = {
            "nativesdk-frida-tools": "14.11.0",
            "nativesdk-frida-python": "17.23.0",
            "nativesdk-python3-colorama": "0.4.6",
            "nativesdk-python3-prompt-toolkit": "3.0.52",
            "nativesdk-python3-pygments": "2.19.2",
            "nativesdk-python3-websockets": "16.0",
        }

        def selected(name):
            return versions[name], f"/recipes/{name}.bb"

        with (
            patch.object(updater, "selected_version", side_effect=selected),
            pytest.raises(RuntimeError, match="does not satisfy"),
        ):
            updater.check_tools(bitbake=True)

    def test_update_rejects_incompatible_core(self):
        incompatible = {
            "info": {
                "version": "14.12.0",
                "requires_dist": ["frida>=18.0.0"],
            },
            "urls": [
                {
                    "packagetype": "sdist",
                    "digests": {"sha256": "b" * 64},
                }
            ],
        }

        with patch.object(updater, "tools_metadata", return_value=incompatible), pytest.raises(RuntimeError):
            updater.update_tools("14.12.0")

        assert self.recipe.exists()

    def test_bitbake_uses_container_python(self):
        import subprocess

        results = [
            subprocess.CompletedProcess([], 0, "14.11.0\n", ""),
            subprocess.CompletedProcess([], 0, "/repo/frida-tools_14.11.0.bb\n", ""),
        ]

        venv = Path(sys.prefix) / "bin"

        with (
            patch.dict(
                updater.os.environ,
                {
                    "PATH": f"{venv}:/usr/bin",
                    "VIRTUAL_ENV": str(venv.parent),
                },
            ),
            patch.object(
                updater.subprocess,
                "run",
                side_effect=results,
            ) as run,
        ):
            version, origin = updater.selected_version("nativesdk-frida-tools")

        assert version == "14.11.0"
        assert origin == "/repo/frida-tools_14.11.0.bb"

        for call in run.call_args_list:
            environment = call.kwargs["env"]
            assert str(venv) not in environment["PATH"].split(":")
            assert "VIRTUAL_ENV" not in environment


if __name__ == "__main__":
    unittest.main()
