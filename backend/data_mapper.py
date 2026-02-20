# data_mapper.py
"""
Data mapping utilities to convert scraped/extracted data to project schema format.
"""

import re
from typing import Dict, Any


def _is_project_schema_like(data: Any) -> bool:
    """Detect if payload already looks like project schema (nested JSON structure)."""
    return isinstance(data, dict) and any(
        key in data for key in ("hero_section", "about", "location", "project_info", "contact")
    )


def _deep_merge_non_empty(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge source into target, but skip empty values from source.
    Keeps valid nested objects from LLM extraction (e.g., about/location blocks).
    """
    if not isinstance(target, dict):
        target = {}
    if not isinstance(source, dict):
        return target

    for key, value in source.items():
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        if isinstance(value, list):
            if len(value) == 0:
                continue
            target[key] = value
            continue
        if isinstance(value, dict):
            nested_target = target.get(key) if isinstance(target.get(key), dict) else {}
            target[key] = _deep_merge_non_empty(nested_target, value)
            continue
        target[key] = value

    return target


def map_scraped_data_to_project(scraped_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map scraped URL data to project schema format.
    
    Args:
        scraped_data: Data from scraper.py (scrape_url result)
        
    Returns:
        Dictionary in project schema format
    """
    project = {
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
            "twitter_card": {
                "title": "",
                "description": "",
                "image": ""
            }
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
        "international_architects": {
            "heading": "",
            "images": []
        }
    }
    
    # Map basic fields
    if scraped_data.get("title"):
        project["project_name"] = scraped_data["title"]
    
    if scraped_data.get("description"):
        project["tagline"] = scraped_data["description"]
        project["seo"]["meta_description"] = scraped_data["description"]
    
    # Map hero section
    hero = scraped_data.get("hero", {})
    if hero:
        project["hero_section"]["heading"] = hero.get("title", "")
        project["hero_section"]["subheading"] = hero.get("subtitle", "")
        project["hero_section"]["background_image"] = hero.get("image", "")
    
    # Map real estate data
    real_estate = scraped_data.get("realEstateData") or {}
    if real_estate:
        if real_estate.get("projectName"):
            project["project_name"] = real_estate["projectName"]
        
        if real_estate.get("location"):
            project["location"]["address"] = real_estate["location"]
        
        if real_estate.get("city"):
            project["location"]["city"] = real_estate["city"]
        
        if real_estate.get("state"):
            project["location"]["state"] = real_estate["state"]
        
        if real_estate.get("pincode"):
            project["location"]["pincode"] = real_estate["pincode"]
        
        if real_estate.get("address"):
            project["location"]["address"] = real_estate["address"]
        
        if real_estate.get("developer"):
            project["developer"]["name"] = real_estate["developer"]
            project["about"]["developer_info"]["name"] = real_estate["developer"]
        
        if real_estate.get("builder"):
            project["developer"]["name"] = real_estate["builder"]
        
        if real_estate.get("reraNumber"):
            project["project_info"]["rera_number"] = real_estate["reraNumber"]
            project["legal_info"]["rera_number"] = real_estate["reraNumber"]
        
        if real_estate.get("possessionDate"):
            project["project_info"]["possession_date"] = real_estate["possessionDate"]
        
        if real_estate.get("price"):
            project["project_info"]["price_range"] = real_estate["price"]
        
        if real_estate.get("area"):
            project["project_info"]["total_area"] = real_estate["area"]
        
        if real_estate.get("amenities"):
            project["amenities"] = real_estate["amenities"] if isinstance(real_estate["amenities"], list) else []
        
        if real_estate.get("contactPhone"):
            project["contact"]["phone"] = real_estate["contactPhone"]
        
        if real_estate.get("contactEmail"):
            project["contact"]["email"] = real_estate["contactEmail"]
        
        if real_estate.get("contactWhatsapp"):
            project["contact"]["whatsapp"] = real_estate["contactWhatsapp"]
        
        if real_estate.get("coordinates"):
            coords = real_estate["coordinates"]
            if isinstance(coords, dict):
                project["location"]["coordinates"]["latitude"] = str(coords.get("lat", ""))
                project["location"]["coordinates"]["longitude"] = str(coords.get("lng", ""))
    
    # Map Google Maps
    if scraped_data.get("googleMap"):
        project["location"]["map_embed_url"] = scraped_data["googleMap"]
    
    # Map images to gallery
    images = scraped_data.get("images", [])
    if images:
        project["gallery"] = [{"url": img, "type": "image"} for img in images[:20]]
    
    # Map navigation
    nav = scraped_data.get("navigation", [])
    if nav:
        project["navigation"]["main_menu"] = [
            {"name": item.get("name", ""), "url": item.get("url", "")}
            for item in nav
        ]
    
    # Map sections to project highlights
    sections = scraped_data.get("sections", [])
    if sections:
        project["project_highlights"] = [
            {"title": sec.get("title", ""), "description": sec.get("content", "")}
            for sec in sections[:10]
        ]
    
    # Map floor plans
    floor_plans = scraped_data.get("floorPlans", [])
    if floor_plans:
        project["floor_plans"] = [{"type": plan} for plan in floor_plans]
    
    # Map SEO data
    og_data = scraped_data.get("ogData", {})
    if og_data:
        project["seo"]["og_title"] = og_data.get("og:title", "")
        project["seo"]["og_description"] = og_data.get("og:description", "")
        project["seo"]["og_image"] = og_data.get("og:image", "")
    
    return project


def map_extracted_data_to_project(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map extracted file data to project schema format.
    This function tries to intelligently map extracted fields to project schema.
    
    Args:
        extracted_data: Data from file_processor.py
        
    Returns:
        Dictionary in project schema format
    """
    # Start with empty project structure
    project = map_scraped_data_to_project({})  # Get empty structure

    if not isinstance(extracted_data, dict):
        return project

    # Map common field names (case-insensitive matching)
    field_mapping = {
        "project_name": "project_name",
        "projectname": "project_name",
        "name": "project_name",
        "title": "project_name",
        "tagline": "tagline",
        "logo": "logo",
        "brand_name": "brand_name",
        "brand": "brand_name",
        "description": "about.description",
        "address": "location.address",
        "city": "location.city",
        "state": "location.state",
        "pincode": "location.pincode",
        "pin_code": "location.pincode",
        "developer": "developer.name",
        "builder": "developer.name",
        "rera": "project_info.rera_number",
        "rera_number": "project_info.rera_number",
        "price": "project_info.price_range",
        "price_range": "project_info.price_range",
        "area": "project_info.total_area",
        "total_area": "project_info.total_area",
        "phone": "contact.phone",
        "contact_phone": "contact.phone",
        "email": "contact.email",
        "contact_email": "contact.email",
        "whatsapp": "contact.whatsapp",
        "contact_whatsapp": "contact.whatsapp",
    }

    # Collect candidate key-value fields from multiple extraction shapes.
    candidates: Dict[str, Any] = {}

    def _add_candidate(key: Any, value: Any) -> None:
        if not key or value in (None, ""):
            return
        key_text = str(key).strip()
        if not key_text:
            return
        if isinstance(value, (dict, list)):
            return
        candidates[key_text] = str(value).strip()

    def _normalize_key(key: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "_", key.strip().lower())
        return normalized.strip("_")

    def _apply_target(target: str, value: str) -> None:
        if "." not in target:
            project[target] = value
            return
        parts = target.split(".")
        if len(parts) != 2:
            return
        parent, child = parts
        if parent in project and isinstance(project[parent], dict):
            project[parent][child] = value

    def _extract_from_sections(sections: Any) -> None:
        if not isinstance(sections, list):
            return
        for section in sections:
            if not isinstance(section, dict):
                continue
            for field in section.get("fields", []):
                if not isinstance(field, dict):
                    continue
                label = field.get("label") or field.get("name") or field.get("key")
                value = field.get("value")
                _add_candidate(label, value)

    def _extract_kv_from_text(raw_text: Any) -> None:
        if not isinstance(raw_text, str) or not raw_text.strip():
            return
        # Parse OCR lines like: "logo = harsh", "project_name: My Project"
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            match = re.match(r"^\s*([^:=]{1,120}?)\s*(?:=|:)\s*(.+?)\s*$", line)
            if not match:
                continue
            label = match.group(1).strip()
            value = match.group(2).strip()
            _add_candidate(label, value)

    # If extracted payload already contains project schema blocks, preserve them.
    if _is_project_schema_like(extracted_data):
        project = _deep_merge_non_empty(project, extracted_data)

    parsed_form = extracted_data.get("parsedFormData")
    if _is_project_schema_like(parsed_form):
        project = _deep_merge_non_empty(project, parsed_form)

    # 1) Direct scalar fields on current dict
    for key, value in extracted_data.items():
        if key in {"parsedFormData", "sections", "extractedText", "text"}:
            continue
        _add_candidate(key, value)

    # 2) Fields from sections (if current dict itself is parser output)
    _extract_from_sections(extracted_data.get("sections"))

    # 3) Fields from parsedFormData payload
    if isinstance(parsed_form, dict):
        # flat parsed keys
        for key, value in parsed_form.items():
            if key == "sections":
                continue
            _add_candidate(key, value)
        _extract_from_sections(parsed_form.get("sections"))

    # 4) Key-value lines from OCR/raw extracted text
    _extract_kv_from_text(extracted_data.get("extractedText"))
    _extract_kv_from_text(extracted_data.get("text"))

    # Apply mapped candidates
    for raw_key, raw_value in candidates.items():
        key_exact = raw_key.strip()
        key_normalized = _normalize_key(raw_key)
        target = field_mapping.get(key_exact) or field_mapping.get(key_normalized)
        if target and raw_value:
            _apply_target(target, raw_value)

    return project

