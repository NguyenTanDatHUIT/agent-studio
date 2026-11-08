# Agent Studio — web app local
Ghi chú: dashboard chỉ lắng nghe trên localhost.

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

## Terminal thật trong dashboard

Thẻ **Agent 0** tự mở một phiên Claude Code tương tác (ConPTY) đã nối sẵn MCP orchestrator;
bạn giao việc và chọn Claude/Codex làm việc ở đây. Thẻ Claude/Codex Worker có nút
**Mở terminal**: chạy CLI tương tác của provider trong worktree của task gần nhất, để
bạn trao đổi trực tiếp với worker. Không còn ô nhập giả trên các thẻ.

Giới hạn an toàn: trình duyệt chỉ chọn loại phiên cố định (`agent0` hoặc `worker` + task id);
executable lấy từ config của chủ máy, không nhận lệnh từ trình duyệt. Mọi API terminal
yêu cầu bearer token và same-origin như các API khác. Terminal tương tác dùng cơ chế xin
quyền mặc định của CLI (không có cờ restricted của runner), nên bạn là người chấp thuận
từng thao tác. Yêu cầu Windows 10 1809+ (ConPTY). xterm.js 5.5.0 (MIT) được đóng gói trong
`web_assets/vendor/`, không dùng CDN.

## Cửa sổ theo dõi task và giao việc cho terminal

**Giao việc xong thì terminal hiện ra.** Khi một agent có việc trong hàng đợi (từ Agent 0 qua MCP, từ web hoặc CLI),
dashboard tự mở cửa sổ `Codex 1` trong tab **Cửa sổ CMD** và báo bằng thông báo. Cửa sổ
hiển thị trực tiếp: hàng đợi, worker bắt đầu, log worker (Codex theo từng sự kiện; Claude chỉ trả kết quả
một lần khi xong nên chỉ có nhịp "vẫn đang chạy"), từng test, rồi kết quả. Nếu 8 giây sau vẫn `queued`
mà dashboard không thấy runner, cửa sổ cảnh báo. Cửa sổ này **chỉ đọc**: worker chạy nền có giới hạn
(đúng cách engine xác minh kết quả), không phải phiên tương tác. Tối đa 12 cửa sổ; cửa sổ của agent đang rảnh được dọn tự động khi cần chỗ.

**ID terminal.** Terminal mở bằng nút CMD và agent hàng đợi có ID `codex-1`, `claude-2`, `agy-3` (số chung, hiện trên thẻ). Agent 0 nhận
`codex-1`, `codex#1`, `Codex #1` đều như nhau. Cửa sổ cmd bạn tự mở bên ngoài dashboard không có ID.

**Agent 0 gõ vào terminal có sẵn.** `send_to_terminal(terminal_id, text)`, mỗi lần được hỏi xác nhận, có
audit và giới hạn (xem `SECURITY.md`). Việc cần test và review vẫn nên giao bằng `enqueue_task`.

**Trang Luồng tự động** chỉ dùng dữ liệu thật: trạng thái kết nối của Agent 0 và tool gần nhất, runner
từng provider, các terminal đang mở (nút Mở nhảy tới cửa sổ), sự kiện gần nhất, profile test trong config.
Khi chưa có gì thì hiện đúng "chưa có", không còn chữ mẫu.

## Agent đánh số, làm tiếp và cài đặt cửa sổ

**Số agent.** Mỗi agent có một số tăng dần chung (`codex 1`, `claude 2`...), không dùng lại và giữ nguyên khi khởi động lại.
Terminal bấm "CMD" và agent hàng đợi do Agent 0 tạo dùng chung bộ đếm. Gõ `codex 1`, `codex-1`, `codex#1` hay chỉ `1` đều được.

**Cửa sổ của agent hàng đợi.** Mỗi agent có đúng một cửa sổ chỉ đọc (`Codex 1`), tự mở khi có việc, và nhận việc tiếp vào chính cửa sổ đó
("vòng 2", "vòng 3"...). Cửa sổ không tự đóng khi task xong mà chuyển sang "Sẵn sàng". Đóng cửa sổ thì nó chỉ mở lại khi agent bắt đầu vòng mới.

**Làm tiếp.** Agent 0 nói "codex 1 làm tiếp ...", hoặc bạn bấm "Giao việc tiếp cho codex 1" trong tab Nhiệm vụ. Mặc định agent nhớ ngữ cảnh:
làm tiếp trong cùng worktree và cùng phiên model (có dự phòng phiên mới kèm tóm tắt). Kết quả và digest tính lại, cần review lại.

**Biểu tượng cài đặt (bánh răng) trên thanh tiêu đề mỗi cửa sổ.**
- Cửa sổ agent hàng đợi: tick "Nhớ ngữ cảnh sau mỗi task". Tắt thì mỗi task bắt đầu mới từ commit gốc. Agent 0 có thể ghi đè từng lần bằng `remember`.
- Cửa sổ Agent 0: tick "Agent mới mặc định nhớ ngữ cảnh" (mặc định bật).
- Terminal tương tác không có tùy chọn: nó là tiến trình sống nên luôn giữ ngữ cảnh.
Danh sách tùy chọn nằm trong `settingDefs` của `app.js` (thêm một dòng ở đó và một khóa trong danh sách cho phép ở `web.py`).

