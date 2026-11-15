# ĐỐI CHIẾU "PHƯƠNG ÁN XỬ LÝ NGHIỆP VỤ" VỚI MÃ NGUỒN VÀ QUYẾT ĐỊNH HIỆN TẠI (11/11/2026)

Nguồn đối chiếu: `C:\Users\tsmda\Downloads\ph_ng_n_x_l_nghi_p_v_his_emr_11_11_2026.md` (viết tắt **PA**). Đối chiếu với mã `main@08ff482c`, `VAN-DE-CAN-XU-LY-2026-11-11.md`, `CAN-PHAN-TICH-THEM-E6B-Q7-BHYT.md`, `THIETKE-E6B.md`.

**Nguyên tắc:** PA là ĐỀ XUẤT, không phải quyết định hay nguồn pháp lý. Mọi khẳng định về quy định BHYT/Bộ Y tế đều ở trạng thái **CHƯA XÁC MINH** cho đến khi người có thẩm quyền (pháp chế/BHYT/KHTH) xác nhận bằng văn bản; mã chỉ nhận thông số qua cấu hình, KHÔNG viết số cứng (quy tắc "nguồn của mọi giá trị").

---

## A. ÁP DỤNG NGAY (phù hợp mã và chỉ đạo; rủi ro thấp)
| Mã | Nội dung PA | Cách áp dụng | Khi nào |
|---|---|---|---|
| A-1 | **A2:** `DEPARTMENT_TRANSFER` không chặn chuyển giường; dòng EXPECTED của phiếu chuyển khoa phải chặn cứng khi đóng bệnh án/ra viện | Đúng với E5b đã merge. Việc cần làm: xác nhận bộ kiểm đóng hồ sơ (`record_closure_checks`, `FinalizeInpatientRecord`) chặn khi còn dòng `record_manifest_items` EXPECTED bắt buộc; nếu thiếu thì thêm vào D11 gate (`MISSING_MANDATORY_EMR_RECORDS`) | Kiểm khi làm D11-2b/D11-3; **câu A2 coi như đã giải quyết theo hướng này, chờ chủ dự án xác nhận** |
| A-2 | **B2:** "ước tính còn lại" về 0 khi y lệnh COMPLETED/CANCELLED/STOPPED | Bảng kê chỉ xét y lệnh ACTIVE/PAUSED (`FeeBoardOne.cs:~174-181`) nên đã thỏa. Ghi thành điều kiện nghiệm thu cho E6b đợt 1 | Nghiệm thu E6b đợt 1 (agy-4 đang làm) |
| A-3 | **A1-8:** chỉ tự chốt y lệnh có tổng số lượt xác định, loại trừ PRN | Khớp phạm vi O-18 (`ONCE`/`FIXED_TERM`). Giữ làm điều kiện khi nối `AutoCompleteOrderOnLastTaskDone` | E6b đợt 3 |
| A-4 | **A1-3:** giá theo đơn vị cơ sở + **B3:** một nguồn giá `drug_price_items`/`service_price_items` | Trùng đề xuất PM. Điều kiện: khoa dược xác nhận bằng truy vấn đối soát giá trên DB thật TRƯỚC khi chạy đợt 2 | E6b đợt 2 |
| A-5 | **E3c/B5:** loại trùng `RefId` trong `items` + giữ khóa đồng bộ | Thêm vào yêu cầu E3c (cùng tệp `PaymentCommand.cs`) | E3c |
| A-6 | **B6:** `LogBusinessEvent` cho `RecordCharge`; sửa `InpatientService.cs:70` (`_emr.Auth`), N+1 `EmrCycleSignerNames`, `SaveEmrFormDraft` `DateTime.Now` | Đã nằm trong danh sách điểm THẤP | E3c / một đợt dọn nợ riêng |
| A-7 | **A4-10:** kiểm dòng trùng `(charge_type, ref_id)` trên DB thật | Agent KHÔNG truy cập DB thật; DBA chạy. Truy vấn chỉ-đọc ở Phụ lục 1 | Ngay, trước khi áp ALTER `encounter_charges` |
| A-8 | **A4-9:** đội dự án soạn sẵn seed `record_catalog_*` cho KHTH duyệt | Hướng đúng (hiện chưa có seed ⇒ mọi hook manifest bị bỏ qua). Nội dung seed PHẢI lấy từ danh mục biểu mẫu do KHTH cung cấp/phê duyệt; PA nói "theo Thông tư 32/2023/TT-BYT" — **chưa xác minh** | Sau khi KHTH xác nhận nguồn |

