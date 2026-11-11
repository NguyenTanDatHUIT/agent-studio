# Mẫu giao việc mới: PROMPT-<tên-việc>.md

> Dùng mẫu này khi Agent 0 soạn tệp giao việc cho cửa sổ CMD hoặc chuẩn bị nội dung cho task mới. Xoá các dòng hướng dẫn trong ngoặc vuông trước khi lưu.

**Đọc trước (bắt buộc):**
- Khung quy định chung (nếu dự án có): `[đường dẫn PROMPT-CHUNG.md]`
- Vai trò chuyên môn áp dụng: `[{ROLES_DIR}/coding/<vai-trò>.md]`
- Thư mục làm việc: `[đường dẫn repo hoặc worktree]` (chuyển vào đúng thư mục này trước khi đọc/sửa)

## 0. Điều kiện bắt đầu & Ngữ cảnh hiện tại
- Nhánh / Commit nền mong đợi: `[tên nhánh / mã hash nếu cần]`
- Những gì đã có sẵn từ đợt trước: `[liệt kê ngắn tệp/lớp/hàm nền tảng để agent dùng lại, không viết trùng]`

## 1. Tài liệu & Mã nguồn cần đọc có chọn lọc
- `[đường dẫn tệp 1: dòng A–B]` — `[mục đích đọc: lấy chữ ký hàm / đối chiếu schema / thứ tự khóa]`
- `[đường dẫn tệp 2]` — `[mục đích đọc]`
- *(Chỉ đọc đúng các đoạn liên quan; không quét toàn bộ kho mã hay thư mục test nếu không cần).*

## 2. Yêu cầu thực hiện & Phạm vi tệp
- **Mục tiêu:** `[mô tả rõ ràng, đo đếm được kết quả cần tạo ra]`
- **Phạm vi ĐƯỢC phép tạo/sửa (`allow_paths`):**
  - `[đường dẫn tệp hoặc thư mục 1]`
- **Phạm vi CẤM chạm:**
  - `[tệp dùng chung / schema / tệp sinh tự động / mã của luồng khác]`

## 3. Tiêu chí đạt (kiểm tra được bằng bằng chứng)
- [ ] `[Tiêu chí 1 — tệp/hàm/chữ ký cụ thể và hành vi mong đợi]`
- [ ] `[Tiêu chí 2 — đối chiếu khớp kiểu/mã trong schema/DDL thật, không tự bịa giá trị mặc định]`
- [ ] `[Tiêu chí 3 — cổng biên dịch / lệnh kiểm tra phải đạt 0 lỗi]`

## 4. Cổng kiểm tra, Commit & Báo cáo
- Cổng cần chạy trước khi kết thúc: `[lệnh build / kiểm tra cụ thể theo cấu hình chủ máy]`
- Ghi báo cáo đầy đủ ra tệp: `{PROMPTS_DIR}/BAOCAO-<tên-việc>.md` (bảng Yêu cầu ↔ `tệp:dòng` thật, số đo cổng, mục *"Thấy nhưng không sửa"* và câu hỏi mở nếu có).
- Trong cửa sổ terminal chỉ in đường dẫn tệp báo cáo và tối đa 3 dòng tóm tắt.
