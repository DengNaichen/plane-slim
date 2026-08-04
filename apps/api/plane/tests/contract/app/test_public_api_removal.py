# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from importlib.util import find_spec
from uuid import uuid4

import pytest
from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.urls import NoReverseMatch, Resolver404, resolve, reverse


@pytest.mark.contract
def test_removed_public_api_routes_are_not_registered():
    with pytest.raises(Resolver404):
        resolve("/api/v1/")
    with pytest.raises(NoReverseMatch):
        reverse("api-tokens")
    with pytest.raises(NoReverseMatch):
        reverse("api-tokens-details", kwargs={"pk": uuid4()})


@pytest.mark.contract
def test_outgoing_webhook_routes_are_not_registered():
    with pytest.raises(Resolver404):
        resolve("/api/workspaces/workspace/webhooks/")
    with pytest.raises(Resolver404):
        resolve(f"/api/workspaces/workspace/webhook-logs/{uuid4()}/")
    with pytest.raises(NoReverseMatch):
        reverse("webhooks", kwargs={"slug": "workspace"})


@pytest.mark.contract
def test_outgoing_webhook_models_are_unregistered_but_github_models_remain():
    model_names = {model.__name__ for model in apps.get_app_config("db").get_models()}

    assert not {"Webhook", "WebhookLog", "ProjectWebhook"} & model_names
    assert {
        "GithubRepositorySync",
        "GithubIssueSync",
        "GithubCommentSync",
        "WorkspaceIntegration",
        "APIToken",
    } <= model_names


@pytest.mark.contract
def test_product_notification_routes_and_models_are_unregistered():
    for path in (
        "/api/workspaces/workspace/users/notifications/",
        f"/api/workspaces/workspace/users/notifications/{uuid4()}/",
        "/api/users/me/notification-preferences/",
    ):
        with pytest.raises(Resolver404):
            resolve(path)

    with pytest.raises(NoReverseMatch):
        reverse("notifications", kwargs={"slug": "workspace", "pk": uuid4()})
    for route_name in ("unread-notifications", "mark-all-read-notifications"):
        with pytest.raises(NoReverseMatch):
            reverse(route_name, kwargs={"slug": "workspace"})
    with pytest.raises(NoReverseMatch):
        reverse("user-notification-preferences")

    model_names = {model.__name__ for model in apps.get_app_config("db").get_models()}
    assert not {"Notification", "UserNotificationPreference", "EmailNotificationLog"} & model_names


@pytest.mark.contract
def test_intake_inbox_and_transactional_email_remain_registered():
    project_id = uuid4()
    intake_kwargs = {"slug": "workspace", "project_id": project_id}

    for route_name in ("intake", "intake-issue", "inbox", "inbox-issue"):
        reverse(route_name, kwargs=intake_kwargs)

    for route_name in ("email-credential-check", "magic-generate", "forgot-password"):
        reverse(route_name)
    reverse("workspace-invitations", kwargs={"slug": "workspace"})
    reverse("project-member-invite", kwargs=intake_kwargs)

    from plane.bgtasks.forgot_password_task import forgot_password
    from plane.bgtasks.magic_link_code_task import magic_link
    from plane.bgtasks.project_add_user_email_task import project_add_user_email
    from plane.bgtasks.project_invitation_task import project_invitation
    from plane.bgtasks.workspace_invitation_task import workspace_invitation

    assert all(
        callable(task)
        for task in (
            magic_link,
            forgot_password,
            workspace_invitation,
            project_invitation,
            project_add_user_email,
        )
    )

    model_names = {model.__name__ for model in apps.get_app_config("db").get_models()}
    assert {
        "Intake",
        "IntakeIssue",
        "Workspace",
        "Project",
        "Issue",
        "State",
        "Label",
        "Cycle",
        "Module",
        "Estimate",
    } <= model_names


@pytest.mark.contract
def test_github_oauth_routes_remain_registered():
    for route_name in (
        "github-initiate",
        "github-callback",
        "space-github-initiate",
        "space-github-callback",
    ):
        reverse(route_name)


@pytest.mark.contract
def test_import_export_routes_and_models_are_unregistered_but_core_models_remain():
    for path in (
        "/api/workspaces/workspace/export-issues/",
        f"/api/workspaces/workspace/user-activity/{uuid4()}/export/",
    ):
        with pytest.raises(Resolver404):
            resolve(path)

    for route_name in ("export-issues", "export-workspace-user-activity"):
        with pytest.raises(NoReverseMatch):
            reverse(route_name, kwargs={"slug": "workspace"})

    model_names = {model.__name__ for model in apps.get_app_config("db").get_models()}

    assert not {"Importer", "ExporterHistory"} & model_names
    assert {
        "Workspace",
        "Project",
        "Issue",
        "Cycle",
        "Module",
        "Intake",
        "FileAsset",
        "SocialLoginConnection",
        "GithubRepository",
        "GithubRepositorySync",
        "GithubIssueSync",
        "GithubCommentSync",
    } <= model_names


