# app.py
import os

# Fix OpenBLAS memory allocation errors on Windows
# Set these environment variables BEFORE importing any libraries that use NumPy/OpenBLAS
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['GOTO_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
import dotenv
import traceback

from scraper import scrape_url
from file_processor import process_file
from database import init_db, get_db
from db_utils import (
    upsert_project, add_project_document, get_all_projects,
    get_project_by_id, get_project_documents, delete_project
)
from data_mapper import map_scraped_data_to_project, map_extracted_data_to_project

# Load environment variables
dotenv.load_dotenv()

# Initialize database
init_db()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure upload settings
UPLOAD_FOLDER = Path(__file__).parent / 'uploads'
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Ensure uploads directory exists
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Mount static files for serving uploads
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_FOLDER)), name="uploads")


# Add exception handler to ensure all errors return JSON
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler to ensure JSON responses"""
    error_trace = traceback.format_exc()
    print(f"Unhandled exception: {error_trace}")
    return JSONResponse(
        status_code=500,
        content={'error': 'Internal server error', 'message': str(exc)}
    )


class ScrapeRequest(BaseModel):
    url: str
    multi_page: bool = False  # Optional: enable multi-page crawling
    max_pages: int = 5  # Optional: maximum pages to crawl if multi_page=True


class ProjectCreateRequest(BaseModel):
    project_data: dict


class ProjectUpdateRequest(BaseModel):
    project_id: Optional[int] = None
    project_data: dict


class WebsiteFetchRequest(BaseModel):
    url: str
    multi_page: bool = False
    max_pages: int = 5


@app.post('/api/scrape')
async def scrape(request: ScrapeRequest):
    """
    Scrape URL endpoint
    
    Supports both single-page and multi-page crawling:
    - Single-page (default): Fast scraping of the main page
    - Multi-page: Crawls related internal pages for comprehensive data extraction
    """
    if not request.url:
        return JSONResponse(
            status_code=400,
            content={'error': 'URL is required', 'message': 'URL is required'}
        )
    
    try:
        result = await scrape_url(request.url, multi_page=request.multi_page, max_pages=request.max_pages)
        return JSONResponse(content=result)
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error scraping URL: {error_trace}")
        return JSONResponse(
            status_code=500,
            content={'error': 'Scraping failed', 'message': str(e)}
        )


@app.post('/api/upload')
async def upload_file(file: UploadFile = File(...)):
    """File upload endpoint"""
    if not file.filename:
        return JSONResponse(
            status_code=400,
            content={'error': 'No file selected', 'message': 'No file selected'}
        )
    
    file_path = None
    try:
        # Generate unique filename
        timestamp = int(datetime.now().timestamp() * 1000)
        random_suffix = os.urandom(4).hex()
        ext = Path(file.filename).suffix
        filename = f"{timestamp}-{random_suffix}{ext}"
        
        # Save file
        file_path = UPLOAD_FOLDER / filename
        with open(file_path, 'wb') as f:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={'error': 'File too large', 'message': 'Maximum file size is 50MB'}
                )
            f.write(content)
        
        # Get MIME type
        mime_type = file.content_type or 'application/octet-stream'
        
        # Process file
        extracted_data = await process_file(str(file_path), mime_type)
        return JSONResponse(content=extracted_data)
        
    except Exception as e:
        # Clean up uploaded file on error
        if file_path and file_path.exists():
            try:
                file_path.unlink()
            except:
                pass
        
        # Log the full error for debugging
        error_trace = traceback.format_exc()
        print(f"Error processing file: {error_trace}")
        
        return JSONResponse(
            status_code=500,
            content={
                'error': 'File processing failed',
                'message': str(e)
            }
        )


# ==================== PROJECT MANAGEMENT ENDPOINTS ====================

@app.get('/api/projects')
async def list_projects(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    """
    List all projects with pagination (default limit 1000 to show all projects).
    Projects are ordered by most recent first.
    """
    try:
        projects = get_all_projects(db, skip=skip, limit=limit)
        return JSONResponse(content={
            'projects': [p.to_dict() for p in projects],
            'total': len(projects)
        })
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error listing projects: {error_trace}")
        return JSONResponse(
            status_code=500,
            content={'error': 'Failed to list projects', 'message': str(e)}
        )


@app.get('/api/projects/{project_id}')
async def get_project(project_id: int, db: Session = Depends(get_db)):
    """
    Get a specific project by ID.
    """
    try:
        project = get_project_by_id(db, project_id)
        if not project:
            return JSONResponse(
                status_code=404,
                content={'error': 'Project not found', 'message': f'Project with id {project_id} not found'}
            )
        
        # Get documents for this project
        documents = get_project_documents(db, project_id)
        
        project_dict = project.to_dict()
        project_dict['documents'] = [
            {
                'id': doc.id,
                'document_type': doc.document_type,
                'document_name': doc.document_name,
                'document_path': doc.document_path,
                'created_at': doc.created_at.isoformat() if doc.created_at else None
            }
            for doc in documents
        ]
        
        return JSONResponse(content=project_dict)
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error getting project: {error_trace}")
        return JSONResponse(
            status_code=500,
            content={'error': 'Failed to get project', 'message': str(e)}
        )


@app.post('/api/projects')
async def create_project(request: ProjectCreateRequest, db: Session = Depends(get_db)):
    """
    Create a new project.
    Automatically maps scraped data to project schema if needed.
    """
    try:
        project_data = request.project_data
        
        # Remove metadata fields if present (from database responses)
        metadata_fields = ['id', 'created_at', 'updated_at', 'documents']
        for field in metadata_fields:
            project_data.pop(field, None)
        
        # IMPORTANT: file extraction payloads often include `type: "pdf"|"image"|...`.
        # We must NOT treat those as scraped-website payloads, otherwise we wipe nested fields
        # like `about`, `location`, etc. Prefer extracted-file mapping when parsedFormData/text exists.
        if project_data.get('parsedFormData') or project_data.get('extractedText') or project_data.get('text'):
            print(f"Mapping extracted file data to project schema...")
            project_data = map_extracted_data_to_project(project_data)
        # Check if this is scraped data format (has url, realEstateData, etc.)
        elif project_data.get('url') or project_data.get('realEstateData'):
            print(f"Mapping scraped data to project schema...")
            project_data = map_scraped_data_to_project(project_data)
        # Check if it's already in project schema format (has hero_section, about, location, etc.)
        elif project_data.get('hero_section') or project_data.get('about') or project_data.get('location'):
            print(f"Data already in project schema format, using as-is...")
            # Already in correct format, use as-is
        else:
            print(f"Warning: Unknown data format, attempting to use as-is...")
            print(f"Data keys: {list(project_data.keys())[:10]}")
        
        project = upsert_project(db, project_data)
        return JSONResponse(content={
            'message': 'Project created successfully',
            'project': project.to_dict()
        }, status_code=201)
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error creating project: {error_trace}")
        return JSONResponse(
            status_code=500,
            content={'error': 'Failed to create project', 'message': str(e)}
        )


@app.put('/api/projects/{project_id}')
async def update_project(project_id: int, request: ProjectUpdateRequest, db: Session = Depends(get_db)):
    """
    Update a project (upsert - only updates null/empty values).
    """
    try:
        if request.project_id is not None and request.project_id != project_id:
            return JSONResponse(
                status_code=400,
                content={'error': 'Project ID mismatch', 'message': 'Path project_id and body project_id must match'}
            )
        project = upsert_project(db, request.project_data, project_id=project_id)
        return JSONResponse(content={
            'message': 'Project updated successfully',
            'project': project.to_dict()
        })
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content={'error': 'Project not found', 'message': str(e)}
        )
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error updating project: {error_trace}")
        return JSONResponse(
            status_code=500,
            content={'error': 'Failed to update project', 'message': str(e)}
        )


@app.delete('/api/projects/{project_id}')
async def remove_project(project_id: int, db: Session = Depends(get_db)):
    """
    Delete a project and its related project documents.
    """
    try:
        deleted = delete_project(db, project_id)
        if not deleted:
            return JSONResponse(
                status_code=404,
                content={'error': 'Project not found', 'message': f'Project with id {project_id} not found'}
            )

        return JSONResponse(content={
            'message': 'Project deleted successfully',
            'project_id': project_id
        })
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error deleting project: {error_trace}")
        return JSONResponse(
            status_code=500,
            content={'error': 'Failed to delete project', 'message': str(e)}
        )


@app.post('/api/projects/{project_id}/fetch-website')
async def fetch_website_for_project(project_id: int, request: WebsiteFetchRequest, db: Session = Depends(get_db)):
    """
    Fetch data from a website and upsert into an existing project.
    Only updates null/empty values in the project.
    """
    try:
        
        # Verify project exists
        project = get_project_by_id(db, project_id)
        if not project:
            return JSONResponse(
                status_code=404,
                content={'error': 'Project not found', 'message': f'Project with id {project_id} not found'}
            )
        
        # Scrape the website
        scraped_data = await scrape_url(request.url, multi_page=request.multi_page, max_pages=request.max_pages)
        
        # Map scraped data to project schema
        mapped_data = map_scraped_data_to_project(scraped_data)
        
        # Upsert the project (only updates null/empty values)
        updated_project = upsert_project(db, mapped_data, project_id=project_id)
        
        # Add document record
        add_project_document(
            db=db,
            project_id=project_id,
            document_type='url',
            document_path=request.url,
            document_name=f"Website: {request.url}",
            extracted_data=scraped_data
        )
        
        return JSONResponse(content={
            'message': 'Website data fetched and merged successfully',
            'project': updated_project.to_dict(),
            'scraped_data': scraped_data
        })
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error fetching website for project: {error_trace}")
        return JSONResponse(
            status_code=500,
            content={'error': 'Failed to fetch website', 'message': str(e)}
        )


@app.post('/api/projects/{project_id}/add-document')
async def add_document_to_project(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Add a document to a project, extract data, and upsert into project.
    Only updates null/empty values in the project.
    """
    try:
        
        # Verify project exists
        project = get_project_by_id(db, project_id)
        if not project:
            return JSONResponse(
                status_code=404,
                content={'error': 'Project not found', 'message': f'Project with id {project_id} not found'}
            )
        
        if not file.filename:
            return JSONResponse(
                status_code=400,
                content={'error': 'No file selected', 'message': 'No file selected'}
            )
        
        file_path = None
        try:
            # Generate unique filename
            timestamp = int(datetime.now().timestamp() * 1000)
            random_suffix = os.urandom(4).hex()
            ext = Path(file.filename).suffix
            filename = f"{timestamp}-{random_suffix}{ext}"
            
            # Save file
            file_path = UPLOAD_FOLDER / filename
            with open(file_path, 'wb') as f:
                content = await file.read()
                if len(content) > MAX_FILE_SIZE:
                    return JSONResponse(
                        status_code=413,
                        content={'error': 'File too large', 'message': 'Maximum file size is 50MB'}
                    )
                f.write(content)
            
            # Get MIME type
            mime_type = file.content_type or 'application/octet-stream'
            
            # Process file
            extracted_data = await process_file(str(file_path), mime_type)
            
            # Map extracted data to project schema (supports parsed fields + OCR text key-value lines)
            mapped_data = map_extracted_data_to_project(extracted_data)
            
            # Upsert the project (only updates null/empty values)
            updated_project = upsert_project(db, mapped_data, project_id=project_id)
            
            # Add document record
            doc = add_project_document(
                db=db,
                project_id=project_id,
                document_type=extracted_data.get('fileType', 'unknown'),
                document_path=f"/uploads/{filename}",
                document_name=file.filename,
                extracted_data=extracted_data
            )
            
            return JSONResponse(content={
                'message': 'Document added and data merged successfully',
                'project': updated_project.to_dict(),
                'document': {
                    'id': doc.id,
                    'document_type': doc.document_type,
                    'document_name': doc.document_name,
                    'document_path': doc.document_path
                },
                'extracted_data': extracted_data
            })
            
        except Exception as e:
            # Clean up uploaded file on error
            if file_path and file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass
            raise e
            
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error adding document to project: {error_trace}")
        return JSONResponse(
            status_code=500,
            content={'error': 'Failed to add document', 'message': str(e)}
        )


if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 3000))
    print(f'Server running on port {port}')
    uvicorn.run(app, host='0.0.0.0', port=port)

