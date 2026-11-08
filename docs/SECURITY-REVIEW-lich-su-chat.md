# Báo Cáo Đánh Giá An Ninh Độc Lập: Tính Năng Chat History & Session Resume

**Dự án**: Agent Orchestrator  
**Tính năng**: Chat History (Lịch sử hội thoại) & Session Resume (Mở lại phiên)  
**Ngày thực hiện**: 08/11/2026  
**Phạm vi đánh giá**: Toàn bộ diff của tính năng Chat History so với nhánh nền tảng `chore/pre-history-baseline`.

---

## 1. Tóm tắt điều hành (Executive Summary)

Tính năng **Chat History & Session Resume** bổ sung khả năng theo dõi tiến trình (Transcript logging) và khôi phục ngữ cảnh (Session Resume) cho các mô hình tương tác (Claude Code, OpenAI Codex, Antigravity). Do tính năng này xử lý trực tiếp các phiên làm việc của dòng lệnh hệ điều hành (ConPTY), nhật ký chứa thông tin trao đổi, và nhận lệnh gọi từ giao diện web, một đợt đánh giá an ninh độc lập đã được thực hiện nhằm rà soát toàn diện các bề mặt tấn công tiềm ẩn.

**Kết luận an ninh**: Hệ thống áp dụng triệt để nguyên tắc phòng thủ theo chiều sâu (Defense-in-Depth). Không phát hiện lỗ hổng nghiêm trọng (Critical/High). Tất cả các rủi ro về leo thang đặc quyền, rò rỉ secret, injection dòng lệnh, và duyệt thư mục trái phép đều được kiểm soát bởi các rào chắn kỹ thuật độc lập.

---

## 2. Bảng ma trận mối đe dọa (Threat Matrix)

| ID | Mối đe dọa (Threat) | Mức độ nghiêm trọng (Severity) | Khả năng xảy ra (Likelihood) | Biện pháp giảm thiểu (Mitigation) | Trạng thái (Status) |
|---|---|---|---|---|---|
| **TH-01** | **Path Traversal qua API đọc Transcript**: Kẻ tấn công truyền `id` chứa `../` hoặc đường dẫn tuyệt đối để đọc file nhạy cảm trên máy chủ. | **High** | Thấp | ID được tra cứu qua bảng SQLite; đường dẫn lấy từ bản ghi nội bộ và được kiểm tra nghiêm ngặt bằng `inside(log_path, transcripts_root)`. | **ĐÃ GIẢI QUYẾT** |
| **TH-02** | **CWD Injection & UNC Path**: Mở lại phiên với thư mục độc hại hoặc đường dẫn mạng UNC (`\\attacker\share`) nhằm đánh cắp NTLM hash hoặc thực thi mã ngoài phạm vi. | **High** | Thấp | Hàm `validate_cwd()` giải quyết đường dẫn (`Path.resolve()`), từ chối symlink, cấm UNC và chỉ cho phép thư mục nằm trong danh sách `repos` hoặc `worktrees/<task_id>`. | **ĐÃ GIẢI QUYẾT** |
| **TH-03** | **Argv Injection qua Session ID**: Kẻ tấn công chèn flag (`--dangerously-skip-permissions`, `--profile`) hoặc khoảng trắng vào `session_id`. | **Critical** | Thấp | Kiểm tra regex nghiêm ngặt `SESSION = re.compile(r'^[a-zA-Z0-9_\-]{8,64}$')` trước khi ghép vào argv. Từ chối mọi chuỗi có dấu cách hoặc ký tự đặc biệt. | **ĐÃ GIẢI QUYẾT** |
| **TH-04** | **Lộ lọt Token / Khóa bí mật trong Transcript**: Output của mô hình hoặc lệnh người dùng chứa API keys, token OAuth, Bearer token ghi vào file log dạng văn bản thô. | **High** | Cao | Lọc tự động trước khi ghi đĩa bằng bộ regex `SECRET_PATTERNS` (hỗ trợ `sk-ant-*`, `sk-*`, `ghp_*`, `Bearer ...`, `api_key=...`), thay bằng `[REDACTED]`. | **ĐÃ GIẢI QUYẾT** |
| **TH-05** | **Cross-Site Scripting (XSS) trên Web Dashboard**: Tên hội thoại hoặc nội dung transcript chứa thẻ `<script>` hoặc mã HTML độc hại thực thi trong trình duyệt. | **Medium** | Trung bình | Giao diện sử dụng hàm `esc()` cho toàn bộ thuộc tính HTML và gán nội dung transcript qua thuộc tính `.textContent` an toàn. Tuyệt đối không dùng `innerHTML` với nội dung từ transcript. | **ĐÃ GIẢI QUYẾT** |
| **TH-06** | **CSRF & DNS Rebinding trên API Resume**: Trang web độc hại từ trình duyệt người dùng kích hoạt POST `/api/conversations/<id>/resume` qua cross-origin request. | **High** | Trung bình | Kiểm tra `Authorization: Bearer <token>` ngẫu nhiên 256-bit tạo mới mỗi phiên server; kiểm tra chặt chẽ header `Origin` khớp với loopback authority. | **ĐÃ GIẢI QUYẾT** |
| **TH-07** | **Leo thang đặc quyền từ Agent 0 qua Bridge**: Agent 0 thông qua kết nối MCP bridge gọi lệnh resume để khởi động tiến trình tùy ý hoặc chiếm quyền điều khiển. | **High** | Thấp | Cầu nối bridge chỉ cấp quyền đọc hạn chế và gửi input có kiểm toán; tuyệt đối không cung cấp endpoint resume trên bridge (trả về 401/404 nếu gọi). | **ĐÃ GIẢI QUYẾT** |
| **TH-08** | **Tấn công cạn kiệt tài nguyên (DoS) qua File Transcript**: Ghi liên tục log làm đầy ổ cứng hoặc tiêu tốn bộ nhớ RAM. | **Medium** | Trung bình | Giới hạn cứng 5 MB mỗi file (tự động cắt tỉa head-truncation giữ lại 80% mới nhất) và giới hạn 100 MB toàn thư mục transcripts (tự động xóa file cũ nhất). | **ĐÃ GIẢI QUYẾT** |