## B. CHỜ XÁC MINH PHÁP LÝ / NGHIỆP VỤ (KHÔNG đưa vào mã)
| Mã | Khẳng định trong PA | Vì sao chưa nhận | Ai xác nhận | Trạng thái |
|---|---|---|---|---|
| B-1 | Thẻ hết hạn giữa đợt: hưởng tối đa **15 ngày** sau ngày hết hạn; tham số `InpatientCardExpiryGraceDays = 15` | PM nhớ quy định là hưởng tới khi ra viện, chưa chắc có mốc 15 ngày; trái nhau ⇒ sai tiền | Pháp chế/BHYT | CHƯA XÁC MINH |
| B-2 | Ngày giường: `ra − vào`; `+1` chỉ khi cùng ngày và > 4 giờ; ≤ 4 giờ không tính | Tài liệu nguồn dự án mâu thuẫn (`GAP-2`, "`+1` theo cách kết thúc") | Pháp chế/KHTH | CHƯA XÁC MINH |
| B-3 | Nằm ghép: 2 người 0,5; ≥ 3 người 0,3 (không dùng 33,33%) | Dự án đang mâu thuẫn giữa 1/2, 1/3, 30%, 33,33% | Pháp chế/BHYT | CHƯA XÁC MINH |
| B-4 | Giường ban ngày hệ số 0,3; chuyển khoa cùng ngày chia 0,5 + 0,5; vào khoa đầu ≤ 4 giờ chuyển ngay (ICU) thì tính trọn ngày theo khoa đến | Cùng nhóm tham số ngày giường, chưa có văn bản làm nguồn | Pháp chế/KHTH | CHƯA XÁC MINH |
| B-5 | Mức hưởng đặc biệt: miễn cùng chi trả (ngưỡng 15% lương cơ sở; 5 năm liên tục), dưới 6 tuổi 100%, thông tuyến nội trú 100% | Quy tắc BHYT phức tạp, thay đổi theo thời kỳ | BHYT | CHƯA XÁC MINH |
| B-6 | Công thức `M = min(T×R_DM, C_tran) × R_huong` | Trong mã chỉ thấy tỷ lệ thanh toán theo danh mục (`InsuranceCoverageRate`), PM chưa thấy cột **trần tiền tuyệt đối** (chưa kiểm hết DDL); thứ tự `min` và `×` cần BHYT chốt | BHYT + DBA | CHƯA XÁC MINH (cần kiểm DDL trước) |
| B-7 | Nhận biết y lệnh phẫu thuật/truyền máu theo nhóm BHYT số **8** và **7** | PM nhớ nhóm 8 gồm CẢ thủ thuật lẫn phẫu thuật nên "tách phẫu thuật khỏi thủ thuật thường" cần phân loại bổ sung; cần đối chiếu danh mục thật | KHTH/khoa dược | CHƯA XÁC MINH |
| B-8 | `EpisodeEndType = 6` = "Tiên lượng nặng xin về" map `MA_LOAI_RV = 4`, `KET_QUA_DTRI = 4` | Cần xem `option_values` thật và quy định XML 130 | KHTH/BHYT | CHƯA XÁC MINH |
| B-9 | 10 mã chặn ra viện (mục 3.3 PA) | Là đề xuất tốt; `check_code` hiện tự do, KHÔNG khóa miền (DDL `discharge_gate_checks`). `UNPRICED_OR_MISSING_CHARGES` cần trạng thái `PENDING_PRICE` chưa tồn tại (xem C-1) | Chủ dự án duyệt danh sách | ĐỀ XUẤT — chờ duyệt |

