# Dataset v2 Schema — Hanoi Weather Chatbot Eval

> Mục tiêu: dataset 500 câu single-turn cho **Phase 2 ablation eval 6-config** thesis. Kế thừa 199 câu cũ (`hanoi_weather_chatbot_eval_questions.csv`) + bổ sung 301 câu mới.

## Phạm vi v2

- **500 câu single-turn** (multi-turn defer hoàn toàn cho cycle sau).
- 184 câu non-POI cũ vào 135-cell coverage matrix.
- 15 câu POI cũ → relabel `expected_clarification=True` (abstention test set).
- 301 câu mới fill 135-cell matrix (không sinh POI).
- **Location source canonical:** `data/processed/dim_ward.csv` (126 ward + 31 district, post-merger).

## Reference docs (BẮT BUỘC đọc trước khi sinh)

- `docs/Weather Intent Design.md` — 14 intent group lõi + slot/scope schema (tham chiếu).
- `docs/intent_disambiguation_rules.md` — rules phân biệt 6 confusion pair quan trọng.
- `experiments/evaluation/tool_accuracy.py` — `INTENT_TO_TOOLS` mapping 15 intent × 3 scope → tool list.

## 15 intent canonical (theo code `INTENT_TO_TOOLS`)

| # | intent | intent_vi | Mô tả ngắn |
|---|---|---|---|
| 1 | `current_weather` | Thời tiết hiện tại | Overview thời tiết bây giờ |
| 2 | `hourly_forecast` | Dự báo theo giờ | Dự báo trong 48h tới |
| 3 | `daily_forecast` | Dự báo theo ngày | Dự báo 1-8 ngày tới |
| 4 | `weather_overview` | Tóm tắt thời tiết | Bản tóm tắt/tổng quan |
| 5 | `rain_query` | Truy vấn mưa | Có/không mưa, khi nào, bao lâu |
| 6 | `temperature_query` | Truy vấn nhiệt độ | Con số nhiệt độ, nóng/lạnh |
| 7 | `wind_query` | Truy vấn gió | Tốc độ, hướng gió |
| 8 | `humidity_fog_query` | Độ ẩm/mây/sương mù | Độ ẩm, mây, tầm nhìn |
| 9 | `historical_weather` | Thời tiết quá khứ | Hôm qua, vài ngày trước |
| 10 | `location_comparison` | So sánh địa điểm | So 2-3 quận/phường |
| 11 | `activity_weather` | Thời tiết theo hoạt động | Chạy bộ, picnic, du lịch... |
| 12 | `expert_weather_param` | Tham số chuyên sâu | Áp suất, UV, dew point... |
| 13 | `weather_alert` | Cảnh báo thời tiết | Bão, lũ, rét đậm, nắng nóng gay gắt |
| 14 | `seasonal_context` | Bối cảnh mùa | Đặc trưng mùa, gió mùa... |
| 15 | `smalltalk_weather` | Smalltalk | Chào hỏi, than vãn, identity bot |

## Schema CSV (16 columns)