---

## 3. Phân tích chi tiết từng bề mặt tấn công

### 3.1. Kiểm soát đường dẫn (Path Traversal & UNC Paths)
- **Cơ chế đọc Transcript**: Endpoint `GET /api/conversations/<id>/transcript` nhận tham số `<id>` từ URL. Hệ thống sử dụng `<id>` để truy vấn cơ sở dữ liệu SQLite cục bộ `db.conversation_get(cid)`. Đường dẫn file được lưu trong cột `transcript_path`. Backend tiến hành chuẩn hóa `Path(raw_path).resolve()` và kiểm tra điều kiện con `inside(log_path, transcripts_root)`. Nếu đường dẫn nằm ngoài thư mục `<state>/transcripts/`, yêu cầu lập tức bị từ chối và trả về kết quả rỗng.
- **Xác thực thư mục làm việc (CWD)**: Tại `POST /api/conversations/<id>/resume`, thư mục `conv['cwd']` được đưa qua hàm `validate_cwd(cwd_path, task_id)`.
  + `Path(cwd_path).resolve()` triệt tiêu các đoạn `..` tương đối.
  + Kiểm tra `not p.is_dir() or p.is_symlink()` để loại bỏ symlink và junction points độc hại.
  + Nếu có `task_id`, `p` bắt buộc phải trùng khớp tuyệt đối với `(state / 'worktrees' / task_id).resolve()`.
  + Nếu không có `task_id`, `p` bắt buộc phải thuộc danh sách `allowed = [Path(r).resolve() for r in cfg.repos.values()]`.
  + **Đường dẫn mạng UNC (Windows UNC)**: Các đường dẫn dạng `\\attacker-host\share` không nằm trong danh sách thư mục dự án được cấu hình trước, do đó bị chặn hoàn toàn, ngăn ngừa tấn công rò rỉ NTLM Hash qua SMB.

### 3.2. Chống tiêm tham số dòng lệnh (Argv Injection)
- Khi khôi phục phiên (`claude --resume <session_id>` hoặc `codex resume <session_id>`), giá trị `session_id` được truyền trực tiếp vào danh sách argv của tiến trình con thông qua ConPTY API (không qua bất kỳ shell trung gian nào như `cmd.exe` hay `powershell.exe`).
- Trước khi đưa vào argv, `session_id` được thẩm định nghiêm ngặt qua biểu thức chính quy:
  ```python
  SESSION = re.compile(r'^[a-zA-Z0-9_\-]{8,64}$')
  ```
  Bất kỳ giá trị nào chứa khoảng trắng, dấu nháy, dấu gạch chéo, hoặc ký tự điều khiển đều bị từ chối ngay lập tức với lỗi `OrchError('Invalid session id')`. Điều này triệt tiêu hoàn toàn nguy cơ chèn cờ nguy hiểm như `--dangerously-skip-permissions`.

### 3.3. Lọc chuỗi nhạy cảm và che giấu bí mật (Token/Secret Redaction)
- Trong mô-đun `transcripts.py`, dữ liệu văn bản từ terminal được xử lý qua hàm `sanitize_for_transcript(text)` trước khi ghi vào đĩa:
  1. Loại bỏ toàn bộ mã điều khiển màu sắc ANSI escape sequences (`strip_ansi`).
  2. Chuẩn hóa xuống dòng và loại bỏ ký tự điều khiển C0/C1 ngoại trừ xuống dòng.
  3. Áp dụng quy tắc Regex `SECRET_PATTERNS`:
     - Bearer tokens: `(?i)\b(bearer\s+)[a-zA-Z0-9_\-\.]{8,}` -> `Bearer [REDACTED]`
     - Khóa OpenAI: `\b(sk-[a-zA-Z0-9_\-]{20,})\b` -> `[REDACTED]`
     - Khóa Anthropic: `\b(sk-ant-[a-zA-Z0-9_\-]{16,})\b` -> `[REDACTED]`
     - GitHub Personal Access Tokens: `\b(gh[pousr]_[a-zA-Z0-9]{20,})\b` -> `[REDACTED]`
     - Gán giá trị bí mật: `(api_key|token|secret|password) = "..."` -> `[REDACTED]`
