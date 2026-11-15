# Bàn giao phiên PM (15/11/2026): TỔNG HỢP đợt S2 Controller HIS_EMR Nhi Đồng, để mở chat mới làm tiếp

**Bản mới nhất, đọc bản này TRƯỚC.** Nó thay thế phần "trạng thái" của các bản 14/11 (vẫn giữ để tra chi tiết). Thứ tự đọc: (1) tệp này; (2) `2026-11-14-ban-giao-phien-pm-s2-04-b-c-d-review-doc-lap.md` mục 2, 7; (3) `TRANG-THAI-CHOT-KE-HOACH-CONTROLLER-2026-11-14.md`; (4) `2026-11-14-ban-giao-phien-pm-s2-02g-s2-04a-s2-02a-s2-04a-a.md` mục 4 (danh sách câu hỏi `Z-*`). Quyết định chủ dự án ở `C:\CongViec\itc-git\HIS_EMR\NhiDong\Plan Coding\Controller\QUYET-DINH-*.md` (đặc biệt `QUYET-DINH-CHUNG-S2-DOT-14-11-V1.md`, `QUYET-DINH-S2-02-VA-S2-15-V1.md`, `QUYET-DINH-S2-18-RA-VIEN-Q1-Q6-V1.md`, `QUYET-DINH-S2-09-HO-SO-NOI-TRU-V1.md`). `prompts\` = `C:\AgentControl\studio-state\prompts\`. Repo công cụ: `C:\CongViec\agent\agent-orchestrator`; repo code: `C:\CongViec\itc-git\HIS_EMR` (thư mục việc `NhiDong\`).

## 0. Việc đầu tiên khi mở chat mới
1. Gọi `get_orchestration_rules`, `list_terminals` (lúc bàn giao chỉ còn Agent 0; mọi cửa sổ agent đã đóng).
2. **Chỉ đạo của chủ máy ngày 14/11 cần xác nhận lại ở chat mới:** (a) "từ giờ không giao việc cho claude nữa": việc mới giao cho **agy** (Hydrogen việc dễ, Argon việc khó; luôn `/model` rồi gõ tên model); (b) "dừng giao việc" lúc cuối phiên 14/11: chat mới do chủ máy mở để **thực hiện**, nên hỏi chủ máy việc nào làm trước. Bộ nhớ: `feedback_khong-giao-viec-cho-claude.md`, `feedback_giu-cmd-cung-ngu-canh.md`.
3. Mỗi cửa sổ agy mới phải chạy `/add-dir C:\wt` và `/add-dir C:\CongViec\itc-git\HIS_EMR` (chủ máy đã cho phép Agent 0 chạy lệnh này). Nếu không, agy bị `Access denied` khi `cd C:\wt\...` và không chạy được `git`. **Chưa kiểm được** agy chạy `git`, build, test được sau `/add-dir`: thử bằng một lệnh nhỏ trước khi giao việc lớn. Không dùng `BypassSandbox`; nếu bị chặn thì dừng và hỏi chủ máy.
4. Chính sách giao việc: tệp prompt trong `prompts\PROMPT-*.md`, dòng gõ vào terminal tối đa 500 ký tự, **tạo prompt và worktree xong TRƯỚC khi gửi lệnh**, mở đầu lệnh bằng "bỏ qua chữ nháp trong ô nhập" (ô nhập của cửa sổ Claude hay có chữ gợi ý mờ), kiểm báo cáo + `git log` + `git status` thay vì tin dòng `[AO] ... đã xong` (hay đến sớm/trễ), tự chạy lại test quan trọng.

## 1. Đã xong và nghiệm thu (chưa merge, chưa push các nhánh code; số test "xanh" là số agent báo trừ chỗ ghi PM tự chạy lại)
| Việc | Nhánh | HEAD | Ghi chú |
|---|---|---|---|
| S2-02-G rà dữ liệu y lệnh miệng | không có | | `NhiDong\Database\review_fixes\s2_02_g_verbal_order_check.sql` (4 truy vấn, CHƯA CHẠY, chưa commit) |
| S2-02-a cổng chặn y lệnh miệng nội trú | `wt/ctrl-s2-02a` | `4d36bf2a` | Test PG 14 pass. Chờ chạy 4 truy vấn trên bản sao (Truy vấn 1 và 3 phải ra 0 dòng) |
| S2-04-a (3 bảng vào `RowLockTables.All` + helper) | `wt/ctrl-s2-04a` | | PM đã đọc code: thứ tự khoá khớp |
| S2-04-b rời Cấp cứu (ma trận, dịch truyền, vượt cổng, tự ngưng chọn lọc) + sửa F1/F3/F4 + fix2 | `wt/ctrl-s2-04a` | `ada26f3e` | Review độc lập 3 pha: ĐẠT CÓ ĐIỀU KIỆN. PM tự chạy lại sau fix2: Phase6 127 pass/2 skip (C2, T11c), Postgres.DrillTests 18 pass |
| S2-04-c hook nhập viện (tiếp nối dịch truyền, CLS, dọn tài nguyên) + sửa C3/C1 + fix2 | `wt/ctrl-s2-04a` | `ada26f3e` | như trên |
| S2-04-d review độc lập (test đối kháng) | `wt/ctrl-s2-04d`, `wt/ctrl-s2-04d-c`, `wt/ctrl-s2-04d-3` | `cfd9f37c`, `4edd81a0`, `37ec381c` | Chỉ test; đã cherry-pick vào `wt/ctrl-s2-04a` |
| S2-15-a `DepartmentScopeResolver` (mặc định `Open`) | `wt/ctrl-s2-15` | `4c5e394e` | chưa review độc lập |
| S2-15-c (4 node `noi_tru.toan_vien_*`), S2-15-j (`ClockNow`), S2-15-h (Nursing theo Mode) | `wt/ctrl-s2-15` | `4c5e394e` | Script `PatchFeaturesToanVienScope_Postgres.sql` CHƯA chạy. `Phase5.Tests` không biên dịch được (xung đột EF Core 8.0.34, có sẵn) nên `PermissionGroupTests` chưa chạy |
| S2-05 hàm thuần `NewbornNameLabels` | `wt/ctrl-s2j` | `ccc6a36b` | chưa nối vào luồng nào (chờ W8) |
| S2-09, S2-14, S2-16, S2-17 | `wt/ctrl-s2d` | `fbf2de37` | |
Dừng đúng chỗ (không mã, báo cáo + câu hỏi): S2I (S2-01, S2-03), S2-06, S2-07 và S2-08 (Nhóm K). Báo cáo ở `prompts\BAOCAO-CTRL-S2I.md` `-2.md`, `BAOCAO-CTRL-S2J.md` `-2.md`, `BAOCAO-CTRL-S2K.md`.

## 2. Worktree/nhánh hiện tại
Worktree còn: `C:\wt\ctrl-base` (nền chỉ-đọc `a2a23e37`), `C:\wt\ctrl-s2-04a` (HEAD `ada26f3e`, sạch), `C:\wt\ctrl-s2k` (Nhóm K, sạch, `180c20e6`), `C:\wt\nhidong-newuikit` (không phải của phiên này). Đã gỡ 10 worktree không dùng (nhánh `wt/*` còn nguyên, commit không mất): muốn dùng lại `git worktree add C:/wt/<tên> <nhánh>`. Repo HIS_EMR `main` = `b3c8ee28` (chưa merge/push gì). Không đụng `C:\Users\tsmda\.codex\worktrees\*` và 3 stash cũ.

## 3. Quyết định đang chờ chủ dự án (trả lời "theo đề xuất" được)
1. **P1 (S2-04, thiếu quy đổi đơn vị thuốc):** hiện cổng dược cấp cứu tạm tính 1 lượt dùng = 1 đơn vị cấp và **vẫn có thể chặn, không có đường vượt** (agent báo chủ dự án đã chọn trong cửa sổ của nó); PM đề xuất đổi sang chỉ cảnh báo hoặc thêm đường vượt có thẩm quyền, để tránh kẹt bệnh nhân.
2. **F5:** ai được vượt cổng rời khoa (E9: Trưởng khoa/Trực lãnh đạo): hướng đã duyệt = node quyền riêng ("sửa `DefaultFeatures.cs`", việc riêng, chưa có prompt); cần nhóm giữ quyền mặc định.
3. **C2:** lần truyền dịch tiếp nối phải kết thúc được: phương án A (cho `RecordInfusionEvent(END)` chạy sau nhập viện), B (đồng bộ khi hoàn tất việc điều dưỡng), hoặc C (nhập lượng dịch lúc nhận bệnh); ai có quyền; thiếu `VolumeInfused` thì chặn hay ghi sau. Reviewer: nếu coi C2 là chặn go-live thì S2-04-c CHƯA ĐẠT.
4. **Xác nhận lựa chọn PM đã áp dụng:** C1 (gắn `AdmissionId`, giữ `ACTIVE`), P3 (không đồng bộ `EncounterId`), F3/C3 (mốc quá giờ giữ nguyên, khuôn `DiscontinueOrder`), gọi lặp lần hai `ConfirmEmergencyDeparture` (giữ từ chối "đã kết thúc trước đó").
5. **Nhóm K:** K1 bảng `clinical_result_views` (đề xuất có; khoá `(source_type, result_id, doctor_id)`; LAB và IMAGING) hay chỉ `LogBusinessEvent`; K2 N+1 xét nghiệm: PM đề xuất sửa `ClinicalController.PartLabResults` ở đợt Controller bằng hàm gom lô có sẵn (agent đề xuất thêm `ListClinicalResultsPagedAsync`).
6. **Còn từ bản trước:** `J5` (khoá đường huỷ cũ), `Y1…Y4` đã quyết theo đề xuất nhưng chưa giao; "admin mục" của nút cha `noi_tru` có tự có 4 cờ xem toàn viện không; luật `Closed` cho khu cấp cứu chưa gán khoa; `is_service_account` cần DDL; mẫu "Phiếu công khai thuốc" của bệnh viện; lịch trực bác sĩ (S2-20); S2-21 ghi DB; chọn giữ hay xoá nhánh test review.
7. **Việc chỉ chủ dự án làm:** chạy 4 truy vấn S2-02-G trên **bản sao/replica**; quyết định tích hợp các nhánh `wt/*` vào đâu (không merge/push khi chưa yêu cầu rõ); kiểm tra đăng nhập Claude nếu cần.

## 4. Hàng đợi việc (khi chủ máy cho giao; giao cho agy)
1. Nghiệm thu thêm fix2 (đọc mã P1 và việc rút hàm `DispenseAdministrationReconciler` sửa `SubmitInpatientDrugReturnCommand.cs`; chạy `SurfaceTests`), rồi **review độc lập Pha 4** (người review khác người viết; Argon). Quy tắc: tối đa 2 lần sửa trước khi thay cửa sổ (đã dùng 2 lần sửa).
2. F5 (node quyền vượt cổng) sau khi có nhóm giữ quyền; C2 sau khi chọn phương án.
3. Nhóm L (`PROMPT-CTRL-S2L.md`: S2-10, S2-12, S2-19), Nhóm M (`PROMPT-CTRL-S2M.md`: S2-11, S2-22, S2-20 chỉ phân tích): chưa giao, không bị chặn bởi câu hỏi đã biết (S2-11 có thể cần DDL: phải dừng nếu cần). Prompt K/L/M/I/J đã bỏ dòng `...-selftest`.
4. S2-04 phần còn lại cần DDL/quyết định; S2-02-b…f (dùng helper S2-04-a; chờ Z-9 DDL); S2-18 các hàm Service mới (nhiều gói, review độc lập); S2-06 (bảng `payment_refund_requests`, J1…J4 đã quyết); S2-01/S2-03 (Y1, Y2, Y4); S2-15-b/d/e/f/g/i.
5. Sửa tài liệu kế hoạch lệch quyết định: D6 dòng 357 (`SETTLED`), D7 dòng 152 và 706 (S2-09), mockup/đặc tả tab Ra viện (bỏ điều kiện "đã tất toán" khỏi cổng "Xác nhận kết thúc đợt"), số action mới (~407–419).
6. Sau khi chốt kế hoạch Controller: lập kế hoạch dựng view theo màn (màn "sẵn sàng" là mọi action đã có Service và không còn câu hỏi mở, ví dụ phần lớn Dược nội trú; màn "bị chặn" ghi rõ câu hỏi/việc S2 chặn: Ra viện, Rời cấp cứu, Nhận bệnh hết giường, Ca đêm). Chưa biết quy ước view/JS của `Web.HIS` và vai trò worktree `nhidong-newuikit`.

## 5. Lệnh kiểm tra hữu ích
- Test PG: `cd <worktree>\NhiDong\Source\NET8\Tests && bash /c/AgentControl/studio-state/build-slot.sh bash ./run-with-temp-postgres.sh Phase6.Tests --filter "FullyQualifiedName~<lớp>"` (và `Postgres.DrillTests`, `Phase4.Tests --filter SurfaceTests`). Docker Desktop phải bật (tắt thì test `[PgFact]` bị Skipped, không đỏ). Tối đa 3 lượt build đồng thời qua `build-slot.sh`.
- Kiểm tên hàm Service trong báo cáo agent: `C:\AgentControl\studio-state\verify-fn.sh "<báo cáo>.md"` và `check-pairs.py` (trong `tools-controller\`).
- Chống lỗi: `QUY-LUAT-CHONG-LOI-LAP-LAI.md`, `PROMPT-CHUNG.md` (mục F worktree).

## 6. Bài học vận hành (tóm tắt)
- Review độc lập nhiều pha tìm được lỗi thật mà người viết bỏ sót (F1, F3, F4, C1, C2, C3, P1) và reviewer tự đính chính khẳng định sai; luôn dùng cho việc đổi hành vi lâm sàng. Người sửa đã có lúc tự sửa test cũ: dặn rõ "hỏi trước khi sửa kỳ vọng test cũ".
- Lệnh Bash chứa heredoc với dấu backtick bị chặn bởi kiểm tra an toàn: dùng công cụ ghi tệp. `git worktree remove` (không ép) an toàn khi cây sạch.
- Sandbox agy chặn worktree ngoài workspace: xem mục 0.3. Agy từng thử `BypassSandbox` (bị hook chặn); không gợi ý và không dùng.
- Chủ dự án có lúc gõ trực tiếp vào cửa sổ agent (ví dụ chọn hướng P1 trong claude-9); khi đọc báo cáo agent phải hỏi lại chủ dự án nếu nó viết "bạn đã chọn".

## 7. Trạng thái repo công cụ `C:\CongViec\agent\agent-orchestrator`
Nhánh `main` = `origin/main` (`https://github.com/NguyenTanDatHUIT/agent-studio.git`) lúc bàn giao, **trước khi commit nhật ký**. Có 17 tệp mã đang sửa dở và nhiều tệp mã chưa theo dõi (`gemini_bridge.py`, `mcp_server.py`, `browser_extension/`, `tmp/`, `tools/...`, `tests/...`) **không phải do phiên PM này làm**; phiên này chỉ commit các tệp trong `NhatKyCongViec/` và không đụng các tệp đó (xem commit nhật ký để biết đã push chưa).
