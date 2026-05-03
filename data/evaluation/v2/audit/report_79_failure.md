# Báo cáo Audit Rerun — `c1_20260502_213048.jsonl`

**Anchor ngày:** Thứ Bảy 02/05/2026, 22:00 (đêm). HÔM NAY=T7 02/05, NGÀY MAI=CN 03/05, HÔM QUA=T6 01/05. **Cuối tuần đang diễn ra** (T7+CN). "Tuần này" = T2 27/04 → CN 03/05. "Tuần qua" rolling = 26/04→02/05.

**File:** 79 entries — bao gồm 23 IDs từ Phase I (1-200) và 56 IDs `v2_xxxx` từ Phase II/III (201-500), tất cả đều là các câu đã từng fail/borderline trong các audit trước.

**Spec:** Tier 1 (grounding + no hallucination) = hard gate. Tolerance ±2°C; mislabel khung trong ngày = sai; "today" data dán "tomorrow" = nghiêm trọng.

---

## PHẦN 1 — PHASE I IDs (23 entries từ 1-200)

### ID 12 — **Bucket: B**
- **Q:** Tầm nhìn sân bay Nội Bài.
- **Tool:** `current_weather` → trả "Hà Nội (toàn TP)", KHÔNG phải Nội Bài cụ thể.
- **Lỗi:** Bot dán "tầm nhìn sân bay Nội Bài 10 km" cho data toàn HN. POI mismatch không thừa nhận.
- **Status:** Không fix.

### ID 23 — **Bucket: C**
- **Q:** **Trưa nay** Đông Anh nắng?
- **Tool:** hourly 12h cover **22:00 T7 → 09:00 CN** (KHÔNG có 12-18h T7 đã qua).
- **Lỗi:** Bot trả "Trưa nay (12-18h)... có mưa nhẹ với xác suất cao 100%" — số 100% là cho 06-09h CN sáng mai. **Mislabel "trưa nay" cho data đêm/sáng mai.**
- **Status:** Không fix — pattern cũ (snapshot/forward dán nhãn quá khứ).

### ID 33 — **Bucket: B**
- **Q:** **Tuần này** HN ngày đẹp nhất.
- **Tool:** `weather_period` 02-03/05 (chỉ T7+CN forward, T2-T6 đã qua).
- **Lỗi:** Bot kết "T7 02/05 tốt hơn" mà không nhắc thiếu data T2-T6 27/04-01/05.
- **Status:** Không fix — incomplete coverage cho "tuần này".

### ID 35 — **Bucket: B**
- **Q:** **Sáng** Thứ Sáu tuần này Ba Đình.
- **Tool:** `daily_forecast` trả 01/05 (T6 vừa rồi). Daily không có breakdown sáng.
- **Lỗi:** Bot dán "Sáng Thứ Sáu" cho daily summary cả ngày (24.6-27.0°C). Không tách sáng.
- **Status:** Một phần — đúng ngày, sai khung sáng.

### ID 36 — **Bucket: A**
- 5 ngày Sóc Sơn 02-06/05, daily forecast OK.

### ID 58 — **Bucket: B**
- **Q:** Mùa này HN có **mưa phùn**.
- **Tool:** `detect_phenomena` ERROR + daily 3 ngày.
- **Lỗi:** Output có "Mưa nhẹ 3.1mm / Mưa to 17.7mm" — không có "mưa phùn" (drizzle). Bot dán "có mưa phùn" — confound mưa nhẹ với mưa phùn.
- **Status:** Không fix — bịa nhãn hiện tượng.

### ID 60 — **Bucket: B**
- **Q:** Cầu Giấy ngoài trời rét lắm không.
- **Tool:** snapshot 22:00, 26.3°C "Ấm dễ chịu" + cảm giác 26.3°C.
- **Lỗi:** Bot trả "khá khó chịu, **hơi lạnh**" — sai cảm giác cho 26°C. Snapshot rõ ràng không có "lạnh".
- **Status:** Không fix — phóng đại trái dữ liệu.

### ID 86 — **Bucket: B**
- **Q:** **Tối nay** Thanh Xuân độ ẩm.
- **Tool:** hourly 24h cover 22:00 T7 → 21:00 CN.
- **Lỗi:** Bot list **toàn bộ 24 giờ** (gồm sáng-trưa-chiều-tối CN) dán nhãn "tối nay". "Tối nay" should be ≈ 22-24h T7 + chuyển khung sang đêm.
- **Status:** Không fix — phạm vi "tối nay" quá rộng.

