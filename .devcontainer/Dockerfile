# syntax=docker/dockerfile:1
ARG UV_VERSION=0.12.22
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM debian:bookworm-slim

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

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
        make \
        openssh-client \
        procps \
        unzip \
        fluidsynth \
        libfluidsynth3 \
    && rm -rf /var/lib/apt/lists/*

RUN install -d -m 755 /etc/apt/keyrings \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# Standalone CLI tools from GitHub releases, pinned by version and sha256.
# To bump: update the version and both checksums (from the release's assets).
ARG PREK_VERSION=0.5.4
ARG PREK_SHA256_AMD64=6147dfe64051af590f4bfc2c073a0780fb5e2cc37d9eab8e47fe9fe26c7dfb80
ARG PREK_SHA256_ARM64=5478e436210b5226b8db3dccdd1a2e9094b1c63d81155d96bfa8b83f0398885c
ARG HADOLINT_VERSION=2.15.1
ARG HADOLINT_SHA256_AMD64=c7187db94eeeeca956519a6af171adc31453941a1e777961f6e680f697c8c507
ARG HADOLINT_SHA256_ARM64=f6198ef8090f404dbb771abfee086eb8c48ac177f30da7fd3510aca35b344b5d
ARG DPRINT_VERSION=0.58.0
ARG DPRINT_SHA256_AMD64=3047dcabe684fe32868d1959f7fad4ccbc2996a393d639bbb6634668fa08dc49
ARG DPRINT_SHA256_ARM64=f161161399b5ef62b3b68570ea1df24d16687adfbb88c125c8c4355e5780c407
ARG SF2_CUTTER_VERSION=0.1.0
ARG SF2_CUTTER_SHA256_AMD64=9d67b219dd3839229a27232df48148b6de7dfd3ef791921e06d69e627974db06
ARG SF2_CUTTER_SHA256_ARM64=e2ebb69b795a1284e7793d9004dcb51d3e2968ca93ba11b97d58135f8f879b94

RUN arch="$(dpkg --print-architecture)" \
    && case "${arch}" in \
        amd64) triple=x86_64; hadolint_arch=x86_64; \
               prek_sha="${PREK_SHA256_AMD64}"; hadolint_sha="${HADOLINT_SHA256_AMD64}"; dprint_sha="${DPRINT_SHA256_AMD64}"; \
               sf2_cutter_sha="${SF2_CUTTER_SHA256_AMD64}" ;; \
        arm64) triple=aarch64; hadolint_arch=arm64; \
               prek_sha="${PREK_SHA256_ARM64}"; hadolint_sha="${HADOLINT_SHA256_ARM64}"; dprint_sha="${DPRINT_SHA256_ARM64}"; \
               sf2_cutter_sha="${SF2_CUTTER_SHA256_ARM64}" ;; \
        *) echo "unsupported architecture: ${arch}" >&2; exit 1 ;; \
    esac \
    && tmp="$(mktemp -d)" \
    && curl -fsSL -o "${tmp}/prek.tar.gz" \
        "https://github.com/j178/prek/releases/download/v${PREK_VERSION}/prek-${triple}-unknown-linux-gnu.tar.gz" \
    && echo "${prek_sha}  ${tmp}/prek.tar.gz" | sha256sum -c - \
    && tar -xzf "${tmp}/prek.tar.gz" -C "${tmp}" --strip-components=1 \
    && install -m 755 "${tmp}/prek" /usr/local/bin/prek \
    && curl -fsSL -o "${tmp}/hadolint" \
        "https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-linux-${hadolint_arch}" \
    && echo "${hadolint_sha}  ${tmp}/hadolint" | sha256sum -c - \
    && install -m 755 "${tmp}/hadolint" /usr/local/bin/hadolint \
    && curl -fsSL -o "${tmp}/dprint.zip" \
        "https://github.com/dprint/dprint/releases/download/${DPRINT_VERSION}/dprint-${triple}-unknown-linux-gnu.zip" \
    && echo "${dprint_sha}  ${tmp}/dprint.zip" | sha256sum -c - \
    && unzip -q "${tmp}/dprint.zip" dprint -d "${tmp}" \
    && install -m 755 "${tmp}/dprint" /usr/local/bin/dprint \
    && curl -fsSL -o "${tmp}/sf2-cutter.tar.gz" \
        "https://github.com/FelixGSE/sf2-cutter/releases/download/v${SF2_CUTTER_VERSION}/sf2-cutter-${triple}-unknown-linux-musl.tar.gz" \
    && echo "${sf2_cutter_sha}  ${tmp}/sf2-cutter.tar.gz" | sha256sum -c - \
    && tar -xzf "${tmp}/sf2-cutter.tar.gz" -C "${tmp}" sf2-cutter \
    && install -m 755 "${tmp}/sf2-cutter" /usr/local/bin/sf2-cutter \
    && rm -rf "${tmp}" \
    && prek --version && hadolint --version && dprint --version && sf2-cutter --version

# Fail the build if a base image change ever pulls in sudo.
RUN if command -v sudo >/dev/null; then echo "sudo must not be installed" >&2; exit 1; fi \
    && groupadd --gid "${USER_GID}" "${USERNAME}" \
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" --create-home --shell /bin/bash "${USERNAME}"

COPY --from=uv /uv /uvx /usr/local/bin/

# The venv lives outside the bind-mounted repo, so it doesn't clash with a .venv a uv on the host creates there
ENV UV_PYTHON_INSTALL_DIR=/home/${USERNAME}/.local/share/uv/python \
    UV_PROJECT_ENVIRONMENT=/home/${USERNAME}/.venv \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH=/home/${USERNAME}/.local/bin:/home/${USERNAME}/.venv/bin:${PATH}

USER ${USERNAME}
WORKDIR /workspaces/pypiano

RUN uv python install 3.11 3.12 3.13 3.14 \
    && git lfs install --skip-repo

ENV CLAUDE_CONFIG_DIR=/home/${USERNAME}/.claude
RUN curl -fsSL https://claude.ai/install.sh | bash \
    && claude --version

RUN mkdir -p /home/${USERNAME}/.cache/uv /home/${USERNAME}/.claude /home/${USERNAME}/.config/gh
