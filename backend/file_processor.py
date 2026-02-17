import os
import re
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance
import pdfplumber
from playwright.async_api import async_playwright
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    
    # Try to auto-detect Tesseract on Windows
    import platform
    if platform.system() == 'Windows':
        common_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Tesseract-OCR\tesseract.exe',
        ]
        import os
        for path in common_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"Tesseract found at: {path}")
                break
        else:
            # Try to find it in PATH
            try:
                import shutil
                tesseract_path = shutil.which('tesseract')
                if tesseract_path:
                    pytesseract.pytesseract.tesseract_cmd = tesseract_path
                    print(f"Tesseract found in PATH: {tesseract_path}")
            except:
                pass
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Warning: pytesseract not available. OCR features will be disabled.")
from text_parser import parse_extracted_text
from column_type_analyzer import analyze_csv_columns
from openai_service import extract_fields_with_openai


def get_mime_type(ext):
    """Get MIME type from file extension"""
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp',
        '.svg': 'image/svg+xml'
    }
    return mime_types.get(ext.lower(), 'image/jpeg')


def preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
    """Apply basic preprocessing to improve OCR quality."""
    # Convert to grayscale
    processed = img.convert('L')

    # Resize very large images to a manageable size while preserving aspect ratio
    max_dim = 1600
    width, height = processed.size
    if max(width, height) > max_dim:
        scale = max_dim / float(max(width, height))
        new_size = (int(width * scale), int(height * scale))
        processed = processed.resize(new_size, Image.LANCZOS)

    # Apply a small median filter to reduce salt-and-pepper noise
    processed = processed.filter(ImageFilter.MedianFilter(size=3))

    # Increase contrast slightly to make text stand out
    enhancer = ImageEnhance.Contrast(processed)
    processed = enhancer.enhance(1.5)

    # Simple binary thresholding to sharpen text edges
# processed = processed.point(lambda p: 255 if p > 180 else 0)
def preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
    # Convert to grayscale
    processed = img.convert('L')

    # 🔥 Increase resolution (VERY IMPORTANT)
    width, height = processed.size
    processed = processed.resize((width * 2, height * 2), Image.LANCZOS)

    # Mild noise reduction
    processed = processed.filter(ImageFilter.MedianFilter(size=3))

    # Slight contrast boost
    enhancer = ImageEnhance.Contrast(processed)
    processed = enhancer.enhance(1.8)

    return processed


    return processed


async def process_file(file_path, mime_type):
    """
    Extract data from uploaded file based on file type
    """
    file_path_obj = Path(file_path)
    ext = file_path_obj.suffix.lower()
    stats = file_path_obj.stat()
    
    base_data = {
        'filename': file_path_obj.name,
        'fileSize': stats.st_size,
        'fileType': mime_type,
        'uploadDate': datetime.now().isoformat()
    }
    
    try:
        if ext == '.pdf':
            return await process_pdf(file_path, base_data)
        elif ext in ['.txt', '.md', '.json']:
            return await process_text_file(file_path, base_data)
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
            return await process_image(file_path, base_data)
        elif ext == '.csv':
            return await process_csv(file_path, base_data)
        else:
            return {
                **base_data,
                'error': 'Unsupported file type',
                'message': f'File type {ext} is not yet supported for data extraction'
            }
    except Exception as error:
        return {
            **base_data,
            'error': 'Processing error',
            'message': str(error)
        }


async def process_pdf(file_path, base_data):
    """Extract text and metadata from PDF"""
    try:
        text_content = ''
        metadata = {}
        pages = 0
        
        with pdfplumber.open(file_path) as pdf:
            pages = len(pdf.pages)
            
            # Extract text from all pages
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + '\n'
            
            # Extract metadata
            if pdf.metadata:
                metadata = {
                    'Title': pdf.metadata.get('Title', ''),
                    'Author': pdf.metadata.get('Author', ''),
                    'Subject': pdf.metadata.get('Subject', ''),
                    'Creator': pdf.metadata.get('Creator', ''),
                    'Producer': pdf.metadata.get('Producer', ''),
                    'CreationDate': str(pdf.metadata.get('CreationDate', '')),
                    'ModDate': str(pdf.metadata.get('ModDate', ''))
                }
        
        # Use OpenAI to extract structured fields from PDF text
        ai_extracted_data = None
        if text_content and len(text_content) > 0:
            try:
                ai_extracted_data = await extract_fields_with_openai(text_content)
            except Exception as ai_error:
                print(f'OpenAI extraction failed for PDF: {ai_error}')
        
        # Fallback: Use text parser if OpenAI extraction failed or is not available
        parsed_form_data = None
        if text_content and len(text_content) > 0:
            if ai_extracted_data:
                # Use AI extracted data if available
                parsed_form_data = ai_extracted_data
            else:
                # Fallback to regex-based text parser
                try:
                    parsed_form_data = parse_extracted_text(text_content)
                except Exception as parse_error:
                    print(f'Text parsing failed for PDF: {parse_error}')
        
        file_path_obj = Path(file_path)
        return {
            **base_data,
            'type': 'pdf',
            'title': metadata.get('Title') or file_path_obj.stem,
            'author': metadata.get('Author', ''),
            'subject': metadata.get('Subject', ''),
            'creator': metadata.get('Creator', ''),
            'producer': metadata.get('Producer', ''),
            'creationDate': metadata.get('CreationDate', ''),
            'modificationDate': metadata.get('ModDate', ''),
            'pages': pages,
            'text': text_content,
            'textLength': len(text_content),
            'metadata': metadata,
            'parsedFormData': parsed_form_data,
            'aiExtracted': bool(ai_extracted_data),
            'documentType': ai_extracted_data.get('documentType') if ai_extracted_data else None
        }
    except Exception as e:
        raise Exception(f'PDF processing failed: {str(e)}')


