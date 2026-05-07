# AUDIT C1 — BATCH 2 (101–199 + v2_0200)
**Dataset:** `c1_20260503_155611.jsonl` (100 entries, 99 v1_legacy + 1 v2_new)
**Snapshot:** ~15:56–16:17 Chủ Nhật 03/05/2026
**Phân bố intent:** activity_weather=23, smalltalk=15, weather_alert=13, seasonal_context=13, expert_param=10, location_compare=8, rain=6, current=3, temp=3, daily=2, hourly=2, wind=1, fog=1
**Phân bố difficulty:** medium=37, hard=32, easy=31

---

## ID 101
**Q:** Hiện tại Cầu Giấy vs Hoàn Kiếm nơi nào mát hơn?
**Tool:** compare_weather snapshot — CG 29.8°C / HK 29.7°C, Δ +0.2°C.
**Claims:** Bot kết luận "không có sự khác biệt rõ rệt" — đúng. Số liệu khớp.
**Bucket: A.**

---

## ID 102
**Q:** Chiều nay mưa Hà Đông vs Thanh Xuân nơi nào nặng hơn?
**Tool:** compare_weather snapshot.
**Claims:** Bot **đúng cách** — nhận ra snapshot không cover "chiều nay", trả "mưa hiện tại chưa diễn ra" + offer gọi hourly. Awareness tốt.
**Bucket: A.**

---

## ID 103
**Q:** Tối nay gió Sóc Sơn vs Bắc Từ Liêm nơi nào mạnh hơn?
**Tool:** compare_weather snapshot 15:56. Tool note: "⚠ KHÔNG dùng cho tối nay".
**Claims:** Bot dán nhãn data snapshot là "Tối nay, gió ở Bắc Từ Liêm mạnh hơn" — **temporal misattribution rõ ràng**. Cuối câu mới offer hourly cho "tối nay cụ thể". Số liệu (7.4 vs 9.3 m/s) bot dán làm "tối nay" là sai khung.
**Bucket: C.**

---

## ID 104
**Q:** Mỹ Đình vs Times City.
**Tool:** compare_weather → "Không tìm thấy Times City".
**Claims:** Bot xin clarify đúng.
**Bucket: A.**

---

## ID 105
**Q:** Nội thành vs ngoại thành tối nay nhiệt chênh bao nhiêu?
**Tool:** get_current_weather + get_hourly_forecast (lỗi subset) + get_current_weather. Tất cả call snapshot. Bot abstain "không tra được".
**Claims:** Bot từ chối generic. Đáng lẽ có thể dùng district_multi_compare hoặc gọi nhiều location. Cách bot xử lý là "fail safe" nhưng thiếu effort.
**Bucket: B.**

---

## ID 106
**Q:** Ngày mai Long Biên vs Gia Lâm nơi nào mưa nhiều hơn?
**Tool:** get_daily_forecast lỗi subset → fallback compare_weather snapshot.
**Claims:** Bot describe data snapshot ("hiện tại 15:57") nhưng câu hỏi là "ngày mai". Có ack: "không có mưa trong khung giờ hiện tại. Nếu muốn lượng mưa ngày mai, mình có thể tra giúp". Acceptable nhưng không thực sự trả lời câu user hỏi.
**Bucket: B.**

---

## ID 107
**Q:** Hôm nay Tây Hồ vs Hoàng Mai nơi nào ẩm hơn?
**Tool:** compare_weather snapshot.
**Claims:** Cả 2 đều 82% → "bằng nhau". Đúng, trả lời trực tiếp.
**Bucket: A.**

---

## ID 108
**Q:** Cuối tuần này nội thành vs ngoại thành Hà Nội thế nào?
**Tool:** get_district_multi_compare snapshot 15:58. Tool note: "⚠ KHÔNG dùng cho cuối tuần / ngày mai".
**Claims:** Bot **vi phạm trực tiếp tool note**: dán nhãn snapshot data thành "Cuối tuần này (09/05–10/05), thời tiết ở nội thành... nhiệt độ 29.5–30.0°C, độ ẩm 54.5–57%..." — toàn bộ số liệu là snapshot tại 15:58 ngày 03/05 (Chủ Nhật) nhưng bot dán nhãn cho 09/05–10/05 (cuối tuần sau). **Lỗi temporal misattribution lớn**, tương tự ID 32 trong batch 1.
**Bucket: D.**

---

## ID 109
**Q:** Chiều nay Hồ Gươm dạo có ổn không?
**Tool:** get_hourly_forecast Hồ Gươm → "Không tìm thấy quận/huyện: ho guom".
**Claims:** Bot xin clarify. Đúng.
**Bucket: A.**

---

## ID 110
**Q:** Tối nay Mỹ Đình chạy bộ có ổn không?
**Tool:** get_hourly_forecast Mỹ Đình → tool **resolve sai** thành "Quận Ba Đình". Mỹ Đình thực tế thuộc Nam Từ Liêm.
**Claims:** Bot dùng data Quận Ba Đình + ghi rõ "Tối nay ở Mỹ Đình (Quận Ba Đình)" — gắn sai địa lý. Đây là lỗi từ tool nhưng bot không catch và còn enforce nó. Tương tự ID 9 và ID 68 trong batch 1.
**Bucket: C.**

---

## ID 111
**Q:** Cuối tuần này Ba Vì trekking thuận lợi không?
**Tool:** get_weather_period 09–10/05 Ba Vì → 09/05 mưa vừa 9.2 mm UV 9.0; 10/05 mưa nhẹ 1.4 mm UV 9.0.
**Claims:** Bot mô tả đầy đủ + kết luận "không thuận lợi do mưa và UV cao". Khớp data.
**Bucket: A.**

---

## ID 112
**Q:** Ngày mai Long Biên có nắng đủ phơi quần áo không?
**Tool:** get_daily_forecast 04/05 → mưa nhẹ 4.5 mm, UV 8.1, xác suất mưa 100%.
**Claims:** Bot kết luận "không phù hợp". Hợp lý.
**Bucket: A.**

---

## ID 113
**Q:** Tối nay đưa trẻ con đi công viên Cầu Giấy có lạnh không?
**Tool:** get_hourly_forecast 12h CG.
**Claims:** Bot mô tả mưa từ 19h, gió mạnh, 20–23°C "không quá lạnh". Khớp data, advice cẩn thận.
**Bucket: A.**

---

## ID 114
**Q:** Sáng mai Hà Nội tập thể dục được không?
**Tool:** get_best_time hôm nay forward.
**Claims:** Bot khuyến nghị 8–10h sáng mai (điểm 100/100). Khớp output.
**Bucket: A.**

---

## ID 115
**Q:** Cuối tuần Hồ Tây chụp ảnh có đẹp không?
**Tool:** get_weather_period 09–10/05 → resolve thành "Hà Nội (toàn thành phố)" thay vì Hồ Tây/Tây Hồ. Bot không cờ điều này, mô tả như cho Hồ Tây cụ thể.
**Claims:** Số liệu bám sát data Hà Nội nhưng trả lời cho POI Hồ Tây với data toàn thành phố. Mismatch nhẹ.
**Bucket: B.**

---

