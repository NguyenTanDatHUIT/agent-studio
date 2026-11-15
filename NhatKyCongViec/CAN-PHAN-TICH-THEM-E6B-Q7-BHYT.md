# CẦN PHÂN TÍCH THÊM — E6b câu 7: công thức BHYT của khoản thu nội trú (11/11/2026)

## Quyết định của chủ dự án (11/11/2026)
Câu 7 của `THIETKE-E6B.md`: **làm theo hướng đề xuất — giữ công thức BHYT hiện có của `BillingService.RecordCharge`** (đã sửa ở E3b-fix2: chỉ trừ BHYT khi `payer_type = BHYT`; `benefitRate` lấy từ `Encounter.BenefitRate` khi `PaymentObjectId == 1 && IsRightRoute`), **kèm đánh dấu mọi vấn đề còn lại cần phân tích thêm** (danh sách dưới). Công thức này là GIẢ ĐỊNH TẠM, KHÔNG phải kết luận cuối.

## Quy ước đánh dấu
- Mã vấn đề: `CPT-Q7-<số>`. Mọi agent chạm tính BHYT ở E6b (và sau này) PHẢI: (a) đặt chú thích mã nguồn dạng `// [CAN-PHAN-TICH-Q7:CPT-Q7-n] <mô tả ngắn>` tại đúng chỗ bị ảnh hưởng; (b) liệt kê các mã đã chạm trong báo cáo; (c) KHÔNG tự "sửa" công thức để khớp ước tính.
- Tìm lại bằng `grep -rn "CAN-PHAN-TICH-Q7" NhiDong/Source/NET8`.
- Khi chủ dự án/bộ phận BHYT chốt: sửa theo quyết định, xóa dấu, cập nhật tệp này.

## Danh sách vấn đề (PM đã đối chiếu mã; mục "Bằng chứng" là tệp:dòng thật trên `main@d1b461d7`/`wt/e3b`)

| Mã | Vấn đề | Bằng chứng | Hậu quả nếu để nguyên | Cần ai xác nhận |
|---|---|---|---|---|
| CPT-Q7-1 | **Hai nguồn mức hưởng khác nhau.** Ước tính lấy `health_insurance_cards.benefit_level` (thẻ còn hiệu lực tại ngày tính) rồi mới dự phòng `encounters.benefit_rate > 0`; khoản thật chỉ lấy `encounters.benefit_rate` khi `PaymentObjectId == 1 && IsRightRoute`. | `InpatientService.OrderCore.cs:2117-2155` (`ResolveAdmissionBhytBenefitRatio`); `PaymentCommand.cs:~523-559` (`RecordCharge`) | Cùng một y lệnh: ước tính có BHYT, khoản thật không (hoặc lệch %) ⇒ bảng kê "thực tế vs dự kiến" lệch, người bệnh bị báo sai. | Bộ phận BHYT / KHTH |
| CPT-Q7-2 | **Nội trú tạo lượt khám mới có `IsRightRoute = false`, `BenefitRate = 0`** và không ca nội trú nào cập nhật hai cột này (grep `IsRightRoute\|BenefitRate` trong Inpatient/Nursing/InpatientPharmacy/Billing: chỉ `CompleteAdmissionCommand.cs:324-325` ghi). ⇒ `RecordCharge` có thể cho BHYT = 0 với mọi khoản nội trú của đợt không đi từ lượt khám ngoại trú đã có tuyến/mức hưởng. | `CompleteAdmissionCommand.cs:324-325`; `PaymentCommand.cs:530,558` | Khoản thật nội trú có thể KHÔNG được trừ BHYT dù người bệnh đóng BHYT ⇒ thu thừa tiền của người bệnh. **Rủi ro CAO nhất của câu 7.** | Chủ dự án + BHYT (ai cập nhật tuyến/mức hưởng cho đợt nội trú, lúc nào) |
| CPT-Q7-3 | **Trần danh mục khác nhau.** Ước tính nhân thêm `CatalogInsuranceCoverageRate` (trần theo danh mục thuốc/dịch vụ) rồi mới nhân mức thẻ; `RecordCharge` dùng `InsurancePrice`/`InsuranceCoverageRate` do NGƯỜI GỌI truyền (vật tư) hoặc 100%. | `OrderCore.cs:2049-2080`; `PaymentCommand.cs` (`itemCoverageRate`, `basis`) | Cùng một dịch vụ, hai công thức ⇒ số lệch. E6b không có người gọi truyền `InsuranceCoverageRate` ⇒ sẽ dùng 100% trừ khi thiết kế bổ sung. | BHYT |
| CPT-Q7-4 | **Đối tượng thanh toán đổi giữa đợt.** `ChangePayer` chỉ đổi `adm.PayerType`, không đổi `enc.PaymentObjectId`; khoản thật chụp `payer_type` theo `admission_payer_changes` (E3b-fix2) nhưng `benefitRate` vẫn từ `enc`. | `ChangePayerCommand.cs:74-90`; `PaymentCommand.cs` (E3b-fix2) | Trường hợp BHYT→viện phí đã xử lý (ép 0). Trường hợp viện phí→BHYT giữa đợt: `payer_type = BHYT` nhưng `benefitRate` có thể vẫn 0 (xem CPT-Q7-2). | BHYT |
| CPT-Q7-5 | **Thẻ BHYT hết hạn giữa đợt.** Ước tính kiểm thẻ còn hiệu lực theo ngày tính; khoản thật không kiểm thẻ. Cách xử lý mặc định chưa có (mục "chờ pháp chế" của `KHOANG-TRONG`). | `OrderCore.cs:2129-2140`; `KHOANG-TRONG-E2-E7-D11.md` mục 5/BHYT hết hạn | Khoản thật vẫn hưởng BHYT sau ngày hết hạn. | Pháp chế |
| CPT-Q7-6 | **Dưới 6 tuổi và các quy tắc BHYT khác** (đồng chi trả, trần theo bậc, tuyến trái) chưa có trong công thức nào; `KHOANG-TRONG` mục 10 ghi "chưa chốt". | `KHOANG-TRONG-E2-E7-D11.md` mục 10 | Mức hưởng đặc biệt không được phản ánh. | BHYT |
| CPT-Q7-7 | **Bảng kê/quyết toán** (E6a `FeeBoardOne`, D11-2b) cộng khoản thật và ước tính có thể dùng hai công thức khác nhau trên cùng một y lệnh. Hiển thị "ước tính còn lại" (E6b đợt 1) sẽ so hai số lệch nhau. | `FeeBoardOne.cs:173-216` | Số hiển thị không nhất quán cho đến khi hai công thức thống nhất. | PM + BHYT |

