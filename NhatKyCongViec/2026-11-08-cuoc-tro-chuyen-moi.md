# Nhật ký 2026-11-08: Cuộc trò chuyện mới, đánh số agent đặt lại, bỏ ô thư mục làm việc

## Yêu cầu
1. Mỗi lần mở công cụ là một cuộc trò chuyện mới, nhưng số hiệu agent đang cộng dồn qua các lần chạy: phải đặt lại.
2. Thêm nút kết thúc "workflow": đóng toàn bộ CMD, đưa vào lịch sử, tự mở lại Agent 0; bấm nút phải mở hộp thoại xác nhận.
3. Bỏ ô "Thư mục làm việc" trong hộp thoại thêm CMD.

## Đã làm
- **Nguyên nhân số cộng dồn:** `agents.n` là AUTOINCREMENT toàn cục, không bao giờ dùng lại.
- **`Store.reset_chat()` / `chat_busy()`:** đặt lại bảng `agents` và bộ đếm, xóa `notices`; từ chối khi còn task `queued/running` hoặc workflow chưa xong (vì task/workflow tham chiếu số hiệu agent).
- **Khi mở công cụ** (`serve_web`) tự gọi `reset_chat()`: số hiệu bắt đầu từ 1. Nếu còn việc dở từ lần trước thì giữ số cũ (không phá việc đang chạy).
- **`Terminals.new_chat()` + `GET /api/chat`, `POST /api/chat/new`:** kiểm tra bận trước khi đóng gì; đóng từng cửa sổ (bộ giám sát vẫn chạy); đặt hội thoại thành `closed` (vẫn trong Lịch sử); đặt lại số; mở lại Agent 0; ghi audit.
- **Giao diện:** nút "Cuộc trò chuyện mới" (thanh công cụ; trong menu bánh răng ở cửa sổ hẹp) mở hộp thoại nêu rõ sẽ làm gì; khóa nút xác nhận kèm lý do nếu còn việc đang chạy; không gửi gì trước khi xác nhận.
- **Bỏ ô "Thư mục làm việc"** khỏi hộp thoại Thêm CMD (giữ ô chọn Agent và Repo khi có nhiều repo). Backend vẫn nhận `task_id` cho nút "Mở terminal" ở chi tiết task.

## Lỗi tiềm ẩn phát hiện và xử lý
Mở lại một phiên cũ truyền số hiệu cũ (`agent_n`). Sau khi đặt lại số, số đó có thể đã thuộc về một agent mới đang chạy, và phiên mở lại sẽ ghi đè cửa sổ đó (cùng khóa `claude-1`). Nay `open()` chỉ dùng lại số cũ khi hàng agent còn, cùng provider, loại `terminal` và không có phiên sống cùng khóa; nếu không thì cấp số kế tiếp. Trước đây trường hợp phiên `worker` (số của agent hàng đợi) cũng có thể đụng khóa với cửa sổ theo dõi; thay đổi này cũng chặn nó.

## Quyết định tự đưa ra
- **Từ chối thay vì tự hủy** khi còn việc đang chạy: hủy nhiệm vụ/workflow là thao tác phá hủy mà yêu cầu không nói rõ; để người dùng tự hủy trước. Có thể đổi thành "hủy luôn" nếu muốn.
- **Nhiệm vụ đã xong vẫn giữ số hiệu cũ** trong danh sách nhiệm vụ (không sửa lại dữ liệu cũ); trong Lịch sử mỗi phiên giữ nhãn lúc đó. Hệ quả: danh sách nhiệm vụ có thể có "codex 1" của cuộc trò chuyện trước bên cạnh "codex 1" mới. Chưa gom nhóm theo cuộc trò chuyện (có thể thêm cột `chat` sau nếu cần).
- **Chưa làm** gom Lịch sử theo "cuộc trò chuyện": hiện mỗi cửa sổ là một dòng, đã đóng thì thành "Đã đóng".

## Kiểm tra
- Test Python: tại `tests/test_history.py` (`TestChatReset`, 3 test store; 3 test API: đóng-lưu-đánh số lại-mở Agent 0, từ chối khi bận mà không đóng gì, phiên mở lại không ghi đè Agent 1 mới).
- Test UI (`flow_ui.cjs`): mở hộp thoại không tự gửi, hủy không gửi, bị khóa khi bận, xác nhận gửi `{confirm:true,...}`, thông báo, và hộp thoại Thêm CMD không còn ô thư mục.
- Chromium thật + server thật (agent giả chạy lâu): trước có Agent 0 + 2 CMD (số 1, 2); sau khi xác nhận chỉ còn Agent 0 mới (mã chạy khác), 2 CMD cũ trong Lịch sử đã đóng, agent mở kế tiếp mang số 1, không có lỗi trang.
- `tools/ui_shots.cjs`: hộp thoại nằm trong màn hình ở 1280px/460px, sáng/tối.
- Chưa thử với Claude Code thật (dùng agent giả); cơ chế mở Agent 0 giống lúc khởi động.
