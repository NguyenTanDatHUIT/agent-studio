# TỔNG HỢP VẤN ĐỀ CẦN PHÂN TÍCH — TẦNG SERVICE HIS_EMR (tài liệu TỰ ĐỦ NGỮ CẢNH)

Ngày lập: 11/11/2026 (đêm). Người đọc dự kiến: một agent/chuyên gia phân tích KHÁC, KHÔNG xem mã nguồn. Mọi khẳng định về mã đã được người điều phối (PM) đối chiếu với mã thật tại `main@f8af97e7` hoặc ghi rõ "đang chạy/chưa vào main". Mọi khẳng định pháp lý ghi rõ mức xác minh. Mục đích: phân tích, đề xuất thiết kế/quyết định, KHÔNG viết mã.

## 0. Cách dùng tài liệu và quy tắc cho người phân tích
- Đầu ra mong muốn cho mỗi vấn đề: một tệp markdown ngắn gồm (1) hiểu biết của bạn về bài toán, (2) các phương án có ưu/nhược, (3) khuyến nghị MỘT phương án kèm lý do, (4) câu hỏi còn thiếu cho chủ dự án/bộ phận nghiệp vụ, (5) rủi ro, (6) mức tin cậy từng khẳng định.
- KHÔNG sửa mã, KHÔNG chạy truy vấn ghi, KHÔNG đụng container Docker của dự án khác. Truy vấn DB thật chỉ khi được cấp quyền và chỉ `SELECT`, kết quả tổng hợp, không đưa dữ liệu định danh người bệnh vào báo cáo.
- KHÔNG kết luận pháp lý từ trí nhớ: cần trích dẫn văn bản (số hiệu, điều, khoản, ngày hiệu lực) hoặc xác nhận bằng văn bản của người có thẩm quyền; nếu chỉ có nguồn thứ cấp thì ghi "nguồn thứ cấp". Quy định BHYT đổi theo thời gian (xem mục 2.3).
- KHÔNG tự điền số liệu pháp lý/lâm sàng (tỷ lệ, số ngày, mốc) như thể đã chốt; mọi số phải là THAM SỐ CẤU HÌNH, có ngày hiệu lực, và ghi rõ nguồn.

## 1. Bối cảnh dự án (đủ để hiểu mà không cần mã)
- **Hệ thống:** HIS_EMR (hệ thống thông tin bệnh viện + bệnh án điện tử) cho bệnh viện nhi (phần nhánh `NhiDong`), .NET 8, PostgreSQL. Đang làm TẦNG SERVICE (nghiệp vụ). Controller/View CHƯA làm theo chỉ đạo; kiểm thử hành vi (test mới) bị hoãn đến sau Controller/View. Chỉ chạy hai lớp test quy ước kiến trúc và build.
- **Tiến độ:** Tầng Service ước tính ~95% (đếm theo ca ghi + hàm đọc). Phần còn lại xem mục 3-7 và 8.
- **Các module (dịch vụ) và hướng phụ thuộc một chiều:** Core (nền, dùng chung: truy vấn người bệnh, khóa dòng, nhật ký, tham số) ← Billing (thu tiền, khoản thu, thanh toán) ← Pharmacy ← Inpatient (nội trú: tiếp nhận, giường, y lệnh, hồ sơ, ra viện) ← Nursing (điều dưỡng) / Emergency (cấp cứu) / InpatientPharmacy (dược nội trú); Emr (bệnh án điện tử, chỉ phụ thuộc Core). Billing KHÔNG được gọi ngược lên Inpatient. Bảng quy tắc phụ thuộc được kiểm bằng test kiến trúc.
- **Quy ước ca ghi (write use case):** mỗi ca ghi chạy trong MỘT giao dịch (`InTransaction`), khóa dòng theo thứ tự cố định các bảng (đợt nội trú → … → việc điều dưỡng → y lệnh → dòng phát thuốc → lô kho → khoản thu …) để tránh deadlock; hàm công khai của service trả `CommandResult<T>` (thành công/thất bại + thông báo tiếng Việt); lỗi ràng buộc DB (ví dụ `23505` trùng khóa, `23514` CHECK) được ánh xạ sang thông báo qua bảng tên ràng buộc; nhật ký nghiệp vụ (`LogBusinessEvent`) ghi NGAY cùng kết nối/giao dịch; gọi chéo giữa các service dùng chung một giao dịch qua cơ chế "chạy chung giao dịch" (hai service phải dùng chung một DbContext). Ca không được tự nhiên làm hỏng ca gốc khi cấu hình/dữ liệu danh mục chưa có (ví dụ chưa có danh mục hồ sơ ⇒ bỏ qua hook, không thất bại).
- **Tham số nghiệp vụ nội trú** lưu ở bảng cấu hình (`app_settings`, tab `Inpatient`), đọc qua một lớp tham số kiểu mạnh có giá trị mặc định và một danh sách "chưa phải giá trị chốt" — nguyên tắc: không viết cứng số pháp lý/lâm sàng.
- **DDL** (cấu trúc bảng) sinh tự động từ định nghĩa Python, không sửa tay; đã từng kiểm cài trên PostgreSQL 16 thật (Docker, container riêng `his-ddl-test-*`, 174 tệp 0 lỗi, 14 thử hành vi DDL) — KHÔNG phải kiểm thử hành vi của mã nghiệp vụ.
- **Quy trình làm việc:** PM điều phối agent lập trình; mọi việc chạm tiền hoặc ca cốt lõi bắt buộc có review độc lập chỉ-đọc rồi PM tự xác minh mục CAO; chỉ agent lập trình viết mã. (Từ 11/11 đêm: agent lập trình chỉ dùng agy; không còn Claude Sonnet/Opus.)

