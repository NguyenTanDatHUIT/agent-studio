# Hướng Dẫn Sử Dụng: Lịch Sử Chat & Mở Lại Phiên (Conversations & Resume)

Tài liệu này hướng dẫn người dùng cuối cách tra cứu lịch sử hội thoại, xem lại nội dung bản ghi màn hình (transcript), và khôi phục các phiên làm việc của Agent 0 cũng như các terminal agent trong giao diện điều khiển Agent Orchestrator.

---

## 1. Mở Hộp Thoại Lịch Sử

Trên thanh công cụ điều khiển của Dashboard (ở tab **Bàn làm việc** / Console), nhấp vào nút **"Lịch sử"** (nằm cạnh nút "Làm mới log").

![Nút Lịch sử trên thanh điều khiển](file:///docs/assets/history_button.png)

Hộp thoại **"Lịch sử chat & phiên làm việc"** sẽ xuất hiện, hiển thị danh sách tất cả các phiên làm việc đã từng khởi chạy trên hệ thống.

---

## 2. Giao Diện & Cách Tìm Kiếm, Lọc

Danh sách các phiên làm việc được nhóm trực quan theo mốc thời gian:
- **Hôm nay**: Các phiên được khởi tạo hoặc có hoạt động trong ngày hiện tại.
- **Hôm qua**: Các phiên của ngày hôm trước.
- **Ngày cụ thể** (`DD/MM/YYYY`): Các phiên cũ hơn.

### Các công cụ tìm kiếm và bộ lọc:
- **Ô tìm kiếm (`input`)**: Nhập từ khóa bất kỳ để tìm theo tiêu đề tóm tắt, mã nhiệm vụ (Task ID), hoặc định danh phiên (Session ID). Quá trình tìm kiếm diễn ra tự động sau khi bạn ngừng gõ 200ms.
- **Bộ lọc nhà cung cấp (Provider)**: Chọn xem cụ thể một nhóm agent:
  - *Tất cả agent*: Hiển thị toàn bộ lịch sử.
  - *Agent 0*: Chỉ xem các phiên điều phối chính của Agent 0 (Claude Code).
  - *Claude*: Các terminal agent chạy Claude Code.
  - *Codex*: Các terminal agent chạy OpenAI Codex.
  - *Antigravity (agy)*: Các terminal agent chạy Google Antigravity.
- **Nút "Làm mới"**: Cập nhật lại danh sách phiên mới nhất từ cơ sở dữ liệu máy chủ.

### Thông tin hiển thị trên mỗi dòng:
1. **Mốc thời gian**: Giờ bắt đầu (`HH:MM`).
2. **Huy hiệu Agent**: Tên và số hiệu agent (ví dụ: `Agent 0`, `Claude 1`, `Codex 2`).
3. **Tiêu đề**: Tóm tắt nội dung phiên (hoặc câu lệnh ban đầu).
4. **Ngữ cảnh**: Tên repo (`default`, `web`...), mã task (`task 1a2b3c4d`), và đường dẫn thư mục làm việc.
5. **Trạng thái**:
   - `Đang mở`: Phiên đang chạy sống trong một cửa sổ terminal trên màn hình.
   - `Đã đóng`: Phiên đã kết thúc tiến trình bình thường.
   - `Lỗi`: Phiên kết thúc với mã lỗi khác 0.

---

## 3. Hai Hành Động: "Xem lại" và "Mở lại"

Mỗi phiên hội thoại cung cấp 2 hành động khác nhau tùy theo nhu cầu của bạn:

### A. Hành động "Xem lại" (Transcript Viewer)
- **Mục đích**: Đọc lại toàn bộ nội dung văn bản hiển thị trên màn hình terminal của phiên trước đó mà không khởi chạy lại tiến trình CLI.
- **Cách dùng**: Nhấp nút **"Xem lại"**. Cửa sổ xem lại transcript sẽ mở ra:
  - Hiển thị toàn bộ text với font monospaced dễ đọc.
  - Mỗi dòng có mốc thời gian chính xác `[HH:MM:SS]`.
  - Các mã màu ANSI phức tạp đã được lọc sạch sẽ, các token bí mật (API key, Bearer token) được tự động che mờ bằng `[REDACTED]`.
  - Nút **"Sao chép"**: Copy nhanh toàn bộ nội dung transcript vào clipboard.
  - Nút **"Tải thêm dòng cũ hơn"**: Nếu bản ghi dài, hỗ trợ phân trang để đọc ngược về đầu phiên.
- **Đối tượng hỗ trợ**: Áp dụng cho **100% tất cả các agent**, bao gồm cả Agent 0, Claude, Codex, và Antigravity (`agy`).

### B. Hành động "Mở lại" (Session Resume)
- **Mục đích**: Khởi động một tiến trình CLI thật sự để **tiếp tục trao đổi** với mô hình ngôn ngữ dựa trên ngữ cảnh và bộ nhớ của phiên trước.
- **Cách dùng**: Nhấp nút **"Mở lại"**.
  - Hệ thống tự động mở một cửa sổ terminal mới trên bàn làm việc.
  - Chuyển đúng vào thư mục dự án ban đầu của phiên đó.
  - Truyền tham số resume chính thức (`--resume <session_id>` cho Claude và Agent 0, `codex resume <session_id>` cho Codex, `--conversation <id>` cho Antigravity).
  - Với Antigravity, id hội thoại chỉ xuất hiện sau **tin nhắn đầu tiên** bạn gửi (agy tạo file hội thoại lúc đó). Nếu đóng terminal trước khi gửi gì, phiên đó chỉ có thể "Xem lại".
  - Tự động cuộn trang bàn làm việc tới vị trí cửa sổ mới.
- **Đối tượng hỗ trợ**: Các CLI có cơ chế lưu trữ phiên chính thức (Claude Code, OpenAI Codex).

---

## 4. Các Trường Hợp Đặc Biệt Cần Lưu Ý

1. **Phiên đang mở (Nút "Mở lại" bị mờ/disable)**:
   - Nếu phiên làm việc đó đang có một cửa sổ terminal sống trên bàn làm việc, nút "Mở lại" sẽ bị vô hiệu hóa kèm chú thích *"Phiên đang mở trong terminal"*.
   - *Lý do*: Ngăn ngừa việc mở đồng thời 2 tiến trình cùng ghi vào một file session của CLI, gây xung đột và hỏng dữ liệu phiên.
2. **Phiên không có Session ID hoặc CLI không hỗ trợ resume**:
   - Đối với các công cụ không có tính năng session persistence (ví dụ Antigravity CLI hiện tại), khi nhấp "Mở lại", hệ thống sẽ thông báo:
     > *"Phiên này không có session ID để mở lại. Bạn có thể chọn 'Xem lại' để đọc bản ghi."*
   - Bạn hãy sử dụng nút **"Xem lại"** để lấy nội dung trao đổi cũ và dán vào một terminal mới nếu cần.
3. **Giới hạn dung lượng và tự động cắt tỉa (Retention Policy)**:
   - Mỗi file transcript có giới hạn tối đa là **5 MB**. Nếu log vượt quá 5 MB, phần đầu của file sẽ tự động được lược bỏ để giữ lại 4 MB dữ liệu gần nhất, kèm dòng thông báo: `[... noi dung cu da duoc luoc bo de giu gioi han 5 MB ...]`.
   - Tổng dung lượng thư mục transcripts trên máy của bạn được giới hạn ở **100 MB**. Khi đạt ngưỡng này, hệ thống sẽ tự động thu hồi các file transcript cũ nhất theo thời gian sửa đổi.


## Xóa lịch sử

Transcript có thể chứa nội dung nhạy cảm, nên bạn có thể xóa bất cứ lúc nào:

- **Xóa một phiên**: nhấn nút **"Xóa"** ở cuối dòng. Hệ thống hỏi xác nhận, rồi xóa dòng trong lịch sử và file transcript tương ứng.
- **Xóa tất cả**: nhấn **"Xóa tất cả"** trên thanh công cụ của hộp thoại Lịch sử (có hỏi xác nhận).
- Phiên **đang mở** trong terminal không bị xóa; hãy đóng terminal trước (nút "Xóa" bị vô hiệu hóa với phiên đang mở).
- Xóa chỉ gỡ dữ liệu do Agent Studio lưu (`state/transcripts` và bảng lịch sử). Phiên do chính Claude/Codex/agy lưu trong thư mục của chúng (ví dụ `~/.claude`, `~/.codex`, `~/.gemini`) **không bị xóa**, nên bạn vẫn có thể tự dọn ở đó nếu cần.
- Việc xóa được ghi vào `terminal-audit.jsonl` (chỉ ghi id và loại hành động, không ghi nội dung).
- Không thể hoàn tác.