### ID 108 — **Bucket: C**
- **Q:** **Cuối tuần** nội/ngoại thành.
- **Tool:** `district_multi_compare` snapshot **21:35 T7** (NOW).
- **Lỗi:** Bot dán snapshot làm "cuối tuần" (T7+CN). Cuối tuần là 2 ngày, không phải 1 phút.
- **Status:** Không fix — snapshot cho cuối tuần.

### ID 119 — **Bucket: A**
- Sáng CN Hồ Gươm. hourly 12h cover 06-09h CN. Bot adapt OK.

### ID 129 — **Bucket: A**
- Điểm sương sáng mai. `humidity_timeline` có data sáng mai. Bot xác định 23.6-24.2°C, nhận định nồm ẩm.

### ID 133 — **Bucket: A**
- "Tuần này HN nắng nóng gay gắt". `temperature_trend` max 33.79°C T6. Bot kết "không vượt 36°C, không gay gắt". OK.

### ID 138 — **Bucket: A**
- Đợt lạnh thấp nhất. `temp_trend` min 18.64°C T2 04/05. OK.

### ID 144 — **Bucket: A**
- Hôm nay mặc gì. `clothing_advice` ERROR + current. Adapt OK.

### ID 150 — **Bucket: A**
- Tối nay ngắm sao. Snapshot 22:00 = đang là tối, đang mưa nhẹ + mây 91% → "không đẹp ngắm sao" đúng.

### ID 167 — **Bucket: C**
- **Q:** **Tuần này vs tuần trước** HN.
- **Tool:** `weather_period` ERROR + history 27/04 (1 ngày) + daily 27/04-03/05 (forecast). KHÔNG có data 20-26/04.
- **Lỗi:** Bot **bịa data tuần trước**: "18-26°C, 1 ngày mưa T6 24/04, gió cấp 2-3, UV thấp, độ ẩm <70%" — output không có 20-26/04!
- **Status:** Không fix — bịa nội dung.

### ID 168 — **Bucket: A**
- "Mùa này HN giông chiều". `seasonal_comparison` (TB 18 ngày mưa/tháng 5). Adapt OK.

### ID 169 — **Bucket: A**
- Hôm qua mưa hôm nay. `compare_with_yesterday` tool mới. Adapt OK.

### ID 175 — **Bucket: A**
- 8h tối nay Nghĩa Đô. 22:00 ≈ "8h tối", 26.3°C đúng.

### ID 177 — **Bucket: C**
- **Q:** Giảng Võ Ba Đình **sáng nay** độ ẩm.
- **Tool:** `humidity_timeline` forward 24h từ 21:39 T7 (KHÔNG có sáng nay đã qua).
- **Lỗi:** Bot dán "sáng nay (02:00-06:00 CN 03/05)" — đó là **rạng sáng MAI**, không phải sáng nay! Mislabel ngày.
- **Status:** Không fix — dán "sáng nay" cho rạng sáng mai.

### ID 196 — **Bucket: C**
- **Q:** **Chiều nay** mưa.
- **Tool:** hourly 12h từ 22:00 T7 (chiều nay 13-18h T7 đã qua).
- **Lỗi:** Bot dán "Chiều nay (13-18h)" cho data 22:00-09:00 CN — toàn data đêm/sáng mai.
- **Status:** Không fix — pattern cũ chiều nay/data đêm.

### ID 197 — **Bucket: C**
- **Q:** Từ **6h sáng đến 9h tối nay** Ba Đình.
- **Tool:** hourly 15h từ 22:00 T7 → 12:00 CN (KHÔNG có 6-21h T7).
- **Lỗi:** Bot trả "6:00-12:00 **Chủ Nhật 03/05**" — tự đổi user query "tối **nay**" thành "trưa **mai**". Mislabel ngày.
- **Status:** Không fix — sai ngày.

### ID 198 — **Bucket: B**
- "Tuần này HN sự kiện ngoài trời". `weather_period` chỉ T7+CN. Bot kết "không có ngày đẹp" chỉ từ 2 ngày, không nhắc T2-T6 đã qua.
- **Status:** Không fix — incomplete tuần này.

---

## PHẦN 2 — Phase II/III IDs (`v2_xxxx`, 56 entries)

### v2_0202 — **A**
"Lúc này vs sáng nay" Khương Đình. current ERROR + 2x hourly forward. Bot **transparent** "thiếu data sáng nay". → **Đã fix** từ D phase trước thành A. ✓