## 2. Mô hình dữ liệu và công thức tiền hiện hành (tối thiểu cần biết)
### 2.1. Khoản thu (`encounter_charges`) — "sổ chi phí thực tế"
Cột chính: lượt khám (`encounter_id`), người bệnh, đợt nội trú (`admission_id`, rỗng với ngoại trú), loại khoản (`charge_type`: 1 Khám, 2 Xét nghiệm, 3 CĐHA, 4 Thuốc, 5 Thủ thuật, 6 Vật tư), mã tham chiếu chứng từ gốc dạng chuỗi ≤ 64 ký tự (`ref_id`), mã dịch vụ/thuốc, tên, `original_price` (giá gốc), `insurance_amount` (BHYT trả), `final_price` (người bệnh phải trả), trạng thái thanh toán (chưa thu / đã thu hoặc miễn phí / **3 = chờ BHYT**: BHYT trả hết, người bệnh 0 đồng), đối tượng thanh toán chụp lúc ghi (`payer_type`: 1 BHYT, 2 Viện phí, 3 Dịch vụ, 4 Bảo hiểm tư nhân), `quantity` (>0), `unit_price` (≥0), nguồn giá (`price_source`: DRUG_PRICE, SERVICE_PRICE, BED_DAY, MANUAL), tham chiếu phiên bản giá, mốc thực hiện, `status` (≥0 còn hiệu lực, −1 đã hủy mềm).
**Chỉ mục duy nhất** `(charge_type, ref_id)` khi `status >= 0 AND ref_id IS NOT NULL`: mỗi chứng từ gốc đúng một khoản (idempotent).
Quy ước `ref_id` theo loại: thuốc nội trú = id dòng phát thuốc; thủ thuật/oxy = id việc điều dưỡng; vật tư = id lần dùng vật tư; xét nghiệm/CĐHA ngoại trú = id đơn chi tiết; thuốc ngoại trú = id đơn thuốc.

### 2.2. Hàm ghi khoản `RecordCharge` (cổng ghi khoản đơn lẻ) và công thức
- Idempotent theo `(loại, mã tham chiếu)`; từ chối khi người bệnh/đợt/lượt khám không khớp nhau; giới hạn cột (số lượng làm tròn 4 chữ số lẻ, đơn giá 2 chữ số lẻ, mã ≤ 64 ký tự).
- **Công thức:** `giá = làm tròn đồng(OriginalPrice)`; `cơ sở BHYT = min(InsurancePrice nếu > 0 ngược lại giá, giá)`; `tỷ lệ hiệu dụng = mức hưởng(%) × tỷ lệ thanh toán danh mục của dòng`; `BHYT trả = làm tròn đồng(cơ sở × tỷ lệ hiệu dụng / 100)`; `người bệnh trả = giá − BHYT`. Khoản không phải BHYT (`payer_type` ≠ 1) ⇒ mức hưởng 0.
- `payer_type` chụp theo mốc thực hiện: nếu sau mốc đó đợt từng đổi đối tượng thì lấy đối tượng CŨ của lần đổi đầu tiên sau mốc.
- **Mức hưởng nội trú BHYT** lấy từ một bộ đọc dùng chung với ước tính (xem 2.4). Ngoại trú vẫn lấy từ lượt khám (`encounters.benefit_rate` khi đối tượng = BHYT và đúng tuyến).

