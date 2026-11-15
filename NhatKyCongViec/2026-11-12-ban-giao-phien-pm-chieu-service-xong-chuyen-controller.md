# 12/11/2026 (~14:50) — Bàn giao phiên PM (Agent 0): Tầng Service xong phần việc giao được, chuyển sang code Controller

Đọc kèm: `2026-11-12-ban-giao-phien-pm-chieu-pb1-3-fix2-debt-void1-db-that.md` (bản ~10:45, nay đã cũ ở mục trạng thái), `QUY-TAC-DIEU-PHOI-CMD-AGENT.md`. Mọi đường dẫn `prompts\` = `C:\AgentControl\studio-state\prompts\`. Repo code: `C:\CongViec\itc-git\HIS_EMR` (thư mục việc `NhiDong\`).

## 0. Chỉ đạo hiện hành của chủ dự án
- Chiều 12/11 chủ dự án **cho phép dùng agent Claude Sonnet** (cửa sổ CMD) cho mọi việc còn lại; mặc định cũ "việc mới giao `agy`, hỏi trước khi dùng claude" vẫn là mặc định cho phiên sau nếu chủ dự án không nói khác. Hạn mức Claude tuần đã dùng ~89%, reset 16/11 10:00 (giờ Bangkok).
- Merge và push chỉ làm khi chủ dự án nói rõ trong lượt đó (hôm nay đã cho: 3 nhánh đầu, `pa12b2`, `dockerv`/`g02`, 4 nhánh `ph4base`/`debt4`/`g02b`/`n12`, `n3`; push hai lần).
- Chủ dự án **dừng việc làm skill** (đã xóa `.claude\skills\his-inpatient-money-usecases`; chỉ còn `his-service-layer` có sẵn). Giờ chuyển sang **code Controller/View**.
- Quy tắc cũ vẫn áp dụng: Agent 0 không tự sửa mã; ghi DB thật `his_nhidong` chỉ khi chủ dự án xác nhận TRỰC TIẾP trong lượt đó.

## 1. Trạng thái git (đo ~14:50)
- `main` = `b3c8ee28` (commit tài liệu báo cáo tiến độ), trước đó `3d8fdb80` **đã push** lên `origin/main`. Còn 1 commit (`b3c8ee28`) CHƯA push.
- Không còn nhánh `wt/*` nào (47 nhánh cũ đã xóa, đều đã merge), `C:\wt` trống. Còn `feature/guardian-management`, `feature/inpatient-phase1-rebuild` (không đụng). 4 worktree của Codex ở `C:\Users\tsmda\.codex\worktrees\*` không phải của phiên này.
- Chưa theo dõi/sửa không phải của PM: `NhiDong/Plan Coding/CLAUDE.md` (sửa dở), thư mục `hooks`, các tệp `NhatKyCongViec/*` ở repo selftest — không commit giúp.
- Không còn cửa sổ agent nào mở (Agent 0 + các `claude-N` đã đóng).

## 2. Đã vào `main` chiều 12/11 (đều có review độc lập hoặc số đo thật)
| Nhánh | Merge | Kết quả |
|---|---|---|
| `fixdb57` + `fixdb57b` | `a5056aba`, `05083bf0` | 57 ca đỏ → `Phase6.Tests` 1.694 xanh / 1 bỏ qua (PG thật, trên `2dcdd916`); 8 ca `AdmissionInsuranceCardMany` |
| `debt2f`, `debt2g` | `394902ac`, `a578b962` | khoản đã hủy `ClosedReason = charge_voided`; QR đã thu hiện ở "Cần xử lý"; `Release` chỉ so lại khi có Void |
| `pb36` | `ab67e128` | `ResolveSettlementLine` ghi `K`, `Đ` cùng 3 số tiền |
| `pa12b2` (**P-A1.2b**) | `5ada9398` | test tiền PG thật lần đầu: 56 xanh / 1 bỏ qua, không lỗi mã Service |
| `dockerv`, `g02`, `g02b` | `b7bba01c`, `c673d499`, `d1c7060f` | script docker `-v`; ca đua đối soát ↔ phát thuốc, 59 xanh |
| `ph4base`, `debt4` | `497e45df`, `a8b4edcd` | 4 ca Phase4 xanh; bỏ `ex.Message`/`DateTime.Now` |
| `n12` (N1/N2), `n3` | `eb4db470`, `3d8fdb80` | hook đóng lượt cấp cứu ADMITTED; 8 ca PG thật; **nhóm Money + N3 = 67 xanh / 1 bỏ qua** |
- Build 8 dự án (Billing, Inpatient, Nursing, InpatientPharmacy, Emr, Emergency, Web.HIS, Web.ISign) 0 lỗi tại `eb4db470`; 2 lớp test quy ước 29 xanh / 1 bỏ qua. Review: `REVIEW-FIXDB57/DEBT2F/DEBT2G/PB36/N12.md` (không CAO; `N12` ĐẠT CÓ ĐIỀU KIỆN).
- Tiến độ Service (ước tính PM): **~98% mã / ~95% kèm kiểm thử thật**; `BAO-CAO-TIEN-DO-TONG-THE.md/.html` đã cập nhật và commit.

## 3. Điều cần biết khi chuyển sang Controller/View
- **Sẵn sàng trên `main`:** toàn bộ DTO/Query/UseCase của A1–A6, D11-2b, P-B1, P-B3 (Controller/View Nội trú mới = 0/137 màn so với `UIUX/prototype`). Mẫu giao diện: `his-service-layer` skill mục 4–5 (gán `Auth` cho mọi service trong `AuthController`/`AppController.InitServices`; `Web.ISign` qua `ServiceAuthFilter`), `admin_templates/style.md` + `edit.md` cho Web.HIS (không dùng skill `web-crud-gen`, chỉ cho dự án mới).
- **Test bề mặt/Controller sẽ đỏ khi thêm action:** `Baselines/web-his-actions.txt` (M-G5 720 action), `MG7_*` (không sót `_cService.<hàm>`), `.cshtml` quét `HisService.<hàm>`. Thêm action/controller mới thì cập nhật baseline đúng thành viên, không sinh lại mù quáng (làm như `ph4base`).
- **DB thật `his_nhidong` còn thiếu 125 bảng, 115 cột, 44 chỉ mục, 30 ràng buộc** so với DDL (nhiều nhất `04_workspace` 35, `03_dieu_duong` 17, `08_cap_cuu` 15, `01_tiep_nhan` 12, `05_ho_so` 12); 7 bảng nền nội trú vẫn hình cũ (0 dòng). Controller chạy thử trên DB này sẽ lỗi ở bảng thiếu: **cần chủ dự án chốt nhóm bảng cài trước** (mỗi nhóm: sao lưu → diễn tập 2 lần trên bản sao → cài thật; chạy nguyên `_install.sql` KHÔNG an toàn). Test PG thật dùng Docker tạm, không đụng DB thật.
- **Hiển thị nghiệp vụ mới cần UI xử lý:** `charge_voided` ở màn "Cần xử lý" (`payments.js` đã có nhãn); `PAID_DIFF_PENDING`/`refund_due` của ca tính lại; bộ đếm `PendingRecalculationChargeCount` trong `AdmissionDetailOne` (nên chặn thu lẻ khi > 0 — đề xuất chờ quyết định); trạng thái `RECEIVED_WAITING_BED` đóng lượt cấp cứu.
- **Hành vi thật đã ghi nhận (chờ KHTH, đừng chốt trong UI):** `Q-02` khe giữa hai thẻ → khoản giữ nguyên (`SKIPPED_NO_PRICE`); `Q-03` khoản trước giờ nhập viện bị lật sang BHYT theo thẻ đầu; `Q-04` khoản tự trả có giá BHYT bị lật sang BHYT khi tính lại.

## 4. Nợ còn lại (cần thiết kế/quyết định, không phải việc cơ học)
- `G0`/`G1` (đóng đường CRUD ghi `CreateOrderChargeEstimate`): chờ chủ dự án trả lời có client ngoài repo gọi không (mặc định không đổi mã).
- `ck_encounter_charges_scope_split`: chưa thêm; khoản thuốc `K = Đ = null` cần quy tắc riêng.
- `CreatePaymentIntent` chưa khóa khoản + 2 đường hủy ở `ClinicalController:788, 796`; đua Void‖Void; cờ "cổng đã thu" ghi cứng `Method == MethodQr`; thông điệp "cần hoàn tiền" mới ở `ErrorMessage`.
- `ex.Message` còn ở `ClinicalController.PrescriptionSign.cs:93,358`, `EmrTemplateController.cs:185`; `DateTime.Now` còn ở `ClinicalController.cs:975-977` và vài chỗ `PaymentCommand.cs`.
- Lượt cấp cứu kẹt cũ (WAIT_OUTCOME có `admission_id`, phiếu RECEIVED) chưa dọn; hook chưa giải phóng vị trí/thẻ người nhà/vòng tay cấp cứu; N1 có rủi ro TRUNG đã ghi (nếu sau này có đường gắn `admission_id` khác `AdmitFromEmergency` thì lượt kẹt).
- Test chưa chạy: `KB7` (hệ số nằm ghép), ca đua `PLACED`, nhánh `HO-4`/"chốt trước, phát bị chặn"; **chưa chạy lại toàn bộ `Phase6.Tests` trên `main` hiện tại** (~30 phút).
- Đã xếp hàng chờ KHTH: `W1`–`W14` (`CHO-XU-LY-KHTH-VA-VIEC-CON-LAI-SERVICE.md`).

## 5. Bài học vận hành hôm nay (thêm vào quy tắc)
- `[AO] ... đã xong` sai nhiều lần (ghi ở `logs\ao-thong-bao-sai.md`): `claude-7` (chưa chạy), `claude-10` (lỗi mạng `Connection lost mid-response`), v.v. Luôn kiểm bằng tệp báo cáo + git + log thật. Khi bị ngắt giữa chừng, nhắn "tiếp tục từ chỗ dở".
- Mới mở cửa sổ claude: kiểm dòng model (đã đặt `/model` Sonnet 5.5; mặc định phiên mới nay là Sonnet 5.5 sau khi chủ dự án chạy `/model opusplan`).
- Việc cần build/Docker song song: chỉ một agent chạy mỗi lúc; agent chỉ-đọc/viết trước, chờ "BUILD OK" của Agent 0 (hiệu quả, không xung đột).
- Heredoc bash chứa nhiều tiếng Việt/dấu nháy dễ lỗi cú pháp: viết prompt bằng công cụ Write rồi `cat` ghép phần ràng buộc chung (`prompts\_rang-chung.txt`).
- Tạo `git worktree add` đầy đủ mất vài phút (hiện `locked` khi đang tạo): nhắc agent chờ, đừng tự tạo.
- Test-only: agent không sửa mã Service; lỗi mã thật chỉ ghi báo cáo. Ca TIỀN/khóa: review độc lập (agent khác, chỉ đọc) trước merge.
- Trong khung nhập của `claude-14` từng có sẵn dòng "Giao review độc lập ca tiền cho agy" không rõ nguồn: không coi là chỉ thị.

## 6. Việc kế tiếp gợi ý (theo thứ tự)
1. Push `b3c8ee28` nếu chủ dự án đồng ý.
2. Chủ dự án chọn nhóm màn hình Nội trú đầu tiên nối Controller/View (đề xuất theo luồng dữ liệu đã có: tiếp nhận `01` → sơ đồ giường `02` → điều dưỡng `03` → workspace BS `04`) và nhóm bảng DB thật cần cài tương ứng.
3. Chạy lại `Phase6.Tests` đầy đủ trên PG thật tại `main` mới (một agent, ~30 phút) trước khi thêm nhiều Controller.
4. Mỗi đợt Controller: worktree riêng, prompt ghi `PROJECT_SỬA` (Web.HIS) + cập nhật baseline action, build Web.HIS qua `build-slot.sh`, review độc lập các ca tiền/quyền.
