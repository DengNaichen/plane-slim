# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models
import plane.db.models.project
import plane.db.models.user


def remove_page_generic_records(apps, schema_editor):
    apps.get_model("db", "UserFavorite").objects.filter(entity_type="page").delete()
    apps.get_model("db", "UserRecentVisit").objects.filter(entity_name__in=["page", "PAGE"]).delete()
    apps.get_model("db", "FileAsset").objects.filter(entity_type="PAGE_DESCRIPTION").delete()
    for model_name, field_name in (
        ("ProjectMember", "preferences"),
        ("ProjectUserProperty", "preferences"),
        ("Profile", "product_tour"),
    ):
        model = apps.get_model("db", model_name)
        for instance in model.objects.all().iterator():
            data = getattr(instance, field_name)
            if isinstance(data, dict) and "pages" in data:
                data.pop("pages")
                setattr(instance, field_name, data)
                instance.save(update_fields=[field_name])


class Migration(migrations.Migration):

    dependencies = [
        ("db", "0122_alter_draftissue_assignees_alter_issue_assignees_and_more"),
    ]

    operations = [
        migrations.RunPython(remove_page_generic_records, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="project",
            name="page_view",
        ),
        migrations.AlterField(
            model_name="projectmember",
            name="preferences",
            field=models.JSONField(default=plane.db.models.project.get_default_preferences),
        ),
        migrations.AlterField(
            model_name="projectuserproperty",
            name="preferences",
            field=models.JSONField(default=plane.db.models.project.get_default_preferences),
        ),
        migrations.AlterField(
            model_name="profile",
            name="product_tour",
            field=models.JSONField(default=plane.db.models.user.get_default_product_tour),
        ),
        migrations.RemoveField(
            model_name="fileasset",
            name="page",
        ),
        migrations.DeleteModel(
            name="PageVersion",
        ),
        migrations.DeleteModel(
            name="ProjectPage",
        ),
        migrations.DeleteModel(
            name="PageLabel",
        ),
        migrations.DeleteModel(
            name="PageLog",
        ),
        migrations.DeleteModel(
            name="Page",
        ),
    ]
