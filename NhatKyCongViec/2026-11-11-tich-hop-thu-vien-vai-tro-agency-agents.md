# 2026-11-11: Chuẩn hóa & tích hợp thư viện vai trò chuyên môn (Mức 2) từ Agency Agents

## Mục tiêu & quyết định thiết kế
- Chắt lọc phần tinh hoa thực sự hữu ích của `agency-agents` (kỷ luật viết mã theo chuyên ngành, cổng chặn nghiệm thu thực chất chống duyệt ảo, và khung bàn giao ngữ cảnh khi sửa/đổi cửa sổ) thành một gói chuẩn hóa, tinh gọn, trung lập dự án bên trong `agent_orchestrator/roles/`.
- Không bê nguyên 197 persona dài dòng hay quyền giả định (`full access`, merge/deploy) để tránh phình ngữ cảnh và xung đột với mô hình bảo mật của Agent Studio (`allow_paths`, `AGENT0_DENIED`, không tự merge/push).
- Tích hợp trọn vẹn cho cả **2 luồng điều phối** (Mức 2):
  1. **Worker hàng đợi** (`claude`, `codex` chạy trong worktree cô lập với `--restricted` / `--ignore-rules`): công cụ nhúng trực tiếp nội dung vai trò vào `Engine.worker_prompt` khi task hoặc bước workflow có `role`.
  2. **Agent tương tác CMD** (`agy`, `claude`, `codex`): công cụ tự đồng bộ thư viện ra `{ROLES_DIR}` (`<prompts_dir>/roles/`, nằm ngoài repo) để Agent 0 và các cửa sổ CMD đọc trực tiếp theo đường dẫn tệp.

## Đã làm
- `agent_orchestrator/roles/` (mới) & `pyproject.toml`:
  - `__init__.py`: định nghĩa 7 vai trò chuyên môn (`minimal-change`, `backend-architect`, `database-optimizer`, `frontend-ui`, `code-reviewer`, `reality-checker`, `security-auditor`), 3 khung mẫu bàn giao (`prompt-task`, `prompt-fix`, `escalation-handoff`), bảng điều hướng `INDEX.md`, hàm kiểm tra tên vai trò, ghép prompt worker và đồng bộ idempotent ra thư mục ngoài repo (giữ nguyên tệp riêng của chủ máy).
  - 11 tệp Markdown chuẩn hóa trong `roles/INDEX.md`, `roles/coding/*.md`, `roles/review/*.md`, `roles/templates/*.md`; khai báo `package-data` trong `pyproject.toml`.
- `agent_orchestrator/rules.py`:
  - Thêm công tắc `roles_enabled` (mặc định `True`) và biến `{ROLES_DIR}`.
  - Khi bật, `render()` bổ sung mục `### Thư viện vai trò & mẫu chuẩn` cho Agent 0 và `write_generated()` tự đồng bộ tệp ra `<prompts_dir>/roles/`.
- `agent_orchestrator/engine.py`, `mcp.py`, `cli.py`, `examples/AGENT0-PROMPT.md`:
  - `Engine.enqueue`, `continue_task`, `plan`, `release_step`, `workflow` và `worker_prompt` hỗ trợ trường `role` (giữ nguyên vai trò qua các vòng tiếp diễn nếu không ghi đè).
  - MCP `enqueue_task` thêm enum `role`, `enqueue_plan` hỗ trợ `role` trên từng bước, `get_orchestration_rules` trả kèm `roles_dir` và danh mục `roles`.
  - CLI `enqueue` thêm cờ `--role`.
  - Cập nhật `examples/AGENT0-PROMPT.md` hướng dẫn Agent 0 chọn `role` và `{ROLES_DIR}`.
- `agent_orchestrator/web.py` & `web_assets/` (`index.html`, `app.js`, `style.css`):
  - `GET /api/config` trả danh sách `roles` (đảm bảo không chứa chuỗi nhạy cảm `command`); `POST /api/tasks` nhận `role`; `/api/orchestration-rules` đồng bộ và trả danh mục `roles` kèm nội dung để xem trực tiếp.
  - Biểu mẫu **Tạo nhiệm vụ** có ô chọn `Vai trò chuyên môn (tùy chọn)`, bảng nhiệm vụ, chi tiết nhiệm vụ và bước workflow hiển thị vai trò.
  - Hộp thoại **Quy tắc điều phối agent** có công tắc bật/tắt thư viện vai trò và mục **Thư viện vai trò & mẫu chuẩn** cho phép chọn xem nội dung từng vai trò/mẫu ngay trong Cài đặt; tuân thủ nghiêm `docs/UI-RULES.md`.
- Kiểm thử & Tài liệu:
  - Tạo mới `tests/test_roles.py` (kiểm danh mục, tính trung lập dự án, an toàn đường dẫn, đồng bộ idempotent, nhúng `worker_prompt` qua nhiều vòng, workflow `plan`, MCP, CLI, Web API).
  - Mở rộng `tests/test_rules.py`, `tests/rules_ui.cjs` và `tools/ui_shots.cjs`.
  - Cập nhật đặc tả `[v4]` trong `docs/TINH-NANG-QUY-TAC-DIEU-PHOI-AGENT.md` (bảng tham số 4.1, biến `{ROLES_DIR}`, mục 4.8, lưu ý tương thích với `PROMPT-CHUNG.md`/sổ vòng nghiệm thu và tiêu chí kiểm thử mục 10) để các phiên làm tiếp Pha 2/Pha 3 giữ tương thích đầy đủ.

## Kiểm chứng
- Python tests: `test_ui_rules`, `test_roles`, `test_rules`, `test_web`, `test_workflow` pass.
- JS DOM tests (`jsdom`): `tests/layout_ui.cjs`, `tests/rules_ui.cjs`, `tests/flow_ui.cjs` pass.
- Ảnh chụp trình duyệt thật (`tools/ui_shots.cjs` bằng Chromium ở `1280x820` và `460x820`, cả chế độ `dark` và `light`): đã kiểm tra trực tiếp bằng mắt ảnh biểu mẫu tạo nhiệm vụ và hộp thoại quy tắc điều phối; không tràn ngang, toàn bộ 19 điều khiển form tuân theo token giao diện.
