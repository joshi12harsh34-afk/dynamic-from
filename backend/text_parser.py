import re
from datetime import datetime


# Patterns for different data types
PATTERNS = {
    'price': re.compile(r'(₹|INR|RS|RS\.|Rs\.?)\s*(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)', re.IGNORECASE),
    'priceWithCommas': re.compile(r'(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)'),
    'currency': re.compile(r'(CR|LAC|LAKH|INR|RS|₹|cr|lac)', re.IGNORECASE),
    'number': re.compile(r'^\d+\.?\d*$'),
    'date': re.compile(r'\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}'),
    'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    'phone': re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),
    'bhk': re.compile(r'(\d+)\s*BHK', re.IGNORECASE),
    'typology': re.compile(r'(BHK|STUDY|ST|SR|BEDROOM|BED|ROOM)', re.IGNORECASE),
    'area': re.compile(r'\((\d+)\)'),
    'percentage': re.compile(r'(\d+\.?\d*)%'),
    'address': re.compile(r'(STREET|ST|ROAD|RD|AVENUE|AVE|LANE|LN|DRIVE|DR)', re.IGNORECASE),
    'size': re.compile(r'(UK|US|EU|IN|CM)\s*(\d+)', re.IGNORECASE),
    'color': re.compile(r'^color\s+', re.IGNORECASE),
    'discount': re.compile(r'(extra|off|discount)\s*(\d+\.?\d*)%', re.IGNORECASE),
    'stock': re.compile(r'(in\s*stock|out\s*of\s*stock|available|unavailable)', re.IGNORECASE)
}