## ID 116
**Q:** Thứ bảy đi xe máy Hà Nội về Hòa Bình có gặp mưa không?
**Tool:** get_weather_period Hà Nội (Hòa Bình ngoài scope).
**Claims:** Bot trả thông tin Hà Nội cho Thứ Bảy 09/05 và Chủ Nhật 10/05 đều mưa. Không cảnh báo Hòa Bình ngoài scope. Khuyến nghị "đi xe máy từ Hà Nội về Hòa Bình hai ngày này" — implies bot có data cho cả tuyến, nhưng thực tế chỉ có Hà Nội.
**Bucket: B.**

---

## ID 117
**Q:** Hôm nay Hà Nội có thích hợp tổ chức sự kiện ngoài trời không?
**Tool:** get_activity_advice "su_kien" → "co_the", lý do mưa cao 80%.
**Claims:** Bot trả "có thể, cần lưu ý mưa, mang ô". Khớp output.
**Bucket: A.**

---

## ID 118
**Q:** Ngày mai Đan Phượng làm nông được không?
**Tool:** get_daily_forecast 04/05 → mưa nhẹ 4.1 mm, UV 8.1.
**Claims:** Bot viết **"Do trời có mưa và nắng gắt"** — mâu thuẫn nội tại (mưa và nắng gắt cùng lúc). Tương tự lỗi ID 33/74 batch 1. UV daily aggregate không bằng "nắng gắt" (mưa lớn UV vẫn ghi cao do daytime exposure).
**Bucket: C.**

---

## ID 119
**Q:** Sáng chủ nhật Hồ Gươm đi bộ có ướt không?
**Tool:** get_hourly_forecast → "Không tìm thấy ho guom". Bot xin clarify.
**Bucket: A.**

---

## ID 120
**Q:** Chiều nay sân Mỹ Đình bóng đá ổn không?
**Tool:** get_hourly_forecast → resolve thành "Hà Nội (toàn thành phố)" (sân Mỹ Đình là POI, không phải quận).
**Claims:** Bot dán nhãn data Hà Nội thành "sân Mỹ Đình" + dải nhiệt 19:00–22:00 "20.8–22.0°C" (data thực: 23.1, 21.4, 20.8, 21.0 → bot chỉ lấy giữa-thấp). Câu trả lời chung khớp pattern (mưa, không lý tưởng) nhưng số chi tiết bot dùng sai khung và POI.
**Bucket: B.**

---

## ID 121
**Q:** Hà Nội áp suất hPa hiện tại?
**Tool:** get_current_weather → 1007.6 hPa.
**Claims:** Bot trả 1007.6 hPa. Đúng.
**Bucket: A.**

---

## ID 122
**Q:** Đống Đa điểm sương bây giờ?
**Tool:** get_current_weather → điểm sương 20.2°C.
**Claims:** 20.2°C "ẩm và oi bức". Đúng.
**Bucket: A.**

---

## ID 123
**Q:** Trưa nay Tây Hồ UV mức nào?
**Tool:** get_current_weather snapshot 16:00 → UV 1.3 (thấp).
**Claims:** Bot dán nhãn "Trưa nay UV 1.3" — **temporal misattribution**. 16:00 là chiều, không phải trưa. UV thấp tại 16:00 không bằng UV trưa (typically peak ~12:00, thường cao hơn). Câu hỏi yêu cầu UV trưa, bot trả UV chiều và gọi là trưa.
**Bucket: C.**

---

## ID 124
**Q:** Hôm qua Gia Lâm tổng lượng mưa bao nhiêu?
**Tool:** get_weather_history 02/05 → 0.7 mm.
**Claims:** Bot trả "0.7 mm". Đúng và súc tích.
**Bucket: A.**

---

## ID 125
**Q:** Độ che phủ mây chiều nay Ba Đình?
**Tool:** get_hourly_forecast 12h.
**Claims:** Bot trả "82–100% trong khung 17:00–04:00". Vấn đề: "chiều nay" về mặt thời gian là 13–18h; bot mở rộng đến 04:00 sáng mai. Range mây 82–100% chỉ đúng cho phần khung dài hơn.
**Bucket: B.**

---

## ID 126
**Q:** Tối nay Hà Nội wind chill bao nhiêu?
**Tool:** get_current_weather snapshot.
**Claims:** Bot **CORRECTLY** acknowledge "wind chill không tính vì không đủ lạnh" + offer hourly cho tối. Tốt.
**Bucket: A.**

---

## ID 127
**Q:** Gió giật mạnh nhất hôm nay Hà Nội bao nhiêu m/s?
**Tool:** get_daily_summary lỗi subset → fallback get_current_weather → giật 14.8 m/s lúc 16:00.
**Claims:** Bot trả 14.8 m/s và **CHỦ ĐỘNG ack** "Đây là dữ liệu snapshot tại thời điểm hiện tại, không phải giá trị trung bình hoặc đỉnh cả ngày" + offer tra thêm. Excellent transparency, tránh bẫy temporal misattribution.
**Bucket: A.**

---

## ID 128
**Q:** Tối nay Hà Nội áp suất tăng/giảm so với chiều?
**Tool:** get_pressure_trend 12h forward → tăng +7.4 hPa.
**Claims:** Bot trả "tăng, +7.4 hPa". Khớp.
**Bucket: A.**

---

## ID 129
**Q:** Sáng mai Hà Nội điểm sương có đạt ngưỡng gây sương mù không?
**Tool:** get_humidity_timeline 24h. Tool note: "TUYỆT ĐỐI KHÔNG suy diễn từ độ ẩm/mây/nhiệt/điểm sương" cho sương mù.
**Claims:** Bot trả "điểm sương 17.4–19.8°C, ngưỡng sương mù thường ≤15°C, không đạt ngưỡng" + thêm "tuy nhiên độ ẩm cao có thể tạo điều kiện cho sương mù nhẹ". Phần "ngưỡng ≤15°C" là kiến thức bot tự thêm (không có trong data); phần cuối suy diễn sương mù từ độ ẩm — vi phạm tool note. Tương tự ID 84 batch 1 nhưng nhẹ hơn.
**Bucket: C.**

---

## ID 130
**Q:** Hồ Tây độ che phủ mây lúc hoàng hôn chiều nay?
**Tool:** get_hourly_forecast → resolve thành "Hà Nội (toàn thành phố)" (Hồ Tây là POI).
**Claims:** Bot trả "82–86% mây hoàng hôn 17–19h". Data 17:00=82%, 18:00=83%, 19:00=85%. Bot's "82–86%" bao gồm 86 không có trong data. Cũng dùng data Hà Nội cho POI Hồ Tây.
**Bucket: B.**

---

## ID 131
**Q:** Chiều nay Hà Nội có mưa dông mạnh không?
**Tool:** get_hourly_forecast 12h → data chỉ "Trời mây" → "Có mưa" (no thunder/dông tag).
**Claims:** Bot khẳng định **"Chiều nay có khả năng xảy ra mưa dông mạnh"** + đưa cảnh báo "mưa dông có thể gây ngập úng cục bộ và ảnh hưởng giao thông". Data **KHÔNG có dông** (thunder/giông) — chỉ là mưa thường. Bot **bịa** hiện tượng dông giống như ID 48 batch 1.
**Bucket: D.**

---

## ID 132
**Q:** Mấy ngày tới Bắc Từ Liêm có rét đậm rét hại không?
**Tool:** get_weather_alerts NOW → cảnh báo: [], số lượng 0.
**Claims:** Bot trả "không có cảnh báo... bao gồm rét đậm/rét hại" + offer get_daily_forecast cho mấy ngày tới. Câu hỏi "mấy ngày tới" — bot dùng tool snapshot NOW, đáng lẽ phải call forecast. Bot không proactively chạy forecast (đợi user xác nhận).
**Bucket: B.**

