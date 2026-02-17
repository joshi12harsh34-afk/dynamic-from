import os
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import dotenv
import traceback

from scraper import scrape_url
from file_processor import process_file

# Load environment variables
dotenv.load_dotenv()

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


@app.post('/api/scrape')
async def scrape(request: ScrapeRequest):
    """Scrape URL endpoint"""
    if not request.url:
        return JSONResponse(
            status_code=400,
            content={'error': 'URL is required', 'message': 'URL is required'}
        )
    
    try:
        result = await scrape_url(request.url)
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


if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 3000))
    print(f'Server running on port {port}')
    uvicorn.run(app, host='0.0.0.0', port=port)

