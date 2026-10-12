# SPDX-License-Identifier: MIT

import subprocess
import sys
import threading
import time
import traceback
from contextlib import contextmanager

if __name__ != "__main__":
    from oeqa.core.decorator.depends import OETestDepends
    from oeqa.runtime.case import OERuntimeTestCase


FRIDA_PYTHON = "/opt/frida-python/bin/python"
FRIDA_ADDRESS = "127.0.0.1:27042"

AGENT = """
const INJECT_FAULT = __INJECT_FAULT__;

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
        const original = retval.toInt32();

        if (INJECT_FAULT)
            retval.replace(-1);

        send({
            kind: "call",
            a: this.a,
            b: this.b,
            original: original,
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

AGENT_IO = """
const openAddress = Module.getGlobalExportByName("open");
const closeAddress = Module.getGlobalExportByName("close");
const close = new NativeFunction(closeAddress, "int", ["int"]);

let injected = false;

Interceptor.attach(openAddress, {
    onEnter(args) {
        this.inject = !injected &&
            args[0].readUtf8String() === "/etc/passwd";
    },

    onLeave(retval) {
        if (!this.inject)
            return;

        injected = true;

        const original = retval.toInt32();

        // The real open() already succeeded. Close its descriptor
        // before reporting a synthetic failure to the application.
        if (original >= 0)
            close(original);

        retval.replace(-1);
        this.errno = 13;  // EACCES on Linux

        send({
            kind: "io-fault",
            original: original,
            result: retval.toInt32(),
            errno: this.errno
        });
    }
});

