# BỐI CẢNH ĐỂ XÁC NHẬN — CPT-Q7-1: NGUỒN MỨC HƯỞNG BHYT CỦA KHOẢN THU NỘI TRÚ (11/11/2026)

Tài liệu tự đủ để giao cho một agent/người khác hỗ trợ xác nhận. Người đọc KHÔNG cần đọc cả nhật ký. Dự án: `HIS_EMR` (.NET 8, PostgreSQL), mã tại `C:\CongViec\itc-git\HIS_EMR\NhiDong\Source\NET8\Services\HIS\` (viết tắt `S/`), DDL tại `NhiDong\Database\`.

## 1. Câu hỏi cần được trả lời (một câu)
**Khi tính tiền BHYT cho một khoản thu của người bệnh NỘI TRÚ, "mức hưởng" phải lấy từ nguồn nào, tại thời điểm nào?** Mã hiện lấy: thẻ BHYT (`health_insurance_cards.benefit_level`) còn hiệu lực tại thời điểm thực hiện dịch vụ; nếu không có thì `encounters.benefit_rate` (khi > 0); nếu cũng không có thì coi là "chưa xác định" (không trừ BHYT). Cần bộ phận BHYT/KHTH/giám định xác nhận đó có đúng quy trình thực tế không, và các trường hợp ngoại lệ (mục 4).

## 2. Vì sao câu hỏi này xuất hiện
- **Ước tính chi phí** (bảng kê tạm tính, khi bác sĩ ra y lệnh) đã đọc mức hưởng từ THẺ BHYT. **Khoản thu thật** (`BillingService.RecordCharge`) trước đây chỉ đọc từ lượt khám (`encounters`) và chỉ khi `PaymentObjectId == 1 && IsRightRoute`.
- Khi nhập viện, `CompleteAdmission` tạo lượt khám nội trú MỚI với `IsRightRoute = false`, `BenefitRate = 0` và không có ca nội trú nào cập nhật hai cột này ⇒ khoản thu thật nội trú có thể không được trừ BHYT trong khi ước tính có trừ ⇒ nguy cơ **thu thừa tiền người bệnh**, và bảng kê lệch.
- Chủ dự án quyết định (C-2): cho khoản thật dùng CÙNG bộ đọc mức hưởng với ước tính. Việc này đã được code ở đợt **E3d** (đang trong review độc lập, chưa vào `main`). Nhưng CHƯA ai ở phía nghiệp vụ xác nhận nguồn đó đúng.

## 3. Hiện trạng mã (bằng chứng; dòng theo `main@8290bc35` và nhánh `wt/e3d@6e360cc5`)
| Nơi | Hành vi | Tệp:dòng |
|---|---|---|
| Tiếp nhận ngoại trú | Mức hưởng = giá trị nhân viên nhập (`ins.BenefitLevel`) → mức đã lưu của thẻ (`card.BenefitLevel`) → trẻ dưới 6 tuổi 100% → còn lại 0 + cảnh báo "chưa có mức hưởng". **Thẻ không hợp lệ (hết hạn, v.v.) ⇒ mức áp dụng cho lượt = 0** (mức của thẻ vẫn lưu ở thẻ). Lưu vào `Encounter.BenefitRate`; `IsRightRoute = model.Insurance?.IsRightRoute ?? true` | `S/Service.Core/Executes/Legacy/ADT/Receptions/ReceptionCommand.cs:366, 418-419, 759, 811` |
| Cấp cứu → nội trú | Sao chép `IsRightRoute` và `BenefitRate` từ lượt khám nguồn (hoặc `request.BenefitRate`) | `S/Service.Emergency/Executes/Emergency/UseCases/AdmitFromEmergency/AdmitFromEmergencyCommand.cs:752-753` |
| Nhập viện nội trú (`CompleteAdmission`) | Tạo `Encounter` mới: `PaymentObjectId = r.PayerType`, **`IsRightRoute = false`, `BenefitRate = 0`**. Đợt nội trú lưu `HealthInsuranceCardId = r.HealthInsuranceCardId` và `BhytRoute = r.BhytRoute`. Kiểm thẻ chỉ `Status >= 0 && PatientId` khớp — KHÔNG kiểm hiệu lực ngày, KHÔNG kiểm tuyến | `S/Service.Inpatient/Executes/Admission/UseCases/CompleteAdmission/CompleteAdmissionCommand.cs:233-237, 274, 324-325, 381, 396` |
| Ước tính nội trú | `ResolveAdmissionBhytBenefitRatio`: (1) `inpatient_admissions.health_insurance_card_id` → `health_insurance_cards.benefit_level` (1..100) với `Status > 0`, `ValidFrom <= ngày`, `ValidTo >= ngày` (ngày = mốc tính, kiểu `DateOnly`); (2) dự phòng `encounters.benefit_rate` khi `> 0 và <= 100`; (3) trả `null` = chưa xác định ⇒ không giảm tiền, đánh dấu `IsBhytBenefitRateUndetermined` | `S/Service.Inpatient/Executes/Base/InpatientService.OrderCore.cs:~2117` (nhánh E3d: chuyển nguyên văn sang `S/Service.Core/Components/BhytBenefitResolver.cs`) |
| Khoản thu thật — TRƯỚC E3d | `benefitRate` chỉ từ `encounters.BenefitRate` khi `PaymentObjectId == 1 && IsRightRoute` | `S/Service.Billing/Executes/Billing/Payments/PaymentCommand.cs:~553-558, 599-608` |
| Khoản thu thật — SAU E3d (đang review) | Khoản nội trú có `PayerType = BHYT`: `benefitRate = bộ đọc chung × 100` (null ⇒ 0). Khoản không phải BHYT: ép 0. Ngoại trú: không đổi | `PaymentCommand.cs` nhánh `wt/e3d` (3 dòng sau kiểm `resolvedPayerType`) |
| Đổi đối tượng giữa đợt | `ChangePayer` chỉ đổi `inpatient_admissions.payer_type` và ghi `admission_payer_changes` (cũ→mới, `effective_from`); KHÔNG đổi thẻ, KHÔNG đổi `encounters.PaymentObjectId`. Khoản thu chụp `payer_type` theo mốc thực hiện | `S/Service.Inpatient/Executes/Admission/UseCases/ChangePayer/ChangePayerCommand.cs:68-90` |

**Dữ liệu liên quan (DDL/entity):** `health_insurance_cards(id, patient_id, card_number, valid_from, valid_to, benefit_level, object_code, status)`; `inpatient_admissions(health_insurance_card_id, bhyt_route, payer_type, admitted_at, discharge_time, encounter_id)` (xem `Database/01_tiep_nhan/inpatient_admissions.sql`); `encounters(payment_object_id, is_right_route, benefit_rate)`.

## 4. Các điểm cần xác nhận (mỗi câu: đáp án + nguồn + mức tin cậy)
| # | Câu hỏi | Mã đang giả định | Hệ quả nếu đáp án khác |
|---|---|---|---|
| Q1 | Mức hưởng nội trú lấy theo **thẻ** (`benefit_level` hiệu lực tại ngày thực hiện dịch vụ) có đúng không? Hay lấy mức tại ngày nhập viện, hay theo tuyến/đối tượng, hay theo kết quả tra cổng BHXH? | Thẻ hiệu lực tại ngày thực hiện; dự phòng `encounters.benefit_rate > 0` | Sửa nguồn trong `BhytBenefitResolver` (một chỗ, dùng chung ước tính và khoản thật) |
| Q2 | **Tuyến** (`bhyt_route`, `IsRightRoute`) có ảnh hưởng mức hưởng NỘI TRÚ không? (trái tuyến nội trú có được hưởng như đúng tuyến?) | Bộ đọc KHÔNG xét tuyến; `IsRightRoute` bỏ qua với nội trú | Thêm hệ số tuyến vào bộ đọc; dữ liệu `bhyt_route` phải đáng tin |
| Q3 | **Thẻ hết hạn giữa đợt** (ValidTo nằm trong thời gian nằm viện): các dịch vụ sau ngày hết hạn tính thế nào? (hưởng tới ra viện? giới hạn số ngày? chuyển Viện phí?) | Chỉ kiểm thẻ còn hiệu lực tại ngày thực hiện ⇒ sau ValidTo mà không có `encounters.benefit_rate > 0` thì BHYT = 0 | Thêm quy tắc gia hạn hoặc giữ mức theo ngày nhập viện. (Tài liệu phương án đề xuất "tối đa 15 ngày" — **CHƯA XÁC MINH**, không được dùng làm căn cứ) |
| Q4 | **Trẻ dưới 6 tuổi:** nội trú có mặc định hưởng 100% khi chưa có mức không? (ngoại trú mặc định 100 nếu dưới 6 tuổi; bộ đọc nội trú KHÔNG có nhánh này) | Không có nhánh dưới 6 tuổi ⇒ chưa có thẻ/mức thì 0 | Thêm nhánh tuổi vào bộ đọc, cần ngày sinh và quy định cụ thể |
| Q5 | **Đổi thẻ/đổi đối tượng giữa đợt** (vào chưa có thẻ, hôm sau trình thẻ; hoặc đổi mã quyền lợi): thẻ gắn đợt (`health_insurance_card_id`) được cập nhật bằng ca nào? Có lịch sử thẻ theo đợt không? Khoản đã ghi trước khi trình thẻ có tính lại không? | Đợt chỉ có MỘT `health_insurance_card_id`; không lịch sử thẻ; không tính lại khoản đã ghi | Cần bảng lịch sử thẻ theo đợt + ca tính lại (CPT-Q7-9) |
| Q6 | **Thẻ không hợp lệ nhưng đợt ghi PayerType = BHYT:** ví dụ thẻ chưa có `ValidFrom/ValidTo` (`default`), hay thẻ `Status <= 0`? | Thẻ `Status <= 0` hoặc ngoài hiệu lực ⇒ rơi xuống dự phòng `encounters.benefit_rate`, rồi 0 | Kiểm dữ liệu thật (mục 6) |
| Q7 | **Khoản đã ghi TRƯỚC khi sửa** (khoản nội trú BHYT với `insurance_amount = 0`): có phải tính lại/hoàn cho người bệnh không? | Không tính lại | Cần script tính lại + quy trình hoàn (thuộc E7, đang bị chặn) |
| Q8 | **Công thức sau mức hưởng:** `tiền BHYT = giá × tỷ lệ thanh toán danh mục (InsuranceCoverageRate) × mức hưởng`; có cần thêm trần tiền tuyệt đối theo danh mục (stent, khớp...) và đồng chi trả không? (CPT-Q7-3/8) | Chỉ tỷ lệ danh mục × mức hưởng; chưa có trần tuyệt đối trong mã | Ngoài phạm vi CPT-Q7-1 nhưng cần ghi nhận |

## 5. Những điều KHÔNG được làm khi xác nhận
- KHÔNG kết luận quy định pháp lý từ trí nhớ hay từ "tài liệu phương án" (`ph_ng_n_x_l_nghi_p_v_his_emr_11_11_2026.md`): mọi khẳng định (mốc 15 ngày thẻ hết hạn, miễn cùng chi trả 5 năm, thông tuyến nội trú 100%, dưới 6 tuổi) đang ở trạng thái **CHƯA XÁC MINH**. Chỉ nhận khi có trích dẫn văn bản cụ thể (loại văn bản, số hiệu, điều/khoản, ngày hiệu lực) hoặc xác nhận bằng văn bản của người có thẩm quyền.
- KHÔNG sửa mã nguồn, DDL, dữ liệu. KHÔNG viết/chạy test. KHÔNG đụng 11 container Docker của dự án khác (`ricons-*`, `worldpulse-*`, `newsolution-*`).
- KHÔNG tự điền số liệu (tỷ lệ, số ngày, mốc) vào mã hay vào báo cáo như thể đã được xác nhận.
- Truy vấn DB thật chỉ khi chủ dự án cấp quyền và CHỈ ĐỌC (`SELECT`).

## 6. Truy vấn chỉ-đọc gợi ý để kiểm dữ liệu thật (DBA/agent có quyền; tên bảng/cột suy từ entity, chỉnh nếu khác)
```sql
-- A) Đợt nội trú theo đối tượng và có/không gắn thẻ
SELECT a.payer_type, (a.health_insurance_card_id IS NOT NULL) AS co_the_gan_dot, COUNT(*) AS so_dot
FROM public.inpatient_admissions a WHERE a.status >= 0 GROUP BY 1,2 ORDER BY 1,2;

