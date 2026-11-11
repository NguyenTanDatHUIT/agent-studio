# Mẫu yêu cầu sửa: PROMPT-<tên-việc>-fix<N>.md

> Dùng khi nghiệm thu phát hiện mục chưa đạt (vòng sửa `1` đến `{MAX_FIX_ROUNDS}`). Áp dụng kỷ luật `coding/minimal-change.md`: CHỈ sửa đúng các mục lỗi liệt kê bên dưới, tuyệt đối không viết lại phần đã đạt.

## 1. Trạng thái nghiệm thu vòng trước
- **Việc / Đợt:** `[tên việc]` — **Vòng sửa:** `[N / {MAX_FIX_ROUNDS}]`
- **Commit / Trạng thái cây hiện tại:** `[hash commit vừa kiểm hoặc danh sách tệp đang sửa dở]`
- **Các phần ĐÃ ĐẠT (bắt buộc GIỮ NGUYÊN, không sửa lại):**
  - `[liệt kê các tệp/hàm/nhánh logic đã kiểm tra đạt]`

## 2. Danh sách mục CHƯA ĐẠT cần sửa

### Lỗi 1 — `[Mức: CAO / TRUNG]` · `[tệp:dòng]`
- **Kỳ vọng (theo đặc tả / schema thật):** `[mô tả hành vi hoặc giá trị đúng, trích dẫn nguồn chuẩn]`
- **Thực tế trong mã hiện tại:** `[trích dẫn ngắn biểu thức/dòng mã đang sai và hậu quả]`
- **Hướng sửa cụ thể:** `[chỉ dẫn rõ cần đổi gì ở tệp nào]`

### Lỗi 2 — `[Mức: CAO / TRUNG]` · `[tệp:dòng]`
- **Kỳ vọng:** `[...]`
- **Thực tế:** `[...]`
- **Hướng sửa cụ thể:** `[...]`

*(Nếu đây là sửa theo báo cáo Review của agent khác: bạn phải tự đối chiếu mã thật từng mục trước khi sửa — ghi rõ `XÁC NHẬN` rồi sửa, hoặc `KHÔNG TÁI HIỆN` kèm bằng chứng nếu báo cáo review nhầm).*

## 3. Tiêu chí hoàn tất vòng sửa
- [ ] Toàn bộ mục lỗi trên đã được xử lý gọn sạch, không phát sinh thay đổi ngoài danh sách tệp liên quan.
- [ ] Chạy lại cổng kiểm tra: `[lệnh build / kiểm tra]` đạt 0 lỗi.
- [ ] Cập nhật bổ sung mục **"Sửa lần `[N]`"** vào `{PROMPTS_DIR}/BAOCAO-<tên-việc>.md` (ghi rõ `tệp:dòng` mới và hash commit sửa); trong terminal chỉ trả đường dẫn báo cáo + tối đa 3 dòng.
