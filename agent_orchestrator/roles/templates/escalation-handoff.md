# Mẫu đổi cửa sổ Agent mới hoặc Báo CHẶN (Escalation & Handoff)

> Dùng trong hai tình huống của vòng nghiệm thu:
> 1. **Thay cửa sổ mới** (sau `{MAX_FIX_ROUNDS}` lần sửa không đạt hoặc cửa sổ cũ treo): Agent 0 **viết lại prompt chuẩn hơn** dựa trên khung dưới đây để cửa sổ mới kế thừa phần đã đạt và không lặp lại sai lầm cũ.
> 2. **Báo CHẶN cho chủ máy** (đã hết `{MAX_AGENTS_PER_TASK}` cửa sổ cho cùng một việc, hoặc gặp mâu thuẫn tài liệu/schema/quyền không được tự quyết).

## 1. Thông tin chung
- **Việc / Đợt:** `[tên việc]`
- **Tình huống:** `[Thay sang cửa sổ thứ 2 / Dừng báo CHẶN chờ quyết định của chủ máy]`
- **Cửa sổ / Agent đã tham gia:** `[ví dụ: agy-2 (gốc + 2 lần sửa)]`
- **Trạng thái cây làm việc hiện tại:** `[sạch ở commit <hash> / còn tệp dở dang <danh sách tệp> — KHÔNG xoá nếu phần dở dang đúng hướng]`

## 2. Lịch sử các lần thử & Vì sao chưa đạt
- **Lần 1 (bản gốc):** Đã làm được `[...]`. Chưa đạt ở `[tệp:dòng — lý do cụ thể]`.
- **Sửa lần 1..N:** Đã thử `[hướng sửa đã áp dụng]` → Kết quả vẫn vướng vì `[bằng chứng lỗi biên dịch / lệch schema / kẹt ngữ cảnh]`.

## 3. Phân tích nguyên nhân gốc (Root Cause)
- **Nguyên nhân chính:** `[ví dụ: prompt cũ mô tả thiếu ràng buộc X / việc quá lớn làm đầy ngữ cảnh / mâu thuẫn giữa kế hoạch và bài test Y]`
- **Điều CẤM lặp lại:** `[nêu đích danh hướng tiếp cận sai mà agent trước đã thử để agent mới tránh ngay]`

## 4. Hành động tiếp theo
- **Nếu giao cho cửa sổ mới:**
  - Phần **ĐÃ ĐẠT giữ nguyên**: `[danh sách commit / tệp không đụng lại]`
  - Phần **CẦN LÀM TIẾP** (đã thu hẹp và làm rõ tiêu chí): `[liệt kê từng bước nhỏ kèm ví dụ đúng]`
- **Nếu báo CHẶN cho chủ máy:**
  - **Câu hỏi cần chủ máy chốt:** `[nêu ngắn gọn các phương án A / B kèm tác động của từng phương án]`
  - **Đề xuất kỹ thuật của Agent 0:** `[phương án khuyến nghị + lý do]`
