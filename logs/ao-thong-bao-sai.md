# Nhật ký thông báo `[AO]` sai / thiếu (để chủ dự án tổng hợp và sửa công cụ)

Mục đích: mỗi lần dòng `[AO] ...` do dashboard gõ vào Agent 0 **sai, thiếu hoặc gây hiểu nhầm**, Agent 0 ghi thêm MỘT mục ở cuối file này (mới nhất cuối). Chỉ ghi **điều quan sát được** (kèm bằng chứng); suy đoán nguyên nhân ghi riêng ở dòng `Giả thuyết`, không trộn.

Mẫu một mục (thêm xuống cuối):
```
## <ngày giờ> — <terminal> — <LOẠI>
- Loại: BÁO SỚM | BÁO LẶP | THIẾU THÔNG BÁO | BÁO SAI NỘI DUNG | GÂY HIỂU NHẦM
- [AO] nói: "<trích nguyên văn>"
- Thực tế: <điều thật sự xảy ra lúc đó>
- Bằng chứng: <terminal đọc được / giờ sửa tệp / commit / tiến trình>
- Mong muốn: <công cụ nên làm gì>
- Giả thuyết (nếu có): <nguyên nhân có thể, ghi rõ chưa kiểm>
```
Nguồn mã liên quan (đã đọc 10/11/2026): `agent_orchestrator/terminals.py` — `BUSY_MARKER` (dòng ~91), `DONE_MARKER` (~92), `terminal_looks_busy` (~96), `notify_agent0` (~1038), dòng tạo thông báo "đã xong" (~1099).

---

## 10/11/2026 ~10:10 — agy-4 — BÁO SỚM
- Loại: BÁO SỚM
- [AO] nói: "[AO] agy-4 đã xong. Dùng read_terminal(agy-4) để xem kết quả."
- Thực tế: agy-4 còn đang làm (đối chiếu test để hoàn thiện báo cáo `XACMINH-A1-A2-PHAN-A.md`); xong thật khoảng 10:14 (terminal `idle: true`, báo cáo không đổi ~4 phút).
- Bằng chứng: `read_terminal(agy-4)` lúc ~10:11 vẫn hiện `Working...`; `list_terminals` lúc 10:14 mới `idle: true`.
- Mong muốn: không báo "xong" khi terminal còn dòng `Working...`.
- Giả thuyết (chưa kiểm): `BUSY_MARKER = Running\s*[(…]` không khớp các chuỗi của agy (`Working...`, `Reading file...`, `Editing files...`, `Running command...`), nên terminal yên vài giây bị coi là rảnh.

## 10/11/2026 ~10:11 — agy-5 — BÁO SỚM
- Loại: BÁO SỚM
- [AO] nói: "[AO] agy-5 đã xong. Dùng read_terminal(agy-5) để xem kết quả."
- Thực tế: agy-5 còn đang ghi `XACMINH-A1-A2-PHAN-B.md` (tệp đổi lúc 10:10:46, ngay trước khi kiểm). Xong thật khoảng 10:14.
- Bằng chứng: terminal lúc ~10:11 hiện `Editing files...` / `Working...`; mtime tệp báo cáo 10:10:46; `idle: true` lúc 10:14.
- Mong muốn: như mục trên.
- Giả thuyết (chưa kiểm): như mục trên.

## 10/11/2026 ~09:25–10:00 — claude-3 — BÁO LẶP
- Loại: BÁO LẶP
- [AO] nói: "[AO] claude-3 đã xong. Dùng read_terminal(claude-3) để xem kết quả." — xuất hiện **ít nhất 9 lần** cho cùng một agent trong khoảng ~35 phút (kể cả sau khi chủ dự án dặn không theo dõi agent này).
- Thực tế: báo cáo của claude-3 đã ghi xong từ ~09:27 (`BAOCAO-PHANTICH-USECASES-ADMISSION.md` 44.9 KB); các lần sau không có gì mới được hoàn thành.
- Bằng chứng: dòng `[AO]` lặp lại trong hội thoại của Agent 0 nhiều lần liên tiếp; `list_terminals` có lúc `idle: true`, có lúc `idle: false` cho claude-3.
- Mong muốn: mỗi lần chuyển trạng thái bận → rảnh chỉ báo MỘT lần; không báo lại khi không có việc mới; có cách tắt thông báo cho từng terminal.
- Giả thuyết (chưa kiểm): `idle_notified` bị đặt lại khi terminal có output nhỏ (nhấp nháy/prompt), nên cờ báo một lần bị xoá; hoặc `update_interactive_idle` đảo trạng thái theo từng đợt output của Claude Code.

