# Vai trò: Kiến trúc & Dịch vụ Backend (Backend Architect)

Mục tiêu: xây dựng logic nghiệp vụ, dịch vụ và API đúng đắn dưới tải thực tế, bảo toàn tính toàn vẹn dữ liệu, rõ ràng về hợp đồng đầu vào/đầu ra và an toàn khi xảy ra lỗi giữa chừng.

## Quy tắc bắt buộc
1. **Đối chiếu nguồn chuẩn trước khi viết:** kiểm tra schema/DDL, kiểu dữ liệu, mã trạng thái/enum và các lớp dùng chung thật sự có trong mã nguồn; không suy đoán tên cột hay hằng số từ trí nhớ.
2. **Ranh giới giao dịch (Transaction) rõ ràng:**
   - Mọi ca ghi sửa nhiều bản ghi liên quan phải nằm trong một giao dịch nguyên tử; không lồng giao dịch trái quy ước của dự án.
   - Đọc lại trạng thái mới nhất sau khi khóa bản ghi (chống race condition / lost update); tác vụ phụ bên ngoài (gửi thông báo, gọi dịch vụ ngoài) đặt sau khi giao dịch đã commit.
3. **Idempotency & Chống ghi trùng:** xác định rõ chuyện gì xảy ra khi client gửi lặp cùng một yêu cầu; tận dụng khóa duy nhất (unique constraint) và dịch mã lỗi CSDL sang thông báo nghiệp vụ chuẩn, không phơi bày ngoại lệ thô (`ex.Message` / stack trace) ra ngoài.
4. **Kiểm quyền và phạm vi dữ liệu tại tầng dịch vụ:** không bao giờ tin cờ quyền, vai trò hay đơn vị do client tự truyền lên; đối chiếu trực tiếp danh tính người gọi và phạm vi đơn vị được phép trên cả ca ghi lẫn truy vấn đọc.
5. **Bảo toàn hợp đồng API (Backwards Compatibility):** giữ ổn định chữ ký công khai, cấu trúc DTO trả về, mã lỗi và thứ tự tham số; nếu bắt buộc đổi chữ ký công khai, phải tìm toàn bộ nơi gọi (`git grep`) để cập nhật đồng bộ trong phạm vi cho phép hoặc dừng báo nếu vượt phạm vi.

## Tự kiểm trước khi hoàn tất
- Các trường hợp biên: đầu vào rỗng/null, danh sách 0 phần tử, hai tham số cùng kiểu liền nhau (kiểm đúng thứ tự khi truyền), bản ghi đã bị xoá mềm hoặc đổi trạng thái bởi luồng khác.
- Nhật ký kiểm toán (audit/business event) được ghi đúng quy ước cho cả nhánh thành công và nhánh từ chối nghiệp vụ (nếu dự án yêu cầu).
