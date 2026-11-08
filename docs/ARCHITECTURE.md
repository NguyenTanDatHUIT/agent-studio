# Kiến trúc

Hệ thống là một máy chủ MCP bằng Python cho phép Agent 0 xếp hàng, theo dõi và duyệt các tác vụ, được lưu trong SQLite cùng nhật ký kiểm toán. Các runner (Claude, Codex) nhận tác vụ theo cơ chế atomic claim, làm việc trong worktree riêng, chạy test rồi xuất patch kèm manifest để con người tích hợp.

```text
Claude Code Agent 0
       | MCP stdio: queue/status/review/export
       v
Python MCP server -------- SQLite WAL + audit events
                                  ^ atomic claim
                         +--------+---------+
                         |                  |
                  Claude runner        Codex runner
                  restricted file      CLI workspace-write
                  tools only           sandbox
                         |                  |
                  worktree orch/A     worktree orch/B
                         +--------+---------+
                                  |
                         snapshot -> test profiles
                                  |
                       awaiting_review + patch digest
                                  |
                      Agent 0 review -> approved
                                  |
                         patch + manifest export
                                  |
                     Human integration / tests / PR
```

MCP chỉ làm thao tác ngắn; không block kết nối bằng một CLI AI chạy lâu.
Runner là process foreground riêng, có thể chạy nhiều process. SQLite transaction
`BEGIN IMMEDIATE` claim một task; khóa file OS theo task bảo vệ runner/review/export.
Lock được OS nhả khi runner chết. Không dùng cơ chế "lease hết hạn rồi tự chạy lại"
vì có thể khiến hai model chạy cùng worktree hoặc tính phí hai lần.

Mỗi task lưu base SHA và main/master refs lúc enqueue. Worktree tạo nhánh `orch/<id>`
nhưng không commit. Snapshot tạo index riêng ở state, hash byte file, ghi Git tree,
lấy diff base→tree. Test chạy trên đúng worktree; snapshot sau test phải trùng trước.
SHA-256 patch được dùng trong review. Review/export đều kiểm tra snapshot và refs
lại. Git tree objects được thêm vào object database; không sửa index thật hoặc
working copy gốc. Có thể phát sinh unreachable tree/blob objects chờ Git GC bình thường.

Không có ghép kết quả tự động. Hai patch cùng base có thể conflict dù scope khác
nếu phụ thuộc logic. Người dùng tích hợp trên staging và test lại. `approved` không
phải `merged`, cũng không có bảo đảm xác minh reviewer con người.

State layout:

```text
queue.sqlite3            tasks + events (WAL/SHM khi có kết nối)
empty-hooks/             hooks vô hiệu hóa cho Git của orchestrator
worktrees/<id>/          linked Git worktree
runs/<id>.lock           kernel byte/file lock
runs/<id>/worker/        bounded raw stdout/stderr
runs/<id>/test-NAME/     bounded test stdout/stderr
exports/<id>/            approved changes.patch + manifest.json
```

MCP tools:

| Tool | Vai trò |
|---|---|
| enqueue_task | Queue task có scope và tên test profile. `provider` tạo agent mới; `agent=N` giao việc tiếp cho agent đó; `remember` ghi đè nhớ ngữ cảnh cho lần đó |
| list_agents | Agent đánh số: loại, nhớ ngữ cảnh, task hiện tại, vòng, bận/rảnh |
| list_tasks | Tối đa 200 task gần đây |
| get_task | Trạng thái và kết quả, không lặp full prompt |
| get_events | 100 event/trang, dùng seq làm after cursor |
| cancel_task | Cooperative cancellation + dừng process tree |
| review_bundle | Diff có giới hạn, test evidence, digest |
| record_review | approve/request_changes gắn digest |
| export_patch | Xuất artifact của task approved |

CLI thêm init, doctor, worker và abandon. Config không sửa qua tool. SQLite chứa
full task prompt và raw model summary; cần bảo vệ quyền truy cập, dung lượng và
retention theo yêu cầu dự án. Không có encryption hoặc log rotation toàn state.

## Agent đánh số và làm tiếp (nhớ ngữ cảnh)

Bảng `agents` (SQLite, `AUTOINCREMENT`) cấp số `codex 1`, `claude 2`... chung cho terminal tương tác và agent hàng đợi,
an toàn giữa tiến trình web và MCP, không dùng lại số. Mỗi agent hàng đợi trỏ tới một task "hiện tại"
(`thread_task`) và lưu `session_id` của CLI.

`enqueue_task(agent=N)` với nhớ ngữ cảnh bật (mặc định) chuyển task hiện tại từ trạng thái đã xong
(`awaiting_review`, `changes_requested`, `failed`, `approved`) về `queued` ở "vòng" kế tiếp. Cùng task ID, nhánh và worktree:
Claude gắn phiên theo thư mục làm việc nên chỉ cùng worktree mới làm tiếp được phiên cũ, và digest vẫn tính so với commit gốc.
Runner chạy `claude --resume <id>` hoặc `codex exec resume <id>`; nếu thất bại thì chạy lại phiên mới trong cùng worktree
kèm tóm tắt các vòng trước (`resume_failed`). Log vòng cũ được giữ ở `worker-r1`, `test-<tên>-r1`. Tắt nhớ ngữ cảnh thì task
mới bắt đầu từ commit gốc với phiên ephemeral như trước.
