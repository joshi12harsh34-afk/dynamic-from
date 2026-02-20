# database.py
"""
Database models and setup for storing real estate project data.
Uses SQLAlchemy with SQLite for simplicity (can be migrated to PostgreSQL/MySQL).
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import os
from pathlib import Path

Base = declarative_base()


class Project(Base):
    """
    Main project table storing the complete project JSON structure.
    Uses JSON column to store nested data structure.
    """
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(500), nullable=True, index=True)
    tagline = Column(String(1000), nullable=True)
    logo = Column(String(1000), nullable=True)
    brand_name = Column(String(500), nullable=True)
    
    # Store nested JSON structures as JSON columns
    hero_section = Column(JSON, nullable=True)
    about = Column(JSON, nullable=True)
    location = Column(JSON, nullable=True)
    amenities = Column(JSON, nullable=True)  # Array
    amenity_categories = Column(JSON, nullable=True)  # Array
    tower_amenities = Column(JSON, nullable=True)  # Array
    gallery = Column(JSON, nullable=True)  # Array
    gallery_categories = Column(JSON, nullable=True)  # Array
    floor_plans = Column(JSON, nullable=True)  # Array
    pricing = Column(JSON, nullable=True)  # Array
    project_highlights = Column(JSON, nullable=True)  # Array
    project_info = Column(JSON, nullable=True)
    site_plan = Column(JSON, nullable=True)
    developer = Column(JSON, nullable=True)
    contact = Column(JSON, nullable=True)
    legal_info = Column(JSON, nullable=True)
    seo = Column(JSON, nullable=True)
    navigation = Column(JSON, nullable=True)
    cta_sections = Column(JSON, nullable=True)  # Array
    international_architects = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert project to dictionary matching the JSON structure"""
        return {
            "id": self.id,
            "project_name": self.project_name,
            "tagline": self.tagline,
            "logo": self.logo,
            "brand_name": self.brand_name,
            "hero_section": self.hero_section or {},
            "about": self.about or {},
            "location": self.location or {},
            "amenities": self.amenities or [],
            "amenity_categories": self.amenity_categories or [],
            "tower_amenities": self.tower_amenities or [],
            "gallery": self.gallery or [],
            "gallery_categories": self.gallery_categories or [],
            "floor_plans": self.floor_plans or [],
            "pricing": self.pricing or [],
            "project_highlights": self.project_highlights or [],
            "project_info": self.project_info or {},
            "site_plan": self.site_plan or {},
            "developer": self.developer or {},
            "contact": self.contact or {},
            "legal_info": self.legal_info or {},
            "seo": self.seo or {},
            "navigation": self.navigation or {},
            "cta_sections": self.cta_sections or [],
            "international_architects": self.international_architects or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ProjectDocument(Base):
    """
    Table to track documents associated with projects.
    """
    __tablename__ = 'project_documents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False, index=True)
    document_type = Column(String(100), nullable=True)  # 'pdf', 'image', 'url', etc.
    document_path = Column(String(1000), nullable=True)  # File path or URL
    document_name = Column(String(500), nullable=True)
    extracted_data = Column(JSON, nullable=True)  # Extracted data from document
    created_at = Column(DateTime, default=datetime.utcnow)


# Database setup
DB_DIR = Path(__file__).parent / 'data'
DB_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_DIR / 'projects.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

