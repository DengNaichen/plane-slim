// Copyright (c) 2023-present Plane Software, Inc. and contributors
// SPDX-License-Identifier: AGPL-3.0-only

package main

import (
	"context"
	"fmt"
	"net/url"
	"strings"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

type toolOutput struct {
	Data any `json:"data" jsonschema:"Plane response data"`
}

type emptyInput struct{}

type workspaceInput struct {
	Workspace string `json:"workspace,omitempty" jsonschema:"Plane workspace slug; defaults to PLANE_WORKSPACE"`
}

type searchInput struct {
	Workspace string `json:"workspace,omitempty" jsonschema:"Plane workspace slug; defaults to PLANE_WORKSPACE"`
	Query     string `json:"query" jsonschema:"Text to search for"`
	Entity    string `json:"entity,omitempty" jsonschema:"Optional entity: workspace, project, work_item, cycle, module, or intake"`
	ProjectID string `json:"project_id,omitempty" jsonschema:"Optional project UUID to restrict the search"`
}

type fetchInput struct {
	Workspace string `json:"workspace,omitempty" jsonschema:"Plane workspace slug; defaults to PLANE_WORKSPACE"`
	Ref       string `json:"ref" jsonschema:"Entity reference, for example work_item:ENG-123, project:<uuid>, cycle:<uuid>, or module:<uuid>"`
	ProjectID string `json:"project_id,omitempty" jsonschema:"Project UUID, required for cycle and module references"`
}

type listWorkItemsInput struct {
	Workspace  string `json:"workspace,omitempty" jsonschema:"Plane workspace slug; defaults to PLANE_WORKSPACE"`
	ProjectID  string `json:"project_id" jsonschema:"Plane project UUID"`
	StateID    string `json:"state_id,omitempty" jsonschema:"Filter by state UUID"`
	AssigneeID string `json:"assignee_id,omitempty" jsonschema:"Filter by assignee UUID"`
	LabelID    string `json:"label_id,omitempty" jsonschema:"Filter by label UUID"`
	CycleID    string `json:"cycle_id,omitempty" jsonschema:"Filter by cycle UUID"`
	ModuleID   string `json:"module_id,omitempty" jsonschema:"Filter by module UUID"`
	Priority   string `json:"priority,omitempty" jsonschema:"Filter by urgent, high, medium, low, or none"`
	UpdatedAt  string `json:"updated_after,omitempty" jsonschema:"Only work items updated after this ISO-8601 timestamp"`
	OrderBy    string `json:"order_by,omitempty" jsonschema:"Sort field, optionally prefixed with a minus sign"`
	Cursor     string `json:"cursor,omitempty" jsonschema:"Opaque cursor returned by Plane"`
	Limit      int    `json:"limit,omitempty" jsonschema:"Maximum results, from 1 to 100; defaults to 50"`
}

type saveWorkItemInput struct {
	Workspace       string   `json:"workspace,omitempty" jsonschema:"Plane workspace slug; defaults to PLANE_WORKSPACE"`
	ProjectID       string   `json:"project_id" jsonschema:"Plane project UUID"`
	ID              string   `json:"id,omitempty" jsonschema:"Work item UUID to update; omit to create"`
	Title           *string  `json:"title,omitempty" jsonschema:"Work item title; required when creating"`
	DescriptionHTML *string  `json:"description_html,omitempty" jsonschema:"Sanitized HTML description"`
	StateID         *string  `json:"state_id,omitempty" jsonschema:"State UUID"`
	Priority        *string  `json:"priority,omitempty" jsonschema:"urgent, high, medium, low, or none"`
	AssigneeIDs     []string `json:"assignee_ids,omitempty" jsonschema:"Complete replacement list of assignee UUIDs"`
	LabelIDs        []string `json:"label_ids,omitempty" jsonschema:"Complete replacement list of label UUIDs"`
	ParentID        *string  `json:"parent_id,omitempty" jsonschema:"Parent work item UUID; empty string clears it"`
	StartDate       *string  `json:"start_date,omitempty" jsonschema:"Start date as YYYY-MM-DD; empty string clears it"`
	TargetDate      *string  `json:"target_date,omitempty" jsonschema:"Target date as YYYY-MM-DD; empty string clears it"`
}

type projectInput struct {
	Workspace string `json:"workspace,omitempty" jsonschema:"Plane workspace slug; defaults to PLANE_WORKSPACE"`
	ProjectID string `json:"project_id" jsonschema:"Plane project UUID"`
}

type optionalProjectInput struct {
	Workspace string `json:"workspace,omitempty" jsonschema:"Plane workspace slug; defaults to PLANE_WORKSPACE"`
	ProjectID string `json:"project_id,omitempty" jsonschema:"Optional Plane project UUID"`
}

type commentsInput struct {
	Workspace  string `json:"workspace,omitempty" jsonschema:"Plane workspace slug; defaults to PLANE_WORKSPACE"`
	ProjectID  string `json:"project_id" jsonschema:"Plane project UUID"`
	WorkItemID string `json:"work_item_id" jsonschema:"Plane work item UUID"`
}

type saveCommentInput struct {
	Workspace  string  `json:"workspace,omitempty" jsonschema:"Plane workspace slug; defaults to PLANE_WORKSPACE"`
	ProjectID  string  `json:"project_id" jsonschema:"Plane project UUID"`
	WorkItemID string  `json:"work_item_id" jsonschema:"Plane work item UUID"`
	ID         string  `json:"id,omitempty" jsonschema:"Comment UUID to update; omit to create"`
	BodyHTML   string  `json:"body_html" jsonschema:"Sanitized HTML comment body"`
	ParentID   *string `json:"parent_id,omitempty" jsonschema:"Parent comment UUID for a reply"`
}

func newMCPServer(client *planeClient, defaultWorkspace string) *mcp.Server {
	server := mcp.NewServer(&mcp.Implementation{Name: "plane", Version: version}, nil)
	registerTools(server, client, defaultWorkspace)
	return server
}

func registerTools(server *mcp.Server, client *planeClient, defaultWorkspace string) {
	mcp.AddTool(server, readTool("list_workspaces", "List Plane workspaces visible to the authenticated user."), func(ctx context.Context, _ *mcp.CallToolRequest, _ emptyInput) (*mcp.CallToolResult, toolOutput, error) {
		data, err := client.get(ctx, "/api/users/me/workspaces/", nil)
		return nil, toolOutput{Data: data}, err
	})

	mcp.AddTool(server, readTool("list_projects", "List projects in a Plane workspace."), func(ctx context.Context, _ *mcp.CallToolRequest, input workspaceInput) (*mcp.CallToolResult, toolOutput, error) {
		workspace, err := requiredWorkspace(input.Workspace, defaultWorkspace)
		if err != nil {
			return nil, toolOutput{}, err
		}
		data, err := client.get(ctx, apiPath("workspaces", workspace, "projects"), nil)
		return nil, toolOutput{Data: data}, err
	})

	mcp.AddTool(server, readTool("search", "Search Plane projects, work items, cycles, modules, and intake items in a workspace."), func(ctx context.Context, _ *mcp.CallToolRequest, input searchInput) (*mcp.CallToolResult, toolOutput, error) {
		workspace, err := requiredWorkspace(input.Workspace, defaultWorkspace)
		if err != nil {
			return nil, toolOutput{}, err
		}
		if strings.TrimSpace(input.Query) == "" {
			return nil, toolOutput{}, fmt.Errorf("query is required")
		}
		entity, err := searchEntity(input.Entity)
		if err != nil {
			return nil, toolOutput{}, err
		}
		query := url.Values{"search": {input.Query}, "workspace_search": {"true"}}
		if entity != "" {
			query.Set("entities", entity)
		}
		if input.ProjectID != "" {
			query.Set("project_id", input.ProjectID)
			query.Set("workspace_search", "false")
		}
		data, err := client.get(ctx, apiPath("workspaces", workspace, "search"), query)
		return nil, toolOutput{Data: data}, err
	})

	mcp.AddTool(server, readTool("fetch", "Fetch one Plane work item, project, cycle, or module by a typed reference."), func(ctx context.Context, _ *mcp.CallToolRequest, input fetchInput) (*mcp.CallToolResult, toolOutput, error) {
		workspace, err := requiredWorkspace(input.Workspace, defaultWorkspace)
		if err != nil {
			return nil, toolOutput{}, err
		}
		path, err := fetchPath(workspace, input.ProjectID, input.Ref)
		if err != nil {
			return nil, toolOutput{}, err
		}
		data, err := client.get(ctx, path, nil)
		return nil, toolOutput{Data: data}, err
	})

	mcp.AddTool(server, readTool("list_work_items", "List and filter work items in one Plane project."), func(ctx context.Context, _ *mcp.CallToolRequest, input listWorkItemsInput) (*mcp.CallToolResult, toolOutput, error) {
		workspace, err := requiredWorkspace(input.Workspace, defaultWorkspace)
		if err != nil {
			return nil, toolOutput{}, err
		}
		if strings.TrimSpace(input.ProjectID) == "" {
			return nil, toolOutput{}, fmt.Errorf("project_id is required")
		}
		query, err := workItemQuery(input)
		if err != nil {
			return nil, toolOutput{}, err
		}
		data, err := client.get(ctx, apiPath("workspaces", workspace, "projects", input.ProjectID, "issues"), query)
		return nil, toolOutput{Data: data}, err
	})

	mcp.AddTool(server, writeTool("save_work_item", "Create or update a Plane work item. Omit id to create; provide id to update."), func(ctx context.Context, _ *mcp.CallToolRequest, input saveWorkItemInput) (*mcp.CallToolResult, toolOutput, error) {
		workspace, err := requiredWorkspace(input.Workspace, defaultWorkspace)
		if err != nil {
			return nil, toolOutput{}, err
		}
		payload, err := workItemPayload(input)
		if err != nil {
			return nil, toolOutput{}, err
		}
		path := apiPath("workspaces", workspace, "projects", input.ProjectID, "issues")
		var data any
		if input.ID == "" {
			data, err = client.post(ctx, path, payload)
		} else {
			data, err = client.patch(ctx, apiPath("workspaces", workspace, "projects", input.ProjectID, "issues", input.ID), payload)
		}
		return nil, toolOutput{Data: data}, err
	})

	mcp.AddTool(server, readTool("list_states", "List workflow states in a Plane project."), func(ctx context.Context, _ *mcp.CallToolRequest, input projectInput) (*mcp.CallToolResult, toolOutput, error) {
		workspace, err := requiredWorkspace(input.Workspace, defaultWorkspace)
		if err != nil {
			return nil, toolOutput{}, err
		}
		if err := required(input.ProjectID, "project_id"); err != nil {
			return nil, toolOutput{}, err
		}
		data, err := client.get(ctx, apiPath("workspaces", workspace, "projects", input.ProjectID, "states"), nil)
		return nil, toolOutput{Data: data}, err
	})

	mcp.AddTool(server, readTool("list_labels", "List labels in a Plane workspace or project."), func(ctx context.Context, _ *mcp.CallToolRequest, input optionalProjectInput) (*mcp.CallToolResult, toolOutput, error) {
		workspace, err := requiredWorkspace(input.Workspace, defaultWorkspace)
		if err != nil {
			return nil, toolOutput{}, err
		}
		path := apiPath("workspaces", workspace, "labels")
		if input.ProjectID != "" {
			path = apiPath("workspaces", workspace, "projects", input.ProjectID, "issue-labels")
		}
		data, err := client.get(ctx, path, nil)
		return nil, toolOutput{Data: data}, err
	})

	mcp.AddTool(server, readTool("list_members", "List members in a Plane workspace or project."), func(ctx context.Context, _ *mcp.CallToolRequest, input optionalProjectInput) (*mcp.CallToolResult, toolOutput, error) {
		workspace, err := requiredWorkspace(input.Workspace, defaultWorkspace)
		if err != nil {
			return nil, toolOutput{}, err
		}
		path := apiPath("workspaces", workspace, "members")
		if input.ProjectID != "" {
			path = apiPath("workspaces", workspace, "projects", input.ProjectID, "members")
		}
		data, err := client.get(ctx, path, nil)
		return nil, toolOutput{Data: data}, err
	})

	mcp.AddTool(server, readTool("list_cycles", "List cycles in a Plane workspace or project."), func(ctx context.Context, _ *mcp.CallToolRequest, input optionalProjectInput) (*mcp.CallToolResult, toolOutput, error) {
		workspace, err := requiredWorkspace(input.Workspace, defaultWorkspace)
		if err != nil {
			return nil, toolOutput{}, err
		}
		path := apiPath("workspaces", workspace, "cycles")
		if input.ProjectID != "" {
			path = apiPath("workspaces", workspace, "projects", input.ProjectID, "cycles")
		}
		data, err := client.get(ctx, path, nil)
		return nil, toolOutput{Data: data}, err
	})

	mcp.AddTool(server, readTool("list_modules", "List modules in a Plane workspace or project."), func(ctx context.Context, _ *mcp.CallToolRequest, input optionalProjectInput) (*mcp.CallToolResult, toolOutput, error) {
		workspace, err := requiredWorkspace(input.Workspace, defaultWorkspace)
		if err != nil {
			return nil, toolOutput{}, err
		}
		path := apiPath("workspaces", workspace, "modules")
		if input.ProjectID != "" {
			path = apiPath("workspaces", workspace, "projects", input.ProjectID, "modules")
		}
		data, err := client.get(ctx, path, nil)
		return nil, toolOutput{Data: data}, err
	})

	mcp.AddTool(server, readTool("list_comments", "List comments on a Plane work item."), func(ctx context.Context, _ *mcp.CallToolRequest, input commentsInput) (*mcp.CallToolResult, toolOutput, error) {
		workspace, err := requiredWorkspace(input.Workspace, defaultWorkspace)
		if err != nil {
			return nil, toolOutput{}, err
		}
		if err := required(input.ProjectID, "project_id"); err != nil {
			return nil, toolOutput{}, err
		}
		if err := required(input.WorkItemID, "work_item_id"); err != nil {
			return nil, toolOutput{}, err
		}
		data, err := client.get(ctx, apiPath("workspaces", workspace, "projects", input.ProjectID, "issues", input.WorkItemID, "comments"), nil)
		return nil, toolOutput{Data: data}, err
	})

	mcp.AddTool(server, writeTool("save_comment", "Create or update a comment on a Plane work item. Omit id to create; provide id to update."), func(ctx context.Context, _ *mcp.CallToolRequest, input saveCommentInput) (*mcp.CallToolResult, toolOutput, error) {
		workspace, err := requiredWorkspace(input.Workspace, defaultWorkspace)
		if err != nil {
			return nil, toolOutput{}, err
		}
		if strings.TrimSpace(input.BodyHTML) == "" {
			return nil, toolOutput{}, fmt.Errorf("body_html is required")
		}
		if err := required(input.ProjectID, "project_id"); err != nil {
			return nil, toolOutput{}, err
		}
		if err := required(input.WorkItemID, "work_item_id"); err != nil {
			return nil, toolOutput{}, err
		}
		payload := map[string]any{"comment_html": input.BodyHTML}
		if input.ParentID != nil {
			payload["parent"] = nullableString(*input.ParentID)
		}
		path := apiPath("workspaces", workspace, "projects", input.ProjectID, "issues", input.WorkItemID, "comments")
		var data any
		if input.ID == "" {
			data, err = client.post(ctx, path, payload)
		} else {
			data, err = client.patch(ctx, apiPath("workspaces", workspace, "projects", input.ProjectID, "issues", input.WorkItemID, "comments", input.ID), payload)
		}
		return nil, toolOutput{Data: data}, err
	})
}

func readTool(name, description string) *mcp.Tool {
	openWorld := false
	return &mcp.Tool{
		Name:        name,
		Description: description,
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true, OpenWorldHint: &openWorld},
	}
}

