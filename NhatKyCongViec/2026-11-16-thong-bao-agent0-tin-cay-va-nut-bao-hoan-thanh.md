# Nhật ký công việc — Thông báo `[AO]` tin cậy hơn và nút "Báo Agent 0 hoàn thành"

**Ngày:** 16/11/2026
**Dự án:** `C:\CongViec\agent\agent-orchestrator`
**Trạng thái bàn giao:** Code và test xong, chưa commit (đúng quy ước repo: không commit/push khi chưa được yêu cầu). Chưa thử với các cửa sổ agy thật đang chạy dài; mọi kiểm tra là test tự động và ảnh chụp giao diện thật với dữ liệu giả.

## Yêu cầu của người dùng

1. Xem vì sao thông báo từ các cửa sổ agy đến Agent 0 bị trễ và đôi khi sai (review), rồi làm theo tất cả đề xuất.
2. Thêm một nút trên cửa sổ agent để báo Agent 0 là agent đã hoàn thành.

## Nguyên nhân đã xác định (đọc code + `logs/ao-thong-bao-sai.md`, chưa tái hiện trên agy thật)

- Dòng `[AO] ... đã xong` suy ra từ việc terminal im lặng, qua nhiều lớp chờ (debounce 4 giây, spinner 30 giây, dấu hiệu mềm 180 giây, dấu hiệu cứng 1200 giây), gửi mỗi lần một dòng cách nhau 5 giây.
- Phát hiện bận/rảnh dựa trên dòng cuối của luồng byte, nhưng TUI vẽ lại từng vùng bằng cursor-move nên dòng đó có thể là footer cũ.
- Yên lặng không đồng nghĩa với xong: chờ lệnh build, chờ subagent, lỗi mạng, hết quota, cửa sổ mới chưa giao việc.
- Sau khi bị báo sớm, terminal chỉ được báo lại khi có spinner hoặc dấu hiệu bận; Agent 0 khởi động lại thì mọi terminal đang yên bị đánh dấu "đã báo" mà không báo gì.

## Đã làm

| Đề xuất | Thay đổi | Nơi |
|---|---|---|
| Đổi câu thông báo | `[AO] agy-N yên lặng (chưa xác nhận đã xong) — thông báo tự động của dashboard, không phải yêu cầu của người dùng. Trạng thái xem ở read_terminal(agy-N).` | `terminals.py` (`notify_agent0`) |
| ~~Bằng chứng tiến độ~~ | **Đã gỡ cùng ngày theo yêu cầu của chủ dự án** (dòng `[AO] Có tiến triển` ghép báo cáo cho mọi terminal dùng chung thư mục, lặp nhiều lần, làm Agent 0 hiểu nhầm). Đã xóa `evidence.py`, luồng theo dõi, khóa cấu hình `terminal_evidence_interval_seconds` và tệp `evidence-snapshot.json` trong thư mục state. | — |
| Nhận diện lỗi | Lỗi mạng, hết quota, lỗi agent được báo riêng: `agy-N có lỗi (lỗi mạng): <trích ngắn>`, không báo "yên lặng" | `terminals.py` (`terminal_error`) |
| Đọc màn hình thật | Bộ giả lập màn hình tối thiểu dựng lại khung hiện tại từ luồng byte; hai dòng cuối của màn hình quyết định bận (`esc to cancel`, spinner) hay rảnh (`? for shortcuts`); không có tín hiệu thì quay về luật cũ | `screen.py` (mới), `is_terminal_spinning` |
| Gộp thông báo, nhận biết đã gửi/đã nhận | Nhiều terminal yên cùng lúc gộp thành một dòng. Sau 6 giây kiểm tra dòng đã hiện trong cửa sổ Agent 0 chưa, ghi vào `terminal-audit.jsonl` (`source: ack`, `seen`), đếm `notices_unconfirmed`. | `_type_notice`, `check_acks` |
| Báo lại sau khi báo sớm | Có thêm ít nhất 4000 byte output sau khi báo (và không phải do đổi cỡ cửa sổ) thì tính là làm việc lại | `update_interactive_idle` |
| Agent 0 khởi động lại | Terminal đã có việc và đang yên được báo một lần cho Agent 0 mới (trước đây bị nuốt) | `notify_agent0` |
| Nút "Báo Agent 0 hoàn thành" | Biểu tượng chuông ở đầu nhóm nút của cửa sổ agent tương tác (không có ở Agent 0 và cửa sổ worker). Gọi `POST /api/terminals/<id>/notify-done`; Agent 0 nhận `[AO] Chủ dự án xác nhận <id> đã hoàn thành (bấm nút trên cửa sổ, không phải thông báo tự động). Vẫn đối chiếu commit và báo cáo trước khi nghiệm thu.` Từ chối kèm thông báo rõ nếu Agent 0 chưa mở hoặc đang có người gõ. | `terminals.py` (`notify_done`), `web.py`, `app.js` |
| Quy tắc Agent 0 | Mục 1 trong `rules.py` và `docs/TINH-NANG-QUY-TAC-DIEU-PHOI-AGENT.md` mô tả bốn loại dòng `[AO]` mới | `rules.py`, docs |