## 10/11/2026 (nhiều lần trong phiên) — mọi agent — GÂY HIỂU NHẦM
- Loại: GÂY HIỂU NHẦM
- [AO] nói: dòng `[AO] <terminal> đã xong. Dùng read_terminal(...) để xem kết quả.` được gõ vào ô nhập của Agent 0, nên Claude Code hiển thị nó như "người dùng gửi tin nhắn mới" (`The user sent a new message while you were working: [AO] ...`).
- Thực tế: đó là thông báo tự động của dashboard, không phải yêu cầu của người dùng; Agent 0 phải tự nhắc lại điều này mỗi lần để không làm theo.
- Bằng chứng: trong `terminals.py`, thông báo loại `notice` (dòng ~1063) có đuôi "— thông báo tự động của dashboard, không phải yêu cầu của người dùng", còn thông báo `đã xong` (dòng ~1099) **không có đuôi này**.
- Mong muốn: thêm đuôi nhận diện tự động cho cả thông báo `đã xong`; câu "Dùng read_terminal(...) để xem kết quả" nghe như mệnh lệnh nên đổi thành mô tả trạng thái ("terminal yên lặng, chưa xác nhận việc đã xong").

## 10/11/2026 — agy-2 (và các agent build) — THIẾU THÔNG BÁO
- Loại: THIẾU THÔNG BÁO
- [AO] nói: (không có dòng nào cho các commit mới của agy-2: `10f4ae81`, `16298851`, `814d100c`, `6586440d`, `708fb1f8`, `39f55a5e`, `311cf190`, `fe2692ac`, `33d87c9d`).
- Thực tế: mỗi commit là một mốc tiến độ có ý nghĩa; `[AO]` chỉ báo khi terminal yên.
- Bằng chứng: Agent 0 phải tự dựng bộ theo dõi nền (`Monitor`, đã dừng 10:50 theo yêu cầu chủ dự án) để biết commit mới và báo cáo vừa ghi.
- Mong muốn: công cụ tự theo dõi `HEAD` của repo đang làm và tệp `BAOCAO-*`/`REVIEW-*`/`XACMINH-*` trong thư mục prompt, gửi MỘT dòng khi đổi (đặc tả `docs/TINH-NANG-QUY-TAC-DIEU-PHOI-AGENT.md` mục 6.5, chưa cài).

## 10/11/2026 — mọi agent — BÁO SAI NỘI DUNG (giả thuyết, cần kiểm)
- Loại: BÁO SAI NỘI DUNG
- [AO] nói: "đã xong" khi terminal yên.
- Thực tế: agent có thể đang build/test hoặc ghi báo cáo mà terminal không in gì mấy phút; ngược lại agent đã xong mà không có `[AO]`.
- Bằng chứng: đã gặp ở các mục trên (agy-4, agy-5); các phiên trước (bàn giao 10/11) ghi nhận cả hai chiều.
- Mong muốn: tín hiệu "xong" dựa bằng chứng (commit mới + báo cáo đã ghi + cây sạch + không có tiến trình build), `[AO]` chỉ là gợi ý.

## 10/11/2026 ~12:00 — agy-3 — BÁO SỚM (khi agent đang build)
- Loại: BÁO SAI NỘI DUNG (sớm)
- [AO] nói: "agy-3 đã xong" (lần 2 trong phiên, sau khi giao PHẦN 1 bỏ Rules).
- Thực tế: terminal còn `Editing files...`, footer `1 task(s)`, có 9 tiến trình dotnet, chưa có commit mới, cây còn tệp `M`/`D` chưa commit.
- Bằng chứng: read_terminal(agy-3) + `git log`/`git status` + `tasklist` lúc ~12:00. (Lần 1 trong phiên: [AO] báo sau khi chủ dự án đổi model, chưa có việc nào — cũng không phải "xong việc".)
- Mong muốn: như mục trên (tín hiệu dựa bằng chứng; bỏ qua khi footer có `task(s)` đang chạy).

