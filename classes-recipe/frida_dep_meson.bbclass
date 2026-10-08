# SPDX-License-Identifier: MIT

inherit frida_source meson pkgconfig

FRIDA_DEPS_PREFIX ??= "${libdir}/frida"
EXTRA_OEMESON:append = " \
    --prefix=${FRIDA_DEPS_PREFIX} \
    --bindir=bin \
    --libdir=lib \
    --includedir=include \
    --datadir=share \
    -Ddefault_library=static \
"
FRIDA_MESON_SKIP_ARGS ??= ""
FRIDA_MESON_OPTIMIZED ??= "${@'0' if d.getVar('DEBUG_BUILD') == '1' else '1'}"

def frida_meson_condition(expression, d):
    import ast

    target_os = (d.getVar("TARGET_OS") or "").split("-")[0]
    if target_os != "linux":
        bb.fatal("%s: frida_dep_meson currently supports hosted Linux only" % d.getVar("PN"))

    arch = d.getVar("TARGET_ARCH")
    machine = {
        "os": target_os,
        "arch": {"aarch64": "arm64", "i586": "x86", "i686": "x86"}.get(arch, arch),
        "config": d.getVar("TCLIBC") or "glibc",
        "is_apple": False,
        "is_freestanding": False,
        "config_is_optimized": d.getVar("FRIDA_MESON_OPTIMIZED") == "1",
    }

    def evaluate(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id == "machine":
                return machine
            raise ValueError("unknown name %s" % node.id)
        if isinstance(node, ast.Attribute):
            receiver = evaluate(node.value)
            if isinstance(receiver, dict) and node.attr in receiver:
                return receiver[node.attr]
            raise ValueError("unknown attribute %s" % node.attr)
        if isinstance(node, ast.Set):
            return {evaluate(part) for part in node.elts}
        if isinstance(node, ast.Tuple):
            return tuple(evaluate(part) for part in node.elts)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not evaluate(node.operand)
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(evaluate(part) for part in node.values)
            if isinstance(node.op, ast.Or):
                return any(evaluate(part) for part in node.values)
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = evaluate(node.left), evaluate(node.comparators[0])
            op = node.ops[0]
            if isinstance(op, (ast.Eq, ast.Is)):
                return left == right
            if isinstance(op, (ast.NotEq, ast.IsNot)):
                return left != right
            if isinstance(op, ast.In):
                return left in right
            if isinstance(op, ast.NotIn):
                return left not in right
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "startswith" and not node.keywords and len(node.args) == 1:
                receiver = evaluate(node.func.value)
                prefix = evaluate(node.args[0])
                if isinstance(receiver, str) and isinstance(prefix, str):
                    return receiver.startswith(prefix)
        raise ValueError("unsupported expression node %s" % type(node).__name__)

    try:
        return bool(evaluate(ast.parse(expression, mode="eval").body))
    except (SyntaxError, TypeError, ValueError) as exc:
        bb.fatal("%s: unsupported releng condition %r: %s" % (d.getVar("PN"), expression, exc))


def frida_meson_arguments(d):
    kind = d.getVar("FRIDA_SOURCE_KIND")
    identifier = d.getVar("FRIDA_SOURCE_NAME")

    if kind != "DEP":
        bb.fatal("%s: frida_dep_meson is for releng dependencies only" % d.getVar("PN"))

    count = d.getVarFlag("FRIDA_DEP_MESON_COUNT", identifier)
    if count is None:
        bb.fatal("%s: no Meson option metadata for %s; regenerate frida_lock.inc" % (d.getVar("PN"), identifier))

    skip = set((d.getVar("FRIDA_MESON_SKIP_ARGS") or "").split())
    result = []
    for index in range(int(count)):
        key = "%s-%03d" % (identifier, index)
        argument = d.getVarFlag("FRIDA_DEP_MESON_ARG", key)
        condition = d.getVarFlag("FRIDA_DEP_MESON_WHEN", key)
        if argument is None:
            bb.fatal("%s: missing FRIDA_DEP_MESON_ARG[%s]" % (d.getVar("PN"), key))
        if argument in skip:
            continue
        if condition and not frida_meson_condition(condition, d):
            continue
        if any(c.isspace() for c in argument):
            bb.fatal("%s: Meson argument contains whitespace: %r" % (d.getVar("PN"), argument))
        result.append(argument)

    unknown = skip - {
        d.getVarFlag("FRIDA_DEP_MESON_ARG", "%s-%03d" % (identifier, i))
        for i in range(int(count))
    }
    if unknown:
        bb.fatal("%s: unknown FRIDA_MESON_SKIP_ARGS: %s" % (d.getVar("PN"), sorted(unknown)))
    return " ".join(result)


def frida_meson_validate_options(d):
    import shlex

    arguments = shlex.split(d.getVar("EXTRA_OEMESON") or "")
    seen = {}
    duplicates = {}

    for argument in arguments:
        if argument.startswith("-D") and "=" in argument:
            name, value = argument[2:].split("=", 1)
        elif argument.startswith("--") and "=" in argument:
            name, value = argument[2:].split("=", 1)
        else:
            continue

        if name in seen:
            duplicates.setdefault(name, [seen[name]]).append(value)
        else:
            seen[name] = value

    if duplicates:
        details = ", ".join(
            "%s (%s)" % (name, ", ".join(values))
            for name, values in sorted(duplicates.items())
        )
        bb.fatal("%s: duplicate Meson options: %s" % (d.getVar("PN"), details))


# nooelint: oelint.task.noanonpython Parse-time evaluation of upstream Meson metadata
python __anonymous() {
    options = frida_meson_arguments(d)
    if options:
        d.appendVar("EXTRA_OEMESON", " " + options)

    frida_meson_validate_options(d)
}
