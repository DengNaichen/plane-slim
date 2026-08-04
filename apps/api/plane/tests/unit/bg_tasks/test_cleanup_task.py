# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Unit tests for the log cleanup tasks.
"""

import pytest

from plane.bgtasks.cleanup_task import process_cleanup_task


@pytest.mark.unit
class TestProcessCleanupTaskErrorHandling:
    def test_batch_delete_failure_is_swallowed(self):
        """A failing batch is logged and skipped; the run does not raise."""

        class _BoomManager:
            @staticmethod
            def filter(**kwargs):
                raise RuntimeError("db unavailable")

        class _BoomModel:
            all_objects = _BoomManager()

        # Should not raise even though the delete blows up.
        process_cleanup_task(lambda: iter([1, 2, 3]), _BoomModel, "Boom")
