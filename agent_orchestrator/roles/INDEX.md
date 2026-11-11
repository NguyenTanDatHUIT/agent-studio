# Bảng điều hướng Vai trò & Mẫu chuẩn (Agent Studio)

Thư viện này cung cấp các **hồ sơ vai trò chuyên môn (Role Profiles)** và **mẫu bàn giao (Templates)** tinh gọn để giữ ngân sách ngữ cảnh nhẹ, tránh sửa mã lan man và nâng chất lượng nghiệm thu.

## 1. Cách áp dụng theo hai kênh của công cụ

- **Kênh Worker hàng đợi (`enqueue_task` / `enqueue_plan`):** truyền tham số `role="<slug>"` (ví dụ `role="minimal-change"`). Công cụ tự nhúng nội dung vai trò vào `worker_prompt` bên trong worktree cô lập — bạn không cần chép tay nội dung vai trò vào `prompt`.
- **Kênh Terminal tương tác (`agy` / `claude` / `codex`):** khi viết tệp `PROMPT-<việc>.md`, dặn agent đọc thêm tệp vai trò tương ứng trong thư mục này (hoặc chép các gạch đầu dòng cốt lõi vào mục quy tắc của tệp prompt).
- **Thứ tự ưu tiên:** Quy tắc an toàn của công cụ → Ràng buộc chung / khung dự án của chủ máy → Phạm vi của việc riêng → Vai trò chuyên môn. Vai trò **không bao giờ** mở rộng phạm vi tệp hay nới quy tắc của chủ máy.

## 2. Chọn vai trò Coding (`coding/`)

| Slug | Tệp | Khi nào dùng |
|---|---|---|
| `minimal-change` | `coding/minimal-change.md` | Sửa lỗi (bug fix), vá theo review (`fix1`, `fix2`), hoặc bổ sung nhỏ trong phạm vi hẹp cần diff tối thiểu. |
| `backend-architect` | `coding/backend-architect.md` | Cài đặt nghiệp vụ Service, API, giao dịch (transaction), idempotency, kiểm tra biên và tương thích ngược. |
| `database-optimizer` | `coding/database-optimizer.md` | Truy vấn dữ liệu lớn, xử lý N+1, phân trang/lọc/đếm, thứ tự khóa dòng chống deadlock, thiết kế index/migration. |
| `frontend-ui` | `coding/frontend-ui.md` | Xây dựng hoặc sửa giao diện web/ứng dụng: tuân thủ design token, đủ trạng thái rỗng/lỗi/focus, chuẩn màn rộng & hẹp. |

## 3. Chọn vai trò Review & Nghiệm thu chỉ-đọc (`review/`)

| Slug | Tệp | Khi nào dùng |
|---|---|---|
| `code-reviewer` | `review/code-reviewer.md` | Giao agent phụ review chỉ-đọc song song cho các commit vừa xong (đúng đắn, bảo trì, hiệu năng, phân loại CAO/TRUNG/THẤP). |
| `reality-checker` | `review/reality-checker.md` | Cổng nghiệm thu cuối đợt trước tích hợp: mặc định `CHƯA ĐẠT`, đối chiếu từng yêu cầu gốc với mã thật và bằng chứng kiểm. |
| `security-auditor` | `review/security-auditor.md` | Rà soát phân quyền phía server, lộ khóa/token, lọc dữ liệu theo đơn vị/người dùng, SQL/command/prompt injection. |

## 4. Mẫu soạn thảo cho Agent 0 (`templates/`)

- `templates/prompt-task.md` — Khung soạn `PROMPT-<việc>.md` cho việc mới.
- `templates/prompt-fix.md` — Khung soạn `PROMPT-<việc>-fixN.md` khi nghiệm thu phát hiện mục chưa đạt.
- `templates/escalation-handoff.md` — Khung viết lại ngữ cảnh khi thay cửa sổ agent mới hoặc dừng báo `CHẶN` cho chủ máy.
