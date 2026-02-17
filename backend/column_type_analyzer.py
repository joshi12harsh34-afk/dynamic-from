import re


def analyze_csv_columns(headers, rows):
    """
    Analyze CSV columns to determine appropriate input field types
    """
    column_types = {}
    
    for header in headers:
        column_data = [str(row.get(header, '')).strip() for row in rows if row.get(header) and str(row.get(header)).strip()]
        
        if not column_data:
            column_types[header] = {
                'type': 'text',
                'detectedType': 'text',
                'confidence': 0
            }
            continue
        
        # Patterns for different data types
        patterns = {
            'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            'phone': re.compile(r'^(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$'),
            'date': re.compile(r'^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}$|^\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}$'),
            'url': re.compile(r'^https?://.+'),
            'number': re.compile(r'^-?\d+\.?\d*$'),
            'percentage': re.compile(r'^\d+\.?\d*%$'),
            'currency': re.compile(r'^[₹$€£]?\s*\d+\.?\d*\s*(CR|LAC|LAKH|INR|RS|USD|EUR|GBP)?$', re.IGNORECASE),
            'boolean': re.compile(r'^(true|false|yes|no|1|0)$', re.IGNORECASE)
        }
        
        # Check header name for hints
        header_lower = header.lower()
        detected_type = 'text'
        confidence = 0.5
        unit = None
        currency = None
        
        # Header-based detection
        if 'email' in header_lower or 'e-mail' in header_lower:
            detected_type = 'email'
            confidence = 0.9
        elif any(word in header_lower for word in ['phone', 'mobile', 'contact']):
            detected_type = 'tel'
            confidence = 0.9
        elif any(word in header_lower for word in ['date', 'time', 'dob', 'birth']):
            detected_type = 'date'
            confidence = 0.9
        elif any(word in header_lower for word in ['url', 'link', 'website']):
            detected_type = 'url'
            confidence = 0.9
        elif any(word in header_lower for word in ['price', 'cost', 'amount', 'fee']):
            detected_type = 'number'
            confidence = 0.8
            if 'cr' in header_lower or 'crore' in header_lower:
                currency = 'CR'
            elif 'lac' in header_lower or 'lakh' in header_lower:
                currency = 'LAC'
        elif any(word in header_lower for word in ['age', 'count', 'quantity', 'qty']):
            detected_type = 'number'
            confidence = 0.8
        elif any(word in header_lower for word in ['percent', 'percentage']) or '%' in header_lower:
            detected_type = 'number'
            confidence = 0.9
            unit = '%'
        elif any(word in header_lower for word in ['area', 'sqft', 'sq.ft']):
            detected_type = 'number'
            confidence = 0.8
            unit = 'sqft'
        elif any(word in header_lower for word in ['active', 'status', 'enabled']):
            detected_type = 'checkbox'
            confidence = 0.7
        
        # Content-based detection (override header-based if content is more confident)
        type_matches = {
            'email': 0,
            'phone': 0,
            'date': 0,
            'url': 0,
            'number': 0,
            'percentage': 0,
            'currency': 0,
            'boolean': 0
        }
        
        for value in column_data[:10]:
            str_value = str(value).strip()
            
            if patterns['email'].match(str_value):
                type_matches['email'] += 1
            if patterns['phone'].match(str_value):
                type_matches['phone'] += 1
            if patterns['date'].match(str_value):
                type_matches['date'] += 1
            if patterns['url'].match(str_value):
                type_matches['url'] += 1
            if patterns['number'].match(str_value):
                type_matches['number'] += 1
            if patterns['percentage'].match(str_value):
                type_matches['percentage'] += 1
            if patterns['currency'].match(str_value):
                type_matches['currency'] += 1
            if patterns['boolean'].match(str_value):
                type_matches['boolean'] += 1
        
        # Find the type with highest matches
        max_matches = max(type_matches.values()) if type_matches.values() else 0
        if max_matches > 0:
            best_match = max(type_matches, key=type_matches.get)
            match_ratio = max_matches / min(len(column_data), 10)
            
            if match_ratio > 0.7:  # 70% of values match the pattern
                if best_match == 'tel':
                    detected_type = 'tel'
                elif best_match == 'email':
                    detected_type = 'email'
                elif best_match == 'date':
                    detected_type = 'date'
                elif best_match == 'url':
                    detected_type = 'url'
                elif best_match in ['number', 'percentage', 'currency']:
                    detected_type = 'number'
                elif best_match == 'boolean':
                    detected_type = 'checkbox'
                else:
                    detected_type = 'text'
                
                confidence = max(confidence, match_ratio)
                
                # Extract currency or unit from content
                if best_match == 'currency':
                    currency_match = re.search(r'(CR|LAC|LAKH|INR|RS|USD|EUR|GBP)', str(column_data[0]) if column_data else '', re.IGNORECASE)
                    if currency_match:
                        currency = currency_match.group(1).upper()
                if best_match == 'percentage':
                    unit = '%'
        
        column_types[header] = {
            'type': detected_type,
            'detectedType': detected_type,
            'confidence': confidence,
            'unit': unit,
            'currency': currency,
            'sampleValues': column_data[:3]
        }
    
    return column_types

