# openai_service.py
"""
OpenAI service module for AI-powered data extraction.

This module provides:
- JSON schema to compact text conversion (reduces token usage by 60-80%)
- Real estate project data extraction from PDFs
- General document field extraction from OCR text
- Safe JSON parsing with error handling

The compact text format converts nested JSON schemas to dot-notation format
to significantly reduce token usage when sending prompts to LLMs.
"""

import os
import json
import openai
from dotenv import load_dotenv

load_dotenv()

# Lazy-load OpenAI client to avoid initialization errors if API key is not set
# This allows the module to be imported even without OPENAI_API_KEY configured
client = None


def get_openai_client():
    """
    Get or create OpenAI client (lazy initialization).
    
    The client is created only when first needed, allowing the module to be
    imported without requiring OPENAI_API_KEY to be set.
    
    Returns:
        openai.OpenAI: Initialized OpenAI client
        
    Raises:
        Exception: If OPENAI_API_KEY is not set in environment variables
    """
    global client
    if not client:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise Exception('OPENAI_API_KEY is not set in environment variables')
        client = openai.OpenAI(api_key=api_key)
    return client


def safe_json_parse(text):
    """
    Safely parse JSON from text that might contain extra content.
    
    LLM responses sometimes include explanatory text before/after JSON.
    This function handles that by extracting just the JSON portion.
    
    Args:
        text (str): Text that may contain JSON
        
    Returns:
        dict or None: Parsed JSON object, or None if parsing fails
    """
    try:
        if not text or not isinstance(text, str):
            return None
        
        # Try direct parse first (most common case)
        try:
            return json.loads(text)
        except:
            # If that fails, try to extract JSON from text
            # Find the first '{' and last '}' to extract JSON portion
            start = text.find('{')
            end = text.rfind('}')
            
            if start == -1 or end == -1 or end <= start:
                return None
            
            clean = text[start:end + 1]
            return json.loads(clean)
    except Exception as err:
        print(f'JSON parse error: {err}')
        return None


def json_to_compact_text(data, prefix="", max_depth=10, current_depth=0):
    """
    Convert JSON to compact text format to reduce token usage in LLM prompts.
    
    Uses dot notation for nested paths instead of full JSON formatting.
    This can reduce token usage by 60-80% for large schemas.
    
    Example:
        Input: {"user": {"name": "", "age": 0}}
        Output: "user: object\nuser.name: string\nuser.age: number"
    
    Args:
        data: JSON-serializable data (dict, list, or primitive)
        prefix (str): Current path prefix for nested structures (used internally)
        max_depth (int): Maximum recursion depth to prevent infinite loops
        current_depth (int): Current recursion depth (used internally)
        
    Returns:
        str: Compact text representation of the JSON structure
    """
    # Prevent infinite recursion on deeply nested structures
    if current_depth > max_depth:
        return "..."
    
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            # Build path using dot notation (e.g., "hero_section.heading")
            path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                if value:  # Non-empty dict - recurse into it
                    lines.append(f"{path}: object")
                    nested = json_to_compact_text(value, path, max_depth, current_depth + 1)
                    if nested:
                        lines.append(nested)
                else:  # Empty dict - just mark it
                    lines.append(f"{path}: object {{}}")
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    # Array of objects - show structure of first item as template
                    lines.append(f"{path}: array[object]")
                    nested = json_to_compact_text(value[0], f"{path}[0]", max_depth, current_depth + 1)
                    if nested:
                        lines.append(nested)
                else:
                    # Array of primitives - just mark as array
                    lines.append(f"{path}: array")
            elif isinstance(value, str):
                # Show example value if provided, otherwise just type
                default = f'="{value}"' if value else ': string'
                lines.append(f"{path}{default}")
            elif isinstance(value, (int, float)):
                # Show example value if non-zero, otherwise just type
                default = f": {value}" if value != 0 else ": number"
                lines.append(f"{path}{default}")
            elif isinstance(value, bool):
                lines.append(f"{path}: boolean")
            elif value is None:
                lines.append(f"{path}: null")
            else:
                lines.append(f"{path}: {type(value).__name__}")
        
        return "\n".join(lines)
    
    elif isinstance(data, list):
        if data and isinstance(data[0], dict):
            # Array of objects - show structure of first item
            lines = []
            lines.append(f"{prefix}: array[object]")
            nested = json_to_compact_text(data[0], f"{prefix}[0]", max_depth, current_depth + 1)
            if nested:
                lines.append(nested)
            return "\n".join(lines)
        else:
            return f"{prefix}: array"
    
    else:
        return f"{prefix}: {data}"


