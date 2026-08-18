// Copyright (c) 2023-present Plane Software, Inc. and contributors
// SPDX-License-Identifier: AGPL-3.0-only

package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
)

const maxResponseBytes = 8 << 20

type planeClient struct {
	baseURL       *url.URL
	apiKey        string
	sessionID     string
	sessionCookie string
	http          *http.Client
}

func newPlaneClient(baseURL, apiKey, sessionID, sessionCookie string, httpClient *http.Client) (*planeClient, error) {
	parsed, err := url.Parse(strings.TrimRight(baseURL, "/"))
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return nil, fmt.Errorf("invalid PLANE_BASE_URL %q", baseURL)
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return nil, fmt.Errorf("PLANE_BASE_URL must use http or https")
	}
	if parsed.RawQuery != "" || parsed.Fragment != "" {
		return nil, fmt.Errorf("PLANE_BASE_URL cannot contain a query or fragment")
	}
	if parsed.User != nil {
		return nil, fmt.Errorf("PLANE_BASE_URL cannot contain credentials")
	}
	if httpClient == nil {
		httpClient = http.DefaultClient
	}
	return &planeClient{
		baseURL:       parsed,
		apiKey:        apiKey,
		sessionID:     sessionID,
		sessionCookie: sessionCookie,
		http:          httpClient,
	}, nil
}

func (c *planeClient) get(ctx context.Context, path string, query url.Values) (any, error) {
	return c.do(ctx, http.MethodGet, path, query, nil)
}

func (c *planeClient) post(ctx context.Context, path string, payload map[string]any) (any, error) {
	return c.do(ctx, http.MethodPost, path, nil, payload)
}

func (c *planeClient) patch(ctx context.Context, path string, payload map[string]any) (any, error) {
	return c.do(ctx, http.MethodPatch, path, nil, payload)
}

func (c *planeClient) do(ctx context.Context, method, path string, query url.Values, payload any) (any, error) {
	target, err := url.Parse(strings.TrimRight(c.baseURL.String(), "/") + "/" + strings.TrimLeft(path, "/"))
	if err != nil {
		return nil, fmt.Errorf("build Plane URL: %w", err)
	}
	target.RawQuery = query.Encode()

	var body io.Reader
	if payload != nil {
		encoded, err := json.Marshal(payload)
		if err != nil {
			return nil, fmt.Errorf("encode Plane request: %w", err)
		}
		body = bytes.NewReader(encoded)
	}

	req, err := http.NewRequestWithContext(ctx, method, target.String(), body)
	if err != nil {
		return nil, fmt.Errorf("create Plane request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	if payload != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if c.apiKey != "" {
		req.Header.Set("X-Api-Key", c.apiKey)
	} else {
		req.AddCookie(&http.Cookie{Name: c.sessionCookie, Value: c.sessionID})
	}

	response, err := c.http.Do(req)
	if err != nil {
		return nil, fmt.Errorf("call Plane: %w", err)
	}
	defer response.Body.Close()

	data, err := io.ReadAll(io.LimitReader(response.Body, maxResponseBytes+1))
	if err != nil {
		return nil, fmt.Errorf("read Plane response: %w", err)
	}
	if len(data) > maxResponseBytes {
		return nil, fmt.Errorf("Plane response exceeds %d bytes", maxResponseBytes)
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		message := strings.TrimSpace(string(data))
		if len(message) > 1000 {
			message = message[:1000]
		}
		return nil, fmt.Errorf("Plane returned %s: %s", response.Status, message)
	}
	if response.StatusCode == http.StatusNoContent || len(data) == 0 {
		return map[string]any{"ok": true}, nil
	}

	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	var result any
	if err := decoder.Decode(&result); err != nil {
		return nil, fmt.Errorf("decode Plane response: %w", err)
	}
	return result, nil
}

func escaped(parts ...string) string {
	for index := range parts {
		parts[index] = url.PathEscape(strings.TrimSpace(parts[index]))
	}
	return strings.Join(parts, "/")
}
