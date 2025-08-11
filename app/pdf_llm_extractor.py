import os
import json
import tempfile
import io
import re
import subprocess
import unicodedata
import shutil
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


def _extract_orders_via_pdf_tables(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """Best-effort table extraction using pdfplumber for supplier invoices.

    Heuristic: find the largest table on the first 2 pages, map common headers to
    standardized fields, coerce qty/unit_cost, and return orders list.
    """
    try:
        import pdfplumber  # type: ignore
    except Exception:
        return []

    def normalize_header(h: str) -> str:
        s = (h or "").strip().lower()
        s = re.sub(r"[^a-z0-9#./\- ]", "", s)
        return s

    header_map = {
        # left → right variants
        "code": "part_id",
        "sku": "part_id",
        "part": "part_id",
        "part no": "part_id",
        "part no.": "part_id",
        "qty": "qty",
        "quantity": "qty",
        "unit": "qty",
        "unit price": "unit_cost",
        "unitprice": "unit_cost",
        "price": "unit_cost",
        "amount": "amount",
        "description": "notes",
        "descriptionspecification": "notes",
        "description&specification": "notes",
        "description & specification": "notes",
    }

    orders: List[Dict[str, Any]] = []
    # Detect supplier once for reuse in all rows
    supplier_name_detected: Optional[str] = _detect_supplier_name(pdf_bytes)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = pdf.pages[:2]
        for page in pages:
            tables = page.extract_tables() or []
            for tbl in tables:
                if not tbl or len(tbl) < 2:
                    continue
                # pick header row as the first non-empty row with >3 cells
                header = None
                start_idx = 1
                for i, row in enumerate(tbl[:3]):
                    if row and sum(1 for c in row if (c or "").strip()) >= 3:
                        header = [normalize_header(str(c or "")) for c in row]
                        start_idx = i + 1
                        break
                if not header:
                    continue
                # map columns (exact synonyms first)
                mapped_idx: Dict[str, int] = {}
                for j, h in enumerate(header):
                    for key, val in header_map.items():
                        if key in h and val not in mapped_idx:
                            mapped_idx[val] = j
                # fallback heuristics: any header containing 'descr' → notes
                if 'notes' not in mapped_idx:
                    for j, h in enumerate(header):
                        if 'descr' in h:
                            mapped_idx['notes'] = j
                            break
                if "part_id" not in mapped_idx or "qty" not in mapped_idx:
                    # allow fallback where part_id is absent but description present
                    if "notes" not in mapped_idx or "qty" not in mapped_idx:
                        continue
                # parse rows
                for row in tbl[start_idx:]:
                    if not row:
                        continue
                    get = lambda k: (row[mapped_idx[k]] if k in mapped_idx and mapped_idx[k] < len(row) else None)
                    part_id = str(get("part_id") or "").strip()
                    if not part_id:
                        # derive a stable slug from description/notes
                        desc = str(get("notes") or "").strip()
                        if not desc:
                            continue
                        # take first 40 chars and slugify
                        slug = re.sub(r"[^a-zA-Z0-9]+", "_", desc)[:40].strip("_")
                        part_id = slug or "UNKNOWN_PART"
                    qty_val = get("qty")
                    unit_cost_val = get("unit_cost")
                    def to_int(x):
                        try:
                            return int(float(str(x).replace(",", "").strip()))
                        except Exception:
                            return 0
                    def to_float(x):
                        try:
                            s = str(x).replace(",", "").replace("$", "").strip()
                            return float(s)
                        except Exception:
                            return 0.0
                    qty = to_int(qty_val)
                    unit_cost = to_float(unit_cost_val)
                    if qty <= 0:
                        continue
                    # Normalize notes: NFKC and collapse whitespace/newlines
                    raw_notes = str(get("notes") or "").strip() or None
                    if raw_notes:
                        normalized_notes = unicodedata.normalize("NFKC", raw_notes)
                        normalized_notes = re.sub(r"\s+", " ", normalized_notes).strip()
                    else:
                        normalized_notes = None

                    order = {
                        "part_id": part_id,
                        "supplier_id": None,
                        "supplier_name": supplier_name_detected,
                        "order_date": None,
                        "estimated_delivery_date": None,
                        "qty": qty,
                        "unit_cost": unit_cost,
                        "payment_date": None,
                        "status": "pending",
                        "po_number": None,
                        "notes": normalized_notes,
                    }
                    orders.append(order)
            if orders:
                break
    return orders


def _ensure_searchable_pdf(pdf_bytes: bytes) -> bytes:
    """If the PDF has sparse text, run optional OCR (ocrmypdf) to embed text.

    Returns original bytes on failure/unavailable.
    """
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text_len = 0
            for p in pdf.pages[:2]:
                t = p.extract_text() or ""
                text_len += len(t.strip())
            if text_len > 200:  # already has reasonable text
                return pdf_bytes
    except Exception:
        pass

    ocrmypdf_path = shutil.which("ocrmypdf")
    if not ocrmypdf_path:
        return pdf_bytes
    try:
        fd_in, path_in = tempfile.mkstemp(suffix=".pdf")
        fd_out, path_out = tempfile.mkstemp(suffix=".pdf")
        os.close(fd_in)
        os.close(fd_out)
        with open(path_in, "wb") as f:
            f.write(pdf_bytes)
        # Run OCR; use fast mode; skip already searchable pages
        cmd = [
            ocrmypdf_path,
            "--skip-text",
            "--fast",
            "--quiet",
            path_in,
            path_out,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with open(path_out, "rb") as f:
            out_bytes = f.read()
        return out_bytes or pdf_bytes
    except Exception:
        return pdf_bytes
    finally:
        try:
            if 'path_in' in locals():
                os.remove(path_in)
        except Exception:
            pass
        try:
            if 'path_out' in locals() and os.path.exists(path_out):
                os.remove(path_out)
        except Exception:
            pass


def _detect_supplier_name(pdf_bytes: bytes) -> Optional[str]:
    """Lightweight supplier detection using first two pages text and alias YAML."""
    alias_path = os.path.join(os.path.dirname(__file__), "..", "supplier_aliases.yaml")
    alias_path = os.path.abspath(alias_path)
    aliases: Dict[str, List[str]] = {}
    try:
        import yaml  # type: ignore
        if os.path.exists(alias_path):
            with open(alias_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                suppliers = data.get("suppliers", {}) or {}
                # normalize: each value must be a list of aliases
                normalized: Dict[str, List[str]] = {}
                for canonical, aka in suppliers.items():
                    if isinstance(aka, list):
                        normalized[canonical] = aka
                    elif isinstance(aka, str):
                        normalized[canonical] = [aka]
                    else:
                        normalized[canonical] = []
                aliases = normalized
    except Exception:
        aliases = {}
    text = ""
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for p in pdf.pages[:2]:
                t = p.extract_text() or ""
                text += "\n" + t
    except Exception:
        pass
    text_low = text.lower()
    try:
        from rapidfuzz import fuzz, process  # type: ignore
    except Exception:
        return None
    # Build candidates list (lowercased for case-insensitive match)
    candidates: List[str] = []
    low_to_canonical: Dict[str, str] = {}
    for canonical, aka in aliases.items():
        all_names = [canonical] + (aka or [])
        for name in all_names:
            low_name = (name or "").lower()
            if not low_name:
                continue
            candidates.append(low_name)
            # Preserve the mapping back to the canonical supplier
            low_to_canonical[low_name] = canonical
    if not candidates:
        return None
    best = process.extractOne(text_low, candidates, scorer=fuzz.partial_ratio)
    if best and best[1] >= 80:
        choice_low = best[0]
        return low_to_canonical.get(choice_low)
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
                            response_json_schema=PendingOrderSchemaJson,
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
                            response_json_schema=PendingOrderSchemaJson,
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


def _try_llms_with_text(text: str) -> Optional[Dict[str, Any]]:
    """Try Gemini then OpenAI using plain text instead of raw PDF."""
    # Gemini
    try:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if api_key:
            from google import genai
            from google.genai import types as genai_types
            client = genai.Client(api_key=api_key)
            for model_name in ["gemini-2.5-flash", "gemini-2.0-flash-001", "gemini-2.0-flash"]:
                try:
                    resp = client.models.generate_content(
                        model=model_name,
                        contents=[PROMPT + "\n\n" + text],
                        config=genai_types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION,
                            response_mime_type="application/json",
                            response_json_schema=PendingOrderSchemaJson,
                        ),
                    )
                    parsed = None
                    if hasattr(resp, "parsed") and isinstance(resp.parsed, dict):
                        parsed = resp.parsed
                    else:
                        parsed = _parse_json_from_text(getattr(resp, "text", None))
                    if parsed:
                        return parsed
                except Exception:
                    continue
    except Exception:
        pass
    # OpenAI
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            client = OpenAI(api_key=api_key)
            resp = client.responses.create(
                model="gpt-4o-mini",
                input=[{"role": "user", "content": [{"type": "input_text", "text": PROMPT + "\n\n" + text}]}],
                response_format={"type": "json_schema", "json_schema": PendingOrderSchemaJson, "strict": True},
            )
            try:
                if hasattr(resp, "output_text") and resp.output_text:
                    return json.loads(resp.output_text)
            except Exception:
                pass
            try:
                data = resp.to_dict() if hasattr(resp, "to_dict") else resp
                if isinstance(data, dict):
                    # Walk for JSON
                    stack = [data]
                    while stack:
                        cur = stack.pop()
                        if isinstance(cur, dict):
                            for v in cur.values():
                                stack.append(v)
                        elif isinstance(cur, list):
                            stack.extend(cur)
                        elif isinstance(cur, str):
                            pj = _parse_json_from_text(cur)
                            if pj:
                                return pj
            except Exception:
                pass
    except Exception:
        pass
    return None


def extract_pending_orders_from_pdf(pdf_bytes: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Attempt to extract pending orders from a PDF using a cost-first fallback chain.

    Order of attempts: Gemini 2.0 Flash → OpenAI GPT-4o mini → Gemini 2.5 Flash Lite.

    Returns a tuple of (orders, errors). Orders is a list of order dicts.
    """
    errors: List[str] = []

    # 0) Normalize PDF (OCR if needed)
    normalized_pdf = _ensure_searchable_pdf(pdf_bytes)

    # 1) Fast, deterministic path: try to read tabular rows directly from the PDF
    try:
        direct_orders = _extract_orders_via_pdf_tables(normalized_pdf)
        if direct_orders:
            return direct_orders, errors
    except Exception as e:
        errors.append(f"pdfplumber: {e}")

    # 2) Extract text and try LLMs on text only (cheaper and often more robust)
    try:
        import pdfplumber  # type: ignore
        text_all = []
        with pdfplumber.open(io.BytesIO(normalized_pdf)) as pdf:
            for p in pdf.pages[:3]:
                text_all.append(p.extract_text() or "")
        text_blob = "\n\n".join(text_all).strip()
        if text_blob:
            r = _try_llms_with_text(text_blob)
            if r and isinstance(r.get("orders"), list) and r["orders"]:
                return r["orders"], errors
    except Exception as e:
        errors.append(f"text-llm: {e}")

    for provider_name, fn in [
        ("gemini-2.0-flash", _try_gemini_flash),
        ("gpt-4o-mini", _try_openai_gpt4o_mini),
        ("gemini-2.5-flash-lite", _try_gemini_flash_lite),
    ]:
        try:
            result = fn(normalized_pdf)
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

    # Final fallback: loose extraction without schema
    try:
        from google import genai
        from google.genai import types as genai_types
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
            tmp_path = _write_temp_pdf(pdf_bytes)
            try:
                file_obj = client.files.upload(file=tmp_path)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[file_obj, PROMPT],
                    config=genai_types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                    ),
                )
                parsed = _parse_json_from_text(getattr(response, "text", None))
                if parsed and isinstance(parsed.get("orders"), list):
                    return parsed["orders"], errors
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
    except Exception:
        pass

    return [], errors