**Hàng × cột.** Ngoài bốn nút 1×2, 2×2, 2×3, 3×3 có một ô nhập cùng kích thước: gõ `1x2`, `1 x 2` hoặc `3×2` rồi Enter hoặc rời ô.
Mỗi số từ 1 đến 6. Nhập sai thì ô đổi viền đỏ, hiện thông báo và giữ bố cục cũ. Bố cục được nhớ khi tải lại trang.

## Giao diện: toàn chiều ngang, sidebar đóng được, phong cách Claude

- **Toàn chiều ngang.** Vùng làm việc không còn bị chặn ở 1800px (giới hạn này có từ commit đầu, nằm trong khối CSS ghi đè cho trang độc lập). Riêng sơ đồ điều phối vẫn là bảng cố định 1274px, cuộn ngang khi hẹp, theo đúng đặc tả sơ đồ.
- **Sidebar đóng được.** Nút ở góc trên bên trái thu sidebar thành thanh biểu tượng 62px (di chuột để xem tên) và mở lại; trạng thái được nhớ khi tải lại. Dưới 850px sidebar đã là thanh biểu tượng nên nút ẩn đi.
- **Phong cách Claude.** Nền giấy ấm, viền mảnh, màu nhấn đất nung, tiêu đề chữ serif (Tiempos nếu máy có, nếu không thì Iowan/Palatino/Georgia), sáng và tối theo hệ điều hành. Màu thành công/đang chạy giữ màu xanh lá để không lẫn với màu thương hiệu. Bảng màu lấy cảm hứng từ màu thương hiệu công khai của Anthropic; **không dùng stylesheet hay font của Anthropic**. Toàn bộ nằm trong một khối CSS ở cuối `style.css` ("Claude-style theme"): sửa các biến `--ao-*` / `--af-*` để đổi màu, xóa khối đó để quay về giao diện teal/navy cũ.

### Cài đặt giao diện (sáng / tối / bảng màu)

Nút mặt trời-mặt trăng ở góc trên bên phải mở hộp "Giao diện":
- **Chế độ**: Theo hệ thống (mặc định), Sáng, Tối. Chọn Sáng hoặc Tối sẽ ghi đè cài đặt của hệ điều hành.
- **Bảng màu**: **Claude** (nền giấy ấm, chữ serif, màu đất nung) hoặc **Cổ điển** (đúng bảng màu cũ: nền xanh lạnh, màu teal, thanh bên và thẻ sáng hơn).
Thay đổi có hiệu lực ngay, kể cả màu nền của các terminal, và được nhớ trong trình duyệt này (localStorage). Giá trị lưu không hợp lệ thì quay về Theo hệ thống + Claude. Bảng màu nằm trong các biến `--ao-*`, `--af-*`, `--cmd-*`; bảng Cổ điển là khối `#ao-studio[data-palette="classic"]` ở cuối `style.css`.

### Cỡ chữ, thanh cuộn và lăn chuột trong terminal

- **Cỡ chữ giao diện là 12px** (chữ thường, nhãn, nút, bảng, ô nhập). Các tiêu đề đã to (tiêu đề trang, `h2`/`h3`, tên thương hiệu, số liệu lớn, tên nút trong sơ đồ) giữ nguyên. Trong cửa sổ CMD chỉ thanh tiêu đề (`.ao-terminal-title-row`) theo cỡ 12px; chữ bên trong terminal (xterm 13px, log 12px) không đổi.
- **Thanh cuộn** là viên thuốc mảnh bo tròn theo giao diện, không có mũi tên ▲▼ (Edge/Chrome; Firefox dùng thanh mảnh chuẩn). Trong terminal thanh cuộn nhạt, đậm lên khi rê chuột.
- **Lăn chuột trong terminal.** Ứng dụng chạy ở bộ đệm thường (có thanh cuộn, ví dụ log dài) cuộn bình thường. Ứng dụng toàn màn hình (màn hình phụ, như Claude Code hay Codex ở chế độ toàn màn hình) không có lịch sử cuộn để xterm cuộn; ConPTY cũng không chuyển chế độ bắt chuột sang xterm, nên xterm.js mặc định biến mỗi nấc lăn thành nhiều phím mũi tên ↑↓ mà các ứng dụng chat hiểu là "duyệt lại câu đã gõ". Biểu tượng cài đặt của terminal có mục **Lăn chuột trong ứng dụng toàn màn hình**: `PageUp/PageDown` (mặc định, mỗi nấc một trang), `Mũi tên ↑ ↓` (kiểu xterm), hoặc `Không gửi gì`. Lựa chọn áp dụng cho mọi terminal và được nhớ trong trình duyệt.

## Thông báo cho Agent 0, workflow và nhiều repo

