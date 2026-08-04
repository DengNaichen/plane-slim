# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from plane.db.models import Issue, Project


def burndown_plot(queryset, slug, project_id, plot_type, cycle_id=None, module_id=None):
    total_issues = queryset.total_issues
    estimate_type = Project.objects.filter(
        workspace__slug=slug,
        pk=project_id,
        estimate__isnull=False,
        estimate__type="points",
    ).exists()

    relation_filter = {
        "workspace__slug": slug,
        "project_id": project_id,
        "estimate_point__isnull": False,
    }
    if cycle_id:
        relation_filter.update(
            issue_cycle__cycle_id=cycle_id,
            issue_cycle__deleted_at__isnull=True,
        )
    elif module_id:
        relation_filter.update(
            issue_module__module_id=module_id,
            issue_module__deleted_at__isnull=True,
        )

    if estimate_type and plot_type == "points":
        total_estimate_points = sum(
            float(value)
            for value in Issue.issue_objects.filter(**relation_filter).values_list(
                "estimate_point__value", flat=True
            )
        )

    if cycle_id:
        date_range = (
            [
                (queryset.start_date + timedelta(days=offset)).date()
                for offset in range(
                    (queryset.end_date.date() - queryset.start_date.date()).days + 1
                )
            ]
            if queryset.start_date and queryset.end_date
            else []
        )
        issue_filter = {
            "workspace__slug": slug,
            "project_id": project_id,
            "issue_cycle__cycle_id": cycle_id,
            "issue_cycle__deleted_at__isnull": True,
        }
    else:
        date_range = [
            queryset.start_date + timedelta(days=offset)
            for offset in range((queryset.target_date - queryset.start_date).days + 1)
        ]
        issue_filter = {
            "workspace__slug": slug,
            "project_id": project_id,
            "issue_module__module_id": module_id,
            "issue_module__deleted_at__isnull": True,
        }

    chart_data = {str(date): 0 for date in date_range}
    completed = Issue.issue_objects.filter(**issue_filter).annotate(date=TruncDate("completed_at"))
    if plot_type == "points":
        completed = completed.filter(estimate_point__isnull=False).values(
            "date", "estimate_point__value"
        )
    else:
        completed = completed.values("date").annotate(total_completed=Count("id"))

    for date in date_range:
        if plot_type == "points":
            completed_value = sum(
                float(item["estimate_point__value"])
                for item in completed
                if item["date"] is not None and item["date"] <= date
            )
            pending = total_estimate_points - completed_value
        else:
            completed_value = sum(
                item["total_completed"]
                for item in completed
                if item["date"] is not None and item["date"] <= date
            )
            pending = total_issues - completed_value
        chart_data[str(date)] = None if date > timezone.now().date() else pending

    return chart_data