## Xử lý tạm (cho tới khi chốt)
1. Giữ công thức `RecordCharge`; không đổi công thức ước tính.
2. E6b chỉ GHI khoản; không "điều chỉnh bù" giữa ước tính và thực tế.
3. Mỗi khoản có `payer_type` và `price_source` chụp (E3b) ⇒ về sau có thể tính lại hàng loạt khi công thức được chốt (cần script riêng, ghi `price_version_ref`).
4. Báo cáo của mọi đợt E6b nêu rõ mã `CPT-Q7-*` đã chạm.

## Việc tiếp theo (chưa ai làm)
- Chủ dự án chỉ định người của bộ phận BHYT/KHTH xác nhận CPT-Q7-1, 2, 3, 5, 6 (đặc biệt CPT-Q7-2).
- Sau khi có quyết định: một đợt riêng "thống nhất công thức BHYT" (dùng chung hàm `ChargeMath` cho ước tính và khoản thật) + tính lại khoản đã ghi.

---
## Bổ sung 11/11 chiều muộn — đối chiếu với "Phương án xử lý nghiệp vụ" (Downloads)
Chi tiết ở `DOI-CHIEU-PHUONG-AN-NGHIEP-VU-2026-11-11.md`. Tóm tắt tác động lên danh sách `CPT-Q7`:
- **CPT-Q7-2 (CAO):** PA đề xuất tính lại `IsRightRoute`/`BenefitRate` ở `CompleteAdmission`. PM đề xuất hướng ít rủi ro hơn (CHƯA duyệt): `RecordCharge` dùng cùng bộ đọc mức hưởng như ước tính (`ResolveAdmissionBhytBenefitRatio`: thẻ `benefit_level`, dự phòng `encounters.benefit_rate`); không ghi đè `encounters`. Cần BHYT xác nhận nguồn mức hưởng.
- **CPT-Q7-3:** thêm **CPT-Q7-8** — PM chưa thấy cột "trần tiền tuyệt đối" theo danh mục trong mã/DDL (chỉ có tỷ lệ `InsuranceCoverageRate`); công thức `min(T×R_DM, C_tran) × R_huong` của PA chưa tính được cho tới khi kiểm DDL (xem DOI-CHIEU Phụ lục 2) và BHYT chốt thứ tự phép tính.
- **CPT-Q7-4:** thêm **CPT-Q7-9** — thẻ BHYT trình muộn giữa đợt (hai chế độ hồi tố đầu đợt / tách mốc) chưa có thiết kế; phụ thuộc công thức thống nhất.
- **CPT-Q7-5:** mốc "tối đa 15 ngày" của PA **CHƯA XÁC MINH**, PM nhớ quy định là hưởng tới khi ra viện; KHÔNG đưa tham số `InpatientCardExpiryGraceDays` vào mã cho tới khi pháp chế xác nhận.
- **CPT-Q7-6:** các quy tắc dưới 6 tuổi, miễn cùng chi trả, thông tuyến nội trú trong PA **CHƯA XÁC MINH** (BHYT).

