# BÀN GIAO PHIÊN AGENT 0 (đêm 17 rạng 18/11/2026, phần 2): đợt 5, review độc lập mức B, sửa lỗi

Nối tiếp `2026-11-18-ban-giao-phien-agent0-view-dot-3-4-cap-cuu-ra-vien-review-doc-lap.md`. Repo HIS_EMR (`C:\CongViec\itc-git\HIS_EMR`). Bạn là Agent 0: chỉ điều phối.

## 1. Trạng thái nhánh
- **`main` = `97c1593b`, CHƯA ĐỘNG, CHƯA PUSH.** `wt/view-int` = `1fa2fbe9`, hơn `main` 39 commit (gồm bản sửa lô K, P1 đến P7, mọi bản sửa review).
- Build `Web.HIS` trên `wt/view-int`: xanh, 0 lỗi (00:59). Phase4: 355 đạt, 0 lỗi, 1 bỏ qua (khớp nền). Baseline `web-his-actions.txt` +5 dòng đã commit `2be96d22`.
- Phase6 (`EmergencyDepartureS204F5Tests`, `DischargeGuaranteePrintBhxhS218bTests`): 2 đạt, **12 bỏ qua** vì cần Postgres tạm; Docker đang tắt. Chưa xác nhận đủ.
- Worktree đã gộp (xoá khi dọn): `C:\wt\viewp1..p9`, `viewq1..q5`. KHÔNG xoá `apply-newuikit`, `ctrl-ddl`, worktree Codex.

## 2. Đã làm trong phần này
- Gộp P1 đến P5; thêm P6 (Dược nội trú: 3 trang), P7 (`Url`/`Sidebar` cho Cấp cứu, Ra viện, Workspace), 3 modal (`mdDrdIns`, `mdVdSetting`, `mdYlCal`).
- Review độc lập: Cấp cứu, P1+P2, P3+P4, P5, P6 (3 vòng), 3 modal, 5 lô mức B (R1 đến R4). Các lô đều CHƯA ĐẠT lần đầu rồi sửa, review lại **ĐẠT** (lô A `theo-doi-nb`, B 10 màn Điều dưỡng, C Workspace, D Bệnh nhân/Thu ngân/Khám, E EMR/Mẫu in). Báo cáo: `C:\AgentControl\studio-state\prompts\BAOCAO-REVIEW-*.md`, `BAOCAO-SUA-*.md`, `BAOCAO-REVIEW-LAI-X1..X4.md`.
- Sửa dùng chung: `uikit-his-bridge.js` `app.confirm` gọi `cb(true)` (lô D) làm sống lại ~11 luồng xác nhận của View cũ (grep 97 chỗ gọi, không callback nào hỏng).
- Bảng độ phủ mockup (trước các bản sửa): 59 màn + 55 modal; 94,7% có View (108/114); chỉ 30,7% đã review đạt lúc đó. **Chưa cập nhật lại sau đợt sửa**: sau đợt này hầu hết mức B đã lên A (xem `BAOCAO-DOI-CHIEU-MOCKUP-1..3.md`).

## 3. Lỗi lặp lại (đã đưa vào prompt, cần nhắc tiếp)
`advanceGrid`: `setSearchParams`/`dataSource`/`beforeLoad` không tồn tại, `paging.options` (đúng `sizes`), số `rows` phải khớp số cột; `MkReason.ask` dùng `onOk(reason, closeModal, unlockOk)` không trả Promise; `app.confirm(type, title, text, callback)` 4 tham số; đọc `res.Success`/`res.Many` PascalCase; mọi POST khoá nút ở `.always`; id kiểu `int` không gửi chuỗi.

