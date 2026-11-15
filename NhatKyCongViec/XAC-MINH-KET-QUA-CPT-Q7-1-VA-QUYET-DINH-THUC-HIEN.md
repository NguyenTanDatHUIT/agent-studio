# XÁC MINH "KẾT QUẢ XÁC NHẬN CPT-Q7-1" VÀ QUYẾT ĐỊNH THỰC HIỆN (11/11/2026)

Tài liệu được xác minh: `C:\Users\tsmda\Downloads\k_t_qu_x_c_nh_n_cpt_q7_1_ngu_n_m_c_h_ng_bhyt_n_i_tr.md` (viết tắt **KQ**). Chủ dự án yêu cầu "xem qua và thực hiện tiếp". PM đã (1) đối chiếu các khẳng định về MÃ với mã thật, (2) kiểm chứng các khẳng định PHÁP LÝ bằng tìm kiếm web (nguồn thứ cấp; KHÔNG đọc được văn bản gốc), (3) quyết định phần thực hiện ngay và phần chưa.

## 1. Đối chiếu khẳng định về MÃ (đọc mã thật, `main@d8c9d48f`)
| Khẳng định của KQ | Kết quả |
|---|---|
| `AdmitFromEmergencyCommand.cs:752-753` sao chép `IsRightRoute`/`BenefitRate` từ lượt khám nguồn | **ĐÚNG** |
| `CompleteAdmissionCommand.cs:324-325` gán `IsRightRoute=false`, `BenefitRate=0` | **ĐÚNG** |
| `CompleteAdmissionCommand.cs:233-237` kiểm thẻ chỉ `Status >= 0` + đúng người bệnh, không kiểm ngày | **ĐÚNG**; lệch với `BhytBenefitResolver` (`Status > 0`) — chính là điểm THẤP L1 của review E3d |
| Bộ đọc: nhánh dự phòng `encounters.benefit_rate` chạy cả khi đợt đã gắn thẻ nhưng thẻ không hợp lệ | **ĐÚNG** (đọc `BhytBenefitResolver.cs`: bước 2 chạy bất kể có `health_insurance_card_id`) |
| Truy vấn F dùng `ec.total_amount` | **SAI — cột không tồn tại** (`encounter_charges` chỉ có `original_price`, `insurance_amount`, `final_price`); truy vấn sẽ lỗi khi chạy. Đã sửa ở `KIEM-DU-LIEU-CPT-Q7-1.sql` |
| `ChangePayerCommand.cs:68-90` không đổi thẻ / `PaymentObjectId` | **ĐÚNG** |

## 2. Kiểm chứng khẳng định PHÁP LÝ (tìm kiếm web 11/11/2026; chỉ có nguồn thứ cấp)
| Khẳng định của KQ | Kết quả kiểm chứng | Trạng thái |
|---|---|---|
| **Q3:** thẻ hết hạn khi đang nội trú ⇒ hưởng đến khi ra viện, **tối đa 15 ngày kể từ ngày thẻ hết hạn** | Hai nguồn thứ cấp độc lập (luatvietnam.vn, ebh.vn) cùng trích **khoản 9 Điều 27 Nghị định 146/2018/NĐ-CP**: "đang điều trị nội trú … cho đến khi ra viện, tối đa không vượt quá 15 ngày kể từ ngày thẻ BHYT hết hạn sử dụng". **KQ lại trích "Điều 50 Nghị định 188/2025/NĐ-CP": KHÔNG tìm thấy căn cứ cho trích dẫn này.** Chưa xác nhận NĐ 188/2025 (hiệu lực 01/7/2025, đang được sửa đổi) còn giữ nguyên quy tắc 15 ngày | **ĐÃ CÓ CĂN CỨ THỨ CẤP cho số 15 (NĐ 146/2018); trích dẫn NĐ 188/2025 CHƯA XÁC MINH.** (Đính chính PM: trước đây PM ghi "hưởng tới khi ra viện" — thiếu giới hạn 15 ngày; BỐI CẢNH đã ghi "chưa chắc có mốc 15 ngày" nên kết luận sơ bộ đó được sửa lại) |
| **Q2:** tuyến ảnh hưởng mức hưởng nội trú (cấp chuyên sâu trái tuyến chỉ 40%…) | Tìm thấy: Luật 51/2024/QH15 sửa đổi Điều 22 (khoản 4 về nội trú), hiệu lực 01/07/2025; có điều kiện theo cơ sở cấp cơ bản/chuyên sâu và mốc "đã xác định là tuyến huyện/tỉnh trước 01/01/2025". KHÔNG xác minh được con số 40% cho từng trường hợp và việc bệnh viện triển khai thuộc cấp nào | **MỘT PHẦN CÓ CĂN CỨ (tuyến CÓ ảnh hưởng); hệ số cụ thể CHƯA XÁC MINH** |
| **Q4:** dưới 6 tuổi chưa có thẻ, dùng Giấy chứng sinh; mã thẻ tạm `TE1…` | Không kiểm chứng riêng; Nghị định 188/2025 có điều về KCB khi chưa có thẻ (Điều 37, Điều 57) nhưng chưa đọc được nội dung chính xác | **CHƯA XÁC MINH** |
| **Q8:** chi phí một lần < 15% lương cơ sở ⇒ 100% | Nguồn thứ cấp nói NĐ 188/2025 có quy định này; **lương cơ sở đã đổi thành 2.530.000 đồng từ 01/7/2026 (Nghị định 161/2026/NĐ-CP)** nên ngưỡng ≈ 379.500 đồng; NĐ 188/2025 đang được sửa đổi | **CÓ CĂN CỨ THỨ CẤP; THÔNG SỐ ĐÃ ĐỔI THEO THỜI GIAN** |
| Luật 51/2024/QH15 hiệu lực 01/07/2025 | Khớp nguồn tìm được | CÓ CĂN CỨ THỨ CẤP |
| Quyết định 4750/QĐ-BYT (XML 130, nhiều thẻ cách `;` trên `MA_THE_BHYT`) | Chưa kiểm chứng | CHƯA XÁC MINH |

