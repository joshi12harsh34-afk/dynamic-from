# Dynamic Scraper Form

A web application that extracts structured data from files (PDF, images, CSV, text) and URLs, then generates dynamic forms for easy editing.

## Features

- **File Upload & Processing**: Supports PDF, images (JPG, PNG, GIF, WebP, BMP), CSV, and text files
- **OCR Text Extraction**: Extracts text from images using Tesseract OCR
- **Web Scraping**: Scrapes metadata from URLs
- **AI-Powered Extraction**: Uses OpenAI to intelligently extract structured fields from documents
- **Dynamic Form Generation**: Automatically generates editable forms from extracted data

## Tech Stack

- **Backend**: Python (FastAPI)
- **Frontend**: Vanilla JavaScript (HTML/CSS/JS)
- **OCR**: Tesseract OCR (via pytesseract)
- **PDF Processing**: pdfplumber
- **Web Scraping**: Playwright
- **AI**: OpenAI API (optional)

## Prerequisites

1. **Python 3.8+**
2. **Tesseract OCR** (for image text extraction)
   - Windows: Download from [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
   - See `backend/INSTALL_TESSERACT.md` for detailed instructions

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
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
- `POST /api/upload` - Upload and process a file
- `GET /uploads/<filename>` - Serve uploaded files
- `GET /docs` - FastAPI interactive API documentation (Swagger UI)

## Project Structure

```
.
├── backend/
│   ├── app.py                 # Main FastAPI server
│   ├── file_processor.py      # File processing logic
│   ├── scraper.py             # Web scraping
│   ├── text_parser.py         # Text parsing and field extraction
│   ├── column_type_analyzer.py # CSV column analysis
│   ├── openai_service.py      # OpenAI integration
│   ├── uploads/               # Uploaded files storage
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── index.html            # Main HTML file
│   └── app.js                # Frontend JavaScript
└── requirements.txt          # Python dependencies (root)
```

## Usage

1. **Extract from URL:**
   - Enter a URL in the input field
   - Click "Fetch" to scrape metadata

2. **Extract from File:**
   - Click the upload area or drag and drop a file
   - Supported formats: PDF, images, CSV, TXT, JSON, MD
   - Click "Extract Data" to process
   - View extracted data in the generated form

## Notes

- **OCR Features**: Require Tesseract OCR to be installed. Without it, image processing will still work but text extraction will be disabled.
- **AI Extraction**: Requires OpenAI API key. Without it, the system falls back to regex-based text parsing.
- **File Size Limit**: Maximum file size is 50MB

## Troubleshooting

- **OCR not working**: See `backend/INSTALL_TESSERACT.md`
- **Server won't start**: Check that port 3000 is not in use
- **Import errors**: Make sure all Python dependencies are installed