### v2_0206 — **A**
3 ngày Đông Ngạc, daily forecast 02-04/05 OK.

### v2_0211 — **B**
"Tổng kết phường Phúc Lợi từ sáng tới giờ". `daily_rhythm` chỉ trả "khung mát/nóng" + hourly forward 12h từ 22h. Bot dán "Từ sáng đến giờ... 25-26.2°C" — số này là từ **forward data**, không phải sáng nay đã qua. Mislabel quá khứ. → **Không fix** từ D.

### v2_0212 — **D**
"Rạng sáng mai vs rạng sáng hôm nay" Bạch Mai. **Recursion limit error**, empty answer.
→ **Vẫn D**, không fix.

### v2_0214 — **B**
"Văn Miếu hiện tại + chênh **TB tuần qua**". current 21:21 + `temperature_trend` (forward 7 ngày, KHÔNG phải tuần qua!). Bot trả **"TB tuần qua 30.26°C"** — đó là TB T7 02/05 từ forecast, không phải tuần qua. Mislabel forward thành past. → **Không fix** từ D.

### v2_0223 — **A**
Long Biên điểm sương vs độ ẩm chênh, snapshot OK + cảm giác bí từ data thực.

### v2_0224 — **A**
3 ngày Sơn Tây giông lốc. alerts 0 + change_alert (mưa 22h) + hourly 47h. Bot kết khung 13-16h CN nguy hiểm (mưa 5.59mm/h, gió 8.2m/s) — có cơ sở từ data forecast. Transparent.

### v2_0227 — **A**
"Đợt rét vs cùng kỳ năm ngoái" Văn Miếu. seasonal + history 2025-05-02 ERROR + daily 02/05. Bot transparent về thiếu data lịch sử. → **Đã fix** từ D thành A ✓.

### v2_0229 — **A**
Gió mùa Đông Bắc Đông Anh. `temp_trend` forward, transparent "thiếu data lịch sử gió mùa".

### v2_0231 — **B**
"Mưa ngoại thành phía Bắc HN". `rain_timeline` cover toàn HN (không phân biệt vùng). Bot dán nhãn "ngoại thành phía Bắc" cho data toàn HN. Tool fail location resolution, bot không nhận ra.

### v2_0232 — **A**
Sáng mai Thanh Liệt nhiều mặt. daily 03/05 với "Sáng 25.4°C". Bot trả từ data đúng.

### v2_0240 — **B**
"**Rạng sáng hôm sau** Kim Liên min nhiệt vs hôm nay". current 21:21 + hourly 24h. Bot kết "min 20.7°C lúc **21:00 CN**" — 21:00 CN là **TỐI Chủ Nhật**, KHÔNG phải rạng sáng hôm sau. Hơn nữa "so với 26.3°C lúc 21:00 hôm nay" — so giữa tối T7 vs tối CN, không phải rạng sáng vs rạng sáng. **Mislabel khung kép.**

### v2_0246 — **A**
3 ngày Trung Giã giông. alerts 0. Bot transparent + đề nghị forecast.

### v2_0248 — **B**
"Trời lúc này so với sáng nay" HN, 5 tools. Bot bịa "**sáng nay (6-11h) UV trung bình đến cao 9.5**" — UV 9.5 là daily summary cả ngày, không phải sáng nay. Hourly forward không có sáng nay đã qua. → **Không fix** từ D, vẫn bịa.

### v2_0256 — **C**
"**Đêm nay** HN min nhiệt". hourly 24h. Bot kết "đêm nay (22h T7-06h CN) min **21.0°C lúc 21:00 CN**" — 21:00 CN nằm **NGOÀI** khung "đêm nay" mà bot tự định nghĩa. Min thực trong khung đêm nay (22h-06h) là 24.9°C. Bot tự mâu thuẫn + lấy số ngoài khung.

### v2_0266 — **C**
"**Chiều nay** Hà Đông max nhiệt". hourly 12h từ 22:00 T7 (chiều nay 13-18h T7 đã qua). Bot dán "Chiều nay max **26.4°C lúc 22:00**" — 22:00 không phải chiều, là tối. Mislabel chiều thành tối + không có data chiều thật.

### v2_0269 — **B**
"**Tuần qua** Sóc Sơn mưa >50mm". `weather_period` 18-24/04 — sai mapping! Tuần qua từ T7 02/05 nên là 26/04-02/05 hoặc 25/04-01/05. Bot adapt với data sai khung. → Mapping ngày sai.