---

## ID 133
**Q:** Tuần này Hà Nội có nắng nóng gay gắt không?
**Tool:** get_temperature_trend 7 ngày forward → max 33.45°C ngày 06/05.
**Claims:** Bot trả "không có nắng nóng gay gắt, max 33.45°C, ngưỡng cần >35°C nhiều ngày liên tiếp". Reasoning hợp lý, ngưỡng đúng theo định nghĩa khí tượng VN.
**Bucket: A.**

---

## ID 134
**Q:** Tối nay Sóc Sơn có cảnh báo giông lốc không?
**Tool:** get_weather_alerts NOW → []. Bot trả "hiện tại không có cảnh báo giông lốc nguy hiểm" + offer hỏi thời tiết tối nay. Câu hỏi "tối nay" — bot dùng tool NOW. Thiếu chủ động gọi forecast.
**Bucket: B.**

---

## ID 135
**Q:** Cuối tuần này có bão/áp thấp ảnh hưởng Hà Nội không?
**Tool:** get_weather_alerts NOW → []. Bot trả "không có cảnh báo bão hay áp thấp" + offer cuối tuần. OK vì cảnh báo bão thường được cập nhật real-time và "không có cảnh báo" là câu trả lời hợp lý.
**Bucket: A.**

---

## ID 136
**Q:** Ngày mai HN có cảnh báo nguy hiểm không?
**Tool:** get_weather_alerts NOW → []. Bot trả "không có cảnh báo... (bão, rét hại, nắng nóng, giông, lũ)" + offer dự báo ngày mai. Câu trả lời cho câu hỏi mang tính "là có cảnh báo hiện hành không" → phù hợp.
**Bucket: A.**

---

## ID 137
**Q:** Mưa lớn tối nay Hà Nội có thể gây ngập ở khu vực nào?
**Tool:** get_rain_timeline + get_weather_alerts + get_district_ranking (lỗi subset) + get_daily_forecast 2 ngày.
**Claims:** Bot **bịa cụ thể 4 quận**: "có thể gây ngập cục bộ ở: Quận Hoàng Mai, Quận Thanh Trì, Quận Long Biên, Quận Hai Bà Trưng". **Không có data nào hỗ trợ** danh sách quận này — đây là kiến thức về urban geography Hà Nội bot tự thêm. Khẳng định "có thể gây ngập" cho specific districts là claim không có hỗ trợ data → hallucinate. Nguy hiểm vì user có thể tin và quyết định di chuyển dựa trên claim sai.
**Bucket: D.**

---

## ID 138
**Q:** Đợt lạnh sắp tới HN nhiệt xuống bao thấp?
**Tool:** get_temperature_trend → xu hướng "stable", min 18.7°C.
**Claims:** Bot trả "thấp nhất 18.7°C ngày 04/05". Câu hỏi giả định có "đợt lạnh sắp tới" — bot không phản biện claim này (xu hướng stable, không có đợt lạnh). 18.7°C cũng không phải "rét đậm". Bot trả 1 con số mà không clarify rằng không có cold spell rõ rệt.
**Bucket: B.**

---

## ID 139
**Q:** HN hôm nay có cảnh báo nắng nóng cực đoan không?
**Tool:** get_weather_alerts → []. Bot trả "không có cảnh báo nắng nóng cực đoan". Chính xác.
**Bucket: A.**

---

## ID 140
**Q:** Tuần tới HN có mưa giông kèm lốc xoáy không?
**Tool:** get_weather_alerts NOW → []. Bot trả "hiện tại không có cảnh báo nguy hiểm" + offer dự báo cụ thể. Reasonable.
**Bucket: A.**

---

## ID 141
**Q:** Trời HN dạo này khó chịu nhỉ?
**Tool:** get_seasonal_comparison → lạnh hơn TB 5.6°C.
**Claims:** Bot trả "đang mát hơn TB tháng 5, dễ chịu, có thể do gió hoặc thời tiết thay đổi". Hợp lý, không bịa.
**Bucket: A.**

---

## ID 142
**Q:** Mai có mưa không nhỉ?
**Tool:** get_daily_forecast 04/05 → mưa nhẹ 4.6 mm.
**Claims:** Bot trả "mưa nhẹ 4.6 mm, xác suất 100%, 18.7-28.2°C". Khớp.
**Bucket: A.**

---

## ID 143
**Q:** Trời lạnh có nên mặc áo phao không?
**Tool:** none. Bot xin clarify location.
**Claims:** Hợp lý — không có location, không tra được.
**Bucket: A.**

---

## ID 144
**Q:** Hôm nay nên mặc gì?
**Tool:** get_clothing_advice lỗi subset → fallback get_current_weather.
**Claims:** Bot recommend "áo khoác mỏng hoặc 外套" (Chinese characters lẫn vào — bug hiển thị/typo). Còn lại "ô, dù". Câu trả lời chính có giá trị nhưng output có lỗi formatting (CJK chars trong text Việt).
**Bucket: C.**

---

## ID 145
**Q:** Sao HN hôm nay nắng đẹp thế?
**Tool:** get_current_weather.
**Claims:** Bot **CORRECTLY phản biện** premise sai của user — "trời mây, mưa rất nhẹ, xác suất mưa 80%, mây u ám 81%". Tốt.
**Bucket: A.**

---

## ID 146
**Q:** Cần mang ô đi làm hôm nay không?
**Tool:** get_hourly_forecast 24h → có mưa từ chiều đến tối.
**Claims:** Bot trả thẳng "Bạn nên mang theo ô" + chi tiết. Khớp data.
**Bucket: A.**

---

## ID 147
**Q:** Mấy hôm nay thời tiết thay đổi quá nhỉ?
**Tool:** get_weather_change_alert → chuyển mưa lúc 19:00.
**Claims:** Bot trả "thay đổi đáng kể trong 6-12h tới, chuyển mưa 19:00". Khớp tool. Note: câu hỏi user nói "mấy hôm nay" (past trend) nhưng bot trả "trong 6-12h tới" (forward). Phần ack thiếu nhưng không sai.
**Bucket: A.**

---

## ID 148
**Q:** HN năm nay rét muộn không?
**Tool:** get_seasonal_comparison snapshot → lạnh hơn TB 5.6°C.
**Claims:** Bot kết luận **"mùa rét năm nay có thể kết thúc muộn hơn so với bình thường"** — extrapolate từ snapshot 1 thời điểm thành "mùa rét năm nay". Tool chỉ so sánh hiện tại vs TB tháng 5, không có data trend "muộn/sớm". Claim climatological không có hỗ trợ.
**Bucket: C.**

---

## ID 149
**Q:** Hôm nay có gì bất thường không?
**Tool:** get_current_weather.
**Claims:** Bot viết: "(82% độ ẩm), (21.1°C điểm sương) — đây là dấu hiệu của hiện tượng **nồm ẩm**". Vấn đề: 
- Bot gọi điểm sương 21.1°C là "thấp" (tool ghi "Rất ẩm, khó chịu 21.1°C" — đây là dew point cao chứ không thấp).
- Bot **bịa "nồm ẩm"** — nồm ẩm là hiện tượng mùa xuân/đông khi không khí ấm ẩm gặp tường lạnh; tại 24°C/82%/dew 21°C trong tháng 5 không phải nồm ẩm điển hình.
- Tool note `detect_phenomena` (không được gọi) lẽ ra cần thiết để xác nhận hiện tượng.
**Bucket: C.**

