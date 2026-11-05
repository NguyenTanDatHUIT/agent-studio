# Cấu hình do chủ máy quản lý

Schema version 1, JSON UTF-8 (chấp nhận BOM Windows). Config được nạp khi CLI/MCP
khởi động; runner giữ cấu hình trong bộ nhớ. Sau khi chỉnh test/provider/quyền,
dừng và khởi động lại runner/MCP để cùng dùng một cấu hình. Không chỉnh config
trong lúc có task chạy. SQLite/state chưa có migration framework.

| Field | Mặc định / giới hạn |
|---|---|
| version | Bắt buộc bằng 1 |
| repo | Repository root tuyệt đối, có commit |
| state_dir | Tuyệt đối, rời cây repo |
| base_ref | HEAD, main hoặc local ref hợp lệ; resolve khi enqueue |
| acknowledge_local_execution | false; chỉ true mới thực thi worker/test |
| timeout_seconds | 900; số nguyên 1..86400, mỗi process |
| output_limit_bytes | 8000000; 1024..100000000, mỗi stdout/stderr |
| agent_env_allow | []; tên biến bổ sung cho worker, không cho test |
| providers | claude/codex, command và model; không có extra_flags |
| tests | Map tên identifier sang argv cố định; cần ít nhất một profile cho mỗi task |

Command provider chỉ nhận `[absolute_executable]` hoặc
`[absolute_interpreter, absolute_entrypoint.js/.py]`. Không cho prefix flags
chèn trước các cờ hạn chế của adapter. `.py` dành cho adapter do chủ máy viết và
offline test double. Điều này không biến một executable/script không tin cậy thành
an toàn: chủ máy chịu trách nhiệm kiểm tra chương trình trong config.

Test profile có thể chứa đối số nhưng chỉ do chủ máy cấu hình; MCP/task chỉ chọn
tên. Relative test script được giải quyết trong worktree; absolute interpreter
có thể là Python venv ngoài worktree. Nếu interpreter/test cần biến môi trường
đặc thù, cấu hình một entrypoint test do chủ máy quản lý. Không dựa vào toàn bộ
environment máy được truyền nguyên vẹn.

CLI trả mã 0 khi thao tác thành công, 2 cho lỗi input/config, 1 khi `worker --once`
xử lý một task failed, 130 khi Ctrl+C. Với cancelled, trạng thái trong database là
nguồn xác định; CLI worker không dùng exit code để biểu đạt mọi trạng thái nghiệp vụ.
`worker --once` không có task cũng trả 0. Runner liên tục in từng id/status khi
xử lý xong; chi tiết ở `show`, `events` và raw log.
