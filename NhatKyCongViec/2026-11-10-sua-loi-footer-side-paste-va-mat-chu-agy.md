# Nhật ký 2026-11-10: Sửa lỗi giao diện footer / `.ao-side`, dán 2 lần khi chuột phải, và mất ký tự khi gõ trong CMD `agy`

## 1. Bối cảnh & Yêu cầu
Người dùng báo 3 lỗi kèm ảnh chụp màn hình thực tế (`1024×503`, chế độ thu gọn sidebar, 3 cửa sổ CMD):
1. **Lỗi giao diện ở footer & `.ao-side` bị mất phần dưới**: Khi chiều cao nội dung của `#ao-studio` vượt quá `100vh` (ví dụ trên trang Cửa sổ CMD khi lưới terminal cộng với 3 hàng chân trang `.ao-terminal-foot`, `.ao-console-hint`, `.ao-footer` cao hơn chiều cao cửa sổ trình duyệt, hoặc trên màn hình thấp), cột sidebar bên trái (`.ao-side`) bị cụt ở mốc `100vh`, làm mất nền `--ao-side` và đường viền `border-right` ở phần đáy cạnh footer; đồng thời khi mở rộng sidebar trên màn hình thấp thì khối `.ao-side-bottom` bị cắt khuất.
2. **Chuột phải paste bị dán 2 lần**: Khi nhấp chuột phải vào cửa sổ terminal để dán văn bản từ clipboard, nội dung bị gửi 2 lần vào phiên làm việc.
3. **CMD của `agy` gõ chữ bị mất ký tự**: Đã xử lý nhiều lần trước đó nhưng vẫn bị nuốt chữ hoặc lặp chữ khi gõ tiếng Việt (Unikey/EVKey/Windows IME) hoặc khi sửa ký tự.

---

## 2. Nguyên nhân gốc & Giải pháp

### 2.1. Lỗi giao diện ở footer và `.ao-side` bị mất phần dưới
- **Nguyên nhân gốc**:
  - Trong `agent_orchestrator/web_assets/style.css` (dòng 2 và dòng 90): `#ao-studio` đặt `overflow:hidden`, còn `#ao-studio .ao-side` bị ép cứng `position:sticky;top:0;height:100vh`. Khi tổng chiều cao của `.ao-shell` lớn hơn `100vh`, `.ao-side` chỉ cao đúng `100vh` nên phần dưới của cột bên trái (ngang hàng với `.ao-terminal-foot`, `.ao-console-hint`, `.ao-footer`) bị trống nền và mất đường kẻ dọc `border-right`.
  - Ở chế độ `.ao-console-compact`, khoảng đệm dọc của `.ao-main`, `.ao-terminal-foot`, `.ao-console-hint`, `.ao-footer` và công thức `--term-h: clamp(340px, calc((100vh - 210px) / var(--console-rows, 2)), 760px)` trừ thiếu chiều cao phần khung trên/dưới (~230px), đẩy phần footer tràn xuống dưới.
- **Cách sửa (`agent_orchestrator/web_assets/style.css`)**:
  - Đổi `#ao-studio .ao-side` sang `min-height:100vh;height:auto;align-self:stretch` (và thêm `min-height:0` trong `@media(max-width:620px)` để không làm cao thanh điều hướng trên màn hình hẹp), đồng thời đặt `overflow-x:clip;overflow-y:visible` cho `#ao-studio`. Nhờ đó `.ao-side` luôn giãn hết chiều cao thực tế của `.ao-shell` và giữ nguyên khối `.ao-side-bottom` ở đáy.
  - Thu gọn khoảng cách dọc trong `#ao-studio.ao-console-compact` (`.ao-main`, `.ao-console-bar`, `.ao-terminal-foot`, `.ao-console-hint`, `.ao-footer`) và cập nhật `--term-h: clamp(300px, calc((100vh - 230px) / var(--console-rows, 2)), 760px)`.

