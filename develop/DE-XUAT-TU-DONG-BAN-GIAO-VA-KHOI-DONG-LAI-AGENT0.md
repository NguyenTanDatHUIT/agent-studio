# Đề xuất: tự động viết bàn giao và khởi động lại Agent 0 khi context đạt ngưỡng

Trạng thái: **ĐỀ XUẤT, chưa phát triển.** Người viết: Agent 0 (Claude Code), theo yêu cầu của chủ máy, 10/11/2026.
Mục này nêu vấn đề, hiện trạng đã kiểm trong mã, phần chưa kiểm, đề xuất thiết kế, rủi ro và câu hỏi mở, để phát triển sau.
Liên quan: `docs/TINH-NANG-QUY-TAC-DIEU-PHOI-AGENT.md` (đặc tả quy tắc điều phối, mục 4.4, 5.12, 6.5), `logs/ao-thong-bao-sai.md` (nhật ký `[AO]` sai/thiếu).

## 1. Vấn đề
Một phiên điều phối dài (nhiều giờ, hàng chục lượt giao việc, đọc nhiều tệp) làm context của Agent 0 đầy dần. Ở phiên ngày 10/11/2026 context đã đạt khoảng **290k/1M token (29%)** sau vài giờ. Khi context lớn:
- Agent 0 chậm và dễ sai chi tiết (cùng nguyên nhân đã áp dụng cho agent con: giới hạn 3–4 việc mỗi cửa sổ).
- Claude Code tự nén ngữ cảnh khi gần đầy; sau nén, các quy tắc và trạng thái dễ bị mất hoặc tóm tắt thiếu.
- Việc viết bàn giao hiện do Agent 0 tự nhớ làm, **không có ngưỡng nào nhắc**, nên có thể làm quá muộn (sau khi nén) hoặc quên.
- Khi khởi động lại phiên, Agent 0 mới phải dựa vào tệp bàn giao có sẵn; nếu không có tệp, phải suy ra trạng thái từ git log, terminal và nhật ký.

Mong muốn của chủ máy: **cấu hình được** một ngưỡng (ví dụ **35% của 1M token**), khi chạm ngưỡng thì Agent 0 viết bàn giao theo mẫu, rồi phiên được khởi động lại và nhận đúng tệp bàn giao.

## 2. Hiện trạng (đã kiểm trong mã, 10/11/2026)
Các điểm sau đã đọc trực tiếp trong `agent_orchestrator/`:
- `terminals.py:1510` `restart_agent0(cols, rows)`: có sẵn, khởi động lại Agent 0.
- `terminals.py:1215-1245` `agent0_argv(resume, session_id)`: dựng dòng lệnh Claude Code; ghi `agent0-mcp.json`; thêm `--append-system-prompt-file` với bản prompt đã ghép (`rules.write_generated`) **mỗi lần mở, khởi động lại hoặc resume**. Hỗ trợ `--resume <session>` và `--session-id`.
- `terminals.py:1038` `notify_agent0`: chỉ gõ vào terminal Agent 0 các dòng `[AO] ...` về agent xong và thông báo workflow. **Không có** nhánh nào về context hay bàn giao.
- `terminals.py:642-643`, `providers.py:95-98`: có đọc số token (`input_tokens`, `output_tokens`, `cache_*`) nhưng **chỉ cho task của worker** chạy qua hàng đợi, không cho Agent 0.
- `mcp.py:50`: công cụ `get_orchestration_rules` mô tả "gọi sau khi cuộc trò chuyện bị nén hoặc mở lại" (chỉ là lời nhắc trong mô tả).
- Chưa có tham số cấu hình nào về ngưỡng context, mẫu bàn giao hay tự khởi động lại (đối chiếu danh sách tham số mục 4.1 của tài liệu quy tắc điều phối).

## 3. Chưa kiểm (cần xác minh trước khi xây)
1. **Nguồn số context của Agent 0.** Hai hướng khả dĩ, chưa hướng nào được kiểm trong môi trường này:
   - (a) File hội thoại (transcript JSONL) mà Claude Code ghi cho phiên: lấy `usage` của lượt trả lời assistant gần nhất (`input_tokens + cache_read_input_tokens + cache_creation_input_tokens`) làm ước lượng kích thước context. Cần xác nhận đường dẫn, định dạng và độ tin cậy của con số này.
   - (b) Cơ chế hook hoặc status line của Claude Code, nếu cung cấp phần trăm context cho lệnh ngoài. Cần xác nhận có hay không và định dạng.
   - Lệnh `/context` là lệnh nội bộ của Claude Code, Agent 0 không tự gọi được; công cụ cũng không gõ được vào ô nhập của Agent 0 để lấy kết quả một cách đáng tin.