---

## ID 150
**Q:** Tối nay trời đẹp ngắm sao không?
**Tool:** get_current_weather snapshot 16:00.
**Claims:** Bot trả "Tối nay tại Hà Nội có mưa rất nhẹ, mây u ám, độ ẩm cao, không thuận lợi ngắm sao" — dán snapshot 16:00 thành "tối nay". Tool note "⚠ KHÔNG dùng cho tối nay". Phải gọi hourly forecast để check.
**Bucket: C.**

---

## ID 151
**Q:** Bây giờ ra ngoài có thoải mái không?
**Tool:** get_current_weather → 24.4°C, mưa rất nhẹ.
**Claims:** Bot mô tả đầy đủ + "nên mang ô, trời mát phù hợp đi dạo nhẹ". Hợp lý.
**Bucket: A.**

---

## ID 152
**Q:** Cầu Giấy có dễ chịu không?
**Tool:** get_comfort_index lỗi subset → fallback get_current_weather.
**Claims:** Bot mô tả 23.4°C trời mây gió mạnh cấp 5, kết luận "ấm và dễ chịu, tuy nhiên xác suất mưa cao". Khớp data.
**Bucket: A.**

---

## ID 153
**Q:** Chiều nay Hồ Tây ra ngoài ổn không?
**Tool:** get_hourly_forecast 12h Tây Hồ.
**Claims:** Bot mô tả "trời mây **rải rác**, có mưa". Data thực: mây u ám 79–94%, không phải rải rác. Misdescription. Tương tự lỗi ID 19 batch 1.
**Bucket: C.**

---

## ID 154
**Q:** Trời có chuyển mưa không?
**Tool:** get_weather_change_alert → chuyển mưa 19:00.
**Claims:** Bot trả "sẽ chuyển mưa từ 19:00". Khớp.
**Bucket: A.**

---

## ID 155
**Q:** Thời tiết sắp có thay đổi gì không?
**Tool:** get_weather_change_alert. Bot trả OK. Khớp.
**Bucket: A.**

---

## ID 156
**Q:** Vài giờ tới Đống Đa có biến động không?
**Tool:** get_weather_change_alert Đống Đa. Bot trả OK chuyển mưa 19:00. Khớp.
**Bucket: A.**

---

## ID 157
**Q:** Xin chào!
**Tool:** none. Bot greets, giới thiệu. OK.
**Bucket: A.**

---

## ID 158
**Q:** Thời tiết Đà Nẵng hôm nay?
**Tool:** none. Bot từ chối — "chỉ hỗ trợ Hà Nội". Đúng.
**Bucket: A.**

---

## ID 159
**Q:** Dự báo thời tiết Hà Nội tháng sau?
**Tool:** none. Bot từ chối — "tối đa 8 ngày". Đúng.
**Bucket: A.**

---

## ID 160
**Q:** Cuối tuần Ba Vì cắm trại được không?
**Tool:** get_weather_period 09–10/05 Ba Vì.
**Claims:** Bot mô tả 2 ngày + "không quá lạnh nhưng có mưa và UV cao, cân nhắc cắm trại trong nhà". Khớp data.
**Bucket: A.**

---

## ID 161
**Q:** Ngày mai Sóc Sơn câu cá có nên không?
**Tool:** get_daily_forecast 04/05 → mưa nhẹ 2.7 mm, UV 8.1.
**Claims:** Bot trả "không nên đi câu cá" + lý do mưa và UV cao. Hợp lý.
**Bucket: A.**

---

## ID 162
**Q:** Hôm nay Mỹ Đình tổ chức sự kiện ngoài trời được không?
**Tool:** get_activity_advice "su_kien" Mỹ Đình → "co_the", lưu ý mưa 80%.
**Claims:** Bot trả "có thể... mang ô". Khớp output.
**Bucket: A.**

---

## ID 163
**Q:** Mưa Hoàng Mai kéo dài đến mấy giờ?
**Tool:** get_rain_timeline 48h → đợt mưa 17:00 Chủ Nhật → 08:00 Thứ Hai.
**Claims:** Bot trả 17:00–08:00. Khớp tóm tắt.
**Bucket: A.**

---

## ID 164
**Q:** Hôm nay nóng hơn hôm qua không?
**Tool:** get_current_weather (24.4°C snapshot 16:00) + get_daily_forecast 02/05 (21.7–33.5°C, TB 30.3°C).
**Claims:** Bot kết luận **"hôm nay nóng hơn hôm qua"** dựa trên 24.4°C (snapshot 1 thời điểm) vs 21.7-33.5°C (cả ngày). Logic sai: 24.4°C < TB hôm qua 30.3°C, < max hôm qua 33.5°C → thực ra **hôm qua nóng hơn**. Bot dán snapshot làm proxy cho "nhiệt cả ngày hôm nay" và đưa kết luận trái ngược.
**Bucket: D.** (kết luận sai trực tiếp + temporal misattribution)

---

## ID 165
**Q:** So với hôm qua thì hôm nay Cầu Giấy thế nào?
**Tool:** compare_with_yesterday lỗi subset → fallback compare_weather(CG, CG) — **so sánh CG với CHÍNH NÓ tại NOW**. Kết quả: "+0.0°C, +0%".
**Claims:** Bot **không phát hiện** tool fallback bị broken (so sánh same-place-same-time). Bot trả "không có sự thay đổi đáng kể về nhiệt độ và độ ẩm... nhiệt độ vẫn giữ nguyên 23.4°C". Đây là "so sánh CG hôm nay với CG hôm nay" được dán nhãn "so với hôm qua". Kết luận hoàn toàn sai logic — không có data hôm qua nào.
**Bucket: D.**

---

## ID 166
**Q:** Mấy ngày nay HN nhiệt tăng/giảm?
**Tool:** get_temperature_trend 7 ngày FORWARD. Tool note: "TUYỆT ĐỐI KHÔNG dán nhãn 'X ngày qua'".
**Claims:** Bot **CORRECTLY** ghi "trong 7 ngày tới (từ Chủ Nhật 03/05 đến Thứ Bảy 09/05) ổn định, thay đổi 0.1°C/ngày". Không dán nhãn "mấy ngày qua" — tuân thủ tool note tốt.
**Bucket: A.**

---

## ID 167
**Q:** Tuần này HN khác tuần trước thế nào?
**Tool:** get_weather_period lỗi subset + get_weather_history 25/04 (1 ngày!) + get_daily_forecast 7 ngày từ 01/05.
**Claims:** Bot generalize từ **1 ngày 25/04** thành "tuần trước trung bình 25.2°C, ít mưa, gió 4.6-10.2 m/s, UV thấp...". Sai phương pháp — 25/04 không thể đại diện cho tuần 19-25/04. Bot cũng nói "UV cao hơn hẳn tuần trước (8.8-9.5)" trong khi UV historical thường 0.0 (không tính được, không phải UV thực thấp). Logic so sánh không có cơ sở.
**Bucket: C.**

---

## ID 168
**Q:** Mùa này HN có hay mưa giông buổi chiều không?
**Tool:** get_seasonal_comparison → snapshot vs TB tháng 5.
**Claims:** Bot trả **"Tháng 5 ở Hà Nội thường có mưa giông vào buổi chiều, đặc biệt 13–17h"** — climatological claim **NGOÀI DATA**. Tool chỉ trả "lạnh hơn TB 5.6°C", không có thông tin về pattern giông buổi chiều. Bot tự thêm kiến thức khí hậu.
**Bucket: C.**

