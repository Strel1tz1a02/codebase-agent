from __future__ import annotations

from fastapi import FastAPI, HTTPException

from src.api.schemas import CreateProjectRequest, ProjectResponse
from src.core.errors import ProjectNotFoundError
from src.runtime.projects import Project


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
        project = app.state.project_runtime.create_project(request.name, request.repo_path)
        return project_to_response(project)

    @app.get("/projects/{project_id}", response_model=ProjectResponse)
    def get_project(project_id: str) -> ProjectResponse:
        try:
            project = app.state.project_runtime.get_project(project_id)
        except ProjectNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return project_to_response(project)

    @app.post("/projects/{project_id}/index", response_model=ProjectResponse)
    def index_project(project_id: str) -> ProjectResponse:
        try:
            project = app.state.project_runtime.get_project(project_id)
        except ProjectNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        project.index_status = "indexed"  # type: ignore[assignment]
        return project_to_response(project)