### 2.3. BHYT: dữ liệu và bộ đọc mức hưởng nội trú (hiện trạng ở `main`)
- **Thẻ BHYT** (`health_insurance_cards`): ngày hiệu lực từ/đến, mức hưởng (80/95/100), mã đối tượng, trạng thái (ý nghĩa giá trị 0 chưa rõ). **Đợt nội trú** (`inpatient_admissions`) lưu MỘT mã thẻ, `payer_type`, tuyến BHYT (`bhyt_route`: 1 Cấp cứu, 2 Đúng tuyến, 3 Trái tuyến, 4 Có giấy chuyển tuyến), giờ vào/ra viện, mã lượt khám, mã lượt khám nguồn. **Lượt khám** (`encounters`) có đối tượng thanh toán, cờ đúng tuyến, mức hưởng — khi nhập viện nội trú, hệ thống tạo lượt khám MỚI với cờ đúng tuyến = sai và mức hưởng = 0 (nên mức hưởng thực sự phải lấy từ thẻ). Đổi đối tượng giữa đợt chỉ ghi `admission_payer_changes` (cũ→mới, hiệu lực từ) và đổi `payer_type` của đợt, KHÔNG đổi thẻ.
- **Bộ đọc mức hưởng nội trú** (dùng chung ước tính và khoản thật), trả `0..1` hoặc "chưa xác định":
  1. Đợt CÓ gắn thẻ: thẻ không tìm thấy/trạng thái ≤ 0/thiếu ngày hiệu lực ⇒ chưa xác định. Thẻ hiệu lực tại ngày thực hiện `d` khi từ-ngày ≤ `d` VÀ (`d` ≤ hết-hạn HOẶC (ngày nhập viện ≤ hết-hạn VÀ `d` ≤ hết-hạn + ân hạn)). Ân hạn = tham số cấu hình `InpatientCardExpiryGraceDays` (mặc định 15, chưa chốt). Hiệu lực ⇒ mức hưởng của thẻ; không hiệu lực ⇒ 0 (có thẻ nhưng không hưởng, đã xác định).
  2. Đợt KHÔNG gắn thẻ: dự phòng mức hưởng của lượt khám nếu > 0, ngược lại chưa xác định.
  3. (Đang làm, chưa vào `main` — đợt E3f) nhân thêm hệ số cấu hình `InpatientWrongRouteBenefitPercent` (mặc định 100 = không giảm) khi tuyến = Trái tuyến (3).
- Ý nghĩa kết quả: "0" ⇒ ước tính/khoản thật không có BHYT, không báo thiếu thông tin; "chưa xác định" ⇒ ước tính đánh dấu "chưa xác định mức hưởng" và tính hết cho người bệnh; khoản thật giữ cách tính theo lượt khám như trước.
- **Công thức ước tính** (bảng kê tạm tính khi bác sĩ ra y lệnh): `tổng × tỷ lệ thanh toán danh mục × mức hưởng` là phần BHYT; phần danh mục không được thanh toán là "tự chi trả"; phần còn lại sau BHYT là "đồng chi trả". Hai công thức (ước tính và khoản thật) cùng hình dạng nhưng khác chi tiết làm tròn và nguồn trần (xem P-B3).

### 2.4. Ước tính chi phí (`order_charge_estimates`) và bảng kê (`FeeBoard`)
- Mỗi y lệnh có bản ước tính mới nhất: số lượng dự kiến (số lần/mốc), đơn giá, nguồn giá, tham chiếu phiên bản giá, thành tiền, phần BHYT, phần người bệnh. Đây là SỐ DỰ KIẾN, không phải tiền thật.
- **Bảng kê chi phí tab Viện phí:** hiển thị khoản thật + "ước tính còn lại" của các y lệnh đang hiệu lực (ACTIVE/PAUSED). Quy tắc nối (đã làm): khoản thuốc nối y lệnh qua dòng phát thuốc (`ref_id` = id dòng phát → y lệnh), khoản thủ thuật/oxy nối qua việc điều dưỡng (`ref_id` = id việc → y lệnh nguồn); phần còn lại = ước tính − khoản thật đã nối (từng trường, kẹp ≥ 0; đang vá để BHYT + người bệnh = tổng). Tiền ngày giường KHÔNG hiện (tham số chưa chốt).

### 2.5. Bảng giá
- Thuốc: `drug_price_items` (mã thuốc, loại giá ≈ đối tượng 1..4, đơn giá, hiệu lực từ/đến) + tỷ lệ thanh toán BHYT theo danh mục thuốc. Dịch vụ kỹ thuật: `service_price_items` (tương tự). Ngày giường: bảng `price_items` riêng (loại dịch vụ ngày giường) — NGUỒN GIÁ KHÁC. Tra giá ưu tiên đúng loại giá của đối tượng, rồi lùi về Viện phí, rồi lấy bất kỳ. Chủ dự án chốt: giá thuốc tính theo ĐƠN VỊ CƠ SỞ (viên/ống/lọ/chai/túi) khớp số lượng cấp phát; một nguồn giá duy nhất cho ước tính và khoản thật; đối soát đơn vị trên DB thật do khoa dược làm (CHƯA xong).