---

## ID 169
**Q:** Hôm qua Đống Đa mưa to mà hôm nay nắng nhỉ?
**Tool:** compare_with_yesterday → hôm nay mưa to 30.9 mm 26.7°C; hôm qua mưa 0.9 mm 30.2°C.
**Claims:** Bot **CORRECTLY phản biện premise sai** — "hôm qua mưa nhẹ 0.9 mm; hôm nay mưa to 30.9 mm; hôm nay không chỉ mưa nhiều hơn mà còn mát hơn". Tốt.
**Bucket: A.**

---

## ID 170
**Q:** HN gần đây có hiện tượng cực đoan nào không?
**Tool:** get_seasonal_comparison.
**Claims:** Bot mô tả comparison hiện tại vs TB tháng 5 (lạnh hơn 5.6°C, 18 ngày mưa TB) nhưng **không trả lời thẳng** "có/không có hiện tượng cực đoan". Tool seasonal_comparison không cung cấp data về extreme events. Câu trả lời lạc đề.
**Bucket: B.**

---

## ID 171
**Q:** Long Biên hôm nay vs hôm qua chênh bao nhiêu?
**Tool:** compare_with_yesterday lỗi + history 02/05 (23.4-32.8°C) + current lỗi + daily_summary 03/05 (20.6-28.1°C).
**Claims:** Bot tính: "thấp hơn 2.8°C (23.4-20.6) và cao hơn 5.7°C (28.1-23.4)". Math: 28.1-23.4=4.7, không phải 5.7 — **lỗi tính toán**. Kết luận confused: bot nói cả "thấp hơn" và "cao hơn" mà không trả lời câu hỏi "chênh bao nhiêu". Hôm qua range rộng hơn (9.4°C) so với hôm nay (7.5°C); hôm qua nóng hơn ở peak.
**Bucket: C.**

---

## ID 172
**Q:** Phường Bạch Mai HBT thời tiết hiện tại?
**Tool:** get_current_weather ward → 23.7°C, mây u ám 79%, gió cấp 5.
**Claims:** Bot list đầy đủ data ward-level. Khớp.
**Bucket: A.**

---

## ID 173
**Q:** Phường Lĩnh Nam HM chiều nay có mưa không?
**Tool:** get_hourly_forecast 12h ward.
**Claims:** Bot trả "chiều nay (17–18h) có mưa với xác suất cao 80%". Vấn đề: tại 17:00 và 18:00 data có "xác suất mưa: Cao 80%" nhưng KHÔNG có cường độ mưa (no rain field) — chỉ có mưa từ 19:00 trở đi. Bot conflate "xác suất mưa cao" với "có mưa". Strictly đúng là "khả năng mưa cao chứ chưa mưa". Câu trả lời ngắn gọn nhưng chiều nay (13-18h) thực tế chưa mưa.
**Bucket: B.**

---

## ID 174
**Q:** Phường Vĩnh Tuy HBT tối nay gió mạnh không?
**Tool:** get_hourly_forecast 12h.
**Claims:** Bot mô tả gió 6.9–7.5 m/s cấp 4 hướng Đông Bắc. Data 17:00=6.9, 18:00=7.5, 19:00=7.0 m/s. Bot kết luận "không quá mạnh" + thêm thông tin mưa và độ ẩm. Khớp.
**Bucket: A.**

---

## ID 175
**Q:** Khoảng 8h tối phường Nghĩa Đô CG nhiệt độ?
**Tool:** get_hourly_forecast 13h.
**Claims:** Bot trả "8 giờ tối (19:00 Chủ Nhật)... nhiệt 22.6°C". 8h tối thường = 20:00, không phải 19:00. Bot off by 1 hour. Data 19:00=22.6°C (đúng nếu bot ngầm hiểu 19:00); 20:00 sẽ khác.
**Bucket: B.**

---

## ID 176
**Q:** Phường Tương Mai HM nhiệt lúc này?
**Tool:** get_current_weather ward → 23.7°C.
**Claims:** Bot trả 23.7°C đầy đủ context. Khớp.
**Bucket: A.**

---

## ID 177
**Q:** Phường Giảng Võ BĐ độ ẩm và sương mù sáng nay?
**Tool:** get_humidity_timeline FORWARD 24h từ 16:17. Tool note: "KHÔNG cover khung đã qua trong ngày (sáng/trưa nếu hỏi sau giờ đó)" + "TUYỆT ĐỐI KHÔNG suy diễn từ độ ẩm" cho sương mù.
**Claims:** Bot viết **"Độ ẩm sáng nay (16:17 Chủ Nhật) tại Giảng Võ dao động khoảng 83%..."** — dán nhãn timepoint 16:17 (chiều) là "sáng nay". Đây vừa là mismapping nhãn thời gian (16:17 ≠ sáng) vừa là vi phạm tool note (timeline forward không cover sáng đã qua). Sau đó bot khẳng định **"có nguy cơ hình thành sương mù cục bộ, đặc biệt từ 21:00 đến 02:00"** — vi phạm trực tiếp tool note "TUYỆT ĐỐI KHÔNG suy diễn".
**Bucket: D.**

---

## ID 178
**Q:** Phường Kiến Hưng HĐ dự báo 3 ngày tới?
**Tool:** get_daily_forecast 3 ngày ward.
**Claims:** Bot list đầy đủ 3 ngày + tổng hợp. Khớp tool output.
**Bucket: A.**

---

## ID 179
**Q:** Cuối tuần Xuân Phương NTL chạy bộ ổn không?
**Tool:** get_weather_period 09–10/05.
**Claims:** Bot mô tả 2 ngày + khuyến nghị "hoãn hoặc chuẩn bị". Khớp.
**Bucket: A.**

---

## ID 180
**Q:** Giá vé máy bay HN-HCM hôm nay?
**Tool:** none. Bot từ chối — "chỉ hỗ trợ thời tiết". Đúng.
**Bucket: A.**

---

## ID 181
**Q:** Nhà hàng nào ngon ở Hoàn Kiếm?
**Tool:** none. Bot từ chối + redirect về thời tiết Hoàn Kiếm. Đúng.
**Bucket: A.**

---

## ID 182
**Q:** Đà Nẵng cuối tuần?
**Tool:** none. Bot từ chối — out of scope. Đúng.
**Bucket: A.**

---

## ID 183
**Q:** Tỷ giá USD?
**Tool:** none. Bot từ chối — out of scope. Đúng.
**Bucket: A.**

---

## ID 184
**Q:** Viết code Python?
**Tool:** none. Bot từ chối — out of scope. Đúng.
**Bucket: A.**

---

## ID 185
**Q:** Ở đó nóng không?
**Tool:** none. Bot xin clarify location. Đúng.
**Bucket: A.**

---

## ID 186
**Q:** Thời tiết ngày mai?
**Tool:** get_daily_forecast 04/05 (default Hà Nội).
**Claims:** Bot default Hà Nội + trả thông tin đầy đủ ngày mai (mưa nhẹ 4.6 mm, 18.7-28.2°C, UV 9.3). Khớp. Default Hà Nội là behavior hợp lý cho weather chatbot Hà Nội.
**Bucket: A.**

---

## ID 187
**Q:** Khu đó có mưa không?
**Tool:** none. Bot xin clarify. Đúng.
**Bucket: A.**

