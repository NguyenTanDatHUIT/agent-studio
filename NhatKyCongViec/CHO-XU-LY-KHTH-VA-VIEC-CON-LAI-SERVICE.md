# Việc chờ KHTH/pháp chế/kế toán (tách khỏi tiến trình service) và việc còn lại để hoàn thành tầng Service

Lập 11/11/2026 ~21:50 theo chỉ đạo của chủ dự án: mục cần KHTH xác nhận thì đánh dấu **CHỜ XỬ LÝ**, KHÔNG tính vào tiến trình hoàn thành Service. Căn cứ: `VAN-DE-CAN-XU-LY-2026-11-11.md`, bản bàn giao `2026-11-11-ban-giao-phien-pm-toi-e3f-vao-main-e6b-sua-loi-thiet-ke-d11-2b.md`, `git log main --merges` (đã đối chiếu), trạng thái worktree lúc 21:25. Mức hoàn thành là ước tính của PM, không phải số đo.

> **Chủ dự án chốt 11/11/2026 ~22:30:** phần mềm hiện chỉ xây để **DEMO**, chưa có khách hàng nên chưa có KHTH/pháp chế/kế toán xác nhận ⇒ toàn bộ mục 1 xử lý SAU khi có yêu cầu khách hàng; không gửi phiếu xác nhận lúc này. Đã duyệt: DDL cho P-B1 và P-B3 (hướng, DDL cụ thể vẫn do đợt thiết kế đề xuất và PM trình lại); thu thập công thức vào `/NhiDong/Docs/business/CONG-THUC-BHYT-NOI-TRU.md`; Docker bật được khi cần; cho commit nhật ký/báo cáo; cho chạy truy vấn kiểm dòng trùng.

## 1. CHỜ XỬ LÝ — nằm ngoài tiến trình service (chờ bên nghiệp vụ)
Mã/DDL nền đã có hoặc đã chạy bằng tham số mặc định an toàn; khi có xác nhận chỉ là đổi giá trị cấu hình hoặc một đợt nhỏ.

| # | Nội dung | Bên xác nhận | Hiện trạng mã (mặc định an toàn) |
|---|---|---|---|
| W1 | Cấp chuyên môn kỹ thuật của bệnh viện (cơ bản/chuyên sâu; tuyến trước 01/01/2025) ⇒ giá trị `InpatientWrongRouteBenefitPercent` (100 hay 40) | Tổ giám định BHYT/KHTH | E3f xong; mặc định 100 (không giảm) |
| W2 | Seed `record_catalog_*` (danh mục hồ sơ; nguồn Thông tư 32/2023/TT-BYT hay danh mục bệnh viện) | KHTH | Chưa seed ⇒ hook manifest bỏ qua, không lỗi |
| W3 | CPT-Q7-1/3/4/5/6/7 (nguồn mức hưởng, trần danh mục, đổi đối tượng giữa đợt, thẻ hết hạn giữa đợt, dưới 6 tuổi) | BHYT/KHTH | E3d/E3e xong theo đề xuất PM; ân hạn thẻ hết hạn là tham số |
| W4 | Tham số ngày giường E2b (nằm ghép, ban ngày 0,3, ngưỡng ≤ 4 giờ, `+1` ngày, chuyển khoa trong ngày) | Pháp chế/KHTH | `BedDayCalculator` xong, tham số chưa chốt ⇒ KHÔNG tính tiền |
| W5 | Nhóm BHYT 7 và 8 có đủ phân biệt phẫu thuật/thủ thuật, truyền máu? (hook `SURGERY_ORDERED`, `TRANSFUSION_ORDERED`) | KHTH/Khoa dược | Chưa làm hook |
| W6 | `EpisodeEndType = 6` (tiên lượng nặng xin về) map `MA_LOAI_RV`/`KET_QUA_DTRI`; nhóm `09` có nguồn tự động riêng? | KHTH/BHYT | Mã nhận 1..5 |
| W7 | Danh sách 10 điều kiện chặn trước ra viện (hiện `check_code` tự do) | KHTH | Có khung, chưa có nguồn mã |
| W8 | D11-3: `SettleAdmission` đặt `CLOSED`, thu tiền, hóa đơn điện tử, XML 130 | Pháp chế/KHTH/Kế toán | Chưa làm, bị chặn |
| W9 | E7: hoàn tiền XN/CĐHA, ví người bệnh Q8 (ngoại trú còn dùng ví?), trả thuốc MỘT PHẦN | Kế toán | Chưa làm |
| W10 | Đơn vị `drug_price_items.Price` (đơn vị bán/cơ sở/liều) đối soát dữ liệu thật | Khoa dược | Mã đang giả định đơn vị cơ sở; sai ⇒ lệch hàng loạt |
| W11 | Quyền thu ngân/mở khóa bảng kê (`benh_nhan.thu_ngan`) | KHTH/Kế toán | Chưa gắn quyền thêm |
| W12 | P-E2: oxy/thủ thuật lặp tính theo lần/ca/giờ/ngày; cột `billing_trigger_mode` | Kế toán/KHTH + chủ dự án (đổi DDL) | E6b3 đang tự ghi khoản; chờ quyết định tạm tắt oxy |
| W13 | Phiếu chuyển khoa: chặn chuyển khoa hay chỉ nhắc ("không chặn lúc chuyển giường, chặn khi đóng bệnh án") | KHTH/chủ dự án | E5b làm theo cách "nhắc" |

