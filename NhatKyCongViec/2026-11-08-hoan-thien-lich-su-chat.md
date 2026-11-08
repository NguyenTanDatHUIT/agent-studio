# Nhật Ký Công Việc: Hoàn Thiện Tính Năng Chat History & Session Resume

**Ngày thực hiện**: 08/11/2026  
**Chế độ thực thi**: Chế độ tự chạy qua đêm (Autonomous Execution)  
**Tác vụ gốc**: `PROMPT-hoan-thien-lich-su-chat.md`  
**Nhánh làm việc**: `feat/chat-history-clean` (phân nhánh từ `chore/pre-history-baseline`)

---

## 1. Tóm Tắt Kết Quả Toàn Diện (Executive Summary)

1. **Giai đoạn 1 — Làm sạch lịch sử Git**:
   - Tạo tag an toàn `backup/chat-history-before-cleanup` và `backup/full-state-at-start`.
   - Tạo nhánh `chore/pre-history-baseline` chứa trọn vẹn toàn bộ các tính năng trước đó (đánh số agent, taskview, workflow nhiều repo, layout UI), vượt qua 100% kiểm thử (153/153 Python tests, 2 UI tests).
   - Tách và đưa tính năng Chat History lên nhánh `feat/chat-history-clean` với cấu trúc commit rõ ràng, sạch sẽ.
   - Xác minh: `git diff chore/pre-history-baseline...feat/chat-history-clean` chỉ chứa DUY NHẤT các tệp tin liên quan đến Chat History.
2. **Giai đoạn 2 — Sửa triệt để quét session của Codex**:
   - Bổ sung quét mở rộng đa ngày (hôm qua, hôm nay, ngày mai) và đa múi giờ (Local Time và UTC).
   - Chuẩn hóa CWD và lọc file có `st_mtime >= started_time - 5.0s`.
   - Cơ chế chọn file có `st_mtime` mới nhất và retry backoff lũy tiến `[200ms, 400ms, 800ms]`.
   - Bổ sung 3 unit tests trong `tests/test_history.py` (vượt qua 28/28 tests).
3. **Giai đoạn 3 — Kiểm thử tích hợp CLI thật (Nhóm E)**:
   - Phát hiện 3 CLI: Claude Code 2.1.319, Codex CLI 0.166.0, Antigravity 1.5.3.
   - Claude Code: **PASS** (chạy native `claude.exe`, render TUI qua ConPTY, lưu `session_id`, resume API hoạt động).
   - Antigravity: **PASS** (chạy `agy.exe`, lưu conversation, tạo transcript đầy đủ 41 dòng banner).
   - OpenAI Codex: Ghi nhận trung thực **CHƯA KIỂM TRA THẬT** (tài khoản ChatGPT hiện tại gặp lỗi model).
4. **Giai đoạn 4 — Thử nghiệm tải và kiểm thử độ bền (Nhóm F)**:
   - Xây dựng `tools/stress_transcripts.py`.
   - 15 terminal threads ghi đồng thời đạt thông lượng **703.9 lines/giây**.
   - Cắt tỉa đầu file khi chạm 5 MB, thu hồi thư mục khi chạm 100 MB.
   - Độ trễ đọc phân trang: **0.42 ms** (ngưỡng < 50 ms).
   - Tự phục hồi sau crash, không làm hỏng cấu trúc file UTF-8.
5. **Giai đoạn 5 — Đánh giá an ninh độc lập (Nhóm G)**:
   - Rà soát toàn bộ bề mặt tấn công: Path traversal, UNC paths, Argv injection, Secret leakage, XSS, Origin/CORS, Bridge isolation.
   - Thêm lớp bảo vệ `inside(log_path, trans_root)` trong `read_transcript`.
   - Hoàn thành báo cáo an ninh tại `docs/SECURITY-REVIEW-lich-su-chat.md`.
6. **Giai đoạn 6 — Tài liệu hóa toàn diện**:
   - Viết mới `docs/HUONG-DAN-LICH-SU-CHAT.md` (cho người dùng).
   - Viết mới `docs/KIEN-TRUC-LICH-SU-CHAT.md` (cho lập trình viên).
   - Viết mới `docs/BAO-CAO-KIEM-THU-lich-su-chat.md` (báo cáo kiểm thử tổng thể).
   - Cập nhật `README.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/WEB-APP.md`.

---

## 2. Bảng Theo Dõi Tiến Trình Chi Tiết