## 4. TREO chờ chủ máy (không tự quyết)
1. **Phân quyền `[Feature]`**: `ReceptionController`, `PatientController`, `GuardianController`, `BillingController`, `ClinicalController`, các Controller Emr/EmrTemplate chưa gắn `[Feature]` (kể cả thao tác tiền/ca thu). Có thể đã có kiểm quyền chung ở `AuthController`: chủ máy quyết có thêm không.
2. **Gộp `main` / push**: `wt/view-int` hơn `main` 39 commit, chưa ai xem trên trình duyệt thật. Hỏi trước khi gộp (`git merge --ff-only wt/view-int` sau khi nói rõ "gộp vào main").
3. Việc Service/Controller còn thiếu: Service trả `PendingRecalculationChargeCount`, `PAID_DIFF_PENDING`, `refund_due` (nút "Duyệt bảng kê"); nút "Thay thế y lệnh"; Service ghi cho `CareWorkflows` (2 luồng); 4 action GET danh sách Dược nội trú (`WardRequisitionList`, `DrugReturnList`, `StockRecallList`, `ControlledDrugShiftCountList`); action ghi cập nhật BHYT trên đối soát ra viện; action cấu hình ngưỡng cảnh báo việc điều dưỡng; endpoint trả `Steps` mẫu xoay ca; quyền `ShiftList` (`ca_truc:v` so với `viec_trong_ca:v`); `Bed/CareZones` ghi (Service G11 hoãn).
4. Seed `features` vào DB thật (sao lưu `db-backups\...truoc_seed_features.dump`), cài nhóm `emergency_*` lên DB thật, gán khoa 202 tài khoản. **Docker Desktop tắt**: bật trước khi `psql` hoặc chạy Phase6.
5. Chạy `Web.HIS` từ `main`/`wt/view-int` để xem trình duyệt thật (sáng/tối, 1366/1024) và chụp ảnh `node tools/ui_shots.cjs`: chưa màn nào được xem.

