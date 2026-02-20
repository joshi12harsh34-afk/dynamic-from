# Database Implementation Guide

## Overview

The application now includes a comprehensive database system for storing and managing real estate project data. The database uses SQLite (can be migrated to PostgreSQL/MySQL) with SQLAlchemy ORM.

## Database Structure

### Projects Table
Stores complete project information matching the provided JSON schema:
- Basic info: `project_name`, `tagline`, `logo`, `brand_name`
- Nested JSON fields: `hero_section`, `about`, `location`, `amenities`, `gallery`, `floor_plans`, `pricing`, `developer`, `contact`, `legal_info`, `seo`, `navigation`, etc.
- Metadata: `created_at`, `updated_at`

### Project Documents Table
Tracks documents associated with projects:
- `project_id`: Foreign key to projects
- `document_type`: Type of document (pdf, image, url, etc.)
- `document_path`: File path or URL
- `document_name`: Original filename
- `extracted_data`: JSON of extracted data
- `created_at`: Timestamp

## Key Features

### 1. Smart Upsert Logic
The `upsert_project` function implements intelligent merging:
- **Only updates null/empty values** - Existing data is preserved
- **Deep merging** - Recursively merges nested dictionaries
- **Array merging** - Appends unique items to arrays
- **Automatic detection** - Finds existing projects by name

### 2. Data Mapping
Automatic conversion from scraped/extracted data to project schema:
- **Scraped URL data** → Project schema (via `map_scraped_data_to_project`)
- **File extracted data** → Project schema (via `map_extracted_data_to_project`)

## API Endpoints

### List Projects
```
GET /api/projects?skip=0&limit=100
```
Returns paginated list of all projects.

### Get Project
```
GET /api/projects/{project_id}
```
Returns project details including associated documents.

### Create Project
```
POST /api/projects
Body: { "project_data": {...} }
```
Creates a new project. Automatically maps scraped/extracted data if needed.

### Update Project
```
PUT /api/projects/{project_id}
Body: { "project_data": {...} }
```
Updates project using smart upsert (only updates null/empty values).

### Fetch Website for Project
```
POST /api/projects/{project_id}/fetch-website
Body: { "url": "...", "multi_page": false, "max_pages": 5 }
```
Fetches data from a website and merges it into the project (upsert).

### Add Document to Project
```
POST /api/projects/{project_id}/add-document
Body: FormData with file
```
Uploads a document, extracts data, and merges it into the project (upsert).

## Frontend Features

### Projects Listing
- View all projects with key information
- Quick actions: Fetch Website, Add Document, View Details

### Project Actions
1. **Fetch Website**: Enter a URL to scrape and merge data
2. **Add Document**: Upload a file (PDF, image, etc.) and merge extracted data
3. **View**: View and edit project details

### Save as Project
After extracting data from URL or file, click "Save as Project" to create a new project entry.

## Usage Example

1. **Create a project from URL:**
   - Enter URL in "Extract from URL" section
   - Click "Fetch"
   - Click "Save as Project"

2. **Add more data to existing project:**
   - Click "View All Projects"
   - Find your project
   - Click "Fetch Website" or "Add Document"
   - New data will be merged (only null/empty fields updated)

3. **View project details:**
   - Click "View" on any project card
   - See all project data in editable form

## Database Location

Database file: `backend/data/projects.db`

The database is automatically initialized on first run. The `data/` directory is created automatically.

## Migration Notes

To migrate to PostgreSQL or MySQL:
1. Change `DATABASE_URL` in `backend/database.py`
2. Install appropriate database driver (psycopg2 for PostgreSQL, pymysql for MySQL)
3. Update connection string format

Example for PostgreSQL:
```python
DATABASE_URL = "postgresql://user:password@localhost/dbname"
```

## Notes

- The upsert logic ensures data integrity - existing values are never overwritten
- Only null, empty strings, empty dicts, and empty arrays are considered "empty"
- Deep merging handles nested structures intelligently
- Array merging appends unique items only

