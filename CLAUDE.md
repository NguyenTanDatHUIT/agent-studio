# Agent Studio: quy ước cho agent làm việc trong repo

- Giao diện web nằm ở `agent_orchestrator/web_assets/`. **Đọc `docs/UI-RULES.md` trước khi sửa UI.** Điểm chính:
  - Mọi `input`, `select`, `textarea` phải theo template (token `--ao-*`) qua khối "QUY TẮC FORM CONTROL" trong `style.css`; không dùng kiểu mặc định của trình duyệt, không rút gọn `background:` trên `select`, không `style=` trực tiếp trên ô nhập.
  - Tên trường dữ liệu trong JS và dữ liệu giả của test phải đúng tên API trả về.
  - Sau khi sửa UI, chụp và xem ảnh thật ở hai cỡ rộng/hẹp bằng `node tools/ui_shots.cjs`; test jsdom không bắt được lỗi bố cục.
- Chạy test Python: `.\.runtime\python\python.exe -m unittest discover -s tests -p "test_*.py"` (khoảng 5 đến 8 phút). Test UI: `node tests/flow_ui.cjs`, `node tests/layout_ui.cjs` (cần `NODE_PATH` tới thư mục có jsdom).
- Không push, không merge vào `main` nếu người dùng chưa yêu cầu. Ghi nhật ký công việc vào `NhatKyCongViec/`.