def parse_extracted_text(text):
    """
    Parse extracted OCR text and identify different data types
    Returns structured data that can be used to generate dynamic forms
    """
    if not text or not text.strip():
        return {
            'fields': [],
            'sections': [],
            'rawText': text
        }
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    fields = []
    sections = []
    current_section = None
    
    for index, line in enumerate(lines):
        # Skip empty lines
        if not line or not line.strip():
            continue
        
        # Try to detect key-value patterns (e.g., "Color: value", "Size: value", "Price: value")
        key_value_match = re.match(r'^([^:]+?):\s*(.+)$', line, re.IGNORECASE)
        if key_value_match:
            key = clean_label(key_value_match.group(1).strip())
            value = key_value_match.group(2).strip()
            
            # Process the value based on patterns
            field = create_field_from_value(key, value, line, index)
            fields.append(field)
            continue
        
        # Detect label + number pattern (e.g., "TOTAL 671.28", "SUBTOTAL 123.45", "AMOUNT 500")
        # Pattern: word(s) followed by a number - handles cases like "TOTAL 671.28"
        # This pattern matches: label (letters/spaces) followed by whitespace and a number
        label_number_match = re.match(r'^([A-Za-z\s]+?)\s+(\d+[.,]?\d*)\s*$', line)
        if label_number_match:
            label_text = clean_label(label_number_match.group(1).strip())
            number_value = label_number_match.group(2).replace(',', '').strip()
            
            # Only process if label is meaningful (not just numbers or special chars)
            if label_text and len(label_text) > 0:
                field = {
                    'id': f'field_{index}',
                    'label': label_text,
                    'value': number_value,
                    'type': 'number',
                    'originalLine': line
                }
                fields.append(field)
                continue
        
        # Check if line contains multiple values (table-like structure)
        multiple_prices = PATTERNS['price'].findall(line)
        multiple_numbers = re.findall(r'\d+\.?\d*', line)
        
        # If line has multiple prices or numbers, split into separate fields
        if multiple_prices and len(multiple_prices) > 1:
            # Extract typology/description part
            typology_match = re.match(r'^([^0-9]+?)(?=\d)', line)
            typology_text = typology_match.group(1).strip() if typology_match else ''
            
            # Create typology field
            if typology_text:
                fields.append({
                    'id': f'field_{index}_typology',
                    'label': 'Typology',
                    'value': typology_text,
                    'type': 'text',
                    'originalLine': line
                })
            
            # Create price fields
            for price_index, price_match in enumerate(multiple_prices):
                # price_match is a tuple (currency, amount) from findall
                if isinstance(price_match, tuple) and len(price_match) >= 2:
                    amount = price_match[1].replace(',', '')
                    currency = price_match[0] if price_match[0] else '₹'
                    # Check for currency suffix in the line
                    currency_suffix_match = re.search(rf'{re.escape(amount)}\s*(CR|LAC|LAKH|INR|RS|₹|cr|lac)', line, re.IGNORECASE)
                    if currency_suffix_match:
                        currency = currency_suffix_match.group(1)
                    
                    fields.append({
                        'id': f'field_{index}_price_{price_index}',
                        'label': 'Min Price' if price_index == 0 else ('Max Price' if price_index == 1 else f'Price {price_index + 1}'),
                        'value': amount,
                        'type': 'number',
                        'currency': currency.upper() if currency else '₹',
                        'originalLine': line
                    })
            continue  # Skip default processing for this line
        
        # Check for typology with area and prices (e.g., "2 BHK + STUDY (1380) 31.63 31.87")
        typology_with_data = re.match(r'(\d+\s*BHK[^0-9]*?)\s*\((\d+)\)\s*([\d.]+)\s*([\d.]+)', line, re.IGNORECASE)
        if typology_with_data:
            fields.append({
                'id': f'field_{index}_typology',
                'label': 'Typology',
                'value': typology_with_data.group(1).strip(),
                'type': 'text',
                'originalLine': line
            })
            
            fields.append({
                'id': f'field_{index}_area',
                'label': 'Area (sqft)',
                'value': typology_with_data.group(2),
                'type': 'number',
                'unit': 'sqft',
                'originalLine': line
            })
            
            fields.append({
                'id': f'field_{index}_min_price',
                'label': 'Min Price',
                'value': typology_with_data.group(3),
                'type': 'number',
                'originalLine': line
            })
            
            fields.append({
                'id': f'field_{index}_max_price',
                'label': 'Max Price',
                'value': typology_with_data.group(4),
                'type': 'number',
                'originalLine': line
            })
            continue  # Skip default processing
        
        field = {
            'id': f'field_{index}',
            'label': '',
            'value': line,
            'type': 'text',
            'originalLine': line
        }
        
        # Detect field type and extract structured data
        # Check for price with ₹ or currency symbols
        price_match = PATTERNS['price'].search(line)
        if price_match:
            field['type'] = 'number'
            price_value = price_match.group(2).replace(',', '')
            field['value'] = price_value
            field['currency'] = '₹'
            field['label'] = extract_label(line, price_match.group(0)) or 'Price'
            # Check if it's a crossed-out price (original price)
            if any(word in line.lower() for word in ['original', 'was', 'mrp']):
                field['label'] = 'Original Price'
        elif PATTERNS['priceWithCommas'].search(line) and re.match(r'^\s*₹?\s*\d', line):
            # Price without explicit currency symbol but starts with number
            price_match2 = PATTERNS['priceWithCommas'].search(line)
            if price_match2:
                field['type'] = 'number'
                field['value'] = price_match2.group(1).replace(',', '')
                field['currency'] = '₹'
                field['label'] = extract_label(line, price_match2.group(0)) or 'Price'
        elif PATTERNS['bhk'].search(line):
            # BHK/Typology field
            bhk_match = PATTERNS['bhk'].search(line)
            if bhk_match:
                field['type'] = 'text'
                field['label'] = 'Typology'
                field['value'] = line
        elif PATTERNS['area'].search(line):
            # Area field (in sqft or similar)
            area_match = PATTERNS['area'].search(line)
            if area_match:
                field['type'] = 'number'
                field['value'] = area_match.group(1)
                field['label'] = extract_label(line, area_match.group(0))
                field['unit'] = 'sqft'
        elif PATTERNS['date'].search(line):
            # Date field
            field['type'] = 'date'
            date_match = PATTERNS['date'].search(line)
            if date_match:
                field['value'] = normalize_date(date_match.group(0))
                field['label'] = extract_label(line, date_match.group(0))
        elif PATTERNS['email'].search(line):
            # Email field
            field['type'] = 'email'
            email_match = PATTERNS['email'].search(line)
            if email_match:
                field['value'] = email_match.group(0)
                field['label'] = extract_label(line, email_match.group(0))
        elif PATTERNS['phone'].search(line):
            # Phone field
            field['type'] = 'tel'
            phone_match = PATTERNS['phone'].search(line)
            if phone_match:
                field['value'] = phone_match.group(0)
                field['label'] = extract_label(line, phone_match.group(0))
        elif PATTERNS['percentage'].search(line):
            # Percentage field
            field['type'] = 'number'
            percent_match = PATTERNS['percentage'].search(line)
            if percent_match:
                field['value'] = percent_match.group(1)
                # Better label extraction for discounts/percentages
                label_text = extract_label(line, percent_match.group(0))
                if any(word in label_text.lower() for word in ['off', 'discount', 'extra']):
                    field['label'] = 'Discount'
                else:
                    field['label'] = label_text or 'Percentage'
                field['unit'] = '%'
        elif PATTERNS['size'].search(line):
            # Size field (UK 3, US 5, etc.)
            size_match = PATTERNS['size'].search(line)
            if size_match:
                field['type'] = 'text'
                field['value'] = f"{size_match.group(1).upper()} {size_match.group(2)}"
                field['label'] = 'Size'
        elif PATTERNS['color'].search(line):
            # Color field
            field['type'] = 'text'
            field['value'] = re.sub(r'^color\s+', '', line, flags=re.IGNORECASE).strip()
            field['label'] = 'Color'
        elif PATTERNS['discount'].search(line):
            # Discount field
            discount_match = PATTERNS['discount'].search(line)
            if discount_match:
                field['type'] = 'number'
                field['value'] = discount_match.group(2)
                field['label'] = 'Discount'
                field['unit'] = '%'
        elif PATTERNS['stock'].search(line):
            # Stock status
            field['type'] = 'text'
            field['value'] = line
            field['label'] = 'Stock Status'
        elif re.match(r'^(MIN|MAX|PRICE|COST|AMOUNT|VALUE)', line, re.IGNORECASE):
            # Label/Header field
            field['type'] = 'text'
            field['label'] = line
            field['value'] = ''
            field['isHeader'] = True
        elif re.match(r'^[A-Z\s]+$', line):
            # All caps line - likely a header or label
            field['type'] = 'text'
            field['label'] = line
            field['value'] = ''
            field['isHeader'] = True
        elif multiple_numbers and len(multiple_numbers) > 1 and not PATTERNS['bhk'].search(line):
            # Check if it's a size list (UK 3, UK 4, etc.)
            size_pattern = re.compile(r'(UK|US|EU)\s*\d+', re.IGNORECASE)
            size_matches = size_pattern.findall(line)
            if size_matches and len(size_matches) > 1:
                # It's a list of sizes
                for size_index, size_str in enumerate(size_matches):
                    size_match = re.search(r'(UK|US|EU)\s*(\d+)', size_str, re.IGNORECASE)
                    if size_match:
                        fields.append({
                            'id': f'field_{index}_size_{size_index}',
                            'label': f'Size {size_index + 1}',
                            'value': f"{size_match.group(1).upper()} {size_match.group(2)}",
                            'type': 'text',
                            'originalLine': line
                        })
                continue  # Skip default processing
            
            # Line with multiple numbers - split into separate fields
            text_part = re.sub(r'\d+\.?\d*', '', line).strip()
            # Clean up text part to create better label
            clean_text_part = clean_label(text_part)
            for num_index, num in enumerate(multiple_numbers):
                fields.append({
                    'id': f'field_{index}_num_{num_index}',
                    'label': f'{clean_text_part} {num_index + 1}' if clean_text_part else f'Value {num_index + 1}',
                    'value': num,
                    'type': 'number',
                    'originalLine': line
                })
            continue  # Skip default processing
        elif PATTERNS['number'].match(line):
            # Pure number
            field['type'] = 'number'
            field['value'] = line
            field['label'] = f'Value {index + 1}'
        else:
            # Default text field
            field['type'] = 'text'
            field['label'] = extract_label(line, '')
        
        # Generate a better label if not set
        if not field.get('label') or len(field['label']) == 0:
            field['label'] = generate_label(line, index)
        
        fields.append(field)
    
    # Group fields into sections based on headers
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
    
    return {
        'fields': fields,
        'sections': sections if sections else [{'title': 'Extracted Data', 'fields': fields}],
        'rawText': text,
        'fieldCount': len(fields)
    }


