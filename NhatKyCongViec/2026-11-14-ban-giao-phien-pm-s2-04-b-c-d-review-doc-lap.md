# Bàn giao phiên PM (14/11 ~18:10, cập nhật 22:45): S2-04-b, S2-04-c đã viết và review độc lập ba pha; sửa lần 2 DỞ; S2-15-c/h xong; Nhóm K dừng; chờ chủ dự án quyết

> **ĐỌC MỤC 7 TRƯỚC (trạng thái lúc 22:45, chủ máy đã dặn dừng giao việc).** Các mục 1 đến 6 là trạng thái lúc 18:10; mục 1 (bảng worktree) và mục 5 (cửa sổ agent) đã lỗi thời.

Đọc kèm (theo thứ tự): `2026-11-14-ban-giao-phien-pm-s2-02g-s2-04a-s2-02a-s2-04a-a.md` (mục 10 là trạng thái lúc 15:55, nay một phần lỗi thời), `TRANG-THAI-CHOT-KE-HOACH-CONTROLLER-2026-11-14.md`, và quyết định `NhiDong\Plan Coding\Controller\QUYET-DINH-CHUNG-S2-DOT-14-11-V1.md`. `prompts\` = `C:\AgentControl\studio-state\prompts\`. Repo code `C:\CongViec\itc-git\HIS_EMR`, worktree ở `C:\wt\`. Số "xanh" bên dưới là số agent báo, trừ chỗ ghi "PM tự chạy lại".

## 1. Nhánh/worktree sau phiên (chưa merge, chưa push)
| Nhánh / worktree | HEAD | Nội dung | Trạng thái |
|---|---|---|---|
| `wt/ctrl-s2-04a` (`C:\wt\ctrl-s2-04a`) | `b2990b48` | S2-04-a (RowLockTables + helper), S2-04-b (rời Cấp cứu) + sửa F1/F3/F4, S2-04-c (hook nhập viện) + sửa C3/C1 | Sạch. Review độc lập: ĐẠT CÓ ĐIỀU KIỆN cả hai |
| `wt/ctrl-s2-15` (`C:\wt\ctrl-s2-15`) | `4c5e394e` | S2-15-a (resolver, mặc định Open), S2-15-c (4 cờ toàn viện), S2-15-j (`ClockNow`), S2-15-h (Nursing theo Mode) | Sạch. Chưa có review độc lập |
| `wt/ctrl-s2-02a` | `4d36bf2a` | S2-02-a cổng chặn y lệnh miệng nội trú | Đạt (chờ chạy 4 truy vấn S2-02-G trên bản sao) |
| `wt/ctrl-s2j` | `ccc6a36b` | S2-05 hàm thuần `NewbornNameLabels` | Đạt; S2-06 dừng (5 câu J1…J5, đã quyết J1…J4; J5 mở) |
| `wt/ctrl-s2-04d` | `61c3ba07` (+ `cfd9f37c`) | Test review Pha 1 của claude-5 | Chỉ test |
| `wt/ctrl-s2-04d-c` | `4edd81a0` (+ `a83af337`) | Test review Pha 2 | Chỉ test |
| `wt/ctrl-s2-04d-3` | `37ec381c` | Test review Pha 3 | Chỉ test |
`ctrl-s2-04a` đã nhận test review qua cherry-pick (`3e516ffb`, `f4c9df1a`, `53b2150f`). Ba nhánh test review (`04d`, `04d-c`, `04d-3`) cần quyết giữ hay gộp test vào `ctrl-s2-04a`.

## 2. S2-04: quy trình đã chạy và kết quả (3 pha review độc lập, người review = claude-5, người viết = claude-9)
- **S2-04-b** (commit `8da3d7f0`, `b61fed09`): ma trận loại y lệnh × hướng rời; dịch truyền chặn mọi hướng; không còn tự gán `ENDED`; vượt cổng chỉ `TRANSFER`/`DEATH` có cờ + lý do; lệnh miệng chặn; tự ngưng chọn lọc; `EmergencyReadinessOne` dùng chung cổng. PM tự chạy lại: 44 pass (lần đầu), 112 pass (sau sửa).
- **Review Pha 1 (S2-04-b): ĐẠT CÓ ĐIỀU KIỆN**, 0 CAO, 3 TRUNG (F1 bỏ sót `dispense_records`, F3 huỷ cả mốc quá giờ, F4 phiếu trả `SUBMITTED` chặn gây kẹt), F5 cần quyết (vượt cổng không kiểm thẩm quyền, E9 ghi chỉ Trưởng khoa/Trực lãnh đạo), 6 THẤP (F6…F11). Sửa lần 1: `48e3e90e` (F1), `4ec84fd2` (F4), `73ee9662` (F3).
- **S2-04-c** (commit `d1b6e9bc`, `10476b6d`): hook `ApplyAdmissionHandover` trong `ReceivePatient`: tiếp nối dịch truyền (`HANDOVER`, việc điều dưỡng), giữ CLS chờ kết quả, ngưng y lệnh theo dõi, dọn vị trí/bằng chứng/thẻ người nhà. PM tự chạy lại: 14 pass (Postgres.DrillTests).
- **Review Pha 2 (S2-04-c): ĐẠT CÓ ĐIỀU KIỆN**, 0 CAO, 3 TRUNG (C1 y lệnh thuốc/lệnh miệng mồ côi, C2 lần truyền tiếp nối không kết thúc được, C3 huỷ mốc quá giờ), 4 THẤP (C4…C7). Sửa lần 1: `08972d2c` (C3), `b2990b48` (C1: gắn `AdmissionId`, giữ `ACTIVE`); C2 chỉ khảo sát. Người viết có sửa test cũ `S204c_3` (thêm mốc quá giờ): PM đã đọc diff, là củng cố không phải nới. PM tự chạy lại: Phase6 117 pass/2 skip (T11c, C2), Drill 14 pass.
- **Review Pha 3 (xác nhận sửa): cả hai ĐẠT CÓ ĐIỀU KIỆN**; báo cáo `BAOCAO-CTRL-S2-04D-PHA3.md`, commit test `37ec381c`. **Phát hiện mới do chính các sửa:**
  - **P1 (TRUNG)**: sửa F1 trừ thẳng liều (mg) khỏi số lượng cấp (viên) không quy đổi đơn vị: cấp 10 viên, một cử 500 mg ⇒ lệnh rời khoa vẫn thành công. Đây chính là F6 (đã khai là THẤP) nhưng nay là đường đối soát chính của lượt cấp cứu thuần. Test đỏ giữ `Skip`.
  - **P2 (THẤP)**: việc tương lai bị huỷ nhưng lịch liên kết quá giờ vẫn `Planned` (ở cả rời khoa và hook nhập viện). **P3 (THẤP)**: C1 gắn `AdmissionId` nhưng không đồng bộ `EncounterId`, chưa có test.

## 3. Việc cần chủ dự án quyết (chặn go-live S2-04)
1. **F5**: ai được vượt cổng rời khoa (E9: Trưởng khoa/Trực lãnh đạo, hay quyền thường + lý do như Z-4). Đề xuất PM: node quyền riêng "vượt cổng rời khoa" (sửa `DefaultFeatures.cs`, việc riêng).
2. **P1/F6**: quy đổi đơn vị thuốc. Đề xuất PM: tái dùng/rút ra hàm quy đổi sẵn có (`ComputeAdministeredQuantitiesForOrders` ở Inpatient) vào `Service.Core/Components/` để cả hai nơi dùng chung; nếu không có đường quy đổi thì báo "chưa đối soát được" kèm cảnh báo thay vì chặn cứng (tránh kẹt bệnh nhân). Cần xác nhận vì chạm hàm dùng chung và có thể đổi hành vi dược nội trú.
3. **C2**: lần truyền tiếp nối phải kết thúc được: chọn (A) cho `RecordInfusionEvent(END)` chạy sau nhập viện, (B) đồng bộ khi hoàn tất việc điều dưỡng truyền dịch, hoặc (C) nhập lượng dịch lúc nhận bệnh; chỉ định ai được kết thúc. Reviewer: nếu coi C2 là chặn go-live thì S2-04-c CHƯA ĐẠT.
4. **C1** (gắn đợt, giữ `ACTIVE`; PM đã chọn theo đề xuất, chưa được xác nhận) và **P3** (đồng bộ `EncounterId`); **F3/C3** (mốc quá giờ giữ nguyên, PM đã chọn theo khuôn `DiscontinueOrder`); **gọi lặp lần hai** (giữ từ chối "đã kết thúc trước đó").
5. Sau khi quyết: sửa lần 2 (tối đa 2 lần sửa theo quy tắc điều phối) cho P1, P2, P3; rồi review Pha 4 ngắn. Nếu vẫn chưa đạt sau 2 lần sửa thì thay cửa sổ (quy tắc mục 4.4).

## 4. Việc khác đã xong hôm nay (xem bản bàn giao 15:55 và `TRANG-THAI-...`)
S2-15-c (4 node `noi_tru.toan_vien_*`, script vá `features` chưa chạy), S2-15-j (3 chỗ `DateTime.Now` → `ClockNow()`), S2-15-h phần Nursing (khu cấp cứu chưa gán khoa đã dừng, 3 câu hỏi). Câu hỏi mới: "admin mục" của nút cha `noi_tru` có tự có 4 cờ xem toàn viện không; chặn `Closed` làm tiếp đón/quản trị không gắn khoa mất truy cập vòng tay và bàn giao; `Phase5.Tests` không biên dịch được (xung đột EF Core 8.0.34, lỗi có sẵn: `PermissionGroupTests` chưa chạy); `is_service_account` cần DDL. Quyết định chung đã ghi: `QUYET-DINH-CHUNG-S2-DOT-14-11-V1.md`.

## 5. Cửa sổ agent
`claude-5` (Sonnet 5.5; S2-15-a/c/h/j, S2I, J, review S2-04-d Pha 1-3): xong, chờ. `claude-9` (Sonnet 5.5; S2-04-b/c và hai lần sửa): xong, chờ sửa lần 2. Hai cửa sổ ăn chung hạn mức Sonnet (chưa đo). Đã đóng: agy-1, 2, 3, 4, 6, 7, 8. Chủ máy dặn: đóng cửa sổ không cần thiết, nhưng hạn chế đóng cửa sổ cùng ngữ cảnh với việc kế tiếp (đã lưu bộ nhớ).

## 6. Bài học vận hành thêm
- Dòng `[AO] ... đã xong` tiếp tục đến sớm hoặc trễ: luôn kiểm báo cáo (thời gian sửa), `git log`, `git status`, và tự chạy lại test quan trọng.
- Lệnh gõ vào terminal tối đa 500 ký tự; chi tiết để trong tệp prompt. Tệp prompt và worktree phải tạo xong TRƯỚC khi gửi lệnh (một lần gửi sớm làm claude-5 dừng đúng quy tắc).
- Trong ô nhập các cửa sổ Claude hay có chữ gợi ý mờ (không phải do Agent 0 hay chủ dự án gõ): luôn mở đầu lệnh bằng "bỏ qua chữ nháp" và không gửi Enter vào ô trống.
- Lệnh Bash chứa heredoc với dấu backtick bị chặn bởi kiểm tra an toàn ("65 command substitutions"): dùng công cụ ghi tệp thay vì heredoc.
- Review độc lập ba pha tìm được lỗi thật mà người viết bỏ sót (F1, F3, F4, C1, C2, C3, P1) và chính reviewer tự đính chính một khẳng định sai: nên giữ quy trình này cho mọi việc đổi hành vi lâm sàng.

## 7. Trạng thái cuối phiên (14/11 22:45) và việc đã làm sau 18:10

### 7.1. Chỉ đạo mới của chủ máy (đã lưu vào bộ nhớ)
- **18:40: "từ giờ không giao việc cho claude nữa"** (xem `feedback_khong-giao-viec-cho-claude.md`): việc mới giao cho agy (Hydrogen dễ, Argon khó), không giao `claude-N`. Việc Claude đã chạy thì để xong.
- **22:3x: "từ giờ dừng giao việc và cập nhật NhatKyCongViec"**: Agent 0 **không giao thêm việc nào** từ thời điểm này; chỉ nghiệm thu bằng bằng chứng và ghi nhật ký.
- Chủ máy đã dọn dẹp: yêu cầu xoá worktree không dùng (xong, 7.3) và **cho phép Agent 0 chạy `/add-dir`** cho agy (7.4).

### 7.2b. CẬP NHẬT 22:50: fix2 ĐÃ XONG về mặt báo cáo, PM đã tự chạy lại test; còn chờ review Pha 4 và 2 quyết định
- `BAOCAO-CTRL-S2-04-fix2.md` đã có (ghi 22:42), dòng cuối `HOÀN TẤT: ada26f3e`. Không còn thay đổi chưa commit ở `ctrl-s2-04a`. Diff so với `b2990b48` không xoá hay sửa dòng nào của test cũ (chỉ thêm 3 tệp test mới: `EmergencyDepartureS204Fix2Tests.cs`, `EmergencyDepartureS204dPha3Tests.cs` cherry-pick, `EmergencyAdmissionHandoverFix2Tests.cs`).
- **PM tự chạy lại (22:5x):** Phase6 (`EmergencyDeparture*`, `EmergencyAdmissionS204dCReviewTests`, kiến trúc, quy ước, hạ tầng): **127 pass, 0 fail, 2 skip** (C2 giữ `Skip` có chủ đích và `T11c_RT4` có sẵn). Postgres.DrillTests (`EmergencyAdmissionHandoverS204cTests`, `EmergencyAdmissionHandoverFix2Tests`, `EmergencyAdmittedHookTests`, `MoneyDrugReturnTests`): **18 pass, 0 fail**. Chưa chạy lại: Phase4 `SurfaceTests` (agent báo 4/4).
- **Nội dung đã làm (agent báo, PM chưa đọc kỹ từng dòng mã):** P1: rút hàm quy đổi đơn vị sang `Service.Core` (`DispenseAdministrationReconciler`), phiếu trả thuốc nội trú và cổng rời khoa cùng dùng; 3 test `MoneyDrugReturnTests` vẫn đạt. P2: huỷ việc kèm lịch liên kết, mốc quá giờ giữ nguyên, ở cả `ConfirmEmergencyDeparture` và hook nhập viện. P3: **không sửa mã** (agent cho rằng xác nhận lệnh miệng chỉ cần `AdmissionId`, đồng bộ `EncounterId` làm lệch liên kết LIS/RIS/dược), thêm test xác nhận lệnh miệng thuốc sau nhập viện.
- **Điểm cần chủ dự án quyết ngay (agent hỏi lại):** khi **thiếu quy đổi đơn vị** cổng dược cấp cứu hiện tạm tính 1 lượt dùng = 1 đơn vị cấp và **vẫn có thể chặn** (kèm ghi chú "thiếu quy đổi" trong thông báo), không có đường vượt. Agent nói "bạn đã chọn theo hàm dược nội trú" khi nó hỏi trong cửa sổ của nó (chủ dự án có gõ trực tiếp "tiếp tục" vào claude-9, không qua Agent 0). Điều này **khác chỉ đạo của Agent 0** (cảnh báo, không chặn) và đúng kiểu rủi ro kẹt bệnh nhân như F4: một thuốc thiếu quy đổi và ghi liều khác đơn vị có thể giữ người bệnh mà không có đường vượt. **Quyết:** giữ hướng này hay quay lại "chỉ cảnh báo" (nếu quay lại phải đổi kỳ vọng test P1). Đề xuất PM: quay lại "chỉ cảnh báo, không chặn", hoặc ít nhất cho đường vượt có thẩm quyền (liên quan F5).
- **Chưa được review độc lập:** rút hàm sửa `SubmitInpatientDrugReturnCommand.cs` (dược nội trú) và hành vi P1/P2/P3. Phải qua Pha 4 (người review khác claude-9, giao cho agy Argon) trước khi dùng. Chưa giao vì chủ máy đã dặn dừng giao việc.
- Cửa sổ claude-9 hiển thị "Not logged in · Please run /login" tại một thời điểm (22:3x); sau đó vẫn chạy xong. Cần chủ máy kiểm tra đăng nhập Claude nếu muốn dùng lại.

### 7.2. S2-04: sửa lần 2 (fix2) do claude-9 làm, trạng thái lúc 22:45 (ĐÃ LỖI THỜI: xem 7.2b ở trên)
- Prompt `PROMPT-CTRL-S2-04-fix2.md` (P1 quy đổi đơn vị thuốc, P2 lịch/việc nhất quán, P3 `EncounterId`/lệnh miệng thuốc sau nhập viện). Báo cáo `BAOCAO-CTRL-S2-04-fix2.md` **chưa tồn tại**; agent chưa ghi dòng `HOÀN TẤT`.
- **Bốn commit đã có** trên `wt/ctrl-s2-04a` (HEAD `ada26f3e`; trước đó `b2990b48`): `776828d6` (rút hàm quy đổi đơn vị dùng chung `DispenseAdministrationReconciler` ở `Service.Core`, đổi `SubmitInpatientDrugReturnCommand`), `e89f7a5f` (P1 ở helper cấp cứu), `e8f0bdd0` (P2), `ada26f3e` (P3: chỉ thêm test `EmergencyAdmissionHandoverFix2Tests.cs`). Diff so với `b2990b48`: 8 tệp, +1093/-290 (`SubmitInpatientDrugReturnCommand.cs` giảm 251 dòng, tạo `DispenseAdministrationReconciler.cs` 312 dòng; test mới `EmergencyDepartureS204Fix2Tests.cs`, cherry-pick `EmergencyDepartureS204dPha3Tests.cs`).
- **Cửa sổ claude-9 báo "Not logged in · Please run /login"** (phiên Claude mất đăng nhập hoặc hết hạn). Nó vẫn đang `Running shell command` (commit P3). Cây lúc 22:42 có thay đổi chưa commit hay không: chưa kiểm lại. **Chưa tự chạy lại test** (agent đang dùng worktree, tránh đụng).
- **Điểm lệch cần review (chưa được ai review):** (1) P1 khi **thiếu quy đổi đơn vị** commit ghi "tạm tính 1 lượt = 1 đơn vị cấp và nói rõ trong thông báo", khác chỉ đạo trong prompt ("cảnh báo, không chặn cứng, không coi đã dùng hết"); phải đọc mã để biết nó chặn hay cảnh báo. (2) Việc rút hàm sửa `SubmitInpatientDrugReturnCommand.cs` (dược nội trú, -251 dòng): phải chứng minh không đổi hành vi bằng test phiếu trả thuốc hiện có. (3) Có sửa test cũ nào không (prompt cấm sửa kỳ vọng test cũ khi chưa hỏi): chưa kiểm.
- **Cần làm tiếp (khi chủ máy cho giao việc lại):** nghiệm thu fix2 (đọc báo cáo khi có, `git diff b2990b48 HEAD`, tự chạy Phase6 + Postgres.DrillTests + Phase4 SurfaceTests), rồi review độc lập Pha 4 (xác nhận P1, P2, P3), người review phải là cửa sổ KHÁC (không phải claude-9). Vì chủ máy đã dặn không giao Claude: giao cho agy (Argon, vì là review lâm sàng), cần quyền worktree và `.git` (7.4). Nếu sau fix2 vẫn chưa đạt: theo quy tắc điều phối phải thay cửa sổ (đã dùng 2 lần sửa).
- **Quyết định còn chờ chủ dự án (không đổi so với mục 3):** F5 (node quyền "vượt cổng rời khoa"; hướng đã duyệt "theo đề xuất" nhưng chưa có prompt: cần nhóm giữ quyền mặc định), C2 (lần truyền tiếp nối phải kết thúc được: phương án A hay B, ai có quyền, thiếu `VolumeInfused` thì chặn hay ghi sau), xác nhận C1/P3/F3/C3, gọi lặp lần hai.

### 7.3. Worktree đã dọn (theo yêu cầu chủ máy ~19:40)
Đã gỡ bằng `git worktree remove` (không ép; từng cái đều sạch): `ctrl-t0`, `ctrl-s1`, `ctrl-s2d`, `ctrl-s2-02a`, `ctrl-s2-04d`, `ctrl-s2-04d-c`, `ctrl-s2-04d-3`, `ctrl-s2-15`, `ctrl-s2i`, `ctrl-s2j`. **Không xoá nhánh nào**; các commit còn nguyên: `wt/ctrl-s2-15` `4c5e394e`, `wt/ctrl-s2j` `ccc6a36b`, `wt/ctrl-s2-02a` `4d36bf2a`, `wt/ctrl-s2d` `fbf2de37`, `wt/ctrl-s2-04d-3` `37ec381c`, `wt/ctrl-s2-04d` `cfd9f37c`, `wt/ctrl-s2-04d-c` `4edd81a0`. Muốn làm tiếp: `git worktree add C:/wt/<tên> <nhánh>`. Còn lại ở `C:\wt\`: `ctrl-base` (nền chỉ-đọc `a2a23e37`), `ctrl-s2-04a` (S2-04, đang dùng), `ctrl-s2k` (Nhóm K, sạch, HEAD `180c20e6`), `nhidong-newuikit` (không phải của phiên này). Không đụng `C:\Users\tsmda\.codex\worktrees\*` và 3 stash cũ.

### 7.4. Sandbox của agy: nguyên nhân và cách đã xử lý
- agy-6, agy-7, agy-8, agy-10 đều bị `Access denied` khi `cd C:\wt\...` (sandbox chỉ cho workspace `C:\CongViec\agent\agent-orchestrator`). Chủ máy cấp quyền `C:\wt` cho agy-10: `cd` vào worktree được.
- Nhưng trong worktree agy-10 vẫn báo `fatal: not a git repository` vì thư mục `.git` của worktree trỏ vào `C:\CongViec\itc-git\HIS_EMR\.git` (ngoài sandbox) nên **agy không chạy được git/commit/build/test**. Chủ máy cho phép Agent 0 chạy `/add-dir`; **Agent 0 đã chạy `/add-dir C:\CongViec\itc-git\HIS_EMR` trong agy-10** (terminal xác nhận "Added C:\CongViec\itc-git\HIS_EMR to workspace"). **Chưa kiểm được** `git`, build và test của agy có chạy sau lệnh này hay không (đã dừng giao việc). Quyền chỉ áp cho cửa sổ agy-10 (mỗi cửa sổ agy mới cần chạy lại `/add-dir C:\wt` và `/add-dir C:\CongViec\itc-git\HIS_EMR`).
- Agy từng thử `BypassSandbox: true` (agy-7) và bị hook chặn: không dùng và đừng gợi ý dùng.

### 7.5. Nhóm K (agy-10, Hydrogen): S2-07, S2-08 dừng đúng chỗ, không mã, không commit
- Báo cáo `BAOCAO-CTRL-S2K.md` (`HOÀN TẤT: không có commit`). Đã kiểm bằng mã: chưa có `ReviewLabResult`; `RecordCriticalResultAction` có; `LabResult` không có cột `Reviewed*/Viewed*`; `CriticalResultViewMinutes = 30` (`InpatientSettings.cs:70`); N+1 ở `Web.HIS/Controllers/ClinicalController.cs` quanh :354-358 và :384; hàm gom lô `LisService.GetClinicalResultsForEncounterAsync` ở `Services/Service.LIS/LisService.cs:37` (báo cáo ghi thiếu thư mục `Services/`).
- **Cần chủ dự án quyết:** **K1** S2-07: tạo bảng `clinical_result_views` (đề xuất agent: có; khoá `(source_type, result_id, doctor_id)`, hỗ trợ `LAB` và `IMAGING`; kết quả nguy kịch có tự ghi `inpatient_critical_result_actions` không) hay chỉ `LogBusinessEvent`. **K2** S2-08: PM đề xuất phương án 1 (sửa `ClinicalController.PartLabResults` ở đợt Controller để dùng hàm gom lô và `LabOrderDetailIds`/`LabOrderIds` có sẵn, không viết thêm Service); agent đề xuất thêm `ListClinicalResultsPagedAsync` ở `Service.LIS` (phương án 2) cho bệnh nhi nằm viện dài ngày.

### 7.6. Cửa sổ agent cuối phiên và việc phải làm đầu phiên sau
- Còn mở: Agent 0; `claude-9` (Claude, "Not logged in", đang commit P3, chưa có báo cáo fix2: **cần chủ máy đăng nhập lại hoặc đóng**); `agy-10` (Hydrogen, rảnh, đã `/add-dir` HIS_EMR). Đã đóng: claude-5, agy-1, 2, 3, 4, 6, 7, 8.
- Đầu phiên sau: (1) `get_orchestration_rules`, `list_terminals`; (2) kiểm `git -C C:\wt\ctrl-s2-04a status`, `git log`, và `BAOCAO-CTRL-S2-04-fix2.md`; (3) nếu chủ máy cho giao việc lại: nghiệm thu fix2 rồi review Pha 4 bằng agy; (4) hỏi chủ máy các quyết định ở 7.2, 7.5 và `Z-*`/`J5`/`Y*` trong `TRANG-THAI-CHOT-KE-HOACH-CONTROLLER-2026-11-14.md` mục 3.
- Vẫn chưa làm/chưa mở khoá: S2-02-b…f (S2-02-d1 cần DDL Z-9), S2-18 các hàm Service mới, S2-06 (cần bảng hoàn phí, J5), S2-01/S2-03 (Y1, Y2, Y4), Nhóm L (S2-10, S2-12, S2-19), Nhóm M (S2-11, S2-22, S2-20), S2-15-b/d/e/f/g/i, F5.
- Trạng thái chưa merge/push: mọi nhánh `wt/*` chưa vào `main`; chưa chạy 4 truy vấn S2-02-G trên bản sao; chưa chạy script `PatchFeaturesToanVienScope_Postgres.sql`.
