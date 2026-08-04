# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0126_remove_slack_project_sync_and_non_github_accounts"),
    ]

    operations = [
        migrations.DeleteModel(name="ProjectWebhook"),
        migrations.DeleteModel(name="WebhookLog"),
        migrations.DeleteModel(name="Webhook"),
    ]
