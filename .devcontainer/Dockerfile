# syntax=docker/dockerfile:1
ARG UV_VERSION=0.12.22
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM debian:bookworm-slim

ARG USERNAME=dev
ARG USER_UID=1000
ARG USER_GID=1000

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        git-lfs \
        gnupg \
        less \
        openssh-client \
        procps \
        fluidsynth \
        libfluidsynth3 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p -m 755 /etc/apt/keyrings \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${USER_GID}" "${USERNAME}" \
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" --create-home --shell /bin/bash "${USERNAME}"

COPY --from=uv /uv /uvx /usr/local/bin/

ENV UV_PYTHON_INSTALL_DIR=/home/${USERNAME}/.local/share/uv/python \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH=/home/${USERNAME}/.local/bin:/workspaces/pypiano/.venv/bin:${PATH}

USER ${USERNAME}
WORKDIR /workspaces/pypiano

RUN uv python install 3.11 3.12 3.13 3.14

RUN git lfs install --skip-repo

ENV CLAUDE_CONFIG_DIR=/home/${USERNAME}/.claude
RUN curl -fsSL https://claude.ai/install.sh | bash \
    && claude --version

RUN mkdir -p /home/${USERNAME}/.cache/uv /home/${USERNAME}/.claude /home/${USERNAME}/.config/gh
