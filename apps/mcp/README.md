# Plane MCP

Go MCP server for Plane. It proxies Plane's existing browser API and does not restore `/api/v1` or any in-product AI feature.

It uses the official MCP Go SDK `v1.7.0` and negotiates protocol `2026-07-28` by default. HTTP transport is stateless as required by that protocol; older clients can negotiate an earlier supported version.

## Tools

- `list_workspaces`
- `list_projects`
- `search`
- `fetch`
- `list_work_items`
- `save_work_item`
- `list_states`
- `list_labels`
- `list_members`
- `list_cycles`
- `list_modules`
- `list_comments`
- `save_comment`

## Configuration

| Variable                    | Required        | Default          | Purpose                                           |
| --------------------------- | --------------- | ---------------- | ------------------------------------------------- |
| `PLANE_BASE_URL`            | yes             | —                | Plane origin, for example `http://localhost:8000` |
| `PLANE_API_KEY`             | one auth method | —                | Sent as `X-Api-Key`                               |
| `PLANE_SESSION_ID`          | one auth method | —                | Existing Plane session value                      |
| `PLANE_SESSION_COOKIE_NAME` | no              | `session-id`     | Plane session cookie name                         |
| `PLANE_WORKSPACE`           | no              | —                | Default workspace slug                            |
| `MCP_TRANSPORT`             | no              | `stdio`          | `stdio` or `http`                                 |
| `MCP_ADDR`                  | no              | `127.0.0.1:8080` | HTTP listen address                               |
| `MCP_BEARER_TOKEN`          | HTTP only       | —                | Protects the MCP HTTP endpoint                    |

This repository currently enables session authentication on the proxied Plane routes. `PLANE_API_KEY` is ready for a later narrow API-key authentication path; use `PLANE_SESSION_ID` until that path exists.

## Run

```sh
cd apps/mcp
go build -o plane-mcp .

PLANE_BASE_URL=http://localhost:8000 \
PLANE_SESSION_ID=your-session-id \
PLANE_WORKSPACE=acme \
./plane-mcp
```

Stateless Streamable HTTP:

```sh
MCP_TRANSPORT=http \
MCP_BEARER_TOKEN=change-me \
PLANE_BASE_URL=http://localhost:8000 \
PLANE_SESSION_ID=your-session-id \
PLANE_WORKSPACE=acme \
./plane-mcp
```

The endpoint is `http://127.0.0.1:8080/mcp`.

## Verify

```sh
go test ./...
go vet ./...
```

The protocol test connects through Streamable HTTP, verifies negotiation of `2026-07-28`, lists all tools, and calls `list_projects` through a fake Plane API.