---

## ID 188
**Q:** Chỗ kia thì sao?
**Tool:** none. Bot xin clarify. Đúng.
**Bucket: A.**

---

## ID 189
**Q:** Cho mình xem thời tiết đi.
**Tool:** get_current_weather (default Hà Nội).
**Claims:** Bot default Hà Nội + list full snapshot 16:00 + offer thêm forecast. OK.
**Bucket: A.**

---

## ID 190
**Q:** ha noi hom nay nong ko (no diacritics)
**Tool:** get_current_weather → 24.4°C "Ấm dễ chịu".
**Claims:** Bot list snapshot 24.4°C + extras. Câu hỏi yes/no "có nóng không" — bot không trả thẳng "không nóng" hoặc "ấm dễ chịu, không nóng". Người đọc phải tự suy luận từ "Ấm dễ chịu". Cũng dán snapshot 16:00 thành "hôm nay".
**Bucket: B.**

---

## ID 191
**Q:** toi o cau giay troi mua k (no diacritics)
**Tool:** get_hourly_forecast 24h.
**Claims:** Bot trả "Tối nay tại Cầu Giấy có mưa, cường độ mưa to từ 19h đến 04h sáng mai". Trực tiếp + chi tiết. Khớp data.
**Bucket: A.**

---

## ID 192
**Q:** troi ha noi co dep hem (no diacritics)
**Tool:** get_current_weather.
**Claims:** Bot mô tả snapshot đầy đủ + "trời không quá nóng nhưng cảm giác ẩm có thể khó chịu". Câu hỏi "có đẹp không" — bot không trả thẳng yes/no nhưng implication "không đẹp" rõ.
**Bucket: B.**

---

## ID 193
**Q:** nhiet do ha noi bnhieu do (no diacritics)
**Tool:** get_current_weather → 24.4°C.
**Claims:** Bot trả 24.4°C trực tiếp + extras. Khớp.
**Bucket: A.**

---

## ID 194
**Q:** bac tu liem hom nay co mua hong (no diacritics)
**Tool:** get_current_weather → snapshot Bắc Từ Liêm xác suất mưa cao 80%, mây u ám. Tool note "⚠ KHÔNG dùng cho hôm nay/tối nay".
**Claims:** Bot trả "khả năng mưa cao trong khung giờ hiện tại, mang ô". Câu hỏi "hôm nay" — bot dùng snapshot, đáng lẽ phải gọi hourly hoặc daily forecast cho cả ngày. Bot không gọi forecast.
**Bucket: B.**

---

## ID 195
**Q:** So sánh nhiệt hôm nay và ngày mai Hoàng Mai.
**Tool:** get_current_weather + get_daily_forecast 04/05 lỗi subset + get_current_weather (lặp lại).
**Claims:** Bot abstain "không tra được dữ liệu cho ngày mai... thử hỏi thời tiết hôm nay?". Bot có data hôm nay nhưng vẫn từ chối hoàn toàn thay vì đưa partial. Có thể dùng tool khác hoặc chí ít báo "tôi có hôm nay nhưng không có ngày mai".
**Bucket: C.**

---

## ID 196
**Q:** Chiều nay có mưa và nên mặc gì?
**Tool:** get_hourly_forecast 12h.
**Claims:** Bot trả 17–22h có mưa + áo khoác mỏng, ô, giày chống nước. Khớp.
**Bucket: A.**

---

## ID 197
**Q:** 6 sáng đến 9 tối nay nhiệt Ba Đình thay đổi thế nào?
**Tool:** get_hourly_forecast 27h (forward từ NOW 16:00).
**Claims:** Bot trả "6:00–9:00 sáng (Thứ Hai 04/05): nhiệt 19.4–21.8°C, không mưa". User hỏi **hôm nay** (Chủ Nhật) 6h–21h, nhưng 6h sáng hôm nay đã qua, tool chỉ có forward; bot mặc định trả "ngày mai" mà không clarify là không có 6h sáng hôm nay (đã qua). Bot cũng nói "10:00–17:00 nhiệt tăng đạt 28°C" — không rõ ngày nào, gây nhầm lẫn. Dán nhãn lộn xộn giữa hôm nay và ngày mai.
**Bucket: C.**

---

## ID 198
**Q:** HN tuần này ngày đẹp nhất sự kiện ngoài trời?
**Tool:** get_weather_period 03–10/05.
**Claims:** Bot chọn Thứ Ba 05/05 (xác suất mưa 33%, mưa 0.3 mm, 21.2–30.3°C). Reasoning bám data — đây là ngày khô nhất và ấm dễ chịu.
**Bucket: A.**

---

## ID 199
**Q:** Cuối tuần Ba Vì cần chuẩn bị gì?
**Tool:** get_weather_period lỗi subset → fallback get_daily_forecast 09–10/05.
**Claims:** Bot list 2 ngày + recommendations cụ thể (ô, áo mưa, kem chống nắng). Khớp data.
**Bucket: A.**

---

## ID v2_0200
**Q:** Phường Yên Hòa hiện tại có cần mang ô luôn bây giờ không? (v2_new source)
**Tool:** get_current_weather ward → 23.7°C, mây u ám 79%, gió cấp 5 8.8 m/s, xác suất mưa cao (implied).
**Claims:** Bot khuyến nghị "nên mang ô vì có thể có mưa bất ngờ". Reasonable từ snapshot. Đầy đủ context (gió, độ ẩm, áo khoác).
**Bucket: A.**

---


---

# PHẦN A — TỔNG HỢP SỐ LƯỢNG (Batch 2)

## A1. Phân loại bucket (100 entries)

| Bucket | Định nghĩa | Số lượng | % |
|---|---|---:|---:|
| **A** | Hoàn toàn đúng (faithful + complete + tool đúng) | 63 | 63% |
| **B** | Faithful nhưng thiếu sót (yes/no không trực tiếp, completeness chưa đạt) | 16 | 16% |
| **C** | Một phần faithful (claim ngoài data, dán nhãn sai khung, sai descriptor, lỗi formatting) | 15 | 15% |
| **D** | Unfaithful nghiêm trọng (hallucinate, kết luận sai trực tiếp, vi phạm tool note) | 6 | 6% |

**Faithfulness rate (A+B+C):** 94%.
**Completeness rate (A):** 63%.

## A2. Phân bố theo intent

| Intent | n | A | B | C | D |
|---|---:|---:|---:|---:|---:|
| activity_weather | 23 | 16 | 4 | 2 | 1 |
| smalltalk_weather | 15 | 13 | 1 | 1 | 0 |
| weather_alert | 13 | 6 | 5 | 0 | 2 |
| seasonal_context | 13 | 5 | 1 | 5 | 2 |
| expert_weather_param | 10 | 6 | 2 | 2 | 0 |
| location_comparison | 8 | 4 | 2 | 1 | 1 |
| rain_query | 6 | 3 | 2 | 1 | 0 |
| current_weather | 3 | 3 | 0 | 0 | 0 |
| temperature_query | 3 | 1 | 1 | 0 | 1 |
| daily_forecast | 2 | 2 | 0 | 0 | 0 |
| hourly_forecast | 2 | 1 | 0 | 1 | 0 |
| wind_query | 1 | 1 | 0 | 0 | 0 |
| humidity_fog_query | 1 | 0 | 0 | 0 | 1 |

(Số ước tính, sai lệch ±1 do gộp ranh giới.)

