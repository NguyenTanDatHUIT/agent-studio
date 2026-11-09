# 2026-11-09: Mất chữ khi gõ có dấu trong agy và lag terminal

## Vấn đề
- Gõ "hà" ra "à", "thở" ra "ở" trong khung CMD của agy (bản sửa debounce 35ms trước đó chưa hết lỗi).
- Khung chat nhiều ký tự thì bị lag.

## Giả thuyết đã xử lý
Debounce 35ms gộp `Backspace + chữ có dấu` vào một lần ghi; agy đọc cả cụm trong một lần và coi là paste/escape nên nuốt chữ đứng trước.

## Thay đổi
- `app.js`: bỏ bộ đệm gom input, gửi từng gói `onData` ngay (giữ thứ tự qua `e.queue`). Có log byte thô: `localStorage.setItem('ao-term-debug','1')` rồi tải lại trang.
- `terminals.py` (`write`): tách mỗi Backspace/DEL thành lần `WriteFile` riêng, cách nhau 2ms.
- Giảm lag: thêm `vendor/addon-webgl.js` (@xterm/addon-webgl 0.18.0, khớp xterm 5.5.0), route trong `web.py`, thẻ script trong `index.html`; gom output theo `requestAnimationFrame` thành một lần `write`; `scrollback` 5000 -> 2000.

## Kiểm chứng
- `flow_ui.cjs`, `layout_ui.cjs`, `test_ui_rules`, `test_interactive_idle`, `test_idle_busy`: PASS.
- Chưa kiểm bằng agy thật và chưa chụp ảnh `ui_shots`; cần người dùng gõ thử "hà", "thở".

## Việc tiếp theo nếu vẫn lỗi
Bật log byte thô để xác định lỗi ở phía gửi hay phía vẽ; chuyển input/output sang WebSocket.

## Bổ sung: lệnh `/clear` (và mọi lệnh `/`) không còn báo "đã xong"
- Nguyên nhân: mọi input đều đặt trạng thái "đang làm việc" (server: `has_active_work`; trình duyệt: `awaitingResponse`), nên output của `/clear` bị coi là kết quả công việc.
- `terminals.py`: thêm `Session._submits_work`, phát lại phím gõ theo từng dòng; dòng bắt đầu bằng `/` (dùng `_is_slash_command`) không đặt `idle=False`, `idle_notified=False`, `has_active_work=True`.
- `app.js` (`term.onData`): cùng logic, lệnh `/` không bật `awaitingResponse`.
- Test mới: `test_slash_commands_do_not_arm_the_finished_notice` trong `tests/test_idle_busy.py`. Chưa thử bằng agy/claude thật.

## Bổ sung: chuột phải dán 2 lần
- `app.js`: thêm `e.pasteOnce(text)` cho mọi đường dán do app gọi (chuột phải, nút Dán, paste event ngoài textarea); bỏ qua cùng nội dung đến lần hai trong 500ms. Menu chuột phải thêm `stopPropagation` và cờ `pasteReading` chống chạy chồng.
- Chưa xác định chắc nguyên nhân gốc (chưa tái hiện trên trình duyệt thật); đây là chặn trùng ở phía app. Nếu vẫn dán 2 lần thì lần dán thứ hai đến từ đường nội bộ của xterm (Ctrl+V) và cần log thêm.
