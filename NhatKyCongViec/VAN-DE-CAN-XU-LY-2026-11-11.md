# CÁC VẤN ĐỀ CẦN XỬ LÝ — HIS_EMR Tầng Service (cập nhật chiều 11/11/2026)

Tổng hợp từ nhật ký bàn giao `2026-11-11-ban-giao-phien-pm-chieu-agy-dong-loat-d11-e6.md` (mục 1–14), `THIETKE-E6B.md`, `REVIEW-E3B.md`, `CAN-PHAN-TICH-THEM-E6B-Q7-BHYT.md`. Mức độ: **CAO** = có thể sai tiền/dữ liệu người bệnh; **TRUNG**; **THẤP**.

**Trạng thái nhanh:** `main` = `origin/main` = `d1b461d7` (đã push FIX-EMR, FIX-TPL, E5b). Tầng Service ước tính ~93%. E3b chưa merge (đang chờ review lần 2). Chưa làm Controller/View (theo chỉ đạo).

---

## A. Việc đang chờ CHỦ DỰ ÁN quyết định / xác nhận

### A1. E6b — 3 câu chưa quyết (chặn đợt 2 và 3)
| # | Câu hỏi | Đề xuất của PM | Chặn đợt |
|---|---|---|---|
| 3 | Đơn vị của `drug_price_items.Price` (đơn vị bán / cơ sở / liều)? | Tính theo đơn vị cơ sở (khớp `Quantity` dòng phát). Khoa dược xác nhận bằng dữ liệu thật trước khi chạy; DDL không có chú thích đơn vị. | Đợt 2 (phát thuốc) |
| 5 | Thiếu giá/danh mục thì làm gì? | Không chặn ca gốc: bỏ qua khoản thu, ghi `LogBusinessEvent`, trả `Warnings`; sau này có hàm đọc "khoản thiếu giá" để bù. | Đợt 2, 3 |
| 8 | Có bật tự động chốt y lệnh khi hết việc (`AutoCompleteOrderOnLastTaskDone`, O-18)? | Nối vào `CompleteNursingTask`; phải rà để không tạo ước tính mới trùng khoản thật và không deadlock. | Đợt 3 |

Đã chốt: 1 (thu theo PHÁT), 2 (dùng chung `ChargeType` 4), 4 (thủ thuật dở không thu), 6 (trả thuốc: hết + chưa thu ⇒ hủy khoản; còn lại chờ E7), 7 (giữ công thức BHYT hiện có, **tạm**, xem mục B1).

### A2. Xác nhận cách hiểu "phiếu chuyển khoa" (E5b đã merge theo cách hiểu này)
Hook `DEPARTMENT_TRANSFER` ở `PerformBedTransfer` chỉ bắn khi chuyển giường **khác khoa** và chỉ sinh dòng "phiếu cần lập" (`record_manifest_items`, trạng thái EXPECTED) — không tạo phiếu thật, không chặn ca. Trong mã chưa có thực thể "phiếu chuyển khoa". **Cần xác nhận:** đúng ý? Nếu muốn CHẶN chuyển khoa cho đến khi có phiếu thì là việc mới (chưa thiết kế).

### A3. Model mặc định
Lệnh `/model sonnet` ở cửa sổ `claude-2` đã **lưu Sonnet 5.5 làm mặc định cho các phiên Claude mới**. Giữ hay đổi lại?

### A4. 10 câu hỏi tồn từ bản bàn giao 17:00 (vẫn chưa có trả lời)
1. `option_values` `EpisodeEndType` có giá trị 6 không (mã hiện chỉ nhận 1..5)?
2. Nhóm `09` (Ra viện và chuyển viện) có cần nguồn tự động riêng không?
3. Ca nội trú chốt không dựng PDF (ký sau khi mở bản in): đúng ý đồ?
4. Y lệnh nào là PHẪU THUẬT, y lệnh nào là TRUYỀN MÁU (theo loại danh mục hay cột nào)? — chặn hook `SURGERY_ORDERED`/`TRANSFUSION_ORDERED`.
5. Ví người bệnh Q8: ngoại trú còn dùng không? — chặn E7.
6. `UnlockStatement` ánh xạ cờ `a`; `CollectPayment/Settle` có đòi thêm quyền `benh_nhan.thu_ngan` không?
7. Danh sách 10 điều kiện chặn trước ra viện (hiện `check_code` tự do, chưa có nguồn).
8. Commit `BAO-CAO-TIEN-DO-TONG-THE.md/.html` và các tệp nhật ký chưa theo dõi lên repo?
9. Seed danh mục hồ sơ `record_catalog_*` do KHTH chốt (chưa có seed ⇒ **mọi hook manifest hiện đều bỏ qua**: `ADMISSION_CREATED`, `DEPARTMENT_TRANSFER`, `SERVICE_REFUSED`).
10. Chạy truy vấn kiểm dòng trùng `(charge_type, ref_id)` trên DB thật **trước khi áp ALTER `encounter_charges`** (script có khối chặn báo cặp trùng).

