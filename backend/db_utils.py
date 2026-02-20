# db_utils.py
"""
Database utility functions for upsert operations.
Implements smart upsert that only updates null/empty values.
"""

from sqlalchemy.orm import Session
from database import Project, ProjectDocument
from typing import Dict, Any, Optional
from datetime import datetime
import json


def is_empty_value(value):
    """
    Check if a value is considered empty (None, empty string, empty dict, empty list).
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, dict) and len(value) == 0:
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    return False


def deep_merge_dicts(existing: Dict, new: Dict) -> Dict:
    """
    Deep merge two dictionaries, only updating null/empty values in existing.
    Recursively merges nested dictionaries and arrays.
    """
    if not existing:
        return new.copy() if new else {}
    if not new:
        return existing.copy() if existing else {}
    
    result = existing.copy()
    
    for key, new_value in new.items():
        if key not in result:
            # Key doesn't exist, add it
            result[key] = new_value
        elif is_empty_value(result[key]):
            # Existing value is empty, replace with new value
            result[key] = new_value
        elif isinstance(result[key], dict) and isinstance(new_value, dict):
            # Both are dicts, recursively merge
            result[key] = deep_merge_dicts(result[key], new_value)
        elif isinstance(result[key], list) and isinstance(new_value, list):
            # Both are lists, merge arrays (append unique items)
            existing_list = result[key]
            for item in new_value:
                if item not in existing_list:
                    existing_list.append(item)
            result[key] = existing_list
        # If existing value is not empty and not a dict/list, keep existing value
    
    return result


def upsert_project(
    db: Session,
    project_data: Dict[str, Any],
    project_id: Optional[int] = None,
    force_create: bool = False
) -> Project:
    """
    Upsert a project - create if doesn't exist, update only null/empty values if exists.
    
    Args:
        db: Database session
        project_data: Dictionary containing project data matching the schema
        project_id: Optional project ID to update existing project
        force_create: If True, always insert a new row and skip matching by project name
        
    Returns:
        Project: The created or updated project
    """
    project = None
    if project_id:
        # Update existing project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with id {project_id} not found")
    elif not force_create:
        # Check if project with same name exists
        if project_data.get("project_name"):
            project = db.query(Project).filter(
                Project.project_name == project_data.get("project_name")
            ).first()
            if project:
                project_id = project.id
    
    if project_id and project:
        # Update existing project - only update null/empty values
        # Handle top-level string fields
        if project_data.get("project_name") and is_empty_value(project.project_name):
            project.project_name = project_data["project_name"]
        if project_data.get("tagline") and is_empty_value(project.tagline):
            project.tagline = project_data["tagline"]
        if project_data.get("logo") and is_empty_value(project.logo):
            project.logo = project_data["logo"]
        if project_data.get("brand_name") and is_empty_value(project.brand_name):
            project.brand_name = project_data["brand_name"]
        
        # Handle JSON fields with deep merge
        json_fields = [
            "hero_section", "about", "location", "amenities", "amenity_categories",
            "tower_amenities", "gallery", "gallery_categories", "floor_plans",
            "pricing", "project_highlights", "project_info", "site_plan",
            "developer", "contact", "legal_info", "seo", "navigation",
            "cta_sections", "international_architects"
        ]
        
        for field in json_fields:
            if field in project_data and project_data[field] is not None:
                existing_value = getattr(project, field) or {}
                new_value = project_data[field]
                
                if isinstance(new_value, dict):
                    merged = deep_merge_dicts(existing_value, new_value)
                    setattr(project, field, merged)
                elif isinstance(new_value, list) and not is_empty_value(new_value):
                    # For lists, merge arrays
                    existing_list = existing_value if isinstance(existing_value, list) else []
                    for item in new_value:
                        if item not in existing_list:
                            existing_list.append(item)
                    setattr(project, field, existing_list)
                elif is_empty_value(existing_value):
                    # Existing is empty, set new value
                    setattr(project, field, new_value)
        
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(project)
        return project
    else:
        # Create new project
        project = Project(
            project_name=project_data.get("project_name"),
            tagline=project_data.get("tagline"),
            logo=project_data.get("logo"),
            brand_name=project_data.get("brand_name"),
            hero_section=project_data.get("hero_section"),
            about=project_data.get("about"),
            location=project_data.get("location"),
            amenities=project_data.get("amenities", []),
            amenity_categories=project_data.get("amenity_categories", []),
            tower_amenities=project_data.get("tower_amenities", []),
            gallery=project_data.get("gallery", []),
            gallery_categories=project_data.get("gallery_categories", []),
            floor_plans=project_data.get("floor_plans", []),
            pricing=project_data.get("pricing", []),
            project_highlights=project_data.get("project_highlights", []),
            project_info=project_data.get("project_info"),
            site_plan=project_data.get("site_plan"),
            developer=project_data.get("developer"),
            contact=project_data.get("contact"),
            legal_info=project_data.get("legal_info"),
            seo=project_data.get("seo"),
            navigation=project_data.get("navigation"),
            cta_sections=project_data.get("cta_sections", []),
            international_architects=project_data.get("international_architects")
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project


def add_project_document(
    db: Session,
    project_id: int,
    document_type: str,
    document_path: str,
    document_name: str,
    extracted_data: Optional[Dict] = None
) -> ProjectDocument:
    """
    Add a document record to a project.
    """
    doc = ProjectDocument(
        project_id=project_id,
        document_type=document_type,
        document_path=document_path,
        document_name=document_name,
        extracted_data=extracted_data
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_all_projects(db: Session, skip: int = 0, limit: int = 100):
    """
    Get all projects with pagination, ordered by most recent first.
    Handles NULL values in updated_at by falling back to created_at.
    """
    from sqlalchemy import desc, nullslast
    return db.query(Project).order_by(
        nullslast(desc(Project.updated_at)),
        nullslast(desc(Project.created_at))
    ).offset(skip).limit(limit).all()


def get_project_by_id(db: Session, project_id: int) -> Optional[Project]:
    """
    Get a project by ID.
    """
    return db.query(Project).filter(Project.id == project_id).first()


def get_project_documents(db: Session, project_id: int):
    """
    Get all documents for a project.
    """
    return db.query(ProjectDocument).filter(ProjectDocument.project_id == project_id).all()


def delete_project(db: Session, project_id: int) -> bool:
    """
    Delete a project and all related project documents.
    Returns True if deleted, False if project was not found.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return False

    db.query(ProjectDocument).filter(ProjectDocument.project_id == project_id).delete()
    db.delete(project)
    db.commit()
    return True

