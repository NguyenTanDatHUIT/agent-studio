# Báo cáo xác minh bản đóng gói

Web app được bổ sung và kiểm tra ngày 05/11/2026: **45/45 test Python pass**,
gồm 8 HTTP test mới. Kiểm thử DOM qua HTTP với demo offline cũng pass.
Xem [WEB-APP.md](WEB-APP.md) và [WEB-TEST-RESULTS.txt](WEB-TEST-RESULTS.txt).
Các kết quả bên dưới là baseline trước khi bổ sung web app.

Ngày: 2026-11-05. Môi trường chạy kiểm thử: Windows, Python 3.12.10,
Git for Windows 2.55.0.windows.5.

* **37/37 unit/integration tests PASS**, thời gian 84.486 giây.
* Chạy bằng `python -m unittest discover -v` trong workspace.
* TEMP/TMP được trỏ vào scratch có quyền ghi trong workspace vì TEMP mặc định
  của môi trường chạy bị hạn chế. Không cần sửa mã để bỏ qua bài kiểm thử.
* Có test hai runner Python subprocess đồng thời, SQLite claim, worktree riêng,
  MCP stdio subprocess và toàn bộ review/export gate.
* Có test Windows Job Object: process cháu không sống tiếp sau timeout.
* Có test bảo toàn main/index, scope, commit/ref thay đổi, test fail hoặc sửa code,
  digest sai, edit sau duyệt, Git hook/filter và argument injection.
* Mã Python qua kiểm tra cú pháp; các file JSON mẫu parse thành công.

CLI cài trên máy được đối chiếu `--help`: Codex CLI 0.166.0,
Claude Code 2.1.318. **Chưa gọi model Claude/Codex thật, chưa xác minh đăng nhập,
quyền thuê bao, chi phí hoặc bảo đảm sandbox của một phiên worker AI thật.**
Test suite dùng CLI giả để tạo thay đổi và JSON usage fixture; các số token
trong fixture không phải mức tiêu thụ thực tế.

Không chạy trên repository dự án của người dùng. Không commit/merge/push bất kỳ
mã dự án thật nào. Package install từ pip/wheel chưa được kiểm tra; chạy module
trực tiếp từ source đã được kiểm tra. Chưa có audit chống agent độc hại hoặc
kiểm thử tải lớn, Git LFS/submodule, HTTP MCP, VM/WSL sandbox.

Chi tiết kết quả: [TEST-RESULTS.txt](TEST-RESULTS.txt).
