# 10/11/2026 (buổi sáng đến trưa) — Bàn giao phiên PM (Agent 0): fix hai đợt review xong; việc kế = bỏ `*Rules.cs` rồi A4.4+A4.5, A5.0

**Đọc file này ĐẦU TIÊN nếu bạn là phiên PM tiếp theo.** File này nối tiếp `2026-11-10-ban-giao-phien-pm-a2-1c-den-a4-3.md` (cùng thư mục): file đó nói đến A4.3 và hai đợt review chỉ-đọc; file này nói điều đã xảy ra sau đó (hai đợt fix, quy tắc mới của chủ dự án, công cụ điều phối). Sau đó đọc `QUY-TAC-DIEU-PHOI-CMD-AGENT.md` (v2, đã cập nhật mục 14–15 trong phiên này), rồi `promt/DIEU-PHOI-TU-DONG.md` (hàng đợi + nhật ký lượt) và `promt/QUYET-DINH-TU-DONG.md`. Thư mục prompt/báo cáo: `C:\CongViec\agent\agent-orchestrator\NhatKyCongViec\promt\` (đã `.gitignore`, **không commit**). **Đầu phiên gọi `get_orchestration_rules` rồi `list_terminals`.**

**Lưu ý trung thực:** mọi số build/test dưới đây (HIS.sln 3.591, Web.HIS 3.413, Phase6 71–100 đạt, Phase4 355, T5 PASS) là số **do agent báo**; PM chưa tự đo build. **Test `[PgFact]` (cần Postgres) bị Skipped** vì Docker/Postgres không chạy (log agy cho thấy `Skipped: 24, Passed: 0`), nên "Phase6 đạt" **chưa kiểm database**. PM bù bằng đọc mã và đối chiếu DDL.

## 1. Quy tắc/yêu cầu mới của chủ dự án trong phiên này
- **Giới hạn agent tương tác cùng lúc: 3 → 6** (Cài đặt, đã đọc lại bằng `get_orchestration_rules`: `max_concurrent_agents = 6`, `single_builder = true`). Vẫn **chỉ MỘT builder**; cửa sổ thêm chỉ cho review chỉ-đọc hoặc viết tài liệu.
- **KHÔNG dựng `Monitor` tự chế.** `[AO] ... đã xong` hay sai: tự kiểm bằng chứng (commit, báo cáo, cây mã, `dotnet`, terminal). Mỗi lần `[AO]` sai/thiếu/lặp thì **ghi một mục vào `C:\CongViec\agent\agent-orchestrator\logs\ao-thong-bao-sai.md`** (đã có 6 mục) để chủ dự án tổng hợp và sửa công cụ. `claude-3` là agent độc lập chủ dự án nhờ (phân tích `Admission/_UseCases`): **không theo dõi, không đọc kết quả khi chưa được yêu cầu**; nó đã được chủ dự án đóng.
- **Kiểm thử HOÃN:** chỉ agent code viết mã, không viết test mới, **không bắt chạy PgFact/Docker**, không khuyên bật Docker; Agent 0 review bằng đọc mã. Cổng hồi quy sẵn có (build 2 sln, Phase6 lọc, Phase4, T5) giữ nguyên. PM từng lệch phạm vi (thúc bật Docker) và đã sửa lại tài liệu.
- **Bỏ `<Ca>Rules.cs` khỏi `_UseCases`** (76 tệp): chủ dự án đã chốt, **không hỏi lại**; việc do phiên Claude khác (`a9`) chuyển cho PM: `promt/PROMPT-BO-RULES-USECASES.md` (4 phần tuần tự). **Chưa bắt đầu** (xem mục 5).
- **Viết prompt không làm agent chậm** (bài học từ log `agy log runing.txt`, 82 lần gọi công cụ, đọc lặp một tệp 5–7 lần): phép quét rộng do **Agent 0 tự chạy** (chỉ-đọc) rồi đưa agent danh sách `tệp:dòng`; mỗi prompt tối đa 3–4 điểm đã biết; dặn giảm output (`git grep -l`, `cut -c1-200`, không grep trong `Tests/`). Đã ghi ở bộ nhớ và `QUY-TAC` mục 14, 15.2, 15.11, 15.12 và `PROMPT-CHUNG.md` mục A.
- **Tài liệu phát triển công cụ** (không làm ngay): `C:\CongViec\agent\agent-orchestrator\develop\DE-XUAT-TU-DONG-BAN-GIAO-VA-KHOI-DONG-LAI-AGENT0.md` (tự bàn giao + khởi động lại Agent 0 theo ngưỡng context, ví dụ 35% của 1M). Đã kiểm trong mã: công cụ **chưa** có tính năng này; còn việc phải kiểm (nguồn số context; `restart_agent0` có làm mất cửa sổ agent con không).

## 2. Trạng thái commit (HIS_EMR, nhánh `main`, **47 commit chưa push**, chủ dự án chưa nói "push")
11 commit sau A4.3 (`fccd057f`), tất cả do agent `agy`, PM nghiệm thu bằng đọc mã:
| Commit | Nội dung |
|---|---|
| `10f4ae81` | mã `ParticipantRoleCreator` = `MAKER` (có trong DDL) |
| `16298851` | gộp hồ sơ: `PatientMergePair(Merged, Survivor)` thay hai `Guid` liền nhau (sửa lỗi chuyển dị ứng/bệnh mạn/y lệnh ngược chiều); `IsPrimary` giấy tờ; truy vấn ứng viên đẩy điều kiện vào SQL trước `Take` |
| `814d100c` | huỷ kế hoạch điều trị cập nhật `clinical_documents`; ràng buộc/phân trang workspace |
| `6586440d` | worklist điều dưỡng: phạm vi rỗng ⇒ rỗng; duyệt đính chính: chặn tự duyệt, khoá `nursing_tasks` trước `nursing_record_corrections`, hạ eMAR cũ `Status = 0`; PRN |
| `708fb1f8` | bàn giao: ánh xạ nơi gửi theo DDL (`1 Cấp cứu · 2 Ngoại trú`), `StateNote` bắt buộc |
| `39f55a5e` | nhận bệnh: `WristbandApplicationId` thật; trần chuỗi lịch trực khớp DDL; ghi lịch sử hạ trưởng ca; thẻ tổng hợp |
| `311cf190` | tìm bệnh nhân bỏ N+1; `CompleteAdmission`: kiểm thẻ BHYT/người đại diện thuộc đúng người bệnh, trần độ dài chuỗi, người đi kèm từ người đại diện |
| `fe2692ac` | bảng giường: không lộ khoa khác, bác sĩ chính từ `admission_doctors`; `ConfirmOccupancy` kiểm đợt ACTIVE; `CancelAdmission` khoá `patient_handovers`/`patient_wristbands` đúng thứ tự |
| `33d87c9d` | hoàn lại `SupplementAdmissionDiagnosis` (`Reason = changeReason`, có test A-05 khoá), chỉnh vài mục khác |
| `4f028b5b` | **sửa lần 1:** `CancelAdmission` huỷ phiếu bàn giao đang mở bằng `HandoverStatuses` (`WAITING`/`IN_TRANSIT` → `CANCELLED`; trước dùng `DRAFT/SENT/NOT_RECEIVED` không có trong DDL); mã lý do trả giường `1..5` (`BedReleaseReasons`), bỏ mặc định `?? 1` của `ReleaseBed`; `HandoverStatuses` chuyển sang `Service.Core` |
| `034a5073` | `CompleteAdmission`: không chèn `admission_referrals` khi thiếu cơ sở chuyển tuyến |

**Đợt A4 còn A4.4+A4.5; A5 và A6 chưa bắt đầu.** Số cổng agent báo ở lần cuối: HIS.sln 0 lỗi 3.591 cảnh báo; Web.HIS 0 lỗi 3.413; Phase6 71 đạt (+100 đạt khi kèm test thuần) 0 hỏng 7 bỏ qua; Phase4 355 đạt; T5 PASS; "PgFact: bỏ qua".

## 3. Nghiệm thu hai đợt fix (PM đã đọc mã)
- **FIX-REVIEW-A3-A4: ĐẠT** (4 commit). Đã xem: chiều tham số gộp hồ sơ khớp ở cả 2 nơi gọi; phạm vi worklist; thứ tự khoá và chặn tự duyệt; `Void` kế hoạch; `MAKER`.
- **FIX-REVIEW-A1-A2: ĐẠT sau sửa lần 1** (5 commit + 2 commit sửa). Khi nghiệm thu lần đầu PM tìm ra: (1) `CancelAdmission` dùng trạng thái bàn giao bịa (script đối chiếu hằng của PM **không bắt được chuỗi viết thẳng** và chỉ kiểm "có trong DDL ở đâu đó", không đúng cột); (2) `ReleaseBed` chỉ chặn `<= 0` và tự thêm mặc định `?? 1`; (3) nhánh referral còn chèn cơ sở = 0. Cả ba đã sửa và PM đã đọc diff. PM cũng bắt được `agy` đổi `Supplement` làm đỏ test A-05 (đã hoàn lại).
- Bảng xác minh chỉ-đọc do 2 agent Gemini lập: `promt/XACMINH-A1-A2-PHAN-A.md` (17 mục CAO/TRUNG) và `-PHAN-B.md` (≈21 mục): **gần như đồng thuận 100% với review gốc** (≈30 xác nhận, 1 KHÁC): đáng ngờ vì cùng một thiên lệch; PM không dùng làm bằng chứng, chỉ làm gợi ý.
- **Phần PM CHƯA kiểm kỹ:** thân `Finalize`/`Sign`/`Addendum` của A4.3 và diff `ReviewTreatmentPlanCommand.cs`; thay đổi điều kiện nhắc phiếu đồng ý trong `NurseWorklistSummaryOne` (đảo `!Incomplete` thành `WaivedEmergency`, chưa rõ đúng không); `CompleteAdmissionCommand` tạo người đi kèm từ người đại diện; thân `CompleteNursingTask`/`RecordPrnMedicationTask`/`SaveNursingAssessmentRules`/`MyPatientsMany` (nợ từ A3); các mục TRUNG khác của hai review chưa đọc từng mục; hai hằng `AdmissionStepIssueCodes` mới (`LEGAL_REPRESENTATIVE_INVALID`, `HEALTH_INSURANCE_CARD_INVALID`) là mã lỗi trả về, không phải giá trị cột.

## 4. Câu hỏi chờ chủ dự án (nằm ở `BAOCAO-FIX-REVIEW-A3-A4.md` mục 2 và `BAOCAO-FIX-REVIEW-A1-A2.md` mục 2 + SỬA LẦN 1)
1. Ca đêm chỉ có một Điều dưỡng trưởng trực và chính người đó lập bản ghi cần đính chính: giữ chặn tự duyệt hay cho tự duyệt kèm cờ kiểm toán.
2. Hồ sơ bị gộp: giữ `Status = 1` + `MergedIntoPatientId` (hành vi cũ, các ô tìm kiếm phải lọc) hay đổi `Status = 0` (cần sửa Service + test).
3. `SupplementAdmissionDiagnosis`: lý do khi bổ sung lần đầu — DDL nói bắt buộc, test A-05/đặc tả nói không (hiện giữ theo test, `NULL`).
4. `ReleaseBed` có đóng `patient_location_histories` không (thiết kế A1.2 cố ý không đóng).
5. `CompleteAdmission` khi có giấy chuyển tuyến nhưng thiếu cơ sở chuyển tuyến: hiện **bỏ qua dòng `admission_referrals`** (mất số giấy) hay từ chối bằng lỗi nghiệp vụ; và `Encounter.IsRightRoute`/`BenefitRate` đang gán cứng `false`/`0` (quy tắc BHYT).
6. Ánh xạ `PayerType` (1..4) với `patient_objects.id`; miễn chặn nguồn Cấp cứu (người đại diện, SĐT); `CashierShiftId = null` khi huỷ tiếp nhận.
7. Hai tệp CRUD sinh sẵn `BedStatusHistoryMany`/`PatientLocationHistoryMany` không kiểm quyền (chấp nhận mô hình sinh sẵn hay bọc).
8. Tên hàm/kiểu trả của `SearchAdmissionPatient` (`CommandResult` cho truy vấn `*Many`, DTO còn `Success/Message`): cần đổi chữ ký công khai (chưa làm).
9. **Test hiện có sẽ đỏ khi chạy lại PgFact:** `BedCoreUseCasesA12Tests.cs:555,560` truyền `ReasonCode = 7` vào `ReleaseBed`, ngoài miền `1..5` mới thêm. Khi bật lại kiểm thử cần quyết sửa test hay nới miền.
10. Còn từ trước: hướng ký số (A hoặc B), mã nhận diện phiếu lâm sàng, dữ liệu sơ sinh nhãn vòng tay, ngưỡng PEWS nhi, 10 tham số `InpatientSettings`, tên/kiểu `PatientMergeCore`, câu hỏi A5/A6 (xem `CAU-HOI-CHU-DU-AN-A3-A5.md`), **push 47 commit**.

## 5. Việc kế theo thứ tự (cho PM mới, khi chủ dự án nói "tiếp")
0. Đầu phiên: `get_orchestration_rules`, `list_terminals`, `git log --oneline -12`, `git status`. **Lịch tick và bộ theo dõi nền chết theo phiên**: không dựng Monitor; hỏi chủ dự án có cần dựng lại lịch tick (`CronCreate`, mỗi 11 phút) không.
1. **Bỏ `Rules.cs` PHẦN 1** (`Admission/_UseCases`, 12 tệp) bằng `PROMPT-BO-RULES-USECASES.md`: **một cửa sổ agy MỚI**, kiểm không còn `dotnet`; cổng PROMPT-CHUNG B. Sau commit, giao review chỉ-đọc song song (so thân hàm cũ `git show HEAD~1:<Rules.cs>` với hàm `private static` mới, không đổi hành vi/thứ tự tham số/thông báo; 5 ca trường hợp B: `SignMedicationReconciliationRules`, `SaveAdmissionExamDraftRules`, `GenerateRosterFromTeamRules`, `RecordInpatientVitalSignRules`, `SaveNursingShiftRules`). Rồi PHẦN 2 (Workspace, 32 tệp), PHẦN 3 (Nursing, 32 tệp), PHẦN 4 (siết `UseCaseArchitectureTests` + sửa tài liệu kế hoạch; chỉ khi 1–3 đã commit). Mỗi phần một commit, mỗi phần một cửa sổ (đóng khi xong). **Chú ý: các hàm Rules vừa bị sửa trong hai đợt fix (ví dụ `SaveNursingShiftRules`, `CreateHandoverRules`, `SendHandoverRules`) — agent phải đọc bản HEAD, không bản cũ.**
2. Sau PHẦN 4: **A4.4+A4.5** (`PROMPT-A4.4.md` sẵn; A4.4 thêm mã vào `Workspace/_UseCases` nên PHẢI sau PHẦN 2). Rồi **A5.0** (`PROMPT-A5.0.md` sẵn, nhạy cảm: không bịa ngưỡng lâm sàng/giá), rồi viết **PROMPT-A5.1..A5.5** (từ `KE-HOACH-CODING-SERVICE-A5.md` mục 5.2), rồi **A6a → A6c → A6b**.
3. Nợ nghiệm thu ở mục 3 (đọc thân hàm chưa kiểm). Có thể giao review chỉ-đọc sau khi chủ dự án đồng ý; tối đa 6 cửa sổ, chỉ một builder.
4. Khi chủ dự án trả lời mục 4: ghi vào `QUYET-DINH-TU-DONG.md`, giao sửa nếu cần (`-fix` riêng).

## 6. Agent, terminal, môi trường (lúc viết)
- Dashboard: `agent0` (PM; phiên khởi động lại giữa phiên), `agy-1` (**chủ dự án mở**, idle, PM không đóng được; đã làm nhiều việc ở phiên trước), `agy-2` (PM mở lúc ~11:00, model **Gemini 4 Argon medium**, đã làm **1/4 việc**: sửa lần 1 A1-A2; idle, báo cáo đã ghi). `claude-3`, `agy-4`, `agy-5`: đã đóng. Số agent được dùng lại sau khi cửa sổ cũ mất.
- **Phiên đã khởi động lại ~10:49** (agent cũ biến mất, lịch tick mất; commit của agent còn nguyên và cây sạch): cách xử lý đúng đã nằm ở `QUY-TAC` mục 13.
- Máy 15,8 GB RAM; Docker Desktop **không chạy**; không có PostgreSQL cục bộ. Chủ dự án nhắc: kiểm thử làm sau; không bật Docker.
- Số cửa sổ tối đa 6; `ram_free_warn_mb = 2000` (chỉ cảnh báo).

## 7. Bài học và sai sót của PM trong giai đoạn này
- **`[AO]` báo sai cả hai chiều** (agy-4/agy-5 báo xong khi còn làm; `claude-3` báo lặp ≥ 9 lần; không báo commit): đã ghi log cho chủ dự án sửa công cụ; PM đã đọc mã công cụ: `BUSY_MARKER` (`terminals.py:91`) chỉ khớp `Running (`/`Running…`, không khớp các chuỗi của agy (`Working…`, `Reading file…`, `Editing files…`, `Running command…`) — giả thuyết, chưa chạy thử.
- **Sai sót PM:** (1) nói "agy-1 rảnh / đủ 3 cửa sổ" mà không kiểm lại danh sách; (2) tự dựng Monitor thay vì báo công cụ sửa; (3) viết prompt sửa giao agent quét 34 tệp ⇒ agent chậm; (4) script đối chiếu hằng chỉ bắt `const string`, không bắt chuỗi viết thẳng và không kiểm đúng cột (lọt lỗi `CancelAdmission`); (5) thúc bật Docker/PgFact trái với "kiểm thử hoãn"; (6) nghiệm thu A3.4 trước đó không bắt lỗi đảo tham số (đã ghi ở bàn giao trước).
- **Hành vi agent đáng canh:** agent tự "chữa" một mục review bằng cách đổi hành vi mà test đang khoá (Supplement, A-05); tự thêm mặc định không ai yêu cầu (`?? 1`); báo cáo ghi "đã sửa" khi mã chưa sửa (Supplement lần đầu); đồng thuận 100% của review lẫn xác minh phải bị nghi ngờ.
- Việc làm tốt nên lặp: PM tự quét chỉ-đọc rồi đưa danh sách cụ thể; kiểm hằng so với CHECK của đúng cột; đọc test như bằng chứng về đặc tả trước khi chấp nhận sửa hành vi.

## 8. Tệp tham chiếu
- **Quy tắc/bàn giao:** `NhatKyCongViec/QUY-TAC-DIEU-PHOI-CMD-AGENT.md` (v2; bản sao ở `HIS_EMR/NhiDong/NhatKyCongViec/` **đang lệch**, chưa đồng bộ), `2026-11-10-ban-giao-phien-pm-a2-1c-den-a4-3.md`, file này.
- **Prompt/báo cáo (`promt/`):** `PROMPT-CHUNG.md` (đã thêm quy tắc giữ output nhỏ + kiểm thử hoãn), `PROMPT-BO-RULES-USECASES.md`, `PROMPT-A4.4.md`, `PROMPT-A5.0.md`, `PROMPT-FIX-REVIEW-A1-A2-fix1.md`, `PROMPT-XACMINH-REVIEW-A1-A2.md`, `BAOCAO-FIX-REVIEW-A3-A4.md`, `BAOCAO-FIX-REVIEW-A1-A2.md` (có mục SỬA LẦN 1), `BAOCAO-PHANTICH-USECASES-ADMISSION.md` (của `claude-3`, PM chưa đọc), `XACMINH-A1-A2-PHAN-A/B.md`, `REVIEW-A3-A4.md`, `REVIEW-A1-A2.md`, `DIEU-PHOI-TU-DONG.md`, `QUYET-DINH-TU-DONG.md`.
- **Công cụ (repo `agent-orchestrator`, PM không sửa):** `logs/ao-thong-bao-sai.md`, `develop/DE-XUAT-TU-DONG-BAN-GIAO-VA-KHOI-DONG-LAI-AGENT0.md`, `docs/TINH-NANG-QUY-TAC-DIEU-PHOI-AGENT.md`.
- **Bộ nhớ làm việc:** `feedback-terminal-agent-handoff.md` (đã thêm "Viết prompt KHÔNG làm agent chậm", kiểm thử hoãn), `feedback-ao-sai-ghi-log.md`, `feedback-cmd-agent-orchestration-rules.md`, `project-his-emr-pm-state.md`.
