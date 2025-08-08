import os
import json
import tempfile
from typing import Any, Dict, List, Tuple, Optional


PendingOrderSchemaJson: Dict[str, Any] = {
    "type": "object",
    "title": "PendingOrdersExtraction",
    "properties": {
        "orders": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "part_id": {"type": "string"},
                    "supplier_id": {"type": ["string", "null"]},
                    "supplier_name": {"type": ["string", "null"]},
                    "order_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "estimated_delivery_date": {"type": ["string", "null"], "description": "YYYY-MM-DD or null"},
                    "qty": {"type": "integer"},
                    "unit_cost": {"type": ["number", "string"]},
                    "payment_date": {"type": ["string", "null"], "description": "YYYY-MM-DD or null"},
                    "status": {"type": ["string", "null"], "description": "pending|ordered|received|cancelled"},
                    "po_number": {"type": ["string", "null"]},
                    "notes": {"type": ["string", "null"]}
                },
                "required": ["part_id", "order_date", "qty"],
                "additionalProperties": True
            }
        }
    },
    "required": ["orders"],
    "additionalProperties": False
}


SYSTEM_INSTRUCTION = (
    "You extract pending purchase order information from supplier invoices or quotes. "
    "Return strictly JSON that conforms to the provided schema. "
    "Dates must be ISO YYYY-MM-DD. Use 'pending' status when not specified. "
    "Map any reasonable line-item fields to the schema. Use unit currency values as numbers."
)

PROMPT = (
    "Extract all line items as pending purchase orders.\n"
    "Infer fields when headers vary (e.g., SKU/Item/Part No → part_id; QTY/Quantity → qty; Unit Price → unit_cost;\n"
    "Date/Order Date/Invoice Date → order_date; Delivery/ETA → estimated_delivery_date).\n"
    "Normalize: strip currency symbols and thousands separators; parse integers for qty; parse floats for unit_cost.\n"
    "If supplier name is visible in the document header/footer, set supplier_name accordingly; otherwise null.\n"
    "Output a JSON object with an 'orders' array only."
)


def _parse_json_from_text(text: Optional[str]) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try to locate a JSON object substring
    try:
        import re
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group(0))
    except Exception:
        return None
    return None


def _write_temp_pdf(pdf_bytes: bytes, filename_hint: str = "upload.pdf") -> str:
    fd, path = tempfile.mkstemp(suffix=".pdf", prefix="sx_", text=False)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(pdf_bytes)
    except Exception:
        # Ensure file handle is closed on error
        try:
            os.close(fd)
        except Exception:
            pass
        raise
    return path


def _try_gemini_flash(pdf_bytes: bytes) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        # Lazy import so that environments without the SDK still work for other providers
        from google import genai
        from google.genai import types as genai_types

        client = genai.Client(api_key=api_key)
        tmp_path = _write_temp_pdf(pdf_bytes)
        try:
            file_obj = client.files.upload(file=tmp_path)
            # Try multiple commonly used model ids for compatibility
            candidate_models = [
                "gemini-2.0-flash-001",
                "gemini-2.0-flash",
                "gemini-2.5-flash",
            ]
            for model_name in candidate_models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[file_obj, PROMPT],
                        config=genai_types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION,
                            response_mime_type="application/json",
                        ),
                    )
                    parsed = None
                    if hasattr(response, "parsed") and isinstance(response.parsed, dict):
                        parsed = response.parsed
                    else:
                        text = getattr(response, "text", None)
                        parsed = _parse_json_from_text(text)
                    if parsed:
                        return parsed
                except Exception:
                    continue
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    except Exception:
        return None
    return None


def _try_openai_gpt4o_mini(pdf_bytes: bytes) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        # Upload PDF for Responses API
        upload = client.files.create(file=("invoice.pdf", pdf_bytes), purpose="assistants")
        schema = PendingOrderSchemaJson
        # Use Responses API with file input and JSON schema enforcement
        resp = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": SYSTEM_INSTRUCTION},
                        {"type": "input_file", "file_id": upload.id},
                    ],
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": schema,
                "strict": True,
            },
        )
        # Extract the JSON result (robust across SDK versions)
        try:
            if hasattr(resp, "output_text") and resp.output_text:
                return json.loads(resp.output_text)
        except Exception:
            pass
        try:
            data = resp.to_dict() if hasattr(resp, "to_dict") else resp  # type: ignore
            if isinstance(data, dict):
                # Walk for any string that looks like JSON with 'orders'
                import re
                text_candidates: List[str] = []
                def _walk(obj):
                    if isinstance(obj, dict):
                        for v in obj.values():
                            _walk(v)
                    elif isinstance(obj, list):
                        for v in obj:
                            _walk(v)
                    elif isinstance(obj, str):
                        if '"orders"' in obj or 'orders' in obj:
                            text_candidates.append(obj)
                _walk(data)
                for t in text_candidates:
                    try:
                        return json.loads(t)
                    except Exception:
                        continue
        except Exception:
            pass
    except Exception:
        return None
    return None


def _try_gemini_flash_lite(pdf_bytes: bytes) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types as genai_types

        client = genai.Client(api_key=api_key)
        tmp_path = _write_temp_pdf(pdf_bytes)
        try:
            file_obj = client.files.upload(file=tmp_path)
            candidate_models = [
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash-lite-001",
                "gemini-2.5-flash",
            ]
            for model_name in candidate_models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[file_obj, PROMPT],
                        config=genai_types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION,
                            response_mime_type="application/json",
                        ),
                    )
                    parsed = None
                    if hasattr(response, "parsed") and isinstance(response.parsed, dict):
                        parsed = response.parsed
                    else:
                        text = getattr(response, "text", None)
                        parsed = _parse_json_from_text(text)
                    if parsed:
                        return parsed
                except Exception:
                    continue
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    except Exception:
        return None
    return None


def extract_pending_orders_from_pdf(pdf_bytes: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Attempt to extract pending orders from a PDF using a cost-first fallback chain.

    Order of attempts: Gemini 2.0 Flash → OpenAI GPT-4o mini → Gemini 2.5 Flash Lite.

    Returns a tuple of (orders, errors). Orders is a list of order dicts.
    """
    errors: List[str] = []

    for provider_name, fn in [
        ("gemini-2.0-flash", _try_gemini_flash),
        ("gpt-4o-mini", _try_openai_gpt4o_mini),
        ("gemini-2.5-flash-lite", _try_gemini_flash_lite),
    ]:
        try:
            result = fn(pdf_bytes)
            if result and isinstance(result, dict):
                orders = result.get("orders")
                if isinstance(orders, list) and len(orders) > 0:
                    return orders, errors
                else:
                    errors.append(f"{provider_name}: empty or missing 'orders' array")
            else:
                errors.append(f"{provider_name}: no result")
        except Exception as e:
            errors.append(f"{provider_name}: {e}")

    return [], errors


