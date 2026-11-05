# Cập nhật Sơ đồ điều phối — 05/11/2026

Theo tài liệu người dùng cung cấp: `C:\Users\tsmda\Downloads\agent-studio-so-do-dieu-phoi.md`.

## Thay đổi

- Board navy 1274 × 428 px, card worker 218 × 136 px, khoảng trống các cột theo mẫu.
- Agent 0 → hai worker → hai test → Review → Xuất patch, từ trái sang phải ở mọi màn hình.
- Cuộn ngang trong `.flow-scroller`; không scale hoặc thu nhỏ card khi màn hình hẹp.
- SVG nằm dưới card; tọa độ được tính từ tâm cạnh thực tế của card bằng `drawEdges` hiện có.
- Nét đứt chuyển động và viền thở chỉ bật khi task `running` có sự kiện giai đoạn phù hợp:
  `worker_started` cho Agent 0 → Worker, `test_started` cho Worker → Test.
- Task queued/failed/cancelled/awaiting_review/approved không tự bật hiệu ứng. Nếu không có
  sự kiện giai đoạn trong dữ liệu hiện tại thì không đoán giai đoạn. Chưa có dữ liệu
  review/export đang chạy nên hai bước đó giữ tĩnh.
- Giữ phần tử SVG khi polling, tránh tạo lại animation sau mỗi lần cập nhật.
- `is-selected` phản ánh card người dùng đã chọn, độc lập với `is-running`. Click mở
  đúng task đang hiển thị, kể cả khi có task queued mới hơn task đang chạy cùng provider.
- Hỗ trợ `prefers-reduced-motion: reduce`; focus bàn phím vẫn có viền rõ.

Áp dụng cho cùng component sơ đồ ở Tổng quan và Luồng tự động. HTML ngoài template
sơ đồ không thay đổi (đã đối chiếu DOM, bỏ qua khoảng trắng). Backend/API, các màn hình
khác, tên hàm/signature và các hook `data-node`/`data-action` hiện có được giữ nguyên.

## File

- `agent_orchestrator/web_assets/index.html`: template sơ đồ, thêm namespace mới bên cạnh class cũ.
- `agent_orchestrator/web_assets/style.css`: CSS theo đặc tả, chỉ scope dưới `.agent-flow-section`.
- `agent_orchestrator/web_assets/app.js`: cập nhật `renderFlow`, `drawEdges`, tái sử dụng handler mở task.
- `tests/flow_ui.cjs`: kiểm tra DOM/trạng thái của sơ đồ; dữ liệu giả chỉ nằm trong kiểm thử.
- [Diff của ba file giao diện](FLOW-DIAGRAM-UPDATE.patch).

## Kết quả xác minh

- `node --check agent_orchestrator/web_assets/app.js`: pass.
- `tests/flow_ui.cjs` với jsdom: pass 7 node/7 connector, CSS fixed board, phép tính tâm cạnh,
  scroll container, ánh xạ worker/test, task running được ưu tiên, chọn card độc lập,
  SVG ổn định khi cập nhật, tắt hiệu ứng khi dừng/chờ review/không rõ giai đoạn,
  handler mở đúng task và quy tắc reduced motion.
- `tests/web_ui.cjs` trên server HTTP demo offline riêng: pass điều hướng, bố cục cửa sổ,
  phân trang, bản nháp, phóng to, sắp xếp, tạo/hủy task, escape HTML, review, export/download.
- Không gọi model thật; không thay đổi dữ liệu trên dashboard người dùng ở cổng 8765.

**Giới hạn:** browser access host không khả dụng trong phiên này. Chưa chụp ảnh trước/sau
hoặc xác minh pixel, body overflow và responsive bằng trình duyệt tại 1366×768, 1440×900,
1920×1080, 800 px hoặc dưới 800 px. Test jsdom dùng hình học suy ra từ CSS để kiểm tra
phép tính đường nối; không thay thế kiểm tra bố cục của trình duyệt.

Dashboard đang chạy đọc trực tiếp các asset này; tải lại tab để nhận giao diện mới.
