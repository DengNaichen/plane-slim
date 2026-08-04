# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from importlib import import_module
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.db import migrations
from django.urls import Resolver404, resolve


@pytest.mark.unit
@pytest.mark.parametrize(
    "path",
    [
        "/api/workspaces/acme/projects/00000000-0000-0000-0000-000000000001/pages/",
        "/api/workspaces/acme/projects/00000000-0000-0000-0000-000000000001/"
        "pages/00000000-0000-0000-0000-000000000002/",
        "/api/workspaces/acme/projects/00000000-0000-0000-0000-000000000001/"
        "pages/00000000-0000-0000-0000-000000000002/versions/",
    ],
)
def test_project_page_routes_are_not_resolved(path):
    with pytest.raises(Resolver404):
        resolve(path)


@pytest.mark.unit
@pytest.mark.parametrize("model_name", ["Page", "PageVersion"])
def test_page_models_are_not_registered(model_name):
    with pytest.raises(LookupError):
        apps.get_model("db", model_name)


@pytest.mark.unit
def test_historical_page_migration_remains_importable():
    migration = import_module("plane.db.migrations.0064_auto_20240409_1134")

    assert migration.Migration.operations


@pytest.mark.unit
def test_project_route_remains_resolved():
    assert resolve("/api/workspaces/acme/projects/").url_name == "project"


@pytest.mark.unit
def test_page_data_cleanup_precedes_page_schema_removal():
    migration = import_module("plane.db.migrations.0123_remove_pages")
    cleanup_index, cleanup = next(
        (index, operation)
        for index, operation in enumerate(migration.Migration.operations)
        if isinstance(operation, migrations.RunPython)
    )
    schema_removal_index = next(
        index
        for index, operation in enumerate(migration.Migration.operations)
        if isinstance(operation, (migrations.RemoveField, migrations.DeleteModel, migrations.AlterField))
    )

    class Manager:
        def __init__(self, records=()):
            self.filters = []
            self.delete_calls = 0
            self.records = records

        def filter(self, **kwargs):
            self.filters.append(kwargs)
            return self

        def all(self):
            return self

        def __iter__(self):
            return iter(self.records)

        def iterator(self):
            return iter(self.records)

        def delete(self):
            self.delete_calls += 1

    class Record:
        def __init__(self, **fields):
            self.__dict__.update(fields)
            self.save_calls = 0

        def save(self, **kwargs):
            self.save_calls += 1

    with_pages = [
        ("ProjectMember", "preferences", Record(preferences={"pages": True, "keep": True})),
        ("ProjectUserProperty", "preferences", Record(preferences={"pages": False, "keep": True})),
        ("Profile", "product_tour", Record(product_tour={"pages": True, "keep": True})),
    ]
    without_pages = [
        ("ProjectMember", "preferences", Record(preferences={"keep": True})),
        ("ProjectUserProperty", "preferences", Record(preferences={"keep": True})),
        ("Profile", "product_tour", Record(product_tour={"keep": True})),
    ]
    managers = {model_name: Manager() for model_name in ("UserFavorite", "UserRecentVisit", "FileAsset")}
    for model_name, _, record in with_pages + without_pages:
        managers.setdefault(model_name, Manager()).records += (record,)

    class HistoricalApps:
        def get_model(self, app_label, model_name):
            assert app_label == "db"
            return SimpleNamespace(objects=managers[model_name])

    cleanup.code(HistoricalApps(), None)

    expected_filters = {
        "UserFavorite": {"entity_type": "page"},
        "UserRecentVisit": {"entity_name__in": ["page", "PAGE"]},
        "FileAsset": {"entity_type": "PAGE_DESCRIPTION"},
    }
    assert cleanup_index < schema_removal_index
    for model_name, filters in expected_filters.items():
        assert managers[model_name].filters == [filters]
        assert managers[model_name].delete_calls == 1
    for _, field_name, record in with_pages:
        assert getattr(record, field_name) == {"keep": True}
        assert record.save_calls == 1
    for _, field_name, record in without_pages:
        assert getattr(record, field_name) == {"keep": True}
        assert record.save_calls == 0
