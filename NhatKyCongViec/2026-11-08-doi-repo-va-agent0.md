# Nhật ký 2026-11-08: đổi repo sang NhiDong làm Agent 0 tự tạo agent trong khung của nó

## Hiện tượng
Sau khi chuyển repo từ `agent-orchestrator` sang `C:\CongViec\itc-git\HIS_EMR\NhiDong`, Agent 0 không mở cửa sổ CMD mới cho agent mà tự tạo agent ngay trong terminal của nó.

## Bằng chứng (bản ghi phiên Agent 0 thật, 15:31 UTC)
Agent 0 tự giải thích: hàng đợi của Agent Studio chỉ có repo `default` là `agent-orchestrator-selftest`, không có HIS_EMR, nên "tôi không dùng được `enqueue_task` hay `open_terminal` cho việc này", và nó giao cho một subagent (công cụ `Agent` của Claude Code) chạy nền. Cơ sở dữ liệu không có task nào cho NhiDong; phiên Agent 0 khởi động với `cwd = agent-orchestrator-selftest`.

## Hai nguyên nhân chồng nhau
1. **Đổi repo chỉ đổi trong bộ nhớ của tiến trình web** (`POST /api/repo`). Agent 0 là phiên riêng với thư mục làm việc cố định và một tiến trình MCP riêng đọc **file cấu hình** (vẫn ghi `agent-orchestrator-selftest`). Công cụ của Agent 0 vì thế gắn với repo cũ; việc `enqueue_task` còn lấy commit gốc của repo cũ.
2. **Không có gì ngăn Agent 0 tự làm.** Nó chạy ở chế độ tự động; `--allowed-tools` chỉ duyệt trước công cụ MCP, không cấm công cụ khác, nên khi công cụ MCP "không dùng được" nó chuyển sang `Agent`/Bash.

## Đã sửa
- `Config` nhận biến môi trường `AGENT_STUDIO_REPO` (ghi đè `repo`, vẫn qua mọi kiểm tra, sai thì báo lỗi). `agent0_argv()` đặt biến này cho MCP của Agent 0 bằng repo hiện tại của dashboard. File cấu hình không bị sửa.
- `POST /api/repo` mở lại Agent 0 (`Terminals.restart_agent0()`): thư mục làm việc và MCP theo repo mới; phiên cũ nằm trong Lịch sử. Phản hồi có `agent0_restarted`; thông báo trên giao diện nói rõ.
- Agent 0 được khởi chạy với `--disallowed-tools Agent Task Workflow Bash(claude:*) Bash(codex:*) Bash(agy:*)` (và `.exe`), và `AGENT0-PROMPT.md` có quy tắc "chỉ điều phối, báo lỗi công cụ cho người dùng, không tự làm thay".

## Kiểm chứng
- Thử cờ trên Claude Code thật: không còn công cụ `Agent`/`Task`; `claude --version` qua Bash bị từ chối.
- Claude Code thật + MCP thật, hai repo tạm A/B (không dùng repo thật của bạn, và không cấp "tin cậy thư mục" cho repo thật): Agent 0 mở ở A, đổi sang B, mở lại ở B; `enqueue_task` thành công, task mang commit gốc của B (trước đây là của A); khi nhờ tạo subagent, Agent 0 trả lời công cụ không có và tự nhắc dùng `enqueue_task`/`open_terminal`.
- Test: `tests/test_repo_switch.py` (6) và 2 test API trong `test_history.py`.

## Chưa giải quyết / cần bạn quyết
- **Profile test:** file cấu hình chỉ có `readiness` (`python -m unittest tests.test_readiness`) chỉ đúng với repo cũ. Task ở NhiDong cần profile test của chính NhiDong (ví dụ lệnh `dotnet`) do chủ máy khai báo; tôi không tự sửa cấu hình của bạn.
- **Mỗi lần khởi động lại công cụ** repo vẫn lấy từ file cấu hình (`selftest`) cho đến khi bạn chọn lại thư mục. Muốn mặc định là NhiDong thì đổi `repo` trong file cấu hình, hoặc làm công cụ nhớ repo đã chọn lần trước.
- Chặn bằng cờ không phải hộp cát: gọi CLI bằng đường dẫn tuyệt đối hoặc qua trình bao khác chưa bị chặn bằng cờ.
- Trong phiên cũ Agent 0 còn chạy `git push origin main` lên HIS_EMR theo yêu cầu "push đi"; việc đó không bị chặn (Bash vẫn có). Nếu muốn cấm Agent 0 push, thêm vào danh sách chặn.
