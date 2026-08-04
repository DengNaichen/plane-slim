# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from .project.base import (
    ProjectViewSet,
    ProjectIdentifierEndpoint,
    ProjectUserViewsEndpoint,
    DeployBoardViewSet,
    ProjectArchiveUnarchiveEndpoint,
)

from .project.invite import (
    UserProjectInvitationsViewset,
    ProjectInvitationsViewset,
    ProjectJoinEndpoint,
)

from .project.member import (
    ProjectMemberViewSet,
    ProjectMemberUserEndpoint,
    UserProjectRolesEndpoint,
    ProjectMemberPreferenceEndpoint,
)

from .user.base import (
    UserEndpoint,
    UpdateUserOnBoardedEndpoint,
    UpdateUserTourCompletedEndpoint,
    UserActivityEndpoint,
)


from .base import BaseAPIView, BaseViewSet

from .workspace.base import (
    WorkSpaceViewSet,
    UserWorkSpacesEndpoint,
    WorkSpaceAvailabilityCheckEndpoint,
    UserWorkspaceDashboardEndpoint,
    WorkspaceThemeViewSet,
)

from .workspace.home import WorkspaceHomePreferenceViewSet
from .workspace.user_preference import WorkspaceUserPreferenceViewSet

from .workspace.member import (
    WorkSpaceMemberViewSet,
    WorkspaceMemberUserEndpoint,
    WorkspaceProjectMemberEndpoint,
    WorkspaceMemberUserViewsEndpoint,
)
from .workspace.invite import (
    WorkspaceInvitationsViewset,
    WorkspaceJoinEndpoint,
    UserWorkspaceInvitationsViewSet,
)
from .workspace.label import WorkspaceLabelsEndpoint
from .workspace.state import WorkspaceStatesEndpoint
from .workspace.user import (
    UserLastProjectWithWorkspaceEndpoint,
    WorkspaceUserProfileIssuesEndpoint,
    WorkspaceUserPropertiesEndpoint,
    WorkspaceUserProfileEndpoint,
    WorkspaceUserActivityEndpoint,
    WorkspaceUserProfileStatsEndpoint,
    UserActivityGraphEndpoint,
    UserIssueCompletedGraphEndpoint,
)
from .workspace.estimate import WorkspaceEstimatesEndpoint
from .workspace.module import WorkspaceModulesEndpoint
from .workspace.cycle import WorkspaceCyclesEndpoint
from .workspace.quick_link import QuickLinkViewSet
from .state.base import StateViewSet, IntakeStateEndpoint
from .cycle.base import (
    CycleViewSet,
    CycleDateCheckEndpoint,
    TransferCycleIssueEndpoint,
    CycleUserPropertiesEndpoint,
    CycleProgressEndpoint,
)
from .cycle.issue import CycleIssueViewSet
from .cycle.archive import CycleArchiveUnarchiveEndpoint

from .asset.base import FileAssetEndpoint, UserAssetsEndpoint, FileAssetViewSet
from .asset.v2 import (
    WorkspaceFileAssetEndpoint,
    UserAssetsV2Endpoint,
    StaticFileAssetEndpoint,
    AssetRestoreEndpoint,
    ProjectAssetEndpoint,
    ProjectBulkAssetEndpoint,
    AssetCheckEndpoint,
    DuplicateAssetEndpoint,
    WorkspaceAssetDownloadEndpoint,
    ProjectAssetDownloadEndpoint,
)
from .issue.base import (
    IssueListEndpoint,
    IssueViewSet,
    ProjectUserDisplayPropertyEndpoint,
    BulkDeleteIssuesEndpoint,
    DeletedIssuesListViewSet,
    IssuePaginatedViewSet,
    IssueDetailEndpoint,
    IssueBulkUpdateDateEndpoint,
    IssueMetaEndpoint,
    IssueDetailIdentifierEndpoint,
)

from .issue.activity import IssueActivityEndpoint

from .issue.archive import IssueArchiveViewSet, BulkArchiveIssuesEndpoint

from .issue.attachment import (
    IssueAttachmentEndpoint,
    # V2
    IssueAttachmentV2Endpoint,
)

from .issue.comment import IssueCommentViewSet, CommentReactionViewSet

from .issue.label import LabelViewSet, BulkCreateIssueLabelsEndpoint

from .issue.link import IssueLinkViewSet

from .issue.relation import IssueRelationViewSet

from .issue.reaction import IssueReactionViewSet

from .issue.sub_issue import SubIssuesEndpoint

from .issue.subscriber import IssueSubscriberViewSet

from .issue.version import IssueVersionEndpoint, WorkItemDescriptionVersionEndpoint

from .module.base import (
    ModuleViewSet,
    ModuleLinkViewSet,
    ModuleUserPropertiesEndpoint,
)

from .module.issue import ModuleIssueViewSet

from .module.archive import ModuleArchiveUnarchiveEndpoint

from .search.base import GlobalSearchEndpoint, SearchEndpoint
from .search.issue import IssueSearchEndpoint


from .external.base import UnsplashEndpoint
from .estimate.base import (
    ProjectEstimatePointEndpoint,
    BulkEstimatePointEndpoint,
    EstimatePointEndpoint,
)

from .intake.base import (
    IntakeViewSet,
    IntakeIssueViewSet,
    IntakeWorkItemDescriptionVersionEndpoint,
)

from .error_404 import custom_404_view

from .user.base import AccountEndpoint, ProfileEndpoint, UserSessionEndpoint

from .timezone.base import TimezoneEndpoint
