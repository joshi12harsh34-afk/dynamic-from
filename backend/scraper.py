# scraper.py
"""
Web scraper module for extracting structured data from URLs.
Enhanced with specialized real estate data extraction capabilities.

This module uses Playwright to scrape web pages and extract:
- Basic metadata (title, description, images)
- Open Graph tags
- JSON-LD structured data
- Real estate specific information (prices, BHK, location, etc.)
"""

from playwright.async_api import async_playwright
import re
import json

async def get_internal_links(page, base_url, keywords=None, limit=10):
    """
    Extract internal links from a page that match real estate keywords.
    
    Args:
        page: Playwright page object
        base_url (str): Base URL to filter internal links
        keywords (list): Keywords to filter links (default: real estate related)
        limit (int): Maximum number of links to return
        
    Returns:
        list: List of filtered internal links
    """
    keywords = keywords or ["about", "amenities", "floor", "plan", "location", "contact", "gallery"]
    links = await page.evaluate("""() => Array.from(document.querySelectorAll('a')).map(a => a.href)""")
    internal_links = [link for link in links if link.startswith(base_url)]
    filtered_links = [link for link in internal_links if any(k in link.lower() for k in keywords)]
    return list(dict.fromkeys(filtered_links))[:limit]


async def scrape_url_multis(page_url, max_pages=5):
    """
    Crawl main page + relevant internal pages for real estate data.
    
    This function crawls multiple pages from a real estate website to aggregate
    comprehensive data from different sections (about, amenities, floor plans, etc.).
    
    Args:
        page_url (str): The main URL to start crawling from
        max_pages (int): Maximum number of pages to crawl (default: 5)
        
    Returns:
        dict: Aggregated data from all crawled pages containing:
            - urlsCrawled: List of URLs that were scraped
            - images: Aggregated images from all pages (deduplicated)
            - sections: Aggregated sections from all pages (deduplicated)
            - realEstateData: Merged real estate data (most complete from all pages)
    """
    visited = set()
    to_visit = [page_url]
    aggregated_data = {
        "outputFormat": "json",
        "urlsCrawled": [],
        "images": [],
        "sections": [],
        "realEstateData": {},
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        while to_visit and len(visited) < max_pages:
            url = to_visit.pop(0)
            if url in visited:
                continue

            page = await context.new_page()
            try:
                # Try multiple wait strategies for reliability
                try:
                    await page.goto(url, wait_until="networkidle", timeout=60000)
                except Exception:
                    try:
                        await page.goto(url, wait_until="load", timeout=60000)
                    except Exception:
                        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                await page.wait_for_timeout(2000)

                # Call single-page scraper with the page object
                page_data = await scrape_url_single_page(url, page=page)
                visited.add(url)
                aggregated_data["urlsCrawled"].append(url)

                # Aggregate images
                aggregated_data["images"].extend(page_data.get("images", []))

                # Aggregate sections
                aggregated_data["sections"].extend(page_data.get("sections", []))

                # Merge real estate data (prefer non-empty values)
                for key, value in page_data.get("realEstateData", {}).items():
                    if value and not aggregated_data["realEstateData"].get(key):
                        aggregated_data["realEstateData"][key] = value

                # Get internal links for further crawling
                base_url = re.match(r"(https?://[^/]+)", url).group(1)
                links = await get_internal_links(page, base_url)
                for link in links:
                    if link not in visited and link not in to_visit:
                        to_visit.append(link)

            except Exception as e:
                print(f"Error scraping {url}: {e}")
            finally:
                await page.close()

        await browser.close()

    # Deduplicate images and sections
    aggregated_data["images"] = list(dict.fromkeys(aggregated_data["images"]))
    aggregated_data["sections"] = [dict(t) for t in {tuple(d.items()) for d in aggregated_data["sections"]}]

    return aggregated_data


async def scrape_url_single_page(url, page=None):
    """
    Scrape a single URL and extract structured metadata + content.
    Enhanced for real estate website data extraction.
    
    Args:
        url (str): The URL to scrape
        page: Optional Playwright page object (if provided, won't create new browser)
        
    Returns:
        dict: Dictionary containing:
            - url: Original URL
            - title: Page title
            - description: Meta description or OG description
            - hero: Hero section data (title, subtitle, image)
            - navigation: Navigation menu links
            - sections: Page sections with headings and content
            - googleMap: Google Maps embed URL if present
            - floorPlans: Detected floor plans from text
            - images: List of image URLs (max 30)
            - type: Detected page type (real_estate, product, article, etc.)
            - ogData: Open Graph metadata
            - structuredData: JSON-LD structured data
            - textContent: Main text content (max 20000 chars)
            - realEstateData: Real estate specific data (if type is real_estate)
    """
    # If page is provided, use it; otherwise create a new browser context
    should_close_browser = False
    browser = None
    playwright = None
    if page is None:
        should_close_browser = True
        playwright = await async_playwright().start()
        # Launch browser in headless mode for server-side scraping
        browser = await playwright.chromium.launch(headless=True)
        
        # Create browser context with realistic user agent to avoid bot detection
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

    try:
        # Navigate to URL if page was provided (it may already be on the URL) or if it's a new page
        current_url = page.url if hasattr(page, 'url') else ""
        if current_url != url:
            # Try multiple wait strategies for better reliability
            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception:
                try:
                    await page.goto(url, wait_until="load", timeout=60000)
                except Exception:
                    print("Load timeout, trying domcontentloaded...")
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Wait for dynamic content to load (especially for SPAs and React/Vue apps)
        await page.wait_for_timeout(3000)
        
        # Scroll to trigger lazy loading of images and content
        # Many real estate sites use lazy loading for images and listings
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1000)
        await page.evaluate("window.scrollTo(0, 0)")

        # Extract page title
        title = await page.title()

        # Extract description from meta tags with Open Graph fallback
        # OG tags are often more accurate for social sharing
        description = await page.evaluate("""
            () => {
                const metaDesc = document.querySelector('meta[name="description"]');
                const ogDesc = document.querySelector('meta[property="og:description"]');
                return (metaDesc?.content || ogDesc?.content || "").trim();
            }
        """)

        # Extract main text content for parsing and LLM processing
        # Increased limit to 30000 chars for real estate sites which often have detailed descriptions
        text_content = await page.evaluate("""
            () => {
                const bodyText = document.body.innerText || "";
                return bodyText.substring(0, 30000); // increased limit for real estate
            }
        """)

        # Extract images including lazy-loaded images with comprehensive detection
        # Handles multiple lazy loading patterns used by modern websites
        images = await page.evaluate("""
            () => {
                const imgs = Array.from(document.querySelectorAll('img'));
                const sources = Array.from(document.querySelectorAll('source[srcset]'));
                const imageSet = new Set();
                
                // Regular images - check multiple data attributes for lazy loading
                imgs.forEach(img => {
                    const src = img.src || img.dataset.src || img.dataset.lazy || 
                               img.dataset.original || img.getAttribute('data-lazy-src') || "";
                    if (src && (src.startsWith("http") || src.startsWith("//"))) {
                        // Normalize protocol-relative URLs
                        imageSet.add(src.startsWith("//") ? "https:" + src : src);
                    }
                });
                
                // Source elements with srcset (responsive images)
                sources.forEach(source => {
                    const srcset = source.srcset || "";
                    srcset.split(',').forEach(src => {
                        // Extract URL from srcset (format: "url width" or "url 2x")
                        const url = src.trim().split(' ')[0];
                        if (url && (url.startsWith("http") || url.startsWith("//"))) {
                            imageSet.add(url.startsWith("//") ? "https:" + url : url);
                        }
                    });
                });
                
                return Array.from(imageSet);
            }
        """)

        # Remove duplicates and filter out non-content images (icons, logos, avatars)
        images = list(set(images))
        images = [img for img in images if img and not any(ext in img.lower() for ext in ['.svg', 'icon', 'logo', 'avatar'])]

        # Extract Open Graph metadata for social sharing
        # OG tags provide structured metadata about the page
        og_data = await page.evaluate("""
            () => {
                const ogTags = {};
                document.querySelectorAll('meta[property^="og:"]').forEach(tag => {
                    ogTags[tag.getAttribute('property')] = tag.content;
                });
                return ogTags;
            }
        """)

        # Extract JSON-LD structured data (Schema.org format)
        # This is very powerful as it provides machine-readable structured data
        # Many real estate sites use this for SEO and rich snippets
        structured_data = await page.evaluate("""
            () => {
                const scripts = Array.from(
                    document.querySelectorAll('script[type="application/ld+json"]')
                );
                return scripts.map(s => {
                    try {
                        return JSON.parse(s.innerText);
                    } catch {
                        return null;
                    }
                }).filter(Boolean);
            }
        """)

        # Detect page type using multiple signals (URL, title, structured data, text)
        type_detected = detect_page_type(url, title, structured_data, text_content)

        # Extract real estate specific data if page is detected as real estate
        # This includes prices, BHK, location, developer info, etc.
        real_estate_data = {}
        if type_detected == "real_estate":
            real_estate_data = await extract_real_estate_data(page, text_content, structured_data)

        # Extract additional page structure elements (hero, navigation, sections, etc.)
        hero = await page.evaluate("""
            () => {
                const h1 = document.querySelector("h1");
                const subtitle = document.querySelector("h2, .subtitle, .tagline");
                const heroImage = document.querySelector("header img, .hero img, .banner img");

                return {
                    title: h1 ? h1.innerText.trim() : "",
                    subtitle: subtitle ? subtitle.innerText.trim() : "",
                    image: heroImage ? heroImage.src : ""
                };
            }
        """)

        # Extract navigation menu
        navigation = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll("nav a"));
                return links
                    .map(a => ({
                        name: a.innerText.trim(),
                        url: a.href
                    }))
                    .filter(a => a.name.length > 0)
                    .slice(0, 20);
            }
        """)

        # Extract sections from page
        sections = await page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll("section, div").forEach(sec => {
                    const heading = sec.querySelector("h1, h2, h3");
                    if (heading && heading.innerText.length < 80) {
                        results.push({
                            title: heading.innerText.trim(),
                            content: (sec.innerText || "").substring(0, 400)
                        });
                    }
                });
                return results.slice(0, 25);
            }
        """)

        # Extract Google Maps iframe
        google_map = await page.evaluate("""
            () => {
                const map = document.querySelector("iframe[src*='google.com/maps']");
                return map ? map.src : "";
            }
        """)

        # Detect floor plans from text content
        floor_plans = list(set(re.findall(r'\d+\s*(?:BHK|Bedroom|Bed)', text_content, re.IGNORECASE)))

        return {
            "outputFormat": "json",
            "url": url,
            "title": title,
            "description": description,
            "hero": hero,
            "navigation": navigation,
            "sections": sections,
            "googleMap": google_map,
            "floorPlans": floor_plans,
            "images": images[:30],
            "type": type_detected,
            "ogData": og_data,
            "structuredData": structured_data,
            "textContent": text_content[:20000],
            "realEstateData": real_estate_data if real_estate_data else None
        }

    except Exception as err:
        print(f"Scraper error: {err}")
        import traceback
        traceback.print_exc()
        return {
            "outputFormat": "json",
            "url": url,
            "title": "",
            "description": "",
            "hero": {},
            "navigation": [],
            "sections": [],
            "googleMap": "",
            "floorPlans": [],
            "images": [],
            "type": "unknown",
            "ogData": {},
            "structuredData": [],
            "textContent": "",
            "realEstateData": None
        }

    finally:
        if should_close_browser and browser:
            await browser.close()
            if playwright:
                await playwright.stop()


