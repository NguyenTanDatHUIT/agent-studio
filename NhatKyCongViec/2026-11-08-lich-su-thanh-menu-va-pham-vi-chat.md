# Nhật ký 2026-11-08: phiên mới sạch việc cũ, Lịch sử thành menu, nút trò chuyện mới ra thanh công cụ

## Yêu cầu (từ ảnh chụp tab Nhiệm vụ)
1. Mở công cụ là phiên chat mới, nhưng tab Nhiệm vụ vẫn hiện nhiệm vụ cũ (codex 7, codex 6, claude 1...) và làm lệch cả tab Luồng tự động.
2. Lịch sử nên là mục menu, không phải nút trong cài đặt.
3. Nút "Cuộc trò chuyện mới" nên nằm ngoài, trên thanh `ao-console-bar`.

## Nguyên nhân của (1)
Lần trước chỉ đặt lại số hiệu agent và các cửa sổ CMD. Nhiệm vụ, workflow và hoạt động nằm trong cơ sở dữ liệu và vẫn được liệt kê đầy đủ, nên tab Nhiệm vụ, Tổng quan, Luồng tự động và Báo cáo (đều đọc cùng danh sách) mang theo việc của các lần chạy trước.

## Đã làm
- **Phạm vi theo cuộc trò chuyện:** `reset_chat()` ghi mốc `chat_since`; `list()`, `wf_list()`, `activity()` chỉ trả bản ghi từ mốc đó (`all_chats=True` bỏ lọc). `/api/tasks`, `/api/activity`, `/api/workflows` nhận `?scope=all`. `/api/chat` trả thêm `since` và `hidden`. Reset bị từ chối thì không dời mốc.
- **Không để mất dấu việc chưa duyệt:** tab Nhiệm vụ có ghi chú "Đang ẩn N nhiệm vụ của các cuộc trò chuyện trước (M đang chờ review)" và nút "Hiện tất cả" / "Chỉ cuộc trò chuyện hiện tại". Mở task cũ theo id vẫn chạy.
- **Engine không bị ảnh hưởng:** việc thả bước workflow dùng `wf_list(100, all_chats=True)`; việc dở vẫn chạy tiếp dù bị ẩn khỏi danh sách. Agent 0 (MCP `list_tasks`, `list_workflows`) thấy cuộc trò chuyện hiện tại.
- **Lịch sử là mục menu bên trái** (giữa Nhiệm vụ và Báo cáo), một trang thật thay cho hộp thoại; nút "Lịch sử" trong cài đặt và thanh công cụ đã bỏ. "Mở lại" tự chuyển sang tab Cửa sổ CMD. Hộp thoại xem transcript vẫn là modal.
- **Nút "Cuộc trò chuyện mới" nằm trên thanh `ao-console-bar`** cạnh "+ CMD"; cửa sổ hẹp (dưới 760px) chỉ còn biểu tượng (có `aria-label` và tooltip).

## Quyết định tự đưa ra
- **Ẩn bằng mốc thời gian, không xóa hay gắn nhãn lại:** an toàn với dữ liệu, không cần migration. Hệ quả: lần chạy đầu sau khi cập nhật (chưa có mốc) chưa ẩn gì; mốc được ghi ở lần mở công cụ hoặc lần bấm "Cuộc trò chuyện mới" đầu tiên.
- **Mở công cụ khi còn việc đang chạy từ lần trước:** reset bị từ chối nên mốc không đổi và việc cũ vẫn hiện (không giấu việc đang chạy).
- **Nút "Hiện tất cả" áp dụng cho mọi tab**, không riêng tab Nhiệm vụ, để Tổng quan, Luồng tự động và Báo cáo luôn nhất quán với danh sách.
- **Bỏ tiêu đề lặp** trong trang Lịch sử (tiêu đề đã có ở đầu trang).

## Kiểm tra
- Python: `TestChatScope` (4 test store/engine) và 1 test API (`/api/tasks`, `/api/activity`, `/api/workflows`, `scope=all`, `/api/chat`); `test_history` 57 test OK.
- UI jsdom (`flow_ui.cjs`): history là mục menu và không còn nút trong cài đặt; mở/đóng trang; ghi chú ẩn việc cũ, nút bật/tắt gọi đúng `scope=all`; nút trò chuyện mới nằm trong `.ao-console-bar-actions`.
- Chromium thật (`tools/ui_shots.cjs`, 1280px và 460px, sáng và tối): nút trên thanh công cụ, trang Lịch sử không tràn ngang, menu select, hộp thoại xác nhận; settings menu không còn liệt kê Lịch sử hay Cuộc trò chuyện mới.
- Chưa thử với dữ liệu thật của bạn (6 nhiệm vụ trong ảnh): sau khi khởi động lại công cụ, các nhiệm vụ đó sẽ bị ẩn và ghi chú sẽ báo "ẩn 6 nhiệm vụ".

## Sửa thêm: hộp thoại xem lại transcript tự hiện ở cuối trang
- **Nguyên nhân:** `.ao-transcript-dialog{display:flex}` đè quy tắc mặc định ẩn `<dialog>` chưa mở, nên hộp thoại đóng vẫn có `display:flex` và cao 640px (đo bằng Chromium thật).
- **Sửa:** `#ao-studio dialog:not([open]){display:none}` (độ ưu tiên cao hơn mọi lớp riêng, che luôn các hộp thoại sau này).
- **Kiểm tra:** đo lại, mọi hộp thoại đóng có `display:none`; `ui_shots.cjs` nay báo lỗi nếu hộp thoại đóng còn hiện và kiểm tra hộp thoại transcript hiện đúng khi mở, ẩn khi đóng (2 cỡ, sáng/tối); `test_ui_rules` thêm 1 test.
- **Bài học:** lỗi này nằm trong CSS hộp thoại viết ở vòng lịch sử đầu tiên; test jsdom không dàn trang nên không bắt được. Đã thêm quy tắc 5 vào `docs/UI-RULES.md`.
