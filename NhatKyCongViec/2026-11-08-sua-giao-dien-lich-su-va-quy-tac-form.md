# Nhật ký 2026-11-08: sửa giao diện Lịch sử, quy tắc form control

Nguồn: hai ảnh chụp màn hình của người dùng (menu cài đặt bố cục và hộp thoại Lịch sử bị loạn) và yêu cầu "mọi input/select dùng CSS theo template, thêm quy tắc đó".

## Lỗi tìm thấy qua ảnh chụp và nguyên nhân gốc
| Hiện tượng | Nguyên nhân | Sửa |
|---|---|---|
| Cột giờ hiện "—", nhóm ngày là "KHÁC" | JS đọc `created_at`, `updated_at`; API trả `started`, `last_active`. Test UI không bắt được vì dữ liệu giả dùng đúng tên sai. | JS đọc đúng tên trường; dữ liệu giả của `flow_ui.cjs` đổi sang tên thật; thêm assertion về giờ và nhóm ngày. |
| Huy hiệu agent, "Đang mở" sai | JS đọc `agent_number`, `terminal_id`; API trả `agent_n`, `terminal_key`. Trạng thái `active` còn sót trong DB sau khi server tắt làm phiên đã đóng bị khóa nút "Mở lại/Xóa". | Backend thêm `live` (terminal thật sự còn sống) và sửa `status` sót thành `closed` khi trả API. JS dùng `live`. |
| Tiêu đề rác (`[O[O[Igiao cho tcho agy moôột…`) | Tiêu đề lấy nguyên chuỗi phím: có báo cáo focus của xterm (`ESC[I`, `ESC[O`) và các lần sửa Backspace của bộ gõ tiếng Việt. | `title_from_keys()` phát lại phím như trên màn hình (bỏ chuỗi điều khiển, xử lý DEL/Backspace). Tiêu đề cũ trong DB được làm sạch khi đọc (`clean_title`). |
| Hộp thoại tràn ngang, nút "Xem lại/Xóa" bị cắt | `.ao-history-list` là grid một cột không có `minmax(0,1fr)`, hàng nới theo nội dung dài. | `grid-template-columns:minmax(0,1fr)`; màn hình hẹp chuyển hàng sang 3 dòng rõ ràng. |
| Menu cài đặt: "Lịch sử" và "Làm mới log" lệch dòng | Vùng nút phụ là `flex` nằm ngang trong menu dọc. | Xếp dọc bằng grid, nút full-width. |
| Select mất mũi tên, ô nhập mỗi chỗ một kiểu | Nhiều rule riêng (`.ao-field`, `.ao-filter`, `.ao-window-dialog select`, ô tìm kiếm lịch sử) tự đặt viền, nền, bo góc, và dùng `background:` rút gọn làm mất mũi tên. | Khối chung "QUY TẮC FORM CONTROL"; gỡ phần khai báo trùng ở các rule riêng. |

## Quy tắc thêm vào repo
- `docs/UI-RULES.md`: 4 quy tắc (form control theo template, dùng đúng tên trường API, phải xem giao diện thật ở hai cỡ, làm sạch chữ do người dùng/terminal sinh ra).
- `CLAUDE.md` (mới): trỏ agent làm việc trong repo tới quy tắc trên.
- `tests/test_ui_rules.py`: cưỡng chế tự động. Đã thử cố ý thêm `select{background:#fff}` vào CSS: test báo lỗi.
- `tools/ui_shots.cjs`: chụp màn hình thật (Chromium) ở 2 cỡ x 2 chế độ sáng/tối, báo nếu có tràn ngang, lỗi JS hoặc ô nhập còn dáng mặc định.

## Quyết định tự đưa ra
- Ngoại lệ có chủ đích: `.ao-command-input` (dòng nhắc trong terminal, không viền) và `.ao-layout-input` (ô "hàng x cột" phải cùng cỡ 32px/bo 6px với các nút bố cục). Ghi trong `docs/UI-RULES.md` và `allowed` của test.
- Khối chung dùng `:where()` (độ ưu tiên 0) để không phá rule của từng thành phần; riêng ảnh mũi tên của select dùng `!important` vì `background:` rút gọn ở rule khác sẽ xóa nó.
- Tiêu đề lỗi cũ trong DB không bị sửa vĩnh viễn: chỉ được làm sạch khi hiển thị, vì không thể khôi phục chữ gốc bị bộ gõ làm lặp (`moôột`). Phiên mới sẽ có tiêu đề đúng nếu bộ gõ gửi Backspace; nếu bộ gõ gửi cả trạng thái trung gian mà không xóa, tiêu đề vẫn có thể lặp chữ (chưa thể kiểm chứng trên bộ gõ thật của người dùng).