async def extract_real_estate_data(page, text_content, structured_data):
    """
    Extract real estate specific data from the page using multiple extraction strategies.
    
    Uses three complementary approaches:
    1. DOM-based extraction using common CSS selectors
    2. Text parsing using regex patterns
    3. Structured data extraction from JSON-LD
    
    Args:
        page: Playwright page object
        text_content (str): Full text content of the page
        structured_data (list): JSON-LD structured data from the page
        
    Returns:
        dict: Dictionary containing real estate fields like:
            - projectName, price, bhk, area, location
            - developer, reraNumber, possessionDate
            - amenities, contact info, coordinates
    """
    try:
        # Strategy 1: Extract data using DOM selectors (common class/id patterns)
        # This works well for sites with semantic HTML
        extracted = await page.evaluate("""
            () => {
                const data = {
                    projectName: "",
                    price: "",
                    priceRange: "",
                    bhk: [],
                    area: "",
                    areaRange: "",
                    location: "",
                    address: "",
                    city: "",
                    state: "",
                    pincode: "",
                    developer: "",
                    builder: "",
                    reraNumber: "",
                    possessionDate: "",
                    projectStatus: "",
                    amenities: [],
                    contactPhone: "",
                    contactEmail: "",
                    contactWhatsapp: "",
                    coordinates: { lat: "", lng: "" }
                };

                // Extract from common class/id patterns
                const selectors = {
                    projectName: [
                        '[class*="project-name"]', '[class*="projectName"]', '[class*="project_title"]',
                        'h1', '.heading', '[data-project-name]', '[id*="project"]'
                    ],
                    price: [
                        '[class*="price"]', '[class*="Price"]', '[data-price]',
                        '[class*="starting-price"]', '[class*="cost"]'
                    ],
                    location: [
                        '[class*="location"]', '[class*="Location"]', '[class*="address"]',
                        '[class*="Address"]', '[data-location]'
                    ],
                    developer: [
                        '[class*="developer"]', '[class*="Developer"]', '[class*="builder"]',
                        '[class*="Builder"]', '[data-developer]'
                    ],
                    amenities: [
                        '[class*="amenity"]', '[class*="Amenity"]', '[class*="facility"]',
                        '[class*="Facility"]', '[data-amenities]'
                    ]
                };

                // Extract project name
                for (const sel of selectors.projectName) {
                    const el = document.querySelector(sel);
                    if (el && el.textContent.trim()) {
                        data.projectName = el.textContent.trim();
                        break;
                    }
                }

                // Extract price
                for (const sel of selectors.price) {
                    const el = document.querySelector(sel);
                    if (el) {
                        const text = el.textContent.trim();
                        if (text && /[₹$€£]|cr|lakh|crore|million/i.test(text)) {
                            data.price = text;
                            break;
                        }
                    }
                }

                // Extract location
                for (const sel of selectors.location) {
                    const el = document.querySelector(sel);
                    if (el && el.textContent.trim()) {
                        data.location = el.textContent.trim();
                        break;
                    }
                }

                // Extract developer
                for (const sel of selectors.developer) {
                    const el = document.querySelector(sel);
                    if (el && el.textContent.trim()) {
                        data.developer = el.textContent.trim();
                        break;
                    }
                }

                // Extract amenities
                const amenityElements = document.querySelectorAll(selectors.amenities.join(','));
                amenityElements.forEach(el => {
                    const text = el.textContent.trim();
                    if (text && text.length < 100) {
                        data.amenities.push(text);
                    }
                });

                // Extract contact info from links
                const phoneLinks = document.querySelectorAll('a[href^="tel:"]');
                if (phoneLinks.length > 0) {
                    data.contactPhone = phoneLinks[0].href.replace('tel:', '').trim();
                }

                const emailLinks = document.querySelectorAll('a[href^="mailto:"]');
                if (emailLinks.length > 0) {
                    data.contactEmail = emailLinks[0].href.replace('mailto:', '').trim();
                }

                // Extract from meta tags
                const metaTags = {
                    'real-estate:price': 'price',
                    'real-estate:location': 'location',
                    'real-estate:developer': 'developer',
                    'property:price': 'price',
                    'property:location': 'location'
                };

                Object.keys(metaTags).forEach(prop => {
                    const meta = document.querySelector(`meta[property="${prop}"], meta[name="${prop}"]`);
                    if (meta && meta.content) {
                        data[metaTags[prop]] = meta.content;
                    }
                });

                return data;
            }
        """)
        

        # Strategy 2: Parse text content using regex patterns
        # This catches data that might not be in semantic HTML elements
        text_data = parse_real_estate_text(text_content)
        
        # Merge extracted data with text parsed data (text parsing fills gaps)
        for key, value in text_data.items():
            if value and not extracted.get(key):
                extracted[key] = value

        # Strategy 3: Extract from structured data (JSON-LD Schema.org format)
        # This is the most reliable source when available
        structured_extracted = extract_from_structured_data(structured_data)
        for key, value in structured_extracted.items():
            if value and not extracted.get(key):
                extracted[key] = value

        return extracted

    except Exception as err:
        print(f"Error extracting real estate data: {err}")
        return {}


