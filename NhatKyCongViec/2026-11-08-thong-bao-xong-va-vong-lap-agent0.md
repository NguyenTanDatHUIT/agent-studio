# Nhật ký 2026-11-08: thông báo "agy đã xong" bắn sai và lặp, vòng lặp giao việc của Agent 0

## Yêu cầu và câu hỏi
Người dùng giao Agent 0: "cho agy làm; xong thì đánh giá; chưa đạt thì bắt sửa; đến lần 2 vẫn chưa xong thì đóng cửa sổ đó, tạo cmd agy mới; nhớ đưa file prompt cho agy". Hỏi: khi agent xong, Agent 0 có hiểu để tự ra lệnh tiếp không? Sau đó dán một đoạn màn hình cho thấy dòng `[AO] agy-1 đã xong` lặp nhiều lần dù agy vẫn đang chạy.

## Thử nghiệm thật (Claude Code thật làm Agent 0, repo tạm)
- **agy thật làm đúng ngay lần đầu:** Agent 0 mở agy, ghi file prompt, gửi một dòng "đọc file ...", nhận `[AO] agy-1 đã xong`, tự chạy kiểm tra thật trên file (không chỉ tin chữ trong terminal) rồi báo kết quả. Bản thân Agent 0 đã hiểu cách làm tiếp.
- **agy giả luôn không làm được:** Agent 0 đánh giá "Chưa đạt: hello.py chưa được tạo", gửi yêu cầu sửa (lần 2), vẫn chưa đạt, rồi **gõ chữ `exit` vào agy** (vì không có công cụ đóng) và mở agy-2. Việc gõ `exit` là cách chữa cháy, với agy thật chữ đó có thể bị coi là lời nhắn.
- **Không cần duyệt:** 0 lần hộp thoại duyệt cho `open_terminal`/`send_to_terminal`, vì Agent 0 chạy ở auto mode ("Allowed by auto mode"). Tài liệu cũ nói "mỗi lần hỏi xác nhận" chỉ đúng khi auto mode tắt.
- **File prompt:** Agent 0 lưu ở thư mục tạm của chính nó (ngoài repo); agy đọc được, không phải duyệt quyền.

## Nguyên nhân thông báo sai và lặp (dữ liệu thật của người dùng)
- Phiên agy-1 im lặng 5 giây đến **443 giây** (đang `dotnet test`) trong khi dòng cuối là `○ Running (cd ...)`; dashboard chỉ kiểm tra "yên lặng 4 giây và không có spinner" nên báo xong. Chính Agent 0 nhận ra: "Dòng [AO] báo xong lần này cũng sai".
- codex-6 bị báo 5 lần liên tiếp (im lặng 5s, 18s, 42s, 87s, 106s) khi dòng cuối luôn là footer rảnh: do báo cáo focus của xterm (`ESC[I`/`ESC[O`) bị coi là thao tác của người dùng và đặt lại cờ "đã báo".
- Mỗi thông báo sai làm Agent 0 tốn một lượt (git status, docker ps...) và tự nhận "tôi sẽ không đánh giá".

## Đã sửa
1. `Session.write()` bỏ qua đầu vào chỉ gồm mã điều khiển (focus/chuột/vị trí con trỏ). Gõ chữ và Enter vẫn đặt lại cờ.
2. `terminal_looks_busy()`: `Running (` chưa có `Ran (`/`Worked for`/`· done` theo sau nghĩa là đang chạy lệnh; chặn thông báo, tối đa `IDLE_BUSY_CAP` = 20 phút im lặng. Kiểm tra bằng chính log thật: **5 trong 6** thông báo sai của agy-1 bị chặn (lần còn lại ngay sau khi mở, agent mới khởi động).
3. Công cụ `close_terminal` (MCP và bridge): Agent 0 đóng được **chỉ terminal do chính nó mở**. Trước đó bridge cố ý từ chối `/close` (test `test_bridge_stays_read_only_except_input`); đã giữ ranh giới bằng cách không cho đóng cửa sổ người dùng mở, Agent 0 hay worker, và cập nhật test cũ (400 thay vì 401).
4. `AGENT0-PROMPT.md`: thêm mục "Giao việc cho agent tương tác" với quy trình 7 bước (file prompt có tiêu chí kiểm tra được, chờ agent sẵn sàng, không poll, coi `[AO] đã xong` chỉ là gợi ý và kiểm tra bằng bằng chứng thật, sửa lần 1 và lần 2, rồi `close_terminal` + `open_terminal`, không gõ `exit`).

## Kiểm chứng
- Test: `tests/test_idle_busy.py` (busy markers, lệnh dài im lặng không báo, báo sau khi xong, dấu hiệu cũ không giữ mãi, báo cáo focus qua ConPTY thật không đặt lại cờ), 2 test đóng terminal, 21 test idle cũ vẫn pass.
- Chạy lại kịch bản "agy không làm được" với prompt và công cụ mới: xem kết quả cuối của phiên.

## Hạn chế / cần bạn quyết
- Bộ nhận diện dựa trên chữ trên màn hình (`Running (`, `Ran (`...) của agy/Claude/Codex hiện tại; đổi giao diện CLI có thể làm lệch. Có trần 20 phút để không im lặng vĩnh viễn.
- Lần báo đầu tiên ngay sau khi mở terminal vẫn có thể xảy ra khi agent khởi động chậm.
- `close_terminal` vẫn chịu cơ chế duyệt của Claude Code (không tự duyệt trước); ở auto mode không hỏi.
- Dòng thông báo vẫn ghi "đã xong" (giữ nguyên để không phá test và thói quen); prompt của Agent 0 giải thích đúng nghĩa.
