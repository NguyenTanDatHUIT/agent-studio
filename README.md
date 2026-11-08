# Agent Orchestrator cho Windows

**Đã có web app Agent Studio**, triển khai theo mẫu giao diện người dùng cung cấp:
cửa sổ CMD/monitor, tổng quan, luồng, nhiệm vụ, review/diff, báo cáo và tải patch.
Mở `Start-AgentStudio.cmd` để thử offline, hoặc chạy
`.\Start-AgentStudio.cmd C:\AgentControl\myapp.json` cho dự án thật.
Mở liên kết Dashboard được in trong terminal. Xem [hướng dẫn web app](docs/WEB-APP.md).

**Lịch sử chat & Mở lại phiên (Conversations & Resume):** Tra cứu lịch sử hội thoại của Agent 0 và các terminal agent, xem lại transcript chỉ đọc (lọc sạch ANSI, che giấu secret) và khôi phục ngữ cảnh làm việc thực tế (`claude --resume`, `codex resume`). Xem [Hướng dẫn Lịch sử chat](docs/HUONG-DAN-LICH-SU-CHAT.md) và [Kiến trúc kỹ thuật](docs/KIEN-TRUC-LICH-SU-CHAT.md).

**Tiếp tục chạy thật:** [hướng dẫn CLI thật](docs/LIVE-RUN.md). `Start-LiveCheck.cmd`
mở repo kiểm tra riêng bằng Codex thật; launcher với config nay chạy web kèm runner.
Đã xác minh Codex và Claude thật sửa code trên repo calculator thử riêng, chạy
3 kiểm tra chức năng đạt và dừng ở chờ review. Chưa xác minh review/export/áp
patch trên dự án thật. Xem [báo cáo Claude](NhatKyCongViec/2026-11-05-claude-live-check.md).

Python 3.11+, chỉ dùng thư viện chuẩn khi chạy. Claude Code **Agent 0** dùng MCP
để giao việc cho Claude Worker / Codex Worker, đọc kết quả, review và xuất patch.
Không cần copy/paste kết quả giữa các agent. Không có lệnh commit, merge hoặc push.

Đây là công cụ local v0.1, dành cho repository bạn tin cậy; chưa phải dịch vụ
production hay hệ thống cách ly mã độc. Đọc [SECURITY.md](SECURITY.md) trước khi bật chạy.

## Có gì trong bộ source

| Phần | Chức năng |
|---|---|
| `agent_orchestrator/cli.py` | CLI cấu hình, hàng đợi, runner, review, export, phục hồi |
| `agent_orchestrator/mcp.py` | MCP stdio JSON-RPC, 12 tools (list_agents, list_terminals, read_terminal chỉ đọc; send_to_terminal có xác nhận), bắt tay 2025-03-26 |
| `agent_orchestrator/store.py` | SQLite WAL, atomic claim, sự kiện trạng thái |
| `agent_orchestrator/transcripts.py` | Ghi bản ghi màn hình, lọc ANSI, che giấu token, giới hạn 5 MB/100 MB |
| `agent_orchestrator/gitops.py` | Nhánh/worktree riêng, snapshot qua index tạm, binary patch |
| `agent_orchestrator/process.py` | Không qua shell, timeout, cancel, log cap, Windows Job Object |
| `agent_orchestrator/providers.py` | Adapter Claude/Codex, đọc JSON usage thực tế |
| `tests/` | Unit/integration, CLI giả offline, hai runner và MCP subprocess |
| `examples/` | Cấu hình mẫu, MCP và prompt Agent 0 |
| `docs/` | Kiến trúc, nguồn tham khảo và phạm vi xác minh |

## 1. Cài đặt

Giải nén vào ví dụ `C:\Tools\agent-orchestrator`. Cần Python 3.11+ và Git for Windows
trên PATH. CLI Claude/Codex và đăng nhập cần được cài riêng theo tài khoản của bạn.
Không cần API key để chạy kiểm thử offline.

