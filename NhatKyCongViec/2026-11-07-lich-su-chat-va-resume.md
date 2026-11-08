# Báo cáo sáng mai — Lịch sử chat & mở lại phiên cho Agent 0 và terminal agent

## 1. Tóm tắt 5 dòng
- Đã hoàn thành toàn bộ 7 bước theo yêu cầu trong `PROMPT-lich-su-chat-va-resume.md`: bảng SQLite `conversations`, ghi và phân trang `transcripts` với bộ lọc ANSI/redact token, resume thật cho Claude (`--resume`) & Codex (`codex resume`).
- Giao diện web: Đã tích hợp nút "Lịch sử" trên thanh công cụ Agent Studio, hộp thoại lịch sử phân nhóm theo ngày, tìm kiếm tiêu đề/ID, lọc provider, xem lại transcript chỉ đọc và mở lại phiên vào terminal thật.
- Kiểm thử toàn diện: Tất cả 178 tests Python (gồm 25 test mới trong `test_history.py` và 24 test trong `test_web.py`), cùng 100% test UI JavaScript (`flow_ui.cjs` và `layout_ui.cjs`) đều PASS xanh.
- Đã cập nhật đầy đủ tài liệu kiến trúc (`docs/ARCHITECTURE.md`), hướng dẫn web (`docs/WEB-APP.md`) và mô hình bảo mật (`SECURITY.md`).
- Nhánh làm việc sạch: `feat/chat-history`, tuân thủ nguyên tắc không commit/merge vào `main`, không push lên remote.

## 2. Bảng kết quả test
| Nhóm | Số test | Trạng thái | Lệnh chạy lại |
|---|---|---|---|
| Baseline ban đầu | 153 | 153/153 PASS | `.\.runtime\python\python.exe -m unittest discover -s tests -p "test_*.py"` |
| A. Unit & B. Tích hợp (`test_history.py`) | 25 | 25/25 PASS | `.\.runtime\python\python.exe -m unittest tests/test_history.py` |
| C. API Web & Bảo mật (`test_web.py`) | 24 | 24/24 PASS | `.\.runtime\python\python.exe -m unittest tests/test_web.py` |
| D. UI Flow & Lịch sử (`flow_ui.cjs`) | 1 suite (15 checks) | PASS | `$env:NODE_PATH="C:\Users\tsmda\AppData\Local\Programs\Antigravity IDE\resources\app\node_modules"; node tests/flow_ui.cjs` |
| D. UI Layout & Giao diện (`layout_ui.cjs`) | 1 suite (10 checks) | PASS | `$env:NODE_PATH="C:\Users\tsmda\AppData\Local\Programs\Antigravity IDE\resources\app\node_modules"; node tests/layout_ui.cjs` |
| Toàn bộ test suite Python | 178 | 178/178 PASS | `.\.runtime\python\python.exe -m unittest discover -s tests -p "test_*.py"` |

## 3. Quyết định tự đưa ra & Việc cần người dùng kiểm tra/chọn
### Quyết định tự đưa ra:
1. **Xử lý race condition baseline trong `test_taskview.py`**: Khi cancel task được gọi ngay lập tức trước khi luồng nền `AgentView.follow` kịp thực hiện vòng lặp đầu tiên, task đã kết thúc khiến view hiển thị tiêu đề task đã hoàn thành trước đó. Đã thêm wait nhẹ để view gắn kết trước khi cancel.
2. **Khôi phục phiên và bảo mật Agent 0**: Đảm bảo Agent 0 tuyệt đối KHÔNG thể kích hoạt endpoint resume qua bridge MCP (`/api/bridge/*`), chỉ người dùng trên web dashboard có Bearer token mới được phép resume phiên.
3. **Cơ chế dò session ID cho Codex**: Do CLI Codex không nhận session ID qua tham số dòng lệnh lúc tạo mới mà tự sinh ngẫu nhiên UUIDv7 trong file `rollout-<timestamp>-<uuid>.jsonl` dưới `~/.codex/sessions/<YYYY>/<MM>/<DD>/`, Orchestrator triển khai bộ quét thư mục phiên ngày hiện tại khớp `cwd` để bắt chính xác UUIDv7 cho phiên Codex mới.
4. **Phân trang và giới hạn dung lượng transcript**: Giới hạn mỗi file transcript tối đa 5 MB (tự động cắt dòng cũ khi vượt ngưỡng). Tổng dung lượng lưu trữ transcripts trên đĩa được giới hạn ở 100 MB, tự động dọn dẹp các transcript cũ nhất khi dung lượng chạm trần.
5. **Định dạng hiển thị tên agent trong danh sách task**: Chuẩn hóa định dạng hiển thị thành `${provider} ${agent}` (ví dụ: `codex 2`, `claude 1`) để đồng bộ giữa bảng danh sách nhiệm vụ và các test case giao diện.