### v2_0270 — **A**
"7 ngày qua Đông Anh trời quang". history 26/04-02/05 ✓ đúng mapping. Bot kết "T5 30/04 trời quang" đúng.

### v2_0271 — **B**
"5 ngày qua Hà Đông đợt rét". history 28/04-02/05 ✓ đúng mapping. Min = 23.1°C T7 02/05. Nhưng 23.1°C không phải "đợt rét" — bot vẫn gọi "đợt rét gây ấn tượng". Phóng đại.

### v2_0273 — **A**
Cầu Giấy → Sơn Tây compare snapshot. OK.

### v2_0274 — **A**
Bắc Từ Liêm vs Nam Từ Liêm tối nay. compare snapshot 21:48 ≈ "tối nay" early evening, adapt OK.

### v2_0281 — **B**
"Trưa mai Tùng Thiện". daily CN có "Sáng 24.7 / Chiều 22.8 / Tối 20.9" (KHÔNG có "trưa"). Bot dán "trưa = chiều 22.8°C" — sai khung trưa (trưa thường = 11-13h, gần đỉnh nóng). 22.8°C là chiều = 14-17h.

### v2_0282 — **B**
"**Chiều tối nay** Hồng Hà nhiệt giảm". hourly 6h từ 22:00 T7 → 03:00 CN. "Chiều tối" thường = 17-22h. Bot dán "chiều tối nay 22h-03h" — đó là **đêm + rạng sáng**, không phải chiều tối. Mislabel.

### v2_0288 — **A**
Tối nay Chương Mỹ chạy bộ. current + hourly 6h + activity_advice. Tổng hợp đầy đủ, kết "có thể với mang ô".

### v2_0300 — **C**
"**5h chiều - 7h tối nay** HN mưa" = 17-19h T7 đã qua. hourly 2h cover 22-23h T7. Bot dán "**5h chiều - 7h tối**" cho data 22-23h. Mislabel khung.

### v2_0303 — **C**
"**Mai từ trưa đến chiều** HN". hourly 12h từ 22h T7 → 09h CN (KHÔNG có 11-17h CN). Bot kết "lượng mưa cao điểm **06-09h**" (sáng CN, không phải trưa-chiều CN). Trả khung sai.

### v2_0304 — **A**
5 ngày HN nắng đẹp. daily forecast 03-07/05, không có nắng đẹp — đúng từ data.

### v2_0311 — **A**
"Đêm nay đến rạng sáng mai" Hồng Hà. hourly 10h cover 22h T7 → 07h CN ✓. Gió max 3.4 m/s lúc 23h. Bot adapt + transparent về gió mùa.

### v2_0316 — **B**
"**Tuần qua** HN max/min". `weather_period` 18-24/04 — **sai mapping**, tuần qua thực = 26/04-02/05 hoặc 25/04-01/05. Bot adapt với data sai khung tuần. → Recursion error đã fix nhưng mapping ngày sai.

### v2_0320 — **B**
"**Tối nay** so sánh nội/ngoại thành". `district_multi_compare` snapshot. Bot phân tách OK với data thực, nhưng dùng snapshot 21:21 cho "tối nay" — chỉ 1 thời điểm, không phải "tối" như khung.

### v2_0323 — **A**
"Chiều nay Cửa Nam vs Hồng Hà". compare snapshot 21:51 — đã quá chiều, nhưng bot dùng từ "Hiện tại" thay "chiều nay", transparent.

### v2_0324 — **B**
"**Sáng mai** 3 phường thấp nhất". daily ERROR + 3x current 21:21 T7. Bot dán snapshot làm "thấp nhất sáng mai". Cuối có disclaimer "không phản ánh sáng mai" — bù đắp một phần. Vẫn B vì body trả số snapshot làm "min sáng mai".

### v2_0325 — **B**
"Vài giờ tới đi từ Đại Mỗ → Tây Mỗ → Yên Nghĩa mưa nơi nào". hourly ERROR + 3x current 21:21. Bot dán snapshot 26.4°C cho cả 3 + transparent ở cuối "khả năng mưa có thể xảy ra". Snapshot cho future query.

### v2_0329 — **A**
"UV vs độ ẩm Hà Đông chênh nhau". `compare_weather` Hà Đông vs Hà Đông (degenerate). Bot **nhận ra** "đây là cùng địa điểm" và xử lý hợp lý. → Phát hiện degenerate compare ✓.

