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

### Agent 0 gõ vào terminal (`send_to_terminal`)

Agent 0 có thể gõ **một dòng** vào một terminal agent tương tác do dashboard mở. Đây là kênh prompt
injection tiềm năng giữa các agent, nên có các rào chắn sau:

- Công cụ không nằm trong danh sách tự duyệt của Agent 0: Claude Code hỏi bạn xác nhận **mỗi lần gọi**.
- Cầu nối chỉ nhận POST `/api/bridge/terminals/<id>/input` kèm khóa riêng của phiên dashboard; mọi
  đường ghi khác trên cầu nối bị từ chối. Khóa đổi mỗi lần chạy và không lưu trong config.
- Chỉ gửi được vào terminal `agent` còn sống; từ chối Agent 0 và cửa sổ theo dõi task.
- Văn bản bị bỏ mọi ký tự điều khiển (kể cả ESC) và gộp về một dòng, tối đa 4000 ký tự,
  tối thiểu 1 giây giữa hai lần gửi vào cùng terminal.
- Mỗi lần gửi được ghi vào `terminal-audit.jsonl` trong state (thời gian, terminal, độ dài, SHA-256, 200
  ký tự đầu).
- Nội dung đọc lại từ terminal vẫn là dữ liệu không đáng tin; Agent 0 không được làm theo lệnh trong đó.

### Cửa sổ theo dõi task

Mỗi agent hàng đợi có việc `queued`/`running` tự có một cửa sổ **chỉ đọc** trong dashboard, hiển thị sự kiện và log. Mọi
văn bản từ log được loại ký tự điều khiển trước khi in, để log của worker không thể chèn escape sequence
vào terminal của bạn. Cửa sổ không nhận phím gõ ở cả trình duyệt lẫn API.

### Nhớ ngữ cảnh giữa các task

Mặc định (tắt được cho từng agent, hoặc mặc định chung ở biểu tượng cài đặt của Agent 0), worker lưu phiên model để
agent làm tiếp. Đánh đổi cần biết:

- Bỏ `--ephemeral` (Codex) và `--no-session-persistence` (Claude) cho các agent đang nhớ: lịch sử hội thoại, gồm lời nhắc và
  nội dung file đã đọc, do chính CLI lưu trên đĩa (thư mục dữ liệu của Claude/Codex trong hồ sơ người dùng) với quyền tài khoản
  Windows của bạn. Tắt nhớ ngữ cảnh để quay lại phiên ephemeral hoàn toàn.
- Chính sách quyền của worker không đổi khi làm tiếp (Claude `--restricted`, công cụ giới hạn; Codex workspace-write, tắt mạng,
  `approval_policy=never`). `codex exec resume` không có `--sandbox` nên chính sách được truyền bằng `-c sandbox_mode`; nếu CLI
  bỏ qua, mặc định của nó là chỉ đọc nên thất bại an toàn ("no changes"), không mở rộng quyền. Chưa kiểm chứng với tài khoản thật.
- Session id lấy từ đầu ra của CLI và được kiểm tra bằng regex trước khi đưa vào dòng lệnh.
- Làm tiếp dùng lại đúng worktree cũ, nên mỗi vòng cần test và review lại với digest mới; bằng chứng cũ mất hiệu lực.
  `protected_refs` được làm mới đầu mỗi vòng (bạn có thể đã tích hợp vào main giữa hai vòng).
- Phạm vi chỉnh sửa vẫn được kiểm tra trên toàn bộ thay đổi so với commit gốc: `allow_paths` của vòng sau phải bao gồm các file
  đã sửa ở vòng trước.

### Lịch sử chat và bản ghi màn hình (Transcripts)

Hệ thống lưu lại các bản ghi màn hình (transcripts) để người dùng có thể xem lại toàn bộ tiến trình trao đổi của các terminal agent và Agent 0:

- **Vị trí lưu trữ**: Nằm tại `<state_dir>/transcripts/<conversation_id>.log`. Chỉ tài khoản người dùng Windows chạy Orchestrator có quyền đọc/ghi.
- **Giới hạn kích thước**: Mỗi file transcript tối đa 5 MB (tự động cắt các dòng cũ nhất khi vượt ngưỡng). Tổng dung lượng thư mục transcripts được giới hạn ở 100 MB; khi đạt mức này, các file transcript cũ nhất sẽ tự động được thu hồi.
- **Lọc chuỗi nhạy cảm (Redaction)**: Mã nguồn tự động loại bỏ các mã điều khiển ANSI escape sequences, đồng thời tự động nhận diện và làm mờ (redact) các chuỗi nhạy cảm giống token/bearer/API key (`ghp_*`, `sk-ant-*`, `sk-*`, `Bearer ...`) trước khi ghi vào đĩa.
- **Cách xóa dữ liệu**: Trong hộp thoại Lịch sử, nút "Xóa" (một phiên) và "Xóa tất cả" gỡ dòng lịch sử và file transcript (API `POST /api/conversations/<id>/delete` và `/api/conversations/delete-all`; cần token + Origin hợp lệ, không có trên bridge của Agent 0, từ chối phiên đang mở, chỉ xóa file nằm trong `transcripts/`, có audit). Xóa thủ công file trong `transcripts/` vẫn an toàn: API sẽ báo bản ghi trống. Phiên do chính Claude/Codex/agy lưu (`~/.claude`, `~/.codex`, `~/.gemini`) không bị Agent Studio xóa.
- **Cách ly Agent 0 đối với Resume**: Agent 0 tuyệt đối không thể gọi resume qua bridge (yêu cầu xác thực token của dashboard web và cơ chế giới hạn tần suất OPEN_INTERVAL). Mọi hành động resume đều được ghi nhận vào nhật ký kiểm toán.
