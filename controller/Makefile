ENVTEST_K8S ?= 1.30.x
IMG ?= docker.io/iracic82/bnk-agents-tenancy-controller:0.1.0
IMG_METER ?= docker.io/iracic82/bnk-agents-tenancy-meter:0.1.0
IMG_MCP ?= docker.io/iracic82/bnk-agents-tenancy-mcp:0.2.0
GOBIN := $(shell go env GOPATH)/bin

.PHONY: build test envtest vet image push meter-image meter-push mcp-image mcp-push mcp-image-hostgo mcp-push-hostgo

build:
	go build -o bin/manager ./cmd/manager
	go build -o bin/meter ./cmd/meter
	go build -o bin/bnk-tenancy-mcp ./cmd/mcp

vet:
	go vet ./...

test: vet
	go test ./internal/... ./cmd/...

# Real kube-apiserver at the BNK 2.4 cluster version, with the Run:ai kai.resources CRDs.
envtest:
	@test -x $(GOBIN)/setup-envtest || go install sigs.k8s.io/controller-runtime/tools/setup-envtest@release-0.23
	KUBEBUILDER_ASSETS="$$($(GOBIN)/setup-envtest use $(ENVTEST_K8S) -p path)" go test ./test/envtest/ -count=1 -v

image:
	docker build --platform linux/amd64 -t $(IMG) .

# This lab only publishes its own bnk-agents-* images, never the BNK Run:ai lab's.
push:
	@case "$(IMG)" in docker.io/iracic82/bnk-agents-*) ;; *) echo "refusing to push $(IMG)"; exit 1 ;; esac
	$(MAKE) image
	docker push $(IMG)

meter-image:
	docker build --platform linux/amd64 -f Dockerfile.meter -t $(IMG_METER) .

meter-push:
	@case "$(IMG_METER)" in docker.io/iracic82/bnk-agents-*) ;; *) echo "refusing to push $(IMG_METER)"; exit 1 ;; esac
	$(MAKE) meter-image
	docker push $(IMG_METER)

# Stateless MCP server with read-only BNK tenant tools (config/mcp.yaml).
mcp-image:
	docker build --platform linux/amd64 -f Dockerfile.mcp -t $(IMG_MCP) .

mcp-image-hostgo:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags="-s -w" -o dist/bnk-tenancy-mcp-linux-amd64 ./cmd/mcp
	docker build --platform linux/amd64 -f Dockerfile.mcp.prebuilt -t $(IMG_MCP) .

mcp-push:
	@case "$(IMG_MCP)" in docker.io/iracic82/bnk-agents-*) ;; *) echo "refusing to push $(IMG_MCP)"; exit 1 ;; esac
	$(MAKE) mcp-image
	docker push $(IMG_MCP)

mcp-push-hostgo:
	@case "$(IMG_MCP)" in docker.io/iracic82/bnk-agents-*) ;; *) echo "refusing to push $(IMG_MCP)"; exit 1 ;; esac
	$(MAKE) mcp-image-hostgo
	docker push $(IMG_MCP)
