// Copyright (c) 2023-present Plane Software, Inc. and contributors
// SPDX-License-Identifier: AGPL-3.0-only

package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"
)

func TestPlaneClientAPIKeyRequest(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.EscapedPath() != "/api/workspaces/acme%20team/projects/" {
			t.Errorf("path = %q", r.URL.EscapedPath())
		}
		if got := r.Header.Get("X-Api-Key"); got != "secret" {
			t.Errorf("X-Api-Key = %q", got)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`[{"id":"project-1"}]`))
	}))
	defer server.Close()

	client, err := newPlaneClient(server.URL, "secret", "", "session-id", server.Client())
	if err != nil {
		t.Fatal(err)
	}
	data, err := client.get(context.Background(), apiPath("workspaces", "acme team", "projects"), nil)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(data, []any{map[string]any{"id": "project-1"}}) {
		t.Fatalf("data = %#v", data)
	}
}

func TestPlaneClientSessionCookieAndPayload(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		cookie, err := r.Cookie("session-id")
		if err != nil || cookie.Value != "session-secret" {
			t.Fatalf("cookie = %#v, err = %v", cookie, err)
		}
		var payload map[string]any
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatal(err)
		}
		if payload["name"] != "Fix MCP" {
			t.Errorf("payload = %#v", payload)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"id":"issue-1"}`))
	}))
	defer server.Close()

	client, err := newPlaneClient(server.URL, "", "session-secret", "session-id", server.Client())
	if err != nil {
		t.Fatal(err)
	}
	if _, err := client.post(context.Background(), "/api/issues/", map[string]any{"name": "Fix MCP"}); err != nil {
		t.Fatal(err)
	}
}

func TestFetchPath(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		projectID string
		ref       string
		want      string
		wantErr   bool
	}{
		{name: "bare work item", ref: "ENG-123", want: "/api/workspaces/acme/work-items/ENG-123/"},
		{name: "typed work item", ref: "work_item:ENG-123", want: "/api/workspaces/acme/work-items/ENG-123/"},
		{name: "project", ref: "project:project-id", want: "/api/workspaces/acme/projects/project-id/"},
		{name: "cycle", projectID: "project-id", ref: "cycle:cycle-id", want: "/api/workspaces/acme/projects/project-id/cycles/cycle-id/"},
		{name: "missing project", ref: "module:module-id", wantErr: true},
		{name: "unknown", ref: "document:doc-id", wantErr: true},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			t.Parallel()
			got, err := fetchPath("acme", test.projectID, test.ref)
			if (err != nil) != test.wantErr {
				t.Fatalf("error = %v", err)
			}
			if got != test.want {
				t.Errorf("path = %q, want %q", got, test.want)
			}
		})
	}
}

func TestWorkItemPayloadPreservesClearOperations(t *testing.T) {
	t.Parallel()

	empty := ""
	payload, err := workItemPayload(saveWorkItemInput{
		ProjectID:   "project-id",
		ID:          "issue-id",
		AssigneeIDs: []string{},
		ParentID:    &empty,
		TargetDate:  &empty,
	})
	if err != nil {
		t.Fatal(err)
	}
	if assignees, ok := payload["assignee_ids"].([]string); !ok || len(assignees) != 0 {
		t.Errorf("assignee_ids = %#v", payload["assignee_ids"])
	}
	if payload["parent_id"] != nil || payload["target_date"] != nil {
		t.Errorf("payload = %#v", payload)
	}
}
