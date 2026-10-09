# SPDX-License-Identifier: MIT

from oeqa.core.decorator.depends import OETestDepends
from oeqa.runtime.case import OERuntimeTestCase


class FridaGumTest(OERuntimeTestCase):
    @OETestDepends(["ssh.SSHTest.test_ssh"])
    def test_interceptor_replace_and_revert(self):
        status, output = self.target.run(
            "frida-gum-smoketest",
            timeout=60,
        )

        self.assertEqual(
            status,
            0,
            f"Frida Gum smoke test failed (exit {status}):\n{output}",
        )
        self.assertIn(
            "PASS: Gum initialized, replaced and restored target function",
            output,
        )