### 2.6. Ra viện và quyết toán (nhóm "ra viện – đối soát")
- Có 7 bảng mới (đã sinh DDL và thực thể): quyết toán đợt (`discharge_settlements`, trạng thái PREPARING → DEPT_CLOSED → APPROVED → CLOSED), bảng kê chốt (`discharge_statements`: snapshot + băm + phiên bản), dòng kiểm cổng chặn trước ra viện (`discharge_gate_checks`: mã kiểm tự do, chưa có nguồn), v.v.
- ĐÃ làm: quyết định ra viện và rút quyết định; đọc quyết toán (nhiều/một); đóng quyết toán theo khoa; mở khóa DEPT_CLOSED → PREPARING; hàm đọc: bảng chi phí, tóm tắt tạm ứng, cảnh báo tạm ứng.
- CHƯA làm: xử lý từng dòng bảng kê (giữ nguyên / điều chỉnh số lượng / hủy khoản / chuyển sang dịch vụ BHYT tương đương / chờ xác nhận); duyệt bảng kê (khóa chi phí, tăng phiên bản, ghi snapshot + băm, sự kiện APPROVED, mở khóa từ APPROVED); đóng đợt `CLOSED`, thu tiền, hóa đơn điện tử, XML 130 gửi BHXH (D11-3, BỊ CHẶN).

## 3. Trạng thái các đợt vừa làm (để biết đâu là "đã có", đâu là "đang làm")
Đã vào `main`: E3b (RecordCharge ghi đủ 7 cột + chống ghi trùng), E3c (khoản ngoại trú xét nghiệm/CĐHA/thuốc ghi đủ cột, loại trùng, chống đua; nhật ký RecordCharge), E3d (bộ đọc mức hưởng nội trú dùng chung), E3e (ân hạn thẻ cấu hình), E5b (hook phiếu chuyển khoa khi chuyển giường KHÁC khoa; hook từ chối dịch vụ khi điều dưỡng ghi "người bệnh từ chối"), E6b đợt 1 (bảng kê nối khoản thật), cổng tra giá công khai, FIX-EMR, FIX-TPL.
ĐANG CHẠY (chưa vào `main`): E6b đợt 2 (ghi khoản khi PHÁT thuốc, chặn phát khi thiếu giá, hủy khoản khi trả hết), E6b đợt 3 (ghi khoản khi hoàn tất việc thủ thuật/oxy; nối tự chốt y lệnh), E3f (hệ số trái tuyến).

## 4. Quyết định ĐÃ CHỐT (đừng hỏi lại)
Thu theo PHÁT thuốc (không theo đã dùng); thuốc nội trú dùng chung loại khoản 4 (phân biệt nội trú bằng mã đợt); thủ thuật làm dở KHÔNG thu; trả thuốc: trả hết + khoản chưa thu ⇒ hủy khoản, còn lại (một phần/đã thu) ⇒ chỉ cảnh báo chờ hoàn tiền (E7); công thức BHYT khoản thật giữ như hiện có (tạm) kèm đánh dấu vấn đề; thiếu giá: phát thuốc thì CHẶN, việc điều dưỡng thì KHÔNG chặn (bỏ qua khoản + nhật ký) — về sau mới có trạng thái chờ định giá; khoản thật nội trú dùng cùng bộ đọc mức hưởng với ước tính; tự chốt y lệnh chỉ cho y lệnh có tổng số lượt xác định, loại trừ y lệnh "khi cần"; phiếu chuyển khoa là dòng "phiếu cần lập" không chặn chuyển giường; **trình thẻ BHYT muộn ⇒ tính lại BHYT từ lúc nhập viện cho MỌI ca nội trú**; hệ số trái tuyến đưa vào cấu hình, mặc định 100.

## 5. DANH SÁCH VẤN ĐỀ CẦN PHÂN TÍCH
Mỗi vấn đề: (Bối cảnh/hiện trạng) → (câu hỏi cần phân tích) → (ràng buộc/đầu vào) → (đầu ra mong muốn). Ưu tiên: P1 cao nhất.

### Nhóm A — Rủi ro hệ thống
**P-A1 (P1). Chưa kiểm thử hành vi mã tiền trên PostgreSQL thật.**
Hiện trạng: toàn bộ chuỗi tiền (ghi khoản, chống đua, ân hạn thẻ, hủy khoản, tra giá, bảng kê) chỉ được kiểm bằng biên dịch + hai lớp test quy ước + đọc mã + review. Không có test hành vi. Bảng DDL đã kiểm cài nhưng chưa kiểm mã nghiệp vụ trên cơ sở dữ liệu thật.
Câu hỏi: thiết kế bộ kiểm thử tích hợp nhỏ nhất, chạy được trên container PostgreSQL riêng (đặt tên `his-ddl-test-*`, xóa sau khi dùng), bao phủ rủi ro tiền lớn nhất; khi nào dựng (trước hay sau Controller/View); dữ liệu mẫu tối thiểu.
Ca cần bao phủ tối thiểu: (1) ghi khoản idempotent và đua hai luồng cùng mã tham chiếu (phải ra một khoản, không lỗi 23505 ngoài giao dịch; trong giao dịch chung thì quay lui đúng); (2) mức hưởng nội trú theo thẻ: trong hạn, hết hạn 1/15/16 ngày, thẻ thiếu ngày, đợt không thẻ, trái tuyến với hệ số; (3) phát thuốc ghi khoản đúng số tiền, chặn khi thiếu giá, trả hết hủy khoản; (4) hoàn tất việc thủ thuật ghi khoản, không chặn khi thiếu giá; (5) bảng kê không cộng đúp; (6) giới hạn cột (CHECK) không bị vi phạm.
Đầu ra: kế hoạch + danh sách ca + ước lượng công sức; KHÔNG viết test.

