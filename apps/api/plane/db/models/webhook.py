# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Migration compatibility for removed outgoing webhook models."""

from urllib.parse import urlparse
from uuid import uuid4

from django.core.exceptions import ValidationError


def generate_token():
    return "plane_wh_" + uuid4().hex


def validate_schema(value):
    if urlparse(value).scheme not in ["http", "https"]:
        raise ValidationError("Invalid schema. Only HTTP and HTTPS are allowed.")


def validate_domain(value):
    if urlparse(value).netloc in ["localhost", "127.0.0.1"]:
        raise ValidationError("Local URLs are not allowed.")