send({ kind: "ready" });
"""


def run_client(pid: int, inject_fault: bool = False) -> None:
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
            expected = -1 if inject_fault else 18

            if (
                payload.get("a") != 7
                or payload.get("b") != 11
                or payload.get("original") != 18
                or payload.get("result") != expected
            ):
                errors.append(f"Unexpected call: {payload}")

            intercepted.set()

    try:
        agent = AGENT.replace(
            "__INJECT_FAULT__",
            "true" if inject_fault else "false",
        )
        script = session.create_script(agent)
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

        if inject_fault:
            print(
                "PASS: replaced frida_smoke_add(7, 11) return value 18 -> -1",
                flush=True,
            )
        else:
            print(
                "PASS: intercepted frida_smoke_add(7, 11) = 18",
                flush=True,
            )

    finally:
        try:
            session.detach()
        except frida.InvalidOperationError:
            if not inject_fault:
                raise

    if not inject_fault:
        print("PASS: detached", flush=True)


def run_io_client(pid: int) -> None:
    import frida

    device = frida.get_device_manager().add_remote_device(FRIDA_ADDRESS)
    processes = device.enumerate_processes()

    if not any(process.pid == pid for process in processes):
        raise RuntimeError(f"Target PID {pid} not found")

    session = device.attach(pid)
    ready = threading.Event()
    injected = threading.Event()
    errors: list[str] = []

    def on_message(message, _data):
        if message["type"] == "error":
            errors.append(message.get("stack", str(message)))
            ready.set()
            injected.set()
            return

        if message["type"] != "send":
            return

        payload = message["payload"]

        if payload.get("kind") == "ready":
            ready.set()

        elif payload.get("kind") == "io-fault":
            if (
                payload.get("original", -1) < 0
                or payload.get("result") != -1
                or payload.get("errno") != 13
            ):
                errors.append(f"Unexpected I/O result: {payload}")

            injected.set()

    script = session.create_script(AGENT_IO)
    script.on("message", on_message)

    try:
        script.load()

        if not ready.wait(10):
            raise TimeoutError("I/O agent initialization timed out")

        if errors:
            raise RuntimeError("; ".join(errors))

        if not injected.wait(10):
            raise TimeoutError("No matching open() call intercepted")

        if errors:
            raise RuntimeError("; ".join(errors))

        print("PASS: intercepted open('/etc/passwd')", flush=True)
        print("PASS: replaced successful open() with -1/EACCES", flush=True)

    finally:
        try:
            session.detach()
        except frida.InvalidOperationError:
            # The process may have exited after receiving EACCES.
            pass


if __name__ != "__main__":

    class FridaCoreTest(OERuntimeTestCase):
        def setUp(self):
            super().setUp()

            status, output = self.target.run(
                "pidof frida-server",
                timeout=10,
            )

            if status == 0 and output.strip():
                return

            status, output = self.target.run(
                "frida-server -D -l 0.0.0.0:27042",
                timeout=30,
            )

            self.assertEqual(
                status,
                0,
                f"Failed to start frida-server:\n{output}",
            )

        def _read_target_file(self, path):
            status, output = self.target.run(
                f"cat {path} 2>/dev/null",
                timeout=10,
            )
            return output.strip() if status == 0 else None

        def _wait_for_integer(self, path):
            for _ in range(50):
                value = self._read_target_file(path)

                if value is not None and value.isdigit():
                    return int(value)

                time.sleep(0.1)

            self.fail(f"Timed out waiting for integer in {path}")

        @contextmanager
        def _target_process(self, name, args=""):
            prefix = f"/tmp/frida-smoke-{name}"
            pid_file = f"{prefix}.pid"
            exit_file = f"{prefix}.exit"
            log_file = f"{prefix}.log"

            self.target.run(f"rm -f {pid_file} {exit_file}")

            # The shell waits for its child and records the exit code.
            # This is needed when Frida deliberately terminates the target.
            command = (
                "( "
                f"frida-smoke {args} </dev/null >{log_file} 2>&1 & "
                "child=$!; "
                f'echo "$child" >{pid_file}; '
                'wait "$child"; '
                f'echo "$?" >{exit_file}; '
                ") </dev/null >/dev/null 2>&1 &"
            )

            pid = None

            try:
                status, output = self.target.run(command, timeout=15)

                self.assertEqual(
                    status,
                    0,
                    f"Failed to start frida-smoke:\n{output}",
                )

                pid = self._wait_for_integer(pid_file)
                yield pid, exit_file

            finally:
                if pid is not None:
                    self.target.run(f"kill {pid} 2>/dev/null || true")

                self.target.run(f"rm -f {pid_file} {exit_file}")

        def _run_client(self, pid, mode=None):
            command = [FRIDA_PYTHON, __file__, str(pid)]

            if mode is not None:
                command.append(mode)

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

            if result.stdout:
                self.logger.info(result.stdout)

            if result.stderr:
                self.logger.info(result.stderr)

            self.assertEqual(
                result.returncode,
                0,
                f"Frida client failed:\n{result.stdout}\n{result.stderr}",
            )

        @OETestDepends(["ssh.SSHTest.test_ssh"])
        def test_remote_interception(self):
            with self._target_process("observe") as (pid, _):
                self._run_client(pid)

                status, output = self.target.run(f"kill -0 {pid}")

                self.assertEqual(
                    status,
                    0,
                    f"Target did not survive detachment:\n{output}",
                )

                self.logger.info("PASS: target survived detachment")

        @OETestDepends(["ssh.SSHTest.test_ssh"])
        def test_return_value_override(self):
            with self._target_process("fault") as (pid, exit_file):
                self._run_client(pid, "inject")

                exit_status = self._wait_for_integer(exit_file)

                self.assertEqual(
                    exit_status,
                    1,
                    (
                        "Expected target to exit with status 1 "
                        f"after fault injection, got {exit_status}"
                    ),
                )

                self.logger.info(
                    "PASS: target exited with status 1 after injected return value"
                )

        @OETestDepends(["ssh.SSHTest.test_ssh"])
        def test_open_eacces_injection(self):
            with self._target_process("io", "io") as (pid, exit_file):
                self._run_client(pid, "io")

                exit_status = self._wait_for_integer(exit_file)

                self.assertEqual(
                    exit_status,
                    42,
                    f"Expected EACCES handling (exit 42), got {exit_status}",
                )

                self.logger.info("PASS: application handled injected EACCES (exit 42)")


if __name__ == "__main__":
    try:
        if len(sys.argv) < 2 or len(sys.argv) > 3:
            raise ValueError("Usage: frida_core.py PID [inject|io]")

        pid = int(sys.argv[1])
        mode = sys.argv[2] if len(sys.argv) == 3 else "observe"

        if mode == "io":
            run_io_client(pid)
        elif mode in ("observe", "inject"):
            run_client(pid, inject_fault=(mode == "inject"))
        else:
            raise ValueError(f"Unknown mode: {mode}")

    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}", file=sys.stderr, flush=True)
        traceback.print_exc()
        sys.exit(1)