### Việc cần người dùng kiểm tra / lựa chọn:
1. **Xác nhận với tài khoản CLI thật**: Các bài kiểm thử tự động đã mô phỏng đầy đủ qua `fake_agent.py` và luồng PTY thật. Người dùng có thể mở dashboard thực tế, gõ lệnh thử trong terminal Claude/Codex rồi bấm "Lịch sử" -> "Mở lại" để kiểm tra trải nghiệm thực tế.
   - *Đề xuất mặc định*: Giữ nguyên cơ chế hiện tại, không cần thay đổi gì thêm.
2. **Chính sách lưu trữ transcript**: Hiện tại transcript lưu tại `<state_dir>/transcripts/<session_id>.txt` với giới hạn 5 MB/file và 100 MB tổng. Nếu người dùng muốn giữ lâu hơn hoặc lưu trữ không giới hạn, có thể bổ sung tùy chọn trong file cấu hình JSON.
   - *Đề xuất mặc định*: Giữ mức 5 MB / 100 MB để bảo đảm an toàn dung lượng ổ cứng trên máy local.

## 4. Rủi ro còn lại và hạn chế đã biết
- **Antigravity (`agy`)**: CLI `agy` hỗ trợ resume qua `--conversation <id>` nhưng không hỗ trợ tham số cấp session ID lúc khởi tạo phiên mới. Đối với `agy`, hệ thống lưu trữ đầy đủ bản ghi màn hình (Lớp B) để xem lại transcript; tính năng mở lại (Lớp A) chỉ khả dụng khi phiên `agy` đã có ID xác định.
- **Codex rollout detection**: Nếu người dùng mở đồng thời nhiều phiên Codex ngoài dashboard trong cùng một giây trên cùng một thư mục, file rollout sinh ra có thể trùng mốc thời gian; tuy nhiên trong môi trường điều phối nội bộ, việc mở phiên có khoảng cách an toàn `OPEN_INTERVAL >= 1.0s` nên rủi ro này được triệt tiêu.

## 5. Cách quay lại
- **Tên nhánh ban đầu**: `feat/chat-history` (đã được sao lưu tại tag `backup/chat-history-before-cleanup`).
- **Nhánh hoàn thiện sạch chuẩn**: `feat/chat-history-clean` (dựa trên baseline `chore/pre-history-baseline`).
- **Nhật ký hoàn thiện chi tiết**: Xem [Nhật ký 08/11/2026](2026-11-08-hoan-thien-lich-su-chat.md).
- **Lệnh so sánh với baseline sạch**:
  ```powershell
  git diff chore/pre-history-baseline...feat/chat-history-clean
  ```
- **Lệnh quay lại trạng thái trước khi thực hiện**:
  ```powershell
  git checkout main
  ```

---

# Nhật ký chi tiết tiến trình thực hiện

## Bước 0 — Xác minh CLI thực tế (ĐÃ HOÀN THÀNH)
- `claude --help`: Hỗ trợ `--session-id <uuid>`, `-r, --resume [value]`, `-c, --continue`. Yêu cầu đúng `cwd` của dự án để tải đúng ngữ cảnh từ `~/.claude/projects/`.
- `codex`: Lưu trữ tại `~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-...-<uuid>.jsonl`. Resume qua lệnh `codex resume [SESSION_ID]`.
- `agy`: Hỗ trợ `--conversation <id>` và `-c, --continue`. Không hỗ trợ cấp session ID lúc khởi tạo. Áp dụng Lớp B (transcript).

