# Nhật ký công việc — Agent Studio

**Ngày:** 05/11/2026  
**Dự án:** `C:\CongViec\agent\agent-orchestrator`  
**Trạng thái bàn giao:** Đã có web app local và luồng quản lý task; hiện chạy demo offline. Chưa xác minh Claude/Codex thật trên repository dự án của người dùng.

## 1. Rà soát công cụ ban đầu

- Đọc source Python, CLI/MCP, SQLite queue, Git worktree, process runner, provider adapter và test suite.
- Xác định bản ban đầu chưa có web app; thao tác thông qua CLI hoặc MCP trong Claude Code.
- Đánh giá có thể triển khai thử nghiệm local, cần kiểm chứng tích hợp model thật trước khi dùng cho dự án thực tế.
- Ghi nhận giới hạn snapshot: 10 MB/file, 50 MB tổng nội dung; mỗi file gọi Git riêng nên cần đo hiệu năng với repo lớn.
- Ghi nhận worktree không phải sandbox bảo mật; runner/test vẫn chịu các giới hạn nêu trong `SECURITY.md`.

## 2. Xây dựng web app theo mẫu người dùng

**Mẫu giao diện:**
`C:\Users\tsmda\Documents\Codex\2026-11-05\referenced-chatgpt-conversation-this-is-an\outputs\agent-studio-giao-dien.html`.

- Tách mẫu HTML thành tài nguyên nội bộ, giữ sidebar, màu sắc, cửa sổ CMD, sơ đồ và cấu trúc điều hướng.
- Thêm backend HTTP local dùng chung `Engine` với CLI/MCP; không tạo queue hoặc quy tắc review riêng.
- Thêm lệnh `web`, tùy chọn `--port`, `--demo`; thêm launcher Windows `.cmd` và `.ps1`.
- Đóng gói HTML/CSS/JS và license icon cùng Python package. Runtime web không cần npm/CDN/frontend build.
- Tạo demo dùng repository tạm và script offline; không gọi model và không cần tài khoản Claude/Codex.

### Chức năng đã làm

| Khu vực | Kết quả |
|---|---|
| Cửa sổ CMD/monitor | Theo dõi Claude/Codex, queue, audit; thêm cửa sổ theo task, phóng to/thu nhỏ, kéo sắp xếp, hỗ trợ di chuyển bằng bàn phím |
| Bố cục cửa sổ | 1×2, 2×2, 2×3, 3×3; phân trang hoặc tất cả; giữ bản nháp khi đổi bố cục |
| Giao nhiệm vụ | Nhập yêu cầu, chọn provider, scope và test profile; enqueue vào SQLite |
| Quản lý task | Tìm/lọc, xem yêu cầu, base, scope, trạng thái; yêu cầu hủy; mở biểu mẫu giao việc tiếp |
| Log và sự kiện | Đọc stdout/stderr worker/test, xem sự kiện; hiển thị tối đa 64 KiB cuối mỗi stream |
| Review | Xem diff, bằng chứng test, digest; nhập nhận xét và xác nhận đã đọc trước khi duyệt/yêu cầu chỉnh sửa |
| Xuất kết quả | Xuất và tải `changes.patch`, `manifest.json`; kiểm tra lại snapshot/digest khi xuất/tải |
| Tổng quan, báo cáo | Trạng thái task/sự kiện, tối đa 200 task gần nhất, test profile đạt, thời gian worker, usage do CLI trả về |
| Quyền và bảo vệ | Hiển thị chính sách hiện tại; không sửa config hay tự bật quyền thực thi từ web |

**Phạm vi ô CMD:** hiện là monitor log và giao task có scope/test, chưa phải terminal PTY/CMD hệ thống tương tác. Dashboard không tự mở runner.

### Bảo vệ HTTP đã bổ sung

- Chỉ bind `127.0.0.1`, sinh bearer token mới mỗi lần server khởi động.
- Kiểm tra Host, Origin và token; POST yêu cầu JSON cùng origin, giới hạn 200 KB.
- Không bật CORS hoặc endpoint thực thi shell/config tùy ý.
- Escape nội dung task/log/diff; thêm CSP, chống nhúng frame và cache dữ liệu nhạy cảm.
- Không ghi token vào nhật ký này. Mở liên kết có token do terminal in ra khi khởi động.

## 3. Điều chỉnh Sơ đồ điều phối theo đặc tả mới

**Tài liệu yêu cầu:** `C:\Users\tsmda\Downloads\agent-studio-so-do-dieu-phoi.md`.

- Chỉ sửa component sơ đồ dùng chung trong Tổng quan và Luồng tự động; giữ HTML các khu vực khác.
- Board navy 1274 × 428 px; card worker 218 × 136 px; khoảng cách các cột rộng hơn.
- Giữ luồng trái → phải: Agent 0 → Claude/Codex → hai test → Review → Xuất patch.
- Màn hình nhỏ cuộn ngang riêng trong sơ đồ, không scale/bóp nhỏ card.
- Thêm nét đứt chuyển động và viền thở nhẹ theo dữ liệu sự kiện thực tế:
  - `worker_started`: nhánh Agent 0 → Worker.
  - `test_started`: nhánh Worker → Test.