---

## B. Vấn đề kỹ thuật/nghiệp vụ cần PHÂN TÍCH THÊM

### B1. Công thức BHYT khoản thu nội trú (E6b câu 7) — chi tiết ở `CAN-PHAN-TICH-THEM-E6B-Q7-BHYT.md`
Mã đánh dấu `CPT-Q7-1..7`; đặt dấu `// [CAN-PHAN-TICH-Q7:CPT-Q7-n]` trong mã khi chạm.
- **CAO — CPT-Q7-2:** nội trú tạo lượt khám mới `IsRightRoute=false`, `BenefitRate=0` (`CompleteAdmissionCommand.cs:324-325`), không ca nội trú nào cập nhật ⇒ `RecordCharge` có thể **không trừ BHYT** dù người bệnh đóng BHYT ⇒ nguy cơ thu thừa tiền.
- TRUNG: CPT-Q7-1 (ước tính lấy mức hưởng từ thẻ `benefit_level`, khoản thật từ `encounters`), CPT-Q7-3 (trần danh mục chỉ có ở ước tính), CPT-Q7-4 (đổi đối tượng giữa đợt), CPT-Q7-5 (thẻ hết hạn giữa đợt), CPT-Q7-6 (dưới 6 tuổi và quy tắc khác), CPT-Q7-7 (bảng kê so hai công thức).
- **Cần:** người bộ phận BHYT/KHTH xác nhận; sau đó một đợt "thống nhất công thức BHYT" + tính lại khoản đã ghi.

### B2. Bảng kê chi phí cộng đúp khi E6b ghi khoản thật (CAO — đã xác minh)
`FeeBoardOne.cs:208-216` chỉ bỏ ước tính khi `RefId == clinical_order.Id`. E6b dùng `RefId = nursing_task.Id / dispense_record.Id` ⇒ không khớp ⇒ cộng đúp (khoản thật + ước tính nguyên y lệnh). **Giải pháp đã chọn:** đợt 1 E6b sửa `FeeBoardOne` nối qua `RefId → ClinicalOrderId`, hiển thị "ước tính còn lại"; không đổi DDL (phương án cột `clinical_order_id` cần chủ dự án duyệt).

### B3. Hai nguồn giá khác nhau
Ước tính dùng `drug_price_items`/`service_price_items` (`LookupEffectiveCatalogPrice`, `private`); `PriceAtOne` (E2a) dùng `price_items`. Phải chọn MỘT cho khoản thật (đề xuất: cùng nguồn với ước tính). Chưa kiểm đơn vị giá thuốc (A1 câu 3).

### B4. Tính tiền ngày giường (E2b) — chạy bằng tham số, mặc định KHÔNG tính tiền
Nằm ghép (1/2, 1/3 hay 30%/33,33%), ban ngày 0,3, ngưỡng ≤ 4 giờ, `+1` ngày theo cách kết thúc, chuyển khoa trong ngày: **tài liệu nguồn mâu thuẫn, chờ pháp chế** (`GAP-2`). Không được điền số tạm.

### B5. Khoản thu — các chỗ chưa ghi 7 cột mới và rủi ro 23505 (E3c, chưa giao)
Ngoài `RecordCharge` (E3b), các chỗ `new EncounterCharge` còn lại chưa ghi `admission_id/payer_type/quantity/...`: `PaymentCommand.cs` `CreateOrderCharges` (:429) và `PayMedicationOrderCharge` (:714) — thêm nữa: `CreateOrderCharges` **có thể nổ 23505** nếu `items` trùng `RefId` trong cùng lần gọi, `PayMedicationOrderCharge` có thể đua; `ReceptionCommand.cs:506`, `EncounterChargeCommand.cs:17` (Service.Core, chuyển ở giai đoạn M). Cùng tệp `PaymentCommand.cs` với E3b nên làm SAU khi E3b merge.

