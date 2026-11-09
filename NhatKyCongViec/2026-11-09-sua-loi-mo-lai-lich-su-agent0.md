# Nhật ký 2026-11-09: Sửa lỗi không mở lại được lịch sử chat của Agent 0

## Vấn đề được báo cáo
Khi vào tab **Lịch sử** và bấm **Mở lại** (`resume`), các agent khác (`claude`, `codex`, `agy`) đều mở lại được phiên lịch sử bình thường, riêng **Agent 0** không mở lại lịch sử mà vẫn giữ nguyên cửa sổ Agent 0 trống hiện tại.

## Nguyên nhân gốc rễ (Root Cause)

1. **`Terminals.open('agent0', resume=...)` trả về sớm khi `agent0` đang chạy (`agent_orchestrator/terminals.py`)**:
   - Khi mở dashboard (hoặc sau khi tạo cuộc trò chuyện mới / đổi repo), `syncTerms()` tự động mở sẵn một phiên `agent0` mới (`self.sessions['agent0']` luôn có trạng thái `alive = True`).
   - Khi người dùng bấm **Mở lại** trên một hội thoại cũ của Agent 0, `Terminals.resume_conversation()` gọi `self.open('agent0', cols=cols, rows=rows, resume=sess_id)`.
   - Tuy nhiên trong `Terminals.open()`, nhánh `if kind == 'agent0':` kiểm tra `if existing and existing.alive: return self.describe(existing)` ngay lập tức mà không kiểm tra tham số `resume`. Do phiên `agent0` trống đang mở sẵn (`alive = True`), hàm trả về luôn phiên trống đó thay vì đóng phiên trống và khởi chạy `claude --resume <session_id>`.

2. **Bộ lọc "Agent 0" / "Claude" trong `Store.conversation_list()` (`agent_orchestrator/store.py`)**:
   - Khi lưu hội thoại của Agent 0 vào bảng `conversations`, dữ liệu được ghi với `provider='claude'` và `kind='agent0'`.
   - Khi lọc trên giao diện theo `provider=agent0`, câu truy vấn SQL tìm `WHERE provider='agent0'` nên trả về rỗng; còn khi lọc `provider=claude` lại trộn lẫn cả Agent 0.

3. **Xử lý phiên Claude khi người dùng gõ `/resume` trực tiếp trong terminal & lọc lệnh slash khỏi tiêu đề (`agent_orchestrator/terminals.py`, `agent_orchestrator/transcripts.py`)**:
   - Khi người dùng gõ `/resume` ngay khi vừa mở Claude Code (chưa gửi tin nhắn nào vào `--session-id` ban đầu), Claude Code không tạo tệp `<session_id>.jsonl` mới mà ghi tiếp vào tệp `<resumed_session_id>.jsonl` trong `~/.claude/projects/<project-slug>/`. Nếu sau đó bấm **Mở lại** theo `session_id` ban đầu thì tệp `.jsonl` không tồn tại.
   - Các lệnh slash đầu tiên như `/model`, `/mo`, `/resume`, `/res` bị `title_from_keys()` bắt làm tiêu đề hội thoại thay vì đợi câu nhắc thực tế đầu tiên của người dùng.

4. **Đua luồng (Race condition) trong `streamLoop()` khi thay thế terminal cùng ID (`agent_orchestrator/web_assets/app.js`, `agent_orchestrator/terminals.py`)**:
   - Khi `agent0` được thay bằng tiến trình mới (cùng `id='agent0'` nhưng `gen` mới), yêu cầu long-poll `/api/terminals/stream` đang chờ của phiên `agent0` cũ trả về có thể ghi đè con trỏ `after` hoặc trạng thái `ended` sang đối tượng terminal mới trong `terms`.

## Các thay đổi đã thực hiện

1. **`agent_orchestrator/terminals.py`**:
   - Trong `Terminals.open()`: khi `kind == 'agent0'` và có `resume`, nếu `existing` đang chạy với `session_id != resume`, đóng phiên `agent0` hiện tại (`self.close('agent0')`), cập nhật trạng thái hội thoại cũ thành `'closed'` trong DB, rồi khởi tạo `Session('agent0', ...)` mới với `self.agent0_argv(resume=resume)`.
   - Đảm bảo `Session.created` (`gen`) luôn tăng nghiêm ngặt giữa các phiên để frontend luôn nhận diện được thế hệ terminal mới.
   - Thêm `resolve_claude_session()` và gọi trong `Terminals.resume_conversation()` để tự động đối chiếu tệp `.jsonl` thực tế trong `~/.claude/projects/<project-slug>/` (qua transcript hoặc thời gian hoạt động) nếu `session_id` ban đầu không có tệp `.jsonl` do người dùng từng dùng `/resume` trong terminal.
   - Bổ sung trường `'gen'` vào kết quả trả về của `Terminals.stream()`.

2. **`agent_orchestrator/store.py`**:
   - Trong `Store.conversation_list()`: phân tách bộ lọc `provider == 'agent0'` (`(kind='agent0' OR provider='agent0')`) và `provider == 'claude'` (`(provider='claude' AND kind!='agent0')`).

3. **`agent_orchestrator/transcripts.py`**:
   - Trong `title_from_keys()`: bỏ qua các dòng lệnh slash (`/model`, `/mo`, `/resume`, `/res`, ...) để chỉ lấy câu lệnh/nội dung trao đổi thực sự đầu tiên làm tiêu đề hội thoại.

4. **`agent_orchestrator/web_assets/app.js`**:
   - Trong `streamLoop()`: đối chiếu đúng thực thể terminal đã gửi request (`reqMap`) và kiểm tra `x.gen === e.gen` trước khi cập nhật dữ liệu/trạng thái vào xterm.

5. **Cập nhật dữ liệu lịch sử hiện có (`C:\AgentControl\studio-state\queue.sqlite3`) & Kiểm thử (`tests/test_history.py`)**:
   - Cập nhật lại `session_id` thực tế và tiêu đề cho các bản ghi Agent 0 trong DB hiện tại từng dùng `/resume` / `/model`.
   - Thêm các unit test `test_resume_agent0_replaces_running_blank_agent0`, `test_resolve_claude_session_when_resumed_inside_terminal`, `test_slash_commands_are_ignored_for_title` và kiểm tra lọc `agent0` vs `claude` trong `tests/test_history.py`.
   - Chạy toàn bộ bộ test (`test_history.py`, `test_ui_rules.py`, `test_idle_busy.py`, `test_repo_switch.py`, `test_taskview.py`): **133/133 tests PASS**.