## C. MÂU THUẪN HOẶC QUYẾT ĐỊNH CẦN CHỦ DỰ ÁN (có tác động phạm vi)
| Mã | Vấn đề | PM đề xuất | Tác động |
|---|---|---|---|
| C-1 ✅ ĐÃ CHỐT 11/11 (theo đề xuất, 2 bước) | **Thiếu giá (A1-5):** PA = chặn cứng phát thuốc thiếu giá; việc điều dưỡng thiếu giá ghi `PENDING_PRICE` và chặn khóa bảng kê/ra viện (thực tế hơn đề xuất cũ "chỉ cảnh báo") | Nhận hướng của PA nhưng làm theo 2 bước: (1) đợt 2: chặn phát thuốc thiếu giá + cảnh báo cho việc điều dưỡng; (2) sau: thêm trạng thái chờ định giá + cổng D11 | `PENDING_PRICE` chưa có trong mã ⇒ có thể phải đổi DDL; sửa ca phát thuốc (Pharmacy); thêm cổng D11. **Cần chủ dự án quyết** |
| C-2 ✅ ĐÃ CHỐT 11/11 (theo đề xuất; đợt E3d) | **CPT-Q7-2:** PA = tính lại `IsRightRoute`/`BenefitRate` ở `CompleteAdmission` rồi ghi vào `encounters`/`admissions` | Đề xuất **ít rủi ro hơn**: cho `RecordCharge` dùng cùng bộ đọc mức hưởng như ước tính (`ResolveAdmissionBhytBenefitRatio`: thẻ `benefit_level`, dự phòng `encounters.benefit_rate`), không ghi đè cột của `encounters`. Đợt nội trú đã có `bhyt_route`, `health_insurance_card_id` | Một nguồn duy nhất; không đụng dữ liệu lượt khám ngoại trú. **Cần BHYT xác nhận mức hưởng đúng nguồn nào** |
| C-3 | **B6 (trả thuốc một phần):** PA = giảm `Quantity` hoặc sinh dòng điều chỉnh âm khi khoản CHƯA thu | Nhận; dòng âm cần `RefId` riêng (chỉ mục `(charge_type, ref_id)`); định nghĩa chi tiết ở đợt 2. Khoản ĐÃ thu vẫn chờ E7 | Mở rộng E6b đợt 2 |
| C-4 | **Hồi tố thẻ BHYT trình muộn (hai chế độ) + `RecalculateAdmissionBHYT` khi duyệt bảng kê** | Nhận làm hướng, đặt sau khi BHYT chốt công thức | Một đợt "thống nhất công thức BHYT" riêng + D11-2b |
| C-5 | **A4-5:** tắt lưu số dư Ví Q8 ngoại trú; chỉ Tạm ứng/Ví cho nội trú | Là quyết định nghiệp vụ tài chính | Mở khóa E7; chủ dự án + kế toán |
| C-6 | **A4-6:** `CollectPayment/Settle` đòi quyền `benh_nhan.thu_ngan`; `UnlockStatement` chỉ cho tổ trưởng viện phí/kế toán trưởng, bắt buộc lý do | Hợp lý theo phân tách nhiệm vụ | Quyết định phân quyền |
| C-7 | **A4-8:** đưa nhật ký bàn giao vào `.gitignore`, chỉ commit `BAO-CAO-TIEN-DO-TONG-THE` | Đổi chính sách repo | Chủ dự án quyết |
| C-8 | **Mục 4.3 PA:** "giữ Sonnet cho `claude-2`" | Chỉ đạo mới nhất: coding Sonnet 5.5, review/phân tích Opus 5.5 | Đã khớp, không cần xử lý |
| C-9 | **A4-3:** dựng PDF gốc khi người đầu tiên ký, các chữ ký sau nối tiếp | Hợp lý; cần kiểm ca ký hiện tại có làm đúng không | Kiểm khi làm EMR ký số |
| C-10 | **A4-2:** nhóm `09` (ra viện/chuyển viện) cần nguồn tự động riêng | Hướng đúng; cần liệt kê trường nguồn | Một đợt EMR nguồn tự động |