## 10/11/2026 ~14:35 (giờ máy) — agy-3 — THIẾU THÔNG BÁO (A4.4+A4.5 xong, Agent 0 không nhận [AO])
- Loại: THIẾU THÔNG BÁO (hoặc báo không tới được Agent 0; chưa phân biệt được)
- [AO] nói: (Agent 0 không nhận dòng `[AO] agy-3 đã xong` nào cho việc A4.4+A4.5).
- Thực tế: agy-3 đã commit `e4e76894` và `37790035`, ghi `BAOCAO-A4.4.md` lúc 14:31, in kết quả cuối ra terminal; chủ dự án thấy "xong" trước Agent 0. Agent 0 chỉ phát hiện khi chủ dự án nhắc, vì lịch kiểm đã giãn 23 phút.
- Bằng chứng: `git log` (2 commit mới), `BAOCAO-A4.4.md` mtime 14:31, `read_terminal(agy-3)` hiện tóm tắt cuối; không có dòng [AO] nào trong ngữ cảnh Agent 0 giữa các lượt.
- Ghi chú: có thể [AO] đã gửi khi Agent 0 đang bận một lượt khác và bị mất/không hiện; công cụ nên ghi nhận "đã gửi/đã nhận" để phân biệt.
- Mong muốn: tín hiệu dựa bằng chứng (commit mới + báo cáo mới) gửi chắc chắn tới Agent 0 (spec `docs/TINH-NANG-QUY-TAC-DIEU-PHOI-AGENT.md` mục 6.5).

## 10/11/2026 ~15:05 (giờ máy) — agy-3 — THIẾU THÔNG BÁO (A5.0 xong, Agent 0 không nhận [AO])
- Loại: THIẾU THÔNG BÁO (lần 2 trong phiên; lần 1: A4.4+A4.5)
- [AO] nói: (không có dòng `[AO] agy-3 đã xong` nào tới Agent 0 cho A5.0; chủ dự án thấy "agy-3 báo xong" trước).
- Thực tế: commit `49d3dc9c` + `BAOCAO-A5.0.md` (15:03) + cây sạch + không còn dotnet; terminal agy-3 in tóm tắt cuối.
- Bằng chứng: `git log`, mtime báo cáo, `read_terminal(agy-3)`. Agent 0 chỉ phát hiện khi chủ dự án hỏi "đã đọc thông báo của agy 3 chưa".
- Mong muốn: như mục trước (tín hiệu dựa bằng chứng: commit mới + báo cáo mới; ghi nhận đã gửi/đã nhận).

## 10/11/2026 ~15:10 (giờ máy) — agy-1 — THIẾU THÔNG BÁO (FIX-A44 xong, Agent 0 không nhận [AO]) — lần 3
- Loại: THIẾU THÔNG BÁO
- [AO] nói: (không có dòng `[AO] agy-1 đã xong` tới Agent 0; chủ dự án báo "agy 1 đã xong" trước).
- Thực tế: commit `531eb58d` ở worktree C:/wt/fixa44 (nhánh wt/fixa44) + `BAOCAO-WT-FIXA44.md` (15:10) + dotnet = 0. Lưu ý: commit nằm ở WORKTREE, không ở cây chính nên bộ theo dõi `HEAD` của repo chính (nếu có) sẽ không thấy.
- Bằng chứng: `git -C C:/wt/fixa44 log main..HEAD`, mtime báo cáo, `read_terminal(agy-1)`.
- Mong muốn: bộ theo dõi commit/báo cáo cần hỗ trợ NHIỀU worktree (`git worktree list`) và thư mục báo cáo chung; ghi nhận đã gửi/đã nhận.