## Kiểm tra
- Ảnh chụp thật ở 1280px và 460px, chế độ tối và sáng: không còn tràn ngang, đủ nút, chữ dài cắt bằng dấu ba chấm.
- Test mới: `TestTitleFromKeys` (5), live/stale status (1), tiêu đề với báo cáo focus qua ConPTY thật (1), `test_ui_rules` (5), kịch bản giờ/nhóm ngày/live trong `flow_ui.cjs`.
- Số test toàn bộ: xem phần cuối nhật ký này khi chạy xong.

## Vòng 2: Agent 0 hiển thị vỡ sau "Mở lại" và danh sách thả xuống của select

### Lỗi Agent 0 sau khi mở lại từ Lịch sử
- **Nguyên nhân:** "Mở lại" tạo tiến trình mới nhưng giữ id cũ (`agent0`, `claude-1`). Dashboard giữ một xterm và một con trỏ đọc cho mỗi id. Nếu phiên cũ đã tự thoát nhưng vẫn nằm trong danh sách, dashboard thấy id đã có nên giữ xterm cũ, trong khi bộ đệm của phiên mới bắt đầu từ 0. Nội dung cũ kẹt lại, phiên mới không hiện hoặc hiện lệch.
- **Sửa:** `describe()` trả thêm `gen` (thời điểm tạo phiên); `syncTerms()` dựng lại cửa sổ khi `gen` đổi.
- **Bằng chứng (Chromium thật + server thật + agent giả chạy lâu):** cho phiên tự thoát rồi mở lại. Tắt bản sửa: sau 25 giây cửa sổ vẫn chỉ có nội dung phiên cũ. Có bản sửa: phiên mới hiện sau khoảng 2 giây, chỉ có nội dung mới.
- **Một lần đo sai đã bỏ:** lần đầu tôi đóng phiên bằng API `close` (server xóa phiên khỏi danh sách nên trang tự dựng lại) và hàm đọc màn hình lấy cả cửa sổ Agent 0; cả hai làm kết quả không phản ánh lỗi. Đã sửa phép đo trước khi kết luận.

### Danh sách thả xuống của select
- Lần trước chỉ đổi giao diện của ô chọn (viền, nền, mũi tên); khi bấm mở, danh sách vẫn là menu gốc của hệ điều hành.
- Nay `openSelectMenu()` thay danh sách đó bằng menu `.ao-select-menu` theo token `--ao-*` (dấu tích mục đang chọn, hover, bàn phím Enter/Space/Alt+↓/↑/↓/Home/End/Esc/Tab, lật lên khi hết chỗ phía dưới, nằm trong hộp thoại). `<select>` thật vẫn được giữ nguyên nên giá trị, sự kiện `change`, kiểm tra hợp lệ và bố cục không đổi.
- Quy tắc được ghi ở `docs/UI-RULES.md` (mục 1 và 2b) và có test (`test_ui_rules.py`, kịch bản bàn phím/chuột trong `flow_ui.cjs`, kiểm tra menu nằm trong màn hình ở `tools/ui_shots.cjs`).

### Kết quả test
- Python đầy đủ: 216 test OK. `flow_ui.cjs`, `layout_ui.cjs`: pass. `tools/ui_shots.cjs`: pass ở 1280px và 460px, sáng và tối.

### Lưu ý khi dùng
- Phần Python (`gen`, `live`, tiêu đề, xóa lịch sử, dò id agy) chỉ có hiệu lực sau khi **khởi động lại server**; CSS/JS chỉ cần tải lại trang (Ctrl+F5).
- Select dạng `multiple` hoặc `size>1` vẫn dùng danh sách gốc (hiện chưa có select nào như vậy).