### B6. Điểm THẤP chưa sửa
- `RecordCharge` chưa ghi `LogBusinessEvent` (Billing chưa có tiền lệ).
- XML cảnh báo thứ tự 2 tham số `decimal` của `ChargeMath.CoveredAmount` (đang giao agy-1, `C:\wt\xmlcm`).
- `RaiseRecordEventForModule` (E5b) là hàm công khai: an toàn vì lõi ném lỗi khi không có giao dịch; cần cập nhật baseline `his-service-public-surface.txt`.
- `adm.Id` dùng làm encounter khi `adm.EncounterId` rỗng không được kiểm sở hữu (E3b-fix2, hiếm).
- Trả thuốc MỘT PHẦN không đổi trạng thái dòng phát ⇒ khoản thu có thể lớn hơn thực dùng cho tới khi có quy tắc (E7).
- FIX-TPL: lô nhiều mẫu giờ trả kết quả từng mẫu thay vì thất bại cả lô — **chưa chạy trên DB thật**.
- FIX-EMR: điểm ngoại trú cũ chưa sửa (`SaveEmrFormDraft` dùng `DateTime.Now` `EmrFormCommand.cs:268`; `EmrCycleSignerNames` truy vấn trong vòng lặp `:383`; `InpatientService.cs:70` chưa gán `_emr.Auth`).

---

## C. Việc BỊ CHẶN (cần chủ dự án/pháp chế, agent không tự làm)
| Việc | Cần |
|---|---|
| D11-3: `SettleAdmission` đặt đợt `CLOSED`, thu tiền, hóa đơn điện tử, XML 130 | Pháp chế/KHTH quy định |
| E7: hoàn tiền XN/CĐHA, ví người bệnh Q8 | A4 câu 5 + quy định hoàn tiền |
| Tham số ngày giường (E2b chạy thật) | B4 |
| BHYT thẻ hết hạn giữa đợt (cách xử lý mặc định) | Pháp chế (CPT-Q7-5) |
| Hook `SURGERY_ORDERED`/`TRANSFUSION_ORDERED` ở `SignOrderBatch` | A4 câu 4 (tiêu chí nhận biết y lệnh) |
| Seed `record_catalog_*` | A4 câu 9 (KHTH) — nếu không, mọi hook manifest vô hiệu |

---

## D. Việc đang chạy / chờ nghiệm thu (đo lúc ~15:00)
| Việc | Ai | Trạng thái | Bước kế |
|---|---|---|---|
| **E3b** `RecordCharge` lưu 7 cột (`C:\wt\e3b`, 5 commit tới `1969e3e1`) | Sonnet (sửa lần 2), agy-1 (làm) | Review lần 1 KHÔNG ĐẠT (2 CAO, 2 TRUNG) ⇒ đã sửa lần 2, PM đã đọc diff | **Review lần 2 (agy-3) đang chạy** → ĐẠT thì merge, build, test, push |
| XML `ChargeMath.CoveredAmount` (`C:\wt\xmlcm`) | agy-1 | Đang làm | Nghiệm thu bằng git + build, merge |
| Thiết kế E6b | Sonnet | **Xong** (`THIETKE-E6B.md`) | Giao đợt 1 sau khi E3b merge |

