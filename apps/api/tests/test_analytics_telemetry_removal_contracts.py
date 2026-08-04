# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.apps import apps
from django.conf import settings
from django.urls import Resolver404, resolve

from plane.celery import app as celery_app


PROJECT_ID = "00000000-0000-0000-0000-000000000001"
CYCLE_ID = "00000000-0000-0000-0000-000000000002"


@pytest.mark.unit
@pytest.mark.parametrize(
    "path",
    [
        "/api/workspaces/acme/analytics/",
        "/api/workspaces/acme/default-analytics/",
        "/api/workspaces/acme/advance-analytics/",
        f"/api/workspaces/acme/projects/{PROJECT_ID}/advance-analytics-stats/",
        f"/api/workspaces/acme/projects/{PROJECT_ID}/cycles/{CYCLE_ID}/analytics/",
    ],
)
def test_analytics_routes_are_not_resolved(path):
    with pytest.raises(Resolver404):
        resolve(path)


@pytest.mark.unit
def test_analytic_view_model_is_not_registered():
    with pytest.raises(LookupError):
        apps.get_model("db", "AnalyticView")


@pytest.mark.unit
@pytest.mark.parametrize(
    ("path", "url_name"),
    [
        (f"/api/workspaces/acme/projects/{PROJECT_ID}/cycles/", "project-cycle"),
        (f"/api/workspaces/acme/projects/{PROJECT_ID}/modules/", "project-modules"),
    ],
)
def test_core_cycle_and_module_routes_remain_resolved(path, url_name):
    assert resolve(path).url_name == url_name


@pytest.mark.unit
def test_analytics_and_tracking_are_absent_from_settings():
    assert "plane.analytics" not in settings.INSTALLED_APPS
    assert not {
        "ANALYTICS_SECRET_KEY",
        "ANALYTICS_BASE_API",
        "POSTHOG_API_KEY",
        "POSTHOG_HOST",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
        "OTEL_EXPORTER_OTLP_METRICS_PROTOCOL",
        "OTEL_EXPORTER_OTLP_METRICS_INSECURE",
        "SCOUT_MONITOR",
        "SCOUT_KEY",
        "SCOUT_NAME",
    }.intersection(dir(settings))
    assert not any("telemetry" in task for task in settings.CELERY_IMPORTS)


@pytest.mark.unit
def test_instance_telemetry_is_not_scheduled():
    assert "push-instance-metrics" not in celery_app.conf.beat_schedule
    assert not any(
        "telemetry" in entry["task"] for entry in celery_app.conf.beat_schedule.values()
    )
