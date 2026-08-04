# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0128_remove_import_export"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="profile",
            name="notification_view_mode",
        ),
        migrations.DeleteModel(name="EmailNotificationLog"),
        migrations.DeleteModel(name="Notification"),
        migrations.DeleteModel(name="UserNotificationPreference"),
    ]
