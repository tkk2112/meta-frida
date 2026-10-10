# SPDX-License-Identifier: MIT

import subprocess
import sys
import threading
import time

if __name__ != "__main__":
    from oeqa.core.decorator.depends import OETestDepends
    from oeqa.runtime.case import OERuntimeTestCase


FRIDA_PYTHON = "/opt/frida-python/bin/python"
FRIDA_ADDRESS = "127.0.0.1:27042"

AGENT = """
if (Process.arch !== "arm64")
    throw new Error("Unexpected architecture: " + Process.arch);

const modules = Process.enumerateModules();

if (modules.length === 0)
    throw new Error("No modules found");

const address = Module.getGlobalExportByName("frida_smoke_add");

if (address === null)
    throw new Error("frida_smoke_add not found");

Interceptor.attach(address, {
    onEnter(args) {
        this.a = args[0].toInt32();
        this.b = args[1].toInt32();
    },
    onLeave(retval) {
        send({
            kind: "call",
            a: this.a,
            b: this.b,
            result: retval.toInt32()
        });
    }
});

send({
    kind: "ready",
    arch: Process.arch,
    modules: modules.length
});
"""


def run_client(pid: int) -> None:
    import frida

    deadline = time.monotonic() + 20
    device = None

    while time.monotonic() < deadline:
        try:
            device = frida.get_device_manager().add_remote_device(FRIDA_ADDRESS)
            break
        except frida.TransportError:
            time.sleep(0.5)

    if device is None:
        raise RuntimeError("Unable to connect to frida-server")

    processes = device.enumerate_processes()

    if not processes:
        raise RuntimeError("Frida returned no processes")

    print(
        f"PASS: connected and enumerated {len(processes)} processes",
        flush=True,
    )

    matches = [process for process in processes if process.pid == pid]

    if len(matches) != 1:
        raise RuntimeError(f"Target PID {pid} not found")

    print(f"PASS: found target PID {pid}", flush=True)

    session = device.attach(pid)
    ready = threading.Event()
    intercepted = threading.Event()
    errors: list[str] = []

    def on_message(message, _data):
        if message["type"] == "error":
            errors.append(message.get("stack", str(message)))
            ready.set()
            intercepted.set()
            return

        if message["type"] != "send":
            return

        payload = message["payload"]

        if payload.get("kind") == "ready":
            if payload["arch"] != "arm64":
                errors.append(f"Unexpected architecture: {payload['arch']}")
            elif payload["modules"] < 1:
                errors.append("No modules enumerated")

            ready.set()

        elif payload.get("kind") == "call":
            if (
                payload.get("a") != 7
                or payload.get("b") != 11
                or payload.get("result") != 18
            ):
                errors.append(f"Unexpected call: {payload}")

            intercepted.set()

    try:
        script = session.create_script(AGENT)
        script.on("message", on_message)
        script.load()

        if not ready.wait(10):
            raise TimeoutError("Agent initialization timed out")

        if errors:
            raise RuntimeError("; ".join(errors))

        print("PASS: attached to ARM64 process", flush=True)
        print("PASS: enumerated modules and resolved export", flush=True)

        if not intercepted.wait(10):
            raise TimeoutError("No intercepted function call")

        if errors:
            raise RuntimeError("; ".join(errors))

        print(
            "PASS: intercepted frida_smoke_add(7, 11) = 18",
            flush=True,
        )

    finally:
        session.detach()

    print("PASS: detached", flush=True)


if __name__ != "__main__":

    class FridaCoreTest(OERuntimeTestCase):
        @OETestDepends(["ssh.SSHTest.test_ssh"])
        def test_remote_interception(self):
            status, output = self.target.run(
                "frida-server -D -l 0.0.0.0:27042",
                timeout=30,
            )

            self.assertEqual(
                status,
                0,
                f"Failed to start frida-server:\n{output}",
            )

            status, output = self.target.run(
                "frida-smoke </dev/null >/tmp/frida-smoke.log 2>&1 & echo $!",
                timeout=15,
            )

            self.assertEqual(
                status,
                0,
                f"Failed to start smoke target:\n{output}",
            )

            pid = int(output.strip().splitlines()[-1])

            try:
                result = subprocess.run(
                    [FRIDA_PYTHON, __file__, str(pid)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )

                self.logger.info(result.stdout)

                if result.stderr:
                    self.logger.info(result.stderr)

                self.assertEqual(
                    result.returncode,
                    0,
                    (
                        "Frida Core smoke test failed:\n"
                        f"{result.stdout}\n{result.stderr}"
                    ),
                )

                status, output = self.target.run(f"kill -0 {pid}")

                self.assertEqual(
                    status,
                    0,
                    f"Target did not survive detachment:\n{output}",
                )

                self.logger.info("PASS: target survived detachment")

            finally:
                self.target.run(f"kill {pid} 2>/dev/null || true")


if __name__ == "__main__":
    try:
        run_client(int(sys.argv[1]))
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
