from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).order_by(models.Project.created_at.desc()).all()


@router.post("", response_model=schemas.ProjectOut)
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)):
    project = models.Project(name=payload.name, description=payload.description or "")
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/{project_id}/documents", response_model=list[schemas.DocumentOut])
def list_project_documents(project_id: str, db: Session = Depends(get_db)):
    return (
        db.query(models.Document)
        .filter_by(project_id=project_id)
        .order_by(models.Document.created_at.desc())
        .all()
    )


@router.get("/{project_id}/contradictions", response_model=list[schemas.ContradictionOut])
def list_contradictions(project_id: str, db: Session = Depends(get_db)):
    return db.query(models.Contradiction).filter_by(project_id=project_id).all()


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    db.delete(project)
    db.commit()
    return {"deleted": True}
