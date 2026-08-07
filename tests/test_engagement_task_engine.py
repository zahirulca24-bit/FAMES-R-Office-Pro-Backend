from types import SimpleNamespace

from app.engagement_template_models import (
    EngagementGeneratedTask,
    EngagementTaskDependency,
    EngagementTaskStatusHistory,
)
from app.routers.engagement_tasks import _ALLOWED_TRANSITIONS, weighted_progress


def test_task_engine_tables_and_control_columns_registered():
    assert EngagementGeneratedTask.__table__.c.parent_task_id is not None
    assert EngagementGeneratedTask.__table__.c.assignee_staff_id is not None
    assert EngagementGeneratedTask.__table__.c.reviewer_staff_id is not None
    assert EngagementGeneratedTask.__table__.c.weight_points is not None
    assert EngagementGeneratedTask.__table__.c.progress_percent is not None
    assert EngagementGeneratedTask.__table__.c.escalation_state is not None
    assert EngagementTaskDependency.__table__.name == "engagement_task_dependencies"
    assert EngagementTaskStatusHistory.__table__.name == "engagement_task_status_history"


def test_weighted_progress_reconciles_by_task_weight():
    tasks = [
        SimpleNamespace(weight_points=5, progress_percent=100),
        SimpleNamespace(weight_points=3, progress_percent=50),
        SimpleNamespace(weight_points=2, progress_percent=0),
    ]
    total_weight, earned_weight, percent = weighted_progress(tasks)
    assert total_weight == 10
    assert earned_weight == 6.5
    assert percent == 65.0


def test_weighted_progress_zero_weight_is_safe():
    tasks = [SimpleNamespace(weight_points=0, progress_percent=100)]
    assert weighted_progress(tasks) == (0, 0.0, 0.0)


def test_task_transition_matrix_blocks_reopening_completed_task():
    assert "COMPLETED" in _ALLOWED_TRANSITIONS["IN_PROGRESS"]
    assert _ALLOWED_TRANSITIONS["COMPLETED"] == set()
    assert "IN_PROGRESS" in _ALLOWED_TRANSITIONS["BLOCKED"]
