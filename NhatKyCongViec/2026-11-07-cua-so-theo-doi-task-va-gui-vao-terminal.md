# Nhật ký công việc — Cửa sổ theo dõi task, ID terminal, Agent 0 gõ vào terminal, Luồng dữ liệu thật

**Ngày:** 07/11/2026
**Dự án:** `C:\CongViec\agent\agent-orchestrator`
**Trạng thái bàn giao:** Code và test xong, chưa commit. Chưa thử bằng Claude/Codex thật và chưa gõ phím trong trình duyệt thật.

## Vấn đề người dùng gặp

1. Agent 0 giao việc (`enqueue_task`) nhưng không thấy terminal mới. Nguyên nhân: tool chỉ ghi vào hàng đợi;
   runner chạy worker headless nên dashboard không có gì để hiển thị.
2. Tự mở một cmd có ID `codex#1` thì Agent 0 không giao việc theo ID được: chỉ có `list_terminals` và `read_terminal`.
3. Trang Luồng tự động trông như dữ liệu mẫu: chỉ đọc hàng đợi, còn Agent 0, runner, terminal, profile test là chữ cố định.

## Đã làm

- **Cửa sổ theo dõi task** (`TaskView` trong `terminals.py`): mỗi task `queued`/`running` tự có một cửa sổ chỉ đọc, bất kể
  được tạo từ MCP, web hay CLI (monitor 1 giây). Hiển thị sự kiện, log worker (Codex JSONL tóm tắt; Claude trả một lần
  nên có nhịp "vẫn đang chạy"), log test, kết quả. Giữ nguyên cách chạy headless vì engine cần kết quả có cấu trúc để xác minh;
  chuyển sang ConPTY sẽ mất cơ chế đó.
- **ID terminal**: `resolve_id` nhận `codex-1`, `codex#1`, `Codex #1`, `codex 1`, `task 1a2b3c4d`. ID hiện trên thẻ cửa sổ.
- **`send_to_terminal`** (MCP tool thứ 11): gõ một dòng vào terminal agent tương tác. Có xác nhận mỗi lần, cầu nối chỉ thêm đúng
  một đường POST có khóa, bỏ ký tự điều khiển, gộp một dòng, tối đa 4000 ký tự, 1 giây giữa hai lần, ghi `terminal-audit.jsonl`.
- **Luồng tự động**: node Agent 0 hiện kết nối MCP và tool gần nhất; node worker hiện trạng thái runner và số terminal mở; node test
  hiện profile trong config; thêm bảng "Hoạt động trực tiếp" (Agent 0, runner, terminal có nút Mở, sự kiện).
- `enqueue_task` báo danh sách test profile hợp lệ khi chọn sai; lỗi từ dashboard được chuyển nguyên lý do cho Agent 0
  (trước đây mọi lỗi đều thành "unavailable").
- Cập nhật `examples/AGENT0-PROMPT.md`, `SECURITY.md`, `docs/WEB-APP.md`, `README.md`.

## Lỗi đã giả định và xử lý (đều có test)

ID sai/mơ hồ (báo danh sách ID hợp lệ); đóng nhầm ID không tồn tại không được đóng tất cả (đã tự mắc lỗi này khi viết, test bắt lại);
terminal đã kết thúc; gửi vào Agent 0 hoặc cửa sổ theo dõi; text rỗng/quá dài/không phải chuỗi; chèn ESC, OSC, C1 qua text hoặc
qua log worker; xuống dòng làm TUI gửi sớm; gửi dồn dập; dashboard tắt hoặc file bridge cũ sau khi sập; sai khóa bridge,
chỉ có token dashboard; task bị hủy/lỗi/xóa khỏi queue; log chưa có, dòng dở dang, UTF-8 hỏng, dòng khổng lồ; runner không chạy
(cảnh báo sau 8 giây); quá 12 cửa sổ (dọn cửa sổ đã xong, hoặc ghi sự kiện `terminal_skipped`); người dùng đóng cửa sổ thì
không mở lại; Enter thật sự chạy lệnh trên ConPTY thật.

## Kiểm thử

- 103 test Python pass (65 cũ + 38 mới trong `tests/test_taskview.py`).
- `tests/flow_ui.cjs` (jsdom) pass, thêm kiểm tra dữ liệu thật; sửa phần giả lập fetch vì test cũ đã lỗi từ trước (trả sai dạng
  cho `/api/runners`, `/api/agent0`, `/api/terminals`).
- `tests/web_ui.cjs` lỗi sẵn trên HEAD (kỳ vọng 4 cửa sổ demo từ thiết kế CMD cũ), không sửa.
- Một lần chạy đầu của bộ test cũ có `ConnectionAbortedError` ngẫu nhiên; lần sau pass hết.

## Việc còn lại

- Khởi động lại Start-Agent Studio và mở lại Agent 0 để nạp code và tool mới.
- Chưa có tool cho Agent 0 tự mở terminal tương tác mới (cố ý; cần xác nhận riêng nếu muốn).
- Adapter headless cho `agy` để giao qua hàng đợi (từ nhật ký 06/11).
- Sửa hoặc thay `tests/web_ui.cjs`.
