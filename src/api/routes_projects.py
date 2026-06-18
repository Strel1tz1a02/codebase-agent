from __future__ import annotations

from fastapi import FastAPI
from uuid import uuid4

from src.api.errors import not_found_to_http_exception
from src.api.schemas import CreateProjectRequest, ProjectResponse
from src.core.errors import ProjectNotFoundError
from src.runtime.project import Project


def project_to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        project_id=project.project_id,
        name=project.name,
        repo_path=project.repo_path,
        index_status=project.index_status,
    )


def register_project_routes(app: FastAPI) -> None:
    @app.post("/projects", response_model=ProjectResponse, status_code=201)
    def create_project(request: CreateProjectRequest) -> ProjectResponse:
        project = Project(project_id=uuid4().hex, name=request.name, repo_path=request.repo_path)
        app.state.runtime.store.add_project(project)
        return project_to_response(project)

    @app.get("/projects/{project_id}", response_model=ProjectResponse)
    def get_project(project_id: str) -> ProjectResponse:
        try:
            project = app.state.runtime.store.get_project(project_id)
        except ProjectNotFoundError as exc:
            raise not_found_to_http_exception(exc) from exc
        return project_to_response(project)

    @app.post("/projects/{project_id}/index", response_model=ProjectResponse)
    def index_project(project_id: str) -> ProjectResponse:
        try:
            project = app.state.runtime.index_project(project_id)
        except ProjectNotFoundError as exc:
            raise not_found_to_http_exception(exc) from exc
        return project_to_response(project)