**Bài học quan trọng:** quy định BHYT thay đổi theo thời gian (lương cơ sở đổi 01/7/2026; Nghị định 188/2025 đang được sửa; có văn bản hợp nhất 2026). Mọi thông số pháp lý trong mã phải là CẤU HÌNH có ngày hiệu lực, KHÔNG viết cứng, và ghi rõ "chưa đối chiếu văn bản gốc". Văn bản gốc chưa đọc được (bản PDF tìm được là ảnh quét; liên kết `.doc` trả 404) — cần người đọc văn bản chính thức (Cổng thông tin Chính phủ / Thư viện Pháp luật) xác nhận trước khi coi là chốt.

## 3. Quyết định thực hiện
### Thực hiện NGAY (đợt **E3e**, có căn cứ mã + căn cứ thứ cấp cho số 15)
Sửa `BhytBenefitResolver` (dùng chung ước tính và khoản thật):
1. **Ân hạn thẻ hết hạn nội trú** theo tham số `InpatientCardExpiryGraceDays` (mặc định 15; trong `InpatientSettings`, đánh dấu "chưa phải giá trị chốt" như các tham số khác): thẻ coi là còn hiệu lực tại ngày thực hiện `d` khi `ValidFrom <= d` và (`d <= ValidTo`, hoặc thẻ còn hạn vào ngày nhập viện và `d <= ValidTo + ân hạn`).
2. **Nhánh dự phòng `encounters.benefit_rate` CHỈ chạy khi đợt KHÔNG gắn thẻ** (`health_insurance_card_id` rỗng). Đợt đã gắn thẻ nhưng thẻ hết hạn quá ân hạn ⇒ trả `0` (không BHYT) thay vì rơi xuống dự phòng; thẻ không tìm thấy/`Status <= 0` ⇒ `null` (chưa xác định, không dự phòng).
3. Giữ chữ ký và mọi chỗ gọi; dấu `CPT-Q7-1`, `CPT-Q7-5`.
Lý do ghép hai thay đổi: chỉ chặn dự phòng mà thiếu ân hạn sẽ làm người bệnh có thẻ hết hạn ≤ 15 ngày mất BHYT (sai luật theo nguồn thứ cấp).

### CHƯA thực hiện (và vì sao)
| Hạng mục KQ | Lý do chưa làm |
|---|---|
| Hệ số tuyến nội trú `InpatientWrongRouteFactor` (Q2) | Cần biết bệnh viện triển khai thuộc cấp nào (cấp chuyên sâu/cơ bản) và quy định cụ thể — KQ tự nêu chưa xác minh; hệ số 40% chưa có căn cứ |
| Sửa `CompleteAdmissionCommand` CHẶN nhập viện khi thẻ `Status <= 0`/ngoài hạn (Q6) | Chặn tiếp nhận người bệnh là quyết định nghiệp vụ (cấp cứu không được chặn; tiếp nhận tạm theo viện phí); cần chủ dự án/BHYT quyết |
| Thẻ tạm `TE1` cho trẻ dưới 6 tuổi (Q4) | Nội dung quy định chưa xác minh; thiết kế dữ liệu thẻ tạm chưa có |
| Bảng `admission_insurance_cards` + ca `Recalculate` (Q5, Q7) | Cần thiết kế DDL được duyệt (CPT-Q7-9) và quy chế hồi tố (KQ mục 3 câu 2 chưa có trả lời) |
| Trần VTYT, ngưỡng 15% lương cơ sở, đồng chi trả 5 năm (Q8) | Cần thiết kế đợt "thống nhất công thức" (CPT-Q7-3/8); thông số đổi theo thời gian (lương cơ sở) |
| Tính lại khoản đã ghi `insurance_amount = 0` (Q7) | Cần số liệu thật trước (truy vấn F đã sửa) rồi mới thiết kế script + hoàn tiền (E7, đang bị chặn) |

### Cần chủ dự án / đơn vị (3 điểm nội bộ KQ đã nêu)
1. Cấp chuyên môn của bệnh viện triển khai (cơ bản/chuyên sâu; trước 01/01/2025 là tuyến gì) — Tổ giám định BHYT/KHTH.
2. Quy chế duyệt hồi tố khi trình thẻ muộn — Tài chính kế toán + Tổ giám định.
3. Chạy bộ truy vấn chỉ-đọc `KIEM-DU-LIEU-CPT-Q7-1.sql` (đã sửa lỗi cột) trên DB thật — DBA/chủ dự án cấp quyền.
4. (Mới) Người có thẩm quyền đối chiếu **văn bản gốc** về ân hạn 15 ngày (NĐ 146/2018 khoản 9 Điều 27 và NĐ 188/2025 hiện hành) và tuyến nội trú (Luật 51/2024/QH15 Điều 22 khoản 4).
