# 10/11/2026 — Bàn giao phiên PM (Agent 0): A2.1c → A3 xong → A4.0–A4.3 xong; hai đợt review chỉ-đọc (87 phát hiện); việc kế

**Đọc file này ĐẦU TIÊN nếu bạn là phiên PM tiếp theo.** Sau đó đọc `QUY-TAC-DIEU-PHOI-CMD-AGENT.md` (bản v2, mục 1–15) cùng thư mục, rồi `promt/DIEU-PHOI-TU-DONG.md` (hàng đợi + nhật ký lượt) và `promt/QUYET-DINH-TU-DONG.md` (quyết định đã chốt thay chủ dự án). File này thay mục "trạng thái / việc chờ / bước kế" của `2026-11-09-ban-giao-phien-pm-hisemr-a1-8-den-a2-1.md`. Thư mục prompt/báo cáo mới: `C:\CongViec\agent\agent-orchestrator\NhatKyCongViec\promt\` (đã `.gitignore`, **không commit**).

**Lưu ý trung thực:** mọi số build/test dưới đây (HIS.sln 3.591, Web.HIS 3.413, Phase6 41+, Phase4 355) là số **do agent báo**; PM chưa tự đo lại build. PM đã tự đọc mã (cấu trúc, khoá, quét `DateTime.Now`/`ex.Message`/`his.*`, đối chiếu hằng với DDL bằng script, đọc thân các ca rủi ro) nhưng **chưa đọc hết thân mọi ca**; phần chưa đọc kỹ nằm ở mục 8.

## 1. Yêu cầu của chủ dự án trong phiên này
- Đẩy nhanh **code Service** (chưa Controller/View, chưa test mới); các câu hỏi cần chủ dự án quyết ⇒ **PM quyết theo đề xuất của kế hoạch và ghi file** (`QUYET-DINH-TU-DONG.md`); cho phép mở nhiều cửa sổ agy khi cần.
- **Mỗi cửa sổ agy chỉ 3–4 việc rồi đóng/mở mới.** Chủ dự án treo máy ~5 giờ: PM tự giao việc, nghiệm thu, đổi cửa sổ (lịch tick + tệp điều phối).
- Khi bị chặn: **dừng việc đó và ghi lại** (không dùng thông báo đẩy: chủ dự án không nhận được).
- **Ngưỡng RAM cố định không cần** (PM tự đặt rồi bỏ): chỉ cần tối đa ~3 cửa sổ agy + một agent build; kiểm RAM khi nghi treo.
- Prompt/báo cáo để ở `agent-orchestrator\NhatKyCongViec\promt\`, không đẩy lên git.
- **Yêu cầu hiện tại (09:00 10/11): sau khi 2 agent đang chạy xong ⇒ viết bàn giao (file này) + cập nhật quy tắc điều phối (đã xong v2) + cập nhật `docs/TINH-NANG-QUY-TAC-DIEU-PHOI-AGENT.md` (đã xong, đánh dấu [v2]). Sau bàn giao PM DỪNG giao việc mới, chờ chủ dự án.**

## 2. Trạng thái commit (HIS_EMR, nhánh `main`, **36 commit chưa push**, chủ dự án chưa nói "push")
| Commit | Đợt | Ghi chú |
|---|---|---|
| `5d8673c1`, `9b038068` | A2.0a nền, A2.2 lịch trực | từ phiên trước |
| `51f3d35d` | A2.1a vòng tay | PM đã đọc lõi Reprint + hook |
| `13c48f43` | **A1.9** dọn kiến trúc | `ClockNow()` lên `ModuleServiceBase`, đổi tên tệp truy vấn, `SafePageOption` chung (lệch nhỏ: `Page`→1 khi null; `OrderBy` rỗng→null: chưa kiểm tương đương) |
| `1080cbea` | A2.1b bàn giao (H-01..H-05) | **đợt thử subagent: đạt** (4 subagent, ~8 phút/16 tệp) |
| `edd69efd` + `6b88f1bf` | A2.1c nhận bệnh (R-01..R-03) | fix1: thứ tự khoá ReceivePatient (beds/bed_assignments phải SAU handovers/wristbands) |
| `32f2d00d` | **A3.0** nền | 3 bảng khoá, 6 node quyền, `PewsCalculator`, `NursingTaskStepSchemas`, `PatientMergeCore` (lõi gộp hồ sơ) |
| `897115ad` | A3.1a việc điều dưỡng T-01..T-08 | |
| `2716686b` | A3.1b đính chính + worklist T-09..T-13 | |
| `70680f57` | A3.2 sinh hiệu/PEWS/cân nặng/đánh giá V-01..V-09 | |
| `fd799b55` | A3.3 đối chiếu thuốc M-01..M-08 | |
| `519e210a` | A3.4 đối soát danh tính I-01..I-09 | **chứa lỗi gộp hồ sơ đảo chiều (mục 4)** |
| `2a810994` + `7b652345` | **A4.0** nền workspace + fix1 | fix1: hằng `WorkspaceClinicalDocumentCodes` bịa không có trong DDL |
| `0103fb27` | A4.1 khám vào viện/chẩn đoán/dị ứng (R1–R13, A1–A6) | ký số qua cổng mặc định đóng |
| `4eadf7ae` | A4.2 kế hoạch điều trị TP1–TP12 | lỗi ký lưu `sign_state=9` + trả thành công kèm cờ |
| `fccd057f` | A4.3 diễn biến SOAP PN1–PN13 | tách lõi `ExecuteReviewTreatmentPlanCore` (Review + Finalize gọi chung) |
| `69e4e91b` | kế hoạch A6a/b/c + html | |
| `3c327d69`, `8b1e96fb`, `db5d2e53`, ... | tài liệu | |
**Đợt A3 xong hết (A3.0–A3.4). Đợt A4 còn A4.4+A4.5.** Số của agent (cổng): HIS.sln 3.591 (đợt A3.0 báo 3.590), Web.HIS 3.413 (3.412), Phase6 filter 41→72 passed (số tăng theo ca mới), Phase4 355, T5 PASS.

## 3. Quyết định đã chốt (chi tiết: `promt/QUYET-DINH-TU-DONG.md`)
- **Nhóm 1 (chủ dự án ĐÃ duyệt thật, 09/11):** A3-Q9 (6 node quyền + 3 bảng khoá), A4-Q3 (7 node + cờ `a`), A5-Q2 (`LockRow`+`row_version`+`idempotency_key`, không `xmin`), A4-Q1, A4-Q2.
- **Nhóm 2 (PM quyết thay theo đề xuất):** A3-Q1..Q8, A4-Q4..Q6, A5-Q3..Q10 (A5-Q6 vượt cảnh báo BLOCK: nhạy cảm an toàn thuốc, nghiệm thu kỹ). Câu mở cũ: tuổi hiển thị, quá hạn 120 phút, phạm vi khoa (giữ hiện trạng), reason_code lịch trực (hằng), sơ sinh/`alert_colors` (null).
- **Quyết định kiến trúc PM tự đặt:** W1/W2 của A4.4 đặt tên `DoctorMyPatientsMany`/`DoctorMyPatientsCountsOne` để tránh trùng `MyPatientsMany` của Nursing (A3.2); `NEW_CONFIRMED` không phải mã DB (DDL chỉ `PENDING/MERGED/RENAMED/UNRESOLVED`).
- **Phát hiện kiến trúc quan trọng:** `clinical_documents.document_type` là `int` và chỉ `1 Ngoại trú/2 Nội trú` ⇒ **không có mã riêng** cho khám vào viện/kế hoạch/diễn biến; phiếu nhận diện bằng `catalog_item_id`/`business_key`/`template_code_key` (A4.1 dùng `business_key = "ADMISSION_EXAM"`, A4.3 `PROGRESS_NOTE`…).

## 4. Hai đợt review chỉ-đọc (agy-1) và việc phải sửa — QUAN TRỌNG
Đã làm 2 review chỉ-đọc (không build/sửa/git ghi): `promt/REVIEW-A3-A4.md` (**40 phát hiện: 10 CAO, 23 TRUNG, 7 THẤP**) và `promt/REVIEW-A1-A2.md` (**47 phát hiện: 9 CAO, 26 TRUNG, 12 THẤP**). **PM đã tự xác minh bằng đọc mã các mục sau, ĐỀU ĐÚNG hoặc cần quyết:**
1. **[NGHIÊM TRỌNG, XÁC NHẬN] A3.4 `ReconcileIdentityMergeCommand.cs:294-307`:** lõi `PatientMergeCore.cs:160` gọi `additionalMoves(context, MergedPatientId, SurvivorPatientId, ...)` nhưng lambda khai `(ctx, survivorId, mergedId, ...)` ⇒ dị ứng/bệnh mạn/y lệnh của hồ sơ GIỮ LẠI bị chuyển sang hồ sơ tạm (đảo chiều).
2. **[XÁC NHẬN] A3.1b `NurseWorklistMany.cs:57-60`:** MyPatients/Team không có phân công ⇒ `scopedAdmissionIds = null` ⇒ hiện mọi việc trong khoa.
3. **[XÁC NHẬN] A3.1b `ReviewNursingRecordCorrection`:** không chặn tự duyệt; duyệt đính chính sinh hiệu cập nhật `nursing_tasks.VitalSignId` sau khi chỉ khoá `nursing_record_corrections` (nursing_tasks đứng trước trong `RowLockTables.All`).
4. **[XÁC NHẬN] A2.1b `CreateHandoverCommand.cs:80` + `HandoverCodes.cs:106-113`:** truyền `adm.SourceType` (DDL: `1 Cấp cứu · 2 Ngoại trú · 3 Chuyển tuyến`) vào `FromAdmissionSource` ánh xạ ngược `1=>Outpatient, 2=>Emergency` ⇒ nơi gửi bàn giao sai. (Cột `admission_source` mà chú thích nhắc không có trong DDL.)
5. **[CẦN QUYẾT, không phải lỗi agent] A1.8 `BedStatusHistoryMany`/`PatientLocationHistoryMany`:** hàm công khai không kiểm quyền, nhận `IncludeDeleted` từ client; thực chất là tệp CRUD **do bộ sinh tạo sẵn** (A1.8 fix2 khôi phục nguyên bản). Chủ dự án quyết: chấp nhận mô hình sinh sẵn (kiểm quyền ở lớp trên) hay phải bọc.
6. Chưa tự xác minh nhưng review trích DDL cụ thể (agent sửa phải tự xác minh): `ParticipantRoleCreator = "CREATOR"` không có trong CHECK `document_participants` (A4.2); duyệt đính chính thuốc không hạ dòng eMAR cũ (A3.1b); `RecordPrnMedicationTask` không đọc `clinical_order_prn_rules` (A3.1a); `IdentityCandidateMany` `.Take(500)` trước khi lọc (A3.4); `VoidTreatmentPlan` không cập nhật `clinical_documents` (A4.2); `PatientMergeCore` giữ `IsPrimary` giấy tờ (A3.0); A2.2 trần độ dài chuỗi lớn hơn cột DDL (`nursing_shifts.code varchar(10)`); `StateNote` bàn giao có thể trống (A2.1b); `WristbandApplicationId` luôn 0 (A2.1c); `CompleteAdmission` lưu thẻ BHYT/người đại diện không kiểm thuộc đúng người bệnh, tạo `admission_referrals` rác (A1.5b/c); `SearchAdmissionPatientMany` N+1 và lệch quy ước kiểu trả (A1.5a, nằm trong nợ K1/RT-3).
**Việc sửa:** `promt/PROMPT-FIX-REVIEW-A3-A4.md` **đã viết sẵn** (agent build tự xác minh từng phát hiện, sửa mục xác nhận, báo mục không tái hiện, chia commit). **Chưa viết** `PROMPT-FIX-REVIEW-A1-A2.md` (nên sao từ A3-A4 và đổi danh sách mục ưu tiên theo `REVIEW-A1-A2.md` mục 15 "Nghi vấn cần PM kiểm" + 9 mục CAO). **Khuyến nghị: làm hai đợt sửa này TRƯỚC A4.4/A5.0** (lỗi 1 đặc biệt: không nên xây tiếp trên nền gộp hồ sơ đảo chiều).

## 5. Việc kế theo thứ tự (cho PM mới, khi chủ dự án nói "tiếp")
1. `list_terminals`; kiểm `git log/status`; đọc `promt/DIEU-PHOI-TU-DONG.md`. **Một builder tại một thời điểm.** Cửa sổ `agy-2` (do PM mở) đã làm 1/4 việc (A4.3) nên dùng được tiếp; `agy-1` do chủ dự án mở: PM không đóng được, nó đã làm nhiều việc (chỉ nên dùng cho review chỉ-đọc).
2. Nghiệm thu nốt A4.3: đọc thân `FinalizeProgressNote`/`SignProgressNote`/`AddProgressNoteAddendum` (chưa đọc kỹ) và diff `ReviewTreatmentPlanCommand.cs` (271+/252−, chưa đọc). `BAOCAO-A4.3.md` **đã có** (29,8 KB, ghi 09:11): số cổng agent báo Phase6 41 đạt/7 bỏ qua, Phase4 355 đạt; mục 4.2 (câu hỏi ký số PN7/PN8, cùng hướng A/B đã nêu ở mục 6) và mục 5.2 (**câu hỏi PN13**: chưa có bảng kết quả xét nghiệm/CĐHA trong DDL nên `InsertableLabResultsMany` trả rỗng có chú thích, chờ A6/LIS/RIS); mục 7 là số liệu subagent đợt này.
3. Giao **FIX-REVIEW-A3-A4** (có sẵn) cho builder; sau đó viết và giao **FIX-REVIEW-A1-A2**. Nghiệm thu bằng đọc mã (đặc biệt mục 4.1, 4.2, 4.3, 4.4 ở trên).
4. Giao **A4.4+A4.5** (`PROMPT-A4.4.md` sẵn). Rồi **A5.0** (`PROMPT-A5.0.md` sẵn, nhạy cảm: không bịa ngưỡng lâm sàng/giá), sau đó cần viết **PROMPT-A5.1..A5.5** (từ `KE-HOACH-CODING-SERVICE-A5.md` mục 5.2: A5.1 danh mục/bộ mẫu, A5.2 nháp+an toàn+dự trù, A5.3 ký lô+sinh lịch (+đầu dò thứ 4), A5.4 vòng đời, A5.5 miệng/học viên/truy vấn). Rồi **A6a → A6c → A6b** (kế hoạch đã commit).
5. Mẫu làm việc đã chứng minh: PROMPT-CHUNG + prompt riêng; agent chính tự làm ca rủi ro cao, subagent làm ca độc lập; review chỉ-đọc song song builder; mục "1A cập nhật sau đợt trước" khi đợt trước làm lộ sự thật mới.

## 6. Việc chờ chủ dự án (nằm ở báo cáo từng đợt và quyết định)
- **Push** 36 commit (`git log origin/main..HEAD`) khi chủ dự án nói "push".
- **Hướng ký số (chặn các ca ký, đang dùng cổng mặc định đóng):** Phương án A (kết xuất PDF qua `EmrTemplate` + `ClinicalDocumentSignatureAnchors` + `EmrSigningCommand.SignClinicalDocumentAsync`) hay B (ký trên `ContentHash` SHA-256 trong `Service.Emr`, không cần PDF) — `BAOCAO-A4.1.md` mục 4.3. Ảnh hưởng A4.1 R4, A4.2 TP5, A4.3 PN7/PN8.
- **Mã nhận diện phiếu lâm sàng** (kế hoạch điều trị/diễn biến): agent dùng `business_key` code đặt; chủ dự án xác nhận hay thêm mục vào danh mục hồ sơ (`record_catalog_items`).
- Nguồn dữ liệu sơ sinh cho nhãn vòng tay (A2.1a); `alert_colors` giữ null; ngưỡng PEWS nhi (A3-Q3, bảng trong code chưa phải giá trị chốt lâm sàng); 10 tham số `InpatientSettings` A3 trong `Unconfirmed`; `PatientMergeCore`/`MergePatient` (IsPrimary, hạ `Status`) nếu hành vi gốc đã vậy.
- Mục 4.5 ở trên: mô hình CRUD sinh sẵn không kiểm quyền.
- Nhóm 2 A3–A5 và câu hỏi A6 (`CAU-HOI-CHU-DU-AN-A3-A5.md` trong `promt/`; A6 chưa gom, GAP-DB-1..5 của A6b cần chủ dự án/DB).
- Quyền chạy tự động: `open/send/close_terminal` hỏi duyệt mỗi lần (xem mục 7).

## 7. Agent, terminal, môi trường
- Dashboard (lúc viết): `agent0` (PM), `agy-1` (chủ dự án mở; vừa xong REVIEW-A1-A2, rảnh), `agy-2` (PM mở; vừa xong A4.3, 1/4 việc, rảnh). Đã đóng: agy-3, agy-4 (đủ 4 việc), agy-5 **mất khi phiên khởi động lại** (xem dưới). Model mặc định agy mới: **Gemini 4 Argon medium**.
- **Phiên đã khởi động lại giữa 06:39–08:24 (10/11):** agent đang chạy biến mất, các `Monitor` chết, lịch `CronCreate` (`d0444630`, 11 phút, session-only, hết hạn sau 7 ngày) còn sống. A4.3 mới ở giai đoạn đọc nên giao lại không mất mã (quy trình: `QUY-TAC...v2 mục 13`). Lịch tick **vẫn đang chạy**: nếu muốn dừng hẳn, `CronDelete d0444630`.
- **Bộ theo dõi nền** (`Monitor`, 30 phút/lần): hiện còn 1 cái; đã chết nhiều lần và phải dựng lại; tín hiệu "xong" đáng tin hơn `[AO]` (commit mới/báo cáo đổi).
- Máy 15,8 GB RAM; lúc viết còn ~3,7 GB trống với 2 cửa sổ agy. Không cần ngưỡng RAM cố định.
- Tệp quan trọng trong `promt/`: `PROMPT-CHUNG.md` (khung chung), `PROMPT-A3.0..A5.0`, `PROMPT-A4.0-fix1.md`, `PROMPT-FIX-REVIEW-A3-A4.md`, `PROMPT-REVIEW-A3-A4.md`/`-A1-A2.md`, `DIEU-PHOI-TU-DONG.md`, `QUYET-DINH-TU-DONG.md`, `REVIEW-A3-A4.md`, `REVIEW-A1-A2.md`, `BAOCAO-*.md` từng đợt, `CAU-HOI-CHU-DU-AN-A3-A5.md`.

## 8. Giới hạn nghiệm thu và sai sót/bài học của PM
- **Chưa tự đo build**; **chưa đọc hết thân** các ca lớn (CompleteNursingTask/RecordPrnMedicationTask A3.1a; SaveNursingAssessmentRules 697 dòng, MyPatientsMany 767 dòng A3.2; từng ca A3.3; thân Finalize/Sign A4.3). Review chỉ-đọc bù một phần; **PM chưa xác minh hết mục CAO của review** (mới 5/19).
- **Sai sót của PM:** (1) nghiệm thu A3.4 mà không bắt được lỗi đảo tham số `additionalMoves` (chỉ kiểm khoá/cấu trúc): **khi nghiệm thu luôn đọc nơi GỌI và nơi KHAI của delegate/lambda có hai Guid liền nhau**; (2) kiểm hằng với DDL bằng script chỉ ở đoạn dòng đã biết (A4.0 lọt `CREATOR` ở A4.2): **chạy lại script cho TOÀN BỘ hằng mỗi đợt**; (3) viết prompt review A1/A2 bằng cách nhân bản và suýt ghi đè báo cáo cũ (đã sửa kịp): **đọc lại đường dẫn đầu ra khi nhân bản**; (4) đưa ngưỡng RAM "1,5 GB" vào quy tắc không có cơ sở đo (đã bỏ); (5) `[AO]` khiến PM báo "chưa xong" lúc agent đã xong (lệch vài phút) và ngược lại.
- **Hành vi agent đáng canh:** báo cáo ghi sai chi tiết dù mã đúng; hằng bịa không có trong DDL; subagent kẹt (~35 phút, một lần nhắc "chia nhỏ/tự viết" là đủ); agent tốt tự ghi `GAP-A3-7` khi kế hoạch lệch DDL.
- Đã cập nhật `docs/TINH-NANG-QUY-TAC-DIEU-PHOI-AGENT.md` (repo agent-orchestrator, chưa commit) với các ý v2 để công cụ cài vào Cài đặt (Pha 2/3 chưa làm).

## 9. Tệp tham chiếu
- **Quy tắc:** `NhatKyCongViec/QUY-TAC-DIEU-PHOI-CMD-AGENT.md` (v2; bản sao `HIS_EMR/NhiDong/NhatKyCongViec/`, chưa commit); bộ nhớ làm việc `feedback-cmd-agent-orchestration-rules.md` (đã thêm v2).
- **Kế hoạch (`HIS_EMR/NhiDong/Plan Coding/`):** `KE-HOACH-CODING-SERVICE-GD2.md` (mục 3, 8.1, 13, 13A, 13B), `-A1..A6a/b/c.md`, `-RETURN-TYPE.md`.
- **Nhật ký đợt (`HIS_EMR/NhiDong/NhatKyCongViec/`):** `2026-11-09-a1-9-...`, `-a2-1a-vong-tay`, `-a2-1b-ban-giao`, `-a2-1c-nhan-benh`, `-a3-0-...`, `-a3-1a/b`, `-a3-2`, `-a3-3`, `-a3-4`, `-a4-0-...`, `-a4-1`, `-a4-2`, `-a4-3` (agent ghi theo đợt).
- **Mã chính:** `Service.Core/Components/{RowLockTables,InpatientCodes,InpatientSettings,PatientMergeCore,SnapshotEnvelope}.cs`, `Service.Core/Executes/Base/ModuleServiceBase.Business.cs` (`ClockNow`, `SafePageOption`, `ExecuteInSharedTransaction`), `Service.Nursing/**` (A2, A3.0–A3.2), `Service.Inpatient/Executes/{Admission,Bed,Workspace}/**`, `Service.Inpatient/Components/{AdmissionPermissions,WorkspacePermissions}.cs`.
