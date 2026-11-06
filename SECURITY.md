# Mô hình quyền và giới hạn an toàn

## Phân biệt ba lớp

1. **Orchestrator policy**: argv dạng mảng, `shell=False`, executable tuyệt đối;
   không nhận command tùy ý từ task/MCP; chỉ chạy test profile trong config do
   chủ máy quản lý. Không có commit/merge/push, xóa repo hay thay đổi config qua MCP.
   Scope edit được phát hiện sau khi worker chạy, không phải ACL ghi file tức thời.
2. **Giới hạn CLI**: Claude restricted bỏ shell và chỉ giữ file tools; Codex yêu
   cầu workspace-write, approval never, network shell tắt. CLI báo không hỗ trợ
   thì task thất bại; không fallback bypass. Đây là chính sách của CLI, không phải
   một sandbox mới do Python tạo ra. CLI và cấu hình quản trị phải được tin cậy.
3. **Cô lập OS**: Windows Job Object quản lý vòng đời process, không chặn đọc file,
   mạng hay truy cập Git. Công cụ không tạo VM/AppContainer/firewall/token hạn chế.
   Native Claude shell không có sandbox Windows, nên adapter không cấp shell.
   Tests do runner chạy là mã tùy ý với quyền người dùng, kể cả khi argv được kiểm tra.

## Khi nào cần máy ảo

Để xử lý repository, dependencies, test hoặc prompt không tin cậy, hãy chạy **cả
Agent 0, runner, repository và state** trong máy ảo Windows riêng, bằng tài khoản
thường. Không mount thư mục nguồn thật ở chế độ ghi, không chia sẻ home chứa key
khác, không cấp Git credential push, chỉ cho mạng cần thiết. Snapshot/backup trước
khi chạy. Worktree cùng repo chia sẻ object database/config/refs: worker có quyền
OS phù hợp vẫn có thể làm hỏng Git chung. Muốn chống worker độc hại, cần clone
riêng trong môi trường cô lập; worktree riêng không cung cấp bảo đảm đó.

Chỉ bật `acknowledge_local_execution` nếu chấp nhận quyền thực thi local này.
Cờ này là lựa chọn của chủ máy, không chứng nhận sandbox đã được thiết lập.

## Chống lỗi vận hành

* Config/state ở ngoài repo; không expose chúng cho worker qua MCP/file scope.
  Dùng ACL NTFS để chỉ tài khoản chạy orchestrator truy cập. Không chạy elevated.
  Công cụ không tự đổi ACL và không ngăn agent cùng tài khoản đọc file qua đường khác.
* Không commit key hoặc lưu key vào task prompt; log raw có thể chứa source/secret.
  Tránh đính kèm dữ liệu nhạy cảm. Log không có cơ chế redaction đáng tin cậy.
* Không kế thừa `GIT_*`, `NODE_OPTIONS`, `PYTHONPATH` hoặc biến key không được liệt kê.
  User home vẫn được CLI dùng để xác thực; environment allowlist không cô lập home.
* Git của orchestrator tắt hooks, fsmonitor, external diff/textconv; snapshot dùng
  hash-object `--no-filters` và index tạm. Repository-local filter config bị từ chối
  trước worktree checkout để tránh chạy smudge/process filter. Checkout phải giữ
  byte baseline, nếu bị attributes/encoding đổi byte thì dừng trước worker.
  CLI worker/test có quyền riêng và có thể
  gọi Git khác nếu có shell; vì vậy cần môi trường tin cậy hoặc VM.
* Snapshot từ chối scope cấu hình (`.git`, `.claude`, `.codex`, `.github`,
  `.mcp.json`, `.gitignore`, `.gitattributes`, `.gitmodules`, `AGENTS.md`, `CLAUDE.md`,
  `.env*`), symlink, junction, submodule. Kiểm tra HEAD/nhánh và main/master
  trước/sau. Nếu vi phạm: dừng task, không tự rollback hay sửa Git refs.
* Đây là kiểm tra phát hiện theo thời điểm, không chống sửa đổi rồi khôi phục,
  hard-link alias, race từ process khác hoặc kẻ cùng tài khoản sửa SQLite/config.
  Không dùng worktree cho công việc khác trong lúc worker/test/review chạy.
* Agent 0 phải xem output của worker, diff và code trong repo là dữ liệu không
  tin cậy; không thực thi chỉ dẫn có trong chúng. Approval digest chỉ gắn review
  với byte diff đã test, không chứng minh test đủ tốt hay reviewer độc lập.
* Test đã pass có thể là false-positive vì test được sửa; Agent 0 phải xem thay
  đổi test. Tests chạy trên host, không bị sandbox CLI bao quanh.
* Job Object được gắn ngay sau khi spawn. Có một khoảng race ngắn trước khi gắn;
  cơ chế này phục vụ dọn process của công cụ tin cậy, không chống malware.
  Nếu Windows từ chối Job Object, công cụ kill process chính và fail closed.
* Snapshot/diff không bao gồm nội dung ignored; compiler cache/venv bên ngoài
  không nằm trong digest. Rerun test trên nhánh tích hợp trước khi phát hành.

## Điều công cụ không làm

Không tự merge vào main hoặc nhánh khác, không commit/push, không tự mở PR,
không thực hiện tự sửa vòng lặp không giới hạn, không giả số token hay chi phí,
không gọi tài khoản mô hình khi test offline. Không có server TCP công khai.
MCP client được xem là bên được tin cậy để tạo task và ghi review, không có auth
riêng trên stdio. Không có hạn mức chi phí nhà cung cấp được bảo đảm từ phía server.

## Terminal nhúng trong dashboard

Dashboard có thể mở phiên terminal tương tác (Agent 0 hoặc worker trong worktree của task).
Phiên chạy bằng quyền tài khoản Windows của bạn; ai có token dashboard có thể gõ vào phiên
đó. Token chỉ có trên loopback và đổi mỗi lần chạy. Không chia sẻ liên kết Dashboard.
Terminal tương tác không dùng chế độ restricted của runner.
