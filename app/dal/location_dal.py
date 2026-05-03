"""Location resolution DAL — admin-only (ward/district/city) fuzzy search.

P9 (2026-05-03): consolidate. Single entry `resolve_location_scoped` handles
4 paths (city/district/ward/scope=None). OSM + POI mapping đã xóa ở P8/P9.
"""

from typing import List, Dict, Any, Optional
from app.db.dal import query, query_one
from app.core.normalize import normalize_name


# City-level keyword detection (check trước mọi scope để tránh fuzzy district match).
CITY_KEYWORDS = ("ha noi", "hanoi", "thanh pho ha noi")


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


def _search_ward_only(norm: str) -> Dict[str, Any]:
    """Tìm CHỈ trong wards. Không tìm thấy → not_found.

    Hỗ trợ format "Ward, District" (ví dụ user gõ "phu dien, bac tu liem"):
    split theo dấu phẩy → tìm ward KHỚP district. Tránh case "multiple" khi
    chỉ có 1 phường đúng trong district cụ thể.
    """
    # 0. Format "ward_part, district_part" — split và query kèm district filter
    if "," in norm:
        ward_part = norm.split(",", 1)[0].strip()
        district_part = norm.split(",", 1)[1].strip()
        if ward_part and district_part:
            # Thử exact ward_name_norm + district_name_norm match
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
            # Fuzzy ward WITHIN the district (nếu district tồn tại)
            fuzzy_in_district = query("""
                SELECT ward_id, ward_name_vi, district_id, district_name_vi, lat, lon,
                       similarity(ward_name_norm, %s) as score
                FROM dim_ward
                WHERE district_name_norm IN (%s, %s, %s)
                  AND ward_name_norm %% %s
                ORDER BY score DESC LIMIT 3
            """, (ward_part, district_part,
                  f"quan {district_part}", f"huyen {district_part}", ward_part))
            if fuzzy_in_district:
                if len(fuzzy_in_district) == 1:
                    return {"status": "fuzzy", "level": "ward", "data": fuzzy_in_district[0]}
                return {
                    "status": "multiple", "level": "ward", "data": fuzzy_in_district,
                    "needs_clarification": True,
                    "message": f"Nhiều phường '{ward_part}' trong {district_part}",
                    "suggestion": "Vui lòng nói chính xác tên phường",
                }
            # District part không khớp — fall through to normal search với ward_part thôi
            norm = ward_part

    # 1. Exact match (norm có thể đã có prefix hoặc chưa)
    result = query_one("""
        SELECT ward_id, ward_name_vi, district_id, district_name_vi, lat, lon
        FROM dim_ward WHERE ward_name_norm = %s LIMIT 1
    """, (norm,))
    if result:
        return {"status": "exact", "level": "ward", "data": result}

    # 2. Thử thêm prefix "phuong"/"xa" (DB lưu ward_name_norm có prefix)
    ward_prefixes = ['phuong', 'xa']
    if not any(norm.startswith(p + ' ') for p in ward_prefixes):
        for prefix in ward_prefixes:
            result = query_one("""
                SELECT ward_id, ward_name_vi, district_id, district_name_vi, lat, lon
                FROM dim_ward WHERE ward_name_norm = %s LIMIT 1
            """, (f"{prefix} {norm}",))
            if result:
                return {"status": "exact", "level": "ward", "data": result}

    # 3. Fuzzy match ward only (thử cả norm gốc và có prefix)
    search_terms = [norm]
    if not any(norm.startswith(p + ' ') for p in ward_prefixes):
        search_terms.extend(f"{p} {norm}" for p in ward_prefixes)

    fuzzy = []
    for term in search_terms:
        results = query("""
            SELECT ward_id, ward_name_vi, district_id, district_name_vi, lat, lon,
                   similarity(ward_name_norm, %s) as score
            FROM dim_ward WHERE ward_name_norm %% %s
            ORDER BY score DESC LIMIT 5
        """, (term, term))
        fuzzy.extend(results)

    # Deduplicate by ward_id, keep highest score
    seen = {}
    for r in fuzzy:
        wid = r["ward_id"]
        if wid not in seen or r.get("score", 0) > seen[wid].get("score", 0):
            seen[wid] = r
    fuzzy = sorted(seen.values(), key=lambda x: x.get("score", 0), reverse=True)[:5]

    if len(fuzzy) == 1:
        return {"status": "fuzzy", "level": "ward", "data": fuzzy[0]}
    elif len(fuzzy) > 1:
        return {
            "status": "multiple", "level": "ward", "data": fuzzy,
            "needs_clarification": True,
            "message": f"Tìm thấy nhiều phường/xã khớp '{norm}'",
            "suggestion": "Vui lòng nói rõ phường/xã cụ thể (kèm quận/huyện)",
        }

    # 4. Không thấy → hỏi lại user
    return {
        "status": "not_found", "level": "not_found",
        "message": f"Không tìm thấy phường/xã: {norm}",
        "needs_clarification": True,
        "suggestion": "Vui lòng cho biết tên phường/xã cụ thể (ví dụ: 'phường Dịch Vọng')",
    }


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