## 4b. Cập nhật cuối phiên (02:25)
- `wt/view-int` = `049c3331`; build xanh 0 lỗi (02:24); Phase4 lại 355/0/1 (khớp nền, `BAOCAO-TEST-DOT5C.md`). `main` vẫn `97c1593b`, chưa push.
- Thêm sau mục 2: R5 (Dược cũ + `mdDcMed`, `mdKySo`) review CHƯA ĐẠT, sửa lô F1 (26 tệp Dược: `paging.sizes`, escape HTML, `app.confirm` 4 tham số, lớp BS3) và F2 (2 modal); review lần 2 ra 3 hồi quy TRUNG (thoát dấu `"` trong helper escape; `Phase` gán cứng ở tải tệp đính kèm) đã sửa (`049c3331`), tự soi diff, CHƯA có lượt review độc lập thứ ba.
- Bảng độ phủ mockup V2 (`BAOCAO-DOI-CHIEU-MOCKUP-V2-3.md`, lập trước R5): 104/114 (91,2%) đã có View và đạt review (19 màn là "A*: nợ `[Feature]`), 111/114 (97,4%) có View; mức B còn lại là các màn Dược cũ và 2 modal đã xử lý ở R5; mức D chỉ 3 mục có lý do (`ghi-chu`, `quy-trinh-tong-the`, `mdHuyVong`). **Đã lập V3 sau R5** (`BAOCAO-CHOT-DOT5.md`): 105/114 (92,1%) đạt review (85 A + 20 A*), 111/114 (97,4%) có View, mức B = 0, mức C = 6, mức D = 3. Review độc lập `049c3331`: ĐẠT. Còn 1 THẤP ngoài commit: `Views\Pharmacy\StockTakeEdit.cshtml:222,272` helper `tkEsc` cục bộ chưa thoát `"` (rủi ro thấp).
- Treo thêm: (a) `SpecialControlMedications.js` là JS mồ côi, xoá hay giữ; (b) bỏ Google Fonts khỏi `_UnifiedSigningModal.cshtml` làm 4 phông chữ ký nghệ thuật (Playwrite VN, Cormorant Garamond, Lora, IM Fell English) rơi về phông hệ thống: bổ sung `.woff2` nội bộ hay chấp nhận; (c) `_UnifiedSigningModal.cshtml` chưa View nào nhúng và `handleSigningSubmit` chưa được định nghĩa (khoá nút xác nhận); (d) `mdDcMed` mới chuẩn bị `data-phase`/`getMedRecPhase()`, chưa có tab ra viện/chuyển khoa; (e) toàn bộ `PharmacyController` cũ thiếu `[Feature]`.

## 4c. Cập nhật cuối (13:35, sau đợt 6 và 7): `main` = `origin/main` = `8467e6b8` (đã push)
- Đợt 6: phân quyền `[Feature]` (kèm sửa kiểm quyền trong thân hàm chỉ chặn khi `Enforce`), xoá `SpecialControlMedications.js`, mdDrdIns/mdDcMed/mdHuyVong/CareZones/mdVdSetting/CareWorkflows luồng 1/mdKySo; review độc lập hai vòng, nhiều lỗi CAO đã sửa.
- Đợt 7: bảng độ phủ V4 (110/114 = 96,5% đạt review; có View 112/114), nút "Thay thế y lệnh", cổng tiền `ApproveSettlement` kiểm độc lập 2 cổng mới (10 cổng), 4 danh sách Dược nội trú, 9 lỗi Phase6 có sẵn đã xử lý (3 test lỗi thời sửa; 6 test do fixture thiếu quyền: cấp quyền fixture, SG5 chấp nhận thông báo nghiệp vụ), 2 DDL + khung Service/entity cho `pews_thresholds`, `nursing_discharge_workflows`.
- Kiểm cuối (`BAOCAO-TEST-DOT7D.md`): build Web.HIS xanh; Phase4 355/0/1; **Phase6 trên Postgres tạm: 2020 đạt, 0 lỗi, 1 bỏ qua** (đã dùng container tạm `his-test-pg` rồi xoá; Postgres tạm cần `max_locks_per_transaction` cao, nếu không lỗi 53200).
- **Cần DBA/chủ máy khi triển khai DB thật:** chạy lại bản phát hành W3 (thêm 2 bảng mới `pews_thresholds`, `nursing_discharge_workflows`) và W0B (6 dòng trạng thái 2 bảng mới + 9 dòng `nursing_task_reasons_status` từ commit B4); cả hai idempotent. Ba cột `destination_ready_*` của `patient_handovers` ĐÃ GỠ khỏi thiết kế (chưa có mã dùng; nguyên văn 3 dòng ở `BAOCAO-DOT7-GEN-FIX.md`, thêm lại khi làm bước "Khoa nhận sẵn sàng" cùng entity). `nursing_discharge_workflows.discharge_decision_id` chỉ là tham chiếu logic (không `ref`, tránh vòng W3-W6): Service phải kiểm khi dùng.
- **Còn mức C (cần phần nghiệp vụ trên khung Service/entity vừa có):** ngưỡng PEWS theo nhóm tuổi (`pews_thresholds`, UI `mdVdSetting` mục 2); thủ tục điều dưỡng ra viện và bước "Khoa nhận sẵn sàng" của `CareWorkflows`.
- **Treo chờ chủ máy:** bật `FeaturePermission:Mode = Enforce` (hiện `Audit`; trước đó cần quyết quyền Tạo/Sửa gộp, xung đột quyền bác sĩ/dược sĩ trên `MedicationOrderDetail`, các cặp màn gọi chéo, seed `features` và gán nhóm quyền); quy trình hoàn tiền E7 (đợt nhập viện có `PAID_DIFF_PENDING` hiện KHÔNG thể duyệt bảng kê: chủ ý đóng-an-toàn); `encounter_charges` và `charge_voided` trên `SettlementDetail`; phông chữ ký nghệ thuật nội bộ; xem giao diện trên trình duyệt thật (chưa màn nào).
- `main` còn thư mục chưa theo dõi của chủ máy `Plan Coding/Testing/` (không đụng).

## 5. Việc kế tiếp đề xuất
Cập nhật bảng độ phủ mockup; dọn worktree đã gộp; khi chủ máy gật, gộp `main`; bật Docker chạy Phase6; review độc lập tab `Billing` (lô A chỉ đổi giao diện) nếu chưa; cửa sổ còn mở cuối phần này: chỉ `claude-7` (BUILD).