def parse_real_estate_text(text):
    """
    Parse real estate data from text content using regex patterns.
    
    Extracts common real estate fields like:
    - BHK configuration (1BHK, 2BHK, etc.)
    - Price (with currency symbols and Indian formats like lakh/crore)
    - Area (sqft, sqm)
    - RERA numbers
    - Possession dates
    - Contact information (phone, email)
    - Location details (city, pincode)
    - Project status
    
    Args:
        text (str): Text content to parse
        
    Returns:
        dict: Dictionary with extracted real estate fields
    """
    data = {
        "projectName": "",
        "price": "",
        "priceRange": "",
        "bhk": [],
        "area": "",
        "areaRange": "",
        "location": "",
        "address": "",
        "city": "",
        "state": "",
        "pincode": "",
        "developer": "",
        "builder": "",
        "reraNumber": "",
        "possessionDate": "",
        "projectStatus": "",
        "amenities": [],
        "contactPhone": "",
        "contactEmail": "",
        "contactWhatsapp": ""
    }

    if not text:
        return data

    text_lower = text.lower()

    # Extract BHK (Bedroom Hall Kitchen) configuration
    # Matches patterns like "2 BHK", "3 Bedroom", "4 Bed"
    bhk_matches = re.findall(r'(\d+)\s*(?:bhk|bedroom|bed)', text, re.IGNORECASE)
    if bhk_matches:
        data["bhk"] = list(set([m[0] if isinstance(m, tuple) else m for m in bhk_matches]))

    # Extract price with multiple patterns to handle different formats
    # Handles: ₹50 Lakh, $500K, 2.5 Crore, Starting price: 1.2 Cr
    price_patterns = [
        r'[₹$€£]\s*(\d+(?:[.,]\d+)*(?:\s*(?:lakh|crore|million|cr|L|Cr))?)',
        r'(?:starting\s*)?(?:price|cost|from)\s*[₹$€£]?\s*(\d+(?:[.,]\d+)*(?:\s*(?:lakh|crore|million|cr|L|Cr))?)',
        r'(\d+(?:[.,]\d+)*)\s*(?:lakh|crore|million|cr|L|Cr)'
    ]
    for pattern in price_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data["price"] = match.group(0)
            break

    # Extract area in square feet or square meters
    # Handles: 1200 sqft, 150 sq. m, 2000 square feet
    area_patterns = [
        r'(\d+(?:[.,]\d+)*)\s*(?:sq\.?\s*ft|sqft|sq\.?\s*m|sqm|square\s*feet|square\s*meter)',
        r'(?:area|size|carpet|super)\s*(?:area)?\s*:?\s*(\d+(?:[.,]\d+)*)\s*(?:sq\.?\s*ft|sqft|sq\.?\s*m|sqm)'
    ]
    for pattern in area_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data["area"] = match.group(0)
            break

    # Extract RERA (Real Estate Regulatory Authority) number
    # Format: State code/Project code/Year/Number (e.g., UP/01/1234/2020)
    rera_match = re.search(r'rera\s*(?:no|number|id)?\s*:?\s*([A-Z]{2,4}/?[A-Z]{2,4}/?\d{4,8}/\d{4})', text, re.IGNORECASE)
    if rera_match:
        data["reraNumber"] = rera_match.group(1)

    # Extract possession date in various formats
    # Handles: DD/MM/YYYY, DD-MM-YYYY, Month YYYY
    possession_patterns = [
        r'possession\s*(?:date|by)?\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'ready\s*(?:to\s*)?move\s*(?:in)?\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'possession\s*(?:date|by)?\s*:?\s*([A-Z][a-z]+\s+\d{4})'
    ]
    for pattern in possession_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data["possessionDate"] = match.group(1)
            break

    # Extract phone numbers with international and Indian formats
    # Handles: +91-9876543210, (123) 456-7890, 9876543210
    phone_patterns = [
        r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
        r'\+91[-.\s]?\d{10}',  # Indian format with country code
        r'\d{10}'  # Simple 10-digit number
    ]
    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        if matches:
            data["contactPhone"] = matches[0]
            break

    # Extract email addresses
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if email_match:
        data["contactEmail"] = email_match.group(0)

    # Extract Indian pincode (6 digits)
    pincode_match = re.search(r'\b\d{6}\b', text)
    if pincode_match:
        data["pincode"] = pincode_match.group(0)

    # Extract city from common Indian metropolitan cities
    # Checks if any major city name appears in the text
    cities = ['mumbai', 'delhi', 'bangalore', 'hyderabad', 'chennai', 'kolkata', 'pune', 
              'ahmedabad', 'jaipur', 'surat', 'lucknow', 'kanpur', 'nagpur', 'indore',
              'thane', 'bhopal', 'visakhapatnam', 'patna', 'vadodara', 'ghaziabad']
    for city in cities:
        if city in text_lower:
            data["city"] = city.title()
            break

    # Extract project status (ready to move, under construction, etc.)
    status_keywords = {
        'ready to move': 'ready_to_move',
        'under construction': 'under_construction',
        'new launch': 'new_launch',
        'pre launch': 'pre_launch',
        'upcoming': 'upcoming'
    }
    for keyword, status in status_keywords.items():
        if keyword in text_lower:
            data["projectStatus"] = status
            break

    return data