-- B) Đợt BHYT có thẻ HẾT HẠN trong thời gian nằm viện (ValidTo trước ngày ra viện hoặc trước hôm nay)
SELECT a.id, a.admission_code, a.admitted_at, a.discharge_time, c.valid_from, c.valid_to, c.benefit_level
FROM public.inpatient_admissions a
JOIN public.health_insurance_cards c ON c.id = a.health_insurance_card_id
WHERE a.status >= 0 AND a.payer_type = 1
  AND c.valid_to < COALESCE(a.discharge_time::date, current_date)
ORDER BY a.admitted_at DESC;

-- C) Lượt khám nội trú: BenefitRate/IsRightRoute (kỳ vọng nhiều dòng 0/false do CompleteAdmission)
SELECT e.payment_object_id, e.is_right_route, (e.benefit_rate = 0) AS benefit_bang_0, COUNT(*) AS so_luot
FROM public.inpatient_admissions a JOIN public.encounters e ON e.id = a.encounter_id
WHERE a.status >= 0 GROUP BY 1,2,3 ORDER BY 4 DESC;

-- D) Chênh giữa mức hưởng trên thẻ và trên lượt khám của cùng đợt (cả hai > 0)
SELECT a.id, c.benefit_level AS muc_the, e.benefit_rate AS muc_luot
FROM public.inpatient_admissions a
JOIN public.health_insurance_cards c ON c.id = a.health_insurance_card_id
JOIN public.encounters e ON e.id = a.encounter_id
WHERE a.status >= 0 AND c.benefit_level > 0 AND e.benefit_rate > 0 AND c.benefit_level <> e.benefit_rate;

