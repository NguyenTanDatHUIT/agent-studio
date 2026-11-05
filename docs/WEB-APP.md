# Agent Studio — web app local

Giao diện được triển khai từ mẫu `agent-studio-giao-dien.html` người dùng cung cấp ngày
05/11/2026. Giữ sidebar, màu sắc, sơ đồ điều phối, cửa sổ CMD và thanh cài đặt bố cục.
Tài nguyên được đóng gói cùng Python package; không cần npm, CDN hay frontend build khi chạy.

## Mở nhanh

Tại thư mục source, với Python 3.11+ và Git:

```powershell
.\Start-AgentStudio.cmd
# Hoặc:
python -m agent_orchestrator web --demo --port 8765
```

Mở **nguyên liên kết Dashboard có `#token=...`** được in trong terminal. Token được
giữ trong sessionStorage của tab và xóa khỏi thanh địa chỉ sau khi mở. Khi server
khởi động lại, dùng liên kết mới. `localhost` không thay thế cho `127.0.0.1` trong
liên kết này vì server kiểm tra Host/Origin chính xác.

Demo tạo Git repository và queue tạm, một task có diff/test thật do script offline
tạo ra, một task chờ chạy. Không gọi model, không cần đăng nhập, không có runner
đang hoạt động. Khi dừng server, dữ liệu demo bị xóa. Usage demo không được ước lượng.

Có thể chỉ định Python:

```powershell
.\Start-AgentStudio.ps1 -Demo -Python C:\Python312\python.exe
```

Nếu máy không cho phép chạy PowerShell script, dùng `Start-AgentStudio.cmd` hoặc
lệnh Python trực tiếp; không cần thay đổi execution policy.

## Dùng với dự án thật

**Cập nhật:** xem [LIVE-RUN.md](LIVE-RUN.md) để phát hiện CLI, kiểm tra đăng nhập
và chạy thử model thật. Launcher với config hiện mở runner cùng web; các lệnh
runner riêng bên dưới dành cho chế độ monitor-only, tránh mở trùng không cần thiết.

Tạo config/state ngoài repo và cấu hình provider/test theo README. Sau đó:

```powershell
.\Start-AgentStudio.cmd C:\AgentControl\myapp.json
# Tương đương:
python -m agent_orchestrator --config C:\AgentControl\myapp.json web --port 8765
```

Mở runner trong các terminal riêng, dùng cùng config:

```powershell
python -m agent_orchestrator --config C:\AgentControl\myapp.json worker --provider claude
python -m agent_orchestrator --config C:\AgentControl\myapp.json worker --provider codex
```

Web app không sửa config hoặc tự bật quyền thực thi. `web --run-workers` mở runner
cho provider đã cấu hình; Ctrl+C dừng cả web/runner/process con. `web` không có cờ
này chỉ monitor. Dashboard đọc `/api/runners` để phân biệt runner được quản lý;
task `running` riêng lẻ không chứng minh process còn sống.

## Chức năng

- **Cửa sổ CMD:** monitor Claude/Codex, queue, audit; thêm cửa sổ theo task,
  bố cục 1×2 / 2×2 / 2×3 / 3×3, phân trang/tất cả, phóng to, kéo tay nắm sắp xếp.
  Alt + trái/phải trên tay nắm cũng di chuyển được cửa sổ. Bản nháp giữ khi đổi bố cục.
- **Ô nhập:** `help`, `status`, `events`, `stdout`, `stderr`, `clear` phục vụ monitor.
  Nội dung khác mở biểu mẫu giao việc với provider, scope và test profile để người dùng
  kiểm tra rồi enqueue. Đây là monitor log và giao task, chưa phải terminal PTY/CMD tương tác.
- **Tổng quan/luồng:** đọc trạng thái task và sự kiện thật, không có nút mô phỏng tiến độ.
- **Nhiệm vụ:** tạo, tìm, lọc, đọc prompt/scope/base, hủy, xem stdout/stderr và test log,
  xem event, xem diff và bằng chứng test, ghi review, xuất/tải patch và manifest.
- **Review:** phải mở diff lấy digest, nhập nhận xét và xác nhận đã đọc bằng chứng.
  Khi diff bị rút gọn ở 100.000 ký tự, tải file đầy đủ để đọc. Engine kiểm tra snapshot
  và digest lại khi duyệt/xuất/tải artifact.
- **Báo cáo:** tổng hợp tối đa 200 task gần nhất, số test profile đạt và trung vị thời
  gian worker đã kết thúc. Token/chi phí chỉ lấy số CLI trả về; thiếu thì ghi “Chưa có”.

Log hiển thị tối đa 64 KiB cuối mỗi stream; raw log vẫn nằm trong state. Dashboard
poll mỗi 3 giây khi tab đang hiển thị. Cấu hình quyền được đọc khi server khởi động;
khởi động lại server/runner sau khi đổi file config.

## Phạm vi HTTP

Server chỉ bind `127.0.0.1`; mỗi lần khởi động tạo bearer token ngẫu nhiên. API kiểm
tra token, Host và Origin; POST yêu cầu JSON cùng origin, tối đa 200 KB. Không bật
CORS, không có endpoint chạy shell/config tùy ý. HTML không thực thi nội dung từ
prompt, log, model summary hoặc diff. Đây là web app một người dùng trên máy local,
không phải server Internet/LAN nhiều tài khoản. Các giới hạn trong SECURITY.md vẫn áp dụng.

## Kiểm thử

```powershell
python -m unittest discover -v
```

Ngày 05/11/2026: **45/45 test pass** với Python 3.13.14 / Windows, gồm 8 HTTP test mới.
Runtime kiểm thử là bản sao cục bộ riêng dưới `.runtime/python`, với đường dẫn source
trong `python313._pth`; không chỉnh Python hoặc cấu hình của ứng dụng khác.

Kiểm thử DOM tùy chọn, cần jsdom (chỉ cho kiểm thử) và server `web --demo` mới:

```powershell
node tests/web_ui.cjs 'http://127.0.0.1:8765/#token=TOKEN_IN_TERMINAL'
```

Đã pass luồng DOM qua HTTP thật: điều hướng, sơ đồ, bố cục/phân trang, bản nháp,
phóng to, sắp xếp, thêm cửa sổ, tạo task, escape HTML, hủy, review/digest, xuất và tải.
Không dùng kiểm thử này với config dự án thật. Chưa xác minh pixel/layout trong trình
duyệt vì quyền điều khiển Edge bị từ chối. Chưa gọi Claude/Codex thật.
