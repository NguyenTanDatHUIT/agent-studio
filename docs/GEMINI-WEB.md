# Provider `gemini_web`: điều khiển tab Google Gemini qua tiện ích trình duyệt

Cho phép Agent Studio dùng tab `https://gemini.google.com` đang đăng nhập của chủ máy như một agent: đọc, sửa tệp trong repo, báo kết quả trên cửa sổ CMD, hoặc nhận task hàng đợi trong worktree riêng (qua cổng duyệt như claude/codex).

Trạng thái (2026-11-12): đã triển khai, 12 test trong `tests/test_gemini_bridge.py` đạt, toàn bộ bộ test (302) đạt ở lần chạy gần nhất. **Đã chạy thật với tab Gemini** ở chế độ cửa sổ CMD (đọc tệp trong repo thành công). **Chưa thử**: giao việc qua hàng đợi với Gemini thật, thao tác sửa/ghi tệp với Gemini thật, nhiều cửa sổ xen kẽ. Nhật ký chi tiết: `NhatKyCongViec/2026-11-12-gemini-web-bridge.md`.

```
Dashboard / Agent 0 / Runner ──► GeminiBridgeHub (127.0.0.1:<port>/api/gemini-bridge/*)
                                      ▲  long-poll /poll + /reply (khóa X-Gemini-Bridge-Key)
                                      ▼
                         Tiện ích Chrome/Edge (browser_extension/) ◄──► tab gemini.google.com
```

## Bật và ghép đôi

1. Trong tệp cấu hình chủ máy (máy này: `C:\AgentControl\studio.json`, shortcut `Agent Studio.lnk` chạy `Start-AgentStudio.cmd C:\AgentControl\studio.json`), mục `providers`, thêm (và `acknowledge_local_execution: true`):
   `"gemini_web": {"command": [], "model": "gemini-web", "enabled": true, "max_turns": 12}`.
   `enabled` phải là `true` rõ ràng; thiếu thì provider tắt. Nút **Gemini** trên thanh CMD cũng bật/tắt được, nhưng chỉ trong bộ nhớ (không ghi lại tệp cấu hình). Server chỉ đọc cấu hình lúc khởi động: sửa tệp xong phải khởi động lại Agent Studio.
2. Nạp tiện ích: `chrome://extensions` → Chế độ nhà phát triển → Tải tiện ích đã giải nén → chọn thư mục `browser_extension/`. Sau khi sửa mã tiện ích phải bấm **tải lại** ở đó.
3. Bấm nút **Gemini** trên thanh CMD, sao chép chuỗi ghép đôi `http://127.0.0.1:<port>|<khóa>`.
4. Mở `gemini.google.com/app` (đã đăng nhập), bấm biểu tượng tiện ích, dán chuỗi, **Lưu & Kết nối**. Chấm trong hộp thoại cầu nối chuyển xanh khi tiện ích đã kết nối.

**Khóa cầu nối đổi mỗi lần khởi động Agent Studio**, nên phải dán lại chuỗi mới vào tiện ích.

## Cách dùng

- **Cửa sổ CMD**: Thêm CMD → Gemini Web (trình duyệt). Gõ yêu cầu; lệnh nội bộ `/help`, `/status`, `/tools on|off`, `/new` (đoạn chat mới), `/clear`. Nhấp đúp vào dòng mã/đường dẫn trên tiêu đề cửa sổ để sao chép mã cửa sổ (ví dụ `gemini_web-1`).
- **Hàng đợi**: `enqueue_task` với `provider: "gemini_web"`, `allow_paths`, `tests`. Worktree tách riêng, Gemini sửa tệp, test chạy, rồi `awaiting_review`. Phần sau đó giữ nguyên cổng duyệt hiện có. `open_terminal` cũng nhận `gemini_web`. Số công cụ MCP vẫn 19 (test cứng).
- **Nhiều cửa sổ**: mở được nhiều cửa sổ `gemini_web-N`, nhưng chúng **dùng chung một hàng chờ và một tab Gemini (tab đầu tiên)**; yêu cầu chạy tuần tự, không song song, và tiện ích điều hướng tab sang đúng hội thoại của từng cửa sổ (tải lại trang, chậm).

