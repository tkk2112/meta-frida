ARG KAS_VERSION=5.5
FROM ghcr.io/siemens/kas/kas:${KAS_VERSION}

COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /uvx /bin/

ARG FRIDA_VERSION

USER root

ENV UV_PYTHON_DOWNLOADS=never

RUN test -n "$FRIDA_VERSION" \
    && uv venv --python /usr/bin/python3 /opt/frida-python \
    && uv pip install --python /opt/frida-python/bin/python \
        "frida==$FRIDA_VERSION" \
    && /opt/frida-python/bin/python -c \
        "import frida; print('Frida Python bindings:', frida.__version__)"