### v2_0332 — **A**
"UV trưa nay Phú Lương". current 21:21 UV=0 (đêm) + uv_safe_windows ERROR. Bot kết "không có UV trưa nay trong data" + cảnh báo phòng hờ. Adapt OK.

### v2_0345 — **A**
"UV từng giờ ngày mai" Phù Đổng. hourly 24h KHÔNG có UV theo giờ. Bot **transparent** "không có data UV theo giờ" + suy luận chung từ mưa nhiều → UV thấp. → **Đã fix** từ D ✓.

### v2_0348 — **A**
7 ngày Bạch Mai mưa lớn nhất. weather_period 02-08/05. CN max 15.8mm. Bot transparent "khung giờ cụ thể không có" → **Đã fix** từ C trước ✓.

### v2_0349 — **A**
Cuối tuần Hoài Đức xe đạp leo dốc. 5 tools tổng hợp tốt + đề nghị sáng sớm Thứ Hai khi best_time điểm 100/100.

### v2_0353 — **A**
Đêm nay 22-23h HN. hourly 2h ✓ exact match, OK.

### v2_0362 — **C**
"**Trưa nay** HN mưa rào". hourly 24h từ 22h T7 (trưa nay 12-14h T7 đã qua). Bot kết "**Trưa nay (12:00 Chủ Nhật)** mưa rào 1.15 mm/h" — 12:00 CN là **trưa MAI**, không phải trưa nay. Mislabel ngày.

### v2_0368 — **B**
"Trưa mai Văn Miếu nhiệt cảm giác oi". daily CN có "Sáng 25.3 / Chiều 22.6 / Tối 20.6". Bot dán "trưa = chiều 22.6°C" — sai khung trưa (trưa ≈ 11-13h thường nóng nhất, daily không có trưa nhưng max cả ngày 28.6°C). 22.6°C là chiều CN.

### v2_0372 — **B**
"Đêm nay HN gió giật mạnh nhất, **km/h**". hourly 24h. Bot kết "**14.3 km/h**" — output rõ ràng "giật **14.3 m/s**" (= ~51 km/h). Bot **giữ nguyên số nhưng đổi đơn vị m/s → km/h** sai. Hơn nữa 14:00 CN không phải "đêm nay". → **Không fix** từ D, vẫn sai đơn vị.

### v2_0379 — **A**
"7 ngày qua chênh nhiệt ngày-đêm lớn nhất" HN. weather_period 26/04-02/05 ✓ đúng mapping. T7 02/05 chênh 11.8°C — đúng. → **Đã fix** từ D (recursion) thành A ✓.

### v2_0380 — **C**
"Tối nay nội thành vs Đông Anh lạnh hơn". 2x current_weather, **cả 2 lần trả "Hà Nội (toàn TP)"** — tool không phân biệt được nội thành vs Đông Anh. Bot kết "tương đương" mà KHÔNG nhận ra tool fail location resolution. Cùng số liệu y hệt = red flag.

### v2_0382 — **A**
Tối nay Hoàng Liệt vs Hoàng Mai. compare snapshot ≈ tối, OK.

### v2_0383 — **B**
"**Sáng mai** Đông Ngạc vs Tây Tựu sương". `compare_weather` snapshot 21:55 T7. Body bot ghi "Hiện tại 21:55 T7" + "cả 2 phường có mưa" — adapt OK ở phần liệt kê dữ liệu, nhưng dán "Sáng mai" lên đầu. Cuối transparent "không xác định được sương sáng mai". Mixed.

### v2_0389 — **B**
"UV **trưa nay** Cầu Giấy". current 22:00 T7 UV=0 (đêm). Bot trả "UV thấp 0, không cần áo chống nắng" cho query "trưa nay" — adapt từ current không phù hợp với trưa. Cuối nhắc "kiểm tra UV cụ thể cho khung giờ" — partial transparent.

### v2_0433 — **C**
"**Sáng mai** 3 phường thấp nhất". daily ERROR + 3x current 21:21 T7. Bot dán snapshot 26.4-26.5°C làm "thấp nhất sáng mai". Cuối có disclaimer ngắn "Nếu cần sáng mai mình tra giúp" — không bù được mislabel. → **Không fix** snapshot misuse cho future.

### v2_0435 — **A**
Sáng mai HN chạy bộ. hourly 24h cover sáng CN 06-10h ✓. Bot adapt OK. → **Đã fix** từ C ✓.