func writeTool(name, description string) *mcp.Tool {
	destructive, openWorld := true, false
	return &mcp.Tool{
		Name:        name,
		Description: description,
		Annotations: &mcp.ToolAnnotations{DestructiveHint: &destructive, OpenWorldHint: &openWorld},
	}
}

func apiPath(parts ...string) string {
	return "/api/" + escaped(parts...) + "/"
}

func searchEntity(entity string) (string, error) {
	entity = strings.TrimSpace(strings.ToLower(entity))
	if entity == "" || entity == "all" {
		return "", nil
	}
	if entity == "work_item" || entity == "issue" {
		return "issue", nil
	}
	for _, allowed := range []string{"workspace", "project", "cycle", "module", "intake"} {
		if entity == allowed {
			return entity, nil
		}
	}
	return "", fmt.Errorf("unsupported entity %q", entity)
}

func fetchPath(workspace, projectID, ref string) (string, error) {
	ref = strings.TrimSpace(ref)
	if ref == "" {
		return "", fmt.Errorf("ref is required")
	}
	kind, value, found := strings.Cut(ref, ":")
	if !found {
		kind, value = "work_item", ref
	}
	kind = strings.ToLower(strings.TrimSpace(kind))
	value = strings.TrimSpace(value)
	if value == "" {
		return "", fmt.Errorf("ref value is required")
	}

	switch kind {
	case "work_item", "issue":
		return apiPath("workspaces", workspace, "work-items", value), nil
	case "project":
		return apiPath("workspaces", workspace, "projects", value), nil
	case "cycle", "module":
		if strings.TrimSpace(projectID) == "" {
			return "", fmt.Errorf("project_id is required for %s references", kind)
		}
		return apiPath("workspaces", workspace, "projects", projectID, kind+"s", value), nil
	default:
		return "", fmt.Errorf("unsupported ref type %q", kind)
	}
}

