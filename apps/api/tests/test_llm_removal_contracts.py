# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.urls import Resolver404, resolve

from plane.utils.instance_config_variables.core import core_config_variables


@pytest.mark.unit
@pytest.mark.parametrize(
    "path",
    [
        "/api/workspaces/acme/ai-assistant/",
        "/api/workspaces/acme/projects/00000000-0000-0000-0000-000000000001/ai-assistant/",
    ],
)
def test_ai_assistant_routes_are_not_resolved(path):
    with pytest.raises(Resolver404):
        resolve(path)


@pytest.mark.unit
def test_unsplash_route_remains_resolved():
    assert resolve("/api/unsplash/").url_name == "unsplash"


@pytest.mark.unit
def test_instance_configuration_excludes_llm_variables():
    config_keys = {variable["key"] for variable in core_config_variables}

    assert not config_keys.intersection({"LLM_API_KEY", "LLM_PROVIDER", "LLM_MODEL", "GPT_ENGINE"})