## 10/11/2026 ~15:15 (giờ máy) — agy-3 — [AO] ĐÚNG NGHĨA "yên lặng" nhưng không phải "xong việc"
- Loại: BÁO SAI NỘI DUNG (nhẹ, theo thiết kế)
- [AO] nói: "agy-3 đã xong".
- Thực tế: agy-3 đang TẠM DỪNG chờ lệnh "được build" của Agent 0 (đã viết sửa lần 1, chưa build/commit).
- Mong muốn: phân biệt "yên lặng" với "xong"; có thể thêm trạng thái "chờ" khi terminal đang hỏi/chờ người.

## 10/11/2026 ~15:20 (giờ máy) — agy-3 — BÁO SỚM (đang build nền)
- Loại: BÁO SAI NỘI DUNG (sớm)
- [AO] nói: "agy-3 đã xong" (lần 2 trong cùng đoạn).
- Thực tế: agy-3 vừa được báo "được build" và đang chạy `dotnet build` (tác vụ nền, footer `1 task(s)`), 9 tiến trình dotnet, chưa có commit sửa lần 1.
- Bằng chứng: `read_terminal(agy-3)` (dòng `dotnet build ... running`), `tasklist`, `git log` (HEAD vẫn 49d3dc9c).
- Mong muốn: bỏ qua/hoãn thông báo khi footer có tác vụ nền đang chạy (`task(s)`), hoặc khi terminal còn dòng `... running`.

## 10/11/2026 ~15:25 (giờ máy) — agy-4 — BÁO SỚM (đang chờ subagent)
- Loại: BÁO SAI NỘI DUNG (sớm)
- [AO] nói: "agy-4 đã xong".
- Thực tế: agy-4 (worktree C:/wt/a6a) vừa `Spawned 2 subagents` cho E-02/E-03/E-04/E-18a và ghi "Đang chờ 2 subagent hoàn tất"; A6a.1 chưa commit; có dotnet đang chạy.
- Bằng chứng: `read_terminal(agy-4)`, `git -C C:/wt/a6a log` (mới có A6a.0), tasklist.
- Mong muốn: không phát "đã xong" khi terminal còn dòng "chờ subagent"/footer tác vụ nền; công cụ chưa nhìn thấy subagent.

## 10/11/2026 ~15:28 (giờ máy) — agy-1 — NGUYÊN NHÂN GỐC (giả thuyết mạnh): công cụ không coi agy-1 là "yên" vì dòng cuối buffer còn dấu hiệu spinner
- Loại: THIẾU THÔNG BÁO có hệ thống riêng cho agy-1 (chủ dự án quan sát: "agy 1 xong thì không gửi thông báo, các agy khác thì có").
- Bằng chứng (đọc mã + audit, KHÔNG sửa công cụ):
  1. `terminal-audit.jsonl`: công cụ CÓ gửi `[AO] agy-1 đã xong` ở 12:06:08 và 14:56:51, nhưng KHÔNG gửi lúc agy-1 xong FIX-A44 (~15:10) và REVIEW-A5.0 (~15:23). Các agy khác (agy-2/3/4/5) có dòng audit tương ứng. => lỗi do công cụ không phát, không phải Agent 0 không nhận.
  2. `list_terminals` lúc 15:28 báo `agy-1 idle: false` dù agent đã ghi xong báo cáo.
  3. `terminals.py` `update_interactive_idle`: chỉ coi yên khi `not is_terminal_spinning(buf)`; `is_terminal_spinning` chỉ xét DÒNG KHÔNG TRỐNG CUỐI của 4000 byte cuối buffer và khớp `BRAILLE_SPINNERS` hoặc `generating...`/`esc to cancel`. `read_terminal(agy-1, clean=false)` cho thấy dòng cuối còn `esc to cancel ... Gemini 4 Argon · medium` và frame `⣾ Generating...` (TUI vẽ lại từng vùng bằng cursor-move nên dòng cuối của luồng byte có thể là footer cũ, không phải màn hình hiện tại).
  4. Cửa sổ do chủ dự án mở và đã chạy rất lâu (nhiều việc) nên buffer có nhiều frame spinner; agy-2..6 do Agent 0 mở thường kết thúc bằng khối chữ tóm tắt nên dòng cuối không còn spinner.