PowerShell, tại thư mục vừa giải nén:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
.\.venv\Scripts\python.exe -m agent_orchestrator --help
.\.venv\Scripts\python.exe -m unittest discover -v
```

Nếu venv chưa có setuptools phù hợp, cài `pip install "setuptools>=68"` trước
lệnh install. Có thể chạy trực tiếp `py -3 -m agent_orchestrator` tại thư mục source
mà không cài package. Dùng Python tuyệt đối trong cấu hình MCP để không phụ thuộc cwd.

## 2. Khởi tạo cấu hình ngoài repository

Ví dụ repository đã có commit: `C:\Projects\MyApp`. Cấu hình và state phải nằm ngoài
repository, không dùng chung một state cho nhiều repo. Dùng ổ đĩa local NTFS; không
dùng network share/OneDrive cho database đang chạy.

```powershell
.\.venv\Scripts\python.exe -m agent_orchestrator --config C:\AgentControl\myapp.json init --repo C:\Projects\MyApp --state-dir C:\AgentControl\myapp-state
.\.venv\Scripts\python.exe -m agent_orchestrator --config C:\AgentControl\myapp.json doctor
```

`init` không ghi đè file. `doctor` không gọi mô hình, không kiểm tra đăng nhập.
Mặc định `acknowledge_local_execution=false`, provider và test profile chưa được cấu hình.

Sửa file `C:\AgentControl\myapp.json`, dựa trên [examples/config.windows.json](examples/config.windows.json):

* `repo`, `state_dir`: đường dẫn tuyệt đối, hai cây thư mục rời nhau.
* `base_ref`: `HEAD` hoặc một nhánh local, được chốt thành commit SHA khi enqueue.
* `providers.*.command`: mảng executable + đối số cố định do chủ máy quản lý.
  Executable phải là đường dẫn tuyệt đối tồn tại. Không nhận chuỗi shell,
  `.cmd`, `.bat`, `.ps1`, PowerShell, CMD hay WSL launcher.
* Nếu cài Codex bằng npm: dùng `node.exe` và file `@openai/codex/bin/codex.js`,
  không gọi `codex.cmd`. Claude có thể dùng `claude.exe` bản native hoặc
  `node.exe` + `@anthropic-ai/claude-code/cli.js`. Tra đường dẫn thật qua
  `Get-Command node,claude,codex -All`, `npm.cmd root -g`; không đoán theo ví dụ.
* `model`: tên model bạn có quyền sử dụng, hoặc `null` để CLI tự chọn mặc định.
* `tests`: map tên profile sang argv cố định. Ví dụ `unit` chạy Python venv của
  **dự án đích**, `-m unittest discover -s tests`; test chạy với cwd là worktree.
* `agent_env_allow`: tên biến môi trường cần truyền cho worker, ví dụ
  `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, hoặc `CODEX_HOME` nếu cần home riêng.
  Không ghi giá trị key vào JSON. Worker vẫn có thể đọc home qua quyền tài khoản;
  allowlist môi trường không phải lớp bảo vệ file credential.
* Chỉ sau khi đọc giới hạn an toàn, đặt `acknowledge_local_execution=true`.

Runner không tự cài dependencies trong worktree; tạo môi trường dự án dùng chung
hoặc chuẩn bị dependencies theo quy trình của bạn trước. Không chọn test profile chỉ
in chữ "passed": profile phải kiểm tra chức năng của thay đổi.

### Yêu cầu phiên bản CLI

Adapter dùng Claude `--restricted` và `--permission-prompts none`: cần bản CLI có
các cờ này (restricted được tài liệu ghi từ v2.1.248). Claude chỉ có
`Read,Edit,Write,Glob,Grep`, `acceptEdits`, không shell, không MCP kế thừa, không
slash command. Test chạy bởi runner riêng.

Codex cần hỗ trợ `exec --json --ephemeral --ignore-user-config --ignore-rules`,
`--sandbox workspace-write`, và cấu hình `approval_policy="never"`. Sandbox
không bật network cho lệnh của model. Xác thực/gọi dịch vụ mô hình vẫn cần mạng.
User config được bỏ qua; cấu hình quản trị hoặc cấu hình dự án có thể vẫn tác động.
Không dùng profile mở rộng quyền và không tự hạ mức bảo vệ nếu CLI báo lỗi.
Kiểm tra `--help` của đúng binary trước khi dùng; CLI cũ không hỗ trợ cờ sẽ làm
task thất bại, không fallback sang chế độ không an toàn.

## 3. Nối Agent 0 với MCP