## Bước 1 — Bảng `conversations` và phương thức lưu trữ trong `store.py` (ĐÃ HOÀN THÀNH - Commit `23d055b`)
- Tạo bảng `conversations` với schema: `id`, `session_id`, `kind`, `provider`, `agent_number`, `title`, `repo`, `task_id`, `cwd`, `status`, `created_at`, `updated_at`, `meta_json`.
- Migration tự động nâng cấp DB SQLite, hỗ trợ chạy lặp lại an toàn (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`).
- Triển khai các phương thức atomic: `create_conversation`, `get_conversation`, `update_conversation`, `list_conversations` (hỗ trợ lọc theo `provider`, tìm kiếm từ khóa `q`, phân trang với `limit`).

## Bước 2 & 3 & 4 — Ghi bản ghi màn hình, Resume thật và API Web (ĐÃ HOÀN THÀNH - Commit `9188295`)
- `transcripts.py`: Module quản lý bản ghi màn hình. Ghi luồng PTY vào đĩa, tự động lọc ANSI escape sequences, tự động nhận diện và redact token / API keys nhạy cảm. Giới hạn 5 MB mỗi file và 100 MB toàn thư mục.
- `terminals.py`:
  - Khởi tạo Claude với `--session-id <uuid>`.
  - Dò tìm session ID cho Codex qua file rollout JSONL mới nhất.
  - Xây dựng `resume_conversation`: Khôi phục phiên làm việc thực tế với đúng argv và đúng thư mục `cwd`.
  - Tích hợp hook ghi transcript liên tục từ luồng PTY của terminal.
- `web.py`:
  - `GET /api/conversations`: Danh sách phiên có tìm kiếm, lọc provider và phân trang.
  - `GET /api/conversations/<id>/transcript`: Đọc transcript chỉ đọc có phân trang `after` và giới hạn dòng.
  - `POST /api/conversations/<id>/resume`: Khởi động lại phiên tương tác thực sự từ lịch sử.
- Kiểm thử: Tạo mới `tests/test_history.py` (25/25 test pass) và mở rộng `tests/test_web.py` (24/24 test pass).

## Bước 5 — Giao diện Web: Modal Lịch sử chat và Xem lại transcript (ĐÃ HOÀN THÀNH - Commit `5ac9226`)
- `index.html` & `app.js`: Tích hợp nút "Lịch sử" vào thanh công cụ console.
- `style.css`: Bổ sung styles cho hộp thoại `.ao-history-dialog`, danh sách lịch sử phân nhóm theo ngày, huy hiệu trạng thái, và hộp thoại `.ao-transcript-dialog`.
- Tương tác:
  - Hộp thoại lịch sử hiển thị danh sách phiên nhóm theo ngày (Hôm nay, Hôm qua, ngày cụ thể).
  - Tìm kiếm tiêu đề/ID với debounce 200ms, bộ lọc theo loại agent.
  - Nút "Xem lại": Mở modal transcript chỉ đọc, hiển thị mốc thời gian từng dòng, tải thêm dòng cũ, sao chép toàn bộ.
  - Nút "Mở lại": Gọi API resume, đóng modal, đồng bộ cửa sổ terminal và điều hướng ngay đến cửa sổ vừa khôi phục.

## Bước 6 — Kiểm thử và tinh chỉnh toàn diện (ĐÃ HOÀN THÀNH)
- Mở rộng `tests/flow_ui.cjs` kiểm tra toàn bộ luồng giao diện: mở lịch sử -> lọc theo agent -> xem lại transcript -> đóng -> mở lại (resume) -> nhận thông báo toast thành công.
- Kiểm tra `tests/layout_ui.cjs` đảm bảo không bị lỗi layout hay tràn giao diện.
- Sửa lỗi tương thích cú pháp `cssstyle` trong jsdom và chuẩn hóa hiển thị `${provider} ${agent}`.
- Chạy toàn bộ 178 tests Python và toàn bộ test JavaScript: 100% PASS.

## Bước 7 — Cập nhật tài liệu (ĐÃ HOÀN THÀNH)
- `docs/ARCHITECTURE.md`: Thêm mục kiến trúc lưu trữ lịch sử phiên và transcript.
- `docs/WEB-APP.md`: Thêm hướng dẫn sử dụng chức năng Lịch sử & Resume trên web dashboard.
- `SECURITY.md`: Thêm mục bảo vệ dữ liệu nhạy cảm trong transcript, vị trí lưu trữ, cơ chế redact và hướng dẫn xóa dữ liệu.
