# Dynamic Scraper Form

A web application that extracts structured data from files (PDF, images, CSV, text) and URLs, then generates dynamic forms for easy editing.

## Features

- **File Upload & Processing**: Supports PDF, images (JPG, PNG, GIF, WebP, BMP), CSV, and text files
- **OCR Text Extraction**: Extracts text from images using Tesseract OCR with image preprocessing
- **Advanced Web Scraping**: Enhanced scraping with:
  - Real estate-specific data extraction (prices, BHK, location, developer info, RERA numbers)
  - Hero section, navigation menu, and page sections extraction
  - Google Maps integration detection
  - Floor plan detection
  - Lazy-loaded image extraction
  - JSON-LD structured data parsing
- **AI-Powered Extraction**: Uses OpenAI to intelligently extract structured fields from documents
  - **Token-Optimized**: Compact JSON schema format reduces token usage by 60-80%
  - Real estate project extraction with comprehensive schema
  - General document field extraction
- **Dynamic Form Generation**: Automatically generates editable forms from extracted data
- **Database-backed Projects**:
  - Stores extracted data in SQLite using SQLAlchemy
  - Supports explicit project creation from extracted results (`Save as Project`)
  - Supports project-scoped merge/update from left panel actions (`Fetch` / `Doc`)
  - Supports project listing, view, update, fetch-website merge, add-document merge, and delete
- **Professional Dashboard UI**:
  - Two-column layout (projects on left, extractor/results on right)
  - Built-in project actions: Fetch, Add Document, View, Delete

## Tech Stack

- **Backend**: Python (FastAPI)
- **Frontend**: Vanilla JavaScript (HTML/CSS/JS)
- **Database**: SQLite + SQLAlchemy ORM
- **OCR**: Tesseract OCR (via pytesseract)
- **PDF Processing**: pdfplumber
- **Web Scraping**: Playwright
- **AI**: OpenAI API (optional)

## Technical Flow (End-to-End)

1. **Extract stage (no DB write yet)**
   - URL flow: `frontend/app.js` -> `POST /api/scrape` -> `backend/scraper.py`
   - File flow: `frontend/app.js` -> `POST /api/upload` -> `backend/file_processor.py`
   - Response is rendered as dynamic form in the right panel.

2. **`AI + parser stage (for PDFs/images when enabled)**
   - PDFs: text extrac`tion (`pdfplumber`) -> real-estate LLM extraction (`extract_real_estate_project`) -> parser fallback (`parse_extracted_text`) -> generic LLM extraction (`extract_fields_with_openai`) fallback.
   - Images: OCR (`pytesseract`) -> parser (`parse_extracted_text`) -> generic LLM extraction fallback.
   - Best available structured payload is returned as `parsedFormData`.

3. **Mapping stage (schema normalization)**
   - `backend/data_mapper.py` maps extracted payloads to the project schema.
   - Supports:
     - Full nested project-schema payloads from LLM
     - Section-based label/value payloads
     - Raw key-value text lines (`label: value` and `label = value`)

4. **Persistence stage**
   - Create new project: `POST /api/projects` (used by **Save as Project**)
   - Update existing project: `PUT /api/projects/{id}` or scoped merge endpoints:
     - `POST /api/projects/{id}/fetch-website`
     - `POST /api/projects/{id}/add-document`
   - Upsert behavior updates only null/empty existing fields (`db_utils.py`).

5. **Read/list stage**
   - Sidebar loads from `GET /api/projects`
   - Full project view comes from `GET /api/projects/{id}` with related documents.

## Prerequisites