func workItemQuery(input listWorkItemsInput) (url.Values, error) {
	if input.Limit < 0 {
		return nil, fmt.Errorf("limit cannot be negative")
	}
	query := url.Values{}
	query.Set("per_page", fmt.Sprint(limit(input.Limit)))
	for key, value := range map[string]string{
		"state_id":       input.StateID,
		"assignee_id":    input.AssigneeID,
		"label_id":       input.LabelID,
		"cycle_id":       input.CycleID,
		"module_id":      input.ModuleID,
		"updated_at__gt": input.UpdatedAt,
		"cursor":         input.Cursor,
	} {
		if strings.TrimSpace(value) != "" {
			query.Set(key, value)
		}
	}
	if input.UpdatedAt != "" {
		if _, err := time.Parse(time.RFC3339Nano, input.UpdatedAt); err != nil {
			return nil, fmt.Errorf("updated_after must use ISO-8601/RFC3339")
		}
	}
	if input.Priority != "" {
		if err := validatePriority(input.Priority); err != nil {
			return nil, err
		}
		query.Set("priority", input.Priority)
	}
	if input.OrderBy != "" {
		if err := validateOrderBy(input.OrderBy); err != nil {
			return nil, err
		}
		query.Set("order_by", input.OrderBy)
	}
	return query, nil
}