- **Bảo toàn khi cắt tỉa (Truncation)**: Khi file vượt quá 5 MB, hàm `truncate_file_head` chỉ cắt bỏ phần đầu file và căn chỉnh theo ranh giới dòng (`\n`), đồng thời chèn thông báo đánh dấu `[... noi dung cu da duoc luoc bo de giu gioi han 5 MB ...]`. Quy trình này không làm hỏng cấu trúc dữ liệu đã được làm mờ trước đó.

### 3.4. An toàn giao diện (Cross-Site Scripting - XSS)
- Toàn bộ các chuỗi từ cơ sở dữ liệu và API (tiêu đề hội thoại, ID, badge, trạng thái, đường dẫn repo) hiển thị trong bảng lịch sử đều đi qua hàm thoát ký tự HTML `esc()`:
  ```javascript
  const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  ```
- Cửa sổ xem lại transcript (`ao-transcript-dialog`) hiển thị nội dung log trực tiếp qua thuộc tính:
  ```javascript
  bodyEl.textContent = transcriptLines.map(...).join('\n');
  ```
  Việc sử dụng `.textContent` bảo đảm trình duyệt xử lý nội dung hoàn toàn dưới dạng văn bản thuần túy, loại trừ 100% khả năng thực thi JavaScript độc hại từ dữ liệu transcript.

### 3.5. Kiểm soát truy cập và bảo vệ API (Origin & Authentication)
- Tất cả các endpoint `/api/conversations*` đều yêu cầu xác thực bằng Bearer token (`Authorization: Bearer <token>`). Token này là chuỗi ngẫu nhiên mật mã 256-bit được tạo mới trong bộ nhớ mỗi lần máy chủ khởi động, không lưu vào file tĩnh.
- Tất cả các request có tính đột biến (mutation) hoặc truy cập dữ liệu đều kiểm tra header `Origin` khớp với `http://127.0.0.1:<port>`. Yêu cầu từ origin khác (ví dụ trang web bên ngoài mở trong trình duyệt) bị từ chối với mã lỗi HTTP 403 Forbidden.
- Cơ chế giới hạn tần suất mở terminal `OPEN_INTERVAL` (tối thiểu 2 giây giữa hai lần mở) ngăn chặn việc tấn công spam tài nguyên. Mọi hành động resume đều được ghi nhận vào `terminal-audit.jsonl` phục vụ kiểm toán an ninh.

### 3.6. Cách ly Agent 0 và phân quyền Bridge
- Dashboard cung cấp cầu nối `terminal-bridge.json` với khóa `bridge_key` dành riêng cho tiến trình MCP Agent 0 chạy nội bộ.
- Cầu nối này chỉ hỗ trợ endpoint đọc trạng thái và gửi input được kiểm soát chặt chẽ (`/api/bridge/terminals/<id>/input`).
- Các endpoint quản lý lịch sử và resume (`/api/conversations/*`) **hoàn toàn không nằm trên cầu nối bridge** và chỉ chấp nhận khóa `token` của giao diện web. Agent 0 tuyệt đối không thể tự động mở lại các phiên cũ hoặc can thiệp vào tiến trình của các agent khác.

---

## 4. Đánh giá rủi ro còn lại và khuyến nghị (Residual Risks & Recommendations)

1. **Rủi ro rò rỉ token đặc thù**: Bộ lọc secret sử dụng regex nhận diện các mẫu token phổ biến (Anthropic, OpenAI, GitHub, Bearer). Nếu người dùng sử dụng các secret không theo định dạng chuẩn (ví dụ chuỗi ngẫu nhiên tùy chỉnh không có tiền tố và không gán theo cú pháp `key=...`), chuỗi đó có thể xuất hiện trong transcript.
   - *Khuyến nghị*: Người dùng nên truyền bí mật qua biến môi trường hoặc file cấu hình riêng biệt thay vì in trực tiếp ra màn hình terminal.
2. **Quyền truy cập tệp cục bộ trên Windows**: Các file transcript được ghi với quyền tài khoản người dùng đang chạy Orchestrator. Các tiến trình khác chạy dưới cùng tài khoản Windows này vẫn có quyền đọc file.
   - *Khuyến nghị*: Không chạy Orchestrator dưới tài khoản dùng chung hoặc môi trường nhiều người dùng không tin cậy nếu có chứa dữ liệu nhạy cảm.

---
**Kết luận**: Tính năng Chat History & Session Resume đáp ứng đầy đủ các tiêu chuẩn an toàn thông tin, kiểm soát rủi ro triệt để và sẵn sàng cho môi trường làm việc thực tế.