-- E) Đợt BHYT KHÔNG có thẻ gắn (mức hưởng chỉ có thể lấy từ dự phòng hoặc không có)
SELECT a.id, a.admission_code, a.admitted_at, a.bhyt_route
FROM public.inpatient_admissions a
WHERE a.status >= 0 AND a.payer_type = 1 AND a.health_insurance_card_id IS NULL;
```

## 7. Mẫu kết quả mong muốn (một tệp markdown ngắn)
Bảng: `Q# | Đáp án | Nguồn (văn bản + điều/khoản, hoặc người xác nhận + ngày, hoặc kết quả truy vấn) | Mức tin cậy (cao/trung/thấp, vì sao) | Hệ quả với mã (sửa gì, ở đâu)`. Thêm mục "Chưa xác minh được" liệt kê rõ điều gì còn thiếu và ai cần hỏi. Kết quả truy vấn dữ liệu (mục 6) kèm số liệu thật, không đưa dữ liệu định danh người bệnh vào báo cáo.

## 8. Tác động tới kế hoạch
- Không chặn việc merge E3d (đã dùng cùng nguồn với ước tính), nhưng quyết định đúng/sai nguồn thuộc về xác nhận này. Nếu Q1–Q4 đáp án khác mã hiện tại ⇒ sửa MỘT chỗ (`BhytBenefitResolver`) rồi hồi quy ước tính + khoản thật.
- Q5, Q7 mở thêm việc: lịch sử thẻ theo đợt, ca tính lại khoản đã ghi, hoàn tiền (E7).
- Liên quan: `CAN-PHAN-TICH-THEM-E6B-Q7-BHYT.md` (CPT-Q7-1..9), `DOI-CHIEU-PHUONG-AN-NGHIEP-VU-2026-11-11.md` (mục B và C-2), `PROMPT-WT-E3D.md`, `REVIEW-E3D.md` (khi có).
