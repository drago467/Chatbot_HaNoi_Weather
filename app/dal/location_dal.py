"""Location resolution DAL — admin-only (ward/district/city) fuzzy search.

P9 (2026-05-03): consolidate. Single entry `resolve_location_scoped` handles
4 paths (city/district/ward/scope=None). OSM + POI mapping đã xóa ở P8/P9.
"""

from typing import List, Dict, Any, Optional
from app.db.dal import query, query_one
from app.core.normalize import normalize_name


# City-level keyword detection (check trước mọi scope để tránh fuzzy district match).
CITY_KEYWORDS = ("ha noi", "hanoi", "thanh pho ha noi")

# P10 (audit C1 batch2 ID 110): pg_trgm `%` operator default threshold ~0.3 cho
# false positives như "my dinh" → "ba dinh" (share trigrams 'din', 'inh' đủ ngưỡng).
# Raise lên 0.5 ngắt được các pair share suffix nhưng vẫn cho phép typo 1-2 ký tự
# ("cau giay" → "Cầu Giấy" similarity ~0.7, "thac that" → "Thạch Thất" ~0.6).
# Áp cho cả district + ward để xử lý nhất quán.
FUZZY_SCORE_THRESHOLD = 0.5


def resolve_location_scoped(
    location_hint: str, target_scope: str | None = None
) -> Dict[str, Any]:
    """Resolve location admin-only theo scope từ router.

    - target_scope="city": trả city level (hint coi như noise nếu không phải keyword)
    - target_scope="district": chỉ tìm trong districts
    - target_scope="ward": chỉ tìm trong wards
    - target_scope=None: rare path (router offline / direct DAL call). Heuristic
      district-first cho bare name (vd "Cầu Giấy" → quận, không phải phường con
      cùng tên) để giữ behavior trước P9.
    - Không tìm thấy → trả not_found (hỏi lại user, KHÔNG silent fallback).
    """
    norm = normalize_name(location_hint)

    # City — check trước cho mọi scope
    if norm in CITY_KEYWORDS or target_scope == "city":
        return {"status": "exact", "level": "city", "data": {"city_name": "Hà Nội"}}

    if target_scope == "district":
        return _search_district_only(norm)

    if target_scope == "ward":
        return _search_ward_only(norm)

    # scope=None / unknown
    return _search_no_scope(norm)


def _search_no_scope(norm: str) -> Dict[str, Any]:
    """Fallback khi router không cung cấp scope.

    Heuristic district-first: bare names hay là quận trong tiếng Việt
    ("thời tiết Cầu Giấy" thường = quận, không phải phường con cùng tên).
    Prefix "phuong"/"xa" → ward; "quan"/"huyen" → district.
    """
    ward_prefixes = ("phuong", "xa")
    district_prefixes = ("quan", "huyen")

    # Explicit ward prefix
    if any(norm.startswith(p + " ") for p in ward_prefixes):
        r = _search_ward_only(norm)
        if r["status"] in ("exact", "fuzzy"):
            return r

    # Explicit district prefix
    if any(norm.startswith(p + " ") for p in district_prefixes):
        r = _search_district_only(norm)
        if r["status"] in ("exact", "fuzzy"):
            return r

    # Bare name: district FIRST (priority preserved từ pre-P9 _resolve_from_database)
    district = _search_district_only(norm)
    if district["status"] in ("exact", "fuzzy"):
        return district

    # Else ward (exact/fuzzy/multiple đều trả về để caller xử lý clarification)
    ward = _search_ward_only(norm)
    if ward["status"] in ("exact", "fuzzy", "multiple"):
        return ward

    # Cả 2 miss — trả ward not_found (suggestion ward-level chi tiết hơn).
    return ward