- Chưa kiểm chứng: cần dump `buffer[-4000:]` của agy-1 ngay lúc nó yên để thấy dòng cuối thật.
- Đề xuất cho người sửa công cụ: (a) không dựa vào "dòng cuối của luồng byte" mà dựng lại màn hình cuối (terminal emulator) hoặc nhận diện footer `? for shortcuts` (rảnh) / `esc to cancel` (bận) trên khung hiện tại; (b) coi là yên khi KHÔNG có output nào trong N giây BẤT KỂ spinner còn trong buffer (đã có debounce) trừ khi spinner còn animate (output vẫn tới); (c) thêm trường `idle_reason` vào `list_terminals` (spinner/busy-marker/debounce/chưa armed) để chẩn đoán; (d) với cửa sổ idle quá `IDLE_BUSY_CAP` nhưng vẫn `idle:false`, gửi cảnh báo riêng.
- Giải pháp tạm phía Agent 0: `PROMPT-CHUNG.md` mục D ép dòng cuối terminal là `HOÀN TẤT: <hash>...` hoặc `ĐANG CHỜ AGENT 0: ...` để dòng cuối của luồng byte không còn là spinner; Agent 0 tiếp tục kiểm bằng commit + báo cáo.

## 10/11/2026 ~15:40 (giờ máy) — agy-6 — BÁO SỚM (đang chờ subagent)
- Loại: BÁO SAI NỘI DUNG (sớm) — lần 2 cùng kiểu với agy-4 (~15:25): agent đang chờ subagent.
- [AO] nói: "agy-6 đã xong".
- Thực tế: agy-6 (worktree C:/wt/a52, A5.2) vừa `Spawned 2 subagents` (O-07/O-09/O-03), ghi "Đang chờ 2 subagent hoàn tất", chưa commit (0 commit, 2 tệp đổi); footer còn spinner `Generating`.
- Bằng chứng: `read_terminal(agy-6)`, `git -C C:/wt/a52 log main..HEAD` (rỗng).
- Mong muốn: không phát "đã xong" khi có `Spawned N subagents` hoặc `Agent(...) Reading file` ở cuối buffer (agent chính chưa kết thúc).
- Thống kê trong hôm nay (Agent 0 ghi nhận): [AO] THIẾU: A4.4, A5.0, agy-1 FIX-A44, agy-1 REVIEW-A5.0, agy-4 A6a (khi xong thật Agent 0 không nhận); BÁO SỚM: agy-3 (build nền) x2, agy-4 (subagent), agy-6 (subagent); đúng: agy-1 (14:56), agy-3 (12:xx).

## 10/11/2026 ~15:45 (giờ máy) — agy-7 — BÁO SỚM (đang build nền, vừa nhận lệnh "ĐƯỢC BUILD")
- Loại: BÁO SAI NỘI DUNG (sớm)
- [AO] nói: "agy-7 đã xong".
- Thực tế: agy-7 (worktree C:/wt/a51, A5.1) vừa nhận lệnh build, dòng `● [15:44:01] ... dotnet build ... running`, footer `Working...`; 0 commit, báo cáo vẫn nháp (cổng "CHƯA ĐO"). Trước đó (~15:42) agy-7 cũng "yên" khi dừng chờ lệnh build.
- Bằng chứng: `read_terminal(agy-7)`, `git -C C:/wt/a51 log main..HEAD` (rỗng), tasklist có dotnet.
- Mong muốn: như các mục trước (hoãn thông báo khi có tác vụ nền đang chạy / dòng `... running`).

- 11/11 ~00:02: [AO] báo "agy-18 đã xong" nhưng agent chỉ idle sau LỖI MẠNG ("There was a network issue connecting to the server", Error ID 95a0dd18-a9d3-4c89-9515-d3e040074f56-326): lệnh SỬA LẦN 1 chưa được thực hiện (git: 0 commit mới, `AllowSelfOverride` còn nguyên). Công cụ coi "yên lặng" là "xong". Đã gửi lại lệnh.