## E. Việc kế (theo thứ tự)
1. Merge E3b (sau review lần 2 ĐẠT) → build Billing/InpatientPharmacy/Inpatient/Web.HIS/Web.ISign + 2 lớp test → push → xóa worktree.
2. **E6b đợt 1** (nền, review bắt buộc): sửa `FeeBoardOne`, cổng tra giá ở Inpatient, gỡ ghi chú A6c-D3. Chỉ cần A1 câu 2 (đã chốt). Prompt phải đính kèm `CAN-PHAN-TICH-THEM-E6B-Q7-BHYT.md`.
3. **D11-2b** (`ResolveSettlementLine`, `ApproveSettlementStatement`, mở khóa từ APPROVED): cần E3b; review bắt buộc (tiền). Dính CPT-Q7 nếu dùng số tiền khoản thật.
4. **E6b đợt 2** (phát thuốc + trả thuốc): cần A1 câu 3, 5, và B1/B3 làm rõ. **Đợt 3** (việc điều dưỡng + auto-complete): cần A1 câu 5, 8.
5. **E3c** (7 cột cho `CreateOrderCharges`/`PayMedicationOrderCharge`, `LogBusinessEvent`): sau khi E3b merge; review bắt buộc.
6. Nợ nối module: `AutoCompleteOrderOnLastTaskDone`→`CompleteNursingTask` (gộp vào E6b đợt 3), hook `ReceivePatient` đóng lượt cấp cứu, baseline `his-service-public-surface.txt`, B2 (`--no-incremental` cả hai solution, trần cảnh báo 3.591/3.413) khi không ai build.
7. Cập nhật `BAO-CAO-TIEN-DO-TONG-THE.md/.html` lên ~93% (sau A4 câu 8).

---

## F. Quy tắc vận hành cần nhớ
- Mọi việc tiền/ca cốt lõi: **review độc lập bắt buộc**, PM tự xác minh mục CAO bằng đọc mã trước khi giao sửa; sau 2 lần sửa ⇒ đổi cửa sổ.
- Build qua `bash /c/AgentControl/studio-state/build-slot.sh ...` (tối đa 3 lượt). Docker: chỉ container `his-ddl-test-*`; 11 container dự án khác TUYỆT ĐỐI không đụng.
- `[AO] ... đã xong` hay sai/đến sớm ⇒ luôn kiểm bằng git log/status + báo cáo + dòng cuối `HOÀN TẤT`.
- **Từ đêm 11/11 (chỉ đạo mới nhất): KHÔNG gọi Opus và KHÔNG gọi Sonnet nữa — mọi việc mới giao agy (Gemini 4 Carbon · medium).** Cửa sổ claude đã giao trước chỉ đạo (đợt 2, đợt 3) để chạy xong rồi đóng. Việc nặng/tiền cho agy: prompt rõ hơn + review độc lập chỉ-đọc bắt buộc bằng agy MỚI + PM tự đọc toàn bộ diff và xác minh mục CAO.
- Tệp bàn giao đọc đầu tiên khi mở phiên mới: mục 11–14 của `2026-11-11-ban-giao-phien-pm-chieu-agy-dong-loat-d11-e6.md`.

---
## Bổ sung 11/11 chiều muộn — tài liệu đối chiếu
Đã đối chiếu "Phương án xử lý nghiệp vụ" (Downloads) tại `DOI-CHIEU-PHUONG-AN-NGHIEP-VU-2026-11-11.md`: **A** áp dụng ngay (A2 coi như đã giải quyết theo hướng "không chặn lúc chuyển giường, chặn khi đóng bệnh án", chờ chủ dự án xác nhận); **B** chờ xác minh pháp lý (mốc 15 ngày thẻ hết hạn, quy tắc ngày giường, nhóm BHYT 7/8, trần tuyệt đối — KHÔNG đưa vào mã); **C** quyết định cần chủ dự án (thiếu giá `PENDING_PRICE`, CPT-Q7-2, trả thuốc một phần, ví Q8, quyền thu ngân, `.gitignore`); **D** phiếu xác nhận nhanh bổ sung; Phụ lục 1: truy vấn kiểm trùng `(charge_type, ref_id)` cho DBA (câu A4-10).

### Quyết định 11/11 chiều muộn
**C-1 (thiếu giá) và C-2 (CPT-Q7-2) đã chốt theo đề xuất PM** — xem mục "QUYẾT ĐỊNH CỦA CHỦ DỰ ÁN" cuối `DOI-CHIEU-PHUONG-AN-NGHIEP-VU-2026-11-11.md`. Tóm tắt: C-1 = chặn phát thuốc thiếu giá + cảnh báo (không chặn) với việc điều dưỡng ở bước 1; `PENDING_PRICE` + cổng D11 là bước 2, trình duyệt riêng (có thể đổi DDL). C-2 = `RecordCharge` dùng chung bộ đọc mức hưởng với ước tính (chuyển hàm xuống `Service.Core`, vì Billing chỉ tham chiếu Core), không ghi đè `encounters`; đợt mới **E3d**. Cập nhật E: thêm E3d sau E6b đợt 1 (có thể gộp E3c).