## Giao thức công cụ (đã đổi so với bản đầu)

Gemini web không chạm được ổ cứng, nên mỗi cửa sổ gửi kèm một chỉ dẫn hệ thống ở lượt đầu (`build_coding_system_prompt`). Gemini xuất **mỗi lệnh là một khối mã ```` ```json ````** chứa đúng một đối tượng, ví dụ `{"action": "read_file", "path": "docs/GEMINI-WEB.md", "start_line": 1, "end_line": 200}`. Các action: `list_files`, `read_file`, `replace_in_file`, `write_file`, `finish_task`. Agent Studio thực thi tại máy rồi gửi kết quả trong `[AO_TOOL_RESULT] ... [/AO_TOOL_RESULT]` ở lượt sau, tối đa `max_turns` lượt (1 đến 30).

Cách bộ đọc (`parse_tool_calls`) lấy lệnh, theo thứ tự:
1. Cú pháp cũ `<<<AO_TOOL {json} AO_TOOL>>>` (vẫn nhận).
2. Khối ```` ```json ```` trong chính câu trả lời.
3. `blocks`: văn bản gốc của các phần tử `<pre>` mà tiện ích gửi kèm (`extractCodeBlocks`).
4. Dự phòng: quét văn bản tìm đối tượng JSON bắt đầu bằng `{"action":`, bỏ qua nhãn như `JSON` mà trang Gemini hiển thị trước khối mã, và bỏ qua phần đã nằm trong một đối tượng trước đó (để chữ giống lệnh trong nội dung tệp không thành lệnh thứ hai).

Nếu thấy dấu hiệu Gemini đã cố gọi công cụ mà không đọc được lệnh nào, bộ đọc trả `_parse_error` và vòng lặp **báo lỗi lại cho Gemini** (kèm cú pháp đúng) thay vì coi là đã xong.

**Kết quả gửi lại** (`format_tool_results`) là dòng mô tả gọn + nội dung thô, không bọc JSON có escape. Giới hạn: `MAX_READ_CHARS = 9000` ký tự mỗi `read_file` (cắt ở ranh giới dòng, kèm `next_start_line` để đọc tiếp), `MAX_FEEDBACK_CHARS = 14000` cho cả lượt gửi lại. Lý do: ô chat Gemini không nhận nổi lượt dài (~49.000 ký tự đã làm lượt gửi thất bại và treo 240 giây).

## Đường dẫn và `read_roots`

Mặc định Gemini chỉ thấy thư mục làm việc (repo của cửa sổ, hoặc worktree của task). Mọi đường dẫn phải **tương đối, dấu `/`**; `C:`, `\`, tuyệt đối, `..`, symlink, `.git`, `.claude`, `.env*`, `CLAUDE.md`, `AGENTS.md`, `.gitignore`... bị chặn (`safe_relative` trong `gitops.py`, cả đọc lẫn ghi). Lời nhắn lỗi gửi lại cho Gemini nói rõ cách sửa.

Muốn cho **đọc** (không ghi) thư mục khác, khai báo trong khối `gemini_web`:

```json
"gemini_web": { "command": [], "enabled": true, "max_turns": 12,
                "read_roots": ["C:/AgentControl/studio-state/prompts"] }
