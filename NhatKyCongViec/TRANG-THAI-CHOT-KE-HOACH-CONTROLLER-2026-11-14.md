# Tình trạng chốt kế hoạch Controller (14/11/2026 ~16:10): cái gì đã chốt, cái gì còn chặn, làm gì tiếp

> **Cập nhật 22:55 (chủ máy đã dặn dừng giao việc; xem `2026-11-14-ban-giao-phien-pm-s2-04-b-c-d-review-doc-lap.md` mục 7):** (1) Quyết định chung đã ghi ở `NhiDong\Plan Coding\Controller\QUYET-DINH-CHUNG-S2-DOT-14-11-V1.md` (Z-1…Z-12, Y1…Y4, J1…J4, V5-Q2, S2-18-Q2.1/2.2, S2-13-Q1/2, S2-20-Q1/2, V1-Q1, V8-Q1). (2) S2-04-b và S2-04-c đã viết, đã qua review độc lập 3 pha (đều ĐẠT CÓ ĐIỀU KIỆN) và sửa lần 2 xong (PM tự chạy lại: Phase6 127 pass/2 skip, Postgres.DrillTests 18 pass); **chưa review Pha 4**; chờ F5, C2 và quyết định hướng P1 (thiếu quy đổi đơn vị: chặn hay chỉ cảnh báo). (3) S2-05 xong (hàm thuần), S2-06 dừng (J1…J4 đã quyết, J5 mở). (4) S2-15-a, c, h, j xong (chưa review độc lập; khu cấp cứu chưa gán khoa dừng). (5) **Nhóm K (S2-07, S2-08) dừng, không mã:** S2-07 cần bảng mới `clinical_result_views` (K1), S2-08 N+1 nằm ở `ClinicalController.PartLabResults` (Webs cấm chạm): PM đề xuất sửa ở đợt Controller bằng hàm gom lô có sẵn (K2). (6) Các nhánh `wt/*` chưa merge; worktree đã dọn, nhánh còn nguyên. Bảng ở mục 2 bên dưới là trạng thái lúc 16:10.

