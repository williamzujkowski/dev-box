# Multi-architecture Dockerfile for dev-box
FROM --platform=$TARGETPLATFORM ubuntu:24.04

ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG TARGETARCH

LABEL org.opencontainers.image.source="https://github.com/williamzujkowski/dev-box"
LABEL org.opencontainers.image.description="Dev-box development environment"
LABEL org.opencontainers.image.licenses="MIT"

# Install base dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
WORKDIR /opt/dev-box
COPY . .

# Install Python dependencies
RUN python3 -m pip install --no-cache-dir -r requirements.txt || true

# Install Node dependencies
RUN npm install || true

# Display architecture info
RUN echo "Built for $TARGETPLATFORM on $BUILDPLATFORM" > /opt/dev-box/arch-info.txt

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python3 --version || exit 1

CMD ["/bin/bash"]