### 2.2. Lỗi chuột phải paste bị dán 2 lần
- **Nguyên nhân gốc**:
  - Trong `vendor/xterm.js`, xterm tự đăng ký listener `contextmenu` (`rightClickHandler`, dịch chuyển `this.textarea` tới dưới con trỏ chuột) và listener `paste` (`handlePasteEvent` trên cả `this.textarea` lẫn `this.element`, gọi thẳng `this.coreService.triggerDataEvent(text, true)` mà không đi qua `e.pasteOnce`).
  - Trong `agent_orchestrator/web_assets/app.js`, cả hai listener `paste` và `contextmenu` trên `el` trước đây được đăng ký ở **bubble phase** (mặc định `false`). Khi người dùng chuột phải hoặc dán, handler nội bộ của xterm trên `textarea` chạy trước hoặc chạy song song với handler của `app.js`, dẫn tới văn bản được gửi 2 lần (1 lần qua xterm, 1 lần qua `e.pasteOnce`).
- **Cách sửa (`agent_orchestrator/web_assets/app.js`)**:
  - Chuyển cả hai listener `el.addEventListener('paste', ..., true)` và `el.addEventListener('contextmenu', ..., true)` sang **capture phase (`true`)** kèm `ev.preventDefault(); ev.stopPropagation(); ev.stopImmediatePropagation();`, chặn hoàn toàn `handlePasteEvent` và `rightClickHandler` nội bộ của xterm trước khi sự kiện chạm tới `.xterm-helper-textarea`.