2. **`restart_agent0` có làm mất các cửa sổ agent con không?** Ở lần khởi động lại ngày 10/11 (khoảng 06:39–08:24), các agent `agy` đang chạy biến mất. Chưa xác định nguyên nhân là khởi động lại **cả dashboard** hay chỉ riêng Agent 0. Nếu chỉ khởi động lại Agent 0 mà cửa sổ con còn nguyên thì tự khởi động lại giữa lúc agent đang làm là an toàn hơn; nếu không thì phải chờ hết việc.
3. **Phục hồi lịch/bộ theo dõi nền.** Lịch `CronCreate` và `Monitor` của Agent 0 sống theo phiên; khởi động lại là mất. Cần quyết định công cụ tự dựng lại hay Agent 0 mới tự dựng theo hướng dẫn trong tệp bàn giao.
4. Claude Code có cho **đặt ngưỡng tự nén** riêng không (nếu có, có thể dùng làm ngưỡng phụ) — chưa kiểm.

## 4. Đề xuất thiết kế

### 4.1 Tham số mới (thêm vào mục "Quy tắc điều phối agent" trong Cài đặt)
| Khoá | Mặc định | Ý nghĩa |
|---|---|---|
| `handover.enabled` | `false` | Bật tự động bàn giao + khởi động lại theo ngưỡng context. |
| `handover.context_window_tokens` | `1000000` | Cửa sổ context của model Agent 0 (để tính %). |
| `handover.warn_pct` | `30` | Từ ngưỡng này chỉ nhắc Agent 0 chuẩn bị (không bắt buộc). |
| `handover.trigger_pct` | `35` | Ngưỡng kích hoạt: yêu cầu Agent 0 viết bàn giao và dừng nhận việc mới. |
| `handover.auto_restart` | `false` | Sau khi bàn giao xong, tự khởi động lại Agent 0. Tắt = chỉ nhắc chủ máy bấm nút. |
| `handover.restart_when` | `no_active_builder` | Điều kiện được phép khởi động lại: `always` / `no_active_builder` / `all_agents_idle`. |
| `handover.dir` | `{PROMPTS_DIR}/handover` | Nơi lưu tệp bàn giao (ngoài repo đích, không bị commit). |
| `handover.template` | (ô Markdown) | Mẫu bàn giao mà Agent 0 phải theo (xem 4.3). |

### 4.2 Luồng
1. Bộ đo (4.4) lấy % context của Agent 0 định kỳ (khoảng 20–30 giây, nhẹ).
2. Chạm `warn_pct`: gõ một dòng `[AO]` nhắc ("context 30%, chuẩn bị bàn giao khi tới đoạn việc hợp lý"), chỉ một lần.
3. Chạm `trigger_pct`: gõ một dòng `[AO]` yêu cầu Agent 0: **không giao việc mới; nghiệm thu việc đang chạy nếu có; viết bàn giao theo mẫu vào `handover.dir`; trả đường dẫn tệp**. Công cụ ghi sự kiện (giờ, %) vào nhật ký.
4. Công cụ coi bàn giao **xong** khi tệp mới xuất hiện trong `handover.dir` (mtime sau thời điểm kích hoạt, kích thước tối thiểu, có đủ mục bắt buộc của mẫu); không tin lời Agent 0 nói đã xong.
5. Nếu `auto_restart` bật và điều kiện `restart_when` thoả: `restart_agent0` mở phiên **mới** (không `--resume`), và gõ dòng đầu tiên: "đọc tệp bàn giao X, rồi `get_orchestration_rules`, `list_terminals`". Nếu không thoả, hiện cảnh báo trên dashboard và nhắc chủ máy.
6. Nếu quá `handover.timeout_minutes` (ví dụ 20) mà chưa có tệp: ghi vào nhật ký, nhắc lại một lần, không tự khởi động lại.

### 4.3 Mẫu bàn giao (ô Markdown cấu hình được; mặc định tổng quát, không chứa tên riêng của dự án)
Các mục bắt buộc (công cụ kiểm có tiêu đề này):
1. Yêu cầu hiện tại của chủ máy và các quyết định đã chốt (kèm giờ).
2. Trạng thái repo: nhánh, hash commit mới nhất, tệp chưa commit của việc đang làm, **chưa push**.
3. Agent đang chạy: terminal, việc đang giữ, số việc đã làm trong cửa sổ, ai mở (Agent 0 hay chủ máy).
4. Việc đã nghiệm thu (bằng chứng) và việc **chưa nghiệm thu** (phần chưa đọc).
5. Hàng đợi việc kế (thứ tự, phụ thuộc, tệp prompt).
6. Câu hỏi chờ chủ máy.
7. Bài học và sai sót của phiên này.
8. Hướng dẫn dựng lại lịch/bộ theo dõi nền (nếu có).
9. Tệp quan trọng cần đọc đầu phiên.