def _search_district_only(norm: str) -> Dict[str, Any]:
    """Tìm CHỈ trong districts. Không tìm thấy → not_found."""
    # 1. Exact match với prefix "quan"/"huyen"
    district_prefixes = ['quan', 'huyen']
    if any(norm.startswith(p + ' ') for p in district_prefixes):
        result = query_one("""
            SELECT district_id, district_name_vi, district_name_norm
            FROM dim_district WHERE district_name_norm = %s LIMIT 1
        """, (norm,))
        if result:
            return {"status": "exact", "level": "district", "data": result}

    # 2. Exact match không prefix
    result = query_one("""
        SELECT district_id, district_name_vi, district_name_norm
        FROM dim_district
        WHERE district_name_norm = %s OR district_name_norm LIKE CONCAT('%% ', %s)
        LIMIT 1
    """, (norm, norm))
    if result:
        return {"status": "exact", "level": "district", "data": result}

    # 3. Fuzzy match district only
    fuzzy = query("""
        SELECT district_id, district_name_vi, district_name_norm,
               similarity(district_name_norm, %s) as score
        FROM dim_district WHERE district_name_norm %% %s
        ORDER BY score DESC LIMIT 3
    """, (norm, norm))
    # P10: filter score floor để tránh false positive như "my dinh" → "ba dinh".
    fuzzy = [r for r in fuzzy if r.get("score", 0) >= FUZZY_SCORE_THRESHOLD]
    if fuzzy:
        if len(fuzzy) == 1:
            return {"status": "fuzzy", "level": "district", "data": fuzzy[0]}
        return {
            "status": "multiple", "level": "district", "data": fuzzy,
            "needs_clarification": True,
            "message": f"Tìm thấy nhiều quận/huyện: {', '.join(d['district_name_vi'] for d in fuzzy)}",
            "suggestion": "Vui lòng nói rõ quận/huyện cụ thể",
        }

    # 4. Không thấy → hỏi lại user
    return {
        "status": "not_found", "level": "not_found",
        "message": f"Không tìm thấy quận/huyện: {norm}",
        "needs_clarification": True,
        "suggestion": "Vui lòng cho biết tên quận/huyện cụ thể (ví dụ: 'quận Cầu Giấy')",
    }


# ── Ward search helpers (tách từ _search_ward_only) ───────────────────
# Mỗi helper trả Optional[dict]: dict = match → caller return luôn; None = thử
# phase tiếp. Pattern này dễ giải thích trong vấn đáp hơn 1 hàm 100 LOC.

_WARD_PREFIXES = ("phuong", "xa")
_DISTRICT_PREFIXES_FOR_WARD_LOOKUP = ("quan", "huyen")


def _try_exact_ward_in_district(ward_part: str, district_part: str) -> Optional[Dict[str, Any]]:
    """Phase 0a: format "ward, district" — exact match cả 2 phần."""
    for wp in (ward_part, f"phuong {ward_part}", f"xa {ward_part}"):
        for dp in (district_part, f"quan {district_part}", f"huyen {district_part}"):
            result = query_one("""
                SELECT ward_id, ward_name_vi, district_id, district_name_vi, lat, lon
                FROM dim_ward
                WHERE ward_name_norm = %s AND district_name_norm = %s
                LIMIT 1
            """, (wp, dp))
            if result:
                return {"status": "exact", "level": "ward", "data": result}
    return None


def _try_fuzzy_ward_in_district(ward_part: str, district_part: str) -> Optional[Dict[str, Any]]:
    """Phase 0b: fuzzy ward TRONG 1 district cụ thể (district không exact)."""
    fuzzy_in_district = query("""
        SELECT ward_id, ward_name_vi, district_id, district_name_vi, lat, lon,
               similarity(ward_name_norm, %s) as score
        FROM dim_ward
        WHERE district_name_norm IN (%s, %s, %s)
          AND ward_name_norm %% %s
        ORDER BY score DESC LIMIT 3
    """, (ward_part, district_part,
          f"quan {district_part}", f"huyen {district_part}", ward_part))
    if not fuzzy_in_district:
        return None
    if len(fuzzy_in_district) == 1:
        return {"status": "fuzzy", "level": "ward", "data": fuzzy_in_district[0]}
    return {
        "status": "multiple", "level": "ward", "data": fuzzy_in_district,
        "needs_clarification": True,
        "message": f"Nhiều phường '{ward_part}' trong {district_part}",
        "suggestion": "Vui lòng nói chính xác tên phường",
    }


def _try_exact_ward(norm: str) -> Optional[Dict[str, Any]]:
    """Phase 1+2: exact ward_name_norm match (thử cả prefix "phuong"/"xa")."""
    # Phase 1: norm như user gõ
    result = query_one("""
        SELECT ward_id, ward_name_vi, district_id, district_name_vi, lat, lon
        FROM dim_ward WHERE ward_name_norm = %s LIMIT 1
    """, (norm,))
    if result:
        return {"status": "exact", "level": "ward", "data": result}

    # Phase 2: thêm prefix "phuong"/"xa" (DB lưu ward_name_norm có prefix sẵn)
    if not any(norm.startswith(p + " ") for p in _WARD_PREFIXES):
        for prefix in _WARD_PREFIXES:
            result = query_one("""
                SELECT ward_id, ward_name_vi, district_id, district_name_vi, lat, lon
                FROM dim_ward WHERE ward_name_norm = %s LIMIT 1
            """, (f"{prefix} {norm}",))
            if result:
                return {"status": "exact", "level": "ward", "data": result}
    return None


