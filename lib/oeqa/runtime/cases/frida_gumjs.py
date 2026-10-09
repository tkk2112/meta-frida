# SPDX-License-Identifier: MIT

from oeqa.core.decorator.depends import OETestDepends
from oeqa.runtime.case import OERuntimeTestCase


class FridaGumJSTest(OERuntimeTestCase):
    @OETestDepends(["ssh.SSHTest.test_ssh"])
    def test_quickjs_execution(self):
        status, output = self.target.run(
            "frida-gumjs-smoketest",
            timeout=60,
        )

        self.assertEqual(
            status,
            0,
            f"Frida GumJS smoke test failed (exit {status}):\n{output}",
        )
        self.assertIn(
            "PASS: GumJS executed QuickJS script and delivered message",
            output,
        )