| Column | Type | Required | Mô tả + ví dụ |
|---|---|---|---|
| `id` | string | ✓ | Format `v2_NNNN`. Câu cũ giữ id số (1-199). Câu mới `v2_0200` trở lên. |
| `question` | string | ✓ | Câu hỏi tiếng Việt tự nhiên. VD: "Chiều nay ở Cầu Giấy có mưa không?" |
| `intent` | enum | ✓ | 1 trong 15 intent ở bảng trên. |
| `intent_vi` | string | ✓ | Label tiếng Việt (theo bảng). |
| `location_scope` | enum | ✓ | `city` \| `district` \| `ward`. (POI cũ giữ giá trị `poi` legacy.) |
| `location_name` | string | optional | `null` nếu city không nói rõ. District: "Quận Cầu Giấy" / "Cầu Giấy". Ward: "Phường Bạch Mai" hoặc full "Phường Bạch Mai (Hai Bà Trưng)". **PHẢI tồn tại trong `dim_ward.csv`** (kiểm tra qua `district_name_vi` hoặc `ward_name_vi`). |
| `time_expression` | string | optional | Ngôn ngữ tự nhiên: "hiện tại", "chiều nay", "tuần sau", "thứ bảy", "3 ngày tới"... |
| `weather_param` | string | optional | `general` \| `temperature` \| `rain` \| `wind` \| `humidity` \| `cloud` \| `uv` \| `pressure` \| `dew_point` \| `visibility` \| `comfort` \| ... |
| `difficulty` | enum | ✓ | `easy` \| `medium` \| `hard`. Tiêu chí: easy = single-slot trực tiếp; medium = multi-slot hoặc thời gian gián tiếp; hard = đa intent ngầm, anaphoric, edge case. |
| `expected_tools` | JSON list | ✓ (mới) | List tool names từ `INTENT_TO_TOOLS[intent][scope]`. VD: `["get_current_weather"]`. |
| `expected_abstain` | bool | ✓ (mới) | `True` khi câu hỏi out-of-scope/no-data → chatbot phải refuse hoặc nói "không đủ dữ liệu". |
| `expected_clarification` | bool | ✓ (mới) | `True` khi câu hỏi ambiguous location/intent → chatbot phải hỏi lại. **15 POI cũ = True.** |
| `expected_grounding_keys` | JSON list | optional | Field gold response phải reference. VD: `["temp", "feels_like"]` cho temperature_query. |
| `disambiguation_rule_ref` | string | optional | Reference rule trong `intent_disambiguation_rules.md`. VD: `"#1 current_weather vs temperature_query"` cho confusion pair. |
| `gold_response_constraint` | string | optional | Mô tả ngắn gold response phải thoả. VD: "Phải nêu cụ thể ngày tạnh mưa nếu có". |
| `source` | enum | ✓ (mới) | `v1_legacy` (199 cũ) \| `v2_new` (301 mới). |
| `notes` | string | optional | Ghi chú free text. |

## Multi-turn columns (defer)

Schema KHÔNG bao gồm `multi_turn_id` và `turn_idx` ở v2 vì multi-turn defer. Khi mở rộng cycle sau sẽ thêm.

## Coverage matrix

```
15 intent × 3 scope (city/district/ward) × 3 difficulty (easy/medium/hard) = 135 cells

Distribution mục tiêu (sau khi sinh 301 mới):
- city scope:     45 cells × ~3 câu  = ~135 câu
- district scope: 45 cells × ~4 câu  = ~180 câu
- ward scope:     45 cells × ~4 câu  = ~180 câu (rare scope, ưu tiên fill)
- Total in matrix: ~485 câu (184 cũ + ~301 mới)
- POI abstention:  15 câu (legacy, expected_clarification=True)
- Grand total:     500 câu
```

## Validation rules (test pin)

- `intent` ∈ 15 enum values.
- `location_scope` ∈ {`city`, `district`, `ward`, `poi`(legacy only)}.
- `location_name` (nếu non-null + scope ∈ {district, ward}) PHẢI normalize-match với `dim_ward.csv`:
  - `scope=district` → khớp `district_name_vi` hoặc `district_name_norm`.
  - `scope=ward` → khớp `ward_name_vi` hoặc `ward_name_norm` (có thể có suffix district trong ngoặc).
- `difficulty` ∈ {`easy`, `medium`, `hard`}.
- `expected_tools` non-empty (trừ smalltalk_weather có thể empty list).
- `expected_clarification=True` IFF `scope=poi` HOẶC user query ambiguous (manual flag).
- `source` ∈ {`v1_legacy`, `v2_new`}.
- Question text Levenshtein distance vs all rows < 0.85 (deduplication).

## Workflow Mode C (collab)

Per session sinh dataset:
1. Tôi đọc `Weather Intent Design.md` + `intent_disambiguation_rules.md`.
2. Tôi check `coverage_tracker.csv` → identify cell rare nhất chưa fill.
3. Tôi propose batch 20 câu cho 5-7 cell, ưu tiên ward + intent thiếu nhất.
4. Mỗi câu mới check Levenshtein < 0.85 với 199 cũ + batch trước.
5. User review trong session: accept/edit/reject.
6. User dictate 5-10 câu edge case (out-of-scope, ambiguous, multi-intent).
7. Tôi expand 10-20 câu paraphrase template.
8. Lưu batch vào `dataset_v2_batchNN.csv`.
9. Update `coverage_tracker.csv` + sanity test.

## Final merged file

Sau khi xong tất cả batches:
- `data/evaluation/v2/hanoi_weather_eval_v2_500.csv` (500 rows).
- `data/evaluation/v2/CHECKSUMS.md` — SHA256 hash cho reproducibility.
