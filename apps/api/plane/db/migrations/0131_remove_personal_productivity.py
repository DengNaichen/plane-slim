# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations


def remove_obsolete_preferences_and_assets(apps, schema_editor):
    apps.get_model("db", "WorkspaceHomePreference").objects.filter(
        key__in=["recents", "my_stickies"]
    ).delete()
    apps.get_model("db", "WorkspaceUserPreference").objects.filter(
        key__in=["views", "drafts", "stickies"]
    ).delete()
    apps.get_model("db", "FileAsset").objects.filter(
        entity_type__in=["DRAFT_ISSUE_ATTACHMENT", "DRAFT_ISSUE_DESCRIPTION"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0130_remove_project_issue_automation"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="fileasset",
            name="draft_issue",
        ),
        migrations.RemoveField(
            model_name="project",
            name="issue_views_view",
        ),
        migrations.RunPython(remove_obsolete_preferences_and_assets, migrations.RunPython.noop),
        migrations.DeleteModel(name="DraftIssueAssignee"),
        migrations.DeleteModel(name="DraftIssueLabel"),
        migrations.DeleteModel(name="DraftIssueModule"),
        migrations.DeleteModel(name="DraftIssueCycle"),
        migrations.DeleteModel(name="DraftIssue"),
        migrations.DeleteModel(name="IssueView"),
        migrations.DeleteModel(name="Sticky"),
        migrations.DeleteModel(name="UserFavorite"),
        migrations.DeleteModel(name="UserRecentVisit"),
    ]
