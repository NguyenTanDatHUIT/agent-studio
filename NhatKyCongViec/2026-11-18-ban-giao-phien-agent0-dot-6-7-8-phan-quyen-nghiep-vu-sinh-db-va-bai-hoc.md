# BÀN GIAO PHIÊN AGENT 0 (18/11/2026, phần 3): đợt 6, 7, 8 — phân quyền, nghiệp vụ còn dở, sinh DB, Postgres tạm, bài học

Nối tiếp `2026-11-18-ban-giao-phien-agent0-dot-5-review-doc-lap-va-sua-muc-b.md` (mục 4b, 4c). Repo HIS_EMR: `C:\CongViec\itc-git\HIS_EMR` (thư mục việc `NhiDong\`). Bạn là Agent 0: chỉ điều phối, không tự viết mã (ngoại lệ đã làm: gộp xung đột `git merge` bằng cách giữ cả hai phía; không viết logic).

## 1. Trạng thái nhánh lúc ghi (14:15)
- **`main` = `origin/main` = `8467e6b8`** (đã push sau đợt 7: Phase6 2020 đạt, 0 lỗi, Phase4 355/0/1, build xanh).
- **`wt/view-int` (`C:\wt\view-int`) hơn `main` các commit của đợt 8**, CHƯA đẩy: PW `dc3a6ffb` (ngưỡng PEWS theo nhóm tuổi), CB DB `9e6d0d58` (3 cột `destination_ready_*` + entity tay + bản W3 sinh lại), CB B2 `bad5028c` (`ConfirmDestinationReady`), CR `122f24dc` (Luồng 2 thủ tục điều dưỡng ra viện), test A12 `934519a3`; HEAD sau gộp `934519a3` (đã giải xung đột `RowLockTables.cs` và `NursingController.CareWorkflows.cs` bằng cách giữ cả hai phía).
- **Build `Web.HIS` trên `view-int` đang LỖI 1 chỗ**: `Service.Nursing\Components\PewsThresholdResolver.cs:94` CS0173 (`? :` DateTime với null, cần `(DateTime?)`). `agy-38` được giao sửa trong `C:\wt\viewu1`. Sau đó cần: build, cập nhật baseline (+6 action: `PewsThresholdsData`, `SavePewsThresholds`, `ConfirmDestinationReady`, `CareWorkflowDischargeDetail`, `StartNursingDischargeWorkflow`, `SaveNursingDischargePhase`), Phase4, Phase6 trọn bộ, review độc lập (đang chạy U1 PEWS `agy-38`, U2 khoa nhận sẵn sàng `agy-39`, U3 Luồng 2 `agy-40`), rồi gộp `main`, push (chủ máy đã dặn "xong thì commit qua main push lên").
- Worktree còn: `view-int`, `viewu1..3` (đã gộp, xoá khi dọn), `apply-newuikit`, `ctrl-ddl` (của chủ máy, KHÔNG xoá). Ổ `C:` ~107 GB trống (từng đầy 100% lúc tạo 41 worktree; mỗi worktree ~3 GB).
- Cây chính còn thư mục chưa theo dõi `Plan Coding/Testing/` của chủ máy (không đụng).
- Container Postgres tạm `his-test-pg` (cổng 55432, mật khẩu `his_test_pw`, `max_locks_per_transaction=4096`) ĐANG CHẠY: xoá bằng `docker rm -f his-test-pg` khi xong.
- Cửa sổ còn mở: `claude-9` (BUILD, Sonnet 5.5), `agy-38`, `agy-39`, `agy-40`. Mọi agy mới đã ở Gemini 4 Hydrogen (medium).

## 2. Đã làm trong đợt 6, 7, 8 (tóm tắt)
- **Đợt 6**: `[Feature]` cho Reception, Patient, Guardian, Billing, Clinical, Emr, EmrTemplate, Pharmacy cũ (chỉ dùng mã có sẵn); xoá `SpecialControlMedications.js`; mdDrdIns, mdDcMed (chọn giai đoạn thuốc), mdHuyVong (`VoidWristband`), CareZones G11, mdVdSetting mục 1, CareWorkflows luồng 1, mdKySo (nhúng `Emr\Detail`, `emr-unified-signing.js`). Review độc lập 2 vòng, nhiều lỗi CAO sửa (huỷ vòng tay thiếu phạm vi khoa; BHYT không phản ánh lên đối soát; ký ảnh trống; ghi cấu hình toàn viện bằng quyền Update; phiếu chuyển khoa tin `FromDepartmentId` client; Pharmacy chốt kiểm kê quyền yếu). Sửa kiểm quyền trong thân hàm: chỉ chặn khi `Enforce` (`AuthController.HasFeaturePermission`).
- **Đợt 7**: bảng độ phủ V4 (110/114 đạt review = 96,5%); nút "Thay thế y lệnh" (`ReplaceOrder`); cổng tiền `ApproveSettlement` kiểm độc lập 2 cổng mới (10 cổng; hồ sơ còn `PAID_DIFF_PENDING` KHÔNG thể duyệt cho tới khi có E7); 4 danh sách Dược nội trú; 9 lỗi Phase6 có sẵn xử lý; DDL 2 bảng mới đưa vào `_tools/defs` + entity + khung Service S1 (`gen_service.py --sample-approved`, mẫu SH6 đã duyệt 04/11/2026); bản phát hành W3, W0B sinh lại.
- **Đợt 8 (đang dở)**: PW, CB, CR như mục 1.

## 3. Bài học mới (đưa vào prompt lần sau)
- **Sinh DB không được viết tay**: `.sql` nhóm DB, `tables.json`, `_install.sql`, `Migrations\*` do `gen.py`/`build_release.py` sinh từ `Database\_tools\defs\*.py`. Thêm bảng vào defs thì CÒN phải: `gen_entities.py` (CHỈ sinh entity cho bảng mới; cột thêm vào bảng ĐÃ có entity thì phải thêm tay property, KHÔNG khai chỉ mục tham chiếu mềm trong EF), `gen_service.py --tables <bảng> --sample-approved` (mỗi lệnh một bảng; khung S1 bắt buộc vì test sinh theo `tables.json`), `build_release.py --release <đợt> --check` cho cả 9 bản (W0B chứa dòng tên trạng thái `option_values`; fixture nạp bản này), `--groups <nhóm>` để thu hẹp `gen_entities`. Test cứng số bảng (`ServiceS1Tests` 125, `A11` 16 bảng không-Guid, `A12` danh sách UseCase) phải cập nhật.
- **Vòng phụ thuộc bản phát hành**: bảng nhóm 03 (W3) không được `ref` tới bảng nhóm 18 (W6) vì W6 requires W4 requires W3 (đã gỡ `ref` của `nursing_discharge_workflows.discharge_decision_id`, Service phải kiểm tồn tại).
- **Cột mới trên bảng đã có entity = rủi ro triển khai**: EF chọn mọi cột; nếu DB thật chưa chạy DDL thì truy vấn hỏng. Chỉ thêm cột khi đã có mã dùng, và DBA chạy bản phát hành TRƯỚC khi triển khai mã.
- **Phase6 cần Postgres tạm cấu hình cao** (`max_locks_per_transaction=4096`, `max_connections=300`), nếu không 53200 "out of shared memory" (1674/2000 lỗi giả). Dùng container riêng, không dùng container dự án khác.
- **Lỗi build lặp lại**: thiếu `using` (`FeatureTypes` ở `DBContext.HIS.Entities`, `CommandErrors` ở `Service.Core.Components`, `AdmissionLabels` ở `Service.Inpatient.Components`), tuple không đặt tên, `?:` DateTime/null: sandbox agy không build nên chỉ `claude-9` bắt được; build SỚM sau mỗi lô.
- **Lệnh gõ dài vào terminal bị cắt** (chỉ còn đoạn cuối): giao việc qua tệp prompt, dòng gõ ≤ 500 ký tự.
- **Khi agy rảnh quá lâu, hay chưa in dòng cuối `HOÀN TẤT`** nhưng báo cáo đã đủ: đọc diff thật, đối chiếu rồi nghiệm thu; ngược lại báo cáo tác giả nhiều lần chỉ đúng một phần (ví dụ test cứng số bảng).
- **Cửa sổ agy mới mở có thể ở model `Orchestrator (Carbon)`** và lần đầu giao việc báo `Failed to start a conversation`: gõ `/model` rồi `Hydrogen` + Enter (menu có ô tìm kiếm), rồi giao lại việc.
- **Cảnh báo hạn mức tuần** của chủ máy (đã 91% lúc xem lần cuối, đặt lại 21/11 8 giờ sáng): gộp các lượt chạy lại và review khi có thể.

## 4. Treo chờ chủ máy (còn hiệu lực)
1. Bật `FeaturePermission:Mode = Enforce` (hiện `Audit`, chưa chặn ai): cần quyết quyền Tạo/Sửa gộp (9 action POST ở Reception/Patient/Guardian/Clinical.Vitals/Pharmacy), xung đột quyền bác sĩ kê đơn ↔ dược sĩ (`MedicationOrderDetail`, `DecideMedicationOrder*`), các cặp màn gọi chéo (Reception↔Billing, Payments↔Cashier, Clinical↔Emr, Dược nội bộ), seed `features` và gán nhóm quyền.
2. DBA khi triển khai DB thật: chạy lại bản phát hành **W3** (2 bảng mới `pews_thresholds`, `nursing_discharge_workflows`, 3 cột `destination_ready_*` của `patient_handovers`) và **W0B** (dòng tên trạng thái; gồm 9 dòng `nursing_task_reasons_status` từ commit B4 của chủ máy); idempotent; chạy TRƯỚC khi triển khai mã.
3. Quy trình hoàn tiền E7 (đợt nhập viện có `PAID_DIFF_PENDING` không duyệt được bảng kê), `encounter_charges` và `charge_voided` trên `SettlementDetail`.
4. Phông chữ ký nghệ thuật nội bộ (bốn phông đang rơi về phông hệ thống); modal `mdKySo` chưa có `handleSigningSubmit` do màn khác định nghĩa (đã thêm lối vào ở `Emr\Detail`).
5. Phase6 đã sạch (2020/0 lỗi ở `8467e6b8`); `T11c_RT4...` bỏ qua từ trước.
6. Xem giao diện trên trình duyệt thật (chưa màn nào), chụp ảnh `node tools/ui_shots.cjs`.
7. Bảng độ phủ mockup V4 (96,5%): còn 2 mục mức C (CareWorkflows luồng 2 + bước 3, PEWS theo nhóm tuổi) NAY đang làm ở đợt 8; mức D còn hai trang ghi chú prototype (không làm).

## 5. Việc kế tiếp đề xuất
1. Chờ `agy-38` sửa lỗi build PEWS và commit hộ; gộp vào `view-int`; `claude-9`: build, baseline +6, Phase4, Phase6 (Postgres tạm đã bật, báo "PG sẵn").
2. Nghiệm thu 3 báo cáo review `BAOCAO-REVIEW-DOT8-U1..U3.md`, giao sửa lỗi CAO/TRUNG, review lại phần đã sửa bằng cửa sổ khác.
3. Khi build, Phase4, Phase6 xanh và review sạch: fast-forward `main` lên `view-int` và push; dọn Postgres tạm, `viewu1..3` và cửa sổ.
4. Lập lại bảng độ phủ V5; chụp ảnh các màn mới.
