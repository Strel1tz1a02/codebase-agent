from __future__ import annotations

from fastapi import FastAPI, Response, status

from src.api.errors import not_found_to_http_exception
from src.api.schemas import CreateProjectRequest, ProjectListResponse, ProjectResponse
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
        project = app.state.runtime.create_project(request.name, request.repo_path)
        return project_to_response(project)

    @app.get("/projects", response_model=ProjectListResponse)
    def list_projects() -> ProjectListResponse:
        projects = [project_to_response(project) for project in app.state.runtime.list_projects()]
        return ProjectListResponse(projects=projects)

    @app.get("/projects/{project_id}", response_model=ProjectResponse)
    def get_project(project_id: str) -> ProjectResponse:
        try:
            project = app.state.runtime.get_project(project_id)
        except ProjectNotFoundError as exc:
            raise not_found_to_http_exception(exc) from exc
        return project_to_response(project)

    @app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_project(project_id: str) -> Response:
        try:
            app.state.runtime.delete_project(project_id)
        except ProjectNotFoundError as exc:
            raise not_found_to_http_exception(exc) from exc
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/projects/{project_id}/index", response_model=ProjectResponse)
    def index_project(project_id: str) -> ProjectResponse:
        try:
            project = app.state.runtime.index_project(project_id)
        except ProjectNotFoundError as exc:
            raise not_found_to_http_exception(exc) from exc
        return project_to_response(project)
