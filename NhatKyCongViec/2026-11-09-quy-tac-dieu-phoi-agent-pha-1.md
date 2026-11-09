# 2026-11-09: Quy tắc điều phối agent, Pha 1

Đặc tả: `docs/TINH-NANG-QUY-TAC-DIEU-PHOI-AGENT.md`. Làm Pha 1 (mục 6.1). Pha 2 (nhận diện treo/lỗi, đọc model từ footer, giám sát RAM) và Pha 3 (sổ vòng nghiệm thu) chưa làm.

## Quyết định thay cho câu hỏi mở (mục 12) vì chủ máy chưa trả lời
1. Thư mục prompt/báo cáo mặc định: `<state>/prompts` (đổi được trong cấu hình, phải là đường dẫn tuyệt đối ngoài repo).
2. Quy tắc chung toàn công cụ, chưa ghi đè theo repo.
3. Pha 3 để sau khi dùng thử Pha 1.
4. `max_concurrent_agents` chặn cứng, có công tắc `concurrency_enforced` để chuyển sang chỉ cảnh báo.
5. Model của `agy` gõ tay trong cấu hình (chưa đọc từ CLI).

## Đã làm
- `agent_orchestrator/rules.py` (mới): tham số mặc định, kiểm chặt (khoá lạ, kiểu, miền giá trị, kích thước, đường dẫn ngoài repo), lưu trong bảng `settings`, lịch sử 20 bản, khôi phục, thay biến (biến lạ giữ nguyên chữ và được báo), ghép prompt, dấu vết bản đã áp dụng.
- `terminals.py`: `agent0_argv` ghi `state/agent0-prompt.generated.md` (prompt lõi + quy tắc) mỗi lần mở/khởi động lại/resume; `get_orchestration_rules` thêm vào `AGENT0_TOOLS`; `open_agent` chặn khi đủ số agent tương tác đang sống (không tính Agent 0, không tính cửa sổ đã kết thúc; cửa sổ chủ máy tự mở bằng nút CMD không bị chặn).
- `mcp.py`: công cụ chỉ-đọc `get_orchestration_rules`. Không có công cụ ghi quy tắc.
- `web.py`: `GET/POST /api/orchestration-rules`, `/preview`, `/reset`, `/history`, `/restore`, `/restart-agent0`. Dùng POST thay PUT vì máy chủ chỉ có GET/POST. `/api/settings` không đổi.
- `examples/AGENT0-PROMPT.md`: mục 7 bước cứng được thay bằng đoạn trỏ tới quy tắc cấu hình + phần cố định (ý nghĩa dòng `[AO] đã xong`, đánh giá bằng bằng chứng, giới hạn đồng thời) và dặn gọi `get_orchestration_rules` đầu phiên/sau khi nén.
- Giao diện: nút "Quy tắc điều phối agent" trong menu cài đặt của khung Cửa sổ CMD mở hộp thoại (tham số, ba ô Markdown có bộ đếm, xem trước, lưu, khôi phục mặc định, lịch sử, xuất/nhập `.md`, trạng thái "Agent 0 đã/chưa nhận bản này" + nút khởi động lại).
- Test: `tests/test_rules.py` (18 test), `tests/rules_ui.cjs` (jsdom), mở rộng `tools/ui_shots.cjs` (hộp thoại quy tắc ở hai cỡ, sáng/tối).

## Kiểm chứng
- Ảnh thật ở 1280 và 460, sáng và tối đã xem: không tràn ngang, ô nhập theo template.
- `--resume`: **chưa kiểm bằng Claude Code thật** (mục 9 của đặc tả). `claude --help` không nói rõ system prompt bổ sung có được áp lại khi resume. Biện pháp: prompt lõi buộc Agent 0 gọi `get_orchestration_rules` đầu phiên và sau khi nén, nên quy tắc mới vẫn tới tay Agent 0 kể cả khi cờ không được áp lại.
- Chưa thử với Agent 0 thật; chưa kiểm `--append-system-prompt-file` nhận nhiều tệp (chỉ truyền một tệp đã ghép).
