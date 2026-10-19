#!/usr/bin/env bash
# Builds this lab's Run:ai MCP image: NVIDIA's runai-mcp-server from source at the same ref as the lab's
# Run:ai control plane, plus one change (stateless.patch) so it serves MCP 2026-07-28 without sessions.
# Run by a person with Docker Hub push rights; it never runs in a lab.
#
# NVIDIA's Dockerfile copies a prebuilt bin/runai-mcp-server-<arch>; their Makefile builds it inside the
# monorepo (go.mod replaces point at ../control-plane and ../runai-clients). We build the same binary
# with the same flags in a golang container, then run their Dockerfile.
#
# Env: RUNAI_REF (default 59e288d7), IMAGE (default docker.io/iracic82/bnk-agents-runai-mcp:0.1.0),
#      WORK (clone dir), PUSH=1 to push after building, GO_IMAGE (default golang:1.27)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNAI_REF="${RUNAI_REF:-59e288d7}"
IMAGE="${IMAGE:-docker.io/iracic82/bnk-agents-runai-mcp:0.1.0}"
WORK="${WORK:-${TMPDIR:-/tmp}/bnk-agents-run-ai-src}"
GO_IMAGE="${GO_IMAGE:-golang:1.27}"   # runai-mcp-server/go.mod at 59e288d7 says go 1.27.2
ARCH="${ARCH:-amd64}"
PKG=github.com/dsx-ai-factory/run-ai/runai-mcp-server

# This lab only ever publishes under its own image names. The BNK Run:ai lab's images (runai-mcp-server,
# bnk-tenancy-mcp, ...) must never be overwritten from here.
case "${IMAGE#docker.io/}" in
  iracic82/bnk-agents-*) ;;
  *) echo "refusing: $IMAGE is not a bnk-agents-* image" >&2; exit 1 ;;
esac

if [ ! -d "$WORK/.git" ]; then
  git clone --filter=blob:none --no-checkout https://github.com/dsx-ai-factory/run-ai.git "$WORK"
fi
git -C "$WORK" fetch -q origin "$RUNAI_REF" 2>/dev/null || true
git -C "$WORK" checkout -q --force "$RUNAI_REF"
git -C "$WORK" apply "$HERE/stateless.patch"
SHA="$(git -C "$WORK" rev-parse HEAD)"
echo "building runai-mcp-server from dsx-ai-factory/run-ai@${SHA} + stateless.patch"

# Same as NVIDIA's golang.mk build-go-amd: GOFIPS140=v1.0.0, version stamped via -ldflags.
# HOST_GO=1 compiles with the host's Go instead of a golang container: same env and flags, for hosts
# behind a TLS-intercepting proxy whose CA the container doesn't trust (module downloads fail there).
build=(go build -trimpath -ldflags "-X ${PKG}/internal/server.serverVersion=${IMAGE##*:}"
       -o "bin/runai-mcp-server-${ARCH}" ./cmd/runai-mcp)
restore() { git -C "$WORK" checkout -q -- runai-mcp-server/internal/http/oauth.go; }
trap restore EXIT
if [ "${HOST_GO:-0}" = 1 ]; then
  (cd "$WORK/runai-mcp-server" && CGO_ENABLED=0 GOOS=linux GOARCH="$ARCH" GOFIPS140=v1.0.0 GOFLAGS=-mod=mod "${build[@]}")
else
  docker run --rm -v "$WORK":/src -w /src/runai-mcp-server \
    -e CGO_ENABLED=0 -e GOOS=linux -e GOARCH="$ARCH" -e GOFIPS140=v1.0.0 -e GOFLAGS=-mod=mod \
    "$GO_IMAGE" "${build[@]}"
fi

docker build --platform "linux/${ARCH}" --build-arg TARGETARCH="$ARCH" \
  --label "org.opencontainers.image.source=https://github.com/dsx-ai-factory/run-ai" \
  --label "org.opencontainers.image.revision=${SHA}" \
  --label "org.opencontainers.image.description=runai-mcp-server, stateless (bnk-agents-lab platform/mcp/stateless.patch)" \
  -t "$IMAGE" "$WORK/runai-mcp-server"

if [ "${PUSH:-0}" = 1 ]; then
  docker push "$IMAGE"
  echo "pushed $IMAGE; pin it in platform/versions.env (RUNAI_MCP_IMAGE) by digest"
else
  echo "not pushed (PUSH=1 to push)"
fi