## D. PHIẾU XÁC NHẬN NHANH (bản bổ sung — họp KHTH/BHYT/Khoa dược/Kế toán)
Dùng mục 5 của PA, thêm các điểm sau (PA chưa có):
- [ ] **BHYT:** thẻ hết hạn giữa đợt nội trú — hưởng tới khi ra viện hay tối đa 15 ngày? Căn cứ văn bản nào? (B-1)
- [ ] **BHYT:** mức hưởng nội trú lấy từ nguồn nào cho khoản thật: thẻ `benefit_level`, tuyến, hay cột riêng? (C-2)
- [ ] **BHYT/DBA:** có cột "trần tiền tuyệt đối" theo danh mục không (stent, khớp...)? nằm ở bảng nào? (B-6)
- [ ] **KHTH/Dược:** nhóm BHYT 7 và 8 có đủ phân biệt phẫu thuật với thủ thuật không? (B-7)
- [ ] **Chủ dự án:** chặn cứng thiếu giá (`PENDING_PRICE`) — chấp nhận đổi DDL và sửa ca phát thuốc không? (C-1)
- [ ] **Chủ dự án:** danh sách 10 mã chặn ra viện (mục 3.3 PA) có duyệt nguyên văn không? (B-9)
- [ ] **KHTH:** nguồn nội dung seed `record_catalog_*` (Thông tư 32/2023/TT-BYT hay danh mục của bệnh viện)? (A-8)

## E. ẢNH HƯỞNG TỚI KẾ HOẠCH
- **Không đổi E6b đợt 1** (agy-4): A-2 thành điều kiện nghiệm thu.
- **E6b đợt 2:** chờ A-4 (đối soát giá), C-1 (thiếu giá), C-3 (trả thuốc chưa thu).
- **E6b đợt 3:** chờ C-1 (việc điều dưỡng), A-3.
- **D11-2b:** kiểm A-1; số tiền phụ thuộc C-2/C-4 (công thức BHYT).
- **E2b (ngày giường):** vẫn chạy bằng tham số, mặc định KHÔNG tính tiền, cho tới khi B-2/B-3/B-4 có văn bản.
- **E7:** chờ C-5.

## Phụ lục 1 — Truy vấn kiểm trùng cho DBA (CHỈ ĐỌC, không sửa dữ liệu)
```sql
-- Dòng đang hiệu lực trùng (charge_type, ref_id): phải = 0 dòng trước khi áp ux_encounter_charges_type_ref
SELECT charge_type, ref_id, COUNT(*) AS so_dong,
       array_agg(id ORDER BY created_date) AS ids,
       array_agg(encounter_id ORDER BY created_date) AS encounter_ids
FROM public.encounter_charges
WHERE status >= 0 AND ref_id IS NOT NULL
GROUP BY charge_type, ref_id
HAVING COUNT(*) > 1
ORDER BY so_dong DESC, charge_type, ref_id;
```
Nếu có dòng trùng: DỪNG, báo PM (không tự xóa/sửa); script ALTER `alter_encounter_charges.sql` đã có khối chặn cùng điều kiện.

## Phụ lục 2 — Kiểm DDL nên làm trước khi bàn B-6 (PM chưa kiểm hết)
Tìm cột trần/giới hạn thanh toán BHYT theo danh mục trong `drug_price_items`, `service_price_items`, bảng danh mục dịch vụ/vật tư (`grep -in "insurance\|coverage\|ceiling\|max" Database/**/*price*.sql Database/**/*catalog*.sql`). Mới thấy `InsuranceCoverageRate` (tỷ lệ) trong tra giá ước tính (`InpatientService.OrderCore.cs:2276-2370`).