## Kiểm chứng

- `tests/test_terminal_signals.py` (mới, 21 test): màn hình, lỗi, gộp dòng, báo lại, nút, đã gửi/đã nhận, dạng dòng cuối của agent. Tắt thử từng cơ chế (báo lại hàng loạt, đọc màn hình, nhận diện lỗi, theo dõi đã nhận) thì test tương ứng đỏ.
- Test cũ chỉ sửa câu chữ mong đợi: `test_idle_busy.py`, `test_idle_rearm.py`, `test_interactive_idle.py`.
- `tests/flow_ui.cjs`: thêm kiểm tra nút (vị trí đầu nhóm, không có ở Agent 0 và worker, một yêu cầu mỗi lần bấm, đúng route, thông báo thành công và lỗi). Hai cỡ ảnh chụp, sáng và tối: nút thẳng hàng, thanh tiêu đề `scrollWidth = clientWidth`, trang 460/460 và 1280/1280.

## Còn tồn tại, cần chủ dự án biết

- `tests/flow_ui.cjs` dòng 295 vốn đang đỏ trên cây làm việc: test mong menu của ô lọc agent có 5 mục, nhưng các thay đổi chưa commit từ trước (thêm provider `gemini_web`) làm thành 6. Chưa sửa vì không thuộc việc này; bản sao có chỉnh số đó thì toàn bộ `flow_ui` đạt.
- Tín hiệu "xong" dựa bằng chứng (đặc tả 6.5: commit mới, báo cáo mới, tiến trình build) hiện KHÔNG có trong công cụ nữa. Agent 0 vẫn tự đối chiếu commit và báo cáo theo quy tắc 5.11.
- "Đã nhận" chỉ kiểm dòng đã hiện trong cửa sổ Agent 0 (đoạn đầu 25 ký tự); không biết Claude Code đã xử lý dòng đó hay chưa. Dòng không hiện chỉ được ghi và đếm, không tự gửi lại.
- Ngưỡng 4000 byte cho việc báo lại là ước lượng; nếu thấy báo lặp, chỉnh `REARM_BULK_BYTES`.
- Cần commit để lưu lại: các tệp mới `screen.py`, `tests/test_terminal_signals.py` chưa được theo dõi bởi git.

## Bổ sung cuối ngày: `PROMPT-CHUNG.md` mục D (ngoài repo, `C:\AgentControl\studio-state\prompts\`)

- Nguyên nhân agent trả về lệch quy ước: dòng cuối chỉ có hai dạng và dạng `HOÀN TẤT:` đòi hash commit, trong khi các agent đợt CTRL-WEB không commit được (sandbox chặn `git`) và quy trình mới bảo làm liền 3 phần. Agent tự viết "Phần 1/3 xong, chờ build".
- Đã sửa mục D: ba dạng dòng cuối (`HOÀN TẤT: <hash>`, `HOÀN TẤT (CHƯA COMMIT): ...`, `ĐANG CHỜ AGENT 0: <lý do>`), cấm cách viết khác, và khi làm liền nhiều phần thì không in dòng cuối cho đến hết gói. Sao lưu bản cũ: `PROMPT-CHUNG.md.bak-16-11`.
- `terminals.py`: `SOFT_DONE_MARKER` nhận thêm dạng `HOÀN TẤT (CHƯA COMMIT):` để dấu "đang làm" cũ được xóa.
- Tệp chung của đợt `PROMPT-CTRL-WEB-CHUNG-DOT2.md` do Agent 0 đang sửa trực tiếp, chưa đụng; mục 6 của nó chưa nhắc ba dạng dòng cuối (nó chỉ trỏ tới `PROMPT-CHUNG.md`).

## Bổ sung buổi chiều: làm cho quy định chung thật sự đến được Agent 0

**Vấn đề (chủ dự án nêu):** Agent 0 đôi khi không áp dụng `PROMPT-CHUNG.md` và cách điều phối trong tài liệu.