```

- Tối đa 5 thư mục tuyệt đối đang tồn tại. Chỉ `read_file` và `list_files` dùng được đường dẫn tuyệt đối, và chỉ bên trong các thư mục này. `write_file`/`replace_in_file` vẫn chỉ trong thư mục làm việc và `allow_paths`.
- Vẫn chặn symlink và các tên được bảo vệ ngay trong thư mục chỉ đọc.
- Cấu hình bị từ chối nếu thư mục là gốc ổ đĩa, chứa thư mục state hoặc tệp cấu hình, hoặc nằm trong repo. Lý do: thư mục state (`C:\AgentControl\studio-state`) có `gemini-bridge.json`, `dashboard-token`, `terminal-bridge.json`, cơ sở dữ liệu hàng đợi. Vì vậy `studio-state/verify-fn.sh` ở gốc state **không** đọc được; chép vào `prompts` hoặc vào repo.
- Mọi thứ Gemini đọc được đều được gửi sang Google.

## Ranh giới an toàn

- Cổng `/api/gemini-bridge/*` (trừ `status` và `toggle`, vốn dùng Bearer token Dashboard + Origin cùng nguồn) chỉ nhận `Origin` dạng `chrome-extension://` hoặc `moz-extension://` và khóa riêng `X-Gemini-Bridge-Key` (so bằng `hmac.compare_digest`). Provider tắt thì trả 403. Trang web bất kỳ không gọi được.
- `POST /jobs` chỉ nhận `worktree` nằm trong `<state>/worktrees` và bắt buộc `allow_paths`, để người giữ khóa không trỏ bộ thực thi vào thư mục tùy ý.
- Task hàng đợi bị khóa trong `allow_paths`; kiểm tra phạm vi, chạy test và cổng duyệt của `Engine._execute` giữ nguyên.
- Cửa sổ CMD tương tác (không có `allow_paths`) đọc và ghi được trong repo của cửa sổ đó như agent CLI khác. Coi nội dung Gemini sinh ra là không tin cậy khi nó đọc tài liệu bên ngoài.
- Chấm "rảnh" của cửa sổ Gemini (`managed_idle`) chỉ bật khi vòng trả lời và gọi công cụ thực sự kết thúc, không dựa vào việc im lặng.

## Xử lý sự cố

| Triệu chứng (popup tiện ích hoặc cửa sổ CMD) | Nguyên nhân | Cách xử lý |
|---|---|---|
| "Chưa cấu hình hoặc đang tạm dừng" | Chưa lưu chuỗi ghép đôi, hoặc bỏ tích "Kích hoạt cầu nối" | Dán chuỗi, Lưu & Kết nối |
| `HTTP 403` | Server đang chạy chưa nạp `gemini_web.enabled=true` (cấu hình chỉ đọc lúc khởi động) | Khởi động lại Agent Studio, hoặc tích công tắc trong hộp thoại Gemini |
| `HTTP 401` | Khóa trong tiện ích cũ (khóa đổi mỗi lần khởi động) | Sao chép chuỗi mới, xóa ô cũ, dán lại |
| "Gemini không nhận câu lệnh..." | Lượt gửi quá dài hoặc nút gửi bị khóa | Giảm kích thước kết quả; xem tab Gemini |
| "Gemini đang trả lời..." / "Nút gửi ... bị khóa" / "Không tìm thấy nút gửi ... [nhãn các nút]" / "Đã bấm nút gửi (và thử lại một lần)..." | Tiện ích chờ Gemini rảnh tối đa 15 giây, chờ nút gửi tối đa 12 giây (tìm nút có lớp `send-button` hoặc nhãn Send/Gửi quanh ô soạn tin, loại nút dừng/micro/thêm), bấm lại tối đa một lần nếu ô chat chưa trống. Phím Enter giả chỉ là dự phòng khi không có nút gửi và Gemini có thể bỏ qua | Xem nhãn nút trong thông báo để cập nhật `SELECTORS`/`SEND_LABEL_RE` trong `content_gemini.js`; mô phỏng: `node tests/gemini_send_sim.cjs` |
| "Quá thời gian chờ phản hồi" (240 giây) | Gemini không trả lời, hoặc bộ chọn DOM trả sai nút/nội dung | Xem tab; kiểm tra `SELECTORS` trong `content_gemini.js` |
| Tool báo `Đường dẫn ... không hợp lệ` | Đường dẫn tuyệt đối/ngoài thư mục làm việc | Dùng đường dẫn tương đối hoặc khai báo `read_roots` |
| `[Tool parse_error]` lặp lại | Gemini xuất lệnh sai cú pháp | Xem `gemini-debug/last-reply.json` (dưới) |

**Chẩn đoán**: mỗi câu trả lời thô được ghi đè vào `<state>/gemini-debug/last-reply.json` gồm `text`, `blocks`, và `html` (HTML thô của câu trả lời cuối, chỉ khi có vẻ chứa lệnh). Đây là nguồn sự thật để biết lỗi nằm ở Gemini hay ở cách trích văn bản. Bản ghi hội thoại nằm ở `<state>/transcripts/<id>.log`.

## Bản đồ mã

| Phần | Tệp |
|---|---|
| Lõi cầu nối: `parse_tool_calls`, `build_coding_system_prompt`, `WorkspaceExecutor`, `BrowserBridgeSession`, `GeminiBridgeHub`, `run_worktree_via_bridge`, `format_tool_results` | `agent_orchestrator/gemini_bridge.py` |
| Cổng HTTP và CORS cho tiện ích (`gemini_ext`, `do_OPTIONS`, `cors_gemini`), `status`/`toggle`, tệp `<state>/gemini-bridge.json` | `agent_orchestrator/web.py` |
| Xác thực khối `gemini_web`, `provider_enabled`, kiểm tra `read_roots` | `agent_orchestrator/config.py` |
| Mở cửa sổ, `managed_idle` (nhánh trong `update_interactive_idle`), `TERMINAL_AGENTS` | `agent_orchestrator/terminals.py` |
| Rẽ nhánh worker sang cầu nối, enqueue/workflow nhận `gemini_web` | `agent_orchestrator/engine.py` |
| `usage()` (`terminal_seen` theo sự kiện `turn.completed`), `session_id` | `agent_orchestrator/providers.py` |
| `probe`, runners, enum MCP, CLI | `readiness.py`, `runners.py`, `mcp.py`, `cli.py` |
| Tiện ích: poll/reply (`background.js`), điền ô chat + đọc câu trả lời + `extractCodeBlocks` (`content_gemini.js`), popup | `browser_extension/` |
| Giao diện: nút Gemini + hộp thoại ghép đôi, logo, thông báo nổi `.ao-toast`, nhấp đúp sao chép mã cửa sổ | `web_assets/app.js`, `style.css`, `index.html` |
| Test | `tests/test_gemini_bridge.py` |

## Hạn chế cần biết

- Điều khiển giao diện web Gemini bằng tiện ích dễ hỏng khi Google đổi DOM (bộ chọn ở đầu `content_gemini.js`), và có thể không phù hợp điều khoản dịch vụ của Google với tự động hóa tài khoản; xem thêm phần pháp lý trong nhật ký. Chủ máy tự chịu trách nhiệm khi bật.
- Mã gửi toàn bộ nội dung tệp Gemini đọc sang Google. Không dùng cho repo/dữ liệu có thông tin bệnh nhân thật hoặc dữ liệu khách hàng bị ràng buộc bảo mật.
- Không có số token hay chi phí (`usage.source = unavailable`).
- Tab đang dùng có thể là `gemini.google.com/u/2/app` (tài khoản số 2). Khi mở hội thoại mới hoặc cũ, mã điều hướng về `/app` (tài khoản mặc định): chưa sửa để giữ nguyên tiền tố `/u/N`.
- Đọc tệp lớn chậm: mỗi đoạn ~9000 ký tự là một lượt chờ Gemini; dễ chạm `max_turns` (tối đa 30).
- Chạy song song nhiều cửa sổ chưa hỗ trợ (cần một tab Gemini cho mỗi cửa sổ).