---
## QUYẾT ĐỊNH CỦA CHỦ DỰ ÁN (11/11/2026 chiều muộn): C-1 và C-2 — theo đề xuất của PM

### C-1 — Thiếu giá: CHỐT theo đề xuất, làm 2 bước
- **Bước 1 (làm trong E6b đợt 2/3, không đổi DDL):**
  - Phát thuốc nội trú (`DispenseInpatientOrder`): **chặn khi mặt hàng thiếu giá hợp lệ** (không ghi dòng phát, trả lỗi nghiệp vụ rõ). Khoa dược không xuất thuốc chưa định giá.
  - Việc điều dưỡng (`CompleteNursingTask`, loại thủ thuật/oxy có dịch vụ): **KHÔNG chặn ca** tại giường; bỏ qua khoản thu + `LogBusinessEvent` + trả `Warnings`.
- **Bước 2 (làm sau, MỖI BƯỚC CẦN DUYỆT RIÊNG):** trạng thái chờ định giá (`PENDING_PRICE`, nhiều khả năng cần đổi DDL — sẽ trình chủ dự án duyệt thiết kế DDL trước khi làm), cổng chặn khóa bảng kê/ra viện ở D11 (mã `UNPRICED_OR_MISSING_CHARGES`), và quy trình chạy bù khoản thu khi có giá.
- Hệ quả: đợt 2 còn chờ A-4 (đối soát đơn vị giá trên DB thật) và câu 3. Chặn phát thuốc cần sửa ca ở `Service.InpatientPharmacy`.

### C-2 — CPT-Q7-2: CHỐT theo đề xuất
- `RecordCharge` dùng **cùng bộ đọc mức hưởng với ước tính** (thẻ `health_insurance_cards.benefit_level` còn hiệu lực tại `PerformedAt`, dự phòng `encounters.benefit_rate > 0`), **không ghi đè** `encounters.IsRightRoute/BenefitRate` ở `CompleteAdmission`. Không đổi công thức ước tính.
- **Ràng buộc kỹ thuật đã xác minh (PM, `.csproj`):** `Service.Billing` chỉ tham chiếu `Service.Core`; `Service.Inpatient` tham chiếu Billing ⇒ Billing KHÔNG gọi được `ResolveAdmissionBhytBenefitRatio` (hiện `private` ở `InpatientService.OrderCore.cs:2117`). **Cách làm đề xuất:** chuyển bộ đọc thành hàm dùng chung ở `Service.Core/Components` (nhận `HisDbContext`, `admissionId`, mốc thời gian; thuần đọc DB), để ước tính (Inpatient) và `RecordCharge` (Billing) cùng gọi MỘT hàm; giữ hành vi ước tính y nguyên (hồi quy bằng đối chiếu mã, không đổi số).
- Đợt mới đề xuất: **E3d** ("thống nhất nguồn mức hưởng BHYT cho `RecordCharge`"), chạm `Service.Core/Components` (mới), `InpatientService.OrderCore.cs` (đổi thành gọi hàm chung), `PaymentCommand.cs` (`RecordCharge`); mọi chỗ chạm BHYT đặt dấu `CAN-PHAN-TICH-Q7`. Review độc lập BẮT BUỘC (tiền). Làm SAU khi E6b đợt 1 merge (cùng tệp `PaymentCommand.cs`) và có thể gộp với E3c.
- **Điều kiện kiểm khi nghiệm thu E3d:** (1) với đợt có thẻ hợp lệ, khoản thật và ước tính dùng cùng mức hưởng; (2) khi chưa xác định được mức hưởng: hành vi KHÔNG làm hỏng ca (không BHYT, đánh dấu như ước tính `IsBhytBenefitRateUndetermined`); (3) ngoại trú không đổi số tiền; (4) BHYT xác nhận nguồn mức hưởng nội trú đúng (CPT-Q7-1) trước khi coi là hoàn tất — đây là bước XÁC NHẬN, không chặn việc viết mã.