### 2.3. Lỗi gõ chữ trong CMD `agy` bị mất ký tự
- **Nguyên nhân gốc** (xác định qua kiểm tra mã nguồn `charmbracelet/ultraviolet` bên trong `agy.EXE`, `vendor/xterm.js` và `agent_orchestrator/terminals.py`):
  1. **Chu kỳ đọc Console Input 10ms của `agy.EXE` (`terminal_reader_windows.go`)**:
     `agy.EXE` dùng `charmbracelet/ultraviolet` đọc `STD_INPUT_HANDLE` trên Windows bằng vòng lặp `peekNConsoleInputs` có `time.Sleep(10 * time.Millisecond)` (10ms). Trong khi đó, `Session.write` ở `terminals.py` chỉ nghỉ `time.sleep(0.002)` (2ms) khi tách `\x7f` trong cùng một lệnh `write`, và **không hề có khoảng nghỉ** giữa hai HTTP request `/input` liên tiếp (khi trình duyệt gửi `\x7f` ở request #1 và ký tự thay thế ở request #2 cách nhau 1–3ms trên localhost). Hệ quả là Backspace (`\x7f`) và ký tự thay thế rơi vào cùng một chu kỳ 10ms của `PeekConsoleInputW`.
  2. **Mã `\x08` (ASCII Backspace) qua Windows ConPTY**:
     Trong `charmbracelet/ultraviolet` (`decoder.go`: `parseWin32InputKeyEvent`), ConPTY dịch byte `\x08` thành tổ hợp `Ctrl+Backspace` (trong khi `\x7f` mới là `Backspace` đơn). Trong `agy.EXE`, `Ctrl+Backspace` là lệnh **xóa cả từ đứng trước (`delete_word_backward`)**, làm bay mất cả từ khi bộ gõ gửi `\x08`.
  3. **Trạng thái `textarea.value` của `xterm.js` sau khi kết thúc IME composition (`CompositionHelper`)**:
     Trong `vendor/xterm.js`, `_finalizeComposition` giữ nguyên chuỗi vừa gõ trong `this._textarea.value`. Đến nhịp gõ dấu tiếp theo (`keyCode === 229`), hàm `_handleAnyTextareaChanges` so sánh độ dài `t.length < e.length` và tự phát mã `DEL (\x7f)` xóa mất ký tự vừa gõ, hoặc gửi chồng ký tự mới mà không xóa ký tự cũ.
  4. **Chuỗi báo cáo focus `\x1b[I` / `\x1b[O`**:
     Khi cửa sổ popup của bộ gõ / chuột làm đổi focus, xterm phát `\x1b[I` / `\x1b[O` xen vào luồng phím đang gõ.
- **Cách sửa**:
  - Trong `agent_orchestrator/terminals.py` (`Session.write`):
    - Chuẩn hóa `NFC` và đổi mọi `\x08` thành `\x7f` trước khi ghi vào ConPTY để không bao giờ kích hoạt `Ctrl+Backspace` (xóa cả từ) trong `agy.EXE`.
    - Lưu mốc thời gian `self._last_write_t` và cờ `self._last_write_bs` trên từng `Session` (bên trong `with self.lock:`). Bất kỳ mảnh dữ liệu nào là `\x7f` hoặc nối tiếp ngay sau `\x7f` (dù nằm trong cùng một lần gọi `write()` hay ở hai HTTP request `/input` liên tiếp) đều được đảm bảo cách nhau tối thiểu **15ms (`0.015s`)**, lớn hơn chu kỳ poll 10ms của `ultraviolet` trong `agy.EXE`.
  - Trong `agent_orchestrator/web_assets/app.js` (`attachTerm`):
    - Không gộp (batch) nhiều lần `onData` trên client; gửi tuần tự từng sự kiện qua `e.queue` sau khi lọc bỏ chuỗi báo focus `\x1b[I` / `\x1b[O`.
    - Thêm capture listener `compositionend` trên `el` để xóa sạch `term.textarea.value = ''` ngay sau mỗi nhịp ghép chữ của IME, ngăn `CompositionHelper` của xterm so sánh độ dài sai ở ký tự tiếp theo.

---

## 3. Kiểm tra & Nghiệm thu
- **Kiểm tra giao diện thật bằng Chromium (`tools/ui_shots.cjs` & `verify_fixes.cjs`)**:
  - Chạy `node tools/ui_shots.cjs`: đạt toàn bộ kiểm tra ở cả 4 chế độ (`wide-dark`, `wide-light`, `narrow-dark`, `narrow-light`).
  - Chụp và kiểm tra trực tiếp ở độ phân giải `1024×503` (giống hệt ảnh lỗi của người dùng, 3 cửa sổ CMD, thu gọn sidebar): `studioH = 540`, `sideH = 540` — cột `.ao-side` phủ kín từ đỉnh xuống tận đáy trang cạnh `.ao-footer`, không còn bị mất góc dưới bên trái; 3 dòng thông tin ở footer hiển thị gọn gàng.
- **Kiểm tra chuột phải paste & Ctrl+V paste trên Chromium**:
  - Nhấp chuột phải vào `.ao-term-el` và phát sự kiện `ClipboardEvent('paste')` vào `.xterm-helper-textarea`: cả hai trường hợp đều chỉ gửi đúng **1 request** `/api/terminals/agy-1/input` duy nhất.
- **Kiểm tra gõ tiếng Việt thực tế vào `agy.EXE` qua ConPTY (`Session.write`)**:
  - Khởi chạy `agy.EXE` thật trong `Session` ConPTY, gửi chuỗi gõ Telex có cả `\x7f` rời, `\x7f` dính liền ký tự thay thế và `\x08` (`giao cho agy một task nhỏ bất kỳ`): dòng nhắc của `agy.EXE` nhận chính xác `> giao cho agy một task nhỏ bất kỳ`, không mất hay lặp bất kỳ ký tự nào.
- **Bộ test tự động**:
  - `node tests/layout_ui.cjs` & `node tests/flow_ui.cjs`: **PASS**.
  - `.\.runtime\python\python.exe -m unittest tests.test_ui_rules tests.test_interactive_idle tests.test_idle_busy`: **Ran 30 tests — OK**.

