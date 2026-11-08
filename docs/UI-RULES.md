# Quy tắc giao diện (bắt buộc cho mọi thay đổi UI)

Áp dụng cho `agent_orchestrator/web_assets/` (`style.css`, `app.js`, `index.html`). Có test cưỡng chế: `tests/test_ui_rules.py`.

## 1. Mọi ô nhập liệu phải theo template, không dùng kiểu mặc định của trình duyệt

Áp dụng cho **mọi** `input`, `select`, `textarea` (hiện có và sẽ thêm sau này).

- Kiểu dáng đến từ **một khối chung** trong `style.css` ("QUY TẮC FORM CONTROL"), dùng token của template:
  `--ao-text`, `--ao-panel`, `--ao-line`, `--ao-accent`, `--ao-muted`, `--ao-red`. Không viết màu cứng.
- Khối chung dùng `:where()` nên độ ưu tiên bằng 0. Thành phần riêng chỉ nên **bố cục** ô nhập (`width`, `flex`, `min-width`, `margin`),
  không khai báo lại viền, nền, màu chữ, bo góc, padding. Muốn đổi giao diện của mọi ô nhập, sửa khối chung.
- `select`: mũi tên tự vẽ (`appearance:none` + biểu tượng). Với `select` **không dùng** `background:` rút gọn; nếu cần đổi nền thì `background-color`.
  (Rút gọn sẽ xóa mũi tên. Khối chung có `!important` cho phần ảnh mũi tên để phòng trường hợp quên.)
- **Danh sách bật ra của `select`** cũng phải theo template: `app.js` (`openSelectMenu`) thay menu gốc của hệ điều hành bằng menu `.ao-select-menu` dùng token `--ao-*`, nhưng vẫn giữ `<select>` thật (giá trị, `change`, kiểm tra hợp lệ, bố cục). Vì vậy `select` mới không cần mã thêm; chỉ cần nằm trong `#ao-studio`. Đừng thay bằng thư viện hoặc `select` tự chế khác. Không dùng `multiple` hoặc `size>1` nếu chưa làm menu tương ứng (hai trường hợp đó vẫn là danh sách gốc).
- `checkbox`, `radio`: dùng `accent-color: var(--ao-accent)`.
- Trạng thái bắt buộc có: placeholder (màu `--ao-muted`), hover, focus-visible (viền `--ao-accent`), disabled (mờ, con trỏ cấm), lỗi (`aria-invalid="true"` viền `--ao-red`).
- Không dùng `style="..."` trực tiếp trên `input`, `select`, `textarea` trong `index.html` hoặc chuỗi mẫu trong `app.js`.
- Ngoại lệ đã được duyệt (có comment trong CSS): `.ao-command-input` (dòng nhắc lệnh trong terminal, không viền) và `.ao-layout-input` (ô "hàng x cột" cùng cỡ với nút bố cục).
  Muốn thêm ngoại lệ phải ghi vào đây và vào `allowed` trong `tests/test_ui_rules.py`.

## 2. Dữ liệu hiển thị phải dùng đúng tên trường của API

Giao diện từng đọc `created_at`, `agent_number`, `terminal_id` trong khi API trả `started`, `agent_n`, `terminal_key`, nên cột giờ trống và nhóm ngày là "Khác",
trong khi test vẫn xanh vì dữ liệu giả cũng dùng tên sai. Vì vậy:

- Dữ liệu giả trong `tests/flow_ui.cjs` phải sao chép đúng tên trường mà backend trả (đối chiếu `store.py` và `web.py`).
- Khi đổi tên trường ở backend, sửa JS và dữ liệu giả cùng lúc.
- Trạng thái "đang mở" lấy từ `live` do backend tính (terminal thực sự còn sống), không suy ra từ cột `status` trong DB (có thể còn sót `active` sau khi server tắt).

## 2b. Một id terminal có thể được dùng lại cho tiến trình mới

"Mở lại" phiên Agent 0 hoặc agent tạo tiến trình mới nhưng giữ id cũ (`agent0`, `claude-1`). Giao diện giữ một xterm cho mỗi id, nên nếu chỉ so id thì nội dung cũ và con trỏ đọc cũ bị trộn với phiên mới (banner lặp, chữ vỡ). Mọi cửa sổ terminal phải so cả `gen` (thời điểm tạo phiên, do `describe()` trả về) và dựng lại khi `gen` đổi.

## 3. Phải nhìn giao diện thật trước khi báo xong

Test jsdom không dàn trang nên không bắt được lỗi tràn ngang, nút bị cắt, chữ chồng nhau. Với thay đổi UI:

1. Chụp ảnh bằng `node tools/ui_shots.cjs <thư-mục-ra>` ở hai cỡ: rộng (1280) và hẹp (460).
2. Xem ảnh. Kiểm tra: không có thanh cuộn ngang, nút hành động hiện đủ, chữ dài được cắt bằng dấu ba chấm, menu không lệch dòng, chế độ tối và sáng đều đọc được.
3. Script cũng in `scrollWidth/clientWidth` của danh sách lịch sử; hai số phải bằng nhau.

## 4. Chữ do người dùng/terminal sinh ra phải được làm sạch

Tiêu đề, đường dẫn, nội dung transcript hiển thị qua `esc()` (không `innerHTML` trực tiếp). Tiêu đề phiên lấy từ phím người dùng gõ phải
được phát lại như trên màn hình (bỏ chuỗi điều khiển, xử lý Backspace của bộ gõ tiếng Việt): xem `title_from_keys()` trong `transcripts.py`.
