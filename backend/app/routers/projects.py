from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _get_owned_project(project_id: str, current_user: models.User, db: Session) -> models.Project:
    """404s (not 403) for projects that exist but belong to someone else,
    so a project ID can't be used to probe for its existence."""
    project = db.query(models.Project).get(project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(404, "Project not found")
    return project


@router.get("", response_model=list[schemas.ProjectOut])
def list_projects(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Project)
        .filter_by(owner_id=current_user.id)
        .order_by(models.Project.created_at.desc())
        .all()
    )


@router.post("", response_model=schemas.ProjectOut)
def create_project(
    payload: schemas.ProjectCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = models.Project(
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description or "",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(
    project_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_project(project_id, current_user, db)


@router.get("/{project_id}/documents", response_model=list[schemas.DocumentOut])
def list_project_documents(
    project_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_project(project_id, current_user, db)
    return (
        db.query(models.Document)
        .filter_by(project_id=project_id)
        .order_by(models.Document.created_at.desc())
        .all()
    )


@router.get("/{project_id}/contradictions", response_model=list[schemas.ContradictionOut])
def list_contradictions(
    project_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_project(project_id, current_user, db)
    return db.query(models.Contradiction).filter_by(project_id=project_id).all()


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_owned_project(project_id, current_user, db)
    db.delete(project)
    db.commit()
    return {"deleted": True}