**P-A2 (P2). Chất lượng review khi chỉ dùng agy.** Agy (Gemini 4 Carbon, mức trung bình) bỏ sót nhiều hơn Claude. Phân tích: biện pháp bù ít tốn kém nhất (kịch bản số bắt buộc trong prompt review, đối chiếu độc lập hai reviewer cho đợt tiền lớn, người thật đọc diff phần tiền).

### Nhóm B — BHYT nội trú
**P-B1 (P1). Hồi tố khi trình thẻ muộn (CPT-Q7-9, chính sách ĐÃ CHỐT: tính lại từ lúc nhập viện cho mọi ca nội trú).**
Hiện trạng: đợt chỉ lưu MỘT mã thẻ; không có ca đổi/gắn thẻ cho đợt đang điều trị; không có lịch sử thẻ theo đợt; đổi đối tượng chỉ đổi `payer_type`. Khoản đã ghi trước khi trình thẻ mang `payer_type` = Viện phí, `insurance_amount` = 0.
Câu hỏi: (a) thiết kế dữ liệu (bảng lịch sử thẻ theo đợt: mã thẻ, tuyến, hiệu lực từ/đến, ai gắn, mốc áp dụng) và cách bộ đọc mức hưởng tra thẻ theo ngày thực hiện; (b) ca "gắn/đổi thẻ" và ca "tính lại khoản thu" (khoản chưa thu: cập nhật tại chỗ cả `payer_type`, BHYT, người bệnh trả; khoản đã thu hoặc đã quyết toán: sinh chênh lệch hoàn trả qua E7; khoản đang nằm trong lần thanh toán chờ: xử lý thế nào); (c) khi một đợt dùng nhiều thẻ nối tiếp (gia hạn giữa đợt) XML 130 ghép nhiều mã thẻ ra sao (nguồn thứ cấp: cách nhau dấu `;`, CHƯA xác minh Quyết định 4750/QĐ-BYT); (d) tương tác với ân hạn 15 ngày (thẻ gia hạn là thẻ khác ⇒ hiện từ ngày thứ 17 sau hết hạn tính 0% BHYT); (e) quyền ai được gắn/đổi thẻ, nhật ký, idempotent; (f) khoản đã ghi trước khi sửa mã BHYT cũng cần tính lại (số lượng chưa biết — xem P-B6).
Đầu ra: thiết kế DDL đề xuất (để chủ dự án duyệt trước khi làm), danh sách ca ghi/hàm đọc, thứ tự khóa dòng, các trường hợp biên, ước lượng.

**P-B2 (P2). Ngoại lệ bệnh hiếm/hiểm nghèo lên thẳng 100% (CPT-Q7-10).** Nguồn thứ cấp: Thông tư 01/2025/TT-BYT có phụ lục danh mục bệnh/kỹ thuật được lên thẳng cấp chuyên sâu hưởng 100% dù trái tuyến. Chưa có danh mục trong hệ thống; đợt nội trú chưa có trường đánh dấu "thuộc diện lên thẳng". Phân tích: nguồn danh mục (mã ICD hay mã kỹ thuật), cách đánh dấu theo đợt (tự động theo chẩn đoán hay nhân viên giám định xác nhận), tương tác với hệ số trái tuyến cấu hình.

**P-B3 (P2). Thống nhất công thức BHYT giữa ước tính và khoản thật (CPT-Q7-3, 7, 8).**
Khác biệt đã biết: ước tính nhân tỷ lệ thanh toán danh mục (với thuốc lấy từ danh mục thuốc, với dịch vụ coi 100%) rồi mức hưởng, làm tròn hai chữ số ở bước trung gian; khoản thật nhân tỷ lệ do người gọi truyền (vật tư) hoặc 100%, làm tròn một lần về đồng; ước tính còn đòi giá khớp loại giá BHYT. Chưa có "trần thanh toán tiền tuyệt đối" theo danh mục (stent, khớp nhân tạo…) trong dữ liệu (chỉ thấy tỷ lệ). Thêm: ngưỡng "chi phí một lần dưới 15% lương cơ sở thì hưởng 100%" (nguồn thứ cấp: Nghị định 188/2025; lương cơ sở 2.530.000 đồng từ 01/7/2026 ⇒ ≈ 379.500 đồng), đồng chi trả khi đủ 5 năm liên tục.
Phân tích: công thức chuẩn một hàm dùng chung; nơi lưu trần tuyệt đối; xử lý ngưỡng toàn đợt khi duyệt bảng kê (P-C1); thông số phải có ngày hiệu lực.