def extract_label(line, match):
    """Extract label from line by removing the matched value"""
    if not match:
        return clean_label(line)
    label = line.replace(match, '').strip()
    # Remove common separators
    label = re.sub(r'[:\-–—]', '', label).strip()
    # Remove leading/trailing special characters
    label = re.sub(r'^[^\w]+|[^\w]+$', '', label)
    return clean_label(label)


def clean_label(text):
    """Clean and format label text to be more meaningful"""
    if not text:
        return ''
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove common prefixes/suffixes that don't add meaning
    text = re.sub(r'^(the|a|an)\s+', '', text, flags=re.IGNORECASE)
    
    # Capitalize first letter of each word for better readability
    words = text.split(' ')
    formatted_words = []
    for word in words:
        if not word:
            continue
        # Keep acronyms uppercase
        if word == word.upper() and len(word) > 1:
            formatted_words.append(word)
        else:
            # Capitalize first letter
            formatted_words.append(word[0].upper() + word[1:].lower() if len(word) > 1 else word.upper())
    
    text = ' '.join(formatted_words)
    
    # Remove duplicate words (e.g., "UK UK UK" -> "UK")
    words = text.split(' ')
    unique_words = []
    for word in words:
        if not unique_words or unique_words[-1] != word:
            unique_words.append(word)
    text = ' '.join(unique_words)
    
    # Limit length
    if len(text) > 50:
        text = text[:47] + '...'
    
    return text