### 4.4 Bộ đo context
- Hướng đề xuất: (a) đọc transcript của phiên Agent 0, lấy `usage` của lượt assistant gần nhất; chuyển thành % theo `context_window_tokens`. Chạy ở tiến trình dashboard, **chỉ đọc**, không ghi vào transcript.
- Nếu (a) không đủ tin cậy, hướng dự phòng: (b) hook/status line, hoặc cho Agent 0 tự báo bằng một công cụ MCP chỉ-ghi `report_context_usage(tokens)` (nhưng Claude Code có thể không cho Agent 0 biết con số này; **cần kiểm trước**).
- Hiển thị % trên giao diện cạnh tên Agent 0 và trong kết quả `list_terminals` (trường mới `context_pct`, có thể rỗng).

## 5. Rủi ro và giảm thiểu
| Rủi ro | Giảm thiểu |
|---|---|
| Khởi động lại làm mất các cửa sổ agent con (đã gặp ngày 10/11, chưa rõ nguyên nhân) | Kiểm trước (mục 3.2); mặc định `restart_when = no_active_builder`; hoặc chỉ nhắc, không tự khởi động lại. |
| Con số context sai/trễ nên kích hoạt sớm hoặc muộn | Dùng vùng đệm (`warn_pct` < `trigger_pct`), ghi nhật ký giá trị đo; cho chủ máy bấm kích hoạt tay. |
| Bàn giao thiếu mục, phiên sau mất thông tin | Công cụ kiểm tiêu đề bắt buộc của mẫu; không khởi động lại khi thiếu. |
| Agent 0 ghi bàn giao sai sự thật | Bàn giao chỉ là bản ghi; phiên mới vẫn phải kiểm lại bằng `git log`, `list_terminals`, đọc terminal. |
| Mất lịch tick/bộ theo dõi sau khởi động lại | Hướng dẫn dựng lại trong bàn giao (mục 8); cân nhắc công cụ tự dựng lại lịch `auto_mode` (mục 6.5 của đặc tả). |
| Khởi động lại giữa một nghiệm thu dở | Chỉ kích hoạt khi không có agent nào ở trạng thái `awaiting_review`/đang chờ nghiệm thu, hoặc Agent 0 ghi rõ phần dở vào bàn giao. |
| Tệp bàn giao chứa thông tin nhạy cảm | Lưu ngoài repo đích; không đưa vào commit; không gửi ra dịch vụ ngoài. |

## 6. Tiêu chí chấp nhận (gợi ý)
1. Đặt `handover.trigger_pct` thấp (ví dụ 1%) trong môi trường thử: dòng `[AO]` yêu cầu bàn giao được gõ đúng một lần, kèm giờ và % trong nhật ký.
2. Tệp bàn giao có đủ các tiêu đề bắt buộc; thiếu tiêu đề thì công cụ không coi là xong và không khởi động lại (test với tệp giả lập).
3. `auto_restart` tắt: không bao giờ tự khởi động lại; chỉ hiện nút/cảnh báo.
4. `auto_restart` bật: sau khi tệp hợp lệ xuất hiện và điều kiện thoả, phiên mới mở và nhận dòng đầu tiên trỏ đúng tệp (test đọc đối số dòng lệnh, không cần chạy Claude thật).
5. Cửa sổ agent con còn nguyên sau khi khởi động lại (hoặc đã chứng minh `restart_agent0` không đụng chúng).
6. Quy tắc tuỳ chỉnh không thêm công cụ hay gỡ lệnh cấm (`AGENT0_DENIED`); Agent 0 không có công cụ ghi quy tắc.
7. Bộ đo context chỉ đọc; không rò rỉ nội dung hội thoại ra log.

## 7. Câu hỏi mở cho chủ máy
1. Ngưỡng mặc định có đúng **35%** của 1M, hay tính theo cửa sổ context thực tế của model đang dùng?
2. Chấp nhận **tự khởi động lại** khi đang treo máy (chủ máy vắng) hay luôn chờ xác nhận?
3. Nếu có agent đang build khi chạm ngưỡng: chờ xong (đề xuất), hay khởi động lại ngay?
4. Mẫu bàn giao mặc định ở 4.3 có đủ không? Có cần mục riêng cho "quyết định thay chủ máy" (đã có file quyết định riêng trong chế độ tự động)?
5. Tệp bàn giao lưu ở `handover.dir` (ngoài repo) hay cũng sao chép vào `NhatKyCongViec/` của repo đích như các bàn giao hiện nay?

## 8. Chia pha gợi ý
- **Pha 0 (kiểm chứng, nửa ngày):** trả lời các điểm ở mục 3 (nguồn số context, `restart_agent0` có đụng cửa sổ con không, ngưỡng tự nén của Claude Code). Kết quả ghi vào nhật ký.
- **Pha 1:** bộ đo + hiển thị `context_pct` + nhắc `warn_pct` / `trigger_pct` (chưa tự khởi động lại), tham số trong Cài đặt, kiểm tiêu đề mẫu bàn giao.
- **Pha 2:** `auto_restart` với `restart_when`, dòng đầu tiên cho phiên mới, dựng lại lịch `auto_mode`.
- **Pha 3 (tuỳ chọn):** lịch sử bàn giao trong giao diện; liên kết với sổ vòng nghiệm thu (mục 6.4 của đặc tả).