- **Thông báo**: khi task của agent đánh số xong (`awaiting_review`), lỗi hoặc bị hủy, và khi workflow giao/chặn/hoàn tất một bước,
  dashboard gõ một dòng `[AO] ...` vào terminal Agent 0 (chỉ id và trạng thái, không có nội dung worker). Tối đa một dòng mỗi 5 giây,
  không gõ khi người dùng đang gõ trong 4 giây gần nhất, mỗi lần gõ đều ghi vào `terminal-audit.jsonl`. Tắt bằng
  `POST /api/settings {"notify_agent0": false}`. Chỉ tin mới sau khi Agent 0 được mở mới được gửi.
- **Workflow**: `enqueue_plan` (MCP), `POST /api/workflows`, xem ở trang "Luồng tự động". Các bước phụ thuộc nhau bằng `after`; bước sau chỉ chạy khi các bước
  trước xong. Hạn chế đã biết: mã của bước do agent khác làm không được tự hợp nhất vào worktree của bước sau; dùng cùng một agent (`same_agent_as`) khi cần mã đó.
- **Nhiều repo**: khai báo trong config `"repos": {"web": "C:/code/web"}`. Chọn repo khi thêm terminal hoặc `enqueue_task(repo="web")`.
  Agent gắn với một repo. Tên repo chỉ lấy từ config, task không gửi đường dẫn.

## Lịch sử chat & Mở lại phiên (Conversations & Resume)

Dashboard cung cấp nút **"Lịch sử"** trên thanh điều khiển (cạnh "Làm mới log"):
- **Hộp thoại Lịch sử**:
  - Nhóm các phiên làm việc theo ngày (`Hôm nay`, `Hôm qua`, hoặc ngày cụ thể `DD/MM/YYYY`).
  - Hỗ trợ ô tìm kiếm theo tiêu đề/ID và bộ lọc nhà cung cấp (Agent 0, Claude, Codex, Antigravity).
  - Hiển thị thời gian bắt đầu, badge số hiệu agent, tiêu đề tóm tắt, ngữ cảnh làm việc (repo, task worktree, thư mục cwd), và trạng thái hiện tại.
- **Hành động**:
  - **"Xem lại"**: Mở modal transcript chỉ đọc. Toàn bộ nội dung hiển thị trong xterm trước đó được lưu và hiển thị kèm mốc thời gian từng dòng. Hỗ trợ phân trang tải thêm các dòng cũ hơn và nút "Sao chép" để lấy nội dung văn bản.
  - **"Mở lại" (Resume)**: Khôi phục phiên làm việc thực tế (`claude --resume <id>` hoặc `codex resume <id>`) vào một cửa sổ terminal mới, tự động định vị lại thư mục dự án và chuyển tới đúng trang cửa sổ. Phiên đang mở được vô hiệu hóa nút mở lại để tránh xung đột hai tiến trình cùng ghi vào một phiên.


## Cuộc trò chuyện mới và hộp thoại Thêm CMD

- Nút **"Cuộc trò chuyện mới"** (tab Cửa sổ CMD) mở hộp thoại xác nhận; khi xác nhận: đóng mọi cửa sổ CMD (giữ trong Lịch sử), đánh số agent lại từ 1 và mở lại Agent 0 trống. Bị khóa (có nêu lý do) khi còn nhiệm vụ hoặc workflow đang chạy. Mỗi lần mở công cụ cũng tự bắt đầu từ số 1. Chi tiết: `docs/HUONG-DAN-LICH-SU-CHAT.md` (mục "Cuộc trò chuyện mới") và `docs/KIEN-TRUC-LICH-SU-CHAT.md` (mục 6).
- Hộp thoại **"Thêm terminal agent"** chỉ còn chọn Agent (và Repo khi có nhiều repo). Ô "Thư mục làm việc" (chọn worktree của task) đã bỏ: terminal luôn mở ở thư mục repo đã chọn. Backend vẫn nhận `task_id` cho nút "Mở terminal" ở chi tiết task.


## Trình duyệt dùng để mở dashboard

Khi chạy bằng `Start-AgentStudio.cmd` (hoặc lối tắt trên desktop), công cụ mở dashboard bằng **Google Chrome** nếu đã cài (tìm trong `Program Files`, `Program Files (x86)`, `%LocalAppData%` và registry App Paths); nếu không có Chrome thì dùng trình duyệt mặc định của Windows. Đổi bằng biến môi trường `AGENT_STUDIO_BROWSER`:

| Giá trị | Kết quả |
|---|---|
| (không đặt) hoặc `chrome` | Chrome nếu có, không thì trình duyệt mặc định |
| `default` | Luôn dùng trình duyệt mặc định của Windows (ví dụ Edge) |
| `C:/Program Files/Mozilla Firefox/firefox.exe` (ví dụ) | Dùng đúng file đó (phải là đường dẫn tuyệt đối tới một file `.exe` có thật) |

Giá trị không hợp lệ (đường dẫn tương đối, không phải `.exe`, không tồn tại) không chạy gì cả mà quay về trình duyệt mặc định. Địa chỉ có token được truyền như một đối số duy nhất, không qua shell. Mã nguồn: `agent_orchestrator/browser.py`.