**P-B4 (P2). Thẻ tạm cho trẻ dưới 6 tuổi và chặn nhập viện khi thẻ không hợp lệ.** Hiện bộ đọc nội trú không có nhánh tuổi (ngoại trú có: trẻ dưới 6 tuổi mặc định 100% khi chưa biết mức). Nguồn thứ cấp: trẻ dưới 6 tuổi hưởng BHYT bằng giấy chứng sinh khi chưa có thẻ; kết xuất XML cần mã thẻ tạm dạng `TE1…` (chưa xác minh). Tiếp nhận nội trú hiện chỉ kiểm thẻ "tồn tại, đúng người, trạng thái ≥ 0", không kiểm ngày/tuyến. Phân tích: có chặn nhập viện hay chỉ cảnh báo (cấp cứu phải là ngoại lệ; trẻ em đặc thù), thiết kế thẻ tạm, vai trò giấy chứng sinh.

**P-B5 (P1 — chờ người có thẩm quyền). Xác minh văn bản gốc.** (a) Ân hạn 15 ngày thẻ hết hạn khi nội trú: hai nguồn thứ cấp cùng trích khoản 9 Điều 27 Nghị định 146/2018/NĐ-CP ("đến khi ra viện, tối đa 15 ngày kể từ ngày thẻ hết hạn"); Nghị định 188/2025/NĐ-CP (hiệu lực 01/7/2025, đang được sửa đổi) có còn quy tắc này không — CHƯA xác nhận; tài liệu phân tích trích "Điều 50 NĐ 188/2025" nhưng không tìm thấy căn cứ. (b) Nội trú trái tuyến: Luật 51/2024/QH15 (hiệu lực 01/7/2025) sửa đổi Điều 22, khoản 4 có điều kiện theo cấp cơ sở (cơ bản/chuyên sâu) và mốc "đã xác định là tuyến huyện/tỉnh trước 01/01/2025"; con số 40% cho cấp chuyên sâu CHƯA xác minh. (c) Cấp chuyên môn của bệnh viện triển khai chưa biết. Ghi chú: văn bản gốc chưa đọc được (bản PDF tìm thấy là ảnh quét). Đầu ra: bảng trích dẫn văn bản gốc + hiệu lực + thay đổi 2026 (có Nghị định 161/2026/NĐ-CP về lương cơ sở; có văn bản hợp nhất Luật BHYT 2026).

**P-B6 (P2). Khoản đã ghi bằng công thức cũ cần tính lại?** Trước E3d khoản nội trú BHYT có thể bị ghi `insurance_amount = 0` do lượt khám nội trú có mức hưởng 0. Chưa biết số lượng thật. Phân tích: truy vấn đo (đã có bộ `KIEM-DU-LIEU-CPT-Q7-1.sql`, chỉ-đọc), nguyên tắc tính lại (chỉ khi đợt chưa quyết toán), hoàn tiền nếu đã thu — gắn P-B1 và P-D1.

**P-B7 (P3). Điểm kỹ thuật nhỏ:** ý nghĩa `status = 0` của thẻ BHYT (bộ đọc coi không hợp lệ, tiếp nhận chấp nhận); tra giá dùng đối tượng thanh toán HIỆN TẠI của đợt chứ chưa theo mốc đổi đối tượng (khoản thu thì chụp đúng mốc); nhãn "đồng chi trả" cho phần BHYT bằng 0 ở ước tính (chỉ nhãn, tổng không đổi); mốc kiểm thẻ là giờ thực hiện do nơi gọi truyền (chưa chặn ghi lùi) và lo ngại múi giờ UTC; cache cấu hình 5 phút.

### Nhóm C — Quyết toán ra viện
**P-C1 (P1). Thiết kế duyệt bảng kê ra viện (D11-2b).** Mô tả ở 2.6. Câu hỏi: (a) từng loại xử lý dòng (giữ nguyên/điều chỉnh số lượng/hủy/chuyển dịch vụ BHYT tương đương/chờ xác nhận): dữ liệu nào đổi, ai được làm, nhật ký, cách tính lại tiền BHYT; (b) duyệt bảng kê: "khóa chi phí" nghĩa là gì ở mức dữ liệu (cờ trên khoản? chặn ghi khoản mới? chặn sửa?), snapshot + băm gồm trường nào, tăng phiên bản khi nào, mở khóa từ trạng thái đã duyệt ra sao và ảnh hưởng gì; (c) tương tác với BHYT thay đổi muộn (P-B1) và ngưỡng 15% lương cơ sở toàn đợt (P-B3): tính lại trước hay sau khi duyệt; (d) chặn duyệt khi còn khoản thiếu giá, việc điều dưỡng chưa xong, hồ sơ bắt buộc chưa lập (xem P-F2); (e) khóa dòng và thứ tự khóa với các ca ghi khoản hằng ngày.
Đầu ra: sơ đồ trạng thái, bảng dữ liệu bị đổi theo từng thao tác, danh sách ca ghi/hàm đọc, rủi ro chạy đua với ca ghi khoản.

