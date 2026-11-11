# Nhật ký: Tích hợp hiệu ứng Radar Status (Running & Stopped) cho tiêu đề Terminal

- **Ngày thực hiện**: 2026-11-11
- **Phạm vi thay đổi**:
  - `agent_orchestrator/web_assets/style.css`
  - `agent_orchestrator/web_assets/app.js`
  - `tests/flow_ui.cjs`

---

## 1. Yêu cầu & Bối cảnh
- Thay thế nhãn chữ trạng thái `Đang chạy` / `Đã dừng` trong thẻ `<span class="ao-terminal-meta"><code data-window-path="">...</code><span data-window-status=""></span></span>` bằng hiệu ứng radar CSS từ thư viện `st-radar-status`.
- Trạng thái dừng (`stopped`): Vòng xung cảnh báo đỏ + lõi chớp đỏ.
- Trạng thái chạy (`running`): Hiệu ứng tương tự như `stopped` (vòng xung cảnh báo + lõi chớp) nhưng mang màu xanh lá cây (`#22c55e`), thay vì vệt quét radar xoay tròn.
- Căn chỉnh chính xác tuyệt đối theo chiều ngang và dọc (center).

---

## 2. Các thay đổi thực hiện

### 2.1. Cập nhật CSS (`agent_orchestrator/web_assets/style.css`)
- Nhúng bộ class `.st-radar`, `.st-radar.running`, `.st-radar.stopped` và các `@keyframes`:
  - `.st-radar`: kích thước `--size: 18px`, `display: inline-flex; align-items: center; justify-content: center; align-self: center`.
  - `.st-radar.running`: nền và viền màu xanh lá nhạt (`rgba(34, 197, 94, .1)` & viền `rgba(34, 197, 94, .45)`). `::before` phát xung vòng tròn mở rộng xanh lá liên tục không nghỉ (`animation: st-radar-alert 1.1s ease-out infinite`), `::after` lõi tròn xanh lá `#22c55e` chớp nhịp đều (`animation: st-radar-blink 1.1s ease-in-out infinite`).
  - `.st-radar.stopped`: nền và viền màu đỏ nhạt (`rgba(239, 68, 68, .1)` & viền `rgba(239, 68, 68, .45)`). `::before` phát xung vòng tròn đỏ liên tục (`st-radar-alert`), `::after` lõi vuông đỏ `#ef4444` chớp nhịp đều (`st-radar-blink`).
  - Loại bỏ khoảng nghỉ 55%–100% (~0.9s) trong `@keyframes` gốc để hiệu ứng phát xung và chớp diễn ra liên tục từ `0%` → `100%`.
  - Scoped dưới `#ao-studio` và hỗ trợ `@media(prefers-reduced-motion: reduce)`.
- Căn chỉnh thanh tiêu đề:
  - `.ao-terminal-title-row`: `align-items: center; min-height: 28px`.
  - `.ao-terminal-meta`: `display: inline-flex; align-items: center; gap: 8px; overflow: visible`.
  - `.ao-terminal-meta code`: `overflow: hidden; text-overflow: ellipsis; white-space: nowrap`.

### 2.2. Cập nhật JS (`agent_orchestrator/web_assets/app.js`)
- Trong `updateWindow(w, text)`:
  - Chỉ cập nhật `statusEl.className` khi giá trị thực sự thay đổi (`if (statusEl.className !== wantCls)`), tránh ghi đè DOM mỗi chu kỳ refresh 3s làm giật/reset nhịp animation.
  - Làm rỗng `statusEl.textContent = ''`.
  - Gán `aria-label` và `title` bằng trạng thái để tooltip hiển thị khi rê chuột và hỗ trợ trợ năng.

### 2.3. Cập nhật kiểm thử UI
- Cập nhật `tests/flow_ui.cjs` để kiểm tra class `.st-radar.running` và `aria-label`.
- Đảm bảo toàn bộ 8 bài test của `python -m unittest tests.test_ui_rules` tiếp tục pass.

---

## 3. Kiểm thử & Đo đạc vị trí
- Đo đạc bounding box qua Chromium headless trên cả 3 cửa sổ mẫu (`agent0`, `agy-29`, `agy-30`):
  - Chiều cao dòng: 28px.
  - Độ lệch tâm so với tâm dòng (`statusDy`): `0px` (chuẩn tâm 100%).
  - Kích thước radar: chính xác `18px × 18px`.
- Chụp ảnh màn hình thực tế và kiểm tra trực quan cả 2 trạng thái running (xanh lá) và stopped (đỏ).

