# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import uuid

import pytest
from django.apps import apps
from django.core.cache import cache
from django.urls import Resolver404, resolve, reverse
from django.utils import timezone

from plane.license.models import Instance


@pytest.mark.unit
@pytest.mark.parametrize(
    "path",
    [
        "/auth/google/",
        "/auth/google/callback/",
        "/auth/spaces/google/",
        "/auth/spaces/google/callback/",
        "/auth/gitlab/",
        "/auth/gitlab/callback/",
        "/auth/spaces/gitlab/",
        "/auth/spaces/gitlab/callback/",
        "/auth/gitea/",
        "/auth/gitea/callback/",
        "/auth/spaces/gitea/",
        "/auth/spaces/gitea/callback/",
    ],
)
def test_removed_oauth_routes_are_not_resolved(path):
    with pytest.raises(Resolver404):
        resolve(path)


@pytest.mark.unit
@pytest.mark.parametrize(
    "name",
    [
        "github-initiate",
        "github-callback",
        "space-github-initiate",
        "space-github-callback",
        "sign-in",
        "sign-up",
        "space-sign-in",
        "space-sign-up",
        "magic-generate",
        "magic-sign-in",
        "magic-sign-up",
        "space-magic-generate",
        "space-magic-sign-in",
        "space-magic-sign-up",
    ],
)
def test_retained_auth_routes_can_be_reversed(name):
    assert reverse(name)


@pytest.mark.unit
def test_slack_sync_model_is_not_registered():
    with pytest.raises(LookupError):
        apps.get_model("db", "SlackProjectSync")


@pytest.mark.unit
@pytest.mark.parametrize(
    "model_name", ["APIToken", "WorkspaceIntegration", "GithubRepositorySync"]
)
def test_retained_integration_models_are_registered(model_name):
    assert apps.get_model("db", model_name) is not None


@pytest.mark.unit
@pytest.mark.django_db
def test_instance_configuration_does_not_expose_slack(client):
    Instance.objects.get_or_create(
        instance_id=str(uuid.uuid4()),
        defaults={
            "instance_name": "Test Instance",
            "current_version": "1.0.0",
            "domain": "http://localhost:8000",
            "last_checked_at": timezone.now(),
            "is_setup_done": True,
        },
    )
    cache.delete("/api/instances/")

    response = client.get("/api/instances/")

    assert response.status_code == 200
    config = response.json()["config"]
    assert not {
        "slack_client_id",
        "is_google_enabled",
        "is_gitlab_enabled",
        "is_gitea_enabled",
    }.intersection(config)
    assert "is_github_enabled" in config