**P-C2 (P1). Vòng đời trạng thái "chờ BHYT" (`PaymentStatus = 3`).** Khi người bệnh phải trả 0 đồng và BHYT trả một phần, khoản được đánh dấu "chờ BHYT" ngay lúc ghi. Chưa rõ trạng thái này kết thúc khi nào, ai xác nhận, liên quan thế nào đến giám định/hồ sơ gửi BHXH và đến quyết toán/hóa đơn. Phân tích: định nghĩa trạng thái, chuyển trạng thái, báo cáo công nợ BHXH, ảnh hưởng khi tính lại BHYT.

**P-C3 (P2, bị chặn). D11-3: đóng đợt, thu tiền, hóa đơn điện tử, XML 130.** Cần pháp chế/kế toán. Phân tích điều kiện tiên quyết, danh sách điều kiện chặn (10 mã đề xuất — P-F2), hóa đơn điều chỉnh khi có tính lại, dữ liệu XML 130 phải khớp khoản thu.

### Nhóm D — Hoàn tiền
**P-D1 (P1, bị chặn). Hoàn tiền (E7) và ví người bệnh.** Hoàn khoản đã thu: xét nghiệm/CĐHA hủy, thuốc trả khi đã thu, chênh lệch sau tính lại BHYT, hoàn tạm ứng. Ví người bệnh (Q8): ngoại trú còn dùng không (đề xuất của tài liệu phân tích: tắt lưu số dư qua ngày ngoại trú; chỉ nội trú dùng tạm ứng/ví) — CHƯA được chủ dự án quyết. Phân tích: luồng hoàn (phiếu chi hoàn), quyền, chứng từ, tương tác với hóa đơn, trạng thái khoản sau hoàn, trả một phần.

**P-D2 (P2). Trả thuốc một phần và dòng điều chỉnh.** Hiện: chỉ hủy khoản khi trả HẾT dòng phát và khoản chưa thu; trả một phần để nguyên khoản (người bệnh có thể bị thu nhiều hơn thực dùng cho tới khi có quy tắc). Tài liệu phân tích đề xuất giảm số lượng khoản chưa thu hoặc sinh dòng điều chỉnh âm — dòng âm vướng chỉ mục duy nhất `(loại, mã tham chiếu)` nên cần mã tham chiếu riêng. Phân tích phương án an toàn và tác động lên bảng kê/XML.

### Nhóm E — Ngày giường
**P-E1 (P2). Tham số và công thức tính tiền ngày giường (E2b).** Đã có hàm tính thuần theo tham số, mặc định KHÔNG tính tiền (bảng kê không hiện tiền ngày giường). Các tham số chưa chốt vì tài liệu nguồn mâu thuẫn: cách tính số ngày (ngày ra − ngày vào, khi nào +1), ngưỡng giờ (đề xuất 4 giờ), nằm ghép (đề xuất 2 người 50%, từ 3 người 30%, tránh 33,33%), giường ban ngày (hệ số 0,3), chuyển khoa trong ngày (chia nửa/nửa hoặc tính theo khoa đến). TẤT CẢ là đề xuất CHƯA xác minh pháp lý. Phân tích: nguồn văn bản, cách cấu hình có ngày hiệu lực, cách ngày giường tương tác với chuyển khoa (hook phiếu chuyển khoa), với bảng kê, và với nguồn giá riêng `price_items`; cách sinh khoản theo ngày hay một lần khi ra viện.

**P-E2 (P1, mới). Đơn vị tính của giá dịch vụ thủ thuật/oxy khi một y lệnh sinh nhiều việc điều dưỡng.**
Hiện trạng (đợt 3 vừa làm, chờ review): mỗi việc điều dưỡng loại thủ thuật/chăm sóc hoặc oxy khi hoàn tất sinh MỘT khoản thu với số lượng 1 và đơn giá = giá hiệu lực của dịch vụ danh mục gắn với y lệnh. Ước tính của y lệnh tính theo số lần/mốc dự kiến. Một y lệnh oxy theo ca hoặc theo ngày, hoặc một thủ thuật lặp lại, có thể sinh nhiều việc; mỗi việc tính đủ giá dịch vụ.
Câu hỏi: giá dịch vụ trong `service_price_items` tính theo lần, theo giờ, theo ngày hay theo đợt điều trị? Với oxy/thủ thuật lặp lại thì mỗi việc có phải một lần tính tiền riêng không? Có dịch vụ nào "tính một lần cho cả y lệnh" hay "theo thời gian thực hiện" (oxy theo giờ, kết quả bước)? Cần dữ liệu: danh sách dịch vụ thủ thuật/oxy có trong danh mục y lệnh nội trú kèm đơn vị tính (cột đơn vị của dịch vụ), cùng số việc điển hình mỗi y lệnh.
Rủi ro: thu thừa người bệnh hoặc sai lệch ước tính. Đầu ra: quy tắc số lượng (theo việc, theo giờ từ dữ liệu bước oxy, hoặc theo y lệnh) và cách xử lý khi giá theo ngày; xác nhận với khoa/kế toán.

