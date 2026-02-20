# text_parser.py
"""
Regex-based OCR text parser for structured document extraction.
Optimized for Indian real estate brochures and documents.
"""
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union


# Pre-compiled regex patterns for different data types
# Optimized for Indian real estate documents
PATTERNS = {
    # Price patterns - enhanced for Indian currency formats
    'price': re.compile(
        r'(₹|INR|RS|RS\.|Rs\.?|Rs)\s*(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)\s*(CR|LAC|LAKH|cr|lac|lakh)?',
        re.IGNORECASE
    ),
    'priceWithCommas': re.compile(r'(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)'),
    'currency': re.compile(r'(CR|LAC|LAKH|INR|RS|₹|cr|lac|lakh)', re.IGNORECASE),
    
    # Number patterns
    'number': re.compile(r'^\d+\.?\d*$'),
    'numberInText': re.compile(r'\d+\.?\d*'),
    
    # Date patterns - supports DD/MM/YYYY, DD-MM-YYYY, etc.
    'date': re.compile(r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}'),
    
    # Contact patterns
    'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    'phone': re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),
    'phoneIndia': re.compile(r'(\+91|91|0)?[-.\s]?[6-9]\d{9}'),  # Indian mobile numbers
    
    # Real estate specific patterns
    'bhk': re.compile(r'(\d+(?:\.\d+)?)\s*BHK', re.IGNORECASE),  # Supports 2.5 BHK, 3+1 BHK
    'bhkExtended': re.compile(r'(\d+(?:\.\d+)?)\s*BHK\s*[+\-]?\s*(\d+)?\s*(STUDY|ST|SR|BEDROOM|BED|ROOM)?', re.IGNORECASE),
    'typology': re.compile(r'(BHK|STUDY|ST|SR|BEDROOM|BED|ROOM|HALL|HK)', re.IGNORECASE),
    'area': re.compile(r'\((\d+(?:\.\d+)?)\)|(\d+(?:\.\d+)?)\s*(?:sq\.?\s*ft\.?|sqft|sq\.?\s*m\.?|sqm|sq\.?\s*mtr)', re.IGNORECASE),
    'areaSimple': re.compile(r'\((\d+(?:\.\d+)?)\)'),
    
    # General patterns
    'percentage': re.compile(r'(\d+\.?\d*)%'),
    'address': re.compile(r'(STREET|ST|ROAD|RD|AVENUE|AVE|LANE|LN|DRIVE|DR|NAGAR|COLONY)', re.IGNORECASE),
    'size': re.compile(r'(UK|US|EU|IN|CM)\s*(\d+)', re.IGNORECASE),
    'color': re.compile(r'^color\s+', re.IGNORECASE),
    'discount': re.compile(r'(extra|off|discount)\s*(\d+\.?\d*)%', re.IGNORECASE),
    'stock': re.compile(r'(in\s*stock|out\s*of\s*stock|available|unavailable)', re.IGNORECASE),
    
    # Inline patterns (pre-compiled for performance)
    'keyValue': re.compile(r'^([^:]+?):\s*(.+)$', re.IGNORECASE),
    'labelNumber': re.compile(r'^([A-Za-z\s]+?)\s+(\d+[.,]?\d*)\s*$'),
    'typologyPrefix': re.compile(r'^([^0-9]+?)(?=\d)'),
    'typologyWithData': re.compile(r'(\d+(?:\.\d+)?\s*BHK[^0-9]*?)\s*\((\d+(?:\.\d+)?)\)\s*([\d.]+)\s*([\d.]+)', re.IGNORECASE),
    'priceStart': re.compile(r'^\s*₹?\s*\d'),
    'headerKeywords': re.compile(r'^(MIN|MAX|PRICE|COST|AMOUNT|VALUE|TOTAL|SUBTOTAL)', re.IGNORECASE),
    'allCaps': re.compile(r'^[A-Z\s]+$'),
    'sizeList': re.compile(r'(UK|US|EU)\s*\d+', re.IGNORECASE),
    'sizeDetail': re.compile(r'(UK|US|EU)\s*(\d+)', re.IGNORECASE),
    'removeNumbers': re.compile(r'\d+\.?\d*'),
    'removeSpecialChars': re.compile(r'[^\w\s]'),
    'removeDigits': re.compile(r'\d+'),
    'whitespace': re.compile(r'\s+'),
    'dateSeparator': re.compile(r'[\/\-\.]'),
    'labelCleanup': re.compile(r'[:\-–—]'),
    'labelTrim': re.compile(r'^[^\w]+|[^\w]+$'),
    'articlePrefix': re.compile(r'^(the|a|an)\s+', re.IGNORECASE),
    'colorPrefix': re.compile(r'^color\s+', re.IGNORECASE),
}