| Giai đoạn | Nội dung công việc | Trạng thái | Commit / Kết quả |
|---|---|:---:|---|
| **1.1** | Đánh dấu backup tags và snapshot worktree | **HOÀN THÀNH** | `backup/chat-history-before-cleanup`, `backup/full-state-at-start` |
| **1.2** | Đo lường baseline kiểm thử ban đầu | **HOÀN THÀNH** | 153/153 Python tests OK, 2 UI tests OK |
| **1.3** | Tạo nhánh `chore/pre-history-baseline` | **HOÀN THÀNH** | Commit `7c8062a` (28 files changed) |
| **1.4** | Tái cấu trúc Chat History lên `feat/chat-history-clean` | **HOÀN THÀNH** | 4 commits sạch: `0f18af6`, `87c76f1`, `98a272f`, `cf8a7f6` |
| **2** | Sửa quét Codex đa ngày, múi giờ và retry backoff | **HOÀN THÀNH** | Commit `e809af3`, 28/28 test_history PASS |
| **3** | Smoke test tích hợp CLI thật (Claude, Codex, agy) | **HOÀN THÀNH** | Claude PASS, agy PASS, Codex CHƯA KIỂM TRA THẬT |
| **4** | Stress test & độ bền (`tools/stress_transcripts.py`) | **HOÀN THÀNH** | Commit `8f9357b`, 703 lines/s, latency 0.42ms, exit 0 |
| **5** | Đánh giá an ninh độc lập & `inside()` boundary check | **HOÀN THÀNH** | Commit `6ce135f`, `docs/SECURITY-REVIEW-lich-su-chat.md` |
| **6** | Viết tài liệu hướng dẫn, kiến trúc, kiểm thử, update README | **HOÀN THÀNH** | Đầy đủ 3 tài liệu mới và 4 tài liệu cập nhật |
| **7** | Nghiệm thu cuối cùng và dọn dẹp môi trường | **HOÀN THÀNH** | Toàn bộ test suite xanh, working tree sạch |

---

## 3. Các Quyết Định Kỹ Thuật Đáng Chú Ý

1. **Khắc phục lỗi ngắt kết nối TCP RST (`WinError 10053`) trên Windows**:
   Trong `agent_orchestrator/web.py`, khi request body vượt quá giới hạn 200 KB, phương thức `read_json` trước đây trả về HTTP 413 và đóng socket ngay lập tức. Trên Windows, việc đóng socket khi còn dữ liệu chưa đọc trong receive buffer sẽ kích hoạt gói tin TCP RST, làm hủy kết nối của client trước khi kịp nhận phản hồi. Giải pháp: Thêm vòng lặp drain an toàn (tối đa 1 MB) để tiêu thụ hết dữ liệu trong buffer trước khi trả lời 413.
2. **Chiến lược phân tách nhánh Git an toàn**:
   Thay vì cherry-pick từng phần code đan xen trong các file dùng chung (`terminals.py`, `web.py`, `app.js`), giải pháp tạo nhánh baseline `chore/pre-history-baseline` tập hợp trọn vẹn phần code tính năng trước, sau đó đưa chat history lên `feat/chat-history-clean` đã bảo đảm tính toàn vẹn cú pháp và giúp `git diff` giữa hai nhánh sạch tuyệt đối.
3. **Thực thi CLI thật trên Windows tuân thủ bảo mật Orchestrator**:
   Orchestrator nghiêm cấm chạy qua shell scripts hoặc shim files (`.cmd`, `.bat`, `.ps1`) để ngăn ngừa shell injection. Khi chạy smoke test thực tế với CLI thật, hệ thống trỏ trực tiếp vào native binaries: `claude.exe`, `node.exe codex.js`, và `agy.exe`.
4. **Phòng vệ theo chiều sâu cho Transcript Reading**:
   Thêm kiểm tra `inside(log_path, trans_root)` trong `read_transcript`, đảm bảo kể cả khi dữ liệu trong cơ sở dữ liệu bị can thiệp trái phép, máy chủ web vẫn không thể đọc bất kỳ tệp tin nào ngoài thư mục `transcripts/`.

---

## 4. Danh Sách Commits Trên Nhánh `feat/chat-history-clean`

```text
6ce135f docs(security): báo cáo đánh giá an ninh độc lập cho chat history
8f9357b test(stress): công cụ stress test và đo đạc độ bền transcripts
e809af3 fix(codex): quét session đa ngày, đa timezone và retry backoff
cf8a7f6 docs(history): tài liệu kiến trúc, web app và nhật ký chat history
98a272f feat(history): bước 5 - UI lịch sử chat và xem lại transcript
87c76f1 feat(history): bước 2, 3, 4 - ghi bản ghi màn hình, resume thật và API web
0f18af6 feat(history): bước 1 - bảng conversations và phương thức lưu trữ trong store.py
```

---

## 5. Hướng Dẫn Kiểm Tra Lại (Reproducibility)

```powershell
# 1. Kiểm tra diff tinh gọn (chỉ chứa các file chat history)
git diff --stat chore/pre-history-baseline...feat/chat-history-clean

# 2. Chạy toàn bộ unit test Python (bao gồm test_history)
.\.runtime\python\python.exe -m unittest discover -s tests -p "test_*.py"

# 3. Chạy test giao diện Web
$env:NODE_PATH="C:\Users\tsmda\AppData\Local\Programs\Antigravity IDE\resources\app\node_modules"
node tests/flow_ui.cjs
node tests/layout_ui.cjs

# 4. Chạy công cụ stress test và kiểm tra độ bền
.\.runtime\python\python.exe tools/stress_transcripts.py
```