### Nhóm F — Hồ sơ bệnh án
**P-F1 (P1). Chưa có dữ liệu danh mục hồ sơ ⇒ mọi hook phát sinh phiếu bị vô hiệu.** Các sự kiện (tạo đợt, chuyển khoa, từ chối dịch vụ…) sinh dòng "phiếu cần lập" vào bảng thành phần bộ hồ sơ theo danh mục `record_catalog_*`; hiện không có dữ liệu danh mục nên các hook luôn bỏ qua (cố ý, để không làm hỏng ca gốc). Phân tích: nguồn nội dung danh mục (tài liệu phân tích nói theo Thông tư 32/2023/TT-BYT — chưa xác minh) do phòng kế hoạch tổng hợp duyệt; cách seed; xác minh hook chạy thật.
**P-F2 (P2). Danh sách điều kiện chặn trước ra viện.** Hiện mã kiểm tự do, chưa có nguồn. Đề xuất 10 mã (y lệnh mở, phiếu lĩnh/trả thuốc chờ, việc điều dưỡng chưa xong, khoản thiếu giá, giường chưa kết thúc, thiếu ICD ra viện, hồ sơ bắt buộc chưa lập, xác thực BHYT, chưa quyết toán…) — chủ dự án CHƯA duyệt. Phân tích: mức chặn cứng/cảnh báo từng mã, nguồn dữ liệu kiểm, thứ tự.
**P-F3 (P3).** Kết thúc đợt `EpisodeEndType = 6` ("tiên lượng nặng xin về"?) và ánh xạ XML; nhóm hồ sơ `09` (ra viện/chuyển viện) cần nguồn tự động riêng; dựng PDF gốc ngay khi người đầu tiên ký số; nhận biết y lệnh phẫu thuật/truyền máu (đề xuất theo nhóm BHYT 8 và 7, nhưng nhóm 8 có thể gộp cả thủ thuật; chưa xác minh); quyền thu ngân riêng cho thu/quyết toán và mở khóa bảng kê.

## 6. Quyết định chờ chủ dự án (chưa trả lời)
Danh sách 10 mã chặn ra viện (P-F2); ví người bệnh ngoại trú (P-D1); quyền thu ngân và mở khóa bảng kê; chặn cứng thiếu giá toàn diện (trạng thái chờ định giá, có thể đổi DDL) và cổng chặn ở quyết toán; đưa nhật ký bàn giao vào danh sách bỏ qua của git; cấp chuyên môn của bệnh viện triển khai (để đặt hệ số trái tuyến).

## 7. Việc ngoài phạm vi agent (cần con người/đơn vị khác)
- Khoa dược/DBA: đối soát đơn vị giá thuốc trên DB thật (bộ truy vấn chỉ-đọc đã soạn).
- DBA/chủ dự án: chạy bộ truy vấn chỉ-đọc kiểm dữ liệu BHYT nội trú (đã soạn, đã sửa lỗi cột).
- Pháp chế/BHYT/giám định: đối chiếu văn bản gốc (P-B5), quy chế hồi tố đã chốt cần bằng văn bản nội bộ, danh mục bệnh hiếm/hiểm nghèo.
- Kế toán/KHTH: ví, hoàn tiền, hóa đơn điều chỉnh, danh mục hồ sơ.

## 8. Phần còn lại của Tầng Service (để định cỡ phân tích)
Ước tính còn ~5% giao được ngay (đợt 2, 3, E3f đang chạy; D11-2b; nợ nối module như hook đóng lượt cấp cứu khi tiếp nhận ở khoa; baseline bề mặt công khai; build lại toàn bộ không tăng dần cuối đợt), ~3% bị chặn (D11-3, E7, ngày giường thật, hook phẫu thuật/truyền máu) và ~2-3% mới phát sinh từ phân tích BHYT (P-B1 đến P-B4).

## 9. Tài liệu liên quan (nếu cần đọc thêm, không bắt buộc)
`CAN-PHAN-TICH-THEM-E6B-Q7-BHYT.md`, `BOI-CANH-XAC-NHAN-CPT-Q7-1-NGUON-MUC-HUONG-NOI-TRU.md`, `XAC-MINH-KET-QUA-CPT-Q7-1-VA-QUYET-DINH-THUC-HIEN.md`, `DOI-CHIEU-PHUONG-AN-NGHIEP-VU-2026-11-11.md`, `THIETKE-E6B.md`, `VAN-DE-CAN-XU-LY-2026-11-11.md`, `KIEM-DU-LIEU-CPT-Q7-1.sql`, `KIEM-DON-VI-GIA-THUOC.sql`; nhật ký `2026-11-11-ban-giao-phien-pm-chieu-agy-dong-loat-d11-e6.md` (mục 11 trở đi). Thư mục: `C:\CongViec\agent\agent-orchestrator-selftest\NhatKyCongViec\` (bản sao một số tệp ở `C:\AgentControl\studio-state\prompts\`).