### v2_0436 — **A**
Cuối tuần Sóc Sơn leo núi + sương mù sáng. weather_period 02-03/05. Bot transparent "không ghi nhận sương mù" + đề xuất hoãn. → **Đã fix** từ C (trước bịa sương từ độ ẩm) ✓.

### v2_0451 — **B**
"Tuần tới Mỹ Đức mưa to + gió mạnh + **khoảng giờ**". weather_period ERROR + daily 6 ngày. T7 09/05 mưa 44.5mm + giật 7.5 m/s. "Khoảng giờ" daily không có. Bot kết "mưa từ sáng đến tối" — bịa khung giờ. → **Không fix** từ C.

### v2_0455 — **A**
"Mai dã ngoại Tây Hồ". `get_best_time` activity=du_lich, output rõ "02-04h sáng CN" tốt nhất. Bot trả từ data — kỳ quặc về thực tế (gia đình dã ngoại 2-4h sáng?) nhưng đúng từ tool output. → **Đã fix** vấn đề ngày T7/CN từ phase trước ✓.

### v2_0464 — **C**
"**Chiều nay 4-6h** Định Công" = 16-18h T7 đã qua. hourly 10h cover 22h T7 → 07h CN. Bot trả "**Chiều nay** từ 22:00 đến 07:00" — đó là tối/đêm/rạng sáng, không phải chiều 4-6h. Mislabel khung.

### v2_0481 — **A**
Sáng mai Nghĩa Đô sương mù. hourly 24h cover sáng CN. Bot transparent "không có data sương mù" + adapt từ độ ẩm/mây cẩn thận. → **Đã fix** từ C (trước suy diễn sương từ mây) ✓.

### v2_0484 — **B**
"**Tuần vừa qua** Đông Ngạc tụt nhiệt". weather_period 18-24/04 — **sai mapping**! Tuần vừa qua từ T7 02/05 nên là 26/04-02/05 hoặc 25/04-01/05. → **Recursion error đã fix** thành non-error, nhưng mapping ngày sai. Đỡ tệ hơn D nhưng vẫn sai khung.

### v2_0500 — **B**
"**12h tới** Cầu Giấy/Yên Hòa/Nghĩa Đô gió mạnh nhất". hourly ERROR + 3x current 21:21 T7. Bot dán snapshot làm "12h tới" + cuối transparent "muốn xem 12h tới gọi hourly_forecast". Snapshot misuse cho future với caveat. → **Không fix** từ C.

---

## PHẦN A — Tổng hợp số lượng (79 entries)

| Bucket | Phase I (23) | v2_xxxx (56) | **TỔNG (79)** | Tỷ lệ |
|--------|--------------|--------------|---------------|-------|
| **A** | 10 (43.5%) | 27 (48.2%) | **37** | 46.8% |
| **B** | 7 (30.4%) | 20 (35.7%) | **27** | 34.2% |
| **C** | 6 (26.1%) | 8 (14.3%) | **14** | 17.7% |
| **D** | 0 (0%) | 1 (1.8%) | **1** | 1.3% |
| **Tier 1 pass (A+B)** | 17 | 47 | **64** | **81.0%** |

---

## PHẦN B — Lỗi nặng còn lại (Bucket C/D — 15 entries)

### Bucket D (1):
- **v2_0212** — Recursion limit error, empty answer. Pattern cũ chưa fix với query "rạng sáng mai chênh rạng sáng hôm nay".

### Bucket C (14):
- **23, 196, v2_0266, v2_0300, v2_0464** — "Trưa/chiều nay" cho data đêm/sáng mai (5 entries, pattern phổ biến nhất).
- **108** — Snapshot cho "cuối tuần".
- **167** — Bịa data tuần trước không có trong tool output.
- **177, v2_0362** — "Sáng nay/trưa nay" dán cho "sáng/trưa MAI" (mislabel ngày).
- **197** — "Tối nay" tự đổi thành "trưa mai".
- **v2_0256** — "Đêm nay min" lấy số ngoài khung tự định nghĩa.
- **v2_0303** — "Mai trưa-chiều" trả khung "sáng" CN.
- **v2_0380** — Compare nội thành vs Đông Anh nhưng tool trả cùng "HN toàn TP" 2 lần, bot không phát hiện.
- **v2_0433** — Sáng mai 3 phường thấp nhất → snapshot 21:21 T7.

---

## PHẦN C — Đối chiếu fix vs lỗi mới phát sinh

