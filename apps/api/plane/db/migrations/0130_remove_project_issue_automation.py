# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0129_remove_product_notifications"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="project",
            name="archive_in",
        ),
        migrations.RemoveField(
            model_name="project",
            name="close_in",
        ),
    ]
