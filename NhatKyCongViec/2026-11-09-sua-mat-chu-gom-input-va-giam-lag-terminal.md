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
