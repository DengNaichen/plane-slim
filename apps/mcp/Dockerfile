# syntax=docker/dockerfile:1.7
FROM golang:1.25-alpine AS builder

WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY *.go ./
RUN --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /plane-mcp .

FROM alpine:3.22
RUN apk add --no-cache ca-certificates
COPY --from=builder /plane-mcp /usr/local/bin/plane-mcp
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/plane-mcp"]
