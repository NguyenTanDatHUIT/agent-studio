# Nhật ký công việc — Terminal nhúng, Agent 0, Antigravity

**Ngày:** 06/11/2026  
**Dự án:** `C:\CongViec\agent\agent-orchestrator`  
**Trạng thái bàn giao:** Dashboard có terminal thật nhúng (Agent 0 và các agent mở thêm), sống qua F5, Agent 0 theo dõi được chỉ-đọc. Chưa tự động hóa agy qua hàng đợi.

## 1. Chạy thử thật hai agent song song

- Tạo config ngoài repo (`C:\AgentControl\*.json`), kiểm tra `doctor --probe --check-auth`: Claude 2.1.318 và Codex 0.166.0 đều tương thích và đã đăng nhập.
- Giao 2 task nhỏ khác file cho Claude và Codex, mỗi task có test profile `readiness`; cả hai tới `awaiting_review`, đã review diff, `record-review approve`, `export` patch, áp bằng `git apply`, commit và push (`d5edc3c`).
- Repo gốc có `.git` thuộc tài khoản khác nên git báo "dubious ownership"; orchestrator cố ý bỏ qua git config toàn cục. Đã chạy trên bản clone `agent-orchestrator-selftest`. Lỗi quyền sở hữu repo gốc vẫn còn.

## 2. Mở nhanh bằng một lối tắt

- Thêm cờ `web --open` (mở trình duyệt đúng link có token); `Start-AgentStudio.cmd` luôn truyền cờ này. Lối tắt Desktop "Agent Studio" trỏ vào config `C:\AgentControl\studio.json`.
- Dữ liệu dashboard chuyển sang state mới, trống (`studio-state`); state cũ giữ nguyên.

## 3. Terminal thật trong dashboard

- `agent_orchestrator/terminals.py`: ConPTY qua `ctypes` (chỉ thư viện chuẩn). Lỗi đã gặp: phải đặt `STARTF_USESTDHANDLES` với handle NULL, nếu không tiến trình con in ra console của cha; phải chờ tiến trình bằng `WaitForSingleObject` rồi mới đóng pseudo console.
- xterm.js 5.5.0 + addon-fit đóng gói trong `web_assets/vendor/` (MIT, không CDN).
- Chỉ mở được loại phiên cố định: `agent0` hoặc `agent` (claude/codex/agy) trong repo hoặc worktree của task. Trình duyệt không gửi lệnh tùy ý; API cần bearer token và same-origin. Terminal tương tác không dùng chế độ restricted của runner. Đã ghi vào `SECURITY.md` và `docs/WEB-APP.md`.
- Agent 0 là phiên Claude Code tương tác đã nối MCP orchestrator; tool đọc/giao việc chạy không hỏi, `record_review`, `export_patch`, `cancel_task` vẫn hỏi xác nhận.
- Bỏ ô nhập giả trên thẻ CMD (từng khiến "gõ CMD" thành "tạo task"), bỏ thẻ Hàng đợi/Audit khỏi trang CMD. Hộp "Thêm CMD" giờ chọn agent và thư mục làm việc.
- Terminal do server giữ nên F5 nối lại và phát lại bộ đệm (tối đa 1 MB mỗi phiên).
- Gộp mọi terminal vào một long-poll chung (`/api/terminals/stream`) vì trình duyệt giới hạn 6 kết nối/host; tăng `request_queue_size` lên 128; bỏ qua `ConnectionError` khi trình duyệt ngắt.
- CSS: lưới CMD cao đều nhau, terminal lấp đầy thẻ.

## 4. Agent 0 theo dõi agent khác (chỉ đọc)

- MCP thêm `list_terminals`, `read_terminal` (tổng 10 tool). MCP gọi dashboard qua `terminal-bridge.json` trong state dir (cổng + khóa riêng, chỉ GET). Nội dung terminal là dữ liệu không đáng tin, đã dặn trong `examples/AGENT0-PROMPT.md`.
- Cố ý không có tool gõ vào terminal khác (tránh kênh prompt injection giữa agent).
- MCP ghi `agent0-presence.json` để thẻ Agent 0 hiện trạng thái kết nối.

## 5. Antigravity (`agy`)

- `agy` 1.4.12 tại `C:\Users\tsmda\AppData\Local\agy\bin\agy.exe`; thêm vào `discover`, config mẫu và hộp "Thêm CMD". Hiện chỉ dùng dạng terminal tương tác.

## 6. Kiểm thử

- 65 test Python pass (`test_web`, `test_readiness`, `test_orchestrator`), gồm test mới cho định tuyến terminal, ConPTY và cầu nối. Hai test đếm tool MCP đã cập nhật 8 → 10.
- Dùng Edge headless điều khiển qua CDP: 3 cửa sổ cao 395px, 3 xterm có nội dung, F5 giữ nguyên. Cờ `--screenshot` của Edge chụp quá sớm nên không đáng tin.
- Chưa tự gõ phím trong trình duyệt thật.

## Việc còn lại

- Adapter headless cho agy (`-p`, `--output-format`) để giao task qua hàng đợi.
- Đổi quyền sở hữu `.git` của repo gốc để chạy trực tiếp, không cần bản clone.
- Task Claude "Thất bại" cũ trong `studio-state` (prompt chỉ là lời chào) chưa dọn.