### ✅ Đã fix (~12 entries):

| ID | Fix mode |
|----|----------|
| v2_0202 | Transparent về thiếu data sáng nay (D → A) |
| v2_0227 | Transparent về thiếu history cùng kỳ (D → A) |
| v2_0270 | Mapping ngày tuần qua đúng 26/04-02/05 (D → A) |
| v2_0345 | Transparent UV theo giờ không có data (D → A) |
| v2_0379 | Recursion error đã fix, mapping tuần qua 26/04-02/05 đúng (D → A) |
| v2_0316 | Recursion error đã fix (D → B, mapping tuần qua vẫn sai) |
| v2_0484 | Recursion error đã fix (D → B, mapping tuần qua vẫn sai) |
| v2_0348 | Đã transparent về khung giờ daily không có (C → A) |
| v2_0435 | Sáng mai → hourly forward đủ cover (C → A) |
| v2_0436 | Không suy diễn sương từ độ ẩm/mây (C → A) |
| v2_0481 | Không suy diễn sương từ mây (C → A) |
| v2_0455 | Best_time đã đúng ngày (C → A) |
| v2_0329 | Đã phát hiện degenerate compare (cùng địa điểm 2 lần) (C → A) |

**Tỷ lệ fix:** ~12/79 entries lỗi cũ đã được fix triệt để hoặc bù đắp bằng transparency.

### ❌ KHÔNG fix — recurring pattern:

#### 1. **Snapshot/forward dán cho khung quá khứ** (lỗi phổ biến nhất, 7+ entries):
   - **Phase I:** 23 (trưa nay), 86 (tối nay rộng), 108 (cuối tuần), 196 (chiều nay), 197 (6h-9h tối nay)
   - **v2:** 0211, 0214, 0248, 0266, 0282, 0300, 0303, 0362, 0464

#### 2. **Mislabel ngày — "nay" → "mai" hoặc ngược lại** (5 entries):
   - **Phase I:** 177 (sáng nay → rạng sáng mai), 197 (tối nay → trưa mai)
   - **v2:** 0240 (rạng sáng mai → tối CN), 0256 (đêm nay min ngoài khung), 0362 (trưa nay → trưa mai), 0464 (chiều 4-6h → tối/đêm/sáng mai)

#### 3. **Snapshot misuse cho future** (4 entries):
   - **v2_0324, v2_0325, v2_0433, v2_0500** — Sáng mai/12h tới/vài giờ tới → router gọi current_weather rồi bot dán snapshot làm forecast.

#### 4. **Mapping ngày-tuần sai** (4 entries):
   - **v2_0269, v2_0271, v2_0316, v2_0484** — "Tuần qua / 5 ngày qua / tuần vừa qua" → tool gọi 18-24/04 (cách HÔM NAY 02/05 ~10 ngày, không phải tuần qua). Đáng lẽ phải là 26/04-02/05.

#### 5. **Bịa hiện tượng / số liệu không có trong output** (3 entries):
   - **58** (mưa phùn cho data "mưa nhẹ"), **167** (bịa data tuần trước 20-26/04), **v2_0248** (UV 9.5 cho "sáng nay" mà thực là cả ngày), **v2_0451** (bịa khung giờ mưa cụ thể từ daily).

#### 6. **Đơn vị sai** (1 entry, lỗi cũ vẫn còn):
   - **v2_0372** — "giật **14.3 m/s**" trong output → bot ghi "**14.3 km/h**". Sai conversion (m/s × 3.6 = km/h, nên 14.3 m/s ≈ 51 km/h, không phải 14.3 km/h).

#### 7. **POI/scope mismatch** (3 entries):
   - **12** (Nội Bài → "HN toàn TP"), **v2_0231** (ngoại thành Bắc → "HN toàn TP"), **v2_0380** (nội thành vs Đông Anh → 2x "HN toàn TP" nhưng bot không phát hiện).

#### 8. **Recursion error còn 1 case** (1 entry):
   - **v2_0212** — "Rạng sáng mai vs rạng sáng hôm nay chênh" — đây là query cần so sánh forecast vs past, agent vẫn rơi vào recursion.

#### 9. **Phóng đại / sai cảm giác** (3 entries):
   - **60** ("hơi lạnh" cho 26.3°C), **v2_0271** ("đợt rét gây ấn tượng" cho 23.1°C T7 02/05), **v2_0211** (mơ hồ).