1. **Python 3.8+**
2. **Tesseract OCR** (for image text extraction)
   - Windows: Download from [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
   - See `backend/INSTALL_TESSERACT.md` for detailed instructions

## Installation

1. **Install Python dependencies:**
   ```bash
   python -m pip install -r requirements.txt
   ```

2. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

3. **Install Tesseract OCR:**
   - See `backend/INSTALL_TESSERACT.md` for installation instructions
   - The backend will auto-detect Tesseract if installed in common locations

4. **Set up environment variables** (optional):
   Create a `.env` file in the `backend` directory:
   ```
   OPENAI_API_KEY=your_api_key_here  # Optional, for AI extraction
   PORT=3000  # Optional, defaults to 3000
   ```

## Running the Application

1. **Start the backend server:**
   ```bash
   cd backend
   python app.py
   ```
   
   Or using uvicorn directly:
   ```bash
   cd backend
   uvicorn app:app --host 0.0.0.0 --port 3000 --reload
   ```

2. **Open the frontend:**
   - Open `frontend/index.html` in your web browser
   - Or serve it using a local web server

The backend will be available at `http://localhost:3000`

## API Endpoints

- `POST /api/scrape` - Scrape a URL and extract metadata
  - Returns: URL metadata, images, Open Graph data, JSON-LD structured data
  - For real estate pages: Also returns hero section, navigation, sections, Google Maps, floor plans, and real estate-specific data (price, BHK, location, developer, RERA, etc.)
- `POST /api/upload` - Upload and process a file
  - Returns extracted payload (`parsedFormData`, OCR/text/meta depending on file type)
- `GET /api/projects` - List projects (most recently updated first)
- `GET /api/projects/{project_id}` - Get a project with related documents
- `POST /api/projects` - Create a project manually / from mapped payload
- `PUT /api/projects/{project_id}` - Upsert project (updates only null/empty values)
- `DELETE /api/projects/{project_id}` - Delete a project and its related project documents
- `POST /api/projects/{project_id}/fetch-website` - Scrape URL and merge into existing project
- `POST /api/projects/{project_id}/add-document` - Upload file, extract, and merge into existing project
- `GET /uploads/<filename>` - Serve uploaded files
- `GET /docs` - FastAPI interactive API documentation (Swagger UI)

## Project Structure

```
.
├── backend/
│   ├── app.py                 # Main FastAPI server
│   ├── database.py            # SQLAlchemy DB models and connection setup
│   ├── db_utils.py            # Project CRUD/upsert/delete DB utilities
│   ├── data_mapper.py         # Maps scraped/extracted payloads to project schema
│   ├── file_processor.py      # File processing logic
│   ├── scraper.py             # Web scraping
│   ├── text_parser.py         # Text parsing and field extraction
│   ├── column_type_analyzer.py # CSV column analysis
│   ├── openai_service.py      # OpenAI integration
│   ├── uploads/               # Uploaded files storage
│   ├── data/                  # SQLite database folder (projects.db)
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── index.html            # Main HTML file
│   └── app.js                # Frontend JavaScript
└── requirements.txt          # Python dependencies (root)
```

## Usage & Processing Workflow

1. **Extract from URL:**
   - Enter a URL in the input field
   - Click "Fetch" to scrape metadata
   - Review/edit extracted output in the right panel
   - Click **Save as Project** if you want to persist as a new project row
   - The scraper automatically detects page type (real estate, product, article, etc.)
   - For real estate pages, extracts:
     - Project name, price, BHK configuration, area
     - Location details (address, city, state, pincode)
     - Developer/builder information
     - RERA number and possession date
     - Amenities and project status
     - Contact information (phone, email)
     - Hero section, navigation menu, page sections
     - Google Maps embed URL
     - Floor plans detected from text

2. **Extract from File:**
   - Click the upload area or drag and drop a file
   - Supported formats: PDF, images, CSV, TXT, JSON, MD
   - Click "Extract Data" to process
   - View/edit extracted data in the generated form
   - Click **Save as Project** if you want to persist as a new project row

3. **Manage projects (left panel):**
   - **View**: Load a project into Extracted Data panel
   - **Fetch**: Scrape a website and merge missing fields into that project
   - **Doc**: Upload document and merge missing fields
   - **Delete**: Remove project and related project documents

### Backend workflow (high level)

- **URL Scraping** (`scraper.py`)
  - Uses Playwright to load pages with multiple wait strategies for reliability
  - Extracts basic metadata (title, description, images)
  - Detects page type using JSON-LD structured data, URL patterns, and text content
  - For real estate pages, uses three extraction strategies:
    1. **DOM-based extraction**: Common CSS selectors for project name, price, location, developer
    2. **Text parsing**: Regex patterns for BHK, prices, RERA numbers, dates, contact info
    3. **Structured data**: JSON-LD Schema.org format (most reliable)
  - Extracts page structure: hero section, navigation menu, sections, Google Maps
  - Handles lazy-loaded images and responsive images (srcset)

- **PDF files**
  - Extract text with `pdfplumber`
  - Try **real-estate–specific extraction** with OpenAI (`extract_real_estate_project`)
    - Uses compact JSON schema format to reduce token usage by 60-80%
    - Comprehensive real estate project schema with 50+ fields
  - Run the **regex/text parser** (`parse_extracted_text`) to build structured fields
  - Convert parsed fields to clean `label: value` lines
  - Send this **parser text** to OpenAI (`extract_fields_with_openai`) for final, cleaner JSON (if AI is enabled)
    - Also uses compact schema format for token optimization
  - The best available result (real-estate JSON → generic AI JSON → parser-only JSON) is returned as `parsedFormData`

- **Image files**
  - Preprocess image (grayscale, resize, denoise, enhance contrast) for better OCR
  - Run OCR with Tesseract (via `pytesseract`)
  - Parse the OCR text with `parse_extracted_text` into structured fields
  - Convert parsed fields to **parser text** and send that to OpenAI (if enabled)
  - Response is merged back into the final `parsedFormData`

- **CSV files**
  - Read with `csv.DictReader`
  - Infer column types with `column_type_analyzer.py`
  - Use the first row as initial form values

- **Text / JSON files**
  - Raw content is returned, with JSON additionally parsed when possible

## Notes

- **OCR Features**: Require Tesseract OCR to be installed. Without it, image processing will still work but text extraction will be disabled.
- **AI Extraction**: Requires OpenAI API key. Without it, the system uses only the regex/text parser (`parse_extracted_text`) to build forms.
  - **Token Optimization**: The system uses compact JSON schema format (dot notation) instead of full JSON, reducing token usage by 60-80% while maintaining extraction accuracy.
- **Web Scraping**: 
  - Handles dynamic content loading (SPAs, React, Vue apps)
  - Supports lazy-loaded images and responsive images
  - Automatically detects real estate pages and extracts specialized data
  - Uses realistic user agent to avoid bot detection
- **Database behavior**:
  - `POST /api/scrape` and `POST /api/upload` only return extraction output (no automatic DB insert)
  - New row is created via `POST /api/projects` (frontend: **Save as Project**)
  - Project merge/update endpoints update only null/empty values
- **File Size Limit**: Maximum file size is 50MB
- **Real Estate Extraction**: 
  - Extracts Indian real estate specific data (RERA numbers, BHK, lakh/crore pricing)
  - Supports major Indian cities detection
  - Handles multiple price formats (₹, $, €, £) and Indian formats (lakh, crore)

## Troubleshooting

- **OCR not working**: See `backend/INSTALL_TESSERACT.md`
- **Server won't start**: Check that port 3000 is not in use
- **OpenBLAS / NumPy memory errors on Windows**: The backend sets `OPENBLAS_NUM_THREADS=1` (and related BLAS vars) in `backend/app.py` to avoid memory allocation errors. If you see OpenBLAS allocation errors, ensure you are starting the server via `python app.py` so these settings are applied.
- **Import errors**: Make sure all Python dependencies are installed
- **Web scraping timeout**: The scraper uses multiple wait strategies. If a page times out, it will try `networkidle`, then `load`, then `domcontentloaded`. Very slow pages may still fail.
- **Real estate data not extracted**: 
  - Ensure the page is detected as "real_estate" type (check the returned `type` field)
  - Some sites may use non-standard HTML structures that aren't covered by the selectors
  - Check if the page has JSON-LD structured data (most reliable source)
- **OpenAI API errors**: 
  - Verify your API key is set correctly in `.env` file
  - Check your OpenAI account has sufficient credits
  - The compact schema format helps reduce costs significantly



Frontend (Dashboard UI)
        │
        ▼
FastAPI Backend
        │
        ├── Scraper Service (Playwright)
        │
        ├── File Processor
        │       ├── PDF Parser
        │       ├── OCR (Tesseract)
        │       └── CSV/Text parser
        │
        ├── AI Extraction Layer
        │       ├── Real Estate Extractor
        │       └── Generic Field Extractor
        │
        ├── Data Mapper (Normalize to Schema)
        │
        ├── Upsert Engine
        │
        ▼
Database (SQLite / PostgreSQL)
        │
        ▼
Dynamic Form Renderer