Mục đích: trả lời "kế hoạch Controller còn chưa chốt chỗ nào, để lên kế hoạch dựng view". Tài liệu gốc ở `C:\CongViec\itc-git\HIS_EMR\NhiDong\Plan Coding\Controller\`; prompt/báo cáo ở `C:\AgentControl\studio-state\prompts\`. Bản bàn giao liên quan: `2026-11-14-ban-giao-phien-pm-s2-02g-s2-04a-s2-02a-s2-04a-a.md` (mục 4, 9, 10).
**Giới hạn:** tôi đối chiếu tài liệu quyết định và báo cáo agent, chưa mở lại từng màn trong 11 báo cáo D1X…D9; test "xanh" là số agent báo.

## 1. Phần ĐÃ chốt (không cần hỏi lại)
- 11 điểm điều chỉnh, 40 câu A, 23 mã B, 9 câu C của chủ dự án (13/11 10:29): `PHAN-HOI-CHOT-KE-HOACH-CONTROLLER-TOAN-BO.md`. PM đã đánh giá và sinh ra "đợt S2" 23 việc Service: `DANH-GIA-QUYET-DINH-KE-HOACH-CONTROLLER-TOAN-BO.md` mục 4. Tài liệu `CAU-HOI-TONG-HOP-KE-HOACH-CONTROLLER-TOAN-BO.md` (bản bàn giao 13/11 ghi là "còn mở") **đã được trả lời** bởi tài liệu trên; phần còn mở thật là các mục 3 và 4 dưới đây.
- 13 câu đợt 1: `PHAN-HOI-CHOT-DOT-1-CONTROLLER-NOI-TRU.md`.
- S2-02 (y lệnh miệng E1–E10) và S2-15 (khoa của tôi Q1–Q10): `QUYET-DINH-S2-02-VA-S2-15-V1.md`. S2-09: `QUYET-DINH-S2-09-HO-SO-NOI-TRU-V1.md`. S2-18 (ra viện Q1–Q6): `QUYET-DINH-S2-18-RA-VIEN-Q1-Q6-V1.md`.
- Nguyên tắc chung: URL kiểu MVC (`/Controller/Action`), liệt kê hết API từng màn, xong S2 liên quan rồi mới viết Controller của màn đó, không sửa `AppController.cs`/`AuthController.cs`/`Program.cs`.

## 2. Bảng tình trạng 23 việc S2 (chặn việc dựng Controller/View của màn nào)
| Việc | Tình trạng | Còn thiếu để chốt/đóng | Chặn đợt |
|---|---|---|---|
| S2-01 hết giường lúc nhận bệnh | Đã phân tích, **dừng** (không mã) | Y1–Y3 (mục 3.2) | 2, 3 |
| S2-02 y lệnh miệng | Đã chốt E1–E10. Mã: **g, a xong** (`4d36bf2a`). Còn b, c, d1, d2, e, f | Z-1, Z-4, Z-9, Z-11; DDL (mục 3.1); chạy 4 truy vấn S2-02-G trên bản sao | 4, 5, 6 |
| S2-03 ca đêm chờ nhận bàn giao | Đã phân tích, **dừng** | Y4 (cần bảng mới), "học viên" chỉ cấu hình | 4 |
| S2-04 rời Cấp cứu | Đã phân tích. Mã: **a xong** (`0d7d5a2d`, `ff5f3e7d`). Còn b, c, d | Z-1…Z-8, Z-12 | 5 |
| S2-05 trẻ sơ sinh chưa tên | **Xong** phần thuần `NewbornNameLabels` (`ccc6a36b`, chưa nối vào luồng nào) | Nối vào luồng và xuất XML chờ W8 (KHTH) | 9 |
| S2-06 huỷ lượt khám | Đã phân tích, **dừng** (cần bảng mới) | J1–J5 (mục 3.3) | 9 |
| S2-07, S2-08 | Chưa giao (`PROMPT-CTRL-S2K.md` sẵn) | Không bị chặn bởi câu hỏi nào đã biết | 5, 4 |
| S2-09 | **Đã chốt**: dùng `AdmissionRecordTreeMany`, không cần Service thêm | Sửa tài liệu D7 dòng 152 và 706 (bỏ yêu cầu `EmrRecordMany` trả khoa/mã đợt) | 7 |
| S2-10, S2-12, S2-19 | Chưa giao (`PROMPT-CTRL-S2L.md` sẵn) | Không bị chặn | 7, 4 |
| S2-11, S2-22 | Chưa giao (`PROMPT-CTRL-S2M.md` sẵn; S2-11 có thể cần DDL, phải dừng nếu cần) | DDL nếu có | 8 |
| S2-13 phiếu công khai thuốc | Đã phân tích, **dừng**: thiếu mẫu phiếu của bệnh viện (`BAOCAO-CTRL-S2D.md` mục 3) | Mẫu phiếu BV; S2-13-Q1, Q2; 8 trường bắt buộc theo báo cáo 8 việc (Việc 6) | 4 |
| S2-14, S2-16, S2-17 | **Xong** (nhánh `wt/ctrl-s2d`, `fbf2de37`). S2-16 dùng `Obsolete(error: true)` | Chưa merge | 1, 3 |
| S2-15 khoa của tôi | Đã chốt Q1–Q10. Mã: **a xong** (`c7973bfc`). Còn b, c, h, j (không chặn), d (lớn), e (script), f/g/i (DDL/DB) | Chạy kiểm độ phủ trên bản sao; DDL f, g | nhiều đợt |
| S2-18 ra viện | Đã chốt Q1–Q6. **Chưa có mã** cho các hàm mới (ghi 3 việc thu tiền, `SettleDischarge`, `CompleteDischarge`, sổ ngoại lệ nợ, In bản chính, phát hành BHXH) | V5-Q1, V5-Q2, S2-18-Q2.1, Q2.2; DDL sổ ngoại lệ nợ; sửa mockup/D6 | 4, 6 |
| S2-20 PEWS | Chỉ phân tích | S2-20-Q1, Q2; có lịch trực bác sĩ chưa | 3 |
| S2-21 quyền in lại vòng tay | Chưa làm | Chủ dự án xác nhận ghi `permission_group_features` | 3 |
| S2-23 xuất danh sách theo khoa | Chưa giao | Phụ thuộc S2-15-c | 1 |

## 3. Quyết định còn chờ chủ dự án (gom một chỗ, kèm đề xuất để trả lời "theo đề xuất")
### 3.1. `Z-1`…`Z-12` (S2-02, S2-04, S2-15, DDL)
Nằm ở mục 4 của bản bàn giao 14/11 (không chép lại): Z-1 rút lẻ thuốc kiểm soát, Z-2 CLS dài ngày, Z-3 tách Xin về/Trốn viện, Z-4 chuyển viện/tử vong khi còn CLS/lệnh miệng chưa ký (đề xuất PA A), Z-5 kết thúc lượt truyền, Z-6 giữ dịch truyền khi nhập viện, Z-7 `admission_id NOT NULL` (GAP-A5-6), Z-8 dọn tài nguyên cấp cứu khi nhập viện, Z-9 DDL `verification_id integer` và kiểu timestamp, Z-10 ký số ra viện sớm (cũng là V5-Q1), Z-11 Khoa Dược rà cờ thuốc kiểm soát, Z-12 `CreateDischargeDecision` Warn hay Block.
### 3.2. S2I (S2-01, S2-03): theo `BAOCAO-CTRL-S2I.md`, `-2.md`
- **Y1** điều dưỡng nhận bệnh có quyền kê băng ca/xếp ghép (đổi quyền)? **Y2** `ReceivedWaitingBed` tự tạo `BedRequest` (đề xuất có)? **Y3** thêm cột loại chỗ tạm cho kết cục chờ (DDL)? **Y4** thêm bảng xác nhận nhận bàn giao diễn biến ca trực (`progress_note_handover_acks`, DDL)?
### 3.3. S2-06 (`BAOCAO-CTRL-S2J-2.md` mục 7)
- **J1** nơi lưu yêu cầu hoàn phí: bảng mới `payment_refund_requests` (đề xuất) hay thêm cột vào `payment_refunds`. **J2** kiểm CLS ở LIS/RIS (hai cơ sở dữ liệu khác): cổng probe được tiêm vào (đề xuất). **J3** ai được huỷ, hạn huỷ (đề xuất: tiếp đón + thu ngân khi chưa thu; cần trưởng quầy duyệt khi đã thu). **J4** lượt đã thu BHYT/chờ hậu kiểm (`PaymentStatus = 3`) có cho huỷ (đề xuất: từ chối bước đầu, chờ KHTH). **J5** khoá đường cũ `UpdateEncounter` đặt `Status = 6` và `DeleteEncounterByIds` sau khi có `CancelEncounter`?
### 3.4. Từ báo cáo 8 việc (`2026-11-13-ban-giao-phien-pm-chieu-toi-s2-baocao-8-viec.md` mục 2)
V2-Q1 (trùng Z-1), S2-04-Q1/Q2 (trùng Z-2/Z-3), V5-Q1 (trùng Z-10), **V5-Q2** in lại bản chính phân biệt "Bản sao", **S2-18-Q2.1** tách cổng BHXH khỏi nợ cá nhân, **S2-18-Q2.2** phân 2 cấp duyệt sổ ngoại lệ nợ theo ngưỡng, **S2-13-Q1/Q2** ẩn/hiện đơn giá và gộp vật tư, **S2-20-Q1/Q2** kịch bản PEWS và chống bão cảnh báo, **V1-Q1** thời hạn lưu nhật ký đọc bệnh án, V1-Q2 (trùng Z-11), **V8-Q1** dùng 24 kịch bản UAT làm cả test tự động lẫn phiếu nghiệm thu.
### 3.5. Còn chưa thấy ghi nhận câu trả lời (DANH-GIA mục 7)
(1) "S2 trước hay Controller trước" (có vẻ đã áp dụng ngầm); (2) mở S2-18 (đã làm); (3) S2-15 bốn bước (đã áp dụng ở S2-15-a); (4) B-D9-4 tái dùng `IsNameProvisional` (S2-05 đã theo hướng này); (5) C-5 rào `PatientWristbandMany` (S2-16 đã chọn `Obsolete(error: true)`: khác phương án đề xuất, cần chủ dự án xác nhận); (6) S2-20 bác sĩ trực (còn mở); (7) thứ tự đợt đưa đợt 8 (Dược) lên trước 5, 6 (chưa thấy ghi nhận).
### 3.6. Quyết định kỹ thuật/tích hợp
Tích hợp các nhánh `wt/ctrl-s2-02a`, `wt/ctrl-s2-04a`, `wt/ctrl-s2-15`, `wt/ctrl-s2j`, `wt/ctrl-s2d`, `wt/ctrl-s1` vào đâu và khi nào (hiện chưa merge; Controller sẽ viết trên nền nào); thêm `emergency_exams`, `emergency_urgent_actions` vào `RowLockTables.All`; xác nhận ghi DB cho S2-21.

## 4. Tài liệu kế hoạch cần sửa để khớp quyết định (việc tài liệu, chưa làm)
1. D6: trạng thái cuối hồ sơ đối soát là `SETTLED` không phải `CLOSED` (`KE-HOACH-CONTROLLER-D6-RA-VIEN-THU-TIEN.md` dòng 357; `A-D6-2` ở `PHAN-HOI-CHOT...:104`).
2. D7 dòng 152 và 706 (S2-09).
3. Mockup/đặc tả tab Ra viện đợt 4/6: bỏ điều kiện "đã tất toán" khỏi cổng "Xác nhận kết thúc đợt" (S2-18 mục Hệ quả 2); không dựng UI theo mockup cũ.
4. Cập nhật số action sau các quyết định (ước ~407–419) và danh sách chuẩn theo quy tắc gộp URL cùng node quyền.

## 5. Đề xuất cách xử lý (theo thứ tự)
1. **Một lượt trả lời duy nhất:** chủ dự án trả lời mục 3.1–3.4 (có thể ghi "theo đề xuất" cho từng nhóm). Tôi sẽ ghi quyết định vào tệp `QUYET-DINH-...-V1.md` như các lần trước (không sửa đè bản đã ký) rồi mở khoá các việc ở mục 2.
2. **Giao ngay, không chờ trả lời** (cần cửa sổ Claude vì agy đang bị chặn quyền trên worktree ngoài workspace): S2-15-b/c/h/j (claude-5 đã có ngữ cảnh), Nhóm K (S2-07, S2-08), Nhóm L (S2-10, S2-12, S2-19), phần không DDL của Nhóm M. Lưu ý hạn mức Sonnet (13/11 ~91%; chưa đo lại).
3. **Sau khi có trả lời:** S2-04-b/c/d, S2-02-b…f, S2-18 (nhiều hàm Service mới, nên tách thành nhiều gói và có review độc lập), S2-06 (DDL), S2-01/03 (quyền/DDL).
4. **Sửa tài liệu mục 4** (có thể giao cho một agent chỉ đọc-sửa tài liệu, chủ dự án duyệt).
5. **Sau đó mới lập kế hoạch view theo màn**: màn "sẵn sàng" = mọi action của màn đã có Service và không còn câu hỏi mở (ví dụ phần lớn Dược nội trú, 87 action đã có); màn "bị chặn" ghi rõ câu hỏi/việc S2 chặn nó (ví dụ Ra viện, Rời cấp cứu, Nhận bệnh khi hết giường, Ca đêm).

## 6. Điều tôi KHÔNG biết (cần xác nhận)
- Quy ước view/JS của `Web.HIS` (và vai trò của worktree `C:\wt\nhidong-newuikit`, nhánh `feat/nhidong-newuikit`) chưa được đọc.
- Hạn mức Claude/agy hiện tại; nguyên nhân sandbox của agy chặn `cd` vào worktree.
- Chủ dự án đã trả lời thêm câu nào ngoài các tài liệu `QUYET-DINH-*` đã liệt kê (nếu có, báo để tôi cập nhật bảng).