func limit(value int) int {
	if value <= 0 {
		return 50
	}
	if value > 100 {
		return 100
	}
	return value
}

func validatePriority(value string) error {
	for _, allowed := range []string{"urgent", "high", "medium", "low", "none"} {
		if value == allowed {
			return nil
		}
	}
	return fmt.Errorf("invalid priority %q", value)
}

func validateOrderBy(value string) error {
	if strings.HasPrefix(value, "--") {
		return fmt.Errorf("invalid order_by %q", value)
	}
	field := strings.TrimPrefix(value, "-")
	for _, allowed := range []string{
		"created_at", "updated_at", "sequence_id", "sort_order", "target_date", "start_date", "priority",
	} {
		if field == allowed {
			return nil
		}
	}
	return fmt.Errorf("invalid order_by %q", value)
}

func workItemPayload(input saveWorkItemInput) (map[string]any, error) {
	if strings.TrimSpace(input.ProjectID) == "" {
		return nil, fmt.Errorf("project_id is required")
	}
	payload := map[string]any{}
	if input.Title != nil {
		if strings.TrimSpace(*input.Title) == "" {
			return nil, fmt.Errorf("title cannot be empty")
		}
		payload["name"] = *input.Title
	}
	if input.DescriptionHTML != nil {
		payload["description_html"] = *input.DescriptionHTML
	}
	if input.StateID != nil {
		payload["state_id"] = nullableString(*input.StateID)
	}
	if input.Priority != nil {
		if err := validatePriority(*input.Priority); err != nil {
			return nil, err
		}
		payload["priority"] = *input.Priority
	}
	if input.AssigneeIDs != nil {
		payload["assignee_ids"] = input.AssigneeIDs
	}
	if input.LabelIDs != nil {
		payload["label_ids"] = input.LabelIDs
	}
	if input.ParentID != nil {
		payload["parent_id"] = nullableString(*input.ParentID)
	}
	if err := addDate(payload, "start_date", input.StartDate); err != nil {
		return nil, err
	}
	if err := addDate(payload, "target_date", input.TargetDate); err != nil {
		return nil, err
	}

	if input.ID == "" && input.Title == nil {
		return nil, fmt.Errorf("title is required when creating a work item")
	}
	if input.ID != "" && len(payload) == 0 {
		return nil, fmt.Errorf("at least one field is required when updating a work item")
	}
	return payload, nil
}

func nullableString(value string) any {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	return value
}

func addDate(payload map[string]any, name string, value *string) error {
	if value == nil {
		return nil
	}
	if strings.TrimSpace(*value) == "" {
		payload[name] = nil
		return nil
	}
	if _, err := time.Parse(time.DateOnly, *value); err != nil {
		return fmt.Errorf("%s must use YYYY-MM-DD", name)
	}
	payload[name] = *value
	return nil
}
