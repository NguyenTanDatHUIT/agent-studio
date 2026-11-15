# Phân tích PB1.3 — ca `RecalculateAdmissionCharges` (tính lại khoản theo thẻ BHYT của đợt nội trú)

Lập 12/11/2026 bởi PM (Agent 0). Dành cho agent khác đọc để hiểu ca này mà KHÔNG cần mở mã. Mọi số liệu dưới đây lấy từ thiết kế (`THIETKE-PB1.md` mục 4.2, 4.3, 5), review độc lập (`REVIEW-PB13.md`) và hai báo cáo của agent (`BAOCAO-WT-PB13.md`, `BAOCAO-WT-PB13-FIX1.md`) trong `C:\AgentControl\studio-state\prompts\`. Trạng thái: đã vào `main` (merge `82623ce9`), chưa chạy trên PostgreSQL thật, chưa có review độc lập riêng cho bản sửa lần 1.

## 1. Bài toán nghiệp vụ

Người bệnh nhập viện nội trú có thể:
- vào viện KHÔNG có thẻ BHYT, vài ngày sau mới trình thẻ (trình thẻ muộn);
- đổi thẻ hoặc gia hạn thẻ giữa đợt.

Mỗi khoản phí (`encounter_charges`: thuốc, vật tư, dịch vụ, giường...) được ghi lúc phát sinh, theo thẻ có hiệu lực LÚC ĐÓ. Khi thẻ thay đổi (đã ghi vào lịch sử thẻ của đợt bằng ca `AttachAdmissionInsuranceCard`), các khoản cũ có thể sai: phần BHYT chi trả và phần người bệnh phải trả cần tính lại. Ca `RecalculateAdmissionCharges` làm việc tính lại đó, an toàn và lặp lại được.

Ca gắn thẻ (Attach) và ca tính lại là HAI ca riêng (quyết định của chủ dự án): gắn thẻ không tự tính lại tiền; người có quyền chủ động chạy tính lại.

## 2. Dữ liệu liên quan (mức khái niệm)

- **Lịch sử thẻ của đợt** (`admission_insurance_cards`): mỗi dòng = một thẻ áp dụng cho đợt trong khoảng `[applied_from, applied_to)`; `applied_to` rỗng = thẻ hiện hành. Dòng đầu của đợt hồi tố từ lúc nhập viện (`retro_from`). Có tuyến khám (đúng tuyến/trái tuyến) kèm theo dòng.
- **Khoản phí** (`encounter_charges`): giá gốc `T` (`OriginalPrice`), phần BHYT chi trả `B` (`InsuranceAmount`), phần người bệnh trả `FinalPrice = T − B`, trạng thái thanh toán (`PaymentStatus`: 0 chưa thu, 1 đã thu, 3 chờ BHYT, còn lại theo quy ước), đối tượng thanh toán (`PayerType`: 1 BHYT, 2 tự trả, 3 dịch vụ, 4 bảo hiểm tư nhân), thẻ đã áp (`applied_card_id`), và hai cột tách phạm vi BHYT: `K` (`bhyt_scope_amount`) và `Đ` (`copay_amount`).
- **Sổ tính lại** (`admission_charge_recalc_items`): sổ CHỈ-THÊM, mỗi khoản mỗi lượt một dòng, ghi giá trị cũ, mới và kết quả (`outcome`).

## 3. Công thức

Gọi: `T` = giá gốc khoản (làm tròn đồng); `G` = giá BHYT của mặt hàng/dịch vụ tại mốc thực hiện; `c` = hệ số danh mục (phần danh mục BHYT chấp nhận, 0..1); `b` = mức hưởng của thẻ (0..1).

- Cơ sở tính: `basis = min(G, T)` khi `G > 0`, ngược lại `basis = T`.
- `K` (phạm vi BHYT) = làm tròn đồng(`basis × c`), không vượt `T`.
- `B` (BHYT chi trả) = làm tròn đồng(`basis × c × b`), không vượt `K`.
- `Đ` (đồng chi trả) = `K − B`.
- `X` (ngoài phạm vi, người bệnh tự trả) = `T − K`.
- Bất biến: `B + Đ + X = T`. Người bệnh trả `FinalPrice = T − B`.
- Làm tròn: về đồng, ra xa số 0. Mọi số tiền là số nguyên đồng.
- Tách bạch `b = 0` (thẻ không hưởng) với `b` chưa xác định (không đoán): chưa xác định thì không ghi BHYT chi trả.

Hàm chuẩn dùng chung tên `BhytChargeFormula.Compute` (tài liệu: `NhiDong/Docs/business/CONG-THUC-BHYT-NOI-TRU.md`, mục CT-C và CT-E). Ca này giữ NGUYÊN số tiền khoản (`B`, `FinalPrice`, trạng thái) như công thức CT-C đang dùng ở `RecordCharge`, và thêm việc ghi `K`, `Đ` theo CT-E.

## 4. Luồng xử lý của ca

**Đầu vào:** `AdmissionId` (đợt), `RunKey` (Guid định danh lượt chạy), `Reason` (lý do). **Quyền:** `noi_tru.the_bhyt_dot` mức cập nhật (cùng quyền gắn thẻ).

1. Kiểm quyền, kiểm đợt hợp lệ, kiểm cổng chặn đợt đã duyệt/tất toán (`APPROVED`/`SETTLED`, qua `AdmissionSettlementLockGuard` chỉ-đọc).
2. **Khóa dòng theo đúng thứ tự khóa chung của hệ thống:** `patients` → `health_insurance_cards` (id tăng dần) → `encounters` → `inpatient_admissions` → `encounter_charges` (sắp theo id tăng dần). Sau khi khóa, đọc lại tập id thẻ và tập id khoản, so với tập đọc TRƯỚC khóa; khác nhau thì từ chối (tránh khoản mới chen vào giữa).
3. **Idempotent theo `RunKey`:** nếu `RunKey` đã có dòng sổ thì trả lại kết quả của lượt cũ (không tính lại). `RunKey` đã dùng cho đợt khác thì từ chối. Hai lượt đua cùng `RunKey` thì ràng buộc duy nhất `(run_key, charge_id)` của sổ chặn lượt sau, rồi đọc lại kết quả.
4. **Phạm vi khoản:** mọi khoản của đợt, trạng thái `>= 0`, có mốc thực hiện (`PerformedAt`, thiếu thì `CreatedDate`) từ `retro_from` của dòng thẻ vừa gắn trở đi (hồi tố từ nhập viện thì là cả đợt).
5. **Từ chối cả lô nếu có khoản nằm trong lần thanh toán chờ xử lý** (có phân bổ thanh toán đang hoạt động): liệt kê tối đa 10 mã khoản, yêu cầu hoàn tất hoặc huỷ lần thanh toán đó rồi thử lại. Kiểm TRƯỚC mọi thay đổi, không sửa gì cả.
6. **Với từng khoản, xác định thẻ đúng:** dùng dòng lịch sử thẻ PHỦ mốc thực hiện của khoản. Khoản có mốc trước dòng đầu thì dùng dòng đầu. Mốc nằm sau mọi `applied_to` (ghi muộn sau khi đóng đợt) thì dùng dòng cuối. Khe hở giữa hai dòng thì dùng dòng hiện hành.
7. **Phân loại và xử lý:**

| Loại khoản | Điều kiện | Xử lý |
|---|---|---|
| Đã thu | `PaymentStatus = 1` và (có mã lần thanh toán hoặc `FinalPrice > 0`) | KHÔNG sửa `InsuranceAmount`, `FinalPrice`, `PayerType`. Ghi sổ `PAID_DIFF_PENDING`. Nếu số mới làm người bệnh được hoàn: `refund_due = max(0, FinalPrice cũ − FinalPrice mới)`. Nếu người bệnh phải trả THÊM thì `refund_due = 0`, chênh lệch nằm ở giá trị mới trong sổ, KHÔNG tự thu thêm (quyết định Q4) và KHÔNG tự hoàn (thuộc đợt E7). |
| Chưa thu | `PaymentStatus = 0` | Cập nhật tại chỗ: `PayerType`, `InsuranceAmount`, `FinalPrice`, `applied_card_id`, `K`, `Đ`, `PaymentStatus` (theo quy tắc: còn phải thu thì 0; `FinalPrice = 0` và `B > 0` thì 3 chờ BHYT; còn lại thì 1 kèm giờ/người thu). Ghi sổ `UPDATED`. |
| Chờ BHYT | `PaymentStatus = 3` | Xử lý như chưa thu (không bao giờ coi là "đã thu" để chặn). Nếu `B` mới = 0 thì `FinalPrice > 0` và trạng thái quay về chưa thu. |
| Không tra được giá BHYT | thuốc/vật tư không tra được giá, hoặc giá tìm thấy không phải loại BHYT, hoặc mức hưởng chưa xác định | Giữ nguyên khoản, ghi sổ `SKIPPED_NO_PRICE`. Không đoán giá. |
| Đã đúng sẵn | số mới bằng số cũ (cả `K`, `Đ`, thẻ đã áp) | Ghi sổ `SKIPPED_UNCHANGED`, không ghi lại khoản. |
| Khoản không thuộc BHYT | `PayerType` là dịch vụ (3) hoặc bảo hiểm tư nhân (4) | Không đổi. |

   Đối tượng thanh toán: khoản tự trả (2) phát sinh trong khoảng người bệnh chưa có thẻ được đổi sang BHYT (1) CHỈ khi giá BHYT xác định được. Thuốc/vật tư đã phát vẫn được tính lại TIỀN (không đổi số lượng, lô, tồn kho).
8. Mỗi khoản một dòng sổ chỉ-thêm (đủ giá trị cũ, mới) cộng một bản ghi nhật ký nghiệp vụ tóm tắt số khoản theo từng kết quả. Từ chối sau khi giao dịch quay lui thì ghi nhật ký từ chối ngoài giao dịch.

## 5. Ví dụ số (kịch bản thiết kế, tính tay)

Đợt nhập 01/11 không thẻ; ngày 05/11 trình thẻ hưởng 80%, đúng tuyến, hồi tố từ 01/11. Có ba khoản:

| Khoản | Hiện trạng | Kết quả sau tính lại |
|---|---|---|
| K1: `T = 100.000`, `G = 100.000`, `c = 100%`, chưa thu | `PayerType = 2`, `B = 0`, `FinalPrice = 100.000` | `B = 80.000`, `FinalPrice = 20.000`, `K = 100.000`, `Đ = 20.000`, `X = 0`; `PayerType` thành 1; trạng thái vẫn chưa thu. Ghi sổ `UPDATED`. |
| K2: `T = 200.000`, đã thu 200.000 | `B = 0` | Không sửa khoản. Ghi sổ `PAID_DIFF_PENDING`: `B` mới 160.000, `FinalPrice` mới 40.000, `refund_due = 200.000 − 40.000 = 160.000` (chỉ ghi nhận, chưa hoàn). |
| K3: `T = 50.000`, nằm trong một lần thanh toán chờ | — | CẢ LÔ bị từ chối, không khoản nào bị sửa, không dòng sổ nào được ghi. |

Ví dụ làm tròn: `T = 33.333`, `b = 80%`, `c = 100%`, `G` bằng `T`: `B = làm tròn đồng(33.333 × 0,8) = 26.666`; `FinalPrice = 6.667`.
Ví dụ có hệ số danh mục: `T = 100.000`, `G = 100.000`, `c = 90%`, `b = 80%`: `K = 90.000`, `B = 72.000`, `Đ = 18.000`, `X = 10.000` (cộng lại 100.000).

## 6. Các quy tắc đã chốt (đừng hỏi lại)

- Hai ca Attach và Recalculate tách riêng. Quyền tính lại = người có quyền cập nhật thẻ BHYT theo đợt.
- Khoản đã thu chỉ ghi sổ chênh lệch; KHÔNG tự thu thêm, KHÔNG tự hoàn.
- Khoản trong lần thanh toán chờ thì từ chối cả lô.
- Tuyến rỗng của dữ liệu cũ khi chuyển đổi: coi là đúng tuyến (giá trị TẠM, chưa chốt).
- Phần mềm đang ở giai đoạn DEMO: mọi con số pháp lý là tham số hoặc chưa bật.

## 7. Kết quả review độc lập và xử lý

Kết luận của reviewer: ĐƯỢC MERGE, không có lỗi mức CAO. Các mục kiểm đạt: thứ tự khóa, phân loại khoản, tính số (tính tay theo kịch bản trên), idempotent, quyền và đăng ký, không có mã cấm (giờ máy, lấy thông điệp lỗi gốc, xóa cứng, số pháp lý), ràng buộc `scope_pair`, hàm tra giá chỉ đổi mức truy cập.

Bốn phát hiện mức trung bình và trạng thái hiện nay:

| # | Phát hiện | Trạng thái |
|---|---|---|
| 1 | Mốc tính dùng `PerformedAt ?? giờ nhập viện`, lệch với phạm vi chọn khoản (`PerformedAt ?? CreatedDate`): khoản không có `PerformedAt` bị tính theo thẻ đầu. | ĐÃ SỬA ở bản sửa lần 1 (dùng `PerformedAt ?? CreatedDate`). |
| 2 | Khoản sửa tại chỗ bị đặt `K`, `Đ` về null, làm mất tách CT-E của các khoản mới ghi sau PB3-3. | ĐÃ SỬA: tính `K`, `Đ` bằng hàm chuẩn, số tiền `B`/`FinalPrice` vẫn theo CT-C; nhánh "đã đúng sẵn" so thêm `K`, `Đ`. |
| 3 | Sổ ghi thẻ là dòng HIỆN HÀNH kể cả khoản thuộc dòng cũ, nên bộ đếm "cần tính lại" của PB1.4 đếm mãi khoản thuộc dòng cũ. | ĐÃ SỬA: ghi đúng dòng phủ mốc của từng khoản. Còn một trường hợp riêng, xem mục 8. |
| 4 | Luồng tạo lần thanh toán không khóa dòng khoản, nên tính lại có thể đua với nó (tính lại đọc "chưa có phân bổ", lần thanh toán tạo xong, rồi tính lại sửa `FinalPrice` thấp hơn số đã tạo thanh toán). | CHƯA SỬA: đang là nợ kỹ thuật `debt2` (khóa dòng ở luồng hủy/thu khoản), thiết kế chưa xong. |

Mức thấp chưa sửa: (a) không giới hạn số khoản mỗi lượt, đợt 2.000 khoản sẽ khóa 2.000 dòng trong một giao dịch và truy vấn giá nhiều lần (cần chủ dự án chốt số tối đa, đề xuất 500); (b) khoản có mốc TRƯỚC giờ nhập viện vẫn mang đối tượng cũ trong khi tra mức hưởng lại dùng dòng thẻ đầu.

## 8. Điểm còn mở

- **Bộ đếm "cần tính lại" (PB1.4) so với phạm vi của ca tính lại:** bộ đếm đếm một khoản nếu có dòng thẻ phủ mốc mà `applied_card_id` của khoản khác thẻ của dòng đó và chưa có dòng sổ cho cặp (khoản, dòng). Ca Attach chỉ đếm khoản thuộc phạm vi hồi tố của dòng mới. Hệ quả: đợt đã gắn thẻ L1 rồi gia hạn L2 mà chưa từng chạy tính lại cho L1 thì khoản thuộc L1 bị đếm "cần tính lại" mãi.
  - **ĐÍNH CHÍNH 12/11/2026 (sau khi đối chiếu `ph_n_t_ch_nghi_p_v_..._pb1_3.md` và mã):** nhận định "chỉ lệch hiển thị, không lệch tiền" là SAI. Mỗi dòng thẻ gắn sau dòng đầu có `RetroFrom = appliedFrom` (`AttachAdmissionInsuranceCardCommand.cs:273`), và `RecalculateChargesQuery` chỉ quét khoản từ `RetroFrom` của dòng HIỆN HÀNH. Khi nhân viên gắn L1 rồi L2 và chỉ bấm tính lại một lần, khoản giai đoạn L1 KHÔNG BAO GIỜ được tính lại: tiền sai thật (vẫn tự trả).
  - Bộ đếm cũ (PB1.4) đếm đúng những khoản đó nên là tín hiệu ĐÚNG. Bản `PB1.4-fix1` (merge `9e5b8449`) thu hẹp bộ đếm cho khớp phạm vi ca tính lại ⇒ báo 0 và CHE lỗi thật. Hướng xử lý đúng: GIỮ bộ đếm cũ (hoàn tác `PB1.4-fix1`) và MỞ RỘNG phạm vi ca tính lại ra toàn đợt (khoản đã khớp rơi vào `SKIPPED_UNCHANGED`, an toàn). Trạng thái: chờ giao đợt `PB1.3-fix2`.
- **Chưa kiểm chứng thực tế:** toàn bộ phân tích dựa trên đọc mã và tính tay. Chưa có ca nào của PB1.3 chạy trên PostgreSQL thật; nhóm ca kiểm thử đợt P-A1.2b nên bao gồm: nhập không thẻ rồi trình thẻ muộn, khoản đã thu, khoản trong lần thanh toán chờ, chạy lặp cùng `RunKey`, hai lượt đua nhau.
- **Khi công thức đổi lần nữa:** nơi dùng công thức trong ca này đã ghi chú `#CT-C` và `#CT-E`; mọi thay đổi công thức phải cập nhật bảng "nơi dùng công thức" ở mục 7 của `CONG-THUC-BHYT-NOI-TRU.md`.

## 9. Việc liên quan ở các đợt khác

- **PB1.2 / PB1.2b:** ca gắn thẻ và việc `CompleteAdmission` tự ghi dòng lịch sử đầu cùng lúc tiếp nhận.
- **PB1.4:** truy vấn lịch sử thẻ và trạng thái "cần tính lại" trong chi tiết đợt.
- **PB3-3, PB3-4, PB3-5:** nối `RecordCharge`, ước tính y lệnh, `CreateOrderCharges` vào hàm công thức chuẩn. PB3-6 (`ResolveSettlementLine`) chưa làm và sẽ xử lý việc ca đó đổi tiền khoản mà không đặt lại `K`, `Đ`.
- **debt2:** khóa dòng khoản ở luồng hủy và thu để đóng điểm 4 ở mục 7.
