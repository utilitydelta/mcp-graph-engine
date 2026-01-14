FROM ubuntu:24.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    nodejs \
    npm \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code globally
RUN npm install -g @anthropic-ai/claude-code

# Create a non-root user with same UID as host user (for file permissions)
ARG HOST_UID=1000
RUN if getent passwd $HOST_UID > /dev/null; then \
        userdel -r $(getent passwd $HOST_UID | cut -d: -f1) 2>/dev/null || true; \
    fi && \
    useradd -m -s /bin/bash -u $HOST_UID developer
USER developer
WORKDIR /home/developer/workspace

# Set up git config (Claude Code needs this)
RUN git config --global user.email "docker@localhost" && \
    git config --global user.name "Docker User"

# Entry point
ENTRYPOINT ["claude", "--dangerously-skip-permissions"]