---
## Bổ sung 11/11 tối — sau xác minh "KẾT QUẢ XÁC NHẬN CPT-Q7-1" (xem `XAC-MINH-KET-QUA-CPT-Q7-1-VA-QUYET-DINH-THUC-HIEN.md`)
- **CPT-Q7-5 (thẻ hết hạn giữa đợt): ĐÍNH CHÍNH.** Số **15 ngày** có căn cứ thứ cấp (2 nguồn cùng trích khoản 9 Điều 27 Nghị định 146/2018/NĐ-CP: hưởng đến khi ra viện, tối đa 15 ngày kể từ ngày thẻ hết hạn). Trích dẫn "Điều 50 Nghị định 188/2025" của tài liệu KQ KHÔNG tìm thấy căn cứ; chưa xác nhận Nghị định 188/2025 hiện hành còn giữ quy tắc này; văn bản gốc chưa đọc được. Mã dùng tham số cấu hình `InpatientCardExpiryGraceDays` (mặc định 15, "chưa chốt") — đợt **E3e**. Ghi chú trước đó "hưởng tới khi ra viện" (thiếu giới hạn 15 ngày) được sửa lại.
- **CPT-Q7-1:** nhánh dự phòng `encounters.benefit_rate` chỉ chạy khi đợt KHÔNG gắn thẻ (E3e).
- **Tính thời vụ của thông số pháp lý:** lương cơ sở đã đổi 2.530.000 đồng từ 01/7/2026 (Nghị định 161/2026/NĐ-CP); Nghị định 188/2025 đang được sửa đổi ⇒ mọi thông số pháp lý phải là cấu hình có ngày hiệu lực, không viết cứng.
- **CPT-Q7-2/Q2 (tuyến):** tuyến CÓ ảnh hưởng mức hưởng nội trú (Luật 51/2024/QH15 Điều 22 khoản 4, hiệu lực 01/7/2025) nhưng hệ số cụ thể (40%) và cấp của bệnh viện CHƯA xác minh ⇒ chưa làm `InpatientWrongRouteFactor`.
- **Q6/Q4/Q5/Q7/Q8:** chặn nhập viện khi thẻ không hợp lệ, thẻ tạm TE1, lịch sử thẻ theo đợt + ca tính lại, tính lại khoản đã ghi, trần VTYT/ngưỡng 15% lương cơ sở: CHƯA làm (cần quyết định/thiết kế/xác minh — xem tài liệu xác minh mục 3).

---
## Bổ sung 11/11 tối (2) — quy chế hồi tố CHỐT bởi chủ dự án
- **CPT-Q7-9 / Q5 (thẻ BHYT trình muộn):** chủ dự án chốt: **tính lại BHYT từ lúc nhập viện cho mọi ca nội trú** (không chỉ cấp cứu) khi thẻ trình trước lúc ra viện và hiệu lực từ ngày vào viện. Chưa có thiết kế/DDL: cần ca gắn/đổi thẻ cho đợt đang điều trị, bảng lịch sử thẻ theo đợt, ca `RecalculateAdmissionCharges` (khoản chưa thu cập nhật tại chỗ; khoản đã thu/đã quyết toán hoàn chênh lệch qua E7, đang bị chặn). Đợt riêng, sau khi duyệt DDL.
- E3e đã vào `main` (ân hạn thẻ cấu hình, dự phòng chỉ khi không gắn thẻ). Review E3e ghi nhận: TRUNG-1 nhãn `0m` ở ước tính xếp vào "đồng chi trả" (không đổi tổng); TRUNG-2 thẻ gia hạn nhưng đợt chưa đổi thẻ ⇒ 0% từ ngày thứ 17 — sẽ được giải bằng CPT-Q7-9.
