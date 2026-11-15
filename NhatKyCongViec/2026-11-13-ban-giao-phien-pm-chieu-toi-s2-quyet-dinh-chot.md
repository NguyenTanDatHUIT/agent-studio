# Bàn giao phiên PM (13/11 chiều tối): Quyết định S2-02 & S2-15 đã chốt — chuẩn bị giao mã

Đọc kèm (theo thứ tự): `2026-11-13-ban-giao-phien-pm-chieu-toi-s2-hang-doi-cau-noi-gemini.md` (toàn bộ), `QUYET-DINH-S2-02-VA-S2-15-V1.md` (đã lưu vào `NhiDong\Plan Coding\Controller\`).
Mọi đường dẫn `prompts\` = `C:\AgentControl\studio-state\prompts\`. Repo công cụ: `C:\CongViec\agent\agent-orchestrator`. Repo code: `C:\CongViec\itc-git\HIS_EMR` (thư mục việc `NhiDong\`).

---

## 0. Chỉ đạo hiện hành (giữ nguyên từ bản trước)

(Xem mục 0 bản `2026-11-13-ban-giao-phien-pm-chieu-toi-s2-hang-doi-cau-noi-gemini.md`)
- Tối đa 3 cửa sổ Claude đồng thời tính cả Agent 0.
- Không push, không merge vào `main`. Không `git checkout/reset/stash/clean`.
- Không ghi lên DB thật; DDL mới phải có chủ dự án đồng ý.
- Agent 0 chỉ điều phối, không tự sửa mã.

---

## 1. Việc đã làm trong phiên này (13/11 ~15:57–16:00)

| # | Việc | Kết quả |
|---|---|---|
| 1 | Copy `quy_t_nh_nghi_p_v_s2_02_v_s2_15_v1.md` vào `NhiDong\Plan Coding\Controller\QUYET-DINH-S2-02-VA-S2-15-V1.md` | ✅ Xong |
| 2 | Kiểm báo cáo `BAOCAO-CTRL-S2-02A.md` và `BAOCAO-CTRL-S2-15A.md` có dòng `HOÀN TẤT` | ✅ Cả hai đều có. `ctrl-base` HEAD `a2a23e37`, cây không đổi |
| 3 | Viết `PROMPT-CTRL-S2-02G.md` (rà dữ liệu chỉ-đọc, bước g trong chuỗi S2-02) | ✅ Tạo xong |

---

## 2. Quyết định E1–E10 (S2-02) và Q1–Q10 (S2-15) — ĐÃ CHỐT

Toàn bộ câu hỏi mà `claude-9` và `claude-8` phân tích **đã được chủ dự án trả lời** trong `QUYET-DINH-S2-02-VA-S2-15-V1.md`. Tóm tắt nhanh các điểm chốt quan trọng nhất:

### S2-02 (Y lệnh miệng)
- **E1:** Điều dưỡng ghi nhận kèm thực hiện → tạo eMAR ngay; bác sĩ ký chỉ đối chiếu + liên kết, **không sinh eMAR thứ hai**.
- **E2:** Chặn thuốc kiểm soát đặc biệt & ngoài danh mục; ngoại lệ cấp cứu chỉ mở khi `is_emergency_cabinet_allowed=true` + bác sĩ có quyền GN-HT + 2 người xác nhận. Chặn tuyệt đối hóa chất ung thư.
- **E3:** Người chứng kiến bắt buộc: High-alert, kiểm soát đặc biệt ngoại lệ, máu/chế phẩm máu, y lệnh qua điện thoại.
- **E4:** Ưu tiên bác sĩ ra lệnh ký; mở "Xác nhận thay" cho Trưởng khoa/Phó/BS điều trị chính/Trưởng tua; giữ `ordered_by` làm `MA_BAC_SI` XML BHYT.
- **E5:** Tách luồng 5A (chọn nhầm BS) và 5B (từ chối sau khi đã dùng → giữ eMAR, không thu tiền/BHYT phần bị từ chối, đẩy vào `INCIDENT_COST_SUSPENSE`, sinh sự cố y khoa TT43/2018).
- **E6:** `NGAY_YL` = `verbal_ordered_at` (giờ BS ra lệnh thực tế), `yyyymmddHHmm`.
- **E7:** Cho ký bù khi đợt ở: Đang điều trị / Chờ ra viện / Chuyển viện / Xin về / Tử vong / Chờ duyệt bảng kê. Khóa cứng khi đã Đóng BA hoặc Khóa XML BHYT.
- **E8:** 4 cổng: (1) Lập QĐ ra viện, (2) ĐD chốt bảng kê, (3) Thu ngân duyệt, (4) Đóng BA.
- **E9:** Ra viện/Chuyển viện/Tử vong/Duyệt bảng kê/Đóng BA → Block 100%. Cấp cứu → Nội trú/Phòng mổ cùng viện → Warn.
- **E10:** Hạn chuẩn 24h (cờ đỏ) + cảnh báo sớm 8h (cờ vàng), cấu hình qua `app_settings`.

### S2-15 ("Khoa của tôi" đóng-mặc-định)
- **Q1:** 4 cờ toàn viện độc lập: `SCOPE_HOSPITAL_DIRECTORY_STATS`, `SCOPE_HOSPITAL_CLINICAL_READ`, `SCOPE_HOSPITAL_FINANCE_BILLING`, `SCOPE_HOSPITAL_ARCHIVED_READ`.
- **Q2:** BGĐ/KHTH mặc định xem Cờ 1; xem chi tiết qua Break-glass. Mở tự động theo ngữ cảnh hàng đợi trình duyệt.
- **Q3:** Tách Read/Write hoàn toàn. Write chỉ mở cho khoa điều trị hiện tại + ngoại lệ hẹp (hội chẩn, gây mê, CLS, ký bù y lệnh miệng).
- **Q4:** Khoa cũ Read-only 7 ngày. Luồng Chuyển khoa 2 bước (Bàn giao–Tiếp nhận), tách `admitting_department_id` và `current_department_id`.
- **Q5:** Chạy script trên bản sao trước; màn web gán khoa phải xong trước khi bật Audit; Phòng TCCB + ĐD trưởng rà soát.
- **Q6:** Break-glass chỉ Read-only, tự đóng sau 4h, hậu kiểm KHTH+QLCL, áp dụng cả BGĐ.
- **Q7:** Audit tối thiểu 14 ngày (qua 2 kỳ trực cuối tuần) VÀ số ca bị chặn nhầm = 0. Bật Closed sáng Thứ Ba.
- **Q8:** Thu hồi cờ Developer trên Production ngay trong S2-15; ghi Audit Log 100% lượt truy cập tài khoản kỹ thuật.
- **Q9:** 72h sau khi ký biên bản hội chẩn (tham số cấu hình).
- **Q10:** Phòng KHTH+CNTT+Pháp chế/TCCB quản trị danh mục. Nhóm nhạy cảm (HIV, Trẻ em bị xâm hại, Tâm thần, VIP) áp dụng Masking ngay cả với cờ toàn viện.

Tham số `app_settings` đã chốt: xem `QUYET-DINH-S2-02-VA-S2-15-V1.md` Phần 3.

---

## 3. Trạng thái cửa sổ Claude

| Cửa sổ | Việc | Trạng thái |
|---|---|---|
| Agent 0 (tôi) | Điều phối | Đang hoạt động |
| `claude-9` | S2-02A phân tích (xong) | **Chờ chủ dự án đóng** |
| `claude-8` | S2-15A phân tích (xong) | **Chờ chủ dự án đóng** |

> ⚠️ Hiện đang có 3 cửa sổ Claude = tối đa. **Phải đóng `claude-9` hoặc `claude-8` trước khi giao việc mới.**

---

## 4. Hàng đợi (CẬP NHẬT — theo thứ tự ưu tiên)

| Thứ tự | Việc | Prompt | Worktree | Điều kiện |
|---|---|---|---|---|
| **1** | **S2-02-g** — Rà dữ liệu, soạn SQL chỉ-đọc | `PROMPT-CTRL-S2-02G.md` ✅ | `C:\wt\ctrl-base` (chỉ đọc) | Đóng claude-9 hoặc claude-8 trước |
| **2** | **S2-04A** — Phân tích `ConfirmEmergencyDeparture` chỉ-đọc | `PROMPT-CTRL-S2-04A.md` ✅ | `C:\wt\ctrl-base` (chỉ đọc) | Sau S2-02-g (xem A4#7 cùng hàm) |
| **3** | **S2-15-a** — Hợp nhất `AssignedDepartmentIds()` → `DepartmentScopeResolver` | Chưa viết | `C:\wt\ctrl-s2-15` (**chưa tạo**) | Sau 04A (giao nhau qua emergency) |
| **4** | **S2-02-a** — Cổng chặn + cờ nội trú | Chưa viết | `C:\wt\ctrl-s2j` (chưa tạo) | Sau S2-02-g |
| **5** | Nhóm J: S2-05, S2-06 | `PROMPT-CTRL-S2J.md` ✅ | `C:\wt\ctrl-s2j` (chưa tạo) | Độc lập, song song được |
| 6 | Nhóm I: S2-01, S2-03 | `PROMPT-CTRL-S2I.md` ✅ | `C:\wt\ctrl-s2i` (chưa tạo) | Độc lập |
| 7 | Nhóm K: S2-07, S2-08 | `PROMPT-CTRL-S2K.md` ✅ | `C:\wt\ctrl-s2k` (chưa tạo) | Độc lập |
| 8 | Nhóm L: S2-10, S2-12, S2-19 | `PROMPT-CTRL-S2L.md` ✅ | `C:\wt\ctrl-s2l` (chưa tạo) | Độc lập |
| 9 | Nhóm M: S2-11, S2-22, S2-20 | `PROMPT-CTRL-S2M.md` ✅ | `C:\wt\ctrl-s2m` (chưa tạo) | Độc lập |

**Lưu ý quan trọng:**
- S2-02-b (cấp cứu không tự dừng y lệnh miệng chưa ký) **phụ thuộc S2-04A** vì cùng đụng `ConfirmEmergencyDeparture`.
- S2-15 làm theo 4 bước (a→b/c/h song song→d→e→f→Audit→g→Closed), không áp một lần.
- S2-02-d1, d2, e đều cần **review độc lập** (an toàn thuốc, kho, tài chính).

---

## 5. Việc cần chủ dự án xác nhận (giữ nguyên từ bản trước + thêm mới)

1. (Mới) Chạy truy vấn SQL `s2_02_g_verbal_order_check.sql` trên bản sao/Replica khi sẵn sàng (sau khi agent soạn xong S2-02-g).
2. (Mới) Xác nhận DDL bổ sung cho S2-02 (cột nullable vào `clinical_order_verifications` và `emar_administration_logs`) trước khi giao S2-02-d2.
3. (Mới) Xác nhận cài `app_settings` cho S2-02 và S2-15 (xem Phần 3 của `QUYET-DINH-S2-02-VA-S2-15-V1.md`).
4. (Giữ) Hai việc nhỏ DDL: `MedicationReconciliationLineCommand.cs:198` (`Decision` varchar(20)↔30).
5. (Giữ) SQL cài `SignedFileMaxMegabytes` có chạy không.
6. (Giữ) 5 hàm Service ra viện + bảng sổ ngoại lệ nợ (DDL).

---

## 6. Cách mở phiên mới

1. Đóng `claude-9` (S2-02A xong, không cần giữ). Nếu muốn giữ làm song song thì đóng `claude-8`.
2. Mở cửa sổ mới → giao `PROMPT-CTRL-S2-02G.md` (worktree `C:\wt\ctrl-base`, chỉ đọc).
3. Song song hoặc kế tiếp: giao `PROMPT-CTRL-S2-04A.md` (worktree `C:\wt\ctrl-base`, chỉ đọc).
4. Sau khi có `BAOCAO-CTRL-S2-02G.md` (HOÀN TẤT): PM tổng hợp câu hỏi DDL, hỏi chủ dự án, rồi mới giao S2-02-a.
5. Tạo worktree S2-15: `git -C C:/CongViec/itc-git/HIS_EMR worktree add -b wt/ctrl-s2-15 C:/wt/ctrl-s2-15 180c20e6`.

---

## 7. Căn cứ pháp lý đã đối chiếu (từ QUYET-DINH-S2-02-VA-S2-15-V1.md)

Tài liệu quyết định đã đối chiếu và ghi rõ hiệu lực tại VN tháng 11/2026:
- TT 13/2025/TT-BYT (HSBA điện tử, thay TT 46/2018)
- TT 31/2021/TT-BYT + QĐ 6858/QĐ-BYT (y lệnh miệng, điều dưỡng)
- TT 43/2018/TT-BYT (sự cố y khoa)
- TT 18/2026/TT-BYT + NĐ 163/2025/NĐ-CP (thuốc kiểm soát đặc biệt, gồm Etomidate)
- TT 23/2011/TT-BYT (tủ trực cấp cứu)
- QĐ 130/QĐ-BYT sửa đổi lần cuối bởi QĐ 1931/QĐ-BYT (XML BHYT)
- NĐ 188/2025/NĐ-CP (xác thực điện tử BHYT từ 01/01/2026)
- Luật 15/2023/QH15 (khám chữa bệnh)
- Luật 91/2025/QH15 (bảo vệ dữ liệu cá nhân, hiệu lực 01/01/2026)
