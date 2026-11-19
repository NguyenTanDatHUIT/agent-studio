# BÀN GIAO PHIÊN AGENT 0 (đêm 17 rạng 18/11/2026): View đợt 3 và 4, Cấp cứu, Ra viện/Thu tiền, review độc lập

Nối tiếp `2026-11-17-ban-giao-phien-agent0-view-newuikit-menu-va-seed-features.md` (phần Seed menu, View cũ, nợ DB/Service vẫn còn hiệu lực; đọc cả hai) và `2026-11-17-ban-giao-phien-agent0-tich-hop-dot-17-11-va-viec-tiep-theo.md`. Repo: `C:\CongViec\itc-git\HIS_EMR` (thư mục việc `NhiDong\`). Bạn là Agent 0: chỉ điều phối, không tự viết mã.

## 0. Làm ngay khi mở phiên
1. `get_orchestration_rules`, `list_terminals` (cuối phiên còn mở: `agy-1`..`agy-6`, `agy-8`, `claude-7` (cửa sổ BUILD, Sonnet), đều RẢNH; phiên mới có thể đánh số lại).
2. Đọc `C:\AgentControl\studio-state\prompts\PROMPT-CHUNG.md`, `KHUON-VIEW-NEWUIKIT.md`, `QUY-LUAT-VIEW-RAZOR-LOI-BIEN-DICH.md`, `PROMPT-VIEW-VIET-DOT3.md`, `PROMPT-VIEW-VIET-DOT4.md`. Bộ nhớ của bạn có 3 ghi nhớ mới (View cũ cũng phải chuyển NewUIKit; agy rảnh thì tự giao việc, tối đa 8 cửa sổ).
3. `git fetch`, so `main`/`origin/main`; `git worktree list`.
4. Nghiệm thu P1 đến P4 (mục 2), vì cả bốn lô đã im lặng mà chưa commit.

## 1. Trạng thái nhánh (HIS_EMR)
- **`main` = `97c1593b`**, cây chính sạch, **CHƯA PUSH**: `main` trước `origin/main` (`d60b2088`) **72 commit** (toàn việc View/menu hôm nay, `origin` không đi trước). Chủ máy CHƯA yêu cầu push; hỏi trước khi push. Mọi lần gộp vào `main` đều bằng `git merge --ff-only wt/view-int` sau khi chủ máy nói rõ "gộp vào main" (một lần lệnh gộp bị hệ thống chặn khi chủ máy chưa yêu cầu: tôn trọng, không lách).
- **`wt/view-int` = `4f294c79`**, hơn `main` 2 commit: bản sửa 4 lỗi CAO của lô K (`11681b77`) + merge. Build `Web.HIS` trên nội dung này xanh (0 lỗi). **Bản sửa lô K CHƯA vào `main`**: `main` đang chứa màn thu tiền ra viện bị lỗi (không tất toán được, KPI = 0). Đề xuất gộp ngay khi chủ máy gật (đã review độc lập lần 2: ĐẠT).
- **Chưa vào `main`:** `wt/viewp5` `ba4e6f0f` (tab `Discharge`, đã commit); `wt/viewp1`..`viewp4` (tệp CHƯA COMMIT, xem mục 2).
- Worktree đã gộp vào `main` (xoá khi dọn): `C:\wt\view-v0/v1/v2/v3/v4`, `view-ph`, `view-menu`, `view-dev`, `viewcu-a..f`, `viewcu-e1/e2`, `viewws-a/b`, `viewh/i/j/k/l/m`, `view-int` (sau khi `main` đã bằng nó). KHÔNG xoá `apply-newuikit`, `ctrl-ddl`, worktree Codex.
- Tạo worktree mới mất 1 đến 6 phút (24 nghìn tệp); chạy nền, đợi `locked` hết.

## 2. Đợt 4 (đang dở): tạo nốt mọi View còn thiếu (chủ máy: "tạo View xong hết rồi review sau")
| Lô | Agent | Worktree | Việc | Trạng thái |
|---|---|---|---|---|
| P1 | `agy-1` | `C:\wt\viewp1` | `Inpatient\PrintAdmissionSheet`, `PrintAdvanceReceipt` (2 action có sẵn nhưng thiếu View: đang lỗi 500), `Partials\PatientSummaryModal` (bấm tên ở `WaitingList` đang 404) | 4 tệp chưa commit, báo cáo `BAOCAO-VIEW-VIET-DOT4-P1.md`; **cần nghiệm thu** |
| P2 | `agy-3` | `C:\wt\viewp2` | `Bed\CareZones`; `Category\Beds`, `BedDayServices` theo mockup; **thêm 2 action GET** `BedEdit`, `BedDayServiceEdit` (`CategoryController.Beds.cs`/`BedDayServices.cs`) | 11 tệp chưa commit; hàm Service/kiểu đã kiểm có thật. Phải **cập nhật baseline `web-his-actions.txt` (+2 dòng)** rồi Phase4 |
| P3 | `agy-5` | `C:\wt\viewp3` | `Nursing\CareWorkflows` (+`WristbandDetail` nếu thiếu) | 3 tệp, báo cáo ngắn (3 KB): có thể chưa xong |
| P4 | `agy-6` | `C:\wt\viewp4` | `kham-chi-dinh-nv` (`Clinical\Partials\_AdmissionOrder`), `Reception\EncounterEdit`, `EmrTemplate\CatalogItemEdit`, `General\partials\NationEdit` | 10 tệp; **sửa 2 tệp cũ đang chạy** (`Clinical\Examination.cshtml`, `Partials\_Transfer.cshtml`): soi hồi quy kỹ |
| P5 | `agy-8` | `C:\wt\viewp5` | tab `Discharge` của Workspace (ra viện) | **xong, đã commit `ba4e6f0f`**, chưa gộp, chưa review độc lập |
Cách nghiệm thu mỗi lô (đã dùng cả ngày): quét `grep` cấm (`style=`, `<style`, `!important`, lớp Limitless, `window.confirm/prompt/alert`, mã màu cứng trừ `var(--uk-..., #hex)`), mọi trang chính có `mk-page-head`, mọi URL/action trong JS có thật (`IActionResult <Tên>(`) và đúng động từ/quyền `[Feature]`, `@using` cho từng kiểu (mở tệp định nghĩa), thuộc tính ViewModel có thật, không tính tiền ở JS, mọi POST ghi có khoá chống bấm lặp; commit hộ theo TÊN tệp (agy không `git commit` được); gộp vào `wt/view-int`; `claude-7` build.

## 3. Review độc lập (agy chỉ-đọc, vai `reality-checker` + `security-auditor`): KẾT QUẢ
`review` bắt được lỗi CAO mà `grep` tĩnh và build KHÔNG thấy (sai tên callback `advanceGrid`, bế tắc nghiệp vụ, thiếu khoá bấm lặp, trường API không tồn tại). Mẫu prompt: `PROMPT-REVIEW-DOT3-J.md`, `PROMPT-REVIEW-DOT3-K.md`, `PROMPT-REVIEW-LAM-SANG-1.md`.
- **Lô J (đối soát ra viện):** lần 1 CHƯA ĐẠT (CAO: `onDataLoaded` → `loadDataCallback`; TRUNG: lọc KPI kẹt) → đã sửa (`2ed2446c`, trong `main`). Nút "Duyệt bảng kê" khoá cứng `disabled` vì Service chưa trả `PendingRecalculationChargeCount`, `PAID_DIFF_PENDING`, `refund_due`: **chưa thể duyệt cho tới khi Service bổ sung** (việc Service, ngoài View).
- **Lô K (thu tiền ra viện):** lần 1 CHƯA ĐẠT, 4 CAO (bế tắc `settleReady`/`xmlReady`; `width: {}`; `dataCallback`; `reloadGrid` lồng `search`) → sửa `11681b77` → lần 2 ĐẠT (bảng 6 trạng thái). **Bản sửa chưa vào `main`** (mục 1).
- **RV-A (y lệnh `Orders`/`Medication`, giường `Bed/Board`):** CHƯA ĐẠT, 1 CAO (thiếu khoá chống bấm lặp trên mọi thao tác ghi, kể cả `SignOrderBatch`) + 4 TRUNG. Đã sửa (SỬA-2, `agy-2`, trong `main`) trừ `ReplaceOrder`: **chưa có nút "Thay thế y lệnh"**, chủ đích chờ chủ máy quyết (đã ghi chú trong `_Orders.cshtml`, `ws-orders.js`). **Chưa review lại bản sửa.**
- **RV-B (hồ sơ lâm sàng):** `AdmissionExam`, `Allergies`, `TreatmentPlan`, `Consultations`, `Fee` ĐẠT; `Emr` có 1 CAO (`ws-emr.js` đọc trường không tồn tại từ `RecordManifestItemDetail`) + `MkReason.ask` không khoá nút xác nhận (ảnh hưởng nhiều tab). Đã sửa (SỬA-1, `agy-4`, trong `main`). **Chưa review lại bản sửa.**
- **CHƯA review độc lập:** Cấp cứu (lô H, I: gồm `SignExam`, `Admit`, `Disposition`, `ConfirmDeparture`), tab `Discharge` (P5), `Billing` (lô A chỉ đổi giao diện), các tab mới của P1 đến P4. Đề xuất một đợt review độc lập trước khi dùng thật, theo mẫu trên; mỗi lần dùng agy KHÁC tác giả.

## 4. Còn thiếu / chưa làm
- **Dược nội trú** (`PharmacyController.InpatientDispense/InpatientRequisition/InpatientSafety`): chỉ có action JSON, không có action trả trang; cần thêm Controller + View (chưa giao, chờ chủ máy).
- **Menu navbar:** `DefaultFeatures.cs` chưa có `Url`/`Sidebar` cho Cấp cứu (`cap_cuu`), Ra viện, tab Workspace mới. Đã có `Url`/`Sidebar` cho 9 nút Nội trú/Điều dưỡng (commit `3c49ba1f`, trong `main`). Giữ nhóm gốc "Nội trú" và "Điều dưỡng" (quyết định chủ máy).
- **Seed `features` vào DB thật CHƯA làm** (lần kiểm cuối: 81 dòng, 0 dòng `noi_tru`/`dieu_duong`/`cap_cuu`). Chủ máy đã cho phép Seed trên DB thật; phải bấm nút "Khởi tạo từ menu mặc định" ở `/developer/features` (cần phiên đăng nhập) bằng bản mã mới của `main`. Sao lưu ngay trước đó: `C:\AgentControl\studio-state\db-backups\his_nhidong_214_20261117_164821_truoc_seed_features.dump`. Sau Seed phải gán quyền vai trò; có thể cần đăng nhập lại. Kiểm lại bằng truy vấn chỉ đọc. **Docker Desktop đang tắt ở cuối phiên** (`docker` không kết nối được): bật lại trước khi `psql`.
- **DB thật thiếu nhóm bảng `emergency_*`** (nhóm `08_cap_cuu`): màn Cấp cứu sẽ lỗi 500 dù View đúng; cần cài theo quy trình sao lưu, diễn tập 2 lần, chủ máy xác nhận. Cũng còn nợ: script vá quyền `cskh.*`, cache nhãn "Chờ nhập viện", 202 tài khoản chưa gán khoa.
- **Nợ kỹ thuật:** `emr-template-detail-uikit.css` còn 222 mã màu cứng (mô phỏng tờ giấy in, tách khỏi token vì rủi ro hỏng bản xem trước, không có trình duyệt để kiểm); `pharmacy-uikit.css` có mã màu chỉ dạng dự phòng trong `var(--uk-..., #hex)`; một số JS dùng chung của `General` còn `<style>`/mã màu (barcode, form-builder).
- **Chưa màn nào được chạy trên trình duyệt thật hay xem ảnh** (kể cả `WaitingList` mẫu, sáng/tối, 1366/1024). Rất cần chủ máy chạy `Web.HIS` từ `main`, Ctrl+F5, chỉ xem (đừng bấm nút ghi trên DB thật dùng chung).
- 12 câu hỏi cũ chủ máy chưa trả lời (mặc định thận trọng đã áp trong prompt, xem nhật ký 17/11 mục 4); riêng 3 câu còn quan trọng: nút "Thay thế y lệnh"; gộp bản sửa K vào `main`; Dược nội trú.

## 5. Bài học và cách làm (đúc kết cả ngày)
- **Lỗi lặp lại nhiều nhất:** thiếu/sai `@using` (agy đoán namespace thay vì mở tệp định nghĩa: `AccountBaseView` ở `DBContext.HIS.Entities`; `EmergencyVisitViewModel` ở `Service.Emergency.Executes.Emergency.EmergencyVisit`), thuộc tính ViewModel bịa (`card.CardId` vs `card.Id`), URL không tồn tại (`ShiftsData` vs `ShiftList`), tên callback thư viện (`loadDataCallback`). Chỉ **build** và **review độc lập** bắt được; build SỚM sau mỗi lô, đừng gộp quá nhiều lô mới build.
- **Build:** agy không chạy `dotnet/bash/git commit`. Gõ cho `claude-7` đúng `BUILD C:\wt\view-int Web.HIS`; log `C:\AgentControl\studio-state\prompts\LOI-BUILD-view-int-Web.HIS.txt` (đọc `Build succeeded`, `Error(s)`, `grep " error "`; **luôn tự đọc log**). Test: `bash /c/AgentControl/studio-state/build-slot.sh dotnet test '<đường dẫn Phase4.Tests.csproj viết sẵn>' [--no-build] -v minimal`; đường dẫn không dùng `$(...)` trong chuỗi. Cập nhật baseline action: `HIS_UPDATE_ACTION_BASELINE=1` + `--filter "FullyQualifiedName~WebHisActionBaselineTests"`, diff phải chỉ THÊM đúng số dòng (đã làm: +4 cho Cấp cứu, 1127 dòng); rồi Phase4 trọn bộ (nền: 355 đạt, 0 lỗi, 1 bỏ qua). Build tăng dần của một dự án chỉ in 0 cảnh báo; build đầy đủ lần đầu ra 3.496 (không so được với mốc B2).
- **Agy kẹt ở vòng chờ worktree:** khi worktree tạo chậm, agy đặt hẹn "90 giây" rồi đứng yên hơn 15 phút dù thư mục đã sẵn sàng. Cách xử lý đã có tác dụng: nhắn MỘT lần "worktree đã sẵn sàng (HEAD, git status sạch), đừng chờ, làm ngay".
- **Xung đột khung `PatientWorkspace.cshtml`:** nhiều lô cùng THÊM nhánh tab/biến quyền/thẻ script ở khung → xung đột cộng thêm khi gộp; giải quyết giữ cả hai bên, nhớ thêm dấu `}` đóng nhánh trước khi nối `else if` (kiểm ngoặc cân).
- **Quyền chủ máy (17/11 tối):** agy rảnh thì Agent 0 tự giao việc kế, tối đa 8 cửa sổ; VẪN hỏi trước khi gộp `main`, push, ghi DB thật, mở `claude` build, đổi quyết định nghiệp vụ/phân quyền chưa chốt.
- **Thông báo `[AO]`:** nhiều dòng "yên lặng" chỉ là gợi ý; "Chủ dự án xác nhận ... hoàn thành" là chủ máy bấm nút (có khi lặp). Đọc terminal + tệp trước khi kết luận.

## 6. Việc kế tiếp (đề xuất theo thứ tự)
1. Nghiệm thu P1 đến P4: kiểm tĩnh, commit hộ, gộp vào `wt/view-int` cùng `viewp5`; thêm 2 action GET của P2 vào baseline (+2 dòng) rồi build + Phase4. Hỏi chủ máy rồi gộp vào `main` (kèm bản sửa lô K).
2. Hỏi chủ máy: gộp bản sửa K vào `main` ngay (màn đang hỏng); Seed menu; chạy `Web.HIS` xem trình duyệt.
3. Giao đợt review độc lập: Cấp cứu (H, I), `Discharge` (P5), kiểm lại SỬA-1/SỬA-2, `Billing`, P1 đến P4 (có ghi lâm sàng).
4. Thêm `Url`/`Sidebar` cho Cấp cứu, Ra viện, Workspace vào `DefaultFeatures.cs` (rồi cập nhật DB bằng Seed hoặc `PatchFeatures*`).
5. Quyết định chủ máy: nút Thay thế y lệnh; Dược nội trú; cài `emergency_*` lên DB thật; gán khoa cho 202 tài khoản.
6. Dọn worktree đã gộp. Push khi chủ máy yêu cầu (tách kỹ vì `main` chứa 72 commit chưa ai xem trên trình duyệt thật).
