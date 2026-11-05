# Chạy Agent Studio với CLI thật

## Kiểm tra nhanh trên máy này

Chạy `Start-LiveCheck.cmd` từ Explorer hoặc terminal Windows của người dùng.
Launcher dùng CLI Codex tìm được trên máy và tài khoản đã đăng nhập, có thể tiêu
thụ quota. Không dùng worker giả. Repo thử là `.local-run/live-check/repo`,
config và state nằm cạnh repo, không sửa dự án khác.

Mỗi lần mở launcher sẽ tạo tối đa một task mới nếu không có task đang chờ/chạy.
Task yêu cầu sửa phép cộng trong `calculator.py`; test cố định kiểm tra ba trường
hợp. Mở nguyên URL Dashboard có token in trong terminal, xem Nhiệm vụ → log/diff.
Khi thành công, task dừng ở chờ review; đọc diff/test rồi duyệt và xuất patch.
Ctrl+C dừng web, runner và process con của worker/test. Dữ liệu được giữ lại.

Không mở nhiều server cùng cổng 8765. Có thể chạy lệnh trực tiếp với `--port 8767`.

## Kết nối repo của bạn

Repo cần là Git repository đã có commit; config/state phải ở ngoài repo đó.
Ví dụ dùng thư mục `.local-run` bên dưới source orchestrator khi repo đích nằm nơi khác:

```powershell
# Dùng Python 3.11+ của bạn hoặc runtime sẵn có trên máy này:
$studioPython = (Resolve-Path .runtime/python/python.exe).Path
& $studioPython -m agent_orchestrator --config .local-run/myapp.json init --repo C:\Projects\MyApp --state-dir C:\AgentControl\myapp-state --detect-providers
```

Sửa `tests` trong file config thành test thực sự của dự án, ví dụ:

```json
"tests": {
  "unit": ["C:/Projects/MyApp/.venv/Scripts/python.exe", "-B", "-m", "unittest", "discover", "-s", "tests"]
}
```

Đường dẫn executable phải tồn tại. Cấu hình dùng argv, không dùng `npm.cmd`, CMD
hay PowerShell. Với Node, gọi `node.exe` cùng file JS CLI tuyệt đối.
Kiểm tra `providers.*.command`; provider không có executable đọc được sẽ để trống.
Sau khi chấp nhận chạy mã/test của repo local, đặt `acknowledge_local_execution`
thành `true`. Có thể cấu hình ngay khi init bằng `--enable-execution` và
`--test-profile 'unit=["C:/Python313/python.exe","-B","-m","unittest"]'`.

```powershell
& $studioPython -m agent_orchestrator --config .local-run/myapp.json doctor --probe --check-auth
.\Start-AgentStudio.cmd .local-run/myapp.json
```

`doctor --probe` chạy version/help để kiểm tra cờ tương thích; `--check-auth`
chạy login status, không gọi model và không trả credential. Đây chưa phải bằng
chứng task model chạy được. `doctor` không có hai cờ này giữ hành vi chỉ đọc config.

Launcher với config khởi chạy runner cho tất cả provider đã cấu hình. Không có
provider hoặc test profile, execution đang khóa hoặc CLI thiếu cờ sẽ dừng ngay.
Muốn chỉ xem dashboard, dùng CLI `web` không có `--run-workers`, hoặc PowerShell
launcher với `-MonitorOnly`. Không config vẫn chạy demo offline như trước.

```powershell
& $studioPython -m agent_orchestrator --config .local-run/myapp.json web --run-workers --port 8767
```

Dashboard phân biệt runner được web quản lý và runner mở riêng. Endpoint
`GET /api/runners` yêu cầu bearer token; không có API chạy shell/bật quyền/sửa
config. Trạng thái `busy` phản ánh thread runner đang thực hiện task, không xác
nhận model còn kết nối. Không có tự động retry task lỗi hoặc tự duyệt patch.

## Bằng chứng kiểm tra ngày 05/11/2026

- Phát hiện Codex CLI 0.166.0 tại `.codex/packages/app-server-daemon/releases`.
- `exec --help` có các cờ adapter; `login status` xác nhận đăng nhập ChatGPT.
- Đã tạo task thật `efb297e06d80496ab6b06d69`, tạo Git worktree và gọi binary
  Codex thật. CLI thoát 1 với `failed to initialize in-process app-server client:
  Access is denied. (os error 5)` trong môi trường thực thi hiện tại.
- Không có terminal result, usage hay patch model; test chức năng chưa được chạy.
  Repo chính của người dùng chưa được chọn. Claude npm bị chặn truy cập trong shell.
- Không nới quyền, sao chép credential hoặc fallback sang bypass sandbox.

Nếu gặp lỗi tương tự, đọc stderr trong task rồi chạy launcher từ phiên Windows
của tài khoản đã cài/đăng nhập CLI. Kiểm tra CLI hoạt động ở terminal đó trước;
không chạy lại task bằng worker giả để đánh dấu thành công. Nếu CLI yêu cầu
đăng nhập hoặc thiết lập sandbox Windows, hoàn tất bằng công cụ chính thức.

Tùy chọn Codex được đối chiếu với binary cục bộ và
[official OpenAI documentation](https://learn.chatgpt.com/docs/developer-commands?surface=cli).
Giới hạn thực thi local và worktree vẫn theo [SECURITY.md](../SECURITY.md).