# Common words for price context detection
PRICE_CONTEXT_WORDS = {'original', 'was', 'mrp', 'strike', 'crossed'}
DISCOUNT_WORDS = {'off', 'discount', 'extra', 'save'}


def parse_extracted_text(text: str) -> Dict[str, Any]:
    """
    Parse extracted OCR text and identify different data types.
    
    Returns structured data in the same format as AI extraction.
    Optimized for Indian real estate brochures.
    
    Args:
        text: Raw OCR text to parse
        
    Returns:
        Dictionary with 'sections' array matching AI format:
        {
            "sections": [
                {
                    "title": "Section Name",
                    "fields": [
                        {
                            "label": "Field Label",
                            "value": "Field Value",
                            "type": "text | number | date | email | tel",
                            "unit": "optional"
                        }
                    ]
                }
            ]
        }
    """
    if not text or not text.strip():
        return {
            'sections': []
        }
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    fields = []
    
    # Process each line
    for index, line in enumerate(lines):
        if not line:
            continue
        
        field = _process_line(line, index)
        if field:
            if isinstance(field, list):
                fields.extend(field)
            else:
                fields.append(field)
    
    # Group fields into sections and clean them
    sections = _group_fields_into_sections(fields)
    
    # Clean sections to match AI format (remove id, originalLine, etc.)
    cleaned_sections = _clean_sections_for_output(sections)
    
    return {
        'sections': cleaned_sections if cleaned_sections else [{'title': 'Extracted Data', 'fields': []}]
    }


