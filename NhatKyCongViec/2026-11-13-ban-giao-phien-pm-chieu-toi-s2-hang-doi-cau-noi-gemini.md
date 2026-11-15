# Bàn giao phiên PM (13/11 chiều tối): đợt S2 Service, hàng đợi việc kế tiếp, cầu nối Gemini web, skill `web-crud-gen`

Đọc kèm (theo thứ tự): `2026-11-13-ban-giao-phien-pm-ke-hoach-controller-toan-bo-man-hinh.md` (mục 0–14; mục 12–14 là cập nhật cùng ngày), `2026-11-12-gemini-web-bridge.md`, `2026-11-13-gemini-bridge-fix.md`.
Mọi đường dẫn `prompts\` = `C:\AgentControl\studio-state\prompts\`. Repo công cụ (phiên này chạy ở đây): `C:\CongViec\agent\agent-orchestrator`. Repo code: `C:\CongViec\itc-git\HIS_EMR` (thư mục việc `NhiDong\`). Tài liệu kế hoạch Controller: `C:\CongViec\itc-git\HIS_EMR\NhiDong\Plan Coding\Controller\`.

## 0. Chỉ đạo hiện hành của chủ dự án (đọc đầu tiên)
- **Tối đa 3 cửa sổ Claude đồng thời, tính cả Agent 0** (tức chỉ 2 agent Claude làm việc cùng lúc). Chủ dự án đã tự dừng `claude-10` khi tôi mở quá số này. Không mở thêm khi chưa có agent xong và đóng.
- Giao việc cho Claude khi chủ dự án nói rõ (lệnh gần nhất: "cho claude làm việc tiếp cho xong s2"). Chủ dự án từng nói "dừng giao việc cho claude" rồi mở lại: **luôn theo lệnh mới nhất**; nghi ngờ thì hỏi.
- Không push, không merge vào `main`. Mọi commit nằm trên nhánh worktree `wt/*`. **Không `git checkout/reset/stash/clean`** (ngoại lệ hẹp đã dùng ở S2E/S2F/S2H: một lệnh `git restore` cho tệp DDL được chứng minh giống hệt `HEAD`).
- Không ghi lên DB thật (`his_nhidong` hoặc DB nào khác); chỉ Postgres tạm qua `run-with-temp-postgres.sh`. Việc chạm `Database/**` hoặc cần DDL mới phải có chủ dự án đồng ý.
- Agent 0 (tôi) chỉ điều phối: không tự sửa mã thay agent (kể cả mã của công cụ `agent-orchestrator`); việc sửa mã giao agent.
- `gemini_web-1` là cửa sổ thử của chủ dự án; chỉ gửi vào khi chủ dự án yêu cầu (mỗi lần gửi được hỏi xác nhận).

## 1. Trạng thái nhánh (đo 13/11 ~14:40)
| Worktree | Nhánh | HEAD | Nội dung | Cây |
|---|---|---|---|---|
| `C:\wt\ctrl-s1` | `wt/ctrl-s1` | `180c20e6` | S1 vòng 3 + toàn bộ S2 đã nghiệm thu bên dưới | sạch |
| `C:\wt\ctrl-s2d` | `wt/ctrl-s2d` | `fbf2de37` | S2-09 (từ `b63d2cbc`) | sạch |
| `C:\wt\ctrl-base` | `wt/ctrl-base` | `a2a23e37` | nền đợt 1 (T0 + S1 vòng 2) | sạch |
| `C:\wt\ctrl-t0` | `wt/ctrl-t0` | `3eb51516` | T0 | sạch |
- **Chưa nhánh nào vào `wt/ctrl-base` hay `main`.** `ctrl-s1` đi trước `ctrl-base` (S1 vòng 3 và mọi commit S2). Việc gộp là của agent và chỉ khi chủ dự án nói "bắt đầu viết Controller" hoặc yêu cầu riêng. HIS_EMR `main` = `b3c8ee28`, không đổi.
- `ctrl-s2d` rẽ từ `b63d2cbc`, **chưa có** các commit S2C/S2E/S2F/S2H của `ctrl-s1`; khi gộp cần xử lý thứ tự.

## 2. Đợt S2: việc đã nghiệm thu (PM đọc diff thật + tự chạy lại test)
Chuỗi commit trên `wt/ctrl-s1` (cũ → mới): `475f423d` S2-14 · `7c2ca73c` S2-16 · `2fb6298c` S2-17 · `83cf6164`, `b63d2cbc` S2-17 vòng 2 (trần dung lượng vào `app_settings`) · `8066a76b` S2C-1 · `c0b3b861` S2C-2 · `f935baa7` S2C-3 · `f93c4a83` S2E · `9967735d` S2F · `180c20e6` S2H. Trên `wt/ctrl-s2d`: `fbf2de37` S2-09.
| Việc | Kết quả | Báo cáo (`prompts\`) |
|---|---|---|
| S2-14 | Phiếu đối chiếu thuốc lùi `PARTIAL` ("Một phần", hiển thị "Đang làm") khi huỷ chữ ký do sửa/thêm/xoá đính kèm, qua `ApplyTransition` | `BAOCAO-CTRL-S2A.md` |
| S2-16 | `PatientWristbandMany` khoá `[Obsolete(error: true)]` (không còn nơi gọi) | S2A |
| S2-17 | `SignedFileUpload` (`Service.Utility2`): PDF/PNG/JPG theo magic bytes, tên server đặt; trần dung lượng đọc từ `app_settings` tab `Inpatient` mục `SignedFileMaxMegabytes` (mặc định 10, hợp lệ 1..50, ngoài khoảng ⇒ 10); `InpatientService.ValidateSignedFile(IFormFile?)` cho Controller. **Chưa có Controller gọi.** SQL đặt giá trị nằm ở `BAOCAO-CTRL-S2B.md` mục 3 (chưa chạy; chưa thấy DDL gốc `app_settings`) | `BAOCAO-CTRL-S2A.md`, `BAOCAO-CTRL-S2B.md` |
| S2C-1 | `PatientWristbandOne`/`PatientWristbandBaseList` kiểm quyền xem + lọc khoa (`GetWristbandAllowedDepartmentIds`); ca ghi dùng hàm đọc lại nội bộ | `BAOCAO-CTRL-S2C.md` |
| S2C-2 | `recon_status` `varchar(20)→varchar(30)` ở nguồn sinh (`defs/d01_tiep_nhan.py`), DDL, `tables.json`, entity, script `DBContexts/DBContext.HIS/Migrations/WidenMedicationReconciliationsReconStatus_Postgres.sql` (idempotent, đã chạy thử **chỉ trên Postgres tạm**; **chưa chạy trên DB nào khác**) | S2C |
| S2C-3 | `OBSOLETE_METHODS` trong `Database/_tools/service_overrides.py` + 1 dòng ở `gen_service.py`: `[Obsolete]` của `PatientWristbandMany` không mất khi sinh lại | S2C |
| S2E | `MedicationReconciliationCommand.cs:84` "tối đa 30 ký tự"; `gen_service.py --compare` KHỚP 4 tệp; dọn 183 tệp DDL bẩn (giống hệt HEAD, chỉ khác xuống dòng) bằng một `git restore` hẹp | `BAOCAO-CTRL-S2E.md` |
| S2F + S2H | `Database/_tools/gen.py` chọn kết thúc dòng theo `core.autocrlf` (true ⇒ CRLF, còn lại LF); chạy ghi thật nhiều lần không làm bẩn cây | `BAOCAO-CTRL-S2F.md`, `BAOCAO-CTRL-S2H.md` |
| S2-09 | `EmrRecordMany` + `SearchEmrRecordModel.AdmissionId` (3 dòng + test). **Chỉ trả hồ sơ ngoại trú** (`DocumentTypeOutpatient`). Chủ dự án chốt **hướng (a)**: hồ sơ nội trú của đợt dùng `AdmissionRecordTreeMany` | `BAOCAO-CTRL-S2D.md`, `QUYET-DINH-S2-09-HO-SO-NOI-TRU-V1.md` |
| S2-13 | Chỉ phân tích, **chưa viết mã**: chưa có mẫu phiếu của bệnh viện, chưa rõ có cần giá tiền; nếu mẫu chỉ cần tên thuốc/liều/đường dùng/giờ/trạng thái thì Controller gọi `MedicationAdministrationMatrixOne` (1 ngày) rồi dựng View HTML, không cần hàm mới; PDF để sau (S2-12) | S2D |
| S2-18 | Phân tích chỉ-đọc các bước ra viện + cổng. Quyết định Q1–Q6 "theo đề xuất": ghi ở `QUYET-DINH-S2-18-RA-VIEN-Q1-Q6-V1.md` (Service đã đúng chiều ở bước ký; mockup/đặc tả sai chiều; thiếu 5 hàm; cần bảng sổ ngoại lệ nợ, DDL mới chưa cài) | `BAOCAO-CTRL-S2-18.md` |
Test chạy lại gần nhất trên `ctrl-s1`: 74 đạt, 0 lỗi, 1 bỏ qua (`ServiceConventionTests.T11c_...`, vốn đã bỏ qua). **Chưa chạy cả bộ Phase6, chưa build cả solution.**

## 3. Đang chạy khi ghi bản này (CHƯA nghiệm thu, đừng coi là xong)
- `claude-8` (Sonnet 5.5): `PROMPT-CTRL-S2-15A.md`, **phân tích chỉ-đọc S2-15** ("khoa của tôi" đóng-mặc-định toàn hệ thống). Báo cáo đích: `BAOCAO-CTRL-S2-15A.md` (chưa có).
- `claude-9` (Sonnet 5.5): `PROMPT-CTRL-S2-02A.md`, **phân tích chỉ-đọc S2-02** (y lệnh miệng). Báo cáo đích: `BAOCAO-CTRL-S2-02A.md` (đã thấy tệp dở 9 dòng lúc 14:37; chưa có dòng `HOÀN TẤT`).
- Khi nhận `[AO] ... đã xong`: **luôn kiểm báo cáo có dòng `HOÀN TẤT` và `git log`** (thông báo hay báo sớm, nhất là khi agent chạm giới hạn 5 giờ; hạn mức làm mới thì agent chờ Enter, nhắc một dòng).
- Nghiệm thu: đọc báo cáo, đối chiếu tên hàm/tệp/mã với mã thật (grep), đọc diff, chạy lại test chính; chỉ khi đạt mới đóng cửa sổ.

## 4. Hàng đợi (chưa giao; giao tuần tự khi có chỗ, tối đa 2 agent làm việc cùng lúc)
| Thứ tự | Việc | Prompt (đã viết) | Worktree |
|---|---|---|---|
| 1 | S2-04A phân tích chỉ-đọc `ConfirmEmergencyDeparture` (A-D5-2; bắt buộc review độc lập trước khi sửa) | `PROMPT-CTRL-S2-04A.md` | đọc `C:\wt\ctrl-base` |
| 2 | Nhóm J: S2-05 (trẻ sơ sinh chưa tên), S2-06 (`CancelEncounter`) | `PROMPT-CTRL-S2J.md` | `C:\wt\ctrl-s2j` (**chưa tạo**) |
| 3 | Nhóm I: S2-01 (hết giường lúc nhận), S2-03 (ca đêm chờ bàn giao) | `PROMPT-CTRL-S2I.md` | `C:\wt\ctrl-s2i` (chưa tạo) |
| 4 | Nhóm K: S2-07 (`ReviewLabResult`), S2-08 (gom lô xét nghiệm, N+1) | `PROMPT-CTRL-S2K.md` | `C:\wt\ctrl-s2k` (chưa tạo) |
| 5 | Nhóm L: S2-10 (số lưu trữ EMR), S2-12 (PDF dùng chung), S2-19 (mở khoá hồ sơ; có thể cần DDL) | `PROMPT-CTRL-S2L.md` | `C:\wt\ctrl-s2l` (chưa tạo) |
| 6 | Nhóm M: S2-11 (scan biên bản tiêu huỷ; có thể cần DDL), S2-22 (`Reserved`), S2-20 (chỉ phân tích) | `PROMPT-CTRL-S2M.md` | `C:\wt\ctrl-s2m` (chưa tạo) |
- Tạo worktree ngay trước khi giao: `git -C C:/CongViec/itc-git/HIS_EMR worktree add -b wt/ctrl-s2X C:/wt/ctrl-s2X 180c20e6` (mỗi worktree ~23k tệp, mất ~1 phút). Các prompt I–M do script `scratchpad\gen_s2_prompts.py` sinh (phiên này); sửa prompt thì sửa trực tiếp tệp `prompts\PROMPT-CTRL-S2*.md`.
- Mỗi nhóm tự quyết "làm hoặc dừng": chỉ viết mã khi việc rõ, không cần quyết định của chủ dự án, không cần DDL, không đổi quyền/hành vi lâm sàng theo cách chưa chốt. Dừng đúng chỗ cần quyết định là đúng.
- Sau mỗi phân tích S2-15A/02A/04A: tôi tổng hợp **đề xuất xử lý** (đã hứa với chủ dự án: "phân tích kỹ theo nghiệp vụ bệnh viện Việt Nam, đưa đề xuất rồi xử lý"), trình chủ dự án quyết, rồi mới giao viết mã (S2-02, S2-04 cần review độc lập; S2-15 làm theo 4 bước, không áp một lần).
- **Chưa đưa vào hàng đợi:** S2-15 (chờ phân tích), S2-23 (phụ thuộc S2-15), S2-21 (ghi `permission_group_features`, **cần chủ dự án xác nhận ghi DB**).

## 5. Câu hỏi/quyết định đang chờ chủ dự án
1. Hai việc nhỏ DDL: `MedicationReconciliationLineCommand.cs:198` (`Decision` tối đa 20, chưa đối chiếu DDL); tài liệu sinh `gen_docs.py` (`README`, `mo-ta-thuoc-tinh.csv`, `so-do-quan-he.html`) còn ghi `varchar(20)`; script cài cũ `Migrations/Inpatient_W1_TiepNhanGiuong_Postgres.sql:1029` còn `varchar(20)`.
2. `PatientWristbandMany` đã khoá; `Create/EditPatientWristband` (CRUD khung) vẫn không kiểm quyền ghi (ngoài phạm vi).
3. Sửa tài liệu D7 (`KE-HOACH-CONTROLLER-D7-*.md` dòng 152 và 706: bỏ yêu cầu `EmrRecordMany` trả tên khoa/mã đợt nội trú) và D6 (trạng thái cuối mã là `SETTLED`, tài liệu ghi `CLOSED`); sửa mockup/đặc tả ra viện (xem `QUYET-DINH-S2-18-...-V1.md`): chưa làm.
4. SQL đặt `SignedFileMaxMegabytes` có chạy không (không bắt buộc, đã có mặc định).
5. 5 hàm Service ra viện + bảng sổ ngoại lệ nợ (DDL): chưa giao; DDL cần chủ dự án xác nhận cài.
6. Các câu còn lại của kế hoạch Controller: xem mục 8 của bản bàn giao trước (7 câu mới ở mục 7 của `DANH-GIA-QUYET-DINH-...`, gán lại nhãn 23 action, gộp trùng C-1, 4 modal chưa phủ `mdDcMed`, bảng DB theo đợt, kế hoạch viết mã theo đợt).

## 6. Cầu nối Gemini web (`gemini_web-1`, công cụ của chủ dự án)
- **Đã kiểm:** mức 1 (đọc `docs/UI-RULES.md` đúng 3 ý), mức 2 (tạo tệp mới `tmp/gemini-test-ghi.md`, 66 byte, khớp từng ký tự; đã xoá) đạt.
- **Lỗi gốc "Gemini không nhận câu lệnh":** `browser_extension/content_gemini.js` chỉ chờ nút gửi ~2,3 giây rồi rơi sang Enter giả. Đã sửa (`BAOCAO-GEMINI-SEND-FIX.md`; tệp hiện ~332 dòng; chờ rảnh 15 giây, chờ nút 12 giây, loại nút dừng/mic/thêm tệp, báo "nút gửi bị khoá", thử bấm lại đúng 1 lần có chốt chặn gửi trùng; thông báo lỗi kèm nhãn nút gần ô soạn tin). `node --check` đạt; `tests/gemini_send_sim.cjs` 8/8 đạt; `tests.test_gemini_bridge` 12 đạt. **Không commit** (các tệp `browser_extension/`, `docs/GEMINI-WEB.md`, `tests/gemini_send_sim.cjs`, `tests/test_gemini_bridge.py`, `agent_orchestrator/gemini_bridge.py` là tệp chưa theo dõi của chủ dự án).
- **Một phiên không nằm trong danh sách terminal** đã ghi đè `content_gemini.js` (166→284 dòng) và từng ghi đè báo cáo S2-SEND-FIX bằng bản sai trong lúc agent làm; chưa rõ nguồn.
- **Chủ dự án đã nạp lại extension và xác nhận "Gemini chạy ổn".** Sau đó mức 3 (bản rút gọn S2-04A với `tmp/s2-04/`, 4 tệp chép chỉ đọc) **chưa đạt**: cầu nối qua được lượt 3–7 (cải thiện rõ), nhưng Gemini đọc lại các đoạn chồng lấn của tệp 02 (617 dòng) và ở lượt 8 báo `Không tìm thấy nút gửi sau 12 giây ... Nhãn các nút gần ô chat: []`. Nghi: khi chữ rất dài, giao diện Gemini đổi (khối "văn bản đã dán" hoặc thanh nút thay đổi) làm cách tìm nút theo vùng ô soạn tin không còn tác dụng; **chưa xác nhận**, cần chủ dự án nhìn tab Gemini/DevTools lúc lỗi.
- **Việc kế tiếp đề xuất:** (1) chia nhỏ `tmp/s2-04/` thành các tệp dưới ~150 dòng và dặn không đọc lại đoạn đã đọc; (2) giao agent sửa `agent_orchestrator/gemini_bridge.py` để giới hạn kích thước kết quả công cụ mỗi lượt (vài KB, kèm "đọc tiếp từ dòng N"). Giới hạn 12 lượt/phiên; mẹo: gõ `/new` rồi gửi lại khi lỗi; `/tools` đang bật. Báo cáo từ model nhỏ **luôn** phải đối chiếu tên hàm với mã thật.
- `tmp/s2-04/` còn trong repo công cụ (chưa xoá).

## 7. Skill dùng chung `web-crud-gen` (đã nâng cấp, xem mục 12 bản bàn giao trước)
`C:\Users\tsmda\.claude\skills\web-crud-gen\` (sao lưu: `C:\AgentControl\studio-state\skill-backup\web-crud-gen-20261113`): đóng-mặc-định (cookie auth + FallbackPolicy), `web.policyPrefix`, `verify_web.py`, `inventory_ui.py`, hai test mẫu (biên dịch sạch, **chưa chạy `dotnet test`**), hai tài liệu mới (`authorization-and-safety.md`, `planning-from-mockups.md`). `verify_web.py` đã chạy chỉ-đọc trên Web.HIS: 840 tên hàm, 0 hàm không tồn tại, 41 URL trong JS cũ không có action (chưa xem từng cái). `smoke_test.py` chưa chạy lại sau thay đổi.

## 8. Bài học vận hành (quan trọng)
1. **Ô nhập của cửa sổ agent có thể còn chữ nháp của chủ dự án** (đã gặp ở `claude-3`, `claude-7`): đọc terminal trước khi gửi; gõ vào sẽ dính vào nháp. Đặt câu "Việc mới, BỎ QUA mọi chữ đứng trước câu này" ở đầu dòng khi không chắc. Không xoá được nháp bằng `send_to_terminal`.
2. `[AO] đã xong` có thể sai: agent chạm giới hạn 5 giờ thì cửa sổ yên lặng; đã gặp. Luôn kiểm báo cáo, `git log`, `git status`.
3. Cửa sổ Claude mới có thể mở với `Opus Plan`: kiểm dòng model, gõ `/model claude-sonnet-5-5` nếu cần.
4. Sleep dài trong Bash bị chặn: chờ bằng `run_in_background` rồi đọc lại.
5. Khi hai phiên cùng sửa một tệp hoặc cùng ghi báo cáo, agent có thể bị lệch: kiểm `ls -la --time-style=full-iso` và nội dung báo cáo so với kết quả tự chạy.
6. Bộ sinh `gen.py` đã ghi lại tệp SQL khi chạy; giờ chọn CRLF/LF theo `core.autocrlf`. Hai tệp (`medication_reconciliations.sql`, `_tools/tables.json`) từng hiện ` M` dù băm khớp HEAD, **nguyên nhân chưa xác định**.
7. Phân tích nghiệp vụ bệnh viện Việt Nam: mọi viện dẫn quy định ghi "chưa đối chiếu văn bản gốc"; không bịa số hiệu; không hardcode.

## 9. Cách mở phiên mới
1. `get_orchestration_rules`, `list_terminals`. Nhớ giới hạn 3 cửa sổ Claude.
2. Đọc báo cáo `BAOCAO-CTRL-S2-15A.md`, `BAOCAO-CTRL-S2-02A.md` (nếu có `HOÀN TẤT`), kiểm bằng grep, nghiệm thu, đóng cửa sổ xong việc.
3. Giao tiếp theo hàng đợi mục 4 (mỗi lần một cửa sổ, tạo worktree trước). Với S2-15/02/04: tổng hợp đề xuất, hỏi chủ dự án, rồi giao viết mã.
4. `git -C C:/wt/<w> log --oneline -5` và `git status --short` của `ctrl-s1`, `ctrl-s2d` để biết thực trạng.

## 10. Chưa kiểm / giới hạn
- Chưa chạy cả bộ Phase6, chưa build cả solution; mọi số test là lọc theo lớp.
- Cầu nối Gemini: chưa biết nguyên nhân thật của lỗi lượt 8 (chữ dài?); chưa thử sửa tệp có sẵn qua Gemini.
- S2-18: chưa kiểm dữ liệu `emr_sign_workflows` của mẫu giấy ra viện trên DB thật, `specs\workspace-*.md` (tab Ra viện) chưa đọc.
- Tên hàm ở "5 hàm Service ra viện" là đề xuất, chưa có trong mã.
- DDL mới (bảng sổ ngoại lệ nợ, có thể cả S2-11/S2-19) chưa viết, chưa cài; DB thật `his_nhidong` còn thiếu 125 bảng (theo bản bàn giao trước), **chưa cài gì**.

## 11. CẬP NHẬT (13/11 ~14:45): báo cáo phân tích S2-02 (y lệnh miệng) đã xong — chỉ ghi lại, CHƯA xử lý

Theo lệnh chủ dự án ("chỉ ghi lại báo cáo không làm gì thêm"): PM **chỉ ghi nhận**; chưa trả lời E1–E10, chưa giao việc viết mã, chưa đóng cửa sổ `claude-9`.

- **Nguồn:** `claude-9` (Sonnet 5.5), `PROMPT-CTRL-S2-02A.md`, phân tích chỉ-đọc trên `C:\wt\ctrl-base` (HEAD `a2a23e37`, cây không đổi, không kết nối DB). Báo cáo gồm 4 tệp trong `prompts\`: `BAOCAO-CTRL-S2-02A.md` (tóm tắt + mục A hiện trạng), `-2.md` (B nghiệp vụ, 12 tình huống), `-3.md` (C phương án), `-4.md` (D kế hoạch, E 10 câu hỏi, F căn cứ pháp lý); có dòng `HOÀN TẤT`.
- **PM đã đối chiếu 5 phát hiện chính với mã thật (grep/đọc, đều khớp):** (1) `RecordVerbalOrder` tạo y lệnh `ACTIVE`, `SourceMode = Verbal`, `SignedBy = null` (`RecordVerbalOrderCommand.cs:230,321,336,341`); (2) `DispenseInpatientOrder` đòi `Active` và `SignedBy` có giá trị, mã lỗi `ORDER_NOT_ACTIVE_OR_UNSIGNED` (`DispenseInpatientOrderCommand.cs:309-313`) nên thuốc dùng theo y lệnh miệng chưa ký không cấp được từ tủ trực; (3) cổng `UNFINISHED_CLINICAL_ORDERS` ở `ApproveSettlement` có đếm `Verbal & Pending` (`ApproveSettlementCommand.cs:508`); (4) `ConfirmEmergencyDeparture` tự chuyển y lệnh Draft/Active/Paused sang `Cancelled`/`Discontinued` (`...ConfirmEmergencyDepartureCommand.cs:379-396`, không xét y lệnh miệng chưa ký); (5) `RecordVerbalOrder` không tra cờ `IsSpecialControl` (grep = 0). **Chưa đối chiếu** các phát hiện còn lại (A2 eMAR, A3 kho, A5 cờ quá hạn) và phần suy luận [S].
- **Sáu điều quan trọng (theo báo cáo):** Cấp cứu không có y lệnh miệng dạng `clinical_orders` (chỉ `emergency_urgent_actions`, văn bản tự do); ghi nhận y lệnh miệng đã sinh sẵn y lệnh ACTIVE + lịch + việc điều dưỡng "chờ làm", nếu bước ký lại sinh thêm dòng "Đã thực hiện" thì **trùng liều**; cấp từ tủ trực chỉ chạy sau khi ký; cổng ra viện chỉ có ở `ApproveSettlement`; `ConfirmEmergencyDeparture` tự dừng y lệnh chưa ký (bản ghi xác nhận kẹt `PENDING`); test hành vi y lệnh miệng = 0.
- **Đề xuất của agent (CHƯA được chủ dự án xác nhận, chưa phải quyết định):** ghi "đã thực hiện" ngay lúc điều dưỡng ghi nhận, bước ký chỉ đối chiếu và liên kết (hướng (b) của E1); agent hiểu "sinh/liên kết khi ký" theo nghĩa "liên kết". Kế hoạch 8 bước: S2-02-g (rà dữ liệu thật bằng truy vấn đếm, chỉ đọc), -a (cổng + cờ nội trú, nhỏ–vừa), -b (cấp cứu không tự dừng y lệnh miệng chưa ký + cổng rời; **cần review độc lập**, giao nhau với S2-04), -d1 (loại thuốc kiểm soát đặc biệt + người chứng kiến; **review độc lập**), -d2 (ghi nhận kèm "đã dùng", tạo việc Completed + eMAR; mức LỚN; **review độc lập bắt buộc**), -c (xác nhận thay, lý do quá hạn, đợt hậu kỳ), -e (dispense tủ trực + đếm bù; mức LỚN; **review độc lập bắt buộc**), -f (hiển thị hồi cứu). DDL chỉ **liệt kê, chưa viết**: `clinical_order_verifications.witness_by`, `verified_on_behalf`, `late_reason`; có thể `emar_administration_logs.source_verbal` hoặc suy từ `source_mode`; chỉ mục unique một phần eMAR **chỉ sau khi rà dữ liệu thật**; có thể `inpatient_dispense_records.nursing_task_id/emar_log_id`; tất cả cột mới cho phép null.
- **10 câu hỏi E1–E10 chờ chủ dự án** (chi tiết, bối cảnh và phương án ở `BAOCAO-CTRL-S2-02A-4.md` mục E): E1 nghĩa của "sinh/liên kết dòng Đã thực hiện khi ký" (+ Cấp cứu có cần y lệnh miệng dạng `clinical_orders` không); E2 nhóm thuốc loại khỏi y lệnh miệng; E3 người chứng kiến bắt buộc khi nào; E4 ai xác nhận thay khi bác sĩ hết ca; E5 xử lý khi từ chối sau khi đã dùng (thu tiền, kho, sự cố); E6 `NGAY_YL` của XML 130 lấy giờ nào (cần mẫu XML, chưa đối chiếu); E7 cho xác nhận khi đợt không còn `Active`; E8 cổng đóng bệnh án (hàm đóng chưa có trong mã); E9 mức Block (mọi y lệnh miệng chưa ký hay chỉ quá hạn); E10 hạn 24 giờ và dùng chung cho Cấp cứu (`VerbalOrderVerificationDueHours`, hiện "chưa phải giá trị chốt"). Dòng nháp trong ô nhập `claude-9` ("Đọc báo cáo và trả lời E1 đến E10 giúp tôi") nhiều khả năng do chủ dự án gõ; chưa gửi, chưa xử lý.
- **Căn cứ pháp lý:** báo cáo không viện dẫn số hiệu văn bản; các chủ đề cần đối chiếu văn bản gốc trước khi khoá cứng (ký/xác nhận y lệnh miệng và thời hạn, kê đơn thuốc gây nghiện/hướng thần, cơ số tủ trực, mẫu XML 130) đều là **chưa đối chiếu**.
- **Chưa kiểm / giới hạn của báo cáo:** chưa đọc thân `ExpandOrderScheduleSlotsCore` (ca y lệnh miệng ghi muộn không sinh việc là [S]); chưa đọc hết helper `RecordVerbalOrderCommand.cs:1053-1259` và `CosignTraineeOrderCommand.cs`; chưa kiểm các đường dừng y lệnh khác ngoài `ConfirmOrRejectVerbalOrder`; không có dữ liệu DB thật.
- **Trạng thái cửa sổ:** `claude-9` đã xong nhưng **chưa đóng** (theo lệnh "không làm gì thêm"); `claude-8` (S2-15A) vẫn đang chạy, chưa có báo cáo. Hàng đợi ở mục 4 giữ nguyên, chưa giao tiếp.

## 12. CẬP NHẬT (13/11 ~14:50): báo cáo phân tích S2-15 ("khoa của tôi" đóng-mặc-định) đã xong — chỉ ghi lại, CHƯA xử lý

Theo lệnh chủ dự án ("chỉ ghi lại báo cáo không làm gì thêm"): PM **chỉ ghi nhận**; **chưa đối chiếu** các phát hiện dưới đây với mã thật (khác mục 11, nơi PM đã đối chiếu 5 điểm); chưa giao việc, chưa đóng cửa sổ.

- **Nguồn:** `claude-8` (Sonnet 5.5), `PROMPT-CTRL-S2-15A.md`, phân tích chỉ-đọc trên `C:\wt\ctrl-base` (HEAD `a2a23e37`; cây không đổi; không kết nối DB, không build/test, không commit). Báo cáo 5 tệp trong `prompts\`: `BAOCAO-CTRL-S2-15A.md` (tóm tắt + A hiện trạng, có dòng `HOÀN TẤT`), `-2.md` (phụ lục nơi gọi, mục B), `-3.md` (C phương án), `-4.md` (D kế hoạch + ma trận test), `-5.md` (E câu hỏi, F căn cứ).
- **Phát hiện chính (theo báo cáo, [chưa đối chiếu]):**
  - Mã "khoa của tôi" hiện có **4 định nghĩa, không phải 2**; trong đó có `StaffDepartmentScope` (`Service.Core/Executes/Legacy/Accounts/Accounts/StaffAccountMany.cs:51`, dùng ở `EncounterMany`, `EncounterOne`...).
  - **Không có chỗ nào trong mã sản xuất ghi bảng `account_departments`**, và Web cũng không có màn gán khoa. Nghĩa là dữ liệu bảng này chỉ có do nạp tay/seed; đóng-mặc-định ngay sẽ làm trống màn của mọi tài khoản chưa được gán.
  - **Tiền đề trong prompt của PM sai một điểm:** prompt nói đính kèm đối chiếu thuốc "đã dùng helper chặt"; báo cáo ghi thực tế nó dùng **helper mở** (`null` = không giới hạn). PM chưa kiểm lại; **nếu đúng thì S1-3 và S2-14 không "đóng-mặc-định" như đã tin**, cần xem lại khi làm S2-15.
  - **Nội trú lọc theo "khoa tiếp nhận"** (cột lúc nhập viện) và `PerformBedTransfer` **không cập nhật cột đó**, nên chuyển khoa là điểm phải sửa **trước** khi đóng-mặc-định (nếu không khoa mới không thấy bệnh nhân vừa chuyển đến, khoa cũ vẫn thấy).
  - Không có chỗ nào của Web gọi `AssignedDepartmentIds` hay các helper Inpatient/Nursing/Emergency; việc lọc nằm trong Service.
- **Đề xuất của agent (CHƯA được chủ dự án xác nhận):** cờ toàn viện là **node quyền riêng**, cần **ít nhất bốn loại** (lâm sàng toàn viện, điều dưỡng (đã có kiểu này), tài chính/thu ngân, và các loại khác ghi ở `-3.md`), không phải một cờ duy nhất; cơ chế chuyển đổi 3 chế độ `Open` / `Audit` / `Closed` (`Audit` vẫn trả dữ liệu nhưng ghi nhật ký "đáng lẽ bị chặn"); **cơ chế mở khẩn cấp (break-glass)** có lý do + nhật ký + hết hạn (agent lập luận: thiếu nó, Cấp cứu và trực đêm sẽ xin cờ toàn viện cho tất cả, vô hiệu hoá đóng-mặc-định); phạm vi tạm thời theo thời hạn (`start_date`/`end_date`) cho điều động/hội chẩn.
- **Kế hoạch 10 việc S2-15-a đến S2-15-j** (chi tiết ở `-4.md`, kèm ma trận test: đúng khoa, khác khoa, nhiều khoa, hết hạn/chưa tới hạn, cờ toàn viện, mở khẩn cấp, tài khoản chưa gán khoa ở từng chế độ). PM **chưa đọc** danh sách từng việc, thứ tự, DDL liệt kê, mức, việc nào cần chủ dự án hoặc đọc DB thật; đọc `BAOCAO-CTRL-S2-15A-4.md` trước khi giao.
- **Câu hỏi cho chủ dự án** (mục E ở `-5.md`) và căn cứ pháp lý (mục F): PM **chưa đọc**; mọi viện dẫn quy định phải coi là "chưa đối chiếu văn bản gốc".
- **Dòng nháp trong ô nhập `claude-8`:** "Giao việc S2-15-a theo kế hoạch" (nhiều khả năng do chủ dự án gõ). **Không gửi, không xử lý**; chủ dự án quyết có giao hay không. Lưu ý trước khi giao S2-15-a: bước đầu của kế hoạch có thể cần quyết định (loại cờ toàn viện, chế độ chuyển đổi) và đọc DB thật, phải kiểm `-4.md`.
- **Trạng thái cửa sổ:** `claude-8` đã xong, chưa đóng; `claude-9` đã xong, chưa đóng (mục 11). **Hiện có 3 cửa sổ Claude kể cả Agent 0** (đúng giới hạn tối đa 3); muốn giao việc mới thì phải đóng một cửa sổ xong việc trước. Hàng đợi mục 4 giữ nguyên, chưa giao; thứ tự mới nên cân nhắc lại sau khi chủ dự án trả lời E (S2-02) và E (S2-15).
- **Hai phân tích còn lại trong kế hoạch phân tích:** S2-04A (`PROMPT-CTRL-S2-04A.md`) **chưa chạy**; S2-04 giao nhau với S2-02-b (cùng `ConfirmEmergencyDeparture`), nên nên chạy S2-04A trước khi viết mã S2-02-b.