@pytest.mark.contract
def test_issue_automation_is_unregistered_but_manual_archive_and_core_workflows_remain():
    project_id = uuid4()
    issue_id = uuid4()
    route_kwargs = {"slug": "workspace", "project_id": project_id, "pk": issue_id}

    archive_route = reverse("project-issue-archive-unarchive", kwargs=route_kwargs)
    assert archive_route.endswith(f"/issues/{issue_id}/archive/")
    reverse("project-issue-archive", kwargs={"slug": "workspace", "project_id": project_id})
    reverse("bulk-archive-issues", kwargs={"slug": "workspace", "project_id": project_id})

    project = apps.get_model("db", "Project")
    for field_name in ("archive_in", "close_in"):
        with pytest.raises(FieldDoesNotExist):
            project._meta.get_field(field_name)

    assert not find_spec("plane.bgtasks.issue_automation_task")
    from plane.celery import app

    assert all(
        task["task"] != "plane.bgtasks.issue_automation_task.archive_and_close_old_issues"
        for task in app.conf.beat_schedule.values()
    )

    model_names = {model.__name__ for model in apps.get_app_config("db").get_models()}
    assert {
        "Workspace",
        "Project",
        "Issue",
        "IssueActivity",
        "State",
        "Label",
        "Cycle",
        "Module",
        "Estimate",
        "Intake",
        "FileAsset",
        "WorkspaceHomePreference",
        "WorkspaceUserPreference",
        "GithubRepository",
        "GithubRepositorySync",
        "GithubIssueSync",
        "GithubCommentSync",
    } <= model_names


@pytest.mark.contract
def test_personal_productivity_features_are_unregistered_but_core_work_item_routes_remain():
    project_id = uuid4()
    issue_id = uuid4()

    for path in (
        "/api/workspaces/workspace/user-favorites/",
        "/api/workspaces/workspace/draft-issues/",
        f"/api/workspaces/workspace/draft-to-issue/{issue_id}/",
        "/api/workspaces/workspace/recent-visits/",
        "/api/workspaces/workspace/stickies/",
        "/api/workspaces/workspace/views/",
        "/api/workspaces/workspace/issues/",
        f"/api/workspaces/workspace/projects/{project_id}/views/",
        f"/api/workspaces/workspace/projects/{project_id}/user-favorite-views/",
        "/api/workspaces/workspace/user-favorite-projects/",
        f"/api/workspaces/workspace/projects/{project_id}/user-favorite-cycles/",
        f"/api/workspaces/workspace/projects/{project_id}/user-favorite-modules/",
    ):
        with pytest.raises(Resolver404):
            resolve(path)

    model_names = {model.__name__ for model in apps.get_app_config("db").get_models()}
    assert not {
        "DraftIssue",
        "DraftIssueAssignee",
        "DraftIssueLabel",
        "DraftIssueCycle",
        "DraftIssueModule",
        "UserFavorite",
        "UserRecentVisit",
        "Sticky",
        "IssueView",
    } & model_names

    project = apps.get_model("db", "Project")
    file_asset = apps.get_model("db", "FileAsset")
    home_preference = apps.get_model("db", "WorkspaceHomePreference")
    user_preference = apps.get_model("db", "WorkspaceUserPreference")
    for model, field_name in ((project, "issue_views_view"), (file_asset, "draft_issue")):
        with pytest.raises(FieldDoesNotExist):
            model._meta.get_field(field_name)

    assert not {"DRAFT_ISSUE_ATTACHMENT", "DRAFT_ISSUE_DESCRIPTION"} & {
        value for value, _ in file_asset.EntityTypeContext.choices
    }
    assert not {"recents", "my_stickies"} & {value for value, _ in home_preference.HomeWidgetKeys.choices}
    assert not {"views", "drafts", "stickies"} & {
        value for value, _ in user_preference.UserPreferenceKeys.choices
    }

    from plane.bgtasks import issue_activities_task

    assert not find_spec("plane.bgtasks.recent_visited_task")
    assert not {
        "create_draft_issue_activity",
        "update_draft_issue_activity",
        "delete_draft_issue_activity",
    } & set(dir(issue_activities_task))

    from plane.app.views.issue.base import IssueListEndpoint, IssueViewSet
    from plane.app.views.project.base import ProjectViewSet
    from plane.app.views.search.issue import IssueSearchEndpoint

    search_path = f"/api/workspaces/workspace/projects/{project_id}/search-issues/"
    assert reverse("project-issue-search", kwargs={"slug": "workspace", "project_id": project_id}) == search_path

    route_classes = {
        f"/api/workspaces/workspace/projects/{project_id}/issues/": IssueViewSet,
        f"/api/workspaces/workspace/projects/{project_id}/issues/{issue_id}/": IssueViewSet,
        f"/api/workspaces/workspace/projects/{project_id}/issues/list/": IssueListEndpoint,
        search_path: IssueSearchEndpoint,
        "/api/workspaces/workspace/projects/": ProjectViewSet,
    }
    for path, view_class in route_classes.items():
        assert resolve(path).func.cls is view_class
