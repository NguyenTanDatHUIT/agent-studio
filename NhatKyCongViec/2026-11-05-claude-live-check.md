# Kiểm thử Claude thật — 05/11/2026

## Phạm vi

Người dùng yêu cầu kiểm thử với Claude. Dùng Claude Code 2.1.318 đã đăng nhập,
adapter restricted hiện có và repo calculator riêng tại `.local-run/live-check/repo`.
Không dùng worker giả. Chỉ giao sửa `calculator.py`; runner chạy test riêng.

## Kết quả

- Preflight: CLI hỗ trợ đủ cờ adapter, kiểm tra đăng nhập đạt; không ghi credential.
- Task `a46acfe0b1bc446998ea0960` trong sandbox hiện tại timeout sau 120,049 giây,
  không stdout/stderr, không thay đổi code và chưa chạy test.
- Thử lại ngoài sandbox của phiên Codex, qua yêu cầu nâng quyền thực thi được chấp nhận;
  vẫn giữ các cờ Claude restricted, không thêm shell tools hoặc bỏ kiểm soát adapter.
- Task `ceaee817ca5d4a53942bb1f7`: worker exit 0 trong 11,449 giây,
  chỉ đổi `return a - b` thành `return a + b` trong `calculator.py`.
- Functional test exit 0 trong 0,120 giây: `add(2, 3) == 5`, `add(-1, 1) == 0`,
  `add(0, 0) == 0`; stdout: `3 functional checks passed`.
- Engine tạo review bundle thành công; task ở `awaiting_review`.
- SHA-256 patch: `96fb3d6026f825c3550f5531b919a5c2c5d5f637b4b1006ade848c30d5428c0c`.
- CLI báo input 6, output 455, cache read 15313, cache creation 2266 token;
  `total_cost_usd` khoảng 0,0151573 USD, là số CLI báo, chưa đối chiếu hóa đơn.

Artifact local được ignore: `.local-run/claude-latest-result.json`,
`.local-run/claude-latest-review.json`; log/task/worktree ở state của live-check.

## Giới hạn

Đã xác minh enqueue → Claude sửa code → runner test → review bundle trên repo thử.
Chưa ghi approve/export hoặc áp patch lên nhánh tích hợp; chưa kiểm thử Claude
trên dự án thật. Lượt thử lại thành công ngoài sandbox không chứng minh nguyên
nhân chính xác của timeout lượt đầu hoặc mức cô lập của CLI. Không đổi cấu hình
provider, không sửa source orchestrator, không commit/merge/push trong lượt này.
