# 2026-11-12: Thêm provider `gemini_web` (cầu nối tab Gemini qua tiện ích trình duyệt)

Nguồn: `h_ng_d_n_t_ch_h_p_gemini_web_v_o_agent_studio.md` (tải về). Tài liệu viết theo giả định về mã, nên đối chiếu với mã thật trước khi áp dụng.

## Đã làm

- Mới: `agent_orchestrator/gemini_bridge.py` (WorkspaceExecutor, BrowserBridgeSession, GeminiBridgeHub, run_worktree_via_bridge), `browser_extension/` (5 tệp), `tests/test_gemini_bridge.py` (6 test), `docs/GEMINI-WEB.md`.
- Sửa: `config.py` (xác thực khối `gemini_web`, `provider_enabled`), `providers.py` (usage), `readiness.py`, `runners.py`, `engine.py` (enqueue, workflow, `_execute` rẽ nhánh sang cầu nối), `mcp.py` (chỉ thêm enum, vẫn 19 tool), `cli.py`, `terminals.py` (TERMINAL_AGENTS, `open`, `managed_idle`), `web.py` (cổng `/api/gemini-bridge/*`, CORS cho tiện ích, status/toggle), giao diện (nút Gemini, hộp thoại ghép đôi, logo, nhãn).

## Khác với tài liệu gốc (vì mã thật khác)

- `Terminals.open` không có `window_title`, `_info`, `_idle_monitor`, `notify_session_idle`. Dùng `describe()`, và `update_interactive_idle` trả sớm khi `managed_idle`.
- `enabled` phải là `true` rõ ràng (tài liệu mặc định `true` khi có khối).
- `usage()` của gemini_web trả `terminal_seen` theo sự kiện `turn.completed`; nếu để `False` như tài liệu, `Engine._execute` sẽ luôn báo "missing terminal result".
- Bổ sung: `POST /jobs` chỉ nhận worktree trong `<state>/worktrees` và bắt buộc `allow_paths`.
- `/api/config` đổi sang `provider_enabled`, không ảnh hưởng fixture cũ.

## Kiểm chứng

- `tests.test_gemini_bridge`, `tests.test_ui_rules`, `tests.test_web`: đạt.
- `tools/ui_shots.cjs` (Chrome cài sẵn, `CHROME_PATH`): đạt cả 4 tổ hợp rộng/hẹp, tối/sáng. Đã xem ảnh hộp thoại cầu nối ở hai cỡ.
- Chưa chạy: `tests/flow_ui.cjs`, `layout_ui.cjs` (máy chưa có jsdom). Chưa thử với tab Gemini thật; bộ chọn DOM trong `content_gemini.js` là phỏng đoán từ tài liệu.

## Còn lại

- Thử thật với tab Gemini đã đăng nhập, chỉnh bộ chọn nếu cần.
- Chưa commit. Không push, không merge vào main.
