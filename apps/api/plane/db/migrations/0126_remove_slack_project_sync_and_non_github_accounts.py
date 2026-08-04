# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0125_remove_api_activity_log"),
    ]

    operations = [
        migrations.DeleteModel(
            name="SlackProjectSync",
        ),
        migrations.AlterField(
            model_name="account",
            name="provider",
            field=models.CharField(choices=[("github", "Github")]),
        ),
        migrations.AlterField(
            model_name="socialloginconnection",
            name="medium",
            field=models.CharField(
                choices=[("Github", "github"), ("Jira", "jira")], default=None, max_length=20
            ),
        ),
    ]
