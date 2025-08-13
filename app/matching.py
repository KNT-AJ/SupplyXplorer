from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

try:
    from rapidfuzz import process, fuzz  # type: ignore
except Exception:  # pragma: no cover
    process = None
    fuzz = None

from sqlalchemy.orm import Session
from app.models import Inventory, PartAlias, Order


def _norm(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    # collapse whitespace
    s = " ".join(s.split())
    return s


@dataclass
class InventoryIndex:
    all_ids: List[str]
    all_names: List[str]
    # Quick membership for exact checks
    id_set: set
    # Supplier buckets: supplier_name -> list of candidate strings (ids+names)
    by_supplier: Dict[str, List[str]]
    # Map from candidate string back to canonical part_id
    key_to_part: Dict[str, str]


def build_inventory_index(db: Session) -> InventoryIndex:
    items: List[Inventory] = db.query(Inventory).all()
    all_ids: List[str] = []
    all_names: List[str] = []
    key_to_part: Dict[str, str] = {}
    by_supplier: Dict[str, List[str]] = {}

    for inv in items:
        pid = inv.part_id
        pname = inv.part_name or ""
        all_ids.append(pid)
        all_names.append(pname)
        key_to_part[pid] = pid
        if pname and pname not in key_to_part:
            key_to_part[pname] = pid
        sname = _norm(inv.supplier_name)
        if sname not in by_supplier:
            by_supplier[sname] = []
        by_supplier[sname].append(pid)
        if pname:
            by_supplier[sname].append(pname)

    return InventoryIndex(
        all_ids=all_ids,
        all_names=all_names,
        id_set=set(all_ids),
        by_supplier=by_supplier,
        key_to_part=key_to_part,
    )


def _alias_lookup(db: Session, supplier_name: Optional[str], vendor_part_id: Optional[str]) -> Optional[str]:
    if not vendor_part_id:
        return None
    sname = _norm(supplier_name)
    row = (
        db.query(PartAlias)
        .filter(PartAlias.vendor_part_id == vendor_part_id)
        .filter(PartAlias.supplier_name == (supplier_name if supplier_name else None))
        .first()
    )
    if row:
        return row.canonical_part_id
    # Try normalized supplier name match if exact None didn't work
    if supplier_name:
        row2 = (
            db.query(PartAlias)
            .filter(PartAlias.vendor_part_id == vendor_part_id)
            .filter(PartAlias.supplier_name == supplier_name)
            .first()
        )
        if row2:
            return row2.canonical_part_id
    return None


def _fuzzy_best(text: str, candidates: List[str]) -> Tuple[Optional[str], int]:
    if not text or not candidates or not process or not fuzz:
        return None, 0
    best = process.extractOne(text, candidates, scorer=fuzz.token_set_ratio)
    if not best:
        return None, 0
    return best[0], int(best[1] or 0)


def map_order_to_part(
    db: Session,
    order: Order,
    inv_index: InventoryIndex,
    high_thresh: int = 90,
    low_thresh: int = 75,
) -> Tuple[Optional[str], int]:
    """Return (canonical_part_id, confidence) for an order.
    Strategy: alias → exact → supplier-fuzzy → global-fuzzy.
    """
    # 1) Alias
    alias = _alias_lookup(db, order.supplier_name, order.part_id)
    if alias:
        return alias, 100

    # 2) Exact match on ID
    if order.part_id and order.part_id in inv_index.id_set:
        return order.part_id, 100

    # Build search text from part_id, notes
    text = _norm(order.part_id or order.notes or "")

    # 3) Supplier-scoped fuzzy (ids+names)
    sname = _norm(order.supplier_name)
    scoped = inv_index.by_supplier.get(sname) or []
    cand, score = _fuzzy_best(text, scoped)
    if cand and score >= high_thresh:
        return inv_index.key_to_part.get(cand, cand), score

    # 4) Global fuzzy
    all_candidates = list(inv_index.key_to_part.keys())
    cand2, score2 = _fuzzy_best(text, all_candidates)
    if cand2 and score2 >= low_thresh:
        return inv_index.key_to_part.get(cand2, cand2), score2

    return None, 0


def upsert_alias(
    db: Session,
    supplier_name: Optional[str],
    vendor_part_id: str,
    canonical_part_id: str,
    confidence: int,
) -> None:
    row = (
        db.query(PartAlias)
        .filter(PartAlias.vendor_part_id == vendor_part_id)
        .filter(PartAlias.supplier_name == (supplier_name if supplier_name else None))
        .first()
    )
    if row:
        row.canonical_part_id = canonical_part_id
        row.confidence = max(int(row.confidence or 0), int(confidence or 0))
    else:
        db.add(
            PartAlias(
                supplier_name=supplier_name,
                vendor_part_id=vendor_part_id,
                canonical_part_id=canonical_part_id,
                confidence=confidence,
            )
        )
    db.commit()

