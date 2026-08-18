// Copyright (c) 2023-present Plane Software, Inc. and contributors
// SPDX-License-Identifier: AGPL-3.0-only

package main

import (
	"context"
	"crypto/subtle"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const version = "0.1.0"

const maxMCPRequestBytes = 1 << 20

type config struct {
	planeBaseURL       string
	planeAPIKey        string
	planeSessionID     string
	planeSessionCookie string
	defaultWorkspace   string
	transport          string
	addr               string
	mcpBearerToken     string
}

func loadConfig() (config, error) {
	cfg := config{
		planeBaseURL:       strings.TrimSpace(os.Getenv("PLANE_BASE_URL")),
		planeAPIKey:        strings.TrimSpace(os.Getenv("PLANE_API_KEY")),
		planeSessionID:     strings.TrimSpace(os.Getenv("PLANE_SESSION_ID")),
		planeSessionCookie: envOr("PLANE_SESSION_COOKIE_NAME", "session-id"),
		defaultWorkspace:   strings.TrimSpace(os.Getenv("PLANE_WORKSPACE")),
		transport:          envOr("MCP_TRANSPORT", "stdio"),
		addr:               envOr("MCP_ADDR", "127.0.0.1:8080"),
		mcpBearerToken:     strings.TrimSpace(os.Getenv("MCP_BEARER_TOKEN")),
	}

	if cfg.planeBaseURL == "" {
		return config{}, errors.New("PLANE_BASE_URL is required")
	}
	if cfg.planeAPIKey == "" && cfg.planeSessionID == "" {
		return config{}, errors.New("PLANE_API_KEY or PLANE_SESSION_ID is required")
	}
	if cfg.transport != "stdio" && cfg.transport != "http" {
		return config{}, errors.New("MCP_TRANSPORT must be stdio or http")
	}
	if cfg.transport == "http" && cfg.mcpBearerToken == "" {
		return config{}, errors.New("MCP_BEARER_TOKEN is required for HTTP transport")
	}

	return cfg, nil
}

func envOr(name, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(name)); value != "" {
		return value
	}
	return fallback
}

func main() {
	cfg, err := loadConfig()
	if err != nil {
		log.Fatal(err)
	}

	client, err := newPlaneClient(
		cfg.planeBaseURL,
		cfg.planeAPIKey,
		cfg.planeSessionID,
		cfg.planeSessionCookie,
		&http.Client{
			Timeout: 30 * time.Second,
			CheckRedirect: func(*http.Request, []*http.Request) error {
				return http.ErrUseLastResponse
			},
		},
	)
	if err != nil {
		log.Fatal(err)
	}

	server := newMCPServer(client, cfg.defaultWorkspace)
	if cfg.transport == "stdio" {
		if err := server.Run(context.Background(), &mcp.StdioTransport{}); err != nil {
			log.Fatal(err)
		}
		return
	}

	handler := mcp.NewStreamableHTTPHandler(
		func(*http.Request) *mcp.Server { return server },
		&mcp.StreamableHTTPOptions{Stateless: true, JSONResponse: true},
	)
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", healthz)
	mux.Handle("/mcp", requireBearer(cfg.mcpBearerToken, limitRequestBody(maxMCPRequestBytes, handler)))

	httpServer := &http.Server{
		Addr:              cfg.addr,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}
	log.Printf("plane-mcp %s listening on http://%s/mcp", version, cfg.addr)
	if err := httpServer.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
}

func healthz(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_, _ = w.Write([]byte(`{"status":"ok"}`))
}

func limitRequestBody(maxBytes int64, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.ContentLength > maxBytes {
			http.Error(w, "request too large", http.StatusRequestEntityTooLarge)
			return
		}
		r.Body = http.MaxBytesReader(w, r.Body, maxBytes)
		next.ServeHTTP(w, r)
	})
}

func requireBearer(token string, next http.Handler) http.Handler {
	want := "Bearer " + token
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if subtle.ConstantTimeCompare([]byte(r.Header.Get("Authorization")), []byte(want)) != 1 {
			w.Header().Set("WWW-Authenticate", `Bearer realm="plane-mcp"`)
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func required(value, name string) error {
	if strings.TrimSpace(value) == "" {
		return fmt.Errorf("%s is required", name)
	}
	return nil
}

func requiredWorkspace(value, fallback string) (string, error) {
	if value = strings.TrimSpace(value); value != "" {
		return value, nil
	}
	if fallback = strings.TrimSpace(fallback); fallback != "" {
		return fallback, nil
	}
	return "", fmt.Errorf("workspace is required when PLANE_WORKSPACE is unset")
}
