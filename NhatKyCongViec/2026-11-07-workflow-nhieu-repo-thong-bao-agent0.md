# 2026-11-07 · Workflow, nhiều repo, thông báo cho Agent 0

- Sửa cuộn: `overscroll-behavior: contain` cho vùng terminal để kéo hết cỡ không cuộn trang ngoài.
- Thông báo: bảng `notices` (ghi khi task agent xong/lỗi/hủy và khi workflow đổi bước); `Terminals.notify_agent0` gõ một dòng `[AO]` vào Agent 0.
- Workflow: bảng `workflows`/`steps`, `Engine.plan/release_ready/cancel_workflow`, MCP `enqueue_plan`/`list_workflows`/`cancel_workflow`, API `/api/workflows`, khối "Workflow" ở trang Luồng tự động.
- Nhiều repo: `repos` trong config, `Git(config, repo)`, task và agent mang tên repo, `list_repos`, chọn repo ở hộp "Thêm terminal".
- Sơ đồ Luồng tự động động (Dynamic Flow): bỏ hoàn toàn logic gán cứng tĩnh và fallback lấy 2 task trong quá khứ (`awaiting_review` / `state.tasks.slice(0, 2)`). Luồng chỉ xuất hiện khi Agent 0 thực sự đang gọi agent hoặc giao việc (task `running`/`queued`, hoặc workflow nhiều bước đang chạy). Khi Agent 0 ở trạng thái chờ lệnh và chưa có agent nào đang làm việc, sơ đồ hiển thị trạng thái chờ (placeholder) kèm tùy chọn xem lại nhanh sơ đồ của các nhiệm vụ trước đó nếu cần.
- Chưa làm: tự hợp nhất mã giữa worktree của các bước khác agent; nút bật/tắt thông báo trên giao diện; test giao diện trình duyệt cho khối Workflow.