## A3. Phân bố theo độ khó

- **Easy** (31): A ~25, B ~3, C ~2, D ~1 → faithfulness 97%, completeness 81%.
- **Medium** (37): A ~24, B ~7, C ~5, D ~1 → faithfulness 97%, completeness 65%.
- **Hard** (32): A ~14, B ~6, C ~8, D ~4 → faithfulness 88%, completeness 44%.

Pattern lặp lại từ batch 1: lỗi tăng mạnh khi độ khó tăng. Hard ở batch 2 đặc biệt yếu vì nhiều câu yêu cầu suy luận seasonal/extrapolate (167, 168, 170) hoặc compare past+future (164, 165).

## A4. Phân bố source

- v1_legacy: 99 entries, A=62, B=16, C=15, D=6.
- v2_new (chỉ 1 entry, v2_0200): A=1.

---

# PHẦN B — DANH SÁCH LỖI NGHIÊM TRỌNG (Bucket D)

**Tổng cộng 6 entries D** (cao hơn batch 1's 4 entries — vì batch 2 có nhiều câu hỏi seasonal/comparison khó hơn).

## B1. ID 108 — Temporal misattribution lớn (cuối tuần ↔ snapshot NOW)
**Q:** "Cuối tuần này thời tiết nội thành vs ngoại thành Hà Nội thế nào?"
**Lỗi:** Bot gọi `get_district_multi_compare` (snapshot 15:58 ngày 03/05) và **dán nhãn toàn bộ số liệu là "cuối tuần này (09/05–10/05)"**. Tool note explicit: "⚠ KHÔNG dùng cho cuối tuần". Vi phạm trực tiếp.
**Mức độ:** Nghiêm trọng — toàn bộ con số bị sai khung thời gian (lệch ~6-7 ngày).

## B2. ID 131 — Hallucinate "mưa dông"
**Q:** "Chiều nay Hà Nội có mưa dông mạnh không?"
**Lỗi:** Data chỉ có "Có mưa" (không có thunder/giông tag). Bot khẳng định "có khả năng xảy ra **mưa dông mạnh**" + cảnh báo "mưa dông có thể gây ngập úng cục bộ và ảnh hưởng giao thông". Tương tự ID 48 batch 1.
**Mức độ:** Nghiêm trọng — bịa hiện tượng nguy hiểm khí tượng có thể ảnh hưởng quyết định người dùng.

## B3. ID 137 — Hallucinate cụ thể danh sách quận bị ngập
**Q:** "Mưa lớn tối nay HN có thể gây ngập ở khu vực nào?"
**Lỗi:** Bot khẳng định cụ thể **4 quận sẽ bị ngập**: "Quận Hoàng Mai, Quận Thanh Trì, Quận Long Biên, Quận Hai Bà Trưng". Không có data nào hỗ trợ — đây là kiến thức urban geography Hà Nội bot tự thêm.
**Mức độ:** Nghiêm trọng — claim cụ thể về địa lý hành chính có thể ảnh hưởng quyết định di chuyển; nguy hiểm về uy tín và độ tin cậy.

## B4. ID 164 — Kết luận so sánh nhiệt sai trực tiếp
**Q:** "Hôm nay nóng hơn hôm qua không?"
**Lỗi:** Bot so 24.4°C (snapshot 16:00 hôm nay) với 21.7-33.5°C (range cả ngày hôm qua) → kết luận "**hôm nay nóng hơn**". Thực tế hôm qua TB 30.3°C, max 33.5°C, đều cao hơn snapshot 24.4°C. Hôm nay thực sự MÁT hơn ở thời điểm so sánh. Logic sai + temporal misattribution (snapshot làm proxy cho cả ngày).
**Mức độ:** Nghiêm trọng — kết luận yes/no sai 180°.

## B5. ID 165 — So sánh same-place-same-time labeled as "hôm qua vs hôm nay"
**Q:** "So với hôm qua thì hôm nay Cầu Giấy thế nào?"
**Lỗi:** Tool `compare_with_yesterday` lỗi subset → bot fallback `compare_weather(CG, CG)` — tool returns CG vs CG NOW (cả 2 đều 23.4°C, "+0.0°C, +0%"). Bot **không phát hiện** tool fallback bị broken và trả "không có sự thay đổi đáng kể... nhiệt vẫn 23.4°C". Đây là so sánh CG với chính nó nhưng dán nhãn "hôm nay vs hôm qua".
**Mức độ:** Nghiêm trọng — câu trả lời hoàn toàn không có ý nghĩa; bot không sanity-check tool output.

## B6. ID 177 — Suy diễn sương mù + dán nhãn 16:17 là "sáng nay"
**Q:** "Phường Giảng Võ Ba Đình độ ẩm và sương mù sáng nay?"
**Lỗi:** Tool humidity_timeline FORWARD 24h từ 16:17. Bot viết "Độ ẩm sáng nay (16:17) tại Giảng Võ..." — 16:17 là chiều, không phải sáng. Tool note: "KHÔNG cover khung đã qua trong ngày" + "TUYỆT ĐỐI KHÔNG suy diễn từ độ ẩm" cho sương mù. Bot khẳng định "có nguy cơ hình thành sương mù cục bộ 21:00-02:00" — vi phạm trực tiếp lệnh cấm. Tương tự ID 84 batch 1.
**Mức độ:** Nghiêm trọng — vi phạm 2 lệnh cấm explicit cùng lúc (label thời gian + suy diễn forbidden field).

---

# PHẦN C — NHẬN ĐỊNH CHUNG (Batch 2)

## C1. So sánh batch 1 vs batch 2

| Tiêu chí | Batch 1 (1–100) | Batch 2 (101–200) |
|---|---:|---:|
| A | 64% | 63% |
| B | 17% | 16% |
| C | 14% | 15% |
| D | 4% | **6%** |
| Faithfulness | 96% | 94% |
| Completeness | 64% | 63% |

Batch 2 **xấu hơn nhẹ** ở Bucket D (4 → 6 entries). Faithfulness giảm 2 điểm.

**Nguyên do batch 2 có nhiều D hơn:**
1. **Tỷ lệ hard cao hơn** (32% vs 16% ở batch 1) — câu hỏi seasonal_context và location_comparison phức tạp.
2. **Nhiều câu hỏi compare past/future** — bot dễ rơi vào trap so sánh snapshot với daily aggregate (ID 164, 165, 167, 171).
3. **Câu hỏi about hiện tượng cụ thể** (mưa dông, giông lốc, ngập úng, sương mù) — bot dễ hallucinate khi data không có (IDs 131, 137, 177).
4. **Tool subset của batch 2** có nhiều lỗi cascading hơn — `compare_with_yesterday`, `get_daily_forecast`, `get_weather_history` thường lỗi; bot fallback không tốt (ID 165 đặc biệt).

## C2. Pattern lỗi nổi bật ở batch 2 (so với batch 1)

### C2.1. Vẫn là temporal misattribution (lỗi cốt lõi không đổi)
- **Batch 2 entries:** 103 (snapshot → tối nay), 108 (snapshot → cuối tuần), 123 (16:00 → trưa nay), 125 (chiều mở rộng đến 04:00 sáng mai), 150 (snapshot → tối nay), 164 (snapshot → cả ngày), 177 (16:17 → sáng nay), 190 (snapshot → hôm nay), 194 (snapshot → hôm nay), 197 (sáng mai conflate hôm nay).
- **9–10 entries** có dấu hiệu temporal mismatch — xấp xỉ batch 1.

### C2.2. Hallucinate hiện tượng (xu hướng tăng ở batch 2)
- **Mưa dông** (ID 131): bịa hiện tượng dông không có data.
- **Giông** (đề cập sai trong activity advice): bot có xu hướng add "giông" cho mưa.
- **Sương mù suy diễn** (IDs 129, 177): vi phạm tool note "TUYỆT ĐỐI KHÔNG suy diễn".
- **Nồm ẩm** (ID 149): bịa hiện tượng nồm ẩm trong tháng 5 — climatologically suspicious.
- **Mưa giông buổi chiều** (ID 168): bịa pattern climatology không có trong tool output.
- **Ngập cụ thể quận** (ID 137): bịa danh sách 4 quận bị ngập từ kiến thức urban geography riêng.

### C2.3. Sanity-check tool output yếu (mới phát hiện)
- ID 165 đặc biệt cho thấy bot **không kiểm tra sanity** khi tool fallback returns trivial output (so sánh A vs A). Bot trình bày kết quả "+0.0°C" như là so sánh thật giữa 2 thời điểm.
- ID 171 lỗi tính toán đơn giản (28.1-23.4=4.7 ≠ 5.7 như bot viết).
- Đây là lỗi mới so với batch 1 — chỉ ra bot thiếu logic sanity-check sau tool call.

### C2.4. Climatological extrapolation (đặc biệt seasonal_context)
- IDs 148 (rét muộn), 167 (tuần này vs tuần trước từ 1 ngày), 168 (mùa này hay mưa giông chiều), 149 (nồm ẩm).
- Bot có xu hướng extrapolate từ 1 datapoint (snapshot, 1 ngày history) thành claim climatology toàn mùa. Tool `get_seasonal_comparison` chỉ trả snapshot vs TB tháng — bot tự thêm trend/pattern.

### C2.5. POI/ward resolution & geographic mismatch (vẫn còn)
- ID 110: Mỹ Đình → resolve sai thành "Quận Ba Đình" (đáng lẽ Nam Từ Liêm). Tương tự lỗi Mỹ Đình ở ID 9, 68 batch 1.
- IDs 115 (Hồ Tây), 120 (sân Mỹ Đình), 130 (Hồ Tây): tool resolve POI thành "Hà Nội (toàn thành phố)" → bot dùng data Hà Nội cho POI và không cờ.
- ID 109, 119: "Hồ Gươm" không tìm thấy → bot đúng cách xin clarify.

### C2.6. Yes/no không trả lời trực tiếp (vẫn còn ở batch 2)
- IDs 138 (đợt lạnh xuống bao thấp), 170 (cực đoan), 173 (chiều mưa), 190 (nóng không), 192 (đẹp không), 194 (hôm nay mưa không).
- Bot dùng pattern "list data + để user tự suy luận" → câu trả lời chậm và buộc user diễn dịch.

## C3. Điểm mạnh ở batch 2

1. **Out-of-scope refusals đúng cách** (180–184, 158, 159): chuẩn xác, thân thiện.
2. **Clarification khi vague location** (143, 185, 187, 188, 109, 119): hợp lý.
3. **Default Hà Nội khi không có location** (186, 189): UX tốt cho weather chatbot Hà Nội.
4. **Chủ động phản biện premise sai** (145 nắng đẹp → mưa, 169 hôm qua mưa to → thực ra hôm nay mưa to): excellent fact-checking behavior.
5. **Tool note awareness ở 1 số entries**:
   - ID 102: nhận ra snapshot không cover "chiều nay", offer hourly.
   - ID 126: từ chối wind chill hợp lý (không đủ lạnh).
   - ID 127: explicit ack "snapshot ≠ giá trị cả ngày".
   - ID 166: tuân thủ "KHÔNG dán nhãn 'X ngày qua'" trên temp_trend forward.
   
   Đây là trường hợp bot đọc và áp dụng tool note đúng — cần được nuôi dưỡng và phát triển thêm.

## C4. Điểm yếu cần ưu tiên

| Mức độ | Pattern | Số entries ảnh hưởng | Tần suất tăng/giảm so batch 1 |
|---|---|---:|---|
| 🔴 Cao | Hallucinate hiện tượng (dông, sương mù, nồm ẩm, ngập) | 5–7 | TĂNG |
| 🔴 Cao | Temporal misattribution snapshot/forecast | 9–10 | Bằng |
| 🟡 Trung | Climatological extrapolation từ 1 datapoint | 4 | TĂNG (intent seasonal nhiều hơn) |
| 🟡 Trung | POI/ward resolve sai địa lý | 4 | Bằng |
| 🟡 Trung | Yes/no không trực tiếp | 6+ | Bằng |
| 🟠 Mới | Sanity-check tool output thiếu (165, 171) | 2 | MỚI |
| 🟢 Thấp | Math errors (171) | 1 | MỚI |
| 🟢 Thấp | Output formatting (CJK chars 144) | 1 | MỚI |

## C5. Khuyến nghị bổ sung từ batch 2

1. **Ưu tiên 1:** Strict prompt rule cho hallucinate hiện tượng — bất kỳ claim "dông/giông/lốc/sương mù dày/ngập/nồm ẩm" phải có **explicit field từ tool output** xác nhận. Nếu không → từ chối hoặc trả "không có data".
2. **Ưu tiên 2:** Tool sanity-check guardrail — bot phải kiểm tra `compare_weather(A, B)` returns Δ=0 và A=B → đây là so sánh trivial, không nên dùng làm câu trả lời.
3. **Ưu tiên 3:** Math validation cho các phép tính trừ/cộng đơn giản — bot tính sai 28.1-23.4=5.7 (thực tế 4.7).
4. **Ưu tiên 4:** Tách biệt rõ "snapshot tại NOW" vs "aggregate cả ngày" trong câu trả lời so sánh. Khi user hỏi "hôm nay vs hôm qua" và bot có snapshot hôm nay + range hôm qua → phải so với daily aggregate hôm nay (gọi tool khác) hoặc rõ ràng cảnh báo "tôi chỉ có snapshot 1 thời điểm, không thể so sánh chính xác cả ngày".
5. **Ưu tiên 5:** Intent classifier cho seasonal_context — bot đang extrapolate trend/pattern từ datapoint đơn lẻ. Cần thêm rule "không claim climatology unless tool returns explicit pattern data".

## C6. Kết luận

**Batch 2 (101–200) cùng config C1/v1_legacy** có chất lượng baseline tương tự batch 1 (~63–64% A, ~94–96% faithfulness) nhưng số D tăng từ 4 → 6 entries do:
- Phân bố intent nghiêng về activity/seasonal/comparison khó hơn.
- Bot dễ hallucinate hiện tượng cụ thể (dông, ngập, sương mù) khi câu hỏi gợi ý.
- Bot thiếu sanity-check khi tool output trivial hoặc fallback fail.

**6 entries D ưu tiên fix:** 108 (cuối tuần snapshot), 131 (mưa dông bịa), 137 (4 quận ngập bịa), 164 (kết luận nóng hôm nay sai), 165 (so CG vs CG), 177 (sương mù suy diễn + 16:17 là sáng nay).

Tất cả pattern systemic đều xuất phát từ **system prompt / tool design** chứ không phải model variance — cần fix ở level prompt/tool, không thể giải quyết qua tweaking output post-hoc.