def _try_fuzzy_ward(norm: str) -> Optional[Dict[str, Any]]:
    """Phase 3: fuzzy ward chỉ ward (thử cả norm gốc và norm + prefix)."""
    search_terms = [norm]
    if not any(norm.startswith(p + " ") for p in _WARD_PREFIXES):
        search_terms.extend(f"{p} {norm}" for p in _WARD_PREFIXES)

    candidates: List[Dict[str, Any]] = []
    for term in search_terms:
        candidates.extend(query("""
            SELECT ward_id, ward_name_vi, district_id, district_name_vi, lat, lon,
                   similarity(ward_name_norm, %s) as score
            FROM dim_ward WHERE ward_name_norm %% %s
            ORDER BY score DESC LIMIT 5
        """, (term, term)))

    # Dedupe theo ward_id, giữ score cao nhất
    best_by_id: Dict[str, Dict[str, Any]] = {}
    for r in candidates:
        wid = r["ward_id"]
        if wid not in best_by_id or r.get("score", 0) > best_by_id[wid].get("score", 0):
            best_by_id[wid] = r
    fuzzy = sorted(best_by_id.values(), key=lambda x: x.get("score", 0), reverse=True)[:5]
    fuzzy = [r for r in fuzzy if r.get("score", 0) >= FUZZY_SCORE_THRESHOLD]

    if not fuzzy:
        return None
    if len(fuzzy) == 1:
        return {"status": "fuzzy", "level": "ward", "data": fuzzy[0]}
    return {
        "status": "multiple", "level": "ward", "data": fuzzy,
        "needs_clarification": True,
        "message": f"Tìm thấy nhiều phường/xã khớp '{norm}'",
        "suggestion": "Vui lòng nói rõ phường/xã cụ thể (kèm quận/huyện)",
    }


def _ward_not_found(norm: str) -> Dict[str, Any]:
    """Phase 4: không match → trả not_found với suggestion clarification."""
    return {
        "status": "not_found", "level": "not_found",
        "message": f"Không tìm thấy phường/xã: {norm}",
        "needs_clarification": True,
        "suggestion": "Vui lòng cho biết tên phường/xã cụ thể (ví dụ: 'phường Dịch Vọng')",
    }


def _search_ward_only(norm: str) -> Dict[str, Any]:
    """Tìm CHỈ trong wards. Không tìm thấy → not_found.

    Pipeline 4 phase, mỗi phase 1 helper:
      0. Format "ward, district" (split dấu phẩy) — exact + fuzzy in-district.
      1+2. Exact ward_name_norm (thử cả prefix "phuong"/"xa").
      3. Fuzzy ward toàn thành phố.
      4. not_found + clarification.

    Format "ward, district" nếu phần district không khớp → fall-through xuống
    phase 1+ với chỉ ward_part (giữ behavior cũ trước refactor).
    """
    # Phase 0: format "ward, district"
    if "," in norm:
        ward_part = norm.split(",", 1)[0].strip()
        district_part = norm.split(",", 1)[1].strip()
        if ward_part and district_part:
            hit = _try_exact_ward_in_district(ward_part, district_part)
            if hit:
                return hit
            hit = _try_fuzzy_ward_in_district(ward_part, district_part)
            if hit:
                return hit
            # District không khớp: fall-through phase 1+ chỉ với ward_part.
            norm = ward_part

    # Phase 1+2
    hit = _try_exact_ward(norm)
    if hit:
        return hit

    # Phase 3
    hit = _try_fuzzy_ward(norm)
    if hit:
        return hit

    # Phase 4
    return _ward_not_found(norm)


def get_ward_by_id(ward_id: str) -> Optional[Dict[str, Any]]:
    return query_one("""
        SELECT ward_id, ward_name_vi, district_id, district_name_vi, lat, lon
        FROM dim_ward WHERE ward_id = %s
    """, (ward_id,))


def get_all_wards() -> List[Dict[str, Any]]:
    return query("""
        SELECT ward_id, ward_name_vi, district_id, district_name_vi, lat, lon
        FROM dim_ward ORDER BY district_name_vi, ward_name_vi
    """)


def get_districts() -> List[Dict[str, Any]]:
    return query("""
        SELECT district_id, district_name_vi, district_name_norm
        FROM dim_district ORDER BY district_name_vi
    """)


def get_wards_in_district(district_name: str) -> List[Dict[str, Any]]:
    """Get all wards in a district."""
    return query("""
        SELECT ward_id, ward_name_vi, district_id, district_name_vi, lat, lon
        FROM dim_ward
        WHERE district_name_vi = %s
        ORDER BY ward_name_vi
    """, (district_name,))


def search_wards(keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
    norm = normalize_name(keyword)
    return query("""
        SELECT ward_id, ward_name_vi, district_id, district_name_vi, lat, lon,
               similarity(ward_name_norm, %s) as score
        FROM dim_ward
        WHERE ward_name_norm %% %s OR district_name_norm %% %s
        ORDER BY score DESC LIMIT %s
    """, (norm, norm, norm, limit))
