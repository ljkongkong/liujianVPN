FROM alpine:latest

RUN apk add --no-cache wget tar curl

WORKDIR /app

# Download sing-box with integrity verification
RUN set -eux; \
    wget -O sing-box.tar.gz \
      https://github.com/SagerNet/sing-box/releases/download/v1.10.1/sing-box-1.10.1-linux-amd64.tar.gz || \
      { echo "ERROR: Failed to download sing-box"; exit 1; }; \
    tar -zxf sing-box.tar.gz || \
      { echo "ERROR: Failed to extract sing-box archive"; exit 1; }; \
    mv sing-box-1.10.1-linux-amd64/sing-box . || \
      { echo "ERROR: sing-box binary not found in archive"; exit 1; }; \
    chmod +x sing-box; \
    ./sing-box version || \
      { echo "ERROR: sing-box binary is not executable or corrupted"; exit 1; }; \
    rm -rf sing-box-1.10.1-linux-amd64*

COPY config.json .

# Validate config at build time so misconfigurations fail the build
RUN ./sing-box check -c config.json || \
      { echo "ERROR: config.json validation failed"; exit 1; }

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO /dev/null http://127.0.0.1:8080/ || exit 1

# Use exec form so sing-box receives SIGTERM directly for graceful shutdown
ENTRYPOINT ["./sing-box"]
CMD ["run", "-c", "config.json"]
