# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations


def remove_analytics_preferences(apps, schema_editor):
    apps.get_model("db", "WorkspaceUserPreference").objects.filter(
        key="analytics"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0123_remove_pages"),
    ]

    operations = [
        migrations.RunPython(
            remove_analytics_preferences,
            migrations.RunPython.noop,
        ),
        migrations.DeleteModel(name="AnalyticView"),
    ]