- Không tự tạo trạng thái chạy review/export. Task dừng, chờ review, đã duyệt hoặc không rõ giai đoạn giữ hiệu ứng tĩnh.
- Tách highlight card được chọn khỏi trạng thái đang chạy; mở đúng task đang hiển thị.
- Giữ SVG khi polling để tránh khởi động lại animation liên tục; hỗ trợ reduced motion và focus bàn phím.
- Không sửa backend, API, MCP, Git worktree, quy tắc test/review/merge; giữ tên hàm và các hook hiện có.

## 4. Kết quả kiểm thử đã thực hiện

| Kiểm tra | Kết quả và phạm vi |
|---|---|
| Python unit/integration sau khi thêm web | **45/45 pass**, 103,446 giây; Windows, Python 3.13.14; gồm 8 HTTP test mới |
| HTTP regression sau hoàn thiện header kết nối | **8/8 pass**, 24,405 giây |
| Kiểm thử DOM qua HTTP thật | Pass điều hướng, lưới/phân trang, bản nháp, phóng to, sắp xếp, thêm cửa sổ, tạo/hủy task, escape HTML, review/digest, xuất/tải artifact |
| Kiểm thử riêng sơ đồ bằng jsdom | Pass 7 node/7 connector, CSS fixed board, phép tính tâm cạnh, scope cuộn ngang, worker/test event mapping, chọn task, selected/running, SVG ổn định và reduced-motion rules |
| Kiểm tra phạm vi HTML | DOM ngoài template sơ đồ giống bản trước, bỏ qua khoảng trắng |
| Cú pháp | Python AST 17 file pass trong lượt triển khai web; `node --check app.js` pass sau chỉnh sơ đồ |
| Khởi chạy local | Launcher `.cmd` chạy được; dashboard cổng 8765 trả HTTP 200 tại thời điểm kiểm tra |

Các test worker dùng script/fixture offline. Kiểm thử DOM hồi quy sau chỉnh sơ đồ chạy trên demo riêng cổng 8766; server kiểm thử riêng đã được dừng. Không gọi Claude/Codex thật.

Runtime Python ban đầu không có trên PATH trong shell hiện tại. Đã chuẩn bị bản sao runtime riêng dưới `.runtime/python` để chạy kiểm thử; không chỉnh Python/config của ứng dụng khác. Runtime và scratch được ignore khỏi source. PowerShell execution policy chặn launcher `.ps1` trên máy hiện tại; dùng `.cmd` hoặc lệnh Python trực tiếp, không thay đổi execution policy.

## 5. Những việc chưa hoàn thành / giới hạn xác minh

1. Chưa cấu hình repository thực tế, đường dẫn CLI Claude/Codex, model, đăng nhập và test profile của dự án đích.
2. Chưa chạy task gọi model thật xuyên suốt: enqueue → worker sửa code → test → review → export → áp patch lên nhánh thử.
3. Chưa kiểm chứng sandbox/quyền của một phiên model thật, usage thực tế, quyền thuê bao hoặc chi phí.
4. Chưa xác minh pixel/layout, tràn ngang toàn trang hoặc responsive trong trình duyệt tại các viewport đặc tả; chưa có ảnh trước/sau. Quyền dùng Edge bị từ chối khi triển khai web; browser access host không khả dụng khi chỉnh sơ đồ. jsdom không thay thế kiểm tra bố cục trình duyệt.
5. Chưa benchmark repo lớn; chưa tối ưu snapshot hoặc thay các giới hạn kích thước đã ghi nhận.
6. Chưa kiểm tra cài package từ pip/wheel. Đã khai báo package data; các lượt chạy được xác minh từ source.
7. Chưa triển khai dịch vụ Internet/LAN nhiều tài khoản, terminal hệ thống tương tác hoặc tự quản lý vòng đời runner trên web.
8. Không commit/merge/push mã dự án thật. Thư mục source hiện tại chưa phải Git repository tại thời điểm rà soát.

**Kết luận hiện trạng:** phần web và cơ chế orchestrator đã có thực thi, không chỉ là mockup. Phiên dashboard được kiểm tra gần nhất vẫn có `demo: true`, trỏ đến repository tạm `OFFLINE-DEMO`, provider dùng `demo_worker.py`, không có runner model thật. Chưa đủ bằng chứng để tuyên bố đã sẵn sàng vận hành Claude/Codex trên dự án thực tế.

## 6. File chính và tài liệu bàn giao

