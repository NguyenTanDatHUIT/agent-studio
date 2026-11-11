# 10/11/2026 — Sửa thông báo `[AO] ... đã xong` báo sớm và bị miss

Nguồn: `logs/ao-thong-bao-sai.md` (agy-1, agy-3, agy-4, agy-6, agy-7). Người dùng thấy: có terminal bị báo sớm, rồi khi xong thật thì không có thông báo; nhiều cửa sổ thì miss nhiều hơn.

## Nguyên nhân (đọc mã `agent_orchestrator/terminals.py`)
1. `idle` và `idle_notified` bị "dính": đã True thì không có gì đặt lại khi agent tự chạy tiếp (build xong, subagent về). Báo sớm một lần là mất lần báo đúng.
2. `BUSY_MARKER` chỉ biết kiểu Claude (`Running (...)`); agy dùng `Working...`, `Editing files...`, `Spawned N subagents`, `... running`, footer `N task(s)`.
3. `is_terminal_spinning` chỉ xét dòng cuối luồng byte, không có trần thời gian: dòng spinner cũ làm terminal (agy-1) không bao giờ được coi là yên.
4. Nhiều terminal: một terminal ném lỗi làm vòng `notify_agent0` bỏ qua các terminal sau; mỗi tick sao chép cả buffer của mọi terminal trong lúc giữ khóa `cond`.

## Đã sửa
- `update_interactive_idle`: ghi `idle_offset`; terminal idle mà có thêm >= 200 byte output kèm dấu hiệu bận/spinner thì đặt lại `idle=False`, `idle_notified=False`.
- Thêm `SOFT_BUSY_MARKER` / `SOFT_DONE_MARKER` (`HOÀN TẤT:`, `ĐANG CHỜ AGENT 0`), `terminal_busy_kind`, `SOFT_BUSY_CAP = 180`, `SPINNER_QUIET_CAP = 30`.
- `describe()` trả thêm `idle_reason` (debounce / spinner / busy-marker / busy-soft / quiet / resumed).
- `notify_agent0`: bọc từng terminal trong try/except; chỉ sao chép đuôi 12 KB buffer.
- Test mới `tests/test_idle_rearm.py` (6 test). `tests/test_interactive_idle.py` dòng 107: đổi output giả `Working...` thành `Analysis summary written` vì `Working...` giờ là dấu hiệu bận của agy.

## Chưa làm
- Chưa đổi câu chữ thông báo thành "yên lặng, chưa xác nhận xong" và chưa thêm đuôi "thông báo tự động" (test hiện so khớp nguyên văn).
- Chưa có tín hiệu "xong" dựa trên commit + báo cáo, gồm nhiều worktree (`docs/TINH-NANG-QUY-TAC-DIEU-PHOI-AGENT.md` mục 6.5).
- Rủi ro: agy để lại `Working...` sau khi xong mà không in `HOÀN TẤT:` thì thông báo trễ tối đa 180 giây.
- Chưa commit.

## Ghi chú
Lúc sửa regex tôi lỡ xóa ký tự Backspace thật ở regex tách Backspace/DEL (`pieces = ... re.split(...)`, dòng ~396); đã khôi phục giống bản gốc (`git diff` không còn thay đổi ở dòng đó). Lần sau không thay ký tự điều khiển hàng loạt bằng script.

## Kiểm thử
- `test_idle_rearm`, `test_idle_busy`, `test_interactive_idle`: 28/28 đạt. `test_history` chạy riêng: 65/65 đạt.
- Bộ đầy đủ: 286 test, 285 đạt, 1 lỗi timeout ở `test_history...test_new_chat_closes_windows_keeps_history_restarts_numbers_and_reopens_agent0` (lúc đạt lúc fail khi chạy riêng, khoảng 1/3 số lần).
- Dump stack lúc treo: request `/api/chat/new` kẹt ở `Session.close` -> `CloseHandle(self.output)` (`terminals.py` ~429) trong khi thread `pump` đang chặn ở `ReadFile` trên chính handle đó. Đoạn này có từ commit `0a7cb97b`, không nằm trong phần sửa idle; chưa sửa (ngoài phạm vi).