def extract_from_structured_data(structured_data):
    """
    Extract real estate data from JSON-LD structured data (Schema.org format).
    
    JSON-LD is the most reliable source as it's machine-readable structured data.
    Many real estate websites use Schema.org types like:
    - RealEstateAgent
    - ApartmentComplex
    - Residence
    
    Args:
        structured_data (list): List of JSON-LD objects from the page
        
    Returns:
        dict: Dictionary with extracted real estate fields from structured data
    """
    data = {}
    
    for item in structured_data:
        if not isinstance(item, dict):
            continue
            
        # Check if this is a real estate related schema type
        schema_type = item.get("@type", "").lower()
        
        if "realestate" in schema_type or "apartment" in schema_type or "residence" in schema_type:
            # Extract name
            if "name" in item:
                data["projectName"] = item["name"]
            
            # Extract address
            if "address" in item:
                addr = item["address"]
                if isinstance(addr, dict):
                    data["address"] = addr.get("streetAddress", "")
                    data["city"] = addr.get("addressLocality", "")
                    data["state"] = addr.get("addressRegion", "")
                    data["pincode"] = addr.get("postalCode", "")
                elif isinstance(addr, str):
                    data["address"] = addr
            
            # Extract price
            if "price" in item:
                price = item["price"]
                if isinstance(price, dict):
                    data["price"] = str(price.get("value", ""))
                else:
                    data["price"] = str(price)
            
            # Extract area
            if "floorSize" in item:
                floor_size = item["floorSize"]
                if isinstance(floor_size, dict):
                    data["area"] = str(floor_size.get("value", ""))
                else:
                    data["area"] = str(floor_size)
            
            # Extract geo coordinates
            if "geo" in item:
                geo = item["geo"]
                if isinstance(geo, dict):
                    data["coordinates"] = {
                        "lat": str(geo.get("latitude", "")),
                        "lng": str(geo.get("longitude", ""))
                    }
            
            # Extract number of rooms
            if "numberOfRooms" in item:
                data["bhk"] = [str(item["numberOfRooms"])]
    
    return data