Ghi chú: số hiệu văn bản pháp lý trong tài liệu ngoài (`Downloads\...`) chưa đối chiếu bản gốc, không đưa vào mã.

## 2. VIỆC SERVICE CÒN PHẢI LÀM (không cần KHTH)
### 2a. Đang dở — cần đóng ngay
1. **E6b2 FIX2** (lỗi tiền CAO: BHYT tính trên giá tự trả; hủy nhầm khoản trả bằng ví): `agy-2` đang tiếp quản ở `C:\wt\e6b2` ⇒ PM nghiệm thu, build, 2 lớp test ⇒ merge.
2. **E6b3 FIX1**: đã commit `963592cb`; PM đã đọc diff (khớp review); còn build Nursing/Billing/Web.HIS/Web.ISign + 2 lớp test ⇒ merge. (E6b3 FIX2 oxy: chờ quyết định, mục W12.)
3. **E3g** (3 điểm liên module mức hưởng): `agy-3` đang làm ở `C:\wt\e3g` ⇒ PM đọc kỹ diff (chạm tiền), review ngắn nếu cần ⇒ merge.
4. Sau mỗi merge: build lại 5 dự án + 2 lớp test (mục kiểm ở bản bàn giao), push `main`, dọn worktree.

### 2b. Thiết kế đang chờ duyệt
5. **D11-2b** (xử lý dòng bảng kê, duyệt/mở khóa, khóa chống đua): `THIETKE-D11-2B.md` XONG (agy-1, 252 dòng); PM đã đọc toàn bộ và đối chiếu DDL/mã (CHECK `ck_discharge_settlements_approved`, `ck_encounter_charges_quantity`, `ck_discharge_settlement_actions_*`, không có ca nào nâng `reconcile_level` lên `OFFICIAL`): khớp. **Thiết kế KHÔNG đổi DDL/Entity ⇒ không cần duyệt DDL.** Còn chờ chủ dự án trả lời 6 câu (mục G.2 của thiết kế) và 3 chỉnh sửa PM đề nghị (cổng `BED_DAY_READY`, cổng `BHYT_CARD_RESOLVED`/ca `UpdateSettlementInsuranceResolution` dính W3/W4, đợt 4a chờ E6b2/E6b3). Sau đó giao 5 đợt: 2b.1 → 2b.2 → 2b.3 (tiền, review CAO nhất), 4a (sau E6b2/E6b3 vào `main`), 4b; mỗi đợt review độc lập bắt buộc.

### 2c. Việc chưa giao
6. **P-A1 — bộ kiểm thử tích hợp PostgreSQL thật cho mã tiền** (chủ dự án đã đồng ý): cần bật Docker Desktop, chỉ dùng container `his-test-pg-*`; 7 nhóm ca (idempotent/đua `23505`+`25P02`, mức hưởng, phát/trả thuốc, hoàn tất việc điều dưỡng, `FeeBoardOne` không cộng đúp, ràng buộc cột, thứ tự khóa). Hiện mã tiền chưa từng chạy kiểm thử thật ⇒ đây là việc lớn nhất để tin cậy.
7. **P-B1** (đa thẻ/trình thẻ muộn, bảng `admission_insurance_cards`, `applied_card_id`) và **P-B3** (công thức chuẩn, `bhyt_scope_amount`/`copay_amount`): cần chủ dự án duyệt DDL trước.
8. **Nợ kỹ thuật từ review E6b2/E6b3:** T2 (`VoidOrderCharge` không khóa dòng `encounter_charges`, đua với `SettlePayment`), T3 (quét đối soát khoản kẹt khi QR hết hạn), L1 (phát gộp `NursingTaskId = null` nhiều lô khác giá), L2 (`CheckRecordChargeExistingOwner` bỏ kiểm encounter khi cùng đợt), L3 (log đóng cảnh báo khi trả gộp đủ) + điểm THẤP các review E3f/E6b.
9. **Nợ nối module:** hook đóng lượt cấp cứu khi `ReceivePatient` (cần THIẾT KẾ vì `Nursing` không được tham chiếu `Emergency`), baseline `his-service-public-surface.txt`, B2 `--no-incremental` hai solution khi không ai build.
10. **Điểm ngoại trú cũ chưa sửa:** `SaveEmrFormDraft` dùng `DateTime.Now` (`EmrFormCommand.cs:268`), `EmrCycleSignerNames` truy vấn trong vòng lặp (`:383`), `InpatientService.cs:70` chưa gán `_emr.Auth`; FIX-TPL chưa chạy trên DB thật.
11. **Hai việc nhỏ cần chủ dự án cho phép:** chạy truy vấn kiểm dòng trùng `(charge_type, ref_id)` trên DB thật trước khi áp ALTER `encounter_charges`; commit nhật ký bàn giao và `BAO-CAO-TIEN-DO-TONG-THE` rồi cập nhật báo cáo (đang ghi 88%, đã cũ).

