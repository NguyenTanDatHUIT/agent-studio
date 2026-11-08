# Nhật ký công việc — Agent đánh số, nhớ ngữ cảnh, cài đặt cửa sổ, ô nhập hàng × cột

**Ngày:** 07/11/2026
**Dự án:** `C:\CongViec\agent\agent-orchestrator`
**Trạng thái bàn giao:** Code và test xong, chưa commit. Chưa thử làm tiếp bằng Claude/Codex thật (chỉ có fake agent) và chưa xem giao diện mới trong trình duyệt thật (chỉ jsdom).

## Yêu cầu của người dùng

1. Task xong rồi muốn nó làm tiếp mà giữ ngữ cảnh; làm cả cách A (làm tiếp phiên thật) và B (dự phòng).
2. ID đơn giản là số nguyên tăng dần, chung cho mọi agent (`codex 1`, `claude 2`), giữ lại khi khởi động lại, gọi bằng "codex 1 làm ...".
3. Biểu tượng cài đặt trên cửa sổ có tick "nhớ ngữ cảnh sau mỗi task", mở rộng được; Agent 0 yêu cầu nhớ/không nhớ từng lần, mặc định nhớ.
4. Ô nhập tay hàng × cột (`1x2`, `1 x 2`), cùng kích thước với các nút.

## Thiết kế

- **Số agent**: bảng `agents` (`AUTOINCREMENT`) trong `queue.sqlite3`, dùng chung cho terminal tương tác và agent hàng đợi, an toàn giữa tiến trình web và MCP. Bảng `settings` giữ mặc định chung. Cột `agent` thêm vào `tasks` bằng migration tự động.
- **Làm tiếp = vòng mới của cùng task** (cùng ID, nhánh, worktree): Claude gắn phiên theo thư mục làm việc nên worktree mới sẽ không tìm thấy phiên cũ. Digest vẫn tính so với commit gốc; `store.requeue` đưa task về `queued` một cách atomic.
- **A**: `claude --resume <id>` / `codex exec resume <id>`. Bỏ `--ephemeral`, `--no-session-persistence` cho agent đang nhớ. `codex exec resume` không có `--sandbox` nên dùng `-c sandbox_mode="workspace-write"` (thất bại an toàn nếu bị bỏ qua).
- **B**: nếu resume lỗi, chạy lại phiên mới trong cùng worktree kèm tóm tắt các vòng trước, ghi sự kiện `resume_failed`.
- **Cài đặt**: danh sách `settingDefs` trong `app.js`, khóa được phép ở `web.py` (`remember_context` cho agent, `default_remember` chung).
- **Cửa sổ**: một cửa sổ chỉ đọc cho mỗi agent hàng đợi (thay cho một cửa sổ mỗi task), không tự đóng khi task xong ("Sẵn sàng"), mở lại khi có vòng mới.

## Việc đã làm

`store.py`, `providers.py`, `engine.py`, `terminals.py` (`AgentView`), `web.py`, `mcp.py` (tool `list_agents`, `enqueue_task` nhận `agent`/`remember`), `cli.py`, `app.js`, `index.html`, `style.css`, hướng dẫn Agent 0, `SECURITY.md`, `docs/WEB-APP.md`, `docs/ARCHITECTURE.md`, `README.md`.

## Lỗi phát hiện khi làm

- Cửa sổ mới có `idle=True` nên có thể bị dọn nhầm khi đầy 12 cửa sổ; đóng cửa sổ ngay sau khi mở làm nó tự mở lại (khóa đóng sai). Đã sửa.
- Giá trị `"__proto__"` trong localStorage làm bố cục `undefined` (lỗi có sẵn của `layouts[pref.layout]`, cũng ở `pages[pref.page]`). Đã sửa bằng `Object.hasOwn`.
- Script thay thế văn bản không báo lỗi khi không khớp: phải kiểm tra bằng test, không tin im lặng.

## Kiểm thử

- 135 test Python (gồm 28 trong `tests/test_agents.py`, 42 trong `tests/test_taskview.py`), pass; một lỗi `ConnectionAbortedError` chập chờn có sẵn ở `test_validation_and_no_arbitrary_execution_endpoint` (gửi thân 200 KB bị trả 413 và đóng kết nối), khoảng một nửa số lần chạy.
- `tests/flow_ui.cjs` và `tests/layout_ui.cjs` (jsdom) pass; đã thử đột biến giới hạn bố cục để chắc test bắt được.
- `tests/web_ui.cjs` vẫn lỗi sẵn từ trước, không sửa.

## Việc còn lại / quyết định mở

- Sơ đồ Luồng tự động vẫn chia hai làn theo model (Claude/Codex); chưa vẽ một làn cho mỗi agent đánh số.
- Task tạo trước tính năng này (ví dụ `1b4bc139`) không có số agent nên chưa làm tiếp được; cần một lần gán số cho chúng nếu muốn.
- Chưa chạy thật resume với Claude/Codex (tốn token và cần tài khoản); nên thử một vòng làm tiếp thật rồi xem `resume_failed` có xuất hiện không.
- Nút thu gọn (−) trên thanh tiêu đề vẫn còn; chưa chốt có bỏ không.