def detect_page_type(url, title, structured_data, text):
    """
    Intelligent page type detection with enhanced real estate detection.
    
    Uses multiple signals in order of reliability:
    1. JSON-LD structured data (most reliable)
    2. URL patterns
    3. Text content patterns
    
    Args:
        url (str): Page URL
        title (str): Page title
        structured_data (list): JSON-LD structured data
        text (str): Page text content
        
    Returns:
        str: Detected page type: "real_estate", "product", "article", "profile", or "article" (default)
    """

    url_lower = url.lower()
    title_lower = title.lower()
    text_lower = text.lower() if text else ""

    # Strategy 1: Check structured data (JSON-LD) - most reliable
    # Schema.org types are explicitly defined by the website
    for item in structured_data:
        if isinstance(item, dict):
            schema_type = item.get("@type", "").lower()
            if "product" in schema_type:
                return "product"
            if any(keyword in schema_type for keyword in ["realestate", "apartment", "residence", "house", "property"]):
                return "real_estate"
            if "article" in schema_type:
                return "article"

    # Strategy 2: URL-based detection - enhanced for real estate
    # Check for real estate keywords in URL path
    real_estate_url_keywords = [
        "property", "project", "residences", "apartment", "flat", "villa", 
        "builder", "developer", "real-estate", "realestate", "housing",
        "residential", "commercial", "plot", "land", "construction"
    ]
    
    if any(word in url_lower for word in real_estate_url_keywords):
        return "real_estate"

    # Check for other page types in URL
    if any(word in url_lower for word in ["product", "shop", "buy"]):
        return "product"

    if any(word in url_lower for word in ["profile", "author", "team"]):
        return "profile"

    # Strategy 3: Text content pattern matching - enhanced for real estate
    # Look for real estate specific terms in the page content
    real_estate_text_signals = [
        r"\b\d+\s*bhk\b",  # BHK configuration
        r"\b\d+\s*bedroom\b",  # Bedroom count
        r"rera\s*(?:no|number)",  # RERA number mention
        r"possession\s*(?:date|by)",  # Possession date
        r"sq\.?\s*ft|sqft",  # Area in square feet
        r"starting\s*price",  # Price mention
        r"project\s*(?:name|by)",  # Project name
        r"builder|developer",  # Developer/builder
        r"ready\s*to\s*move",  # Ready to move status
        r"under\s*construction"  # Under construction status
    ]
    
    for pattern in real_estate_text_signals:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return "real_estate"

    # Default to article if no specific type detected
    return "article"


async def scrape_url(url, multi_page=False, max_pages=5):
    """
    Main entry point for URL scraping.
    
    This function provides a unified interface for both single-page and multi-page scraping.
    By default, it performs single-page scraping. Set multi_page=True for comprehensive
    multi-page crawling (useful for real estate websites with data spread across pages).
    
    Args:
        url (str): The URL to scrape
        multi_page (bool): If True, crawl multiple pages (default: False)
        max_pages (int): Maximum pages to crawl if multi_page=True (default: 5)
        
    Returns:
        dict: Scraped data (single page or aggregated multi-page data)
    """
    if multi_page:
        # Use multi-page crawling for comprehensive data extraction
        return await scrape_url_multis(url, max_pages=max_pages)
    else:
        # Use single-page scraping (faster, good for most cases)
        return await scrape_url_single_page(url)
