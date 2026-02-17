from playwright.async_api import async_playwright


async def scrape_url(url):
    """
    Scrape URL and extract metadata
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        try:
            # Try 'load' first (waits for page load event)
            # If that fails, fall back to 'domcontentloaded' (more lenient)
            try:
                await page.goto(url, wait_until='load', timeout=60000)
            except Exception:
                # Fallback to domcontentloaded if load times out
                print('Load timeout, trying domcontentloaded...')
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Extract metadata
            title = await page.title()
            
            # Get description from meta tag
            description = ''
            try:
                desc_element = page.locator('meta[name="description"]')
                if await desc_element.count() > 0:
                    description = await desc_element.get_attribute('content') or ''
            except:
                pass
            
            # Extract images
            images = await page.evaluate("""
                () => {
                    const imgs = Array.from(document.querySelectorAll('img'));
                    return imgs
                        .map(img => img.src)
                        .filter(src => src && src.length > 0);
                }
            """)
            
            # Basic type detection
            type_detected = 'article'
            if 'product' in url.lower() or 'buy' in title.lower():
                type_detected = 'product'
            if 'profile' in url.lower():
                type_detected = 'profile'
            
            return {
                'title': title,
                'description': description,
                'images': images,
                'type': type_detected
            }
            
        except Exception as err:
            print(f'Scraper error: {err}')
            return {
                'title': '',
                'description': '',
                'images': [],
                'type': 'article'
            }
        finally:
            await browser.close()