## Bổ sung: giao diện toàn chiều ngang, sidebar đóng được, phong cách Claude

- `max-width:1800px` của `.ao-main` có từ commit đầu (khối CSS ghi đè trang độc lập); đã bỏ.
- Nút đóng/mở sidebar (thu thành thanh biểu tượng 62px, nhớ trạng thái trong localStorage, tooltip cho nút điều hướng).
- Bộ giao diện phong cách Claude trong một khối CSS cuối `style.css` (biến màu `--ao-*`, `--af-*`, `--cmd-*`; tiêu đề serif; sáng/tối). Sidebar rộng 216px (trước 168px) vì chữ serif rộng hơn. Màu xanh lá riêng cho trạng thái thành công.
- Xem bằng mắt: điều khiển Edge qua CDP (Node 24 có WebSocket sẵn) chụp trang demo ở 1500px sáng/tối và 2560px khi sidebar đóng; Edge `--screenshot` và `--virtual-time-budget` bị treo vì long-poll.
- Test jsdom mới: toggle, ghi nhớ, giá trị lưu hỏng, không còn cap 1800px (đã thử đột biến).
- Chưa làm: bảng sơ đồ vẫn cố định 1274px; chiều cao lưới terminal không co giãn theo chiều cao cửa sổ trình duyệt.

## Bổ sung: cài đặt giao diện sáng/tối và bảng màu

- Người dùng thấy nền cũ (sáng hơn, xanh lạnh) dễ nhìn hơn nền Claude mới, và muốn có cài đặt sáng/tối. Vì "nền cũ" có thể hiểu theo nhiều cách, thay vì đoán một màu mới, có hai bảng màu chọn được: **Claude** và **Cổ điển** (khôi phục đúng token cũ bằng thuộc tính `data-palette="classic"`), cùng ba chế độ Theo hệ thống / Sáng / Tối.
- Nút mặt trời-mặt trăng trên thanh trên mở hộp thoại; áp dụng ngay, lưu localStorage, kiểm tra danh sách giá trị hợp lệ bằng `Object.hasOwn`. Màu nền terminal (xterm) đọc từ `--cmd-bg` đã giải quyết nên đổi theo bảng màu.
- Lỗi suýt gặp: khối này phải đặt sau khai báo `const terms` (khối sidebar chạy trước đó sẽ gặp lỗi truy cập biến chưa khởi tạo).
- Xem bằng mắt qua CDP: Cổ điển tối, Cổ điển sáng, Sáng bắt buộc khi hệ điều hành tối. Test jsdom thêm cho hộp thoại, ghi nhớ, giá trị hỏng (đã thử đột biến).

## Bổ sung: thanh cuộn, cỡ chữ 12px, lăn chuột trong terminal

- **Cỡ chữ**: cỡ nền 14px → 12px và 72 luật 11px/13px → 12px (cả khối CSS mới); tiêu đề to giữ nguyên theo yêu cầu; chữ bên trong CMD (xterm 13px, log 12px, lịch sử 11px) không đụng, chỉ `.ao-terminal-title-row` (meta 11px → 12px). Script thay thế nhận biết luật theo bộ chọn và liệt kê các luật được giữ.
- **Thanh cuộn**: ban đầu dùng `scrollbar-width: thin` nhưng Edge vẫn vẽ nút mũi tên ▲▼; chuyển sang `::-webkit-scrollbar*` (ẩn nút), giữ thuộc tính chuẩn cho Firefox bằng `@supports`. Chuẩn Chrome 121+: nếu đặt `scrollbar-color/width` thì pseudo-element webkit bị bỏ qua, nên không dùng song song.
- **Lăn chuột không cuộn được trong cmd**: tái hiện bằng CDP gửi sự kiện lăn chuột thật lên ba "TUI" giả chạy trong ConPTY thật. Bộ đệm thường cuộn bình thường (scrollTop đổi). Màn hình phụ thì không cuộn: ConPTY không chuyển `?1000h` sang xterm (không có class `enable-mouse-events`), nên xterm.js đổi mỗi nấc lăn thành ~16 phím ↑↓ (đo được: 80 phím ↑ cho 5 nấc). Các ứng dụng chat đọc ↑↓ là lịch sử gõ.
- **Sửa**: `attachCustomWheelEventHandler`; ở màn hình phụ gửi PageUp/PageDown (mỗi 90px một phím, tối đa 4/sự kiện) thay cho mũi tên; chọn được `page`/`arrows`/`none` trong cài đặt terminal, lưu localStorage, kiểm tra bằng `Object.hasOwn`. Đã đo lại: chế độ page nhận PageUp/PageDown và 0 phím ↑ do lăn; arrows nhận 80 phím ↑; none không gửi gì.
- **Chưa kiểm chứng**: Claude Code/Codex thật có phản hồi PageUp/PageDown bằng cách cuộn nội dung hay không (chỉ thử với ứng dụng giả). Nếu không, chọn lại mũi tên hoặc cần xem ứng dụng đó có chế độ không dùng màn hình phụ (Codex: `--no-alt-screen`).