- [Backend web](../agent_orchestrator/web.py)
- [CLI](../agent_orchestrator/cli.py)
- [Demo workspace](../agent_orchestrator/demo.py), [worker offline](../agent_orchestrator/demo_worker.py)
- [HTML](../agent_orchestrator/web_assets/index.html), [CSS](../agent_orchestrator/web_assets/style.css), [JavaScript](../agent_orchestrator/web_assets/app.js)
- [Launcher CMD](../Start-AgentStudio.cmd), [launcher PowerShell](../Start-AgentStudio.ps1)
- [HTTP tests](../tests/test_web.py), [DOM regression](../tests/web_ui.cjs), [flow DOM tests](../tests/flow_ui.cjs)
- [Hướng dẫn web app](../docs/WEB-APP.md)
- [Kết quả 45 test](../docs/WEB-TEST-RESULTS.txt), [kết quả 8 HTTP test](../docs/WEB-HTTP-TEST-RESULTS.txt)
- [Báo cáo chỉnh sơ đồ](../docs/FLOW-DIAGRAM-UPDATE.md), [diff giao diện](../docs/FLOW-DIAGRAM-UPDATE.patch)

## 7. Hướng tiếp tục

1. Chọn repository thử nghiệm riêng và test profile có kiểm tra chức năng thật.
2. Cấu hình CLI/provider từ executable thực tế, kiểm tra khả năng hỗ trợ các flag adapter và đăng nhập.
3. Chạy một task nhỏ bằng từng provider, review patch và test lại khi áp lên nhánh thử.
4. Kiểm tra trực quan sơ đồ theo các viewport trong đặc tả, bổ sung ảnh trước/sau và xử lý lỗi nếu phát hiện.
5. Đo thời gian snapshot/dung lượng trên repo dự kiến dùng trước khi tăng số worker.

## 8. Tiếp tục: chuẩn bị vận hành CLI thật

### Đã triển khai

- `init --detect-providers`: tìm native CLI hoặc Node + entrypoint; thêm
  `--test-profile NAME=JSON_ARGV`, `--enable-execution` cho cấu hình local tường minh.
- `doctor --probe --check-auth`: kiểm tra version/help/cờ và đăng nhập, không gọi
  model, không trả nội dung credential. Thiếu CLI giữ trạng thái chưa cấu hình.
- `web --run-workers`: runner riêng cho từng provider đã cấu hình, dùng chung
  Engine/SQLite; preflight trước khi chạy. Ctrl+C hủy worker/test đang chạy và
  đóng thread; task bị hủy được giữ worktree/log để xem lại.
- Launcher CMD với config và PowerShell với `-Config` mở runner cùng web.
  PowerShell có `-MonitorOnly`; CLI `web` không có cờ vẫn chỉ monitor.
- `GET /api/runners` có xác thực; dashboard hiển thị runner sẵn sàng/busy/lỗi/dừng,
  phân biệt runner do web quản lý và runner mở riêng. Không thêm API chạy shell.
- Sửa đọc pipe bằng `read1` và flush log để stdout/stderr xuất hiện khi process
  còn chạy; lỗi CLI lấy phần cuối stderr để hiển thị trong chi tiết task.
- Thêm `tools/prepare_live_check.py`, `Start-LiveCheck.cmd` và `docs/LIVE-RUN.md`.
  Repo calculator riêng có lỗi cộng/trừ và ba functional checks cố định;
  config/state ở ngoài repo thử, dưới `.local-run` đã ignore.

### Kiểm tra thực tế và giới hạn

- Codex CLI **0.166.0** trong `.codex/packages/app-server-daemon/releases` đọc và
  thực thi được; bản npm Claude/Codex đang có process nhưng shell bị chặn truy cập.
- Help Codex có đủ cờ adapter. Với home xác thực được chỉ định cho subprocess,
  `login status` báo **Logged in using ChatGPT**. Không đọc/in credential.
- Task thật **efb297e06d80496ab6b06d69** trên repo thử đã tạo worktree và gọi native
  Codex. CLI thoát 1 trước khi gọi model với lỗi
  `failed to initialize in-process app-server client: Access is denied. (os error 5)`.
  Đây là lỗi quyền môi trường thực thi hiện tại, không phải task model thành công.
- Không có terminal result/usage/patch, chưa chạy test chức năng của task thật,
  chưa đi qua review/export/áp patch bằng model thật. Không đổi ACL/quyền, sao
  chép credential hoặc nới sandbox để vượt lỗi. Không để server/runner thử chạy nền.
- Người dùng có thể chạy `Start-LiveCheck.cmd` từ phiên Windows đã cài/đăng nhập CLI;
  launcher này thực sự gọi model và có thể tiêu thụ quota. Chưa xác minh lượt này.
- Chưa nhận repo đích của người dùng; chưa cấu hình test hoặc sửa code dự án khác.

### Kết quả hồi quy

- **52/52 tests pass**, 228,797 giây, Windows/Python 3.13.14. Gồm tương thích CLI,
  login-output handling, runner xử lý task đến chờ review, shutdown hủy child,
  log xuất hiện trước khi child thoát và HTTP runner status có xác thực/read-only.
- `node --check agent_orchestrator/web_assets/app.js` pass.
- CLI chặn kết hợp `web --demo --run-workers` đúng kỳ vọng.
- Bản kiểm thử runner dùng fixture offline; không tính là bằng chứng model thật.
  Chưa chạy lại jsdom/browser layout hoặc đóng gói wheel trong lượt này.
- Báo cáo text sạch: `docs/LIVE-TEST-RESULTS.txt`.
