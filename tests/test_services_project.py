"""
Unit tests for ProjectService.
"""

from __future__ import annotations

import pytest

from services.project_service import ProjectService


def test_create_project_persists_metadata(project_service: ProjectService):
    project = project_service.create_project("Strategy Review")

    assert project["id"]
    assert project["name"] == "Strategy Review"
    assert project["documents"] == []
    assert project["reports"] == []

    loaded = project_service.get_project(project["id"])

    assert loaded["name"] == "Strategy Review"


def test_get_project_returns_copy(project_service: ProjectService):
    project = project_service.create_project("Copy Check")

    loaded = project_service.get_project(project["id"])
    loaded["name"] = "Mutated"

    reloaded = project_service.get_project(project["id"])

    assert reloaded["name"] == "Copy Check"


def test_create_project_rejects_duplicate_name(
    project_service: ProjectService,
):
    project_service.create_project("Duplicate Name")

    with pytest.raises(ValueError, match="already exists"):
        project_service.create_project("Duplicate Name")


def test_rename_project(project_service: ProjectService):
    project = project_service.create_project("Old Name")

    updated = project_service.rename_project(
        project["id"],
        "New Name",
    )

    assert updated["name"] == "New Name"
    assert project_service.get_project(project["id"])["name"] == "New Name"


def test_delete_project(project_service: ProjectService):
    project = project_service.create_project("Temporary Project")

    project_service.delete_project(project["id"])

    with pytest.raises(ValueError, match="Project not found"):
        project_service.get_project(project["id"])


def test_get_statistics(project_service: ProjectService):
    project_service.create_project("Stats Project A")
    project_service.create_project("Stats Project B")

    stats = project_service.get_statistics()

    assert stats["projects"] >= 2
