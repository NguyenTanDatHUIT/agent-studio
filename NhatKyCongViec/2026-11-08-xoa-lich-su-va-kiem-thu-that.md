# Nhật ký 2026-11-08 (vòng cuối): xóa lịch sử, kiểm thử CLI thật, resume agy

Nhánh: `feat/chat-history-clean`. Codex bỏ qua vì gói ChatGPT Plus đã hết.

## Việc đã làm
1. **Chức năng xóa lịch sử** (trước đó chưa có, trong khi transcript có thể chứa dữ liệu nhạy cảm):
   - `store.conversation_delete`, `Terminals.delete_conversation` / `delete_all_conversations`.
   - API: `POST /api/conversations/<id>/delete` (body rỗng), `POST /api/conversations/delete-all` (body `{"confirm": true}`).
   - UI: nút "Xóa" ở từng dòng, nút "Xóa tất cả" trên thanh công cụ, đều hỏi xác nhận; phiên đang mở bị vô hiệu hóa.
   - Bảo vệ: token + Origin (như resume), không có trên bridge Agent 0, từ chối phiên đang mở, chỉ xóa file nằm trong `state/transcripts` và không phải symlink (đường dẫn trong DB không được tin), có ghi audit (`delete`, `delete_all`).
2. **Resume cho Antigravity** (trước đó id agy không bao giờ được lưu nên "Mở lại" không dùng được):
   - Khảo sát agy thật: mỗi hội thoại là file `<id>.db` trong `~/.gemini/antigravity-cli/conversations/`, được tạo ở tin nhắn đầu tiên.
   - Thêm `scan_agy_session()` (dò file mới tạo sau lúc mở terminal, bỏ id đã dùng, chọn file sớm nhất, thăm dò tối đa 15 phút) và khóa `agy_claim` để hai terminal agy không lấy trùng id.
3. **Kiểm thử CLI thật có kiểm tra nhớ ngữ cảnh** (lần trước chỉ chứng minh mở được phiên):
   - Claude Code: nhớ `TANGO-4417` sau resume.
   - Agent 0 (Claude + MCP): nhớ `KILO-8820` sau resume.
   - Antigravity: id dò được, resume nhớ `ZULU-3391`.
4. **Sửa tài liệu**: hướng dẫn (xóa, agy), kiến trúc (API xóa, dò id agy), báo cáo kiểm thử (bảng E thật, nhóm G, xóa, agy, ghi chú số ca và thời gian chạy), review bảo mật (thêm TH-09), `SECURITY.md` và `docs/ARCHITECTURE.md` (đuôi file transcript ghi sai `.txt`, đúng là `<conversation_id>.log`).

## Quyết định tự đưa ra
- **Xóa không đụng dữ liệu của CLI** (`~/.claude`, `~/.codex`, `~/.gemini`): Agent Studio chỉ xóa thứ nó tạo. Nếu muốn xóa cả phiên gốc của CLI, đó là thay đổi riêng và rủi ro hơn.
- **Dò id agy theo thời điểm tạo file, không theo thư mục**: agy không ghi `cwd` trong tên file nên không thể đối chiếu như Codex. Hạn chế đã ghi trong tài liệu kiến trúc: nếu bạn chạy agy ngoài Agent Studio đúng lúc, id có thể bị nhận nhầm.
- **Script kiểm thử CLI thật chưa đưa vào repo**: chúng gõ phím vào hộp thoại tin cậy và dùng tài khoản thật, nên để ở thư mục tạm (`scratchpad`). Nếu muốn lặp lại hằng ngày, cần làm thành công cụ riêng có cờ xác nhận.

## Phát hiện khi làm
- Hộp thoại "tin cậy thư mục" của Claude mặc định chọn "No, exit": nhấn Enter trần sẽ thoát. Script phải nhấn mũi tên xuống rồi Enter. (Của agy mặc định là "Yes".)
- Điều kiện kiểm tra "nhớ" bằng đếm số lần xuất hiện mã có thể đúng nhờ phần lịch sử tự in lại khi resume; vì vậy đã đối chiếu thêm dòng trả lời cuối trong màn hình (`●TANGO-4417`, `●KILO-8820`, `ZULU-3391` ngay sau câu hỏi).

## Kết quả test (xem số liệu thật ở cuối khi chạy xong, mục "Kết quả chạy lại")
- `tests.test_history`: 38 test (28 cũ + 5 xóa/API + 5 dò agy), OK.
- `flow_ui.cjs` và `layout_ui.cjs`: PASS, `flow_ui` có thêm kịch bản xóa (hủy xác nhận, xóa một phiên, xóa tất cả).

## Việc còn lại / không làm được
- **Codex**: chưa kiểm tra thật (hết gói Plus). Phần dò id Codex chỉ có test bằng thư mục giả.
- Stress test (`tools/stress_transcripts.py`) không chạy lại ở vòng này vì không sửa phần ghi transcript.
- Chưa có cách xóa theo bộ lọc (chỉ xóa một hoặc tất cả); chưa có tự động xóa theo tuổi.