def _process_line(line: str, index: int) -> Union[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Process a single line and extract field(s).
    
    Returns a single field dict, list of field dicts, or None.
    """
    # Try key-value pattern first (e.g., "Color: Red", "Price: ₹5000")
    key_value_match = PATTERNS['keyValue'].match(line)
    if key_value_match:
        key = clean_label(key_value_match.group(1).strip())
        value = key_value_match.group(2).strip()
        return create_field_from_value(key, value, line, index)
    
    # Try label + number pattern (e.g., "TOTAL 671.28", "AMOUNT 500")
    label_number_match = PATTERNS['labelNumber'].match(line)
    if label_number_match:
        label_text = clean_label(label_number_match.group(1).strip())
        number_value = label_number_match.group(2).replace(',', '').strip()
        if label_text:
            return {
                'id': f'field_{index}',
                'label': label_text,
                'value': number_value,
                'type': 'number',
                'originalLine': line
            }
    
    # Check for multiple prices in a line
    multiple_prices = PATTERNS['price'].findall(line)
    if len(multiple_prices) > 1:
        return _process_multiple_prices(line, index, multiple_prices)
    
    # Check for typology with area and prices (e.g., "2 BHK + STUDY (1380) 31.63 31.87")
    typology_match = PATTERNS['typologyWithData'].match(line)
    if typology_match:
        return _process_typology_with_data(line, index, typology_match)
    
    # Check for multiple numbers (might be a list or table row)
    multiple_numbers = PATTERNS['numberInText'].findall(line)
    if len(multiple_numbers) > 1 and not PATTERNS['bhk'].search(line):
        return _process_multiple_numbers(line, index, multiple_numbers)
    
    # Process single field with type detection
    return _detect_and_create_field(line, index)


def _process_multiple_prices(line: str, index: int, price_matches: List[Tuple[str, ...]]) -> List[Dict[str, Any]]:
    """Process a line containing multiple prices."""
    fields = []
    
    # Extract typology/description part
    typology_match = PATTERNS['typologyPrefix'].match(line)
    typology_text = typology_match.group(1).strip() if typology_match else ''
    
    if typology_text:
        fields.append({
            'id': f'field_{index}_typology',
            'label': 'Typology',
            'value': typology_text,
            'type': 'text',
            'originalLine': line
        })
    
    # Create price fields
    for price_index, price_match in enumerate(price_matches):
        if isinstance(price_match, tuple) and len(price_match) >= 2:
            amount = price_match[1].replace(',', '')
            currency = price_match[0] if price_match[0] else '₹'
            
            # Check for currency suffix (CR, LAC, etc.)
            if len(price_match) >= 3 and price_match[2]:
                currency_suffix = price_match[2].upper()
            else:
                # Search for currency suffix after the amount
                currency_suffix_match = PATTERNS['currency'].search(
                    line[line.find(amount) + len(amount):line.find(amount) + len(amount) + 10]
                    if amount in line else ''
                )
                currency_suffix = currency_suffix_match.group(1) if currency_suffix_match else None
            
            label = 'Min Price' if price_index == 0 else ('Max Price' if price_index == 1 else f'Price {price_index + 1}')
            
            field = {
                'id': f'field_{index}_price_{price_index}',
                'label': label,
                'value': amount,
                'type': 'number',
                'currency': currency.upper() if currency else '₹',
                'originalLine': line
            }
            
            if currency_suffix:
                field['currencySuffix'] = currency_suffix
            
            fields.append(field)
    
    return fields


def _process_typology_with_data(line: str, index: int, match: re.Match) -> List[Dict[str, Any]]:
    """Process typology line with area and prices."""
    fields = [
        {
            'id': f'field_{index}_typology',
            'label': 'Typology',
            'value': match.group(1).strip(),
            'type': 'text',
            'originalLine': line
        },
        {
            'id': f'field_{index}_area',
            'label': 'Area (sqft)',
            'value': match.group(2),
            'type': 'number',
            'unit': 'sqft',
            'originalLine': line
        },
        {
            'id': f'field_{index}_min_price',
            'label': 'Min Price',
            'value': match.group(3),
            'type': 'number',
            'originalLine': line
        },
        {
            'id': f'field_{index}_max_price',
            'label': 'Max Price',
            'value': match.group(4),
            'type': 'number',
            'originalLine': line
        }
    ]
    return fields


def _process_multiple_numbers(line: str, index: int, numbers: List[str]) -> List[Dict[str, Any]]:
    """Process a line with multiple numbers."""
    # Check if it's a size list (UK 3, UK 4, etc.)
    size_matches = PATTERNS['sizeList'].findall(line)
    if len(size_matches) > 1:
        fields = []
        for size_index, size_str in enumerate(size_matches):
            size_detail_match = PATTERNS['sizeDetail'].search(size_str)
            if size_detail_match:
                fields.append({
                    'id': f'field_{index}_size_{size_index}',
                    'label': f'Size {size_index + 1}',
                    'value': f"{size_detail_match.group(1).upper()} {size_detail_match.group(2)}",
                    'type': 'text',
                    'originalLine': line
                })
        if fields:
            return fields
    
    # Line with multiple numbers - split into separate fields
    text_part = PATTERNS['removeNumbers'].sub('', line).strip()
    clean_text_part = clean_label(text_part)
    
    fields = []
    for num_index, num in enumerate(numbers):
        fields.append({
            'id': f'field_{index}_num_{num_index}',
            'label': f'{clean_text_part} {num_index + 1}' if clean_text_part else f'Value {num_index + 1}',
            'value': num,
            'type': 'number',
            'originalLine': line
        })
    return fields


def _detect_and_create_field(line: str, index: int) -> Dict[str, Any]:
    """
    Detect field type and create field dictionary.
    Uses optimized pattern matching with early returns.
    """
    field = {
        'id': f'field_{index}',
        'label': '',
        'value': line,
        'type': 'text',
        'originalLine': line
    }
    
    # Price detection (most common in real estate)
    price_match = PATTERNS['price'].search(line)
    if price_match:
        field['type'] = 'number'
        price_value = price_match.group(2).replace(',', '')
        field['value'] = price_value
        field['currency'] = price_match.group(1) or '₹'
        
        # Check for currency suffix
        if len(price_match.groups()) >= 3 and price_match.group(3):
            field['currencySuffix'] = price_match.group(3).upper()
        
        field['label'] = extract_label(line, price_match.group(0)) or 'Price'
        
        # Check if it's an original/crossed-out price
        line_lower = line.lower()
        if any(word in line_lower for word in PRICE_CONTEXT_WORDS):
            field['label'] = 'Original Price'
        
        return field
    
    # Price without explicit currency but starts with number
    if PATTERNS['priceWithCommas'].search(line) and PATTERNS['priceStart'].match(line):
        price_match2 = PATTERNS['priceWithCommas'].search(line)
        if price_match2:
            field['type'] = 'number'
            field['value'] = price_match2.group(1).replace(',', '')
            field['currency'] = '₹'
            field['label'] = extract_label(line, price_match2.group(0)) or 'Price'
            return field
    
    # BHK/Typology detection
    bhk_match = PATTERNS['bhk'].search(line)
    if bhk_match:
        field['type'] = 'text'
        field['label'] = 'Typology'
        field['value'] = line
        return field
    
    # Area detection
    area_match = PATTERNS['area'].search(line)
    if area_match:
        field['type'] = 'number'
        # Try group 1 first (parentheses), then group 2 (with unit)
        field['value'] = area_match.group(1) or area_match.group(2) or ''
        field['label'] = extract_label(line, area_match.group(0)) or 'Area'
        field['unit'] = 'sqft'
        return field
    
    # Date detection
    date_match = PATTERNS['date'].search(line)
    if date_match:
        field['type'] = 'date'
        field['value'] = normalize_date(date_match.group(0))
        field['label'] = extract_label(line, date_match.group(0)) or 'Date'
        return field
    
    # Email detection
    email_match = PATTERNS['email'].search(line)
    if email_match:
        field['type'] = 'email'
        field['value'] = email_match.group(0)
        field['label'] = extract_label(line, email_match.group(0)) or 'Email'
        return field
    
    # Phone detection (try Indian format first, then general)
    phone_match = PATTERNS['phoneIndia'].search(line) or PATTERNS['phone'].search(line)
    if phone_match:
        field['type'] = 'tel'
        field['value'] = phone_match.group(0)
        field['label'] = extract_label(line, phone_match.group(0)) or 'Phone'
        return field
    
    # Percentage detection
    percent_match = PATTERNS['percentage'].search(line)
    if percent_match:
        field['type'] = 'number'
        field['value'] = percent_match.group(1)
        field['unit'] = '%'
        label_text = extract_label(line, percent_match.group(0))
        line_lower = line.lower()
        if any(word in label_text.lower() or word in line_lower for word in DISCOUNT_WORDS):
            field['label'] = 'Discount'
        else:
            field['label'] = label_text or 'Percentage'
        return field
    
    # Size detection
    size_match = PATTERNS['size'].search(line)
    if size_match:
        field['type'] = 'text'
        field['value'] = f"{size_match.group(1).upper()} {size_match.group(2)}"
        field['label'] = 'Size'
        return field
    
    # Color detection
    if PATTERNS['color'].search(line):
        field['type'] = 'text'
        field['value'] = PATTERNS['colorPrefix'].sub('', line, count=1).strip()
        field['label'] = 'Color'
        return field
    
    # Discount detection
    discount_match = PATTERNS['discount'].search(line)
    if discount_match:
        field['type'] = 'number'
        field['value'] = discount_match.group(2)
        field['label'] = 'Discount'
        field['unit'] = '%'
        return field
    
    # Stock status
    if PATTERNS['stock'].search(line):
        field['type'] = 'text'
        field['value'] = line
        field['label'] = 'Stock Status'
        return field
    
    # Header detection
    if PATTERNS['headerKeywords'].match(line) or PATTERNS['allCaps'].match(line):
        field['type'] = 'text'
        field['label'] = line
        field['value'] = ''
        field['isHeader'] = True
        return field
    
    # Pure number
    if PATTERNS['number'].match(line):
        field['type'] = 'number'
        field['value'] = line
        field['label'] = f'Value {index + 1}'
        return field
    
    # Default text field
    field['label'] = extract_label(line, '') or generate_label(line, index)
    return field


def extract_label(line: str, match: str) -> str:
    """Extract label from line by removing the matched value."""
    if not match:
        return clean_label(line)
    
    label = line.replace(match, '', 1).strip()
    label = PATTERNS['labelCleanup'].sub('', label).strip()
    label = PATTERNS['labelTrim'].sub('', label)
    return clean_label(label)


def clean_label(text: str) -> str:
    """
    Clean and format label text to be more meaningful.
    Optimized for performance.
    """
    if not text:
        return ''
    
    # Remove excessive whitespace
    text = PATTERNS['whitespace'].sub(' ', text).strip()
    
    # Remove common prefixes
    text = PATTERNS['articlePrefix'].sub('', text)
    
    # Capitalize words intelligently
    words = text.split()
    formatted_words = []
    for word in words:
        if not word:
            continue
        # Keep acronyms uppercase
        if word == word.upper() and len(word) > 1:
            formatted_words.append(word)
        else:
            # Capitalize first letter
            formatted_words.append(
                word[0].upper() + word[1:].lower() if len(word) > 1 else word.upper()
            )
    
    text = ' '.join(formatted_words)
    
    # Remove duplicate consecutive words
    words = text.split()
    unique_words = []
    for word in words:
        if not unique_words or unique_words[-1] != word:
            unique_words.append(word)
    text = ' '.join(unique_words)
    
    # Limit length
    if len(text) > 50:
        text = text[:47] + '...'
    
    return text


def create_field_from_value(key: str, value: str, original_line: str, index: int) -> Dict[str, Any]:
    """Create a field from a key-value pair with type detection."""
    field = {
        'id': f'field_{index}',
        'label': clean_label(key),
        'value': value,
        'type': 'text',
        'originalLine': original_line
    }
    
    # Detect type from value (optimized order: most common first)
    price_match = PATTERNS['price'].search(value)
    if price_match:
        field['type'] = 'number'
        if len(price_match.groups()) >= 2:
            field['value'] = price_match.group(2).replace(',', '')
            field['currency'] = price_match.group(1) or '₹'
            if len(price_match.groups()) >= 3 and price_match.group(3):
                field['currencySuffix'] = price_match.group(3).upper()
        return field
    
    if PATTERNS['priceWithCommas'].search(value):
        price_match2 = PATTERNS['priceWithCommas'].search(value)
        if price_match2:
            field['type'] = 'number'
            field['value'] = price_match2.group(1).replace(',', '')
            field['currency'] = '₹'
        return field
    
    percent_match = PATTERNS['percentage'].search(value)
    if percent_match:
        field['type'] = 'number'
        field['value'] = percent_match.group(1)
        field['unit'] = '%'
        return field
    
    date_match = PATTERNS['date'].search(value)
    if date_match:
        field['type'] = 'date'
        field['value'] = normalize_date(date_match.group(0))
        return field
    
    email_match = PATTERNS['email'].search(value)
    if email_match:
        field['type'] = 'email'
        field['value'] = email_match.group(0)
        return field
    
    phone_match = PATTERNS['phoneIndia'].search(value) or PATTERNS['phone'].search(value)
    if phone_match:
        field['type'] = 'tel'
        field['value'] = phone_match.group(0)
        return field
    
    if PATTERNS['number'].match(value):
        field['type'] = 'number'
    
    return field


def generate_label(line: str, index: int) -> str:
    """Generate a label from the line content."""
    label = PATTERNS['removeSpecialChars'].sub(' ', line)
    label = PATTERNS['removeDigits'].sub('', label).strip()
    words = label.split()
    label = ' '.join(words[:3])
    
    if not label:
        label = f'Field {index + 1}'
    
    return clean_label(label)


def normalize_date(date_str: str) -> str:
    """
    Normalize date to YYYY-MM-DD format.
    Supports DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY formats.
    """
    try:
        parts = PATTERNS['dateSeparator'].split(date_str)
        if len(parts) == 3:
            day, month, year = parts[0], parts[1], parts[2]
            
            # Handle 2-digit years
            if len(year) == 2:
                year = '20' + year
            
            # Try DD/MM/YYYY format (common in India)
            try:
                date_obj = datetime.strptime(f'{year}-{month.zfill(2)}-{day.zfill(2)}', '%Y-%m-%d')
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                # Try MM/DD/YYYY format (US format)
                try:
                    date_obj = datetime.strptime(f'{year}-{day.zfill(2)}-{month.zfill(2)}', '%Y-%m-%d')
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    pass
    except Exception:
        pass
    
    return date_str


def _group_fields_into_sections(fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group fields into sections based on headers."""
    sections = []
    current_section = None
    
    for field in fields:
        if field.get('isHeader'):
            current_section = {
                'title': field['label'],
                'fields': []
            }
            sections.append(current_section)
        elif current_section:
            current_section['fields'].append(field)
        else:
            # Fields before any section
            if not sections:
                sections.append({
                    'title': 'General Information',
                    'fields': []
                })
            sections[-1]['fields'].append(field)
    
    return sections


def _clean_sections_for_output(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Clean sections to match AI output format.
    Removes internal fields like 'id', 'originalLine', 'isHeader', etc.
    Only keeps: label, value, type, and optional unit/currency.
    """
    cleaned_sections = []
    
    for section in sections:
        cleaned_fields = []
        
        for field in section.get('fields', []):
            # Skip header fields (they're already converted to section titles)
            if field.get('isHeader'):
                continue
            
            # Create cleaned field matching AI format
            cleaned_field = {
                'label': field.get('label', ''),
                'value': field.get('value', ''),
                'type': field.get('type', 'text')
            }
            
            # Add optional unit if present
            if field.get('unit'):
                cleaned_field['unit'] = field['unit']
            
            # Add currency if present (for number type fields)
            if field.get('currency') and field.get('type') == 'number':
                cleaned_field['currency'] = field['currency']
            
            # Only add non-empty fields
            if cleaned_field.get('label') or cleaned_field.get('value'):
                cleaned_fields.append(cleaned_field)
        
        # Only add sections with fields
        if cleaned_fields:
            cleaned_sections.append({
                'title': section.get('title', 'Extracted Data'),
                'fields': cleaned_fields
            })
    
    return cleaned_sections
