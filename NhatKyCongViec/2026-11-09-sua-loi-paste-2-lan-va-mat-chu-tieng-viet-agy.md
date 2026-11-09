# Nhật ký 2026-11-09: Sửa lỗi dán 2 lần khi copy vào CMD và mất chữ/sai dấu tiếng Việt trong agy

## Vấn đề được báo cáo
Người dùng phản ánh 2 lỗi trong giao diện web Agent Studio (`agent-orchestrator`):
1. **Dán 2 lần (Double paste):** Khi copy nội dung và paste (Ctrl+V) vào cửa sổ CMD/terminal của web app, văn bản bị dán 2 lần liên tiếp.
2. **Mất chữ khi gõ tiếng Việt có dấu trong agy:** Khi gõ tiếng Việt có dấu (Unikey / EVKey theo kiểu Telex hoặc VNI) trong cửa sổ terminal của `agy` (Antigravity CLI), các chữ cái bị mất hoặc vị trí ký tự bị lệch. Ví dụ: gõ "nhớ" thì bị thành "nớ" và các ký tự gõ tiếp theo sau ký tự có dấu bị mất hoặc xáo trộn.

## Nguyên nhân gốc rễ (Root Cause)

### 1. Lỗi dán 2 lần (Double paste)
- **Vị trí:** `agent_orchestrator/web_assets/app.js` trong hàm khởi tạo terminal `create()`.
- **Cơ chế:**
  - `term.attachCustomKeyEventHandler` bắt phím `Ctrl+V` (hoặc `Shift+Insert`), gọi bất đồng bộ `navigator.clipboard.readText().then(text => term.paste(text))` rồi trả về `false`.
  - Việc trả về `false` cho phép trình duyệt tiếp tục lan truyền sự kiện phím tự nhiên tới phần tử trợ giúp bên trong của xterm (`<textarea class="xterm-helper-textarea">`).
  - xterm có sẵn bộ xử lý sự kiện DOM `paste` nội bộ (`handlePasteEvent`). Khi nhận sự kiện này, nó đọc đồng bộ `e.clipboardData.getData('text/plain')` và gọi `term.paste(text)` lần thứ nhất.
  - Ngay sau đó, Promise từ `navigator.clipboard.readText()` giải quyết xong và gọi `term.paste(text)` lần thứ hai -> gây ra hiện tượng nhân đôi văn bản mỗi lần paste.

### 2. Lỗi mất chữ khi gõ tiếng Việt trong agy ("nhớ" -> "nớ")
- **Nguyên nhân 1 - Console Code Page trên ConPTY Windows:**
  - Các tiến trình con chạy trong Windows Pseudo Console (ConPTY) mặc định thừa kế bảng mã OEM (OEMCP = 437 trên hệ thống Windows tiếng Anh / US).
  - Không giống như Claude Code (chạy trên Node.js có sẵn cơ chế tự gọi `SetConsoleCP(65001)`), các công cụ biên dịch nhị phân như `agy.exe` chạy với code page 437 của ConPTY.
  - Ở code page 437, các ký tự UTF-8 đa byte của tiếng Việt (ví dụ `ơ` là 2 byte `0xC6 0xA1`, `ớ` là 3 byte `0xE1 0xBB 0x9B`) bị ConPTY coi là nhiều ký tự đơn byte riêng biệt.
  - Khi bộ gõ Unikey / EVKey thực hiện thao tác bỏ dấu: nó phát phím Backspace (`\x08` / `\x7f`) để xóa nguyên âm cũ rồi điền nguyên âm có dấu mới vào. Do ConPTY hiểu là CP437, một phím Backspace chỉ xóa 1 byte thay vì nguyên 1 ký tự UTF-8, làm đứt đoạn chuỗi byte đa ký tự, vô tình xóa mất ký tự đứng trước (chữ 'h' trong "nhớ" biến thành "nớ", 'i' trong "nhiêu" thành "nhêu", 'b' trong "bằng" thành "ằng") và làm hỏng con trỏ cho các ký tự gõ tiếp theo.