async def process_text_file(file_path, base_data):
    """Extract content from text files"""
    file_path_obj = Path(file_path)
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Try to parse as JSON if it's a .json file
    parsed_data = None
    if file_path_obj.suffix.lower() == '.json':
        try:
            import json
            parsed_data = json.loads(content)
        except:
            pass  # Not valid JSON, treat as text
    
    return {
        **base_data,
        'content': content,
        'contentLength': len(content),
        'lineCount': len(lines),
        'wordCount': len(content.split()),
        'parsedData': parsed_data,
        'firstLine': lines[0] if lines else '',
        'preview': content[:500]  # First 500 characters
    }


async def process_image(file_path, base_data):
    """Extract content and metadata from images using Playwright and OCR"""
    file_path_obj = Path(file_path)
    ext = file_path_obj.suffix.lower()
    mime_type = get_mime_type(ext)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        try:
            # Read image as base64
            with open(file_path, 'rb') as f:
                image_buffer = f.read()
            
            import base64
            image_base64 = base64.b64encode(image_buffer).decode('utf-8')
            data_url = f'data:{mime_type};base64,{image_base64}'
            
            # Create HTML page with the image
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        margin: 0;
                        padding: 20px;
                        background: white;
                    }}
                    img {{
                        max-width: 100%;
                        height: auto;
                    }}
                </style>
            </head>
            <body>
                <img id="targetImage" src="{data_url}" alt="Image to analyze" />
                <script>
                    window.imageInfo = {{
                        width: document.getElementById('targetImage').naturalWidth,
                        height: document.getElementById('targetImage').naturalHeight,
                        complete: document.getElementById('targetImage').complete
                    }};
                </script>
            </body>
            </html>
            """
            
            # Load the page with the image
            await page.set_content(html_content)
            await page.wait_for_load_state('networkidle')
            
            # Get image dimensions using Playwright
            image_info = await page.evaluate("""
                () => {
                    const img = document.getElementById('targetImage');
                    return {
                        width: img.naturalWidth || img.width,
                        height: img.naturalHeight || img.height,
                        displayWidth: img.width,
                        displayHeight: img.height
                    };
                }
            """)
            
            # Extract image type and format information
            image_type = ext.replace('.', '').upper()
            format_type = mime_type.split('/')[1].upper() if '/' in mime_type else image_type
            
            # Use Tesseract for OCR to extract text from image
            extracted_text = ''
            ocr_confidence = 0
            ocr_words = []
            ocr_error_message = None
            
            if not TESSERACT_AVAILABLE:
                ocr_error_message = (
                    'Tesseract OCR is not installed. '
                    'Download from: https://github.com/UB-Mannheim/tesseract/wiki '
                    'After installation, restart the server.'
                )
                extracted_text = ''
            else:
                try:
                    # Use PIL to open and preprocess image for pytesseract
                    with Image.open(file_path) as img:
                        preprocessed_img = preprocess_image_for_ocr(img)

                    # Run OCR on preprocessed image
                    ocr_data = pytesseract.image_to_data(
                        preprocessed_img,
                        lang='eng',
                        output_type=pytesseract.Output.DICT
                    )

                    # Extract text
                    extracted_text = pytesseract.image_to_string(
                        preprocessed_img,
                        lang='eng'
                    ).strip()
                    
                    # Calculate confidence and extract words
                    confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
                    ocr_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    # Extract word-level data
                    words = []
                    for i in range(len(ocr_data['text'])):
                        if int(ocr_data['conf'][i]) > 0:
                            words.append({
                                'text': ocr_data['text'][i],
                                'confidence': float(ocr_data['conf'][i]),
                                'bbox': {
                                    'x0': ocr_data['left'][i],
                                    'y0': ocr_data['top'][i],
                                    'x1': ocr_data['left'][i] + ocr_data['width'][i],
                                    'y1': ocr_data['top'][i] + ocr_data['height'][i]
                                }
                            })
                    ocr_words = words[:50]  # Limit to first 50 words
                    
                except Exception as ocr_error:
                    error_msg = str(ocr_error)
                    if 'tesseract' in error_msg.lower() or 'not found' in error_msg.lower() or 'not installed' in error_msg.lower():
                        ocr_error_message = (
                            'Tesseract OCR is not installed or not in your PATH. '
                            'Download from: https://github.com/UB-Mannheim/tesseract/wiki '
                            'During installation, check "Add to PATH" or note the installation path. '
                            'After installation, restart the server.'
                        )
                    else:
                        ocr_error_message = f'OCR processing failed: {error_msg}'
                    extracted_text = ''
                    print(f'OCR Error: {ocr_error}')
            
            # Get additional metadata using Playwright
            image_metadata = await page.evaluate("""
                () => {
                    const img = document.getElementById('targetImage');
                    return {
                        src: img.src.substring(0, 50) + '...',
                        alt: img.alt || '',
                        loading: img.loading || 'eager',
                        decoding: img.decoding || 'auto'
                    };
                }
            """)
            
            # Parse extracted text to generate structured form data (fallback method)
            # Only parse if we have extracted text and no OCR error
            parsed_form_data = None
            if extracted_text and len(extracted_text) > 0 and not ocr_error_message:
                parsed_form_data = parse_extracted_text(extracted_text)
            
            # Use OpenAI to extract structured fields (more accurate)
            ai_extracted_data = None
            if extracted_text and len(extracted_text) > 0 and not ocr_error_message:
                try:
                    ai_extracted_data = await extract_fields_with_openai(extracted_text)
                except Exception as ai_error:
                    print(f'OpenAI extraction failed: {ai_error}')
                    # Continue with fallback parsing
            
            aspect_ratio = (image_info['width'] / image_info['height']) if image_info['height'] > 0 else 0
            
            result = {
                **base_data,
                'imageUrl': f'/uploads/{file_path_obj.name}',
                'type': 'image',
                'imageType': image_type,
                'format': format_type,
                'mimeType': mime_type,
                'dimensions': {
                    'width': image_info['width'],
                    'height': image_info['height'],
                    'displayWidth': image_info['displayWidth'],
                    'displayHeight': image_info['displayHeight'],
                    'aspectRatio': f'{aspect_ratio:.2f}'
                },
                'extractedText': extracted_text,
                'textLength': len(extracted_text),
                'ocrConfidence': f'{ocr_confidence:.2f}%' if ocr_confidence > 0 else 'N/A',
                'ocrWordCount': len(ocr_words),
                'ocrWords': [
                    {
                        'text': w['text'],
                        'confidence': f"{w['confidence']:.2f}",
                        'bbox': w['bbox']
                    }
                    for w in ocr_words
                ],
                'metadata': image_metadata,
                'hasText': len(extracted_text) > 0,
                'parsedFormData': ai_extracted_data or parsed_form_data,
                'aiExtracted': bool(ai_extracted_data),
                'documentType': ai_extracted_data.get('documentType') if ai_extracted_data else None
            }
            
            # Add OCR error message if OCR failed
            if ocr_error_message:
                result['ocrError'] = ocr_error_message
                result['warning'] = 'OCR is not available. Image metadata was extracted, but text extraction requires Tesseract OCR installation.'
            
            return result
            
        except Exception as error:
            print(f'Image processing error: {error}')
            return {
                **base_data,
                'type': 'image',
                'error': 'Image processing failed',
                'message': str(error)
            }
        finally:
            await browser.close()


async def process_csv(file_path, base_data):
    """Parse CSV files"""
    import csv
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        # Try to detect delimiter
        sample = f.read(1024)
        f.seek(0)
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter
        
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = list(reader)
    
    if not rows:
        return {
            **base_data,
            'error': 'Empty CSV file',
            'rows': []
        }
    
    headers = list(rows[0].keys()) if rows else []
    
    # Analyze column types for form generation
    column_types = analyze_csv_columns(headers, rows)
    
    # Get first row data for pre-filling form
    first_row_data = rows[0] if rows else {}
    
    return {
        **base_data,
        'type': 'csv',
        'headers': headers,
        'rows': rows,
        'rowCount': len(rows),
        'columnCount': len(headers),
        'preview': rows[:10],  # First 10 rows as preview
        'columnTypes': column_types,
        'firstRowData': first_row_data
    }