def create_field_from_value(key, value, original_line, index):
    """Create a field from a key-value pair"""
    field = {
        'id': f'field_{index}',
        'label': clean_label(key),
        'value': value,
        'type': 'text',
        'originalLine': original_line
    }
    
    # Detect type from value
    price_match = PATTERNS['price'].search(value)
    if price_match:
        field['type'] = 'number'
        # price_match groups: (currency, amount)
        if len(price_match.groups()) >= 2:
            field['value'] = price_match.group(2).replace(',', '')
            field['currency'] = price_match.group(1) or '₹'
        else:
            field['value'] = price_match.group(0).replace(',', '')
            field['currency'] = '₹'
    elif PATTERNS['priceWithCommas'].search(value):
        price_match2 = PATTERNS['priceWithCommas'].search(value)
        if price_match2:
            field['type'] = 'number'
            field['value'] = price_match2.group(1).replace(',', '')
            field['currency'] = '₹'
    elif PATTERNS['percentage'].search(value):
        percent_match = PATTERNS['percentage'].search(value)
        if percent_match:
            field['type'] = 'number'
            field['value'] = percent_match.group(1)
            field['unit'] = '%'
    elif PATTERNS['date'].search(value):
        field['type'] = 'date'
        date_match = PATTERNS['date'].search(value)
        if date_match:
            field['value'] = normalize_date(date_match.group(0))
    elif PATTERNS['email'].search(value):
        field['type'] = 'email'
        email_match = PATTERNS['email'].search(value)
        if email_match:
            field['value'] = email_match.group(0)
    elif PATTERNS['phone'].search(value):
        field['type'] = 'tel'
        phone_match = PATTERNS['phone'].search(value)
        if phone_match:
            field['value'] = phone_match.group(0)
    elif PATTERNS['number'].match(value):
        field['type'] = 'number'
    
    return field


def generate_label(line, index):
    """Generate a label from the line content"""
    # Remove special characters and numbers, capitalize first letter
    label = re.sub(r'[^\w\s]', ' ', line)
    label = re.sub(r'\d+', '', label).strip()
    words = label.split()
    label = ' '.join(words[:3])
    
    if not label:
        label = f'Field {index + 1}'
    
    return clean_label(label)


def normalize_date(date_str):
    """Normalize date to YYYY-MM-DD format"""
    try:
        parts = re.split(r'[\/\-]', date_str)
        if len(parts) == 3:
            day = parts[0]
            month = parts[1]
            year = parts[2]
            
            if len(year) == 2:
                year = '20' + year
            
            # Try to create date
            date_obj = datetime.strptime(f'{year}-{month.zfill(2)}-{day.zfill(2)}', '%Y-%m-%d')
            return date_obj.strftime('%Y-%m-%d')
    except:
        pass  # Return original if parsing fails
    return date_str