Tại terminal của Claude Code Agent 0, đăng ký MCP local (thay đường dẫn):

```powershell
claude mcp add --transport stdio --scope local agent-orchestrator -- C:\Tools\agent-orchestrator\.venv\Scripts\python.exe -m agent_orchestrator --config C:\AgentControl\myapp.json serve
```

Hoặc dùng [examples/mcp.json](examples/mcp.json) với cơ chế cấu hình MCP của client.
Kiểm tra bằng `/mcp` trong Claude Code. Chỉ cung cấp MCP này cho Agent 0; không
cung cấp cho worker. MCP không có tool shell, sửa config, bật runner hay merge.

Mở **hai terminal riêng**, chạy liên tục; Ctrl+C để dừng:

```powershell
# Terminal 1: Claude Worker
C:\Tools\agent-orchestrator\.venv\Scripts\python.exe -m agent_orchestrator --config C:\AgentControl\myapp.json worker --provider claude
```

```powershell
# Terminal 2: Codex Worker
C:\Tools\agent-orchestrator\.venv\Scripts\python.exe -m agent_orchestrator --config C:\AgentControl\myapp.json worker --provider codex
```

Hai tiến trình lấy việc bằng transaction SQLite; một task chỉ được claim một lần.
Không cần giữ cửa sổ MCP riêng: client sẽ khởi chạy `serve`. Queue chỉ chạy khi
runner do bạn mở đang hoạt động. Không có scheduler/service ẩn.

Dùng [examples/AGENT0-PROMPT.md](examples/AGENT0-PROMPT.md) làm hướng dẫn cho Agent 0:
chia task độc lập, gọi `enqueue_task`, kiểm tra trạng thái theo nhịp vừa phải,
gọi `review_bundle`, đọc code liên quan, ghi review với digest, rồi `export_patch`.
Agent 0 có thể tự duyệt review kỹ thuật; việc đưa patch vào nhánh tích hợp là
thao tác riêng của người dùng. MCP không chứng minh danh tính reviewer con người.

## 4. Quy trình CLI tương đương

```powershell
py -3 -m agent_orchestrator --config C:\AgentControl\myapp.json enqueue --provider codex --prompt-file C:\AgentControl\task.txt --allow-path src --allow-path tests --test unit
py -3 -m agent_orchestrator --config C:\AgentControl\myapp.json worker --once
py -3 -m agent_orchestrator --config C:\AgentControl\myapp.json list
py -3 -m agent_orchestrator --config C:\AgentControl\myapp.json show TASK_ID
py -3 -m agent_orchestrator --config C:\AgentControl\myapp.json review TASK_ID
py -3 -m agent_orchestrator --config C:\AgentControl\myapp.json record-review TASK_ID --verdict approve --patch-sha256 DIGEST_FROM_REVIEW --notes-file C:\AgentControl\review.txt
py -3 -m agent_orchestrator --config C:\AgentControl\myapp.json export TASK_ID
```

`TASK_ID` / `DIGEST_FROM_REVIEW` là giá trị thật do chương trình trả về. Mọi lệnh
trên phải chạy trong source directory hoặc bằng Python đã cài package.

Worktree ở `state/worktrees/<id>`, nhánh `orch/<id>`. Worker không được commit;
snapshot vẫn giữ thay đổi chưa commit, dùng **index tạm**, không stage vào index
thật. File untracked không bị ignore cũng được đưa vào patch. File bị ignore không
được tính vào patch/test digest; test không nên dựa vào artifact ignored có thể đổi.
Chỉ có scope file/thư mục cụ thể; `.` hoặc wildcard không được dùng làm toàn repo.

Trạng thái: `queued → running → awaiting_review → approved` hoặc
`changes_requested`, `failed`, `cancelled`. `approved` chỉ là review gate, không
có nghĩa đã commit/merge. Patch xuất gồm `changes.patch` và `manifest.json` ghi
base SHA, tree, SHA-256 patch, test và review.

### Tích hợp bằng người dùng

Trong repository, tự tạo một nhánh tích hợp sạch từ base SHA trong manifest,
kiểm tra patch, áp dụng, chạy lại test rồi commit/PR theo quy trình của bạn:

```powershell
git switch -c integration/task-id BASE_SHA_FROM_MANIFEST
git apply --check C:\AgentControl\myapp-state\exports\TASK_ID\changes.patch
git apply C:\AgentControl\myapp-state\exports\TASK_ID\changes.patch
# Review, run project tests, then decide whether to commit and open a PR.
```

Các task song song đều bắt đầu từ base được chốt lúc enqueue, không tự thấy thay
đổi của nhau. Nếu B phụ thuộc A, tích hợp A vào nhánh staging bằng người dùng,
đổi `base_ref` sang nhánh đó rồi enqueue B. Không tự giải conflict hay auto merge main.

## 5. Log, usage, hủy và phục hồi

* SQLite `events`: sự kiện queue/start/test/usage/review/export, thời gian UTC.
* `runs/<id>/worker/{stdout,stderr}.log` và `test-<profile>/...`: log raw,
  tối đa `output_limit_bytes` **mỗi stream**. Quá giới hạn làm task fail.
* Usage lấy từ `result.usage` của Claude hoặc `turn.completed.usage` của Codex.
  Không cộng lại các event trung gian. Cache metrics giữ nguyên tên nhà cung cấp.
  Không có usage → `source=unavailable`, số token/cost là `null`, không ước lượng.
  Chi phí chỉ ghi khi Claude CLI trả `total_cost_usd`; Codex cost thường là `null`.
* Không có budget token cứng nếu CLI không báo theo thời gian thực. Timeout là
  giới hạn wall-clock mỗi worker/test; không phải giới hạn hóa đơn. Hủy local
  process cũng không bảo đảm dịch vụ từ xa dừng tính phí ngay lập tức.
* `cancel TASK_ID`: đánh dấu yêu cầu; runner kiểm tra mỗi ~50ms khi process chạy,
  đóng process tree, giữ worktree/log. Task chưa chạy bị hủy ngay.
* Nếu process runner chết: task `running` không tự requeue, tránh trả phí lặp và
  chạy lại trên mã dang dở. Kiểm tra không còn process con, sau đó dùng
  `abandon TASK_ID` (CLI-only). Tạo task mới để thử lại.
* `request_changes`: tạo task mới với yêu cầu sửa cụ thể; không tự resume CLI và
  không tự tái dùng worktree cũ. Giữ đầy đủ dấu vết review.
* Không tự xóa worktree/nhánh/log. Sau khi lưu artifact cần thiết, bạn có thể dùng
  `git worktree remove <path>` và `git branch -d orch/<id>`; Git có thể từ chối xóa
  worktree đang bẩn. Kiểm tra nội dung trước khi quyết định xử lý.

## 6. Kiểm thử và phạm vi

```powershell
py -3 -m unittest discover -v
```

Test suite tạo Git repository tạm, gọi CLI giả bằng Python, thực thi test dự án,
kiểm tra main/index không đổi, test queue song song, review/hash gate, timeout,
cancel, output cap, argv injection và MCP qua process stdio thật. Không gọi dịch
vụ mô hình. Xem [docs/VALIDATION.md](docs/VALIDATION.md) để biết kết quả đóng gói.

Nếu TEMP của môi trường bị giới hạn, đặt `$env:TEMP` và `$env:TMP` vào một thư mục
scratch có quyền ghi trước khi chạy test. Không đặt thư mục tạm trong repo đích.

Giới hạn chủ ý: file tối đa 10MB, tổng file snapshot tối đa 50MB, tối đa 100000
entry; không hỗ trợ submodule, symlink/junction/reparse point, Git LFS/filter
smudge/clean hay tên file có ký tự điều khiển. Snapshot đọc byte gốc, không chạy
filter của repository; repo-local filter config bị từ chối trước checkout. Nếu
attributes/encoding làm checkout đổi byte baseline thì task dừng trước worker.
Repo lớn cần điều chỉnh thiết kế snapshot trước khi dùng.
MCP hỗ trợ stdio phiên bản 2025-03-26 và thương lượng fallback về phiên bản này;
không hỗ trợ HTTP, OAuth, resources, prompts, streaming progress hoặc batch JSON-RPC.

## Tài liệu

[SECURITY.md](SECURITY.md) · [Kiến trúc](docs/ARCHITECTURE.md) ·
[Nguồn chính thức](docs/SOURCES.md) · [Xác minh](docs/VALIDATION.md)