**Nguyên nhân có bằng chứng:** prompt của Agent 0 (`examples/AGENT0-PROMPT.md`, `rules.py`, và `agent0-prompt.generated.md` đang dùng thật) không hề nhắc `PROMPT-CHUNG.md`; việc "giao việc lần đầu thì bắt agent đọc nó" chỉ là một yêu cầu bằng lời ghi ở `docs/DIEU-PHOI-TU-DONG.md` dòng 142, nên mất khi sang chat mới hoặc nén ngữ cảnh. Hai bản `PROMPT-CHUNG.md` đã lệch nhau; tệp đợt chồng lên nhau và không nhắc mục D. `get_orchestration_rules` không cập nhật trạng thái "đã nhận". **Giả thuyết chưa kiểm:** prompt 22 KB làm loãng các điểm quan trọng; Agent 0 không biết khi quy tắc vừa đổi.

| Đề xuất | Đã làm | Nơi |
|---|---|---|
| 1. Đưa tệp chung vào quy tắc | Tham số `common_prompt_file` (trống = `PROMPT-CHUNG.md` trong thư mục prompt nếu có) và `common_prompt_enforce` (bật); ô nhập và ô tích trong Cài đặt | `rules.py`, `app.js` |
| 2. Ép bằng công cụ | `Terminals.send` từ chối dòng ĐẦU TIÊN gõ vào cửa sổ agent mới nếu không chứa đường dẫn tệp chung, kèm đúng câu cần dùng. Không chặn lệnh `/...` và cửa sổ resume; dòng sau tự do | `terminals.py` (`require_common_prompt`) |
| 3. Một bản chuẩn | Bản chuẩn: `C:\AgentControl\studio-state\prompts\PROMPT-CHUNG.md`. Hai bản chép trong repo đã ghi đè bằng bản chuẩn; `tools/Sync-PromptChung.ps1` (`-Check`) đồng bộ; test giữ hai bản không lệch. `PROMPT-CHUNG-DOT2.md` thêm mục D vào danh sách đọc; `PROMPT-CTRL-WEB-CHUNG-DOT2.md` mục 6 thêm đoạn trỏ về mục D (sao lưu `.bak-16-11`) | tệp prompt, `tools/`, `tests/test_common_prompt.py` |
| 4. Báo khi quy tắc đổi | Lưu / đặt mặc định / khôi phục quy tắc: Agent 0 đang chạy mà chưa có bản đó nhận một dòng `[AO] Quy tắc điều phối của chủ máy vừa đổi (bản <mã>) ... Gọi get_orchestration_rules ...`. Gọi `get_orchestration_rules` thì bản đó được ghi là đã nhận (trước đây chỉ ghi khi khởi động Agent 0) | `terminals.py` (`rules_changed`), `web.py`, `mcp.py` |
| 5. Đưa điểm quan trọng lên đầu | Khối "Những điều không được bỏ" (5 mục) đứng ĐẦU `agent0-prompt.generated.md`, trước prompt lõi, và mở đầu bản trả về của `get_orchestration_rules` | `rules.py` (`top_block`) |

**Kiểm chứng:** `tests/test_common_prompt.py` (19 test). Tắt thử cổng chặn, thông báo quy tắc đổi và khối đầu prompt thì test tương ứng đỏ. `tests/rules_ui.cjs` đạt (thêm kiểm tra ô mới và việc gửi giá trị). Ảnh chụp thật hộp thoại quy tắc ở cỡ rộng và hẹp, sáng và tối: trường mới theo mẫu, form có 20 điều khiển (trước là 19), không tràn ngang.

**Cần chủ dự án biết:**
- **Ép buộc tự bật trên máy này** sau khi khởi động lại Agent Studio, vì tệp `C:\AgentControl\studio-state\prompts\PROMPT-CHUNG.md` đã tồn tại. Agent 0 sẽ bị từ chối ở dòng giao việc đầu tiên cho mỗi cửa sổ agent mới nếu thiếu đường dẫn đó. Tắt: bỏ tích "Ép dòng giao việc đầu tiên..." trong Cài đặt, hoặc đổi đường dẫn tệp chung.
- Quy tắc mới chỉ đến Agent 0 sau khi nó khởi động lại hoặc gọi `get_orchestration_rules`; Agent 0 đang chạy sẽ nhận dòng thông báo ngay khi lưu.
- Đã dùng lại cơ chế `Terminals.send`, nên cổng chặn chỉ áp dụng cho dòng Agent 0 gõ qua `send_to_terminal`; dòng bạn tự gõ vào cửa sổ agent không bị chặn.
- Chưa thử với Agent 0 và agy thật; mọi kiểm tra là test tự động và ảnh chụp với dữ liệu giả.
