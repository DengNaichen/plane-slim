# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0127_remove_outgoing_webhooks"),
    ]

    operations = [
        migrations.DeleteModel(name="ExporterHistory"),
        migrations.DeleteModel(name="Importer"),
        migrations.AlterField(
            model_name="socialloginconnection",
            name="medium",
            field=models.CharField(choices=[("Github", "github")], default=None, max_length=20),
        ),
    ]
