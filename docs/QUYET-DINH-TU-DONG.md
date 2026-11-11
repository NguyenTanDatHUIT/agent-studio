# QUYẾT ĐỊNH THAY CHỦ DỰ ÁN (Agent 0, theo đề xuất của kế hoạch) — ghi 09/11/2026

Chủ dự án (treo máy ~5 giờ) uỷ quyền: "các vấn đề cần tôi quyết sẽ theo đề xuất của bạn nhưng cần ghi file lại". Mọi quyết định dưới đây **có thể đảo lại** khi chủ dự án xem lại. Nguồn đề xuất chuẩn: mục "Câu hỏi cho chủ dự án" của `KE-HOACH-CODING-SERVICE-A3/A4/A5.md`; bản tóm tắt: `CAU-HOI-CHU-DU-AN-A3-A5.md`.

## Nhóm 1 (chủ dự án ĐÃ duyệt thật, 09/11)
A3-Q9, A4-Q3, A5-Q2, A4-Q1, A4-Q2: đồng ý theo đề xuất.

## Nhóm 2 (Agent 0 quyết thay theo đề xuất)
| Mã | Quyết định |
|---|---|
| A3-Q1 | Nhắc phiếu đồng ý chưa ký tính khi đọc; hook `OnConsentPending` để rỗng |
| A3-Q2 | Bước thực hiện/nhật ký theo dõi lưu ở `nursing_tasks.result_data jsonb` (record C# kiểu mạnh), không thêm bảng |
| A3-Q3 | Ngưỡng PEWS Nhi là bảng trong code, ghi rõ "chưa phải giá trị chốt lâm sàng" |
| A3-Q4 | Sửa sinh hiệu trong 24 giờ: luôn ghi dòng mới + `correction_of_id`, không ghi đè |
| A3-Q5, Q7, Q8 | Theo đề xuất mục 7 của A3 |
| A3-Q6 | `continued_order_item_id` lưu `null`, nối ở A5 |
| A4-Q4 | Ký kế hoạch điều trị thất bại (`sign_state = 9`): trả thành công kèm trạng thái lỗi ký hoặc tách hàm ghi lỗi ký, theo đề xuất mục 7 của A4 |
| A4-Q5 | Đánh giá kế hoạch nhúng trong phiếu diễn biến chỉ gửi lúc chốt, không lưu nháp |
| A4-Q6 | Huỷ bản nháp kế hoạch: `status = -1` |
| A5-Q3 | Vòng đời sau ký làm đủ (PAUSED, sửa ngày kết thúc) theo `workspace-2.md` và DDL |
| A5-Q4 | Y lệnh miệng cấp cứu: `ACTIVE` ngay, bác sĩ xác nhận sau (theo mục 7 của A5) |
| A5-Q5 | Y lệnh học viên giữ `DRAFT` đến khi bác sĩ hướng dẫn đồng ký (trừ cấp cứu) |
| A5-Q6 | Cưỡng chế vượt cảnh báo `BLOCK`: theo đề xuất mục 7 của A5 (**nhạy cảm an toàn người bệnh: agent code phải ghi rõ nhánh vượt và lý do bắt buộc, có `LogBusinessEvent`; Agent 0 đọc kỹ khi nghiệm thu**) |
| A5-Q7 | Tương tác thuốc: đọc trực tiếp `drug_interactions` |
| A5-Q8 | Mốc cử rơi vào khoảng tạm ngưng: bỏ qua (`SKIPPED`), có cờ chọn |
| A5-Q9 | Dự trù chi phí y lệnh `OPEN_ENDED`: tính 1 ngày điều trị tiếp theo |
| A5-Q10 | Ký y lệnh CLS: chỉ tạo y lệnh + việc + hook, hook cho A6 (không ghi thẳng phiếu CLS/viện phí) |

## Câu hỏi mở cũ (quyết tạm thời)
| Mã | Quyết định tạm |
|---|---|
| A1.8 tuổi hiển thị | Giữ ngưỡng hiện có trong mã, không đổi |
| A1.8 quá hạn chờ tiếp nhận | Giữ 120 phút (như hiện có), riêng Cấp cứu làm sau |
| A1.8 `AssignedDepartmentIds()` = null khi chưa có `account_departments` | Giữ hành vi hiện tại (xem mọi khoa); chưa gộp hàm phạm vi khoa (K6 phần còn lại) |
| A2.2 `reason_code` lịch trực | Giữ hằng ở code |
| A2.1a dữ liệu sơ sinh trên nhãn vòng | Để `null` đến khi có nguồn dữ liệu; không bịa |
| A2.1a `alert_colors` | Giữ `null` (đặc tả: không mã hoá cảnh báo bằng màu vòng) |
| A2.1a người duyệt in lại trùng người thao tác | Cho phép nếu người đó có cờ `a` (như đã code) |
| A6 (khi tới lượt) | Theo đề xuất trong kế hoạch A6a/b/c; thứ tự A6a → A6c → A6b; khoảng hở DB (GAP-DB-1..5 của A6b) KHÔNG tự sửa `Database/**`: ghi thành câu hỏi cho chủ dự án và bỏ qua phần phụ thuộc |

## Nhật ký quyết định bổ sung (Agent 0 ghi thêm ở đây)
- 10/11/2026 ~12:30 (chủ dự án giao quyền "theo đề xuất" cho 3 câu hỏi từ REVIEW-NO-NGHIEMTHU; đảo lại được):
  - NNT-1 ký số phiếu diễn biến: người ký PHẢI là tác giả (đồng bộ Finalize/StartCorrection), không cho ký thay. Lý do: chữ ký số gắn trách nhiệm cá nhân.
  - NNT-2 thang đánh giá lệch tuổi ngoài nhóm đau: GIỮ như hiện tại (cho lưu kèm "Lưu ý độ tuổi"), không chặn. Lý do: mã cố ý ghi chú, chưa có đặc tả bắt chặn.
  - NNT-3 3 Command điều dưỡng ghi: kiểm phạm vi khoa như worklist (GetWorklistAllowedDepartmentIds). Lý do: đồng bộ với đọc, tránh ghi chéo khoa.
  - Thứ tự: FIX-NNT sau PHẦN 3 (các Rules sẽ gộp vào Command), trước A4.4. Agent sửa phải tự xác minh từng mục (XÁC NHẬN/KHÔNG TÁI HIỆN/KHÁC); mục Partial-dị ứng và lọc kíp MyPatientsMany chưa xác minh.

- 10/11 ~14:25 (CHU DU AN chi dao): "code service nao thi build service do". Quyet dinh BLD-1: cong mac dinh moi commit = B1 (build tang dan project vua sua + test lien quan); cong day du 2 solution --no-incremental = B2, chi khi PM yeu cau (cuoi dot/truoc moc tich hop). PM chay B2 mot lan cuoi chuoi FIX-NNT/A4 de kiem day chuyen. Da sua PROMPT-CHUNG.md muc B. Viec dang chay (FIX-NNT) da doc ban cu, khong doi giua chung.

- 10/11 ~14:40 (CHU DU AN nhac lai): "chi coding thoi". Sua BLD-1: BO HAN buoc chay test khoi cong (khong dotnet test, khong Phase6/Phase4, khong T5 bat buoc). Cong = build project vua sua (B1) / build day du 2 sln (B2, khi PM yeu cau). Mat bao ve: UseCaseArchitectureTests (cam *Rules.cs trong _UseCases) khong con tu chay; chu du an co the bat lai khi can. PM sai khi dua test vao B1 truoc do; da sua.

- 10/11 ~14:50 (CHU DU AN chi dao): build chi project dang code nen nhieu agent co the code service khac nhau. Quyet dinh BLD-2: thay single_builder toan cuc bang KHOA THEO PROJECT/PHU THUOC. Dieu kien (PM kiem cau truc 10/11): Billing,Emr->Core; Pharmacy->Core,Billing; Inpatient->Core,Billing,Emr; Nursing,Emergency->Core,Inpatient; InpatientPharmacy->Core,Inpatient,Pharmacy. Hai agent build song song CHI KHI project nay khong nam trong closure cua kia (va nguoc lai), khong ai sua Service.Core/Utility2/DBContext/Database, toi da 2 build; B2 va project dung chung doc quyen. Da sua PROMPT-CHUNG.md (muc A + Rang buoc chung) va docs spec (builder_lock_scope). CHUA sua duoc: setting single_builder trong Cai dat dashboard va rules_markdown get_orchestration_rules (chu dung chinh tay).

- 10/11 ~15:00 (CHU DU AN): tang so build song song toi da tu 2 len 3 (BLD-2 sua). Da sua PROMPT-CHUNG.md + docs spec (max_parallel_builders mac dinh 3). PM rà ke hoach cho agent moi: (1) RowLockTables.cs va DefaultFeatures.cs nam trong Service.Core (project dung chung): moi job nen (A5.0, A6a.0, A6b.0, A6c.0) sua Core => doc quyen, khong song song voi bat ky build nao; (2) Service.Inpatient la hub (Billing, Emr, Nursing, Emergency, InpatientPharmacy deu lien quan) => A5.x, A6b.x tuan tu; A5.1||A5.2 cua ke hoach cung project nen KHONG song song duoc theo khoa; (3) song song that su chi khi Inpatient yen: A6a (Emergency) || A6c (Pharmacy/InpatientPharmacy). Thu tu de xuat: A5.0 -> nen A6a.0/A6b.0/A6c.0 (mot cua so, tuan tu) -> A5.1..A5.5 -> A6b -> [A6a || A6c song song]. Viec song song an toan ngay: review chi-doc (agy-1: PROMPT-REVIEW-A4.4.md, giao ~15:00).

- 10/11 ~15:20 (CHU DU AN CHO PHEP, deadline): moi agent mot GIT WORKTREE rieng de code song song. Quyet dinh BLD-3: (a) worktree dat o C:/wt/<ten> (duong dan ngan, longpaths da bat), nhanh wt/<ten> tao tu main; Agent 0 tao worktree (khong xoa worktree nao; cac worktree .codex cua cong cu khac KHONG dung); (b) agent chi lam trong worktree cua minh, commit len nhanh minh, khong merge/rebase/checkout/push; (c) Agent 0 TICH HOP vao main CUC BO (git merge --no-ff, KHONG push) sau khi nghiem thu tung luong, giai quyet xung dot RowLockTables.All/DefaultFeatures (thu tu khoa dong la thu tu toan cuc), roi chay B2 tren main khi khong ai build main; moi nhanh giu nguyen de revert; (d) tong so build song song toi da 3 (agy-3 tren main + 2 worktree); (e) mien khoa-theo-project (BLD-2) chi con ap trong cung mot worktree/cay. Luong dau: wt/a6a (A6a.0->A6a.1->A6a.2, Service.Emergency) agy-4; wt/a6c (A6c.0->A6c.2->A6c.3, Pharmacy/InpatientPharmacy) agy-5. A6a.3/.4 va A6c.1 can A5: lam sau khi A5 tich hop. A6b chua co luong (GAP-DB, thu tu A6a->A6c->A6b). Prompt: PROMPT-WT-A6a.md, PROMPT-WT-A6c.md; PROMPT-CHUNG.md muc F.

- 10/11 ~15:30 (CHU DU AN chi dao): "neu cong viec xong thi don no khoi tao cmd agy moi". Quyet dinh WIN-1: khi mot viec cua mot cua so da duoc nghiem thu dat thi Agent 0 (a) DONG cua so do neu do Agent 0 mo (cua so chu du an mo, vd agy-1, khong dong duoc), (b) MO cua so agy MOI (Gemini 4 Argon Medium; hien mac dinh da Medium) cho viec ke trong hang doi, trong WORKTREE rieng khi la coding; (c) giu toi da 6 cua so, toi da 3 build song song (cua so moi doc/viet truoc, CHUA build den khi duoc bao). Ap dung ngay: agy-1 xong review -> mo agy-7 cho A5.1 (wt/a51).

- 10/11 ~16:35 (PM, theo review A5.2 của agy-10; đảo lại được): FIX-A52 mục 4 sở hữu nháp y lệnh: sửa/áp bộ mẫu vào nháp đã có CHỈ cho người tạo nháp; `CancelOrderDraft` cho người tạo hoặc bác sĩ điều trị chính (`AttendingDoctorId`) và bắt buộc cờ `d`. Lý do: PROMPT-CHUNG G.1 (nháp bác sĩ khác không được hiện) + kế hoạch A5 O-07. Mục 2: ghi đè nhánh khẩn của ALLERGY_REVIEW_MISSING chỉ khi lô CÓ thuốc/dịch truyền và TẤT CẢ đều Urgent.

- 10/11/2026 ~21:45 (CHỦ DỰ ÁN trả lời "theo đề xuất" cho 5 câu A6b; đảo lại được): **A6b-Q1** giao DBA thêm `DROP INDEX IF EXISTS public.ux_clinical_documents_encounter_doc_type;` vào script migration (BẮT BUỘC trước khi thử tích hợp DB `CreateRecordFromTemplate`; agent code KHÔNG sửa `Database/**`). **A6b-Q2** phương án (a): dùng cột thật hiện có cho GAP-DB-1/2/3 (`record_access_audit.is_sensitive` + lý do bắt buộc ở `purpose`; `record_addenda.content`, sắp theo `created_date, id`; số lưu trữ/khóa sửa qua `emr_record_archives` theo từng `DocumentId`); không thêm cột. **A6b-Q3** chốt 2 lần áp cho cả 24 mẫu `BV1` nội trú theo `section` (Phần A = lần 1, Tổng kết/Phần B = lần 2). **A6b-Q4** cho phép thêm built-in `Admission.Reason -> InpatientAdmission.Reason` ở A6b.2; `Encounter.StartTime` và `Patient.Nationality` chờ chốt nghĩa nghiệp vụ (không làm). **A6b-Q5** thêm nút `noi_tru.ho_so_benh_an` (`Has: "vcudta"`, `Sidebar: false`) và cờ `a` vào `dich_vu.mau_in` trong `DefaultFeatures.cs` (ở A6b.0).

- 10/11/2026 ~23:55 (CHỦ DỰ ÁN): mọi agent phải đọc `NhatKyCongViec\promt\QUY-LUAT-CHONG-LOI-LAP-LAI.md` (R1–R5 + checklist 10 điểm trước mỗi commit). Đã thêm vào `PROMPT-CHUNG.md` (bản canonical `C:\AgentControl\studio-state\prompts\` + hai bản sao) một đoạn BẮT BUỘC đọc + tự đối chiếu 10/10 trước MỖI commit + dòng xác nhận trong báo cáo, kèm 5 bổ sung rút từ review thực tế (LogBusinessEvent từ chối ngoài lambda, không trùng tên hàm, không suy nghĩa từ tên hằng, tên constraint đúng DDL, không để cờ client quyết định quyền). Mọi prompt giao việc MỚI (và PM khi nghiệm thu) dùng checklist này; agent đang chạy được nhắc đọc.
