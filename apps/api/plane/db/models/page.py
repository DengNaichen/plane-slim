# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Compatibility callable retained for historical migrations.

The Pages models were removed, but migration 0064 imports this default.
"""


def get_view_props():
    return {"full_width": False}
