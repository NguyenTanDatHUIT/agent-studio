# 2026-11-19: Mất chữ khi gõ dấu (bộ gõ kiểu soạn thảo) và dán chuột phải bị 2 lần trong Claude

## Lỗi báo
1. Gõ tiếng Việt trong cửa sổ agy mất chữ ("Chào" thành "Cào").
2. Dán bằng chuột phải trong Claude bị dán 2 lần, agy thì không.
3. Cửa sổ Agent 0 đã chạy agy nhưng vẫn hiện tên và biểu tượng Claude (sửa trước đó trong ngày, `liveCli()` trong `app.js`).

## Bằng chứng đo được
- Phía máy chủ (`Session.write` vào agy thật qua ConPTY) ghi đúng "Chào"/"nhiều" với mọi khoảng cách 3 đến 30 ms. Chỉ khi dư một `\x7f` mới ra "Cào" (đã thử). Vậy lỗi nằm ở chuỗi byte của trình duyệt.
- Chromium + CDP (`Input.imeSetComposition`): với đoạn `compositionend` xóa `textarea.value` ngay (thêm ngày 10/11), bộ gõ kiểu soạn thảo ra `[]` (mất sạch chữ). Nguyên nhân: listener capture của app chạy trước `setTimeout(0)` của xterm nên xterm đọc textarea rỗng. Bỏ đoạn đó thì ra `["Chào","nhiều"]`.
- Bộ gõ kiểu Unikey (Backspace thật rồi chèn chữ) vẫn ra đúng số `\x7f`, không phải nguồn lỗi.
- Claude bật chế độ chuột `?1000/1002/1003/1006`, agy chỉ bật `?1004/2004`. Khi đó xterm gửi `ESC[<2;x;yM` cho nút phải; Claude coi là dán, cộng với lần dán của dashboard thành 2 lần. Chặn nút phải ở capture thì không còn byte nào gửi đi.

## Sửa (`web_assets/app.js`)
- Xóa textarea trễ 60 ms và chỉ khi không còn soạn thảo (cờ `e.composing`).
- Chặn `mousedown/mouseup/pointerdown/pointerup/auxclick` nút phải ở capture, không cho tới ứng dụng.

## Chưa làm / chưa chắc
- Chưa thử với bộ gõ thật của chủ máy. Nếu vẫn mất chữ: `localStorage.setItem('ao-term-debug','1')`, tải lại trang, gõ "Chào", gửi dòng `[term in]` trong Console.
- `tests/flow_ui.cjs`, `tests/layout_ui.cjs` chưa chạy (thiếu jsdom trên máy này).

## Cập nhật: nguyên nhân thật của mất chữ với Unikey (có log byte thật của chủ máy)
- Unikey KHÔNG dùng soạn thảo. Log `[term key]`/`[term in]`: trước mỗi lần thay chữ nó gửi một ký tự giả `·` (U+00B7, keyCode 231), rồi gửi Backspace nhiều hơn cần đúng 1 cái (3 cho "ao", 2 cho "e", 3 cho "êu"), rồi chữ thay thế.
- Agy không hiển thị `·` nên Backspace dư xóa nhầm chữ thật. Tái hiện bằng ConPTY: `Chao` + `·` + 3 BS + `ào` ra "Cào"; không có `·` và 2 BS ra "Chào".
- Sửa (`app.js`, `term.onData`): nuốt `·` do phím keyCode 231 sinh ra (trong 150 ms) và đúng một Backspace đi kèm (hết hạn 800 ms). Kiểm bằng Chromium + agy thật, giả lập đúng chuỗi phím của log: ra "Chào nhiều".
- Log gỡ lỗi mới (`ao-term-debug`): thêm `[term key]` (phím) và `[term ev]` (sự kiện textarea).
- Đoạn "xóa textarea trễ khi compositionend" ở trên vẫn giữ (sửa lỗi mất sạch chữ với bộ gõ kiểu soạn thảo), nhưng không phải nguyên nhân của lỗi Unikey.