def get_compact_schema_text(schema_dict):
    """
    Convert a JSON schema dictionary to compact text format.
    
    This is a convenience wrapper around json_to_compact_text() specifically
    for converting JSON schemas that will be sent to LLMs in prompts.
    
    The compact format significantly reduces token usage while maintaining
    all the structural information the LLM needs to understand the schema.
    
    Args:
        schema_dict (dict): JSON schema dictionary to convert
        
    Returns:
        str: Compact text representation of the schema
        
    Example:
        Input: {"sections": [{"title": "", "fields": []}]}
        Output: "sections: array[object]\nsections[0].title: string\nsections[0].fields: array"
    """
    return json_to_compact_text(schema_dict)


async def extract_real_estate_project(pdf_text):
    """
    Extract real estate project data from PDF text using OpenAI.
    
    This function uses GPT-4o-mini to extract structured real estate project
    information from PDF text. It uses a compact schema format to reduce
    token usage while maintaining extraction accuracy.
    
    Args:
        pdf_text (str): Text content extracted from PDF
        
    Returns:
        dict or None: Extracted real estate project data matching the schema,
                     or None if extraction fails or API key is not configured
    """
    if not pdf_text or not pdf_text.strip():
        return None
    
    # Check if API key is configured
    if not os.getenv('OPENAI_API_KEY'):
        print('OPENAI_API_KEY not configured, skipping AI extraction')
        return None
    
    try:
        openai_client = get_openai_client()
        
        # Truncate text if too long (OpenAI has token limits)
        # Keep more text for better extraction (up to 12000 chars)
        # This balances between context and token usage
        truncated_text = pdf_text[:12000] + ('... (truncated)' if len(pdf_text) > 12000 else '')
        
        # Define the schema as a dict (for compact conversion)
        # This schema defines all possible fields for a real estate project
        schema_dict = {
            "project_name": "",
            "tagline": "",
            "logo": "",
            "brand_name": "",
            "hero_section": {
                "heading": "",
                "subheading": "",
                "description": "",
                "background_image": "",
                "background_video": "",
                "cta_buttons": {
                    "primary": {"text": "", "action": ""},
                    "secondary": {"text": "", "action": ""}
                },
                "quick_stats": {
                    "total_area": "",
                    "total_towers": "",
                    "total_units": ""
                },
                "status_badge": {"text": "", "icon": ""}
            },
            "about": {
                "heading": "",
                "description": "",
                "detailed_content": "",
                "image": "",
                "stats": {
                    "total_projects": "",
                    "years_experience": "",
                    "total_families": "",
                    "total_cities": ""
                },
                "developer_info": {
                    "name": "",
                    "description": "",
                    "achievements": [],
                    "image": "",
                    "website": "",
                    "established_year": ""
                }
            },
            "location": {
                "address": "",
                "sector": "",
                "city": "",
                "state": "",
                "pincode": "",
                "coordinates": {"latitude": "", "longitude": ""},
                "map_image": "",
                "map_embed_url": "",
                "description": "",
                "quick_distances": [{"place": "", "distance": "", "time": ""}],
                "connectivity": [{"type": "", "title": "", "description": ""}],
                "nearby_places": [{"category": "", "places": [{"name": "", "distance": ""}]}],
                "location_advantages": [{"title": "", "items": []}]
            },
            "amenities": [{"id": "", "name": "", "description": "", "category": "", "image": "", "icon": ""}],
            "amenity_categories": [],
            "tower_amenities": [],
            "gallery": [{"id": "", "src": "", "alt": "", "category": ""}],
            "gallery_categories": [],
            "floor_plans": [{"id": "", "type": "", "area": "", "area_unit": "", "description": "", "features": [], "image": "", "floor_plan_image": "", "price": "", "price_currency": ""}],
            "pricing": [{"id": "", "apartment_type": "", "area_range": "", "area_unit": "", "starting_price": "", "price_currency": "", "description": "", "features": [], "payment_plans": [], "notes": ""}],
            "project_highlights": [{"icon": "", "title": "", "description": ""}],
            "project_info": {
                "total_area": "",
                "total_towers": "",
                "total_units": "",
                "apartments_per_floor": "",
                "possession_date": "",
                "price_range": "",
                "rera_number": "",
                "rera_status": ""
            },
            "site_plan": {
                "master_plan_image": "",
                "legend": [{"code": "", "name": "", "color": ""}],
                "outdoor_amenities_list": [],
                "description": "",
                "disclaimer": ""
            },
            "developer": {
                "name": "",
                "description": "",
                "history": "",
                "achievements": [],
                "projects_completed": "",
                "area_developed": "",
                "cities_presence": [],
                "philosophy": "",
                "logo": "",
                "website": "",
                "established_year": ""
            },
            "contact": {
                "phone": "",
                "whatsapp": "",
                "email": "",
                "address": "",
                "office_hours": "",
                "sales_office_address": "",
                "site_office_address": "",
                "social_media": {
                    "facebook": "",
                    "twitter": "",
                    "instagram": "",
                    "linkedin": "",
                    "youtube": ""
                }
            },
            "legal_info": {
                "rera_number": "",
                "rera_status": "",
                "rera_registration_date": "",
                "legal_disclaimer": "",
                "terms_and_conditions": "",
                "privacy_policy": "",
                "refund_policy": ""
            },
            "seo": {
                "meta_title": "",
                "meta_description": "",
                "keywords": [],
                "og_title": "",
                "og_description": "",
                "og_image": "",
                "twitter_card": {"title": "", "description": "", "image": ""}
            },
            "navigation": {
                "main_menu": [{"name": "", "href": ""}],
                "footer_links": {
                    "quick_links": [],
                    "legal_links": [],
                    "social_links": []
                }
            },
            "cta_sections": [{"heading": "", "description": "", "buttons": [{"text": "", "action": "", "type": ""}]}],
            "international_architects": {"heading": "", "images": []}
        }
        
        # Convert schema to compact text format to reduce token usage
        # This reduces the schema from ~2000 tokens to ~400-600 tokens
        compact_schema = get_compact_schema_text(schema_dict)
        
        # Call OpenAI API with compact schema format
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Cost-effective model with good extraction capabilities
            messages=[
                {
                    "role": "system",
                    "content": "You are a real estate document extraction specialist. Extract structured project information from PDF text and return it in the exact JSON schema provided. Only extract information that is explicitly present in the text. Leave fields empty if information is not found."
                },
                {
                    "role": "user",
                    "content": f"""Extract real estate project information from the following PDF text and populate the JSON schema below.

CRITICAL INSTRUCTIONS:
1. Only extract information that is EXPLICITLY present in the text
2. Leave fields as empty strings "" if information is not found
3. For arrays, only include items if data is found
4. Extract phone numbers, emails, addresses, prices, dates, and other details accurately
5. For coordinates, extract latitude and longitude if mentioned
6. For amenities, extract names, descriptions, categories, and icons if available
7. For pricing, extract apartment types, area ranges, starting prices, and payment plans
8. For location, extract address, sector, city, state, pincode, nearby places, and connectivity
9. For developer info, extract name, description, achievements, website, established year
10. For legal info, extract RERA number, status, registration date, and disclaimers
11. For SEO, generate appropriate meta title, description, and keywords based on project name
12. Output MUST be valid JSON matching the exact schema structure

REAL ESTATE PROJECT JSON SCHEMA (compact format):
{compact_schema}

Now extract information from this PDF text:

{truncated_text}"""
                }
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON response from OpenAI
        raw_response = response.choices[0].message.content
        extracted_data = safe_json_parse(raw_response)
        
        # Ensure all required fields exist with empty defaults if missing
        # This guarantees the returned data matches the complete schema structure
        if extracted_data:
            extracted_data = ensure_schema_completeness(extracted_data)
        
        return extracted_data
    except Exception as error:
        print(f'Real estate extraction error: {error}')
        return None


def ensure_schema_completeness(data):
    """Ensure the extracted data matches the complete schema structure"""
    schema_template = {
        "project_name": "",
        "tagline": "",
        "logo": "",
        "brand_name": "",
        "hero_section": {
            "heading": "",
            "subheading": "",
            "description": "",
            "background_image": "",
            "background_video": "",
            "cta_buttons": {
                "primary": {"text": "", "action": ""},
                "secondary": {"text": "", "action": ""}
            },
            "quick_stats": {
                "total_area": "",
                "total_towers": "",
                "total_units": ""
            },
            "status_badge": {"text": "", "icon": ""}
        },
        "about": {
            "heading": "",
            "description": "",
            "detailed_content": "",
            "image": "",
            "stats": {
                "total_projects": "",
                "years_experience": "",
                "total_families": "",
                "total_cities": ""
            },
            "developer_info": {
                "name": "",
                "description": "",
                "achievements": [],
                "image": "",
                "website": "",
                "established_year": ""
            }
        },
        "location": {
            "address": "",
            "sector": "",
            "city": "",
            "state": "",
            "pincode": "",
            "coordinates": {"latitude": "", "longitude": ""},
            "map_image": "",
            "map_embed_url": "",
            "description": "",
            "quick_distances": [],
            "connectivity": [],
            "nearby_places": [],
            "location_advantages": []
        },
        "amenities": [],
        "amenity_categories": [],
        "tower_amenities": [],
        "gallery": [],
        "gallery_categories": [],
        "floor_plans": [],
        "pricing": [],
        "project_highlights": [],
        "project_info": {
            "total_area": "",
            "total_towers": "",
            "total_units": "",
            "apartments_per_floor": "",
            "possession_date": "",
            "price_range": "",
            "rera_number": "",
            "rera_status": ""
        },
        "site_plan": {
            "master_plan_image": "",
            "legend": [],
            "outdoor_amenities_list": [],
            "description": "",
            "disclaimer": ""
        },
        "developer": {
            "name": "",
            "description": "",
            "history": "",
            "achievements": [],
            "projects_completed": "",
            "area_developed": "",
            "cities_presence": [],
            "philosophy": "",
            "logo": "",
            "website": "",
            "established_year": ""
        },
        "contact": {
            "phone": "",
            "whatsapp": "",
            "email": "",
            "address": "",
            "office_hours": "",
            "sales_office_address": "",
            "site_office_address": "",
            "social_media": {
                "facebook": "",
                "twitter": "",
                "instagram": "",
                "linkedin": "",
                "youtube": ""
            }
        },
        "legal_info": {
            "rera_number": "",
            "rera_status": "",
            "rera_registration_date": "",
            "legal_disclaimer": "",
            "terms_and_conditions": "",
            "privacy_policy": "",
            "refund_policy": ""
        },
        "seo": {
            "meta_title": "",
            "meta_description": "",
            "keywords": [],
            "og_title": "",
            "og_description": "",
            "og_image": "",
            "twitter_card": {"title": "", "description": "", "image": ""}
        },
        "navigation": {
            "main_menu": [],
            "footer_links": {
                "quick_links": [],
                "legal_links": [],
                "social_links": []
            }
        },
        "cta_sections": [],
        "international_architects": {"heading": "", "images": []}
    }
    
    # Deep merge: use extracted data where available, fall back to template
    def deep_merge(template, extracted):
        if isinstance(template, dict) and isinstance(extracted, dict):
            result = template.copy()
            for key, value in extracted.items():
                if key in result:
                    if isinstance(result[key], dict) and isinstance(value, dict):
                        result[key] = deep_merge(result[key], value)
                    else:
                        result[key] = value
                else:
                    result[key] = value
            return result
        elif isinstance(template, list) and isinstance(extracted, list):
            return extracted if extracted else template
        else:
            return extracted if extracted else template
    
    return deep_merge(schema_template, data)


async def extract_fields_with_openai(ocr_text):
    """
    Extract structured fields from OCR text using OpenAI.
    
    This function processes OCR text (from images or PDFs) and extracts
    structured field data using AI. It's more flexible than the real estate
    specific extraction and works for any document type.
    
    Args:
        ocr_text (str): Text content from OCR processing
        
    Returns:
        dict or None: Extracted structured fields with sections and fields,
                     or None if extraction fails or API key is not configured
    """
    if not ocr_text or not ocr_text.strip():
        return None
    
    # Check if API key is configured
    if not os.getenv('OPENAI_API_KEY'):
        print('OPENAI_API_KEY not configured, skipping AI extraction')
        return None
    
    try:
        openai_client = get_openai_client()
        
        # Define output schema as dict (will be converted to compact format)
        # This schema is more generic and works for any document type
        output_schema = {
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
        
        # Convert to compact format to reduce token usage
        compact_schema = get_compact_schema_text(output_schema)
        
        # Call OpenAI API for field extraction
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Good balance between cost and performance
            messages=[
                {
                    "role": "system",
                    "content": "You are a document structure extraction engine. Your task is to convert raw extracted PDF text into clean structured JSON format suitable for rendering a dynamic form."
                },
                {
                    "role": "user",
                    "content": f"""You are a document structure extraction engine.

Your task is to convert raw extracted PDF text into clean structured JSON format suitable for rendering a dynamic form.

Instructions:

1. Extract meaningful label-value pairs from the text.

2. If a line contains:
   - "Label: Value" → split into label and value.
   - "LABEL VALUE" (number at end) → treat trailing number as value.
   - Monetary values → mark type as "number" and include currency if available.
   - Dates → convert to YYYY-MM-DD format and mark type as "date".
   - Emails → type "email".
   - Phone numbers → type "tel".
   - Percentages → type "number" with unit "%".

3. If a line is ALL CAPS and does not contain a value, treat it as a section header.

4. Ignore decorative lines, random symbols, and broken layout artifacts.

5. Clean labels:
   - Remove extra spaces and special characters.
   - Convert to Title Case (except acronyms).

6. Preserve the original numeric values without formatting commas.

7. Do NOT hallucinate missing values.

8. Output strictly valid JSON.

Output Format (compact schema):
{compact_schema}

Now structure the following text:

{ocr_text[:8000]}{'... (truncated)' if len(ocr_text) > 8000 else ''}"""
                }
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        raw_response = response.choices[0].message.content
        return safe_json_parse(raw_response)
    except Exception as error:
        print(f'OpenAI extraction error: {error}')
        return None

