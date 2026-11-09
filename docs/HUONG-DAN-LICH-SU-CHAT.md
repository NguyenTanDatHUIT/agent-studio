# Hướng Dẫn Sử Dụng: Lịch Sử Chat & Mở Lại Phiên (Conversations & Resume)

Tài liệu này hướng dẫn người dùng cuối cách tra cứu lịch sử hội thoại, xem lại nội dung bản ghi màn hình (transcript), và khôi phục các phiên làm việc của Agent 0 cũng như các terminal agent trong giao diện điều khiển Agent Orchestrator.

---

## 1. Mở Trang Lịch Sử

Chọn mục **"Lịch sử"** trong menu bên trái của Dashboard (giữa "Nhiệm vụ" và "Báo cáo"). Trang **"Lịch sử trò chuyện"** hiển thị danh sách tất cả các phiên làm việc đã từng khởi chạy trên hệ thống: tìm kiếm, lọc theo agent, "Xem lại", "Mở lại" và "Xóa". Khi bấm "Mở lại", Dashboard tự chuyển sang tab Cửa sổ CMD để bạn thấy cửa sổ vừa mở.

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
- **Xóa tất cả**: nhấn **"Xóa tất cả"** trên thanh công cụ của trang Lịch sử (có hỏi xác nhận).
- Phiên **đang mở** trong terminal không bị xóa; hãy đóng terminal trước (nút "Xóa" bị vô hiệu hóa với phiên đang mở).
- Xóa chỉ gỡ dữ liệu do Agent Studio lưu (`state/transcripts` và bảng lịch sử). Phiên do chính Claude/Codex/agy lưu trong thư mục của chúng (ví dụ `~/.claude`, `~/.codex`, `~/.gemini`) **không bị xóa**, nên bạn vẫn có thể tự dọn ở đó nếu cần.
- Việc xóa được ghi vào `terminal-audit.jsonl` (chỉ ghi id và loại hành động, không ghi nội dung).
- Không thể hoàn tác.


## Cuộc trò chuyện mới (kết thúc một workflow)

Mỗi lần mở Agent Studio là một cuộc trò chuyện mới: Agent 0 bắt đầu trống và **số hiệu agent bắt đầu lại từ 1** (Claude 1, Codex 1...). Muốn kết thúc giữa chừng và bắt đầu lại mà không phải tắt công cụ:

1. Bấm **"Cuộc trò chuyện mới"** ngay trên thanh công cụ của tab Cửa sổ CMD (cạnh nút "+ CMD"; ở cửa sổ hẹp chỉ còn biểu tượng, rê chuột để xem tên).
2. Hộp thoại cho biết sẽ làm gì: đóng N cửa sổ CMD, lưu tất cả vào Lịch sử, đánh số lại từ 1 và mở lại Agent 0 với cuộc trò chuyện trống. Bấm **"Hủy"** thì không có gì xảy ra.
3. Bấm **"Đóng và mở cuộc trò chuyện mới"** để thực hiện.

Lưu ý:
- Các cửa sổ đã đóng vẫn nằm trong **Lịch sử** (trạng thái "Đã đóng"), có thể "Xem lại" hoặc "Mở lại". Khi mở lại một phiên cũ trong cuộc trò chuyện mới, nó nhận **số hiệu kế tiếp còn trống**, không chiếm số của agent đang chạy.
- Nếu còn **nhiệm vụ đang chạy/chờ chạy** hoặc **workflow chưa xong**, nút xác nhận bị khóa và hộp thoại ghi rõ lý do. Hãy chờ xong hoặc hủy chúng trước (vì nhiệm vụ và workflow tham chiếu số hiệu agent). Khi mở công cụ lên, nếu còn việc dở từ lần trước thì số hiệu cũ được giữ nguyên cho đến khi bạn bắt đầu cuộc trò chuyện mới.
- Các nhiệm vụ đã xong vẫn giữ số hiệu cũ trong danh sách nhiệm vụ; trong Lịch sử mỗi phiên giữ nhãn số hiệu mà nó có lúc đó.

## Nhiệm vụ của các cuộc trò chuyện trước

Mỗi lần mở công cụ (và mỗi lần bấm "Cuộc trò chuyện mới") là một cuộc trò chuyện mới, nên các tab **Tổng quan, Luồng tự động, Nhiệm vụ, Báo cáo** chỉ hiện nhiệm vụ, workflow và hoạt động của cuộc trò chuyện hiện tại. Dữ liệu cũ **không bị xóa**:

- Ở tab **Nhiệm vụ** có dòng ghi chú "Đang ẩn N nhiệm vụ của các cuộc trò chuyện trước (M đang chờ review)". Bấm **"Hiện tất cả"** để xem cả việc cũ (áp dụng cho mọi tab); bấm **"Chỉ cuộc trò chuyện hiện tại"** để quay lại.
- Nhiệm vụ cũ đang **chờ review** vẫn được đếm riêng trong ghi chú đó để bạn không bỏ sót patch chưa duyệt.
- Mở một nhiệm vụ cũ bằng id (ví dụ từ Lịch sử) vẫn hoạt động.
- Agent 0 (công cụ `list_tasks`, `list_workflows`) cũng chỉ thấy cuộc trò chuyện hiện tại.
