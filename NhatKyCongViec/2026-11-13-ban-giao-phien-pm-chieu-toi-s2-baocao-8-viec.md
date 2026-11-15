# Bàn giao phiên PM (13/11 ~16:22): Báo cáo 8 việc nghiệp vụ S2 — Tổng hợp câu hỏi chưa chốt

Đọc kèm (theo thứ tự): `2026-11-13-ban-giao-phien-pm-chieu-toi-s2-quyet-dinh-chot.md`, `QUYET-DINH-S2-02-VA-S2-15-V1.md`, `BAOCAO-NGHIEP-VU-8-VIEC-S2-BV-NHI-DONG-V1.md` (đã lưu vào `NhiDong\Plan Coding\Controller\`).

---

## 1. Nguồn tài liệu vừa xử lý

**File:** `BAOCAO-NGHIEP-VU-8-VIEC-S2-BV-NHI-DONG-V1.md` — Báo cáo phân tích nghiệp vụ độc lập 8 việc, không đọc mã nguồn, gắn nhãn `[đã kiểm]`/`[kinh nghiệm]`/`[suy luận]`. **Tất cả 8 việc đều HOÀN TẤT.**

**Đánh giá:** Nhất quán với `QUYET-DINH-S2-02-VA-S2-15-V1.md`. Không có mâu thuẫn. Bổ sung thêm:
- Chi tiết ma trận xử lý rời Cấp cứu (Việc 3) → đầu vào cho S2-04
- Đặc tả trường sổ ngoại lệ nợ Append-only (Việc 4) → DDL spec cho S2-18
- 9 bước ra viện chuẩn hóa + 5 hàm Service mới (Việc 5) → đầu vào S2-18
- 8 trường thiếu trên Phiếu công khai thuốc (Việc 6) → đầu vào S2-13
- Thiết kế PEWS 2 kịch bản (Việc 7) → đầu vào S2-20
- Bộ 24 kịch bản UAT (Việc 8) → tiêu chí nghiệm thu

---

## 2. Câu hỏi mới cần chủ dự án xác nhận (phát sinh từ báo cáo 8 việc)

> Các câu hỏi đã có trong quyết định `QUYET-DINH-S2-02-VA-S2-15-V1.md` không lặp lại ở đây.

### Nhóm S2-02 (Y lệnh miệng)
| Mã | Câu hỏi | Đề xuất báo cáo | Trạng thái |
|---|---|---|---|
| `V2-Q1` | Thuốc kiểm soát đặc biệt rút lẻ liều theo cân nặng bệnh nhi (ví dụ dùng 0.2 ống, dư 0.8 ống): có bắt buộc nhập lượng thực tiêm + biên bản hủy kèm người chứng kiến ngay trên màn hình thực hiện thuốc không? | **(a) Có** — bắt buộc ghi nhận trên HIS | ⚠️ **Chờ chốt** |

### Nhóm S2-04 (Rời Cấp cứu)
| Mã | Câu hỏi | Đề xuất báo cáo | Trạng thái |
|---|---|---|---|
| `S2-04-Q1` | CLS đã lấy mẫu dài ngày (cấy máu/dịch não tủy, 3–5 ngày có kết quả): gắn cờ tự chuyển tiếp khi nhập Nội trú + Trưởng tua trực có quyền Override khi chuyển ICU/Phòng mổ khẩn? | **(a) Có, gắn cờ nhóm CLS dài ngày + Override có lý do** | ⚠️ **Chờ chốt** |
| `S2-04-Q2` | Tách 2 mã kết quả rời Cấp cứu riêng biệt: *Xin về (thân nhân ký cam kết + đóng viện phí)* vs *Trốn viện (tự ý bỏ về không rõ ràng)*? | **(a) Tách 2 mã, cổng kiểm soát khác nhau** | ⚠️ **Chờ chốt** |

### Nhóm S2-18 (Ra viện)
| Mã | Câu hỏi | Đề xuất báo cáo | Trạng thái |
|---|---|---|---|
| `V5-Q1` | **Quan trọng — ảnh hưởng thiết kế:** Vị trí bước Ký số Giấy ra viện: cho phép ký ngay sau khi chốt tờ bệnh án (song song bước đối soát/thu ngân), chỉ chặn ở bước *In bản chính*? Hay bắt tất toán xong mới cho ký? | **(a) Cho ký sớm, chặn In bản chính** | ⚠️ **Chờ chốt — cần trước khi giao mã S2-18** |
| `V5-Q2` | In lại bản chính Giấy ra viện: lần 2+ đóng dấu "Bản sao", muốn in lại "Bản chính" phải có quyền riêng + nhập lý do? | **(a) Có phân biệt** | ⚠️ **Chờ chốt** |
| `S2-18-Q2.1` | Tách cổng phát hành BHXH khỏi nợ cá nhân: chỉ chặn *In bản chính* khi chưa tất toán, còn *Phát hành BHXH* cho đi ngay khi đủ chữ ký + bảng kê duyệt? | **(a) Cho phép gửi BHXH ngay** — tránh trễ hạn phần quỹ BHYT | ⚠️ **Chờ chốt** |
| `S2-18-Q2.2` | Phân 2 cấp duyệt sổ ngoại lệ nợ: dưới ngưỡng tiền → Trưởng phòng TCKT/KHTH/Trực lãnh đạo; trên ngưỡng → Ban Giám đốc? | **(a) Phân 2 cấp theo ngưỡng cấu hình** | ⚠️ **Chờ chốt** |

### Nhóm S2-13 (Phiếu công khai thuốc)
| Mã | Câu hỏi | Đề xuất báo cáo | Trạng thái |
|---|---|---|---|
| `S2-13-Q1` | Ẩn/hiện Đơn giá & Thành tiền trên phiếu: làm tham số tùy chọn lúc bấm In? | **(a) Tham số chọn lúc in, mặc định theo cấu hình viện** | ⚠️ **Chờ chốt** |
| `S2-13-Q2` | Gộp Vật tư tiêu hao tính phí (kim luồn, dây truyền) vào phần dưới bảng thuốc? | **(a) Cho phép gộp có cờ bật/tắt** | ⚠️ **Chờ chốt** |

### Nhóm S2-20 (PEWS)
| Mã | Câu hỏi | Đề xuất báo cáo | Trạng thái |
|---|---|---|---|
| `S2-20-Q1` | Chọn Kịch bản (b) làm mặc định: Nút Nhận ca trực + Broadcast BS đang mở phiên + ĐD tích xác nhận đã gọi trực tiếp? | **(a) Kịch bản (b) mặc định, ghép lịch trực khi có** | ⚠️ **Chờ chốt** |
| `S2-20-Q2` | Chống bão cảnh báo tại PICU/NICU: trại thường báo khi PEWS ≥ 4, Hồi sức chỉ báo khi tăng thêm ≥ 2 điểm? | **(a) Cấu hình theo khoa** | ⚠️ **Chờ chốt** |

### Pháp lý (Việc 1)
| Mã | Câu hỏi | Đề xuất báo cáo | Trạng thái |
|---|---|---|---|
| `V1-Q1` | Thời hạn lưu nhật ký đọc bệnh án (`Read log`): lưu nóng 12 tháng + lưu lạnh theo tuổi thọ hồ sơ 15–20 năm? | **(a) Lưu kép** | ⚠️ **Chờ chốt** |
| `V1-Q2` | Khoa Dược rà soát cập nhật cờ kiểm soát đặc biệt toàn bộ danh mục (đặc biệt *Etomidate* vào nhóm hướng thần từ 01/06/2026) trước khi bật S2-02? | **(a) Phải rà soát trước** | ⚠️ **Chờ chốt — cần trước khi bật S2-02** |

### UAT (Việc 8)
| Mã | Câu hỏi | Đề xuất báo cáo | Trạng thái |
|---|---|---|---|
| `V8-Q1` | 24 kịch bản UAT dùng làm cả Integration Test tự động (phải xanh 100% trước bàn giao) lẫn phiếu nghiệm thu người dùng cuối? | **(a) Cả hai** | ⚠️ **Chờ chốt** |

---

## 3. Nội dung quan trọng từ báo cáo cần đưa vào prompt agent

### 3.1. Ma trận rời Cấp cứu (Việc 3) → đầu vào S2-04A

Báo cáo đã lập bảng ma trận `5 kiểu rời × 7 thứ còn dở` chi tiết. **Khi giao S2-04A, agent phải đọc tài liệu này** làm tham chiếu nghiệp vụ bổ sung cho `PROMPT-CTRL-S2-04A.md`.

Trích điểm quan trọng nhất cho S2-04:
- Y lệnh miệng chưa ký: Nhập Nội trú → **Cảnh báo + Chuyển tiếp chờ ký** (không tự hủy). Ra viện về nhà/Chuyển viện/Xin về → **Chặn cứng**. Tử vong → **Cảnh báo đỏ + Chặn khóa hồ sơ/bảng kê** (cho giải phóng giường nhưng BS phải ký bù đủ trong ca).
- CLS dài ngày (cấy máu/dịch não tủy): cho phép Chuyển tiếp khi nhập Nội trú + có Override của Trưởng tua.
- Thuốc kiểm soát đặc biệt rút lẻ liều: ghi lượng thực dùng + biên bản hủy lượng dư có 02 nhân viên xác nhận **ngay trên dòng thực hiện thuốc** trước khi mở cổng rời.
- Tách *Xin về* (thân nhân ký cam kết) và *Trốn viện* (tự ý bỏ về) thành 2 mã riêng biệt với cổng khác nhau.

### 3.2. Đặc tả sổ ngoại lệ nợ (Việc 4) → DDL spec S2-18

Bảng 15 trường `Append-only`, 5 loại `action_type` (`GRANT`, `EXTEND`, `ADJUST`, `SETTLED`, `REVOKE`). **Khi agent viết DDL bảng sổ ngoại lệ nợ, phải đọc Việc 4 của tài liệu này.**

### 3.3. 9 bước ra viện + 5 hàm Service mới (Việc 5) → S2-18

Thứ tự chuẩn hóa, điều kiện cổng từng bước, kết quả hệ thống đã được định nghĩa rõ. Đặc biệt:
- Bước 2 `[HÀM MỚI 1]`: Xác nhận hoàn tất ra viện lâm sàng (Trả giường) — không chặn tài chính
- Bước 6 `[HÀM MỚI 2]`: Thu tiền / Chi hoàn ứng & Hóa đơn điện tử
- Bước 7 `[HÀM MỚI 3]`: Tất toán (hỗ trợ 0 đồng)
- Bước 8 `[HÀM MỚI 4]`: In bản chính Giấy ra viện
- Bước 9 `[HÀM MỚI 5]`: Phát hành dữ liệu lên cổng BHXH

### 3.4. Phiếu công khai thuốc (Việc 6) → S2-13

8 trường bắt buộc bổ sung: Ngày sinh + Tháng tuổi (sơ sinh → ngày tuổi), Giới tính, Số buồng/giường, Ngày vào viện, Chẩn đoán, **Đơn vị tính (ĐVT)**, **Số lượng ngày quy đổi**, **Tổng số khoản mỗi ngày** (theo Phụ lục 7 TT 23/2011).

### 3.5. UAT 24 kịch bản (Việc 8) → Tiêu chí nghiệm thu

Khi agent hoàn thành S2-02/S2-15/S2-18/S2-04, PM nghiệm thu theo 24 UAT này:
- Nhóm 1 (UAT-01→04): Y lệnh miệng
- Nhóm 2 (UAT-05→08): Ra viện & Tất toán
- Nhóm 3 (UAT-09→12): Khoa của tôi đóng mặc định
- Nhóm 4 (UAT-13→16): Break-glass
- Nhóm 5 (UAT-17→20): Chuyển khoa 2 bước
- Nhóm 6 (UAT-21→24): Hội chẩn liên khoa

---

## 4. Hàng đợi (CẬP NHẬT)

| Thứ tự | Việc | Prompt | Worktree | Điều kiện |
|---|---|---|---|---|
| **1** | S2-02-g (rà dữ liệu, chỉ đọc) | `PROMPT-CTRL-S2-02G.md` ✅ | `ctrl-base` | Đóng claude-9 hoặc claude-8 trước |
| **2** | S2-04A (phân tích `ConfirmEmergencyDeparture`) | `PROMPT-CTRL-S2-04A.md` ✅ + đọc Việc 3 báo cáo | `ctrl-base` | Sau S2-02-g |
| **3** | S2-15-a (DepartmentScopeResolver) | Chưa viết | `ctrl-s2-15` chưa tạo | Sau 04A |
| **4** | S2-02-a (cổng chặn + cờ nội trú) | Chưa viết | worktree mới | Sau S2-02-g |
| **5–9** | Nhóm J, I, K, L, M | Đã có prompt | Worktree chưa tạo | Độc lập |

---

## 5. Trạng thái cửa sổ Claude (vẫn giữ nguyên từ bản trước)

| Cửa sổ | Việc | Trạng thái |
|---|---|---|
| Agent 0 | Điều phối | Đang hoạt động |
| `claude-9` | S2-02A phân tích (xong) | **Chờ chủ dự án đóng** |
| `claude-8` | S2-15A phân tích (xong) | **Chờ chủ dự án đóng** |

> ⚠️ Hiện 3 cửa sổ = tối đa. **Phải đóng claude-9 hoặc claude-8 trước khi giao S2-02-g.**