#### 10. **Mislabel khung trong daily** (2 entries):
   - **v2_0281, v2_0368** — "Trưa mai" → bot dán "chiều CN" (22.6-22.8°C) trong khi daily không có trường "trưa".

---

## Nhận định tổng kết

### Điểm tích cực:
1. **A/B/C/D từ rerun:** 37 A + 27 B = **64 Tier 1 pass / 79 (81.0%)** — tỷ lệ pass khá cao trong nhóm các câu vốn đã từng fail.
2. **D giảm mạnh:** Từ 14 D ban đầu (Phase II 13 + Phase III 1) còn lại **chỉ 1 D** (v2_0212). Recursion error đã được handle ở 4/5 trường hợp (269, 270, 316, 379, 484 — chỉ 212 còn).
3. **Transparency cải thiện rõ:** Nhiều câu (v2_0202, 0227, 0345, 0348, 0436, 0481) bot đã chủ động nói "thiếu data" thay vì bịa. Đây là tiến bộ lớn nhất.
4. **Tool mới hoạt động:** `compare_with_yesterday` (169) hoạt động tốt; phát hiện degenerate compare (0329) đã có cải thiện.

### Điểm tiêu cực — pattern persistent:

1. **Pattern temporal misattribution chưa fix** ở mức router: Khoảng **20+ entries vẫn vướng** lỗi cũ dán snapshot/forward cho quá khứ, hoặc dán "nay" cho "mai". Đây vẫn là failure mode chính, không phải fix bằng prompt-level mà cần **router-level enforcement**:
   - Khi anchor 22:00 và user hỏi "trưa nay/chiều nay/sáng nay" → router phải nhận ra khung đã qua, gọi `get_weather_history` thay vì `get_hourly_forecast` forward.
   - Khi hourly cover phần sau anchor + sáng mai, bot không được dán nhãn "sáng nay" cho data sáng mai.

2. **Mapping "tuần qua" vẫn sai:** Tool đang gọi `weather_period(start=18/04, end=24/04)` cho query "tuần qua" tại anchor 02/05. Đáng lẽ phải `start=26/04, end=02/05`. Lỗi này hiện diện ở **0269, 0271, 0316, 0484**. Cần fix ở router (date arithmetic).

3. **Sai đơn vị km/h vs m/s** (v2_0372) **vẫn nguyên si** từ Phase II — bot lấy số 14.3 m/s rồi ghi "14.3 km/h" mà không nhân 3.6.

4. **Snapshot misuse cho future query** vẫn là pattern lớn (0324, 0325, 0433, 0500). Khi router fail (`hourly_forecast` không trong subset) → fallback gọi current → bot không refuse mà dán snapshot làm forecast.

5. **POI/scope unresolved:** Tool `get_current_weather` cho POI ("Nội Bài"), ngoại thành phía Bắc, Đông Anh — đều trả "HN toàn TP". Bot không phát hiện và vẫn dán nhãn POI riêng cho data toàn TP. Cần tool flag rõ "POI not resolved, fell back to city".

### Ưu tiên fix tiếp theo:

| Mức ưu tiên | Vấn đề | Số entries còn lỗi | Fix layer |
|-------------|--------|---------------------|-----------|
| **P0** | Trưa/chiều/sáng "nay" với anchor đêm → khung đã qua | ~10 | Router: detect past-frame query, gọi history |
| **P0** | Mapping "tuần qua/N ngày qua" sai date arithmetic | 4 | Router: anchor-aware date math |
| **P1** | Snapshot dán làm future (sáng mai, 12h tới) | 4 | Router: refuse current cho future query, force hourly/daily |
| **P1** | Mislabel ngày "nay" ↔ "mai" trong forward data | 5 | Bot prompt: enforce labeling khớp với output time |
| **P2** | Sai đơn vị m/s → km/h (372) | 1 | Tool output: thêm cảnh báo đơn vị; bot prompt cấm convert tự |
| **P2** | POI/scope fallback im lặng | 3 | Tool output: flag `⚠ scope_fallback: city` khi POI unresolved |
| **P3** | Recursion error v2_0212 | 1 | Agent: aggregate tool cho query cross-time-frame |
| **P3** | Mislabel "trưa" trong daily không có "trưa" | 2 | Bot prompt: nếu daily chỉ có Sáng/Chiều/Tối, không dán "trưa" |

---

*Báo cáo audit rerun — 79 entries / `c1_20260502_213048.jsonl`. Anchor 22:00 Thứ Bảy 02/05/2026.*