- **Nguyên nhân 2 - Client Debounce Timer quá ngắn (10ms):**
  - Trong `app.js`, bộ đệm gom phím `term.onData` có `setTimeout(flush, 10)`.
  - Trên Windows, độ trễ giữa phím Backspace giả lập của Unikey và ký tự thay thế thường dao động trong khoảng 15ms - 35ms.
  - Timeout 10ms khiến phím Backspace bị gửi đi trước trong một request POST riêng biệt, khiến ConPTY và agy xử lý Backspace và vẽ lại màn hình trước khi ký tự thay thế tới, làm tăng nguy cơ lệch trạng thái con trỏ.

## Các thay đổi đã thực hiện

1. **`agent_orchestrator/web_assets/app.js`**:
   - Trong `term.attachCustomKeyEventHandler`: xóa bỏ hoàn toàn lệnh gọi trùng lặp `navigator.clipboard.readText()`. Khi người dùng bấm `Ctrl+V` hoặc `Shift+Insert` (nếu không ở chế độ readonly), hàm chỉ cần trả về `false` để xterm tự xử lý sự kiện `paste` từ clipboard một cách an toàn và duy nhất.
   - Thêm bộ lọc trong `el.addEventListener('paste')` của khung chứa terminal để bỏ qua các sự kiện paste xuất phát từ `xterm-helper-textarea` nhằm tránh sự kiện nổi bọt (bubbling).
   - Tăng `debounce` của bộ đệm đầu vào `inputBuffer` trong `term.onData` từ `10ms` lên `35ms` để gom trọn chuỗi Backspace + ký tự có dấu do Unikey/EVKey phát ra trong cùng một gói dữ liệu.

2. **`agent_orchestrator/terminals.py`**:
   - Trong `base_env()`: bổ sung biến môi trường chuẩn UTF-8 `LANG='en_US.UTF-8'` và `LC_ALL='en_US.UTF-8'` bên cạnh `PYTHONIOENCODING` và `PYTHONUTF8`.
   - Trong `open()`: khi khởi chạy các công cụ CLI độc lập (`agy`, `codex`) trên Windows trong ConPTY, bọc lệnh khởi tạo qua:
     `cmd.exe /d /c chcp 65001 >nul && <command>`
     Lệnh này ép ConPTY buffer chuyển sang code page 65001 (UTF-8) ngay khi khởi động.

## Kiểm chứng (Verification)
- Kiểm tra qua script ConPTY thật (`test_wrapped_agy.py`):
  - Khởi động `agy.exe` thật với ConPTY có bọc `chcp 65001`.
  - Gõ các chuỗi Telex có phím xóa dấu: `['n', 'h', 'o', '\x7f', 'ơ', '\x7f', 'ớ', ' ', 'b', 'a', 'n']`.
  - Kết quả hiển thị: xuất hiện nguyên vẹn `"nhớ ban"`, không mất ký tự 'h', không lệch con trỏ, không rơi chữ sau dấu.
- Bộ test tự động:
  - `tests.test_interactive_idle` và `tests.test_history`: 71/71 tests PASS (31.85s).
  - Toàn bộ suite `unittest discover -s tests -p "test_*.py"`: PASS không có hồi quy.

---

## Bổ sung: Nâng cấp tab "Luồng tự động" hiển thị đúng Agent tương tác đang mở (không hardcode Codex)
- **Vấn đề**: Người dùng mở tab "Luồng tự động" thấy xuất hiện `Codex Worker` và sơ đồ cố định không khớp với các agent thực tế đang chạy (`Agent 0`, `Agent 2 · Claude`, `Agent 3 · Claude`).
- **Nguyên nhân**: Khi hàng đợi nhiệm vụ không có task (`relevantTasks.length === 0`), `renderFlow()` tự động lấy danh sách `['claude', 'codex']` từ config và vẽ lane tĩnh cho Codex dù không có agent hay task Codex nào.
- **Đã sửa**:
  - Khi không có task trong queue: kiểm tra các terminal agent tương tác đang sống (`liveAgents = state.sessions.filter(s => s.kind === 'agent' && s.alive)`).
  - Nếu có agent tương tác: vẽ các lane tương ứng với chính các agent đang mở (`Agent 2 · Claude`, `Agent 3 · Claude`, `agy`...), nối từ `Agent 0` qua các agent, kèm trạng thái đang chạy / sẵn sàng thật.
  - Bấm vào node agent trên sơ đồ sẽ tự động chuyển sang tab "Cửa sổ CMD" và focus đúng terminal đó.
  - Loại bỏ hoàn toàn việc hardcode lane `Codex Worker` khi không có agent hay runner Codex hoạt động.