## 3. Thứ tự đề xuất
2a (đóng 3 đợt) → 2b/5 (D11-2b: duyệt DDL, code) → 2c/6 (P-A1) → 2c/8–10 (nợ kỹ thuật) → 2c/7 (P-B1/P-B3 sau duyệt DDL) → cập nhật báo cáo tiến độ. Mọi mục ở mục 1 chỉ mở lại khi bên nghiệp vụ trả lời.

---
## Cập nhật 11/11/2026 ~23:05 (PM)

### Quyết định mới của chủ dự án
- **W14 (mới, chờ khách hàng thật): "tờ bệnh án ra viện" của `ApproveSettlement` (D11-2b.3).** Chủ dự án chọn phương án **A**: giữ như hiện nay = bất kỳ tờ nội trú đã chốt/đã ký/đã sửa của đợt (`DocumentType = 2`, `Status ∈ {2,3,4}`, không bị thay thế/kết thúc) đủ để nâng `reconcile_level` lên `OFFICIAL` và gắn `discharge_document_id`. Rủi ro đã biết (REVIEW-D112B3 TRUNG #2): đợt có tờ điều trị/phiếu cam kết đã chốt nhưng chưa có tờ ra viện có thể lên `OFFICIAL`. Khi có khách hàng: lọc theo `CatalogItemId`/mẫu "tờ ra viện" do KHTH chốt và cân nhắc chỉ nhận `Signed (3)`.
- Mặc định đã chấp nhận (chưa ai phản đối): KHÔNG lưu `discharge_gate_checks` cho lần duyệt bị chặn (lý do chặn nằm trong thông báo lỗi); phiếu phát thuốc `ISSUED` chưa nhận KHÔNG chặn duyệt bảng kê.
- **Chỉ đạo vận hành:** từ 11/11 ~22:40 mọi việc MỚI giao `agy` (không giao `claude`); đã đóng toàn bộ cửa sổ claude.

### Đã vào `main` (đã push tới `0fe371d5`; `9c1d36c1` chờ cổng)
E6b2 (C1, T1), E3g, E6b3 (+ tạm tắt oxy: W12 TẠM TẮT, chờ chốt đơn vị tính), D11-2b.1 (guard + mở khóa từ `APPROVED`), D11-2b.2 (`ResolveSettlementLine`), PB3-1 (`BhytChargeFormula`), DDL + entity P-B1/P-B3 (`admission_insurance_cards`, `admission_charge_recalc_items`, `bhyt_scope_amount`, `copay_amount`, `applied_card_id`; hoãn `scope_split`), PB1.1 (resolver đọc lịch sử thẻ), D11-2b.3 (`ApproveSettlement`, chờ push).

### Đang làm / còn lại (không cần KHTH)
- Đang chạy (agy): D11-2b.4a, D11-2b.4b (cắm guard vào các ca ghi), review PB1.2.
- Chưa giao: PB3-3/4/5/6 (nối công thức chuẩn; PB3-3 và PB3-5 chờ D11-2b.4a vì cùng `PaymentCommand.cs`), PB1.3 (`RecalculateAdmissionCharges`, chờ PB1.2), PB1.4 (truy vấn đọc), P-A1 (kiểm thử PostgreSQL thật cho mã tiền; Docker đang chạy), nợ kỹ thuật (T3 khóa dòng `encounter_charges` ở luồng thu/hủy, L1–L3, hook đóng lượt cấp cứu...).
- Khi cài DB thật: dùng cửa sổ bảo trì cho `ALTER encounter_charges` (REVIEW-DDLPB T1); kiểm phiên bản PostgreSQL, quyền `btree_gist`, số dòng thật.

### Rủi ro còn lại ghi nhận (D11-2b.4b, 11/11 ~23:35)
- `CorrectBedStay`, `ReleaseBed` (và có thể `PerformBedTransfer`) KHÔNG khóa `inpatient_admissions` (chỉ khóa `beds`/`bed_assignments`): guard CHỈ ĐỌC được cắm sau khi biết `AdmissionId` nhưng không tuần tự hóa tuyệt đối với `ApproveSettlement` (cửa sổ đua nhỏ). Đóng bằng cách thêm khóa `inpatient_admissions` đúng thứ tự `RowLockTables.All` ở đợt riêng (cần thiết kế vì đổi thứ tự khóa của ca giường).
- Chưa cắm: `CreateOrderChargeEstimate` (tệp CRUD sinh sẵn, không có đợt/khóa), `SetBedSharing` (đổi sức chứa giường, không gắn đợt).
- `ReleaseBed` bị chặn từ `APPROVED`: D11-3 (`SettleAdmission`) cần ngoại lệ trả giường khi ra viện.
