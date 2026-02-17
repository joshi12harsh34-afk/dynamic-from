import os
import json
import openai
from dotenv import load_dotenv

load_dotenv()

# Lazy-load OpenAI client to avoid initialization errors if API key is not set
client = None


def get_openai_client():
    """Get or create OpenAI client (lazy initialization)"""
    global client
    if not client:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise Exception('OPENAI_API_KEY is not set in environment variables')
        client = openai.OpenAI(api_key=api_key)
    return client


def safe_json_parse(text):
    """Safely parse JSON from text that might contain extra content"""
    try:
        if not text or not isinstance(text, str):
            return None
        
        # Try direct parse first
        try:
            return json.loads(text)
        except:
            # If that fails, try to extract JSON from text
            start = text.find('{')
            end = text.rfind('}')
            
            if start == -1 or end == -1 or end <= start:
                return None
            
            clean = text[start:end + 1]
            return json.loads(clean)
    except Exception as err:
        print(f'JSON parse error: {err}')
        return None


async def extract_fields_with_openai(ocr_text):
    """Extract structured fields from OCR text using OpenAI"""
    if not ocr_text or not ocr_text.strip():
        return None
    
    # Check if API key is configured
    if not os.getenv('OPENAI_API_KEY'):
        print('OPENAI_API_KEY not configured, skipping AI extraction')
        return None
    
    try:
        openai_client = get_openai_client()
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # good balance cost/performance
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

Output Format:

{{
  "sections": [
    {{
      "title": "Section Name",
      "fields": [
        {{
          "label": "Field Label",
          "value": "Field Value",
          "type": "text | number | date | email | tel",
          "unit": "optional"
        }}
      ]
    }}
  ]
}}

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

