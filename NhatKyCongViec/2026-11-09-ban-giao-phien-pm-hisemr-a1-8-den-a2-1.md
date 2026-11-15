# 09/11/2026 (chiều) — Bàn giao phiên PM (Agent 0): A1.8 xong → A2.0a, A2.2 xong → A2.1a đang làm; kế hoạch A2–A6; làm hết Service rồi mới Controller/View

**Đọc file này ĐẦU TIÊN nếu bạn là phiên PM tiếp theo.** Sau đó đọc `2026-11-09-ban-giao-phien-pm-a1-6b-den-rt-2.md` (vai PM, bẫy kỹ thuật, quyết định A1.5–A1.7, hoãn kiểm thử) và `Plan Coding/KE-HOACH-CODING-SERVICE-A2.md` (kế hoạch đợt đang làm). File này thay các mục "trạng thái / việc chờ / bước kế" của file `…a1-6b-den-rt-2.md`.

**Lưu ý trung thực:** mọi số build/test dưới đây là số **do agent báo**; PM phiên này **chưa tự đo lại** được build trên cây sạch (worktree riêng lỗi môi trường EF Core 8.0.31/8.0.33, xem mục 6). PM đã tự đọc mã của: A1.8 (sau sửa 1, 2), A2.0a (diff đầy đủ), A2.2 (`AssignRosterEntry` và hằng so với DDL), kế hoạch A2…A6 (đối chiếu DDL/DefaultFeatures bằng lệnh). Chưa đọc hết mọi tệp.

## 0. Việc đổi hướng quan trọng của chủ dự án trong phiên
- **Làm XONG HẾT SERVICE (A2…A6) rồi mới sang Controller/View.** Không lập `KE-HOACH-CODING-CONTROLLER-VIEW.md` lúc này (chủ dự án: "chưa code xong hết service thì làm service xong mới qua view").
- Vẫn **hoãn viết test mới và kiểm thử** (GD2 mục 8.1, nợ ở 13A/13B). Agent code chỉ viết mã.
- Chủ dự án yêu cầu: **đúng kiến trúc Service trong tài liệu** (GD2 mục 3, skill `his-service-layer`, RETURN-TYPE); **agent code trả báo cáo bằng TỆP MD** (đường dẫn) thay vì dán dài trong terminal; muốn các agy **tận dụng subagent của chính agy** (không mở thêm CMD): đang thử ở A2.1b.

## 1. Quyết định đã chốt trong phiên (không bàn lại)
- **Vị trí truy vấn đọc (phương án A):** ca GHI ở `Executes/<Nhóm>/_UseCases/<Ca>/` (`<Ca>Command.cs` + `<Ca>Models.cs` + `<Ca>Rules.cs` nếu cần); truy vấn ĐỌC ở `Executes/<Nhóm>/<TênTruyVấn>/` **ngoài `_UseCases`**, hàm kết thúc `Many`/`One`/`BaseList`, **không hậu tố `Query`**, không `InTransaction`. Lý do: `UseCaseArchitectureTests` R2 (mỗi thư mục ca phải có `<Ca>Command.cs`) và R3 (mọi hàm công khai trong `_UseCases` đi qua `InTransaction`). GD2 mục 3.1 đã sửa theo đó (`8633a631`). **Không nới R2/R3.**
- **A2 Q1–Q11 chốt theo đề xuất PM** (kế hoạch A2 mục 8): riêng **Huỷ vòng (W-04) chưa duyệt ⇒ bỏ khỏi A2**; Q4 node mới; Q7 tự tạo vòng ACTIVE ở hook không chặn tiếp nhận; Q9 mã lý do là hằng ở code; Q1 tiếp nhận chỉ bàn giao khi tham số `AllowReceptionHandover` bật.
- Quyền dùng node `noi_tru.*` / `dieu_duong.*` trong `DefaultFeatures.Tree` với cờ `Has` ∈ `v c u d t a` (`PermissionAction`), bộ kiểm quyền kiểu `BedPermissions`/`NursingRosterPermissions` (đóng-mặc-định `DenyAll…`, `Feature…Checker`). **Tuyệt đối không dùng chuỗi `his.inpatient.*`/`his.nursing.*`.**
- `Snapshot` (IN9) nay đã có: `Snapshot<T>(T data, DateTime serverNow)` (A2.0a); đọc lại bằng `ReadSnapshot<T>`.
- Thứ tự khoá: `RowLockTables.All` nay có `patient_handovers`, `patient_wristbands` **trước** giường; tên thật là `All`/`IdTypes` (không có `.Allowed`).
- **A1.9 (dọn kiến trúc, GD2 mục 13B) xếp SAU A2.1a, TRƯỚC A2.1b.** Chưa viết prompt A1.9.
- Đóng cửa sổ agent khi xong việc (giảm tải RAM); agent kế hoạch dài phải chia nhỏ (ghi từng phần < 150 dòng).

## 2. Trạng thái commit (từ `20efecc1`; trước commit file này `main` hơn `origin/main` 18 commit, **chưa push**: chủ dự án chưa nói "push")
| Commit | Nội dung | Ghi chú |
|---|---|---|
| `37df6d9a` | A1.8: 8 hàm truy vấn (A-03/04, B-09/10, C-10..C-12) | agent code agy-1 |
| `32f7c7ff` | A1.8 sửa 1: bỏ nhánh `DenyAll` làm hở quyền C-12, `includeDeleted:false` | PM bắt lỗi |
| `95dce290` | A1.8 sửa 2: `EpisodeListMany`+`EpisodeListCountsOne`, `BedBoardMany`+`BedBoardSummaryOne`, hai ca `PatientLocationTimelineMany`/`BedStatusTimelineMany`, khôi phục 4 tệp CRUD sinh sẵn (SHA khớp `20efecc1`) | L1 (dời vào `_UseCases`) bị R2/R3 chặn ⇒ chủ dự án chọn A |
| `a9b8417e` | Kế hoạch A2 (+html) | PM + agy-2 |
| `c18c97f0`, `8633a631` | Sửa A2 và **GD2 mục 3.1** theo phương án A | PM |
| `9b038068` | **A2.2** N-01…N-09: danh mục ca, mẫu xoay, kíp, lịch trực (13 ca ghi + 5 truy vấn), `NursingRosterPermissions`, node `dieu_duong.lich_truc/kip_truc/ca_truc` | agy-2; xong, đã đóng |
| `5d8673c1` | **A2.0a**: `Snapshot`/`SnapshotEnvelope.cs`, `RowLockTables` (+`patient_wristbands`, handovers dời trước giường), `InpatientSettings` (+`WristbandReprintApprovalFromSeq=3`, `AllowReceptionHandover=false`, `MinRestBetweenShiftsHours=12`, `LongShiftThresholdHours=12`) | agy-1 |
| `db5d2e53` | Kế hoạch **A3, A4, A5** (+html) | đã đạt nghiệm thu PM |
| `8b1e96fb` | GD2 **13B** nợ kiến trúc K1–K6 + **A1.9** vào A1 và A2 | PM |
Số của agent: cổng A2.2 trên cây có A2.0a: `HIS.sln` **3.591**, `Web.HIS/HIS.sln` **3.413** (0 lỗi), bộ test quy ước 41 đạt (7 bỏ qua), Phase4 355 đạt, T5 PASS. **Mốc để so cho các đợt sau: 3.591 / 3.413.**

## 3. Việc đang dở lúc bàn giao (KHÔNG làm hỏng)
- **agy-1 đang làm A2.1a (vòng tay)** theo `PROMPT-A2.1a.md`, báo cáo sẽ ghi `C:\Users\tsmda\Downloads\BAOCAO-A2.1a.md`. Chưa commit. Tệp của A2.1a hiện trong cây: `Service.Nursing/Components/{WristbandAdmissionHookHandler,WristbandBuilder,WristbandCodes,WristbandPermissions}.cs`, `Executes/Base/NursingService.WristbandCheck.cs`, thư mục truy vấn `WristbandQueue/`, `WristbandHistory/`, `WristbandDetail/`, ca `_UseCases/{IssueWristband,ReprintWristband,ReportWristbandLost}/`; sửa `DefaultFeatures.cs` (node `noi_tru.vong_tay`), `NursingService.cs`, `ServiceRegistration.cs`, `UseCaseArchitectureTests.cs`, **và `NursingRosterCodes.cs` (tệp của A2.2: kiểm xem sửa gì và vì sao khi review)**. Cây cũng có `KE-HOACH-CODING-SERVICE-A2.md/.html` và `GD2.md/.html` **đang bị sửa chưa commit** (khả năng agy-1 cập nhật bảng tiến độ): đừng `git add` bừa, xem `git diff` trước.
- **Cần xem kỹ khi review A2.1a:** thứ tự khoá, duyệt in lại từ lần 3 bằng người có cờ `a`, `label_snapshot` qua `Snapshot` (không số giường/CCCD), hook W-05/W-06 (hook chỉ nhận `(context, admissionId)`; agent có thể đã mở rộng `IAdmissionHookHandler` ở Service.Inpatient: đọc diff), và đối chiếu tên cột với DDL.
- **agy-7 đang sửa kế hoạch A6 lần 1** theo `PROMPT-PLAN-A6-fix1.md` (A6b: cột/enum bịa so với DDL nhóm `05_ho_so`; A6c: phân biệt node `duoc.*` có sẵn/đề xuất). Tệp `KE-HOACH-CODING-SERVICE-A6a.md`, `A6b.md`, `A6c.md` **chưa commit, chưa có `.html`**. A6a đã đạt. Báo cáo `BAOCAO-PLAN-A6.md`.
- `Plan Coding/CLAUDE.md` đang sửa chưa commit (có dòng A2 do agy-2 thêm và dòng BAO-CAO của phiên khác); **bảng ở đầu `CLAUDE.md` còn thiếu dòng A3, A4, A5, A6a/b/c**: thêm khi commit các tài liệu này (hỏi chủ dự án về việc commit chung với phần sửa của phiên khác).

## 4. Việc kế tiếp theo thứ tự (cho PM mới)
1. `list_terminals` xem agy-1/agy-7 còn sống; đọc terminal và tệp báo cáo (đừng tin dòng `[AO]`).
2. **Nghiệm thu A2.1a** (đọc mã), nếu cần giao sửa lần 1 (agy-1 chưa dùng lần sửa nào cho A2.1a). Khi đạt: cho agy-1 chạy cổng + commit (đã dặn trong prompt).
3. **Viết prompt A1.9** (dọn kiến trúc: K2 `ClockNow()` lên `ModuleServiceBase` + đổi 13 ca giường sang `ClockNow()`, xoá hai bản con ở `InpatientService.AdmissionCheck.cs:19` và `NursingService.RosterCheck.cs:18` (đừng khai lại, tránh CS0108); K3/K4 đổi tên tệp truy vấn cho khớp tên hàm; K6 gộp hàm phân trang an toàn vào `Service.Core`; KHÔNG đổi hành vi, KHÔNG test) và giao agy-1.
4. **Gửi `PROMPT-A2.1b.md`** (đã viết sẵn, có giao thức **subagent** đợt thử) cho agy-1 sau A1.9; dòng điều kiện trong prompt đòi thấy commit A2.1a và A1.9. Sau đó **A2.1c** (`ReceivePatient`, ca phức tạp nhất, gọi `ConfirmOccupancy`; cần viết prompt, khoá `inpatient_admissions → patient_handovers → patient_wristbands → beds…`).
5. Khi agy-7 nộp A6: tự kiểm bằng `grep` (mục 7), commit A6a/b/c + html + `.html` mới (copy `KE-HOACH-CODING-SERVICE-A2.html` rồi `PYTHONUTF8=1 python sync-html.py`), đóng agy-7.
6. Gom câu hỏi A6 vào `CAU-HOI-CHU-DU-AN-A3-A5.md` (hiện mới có A3–A5) và nhắc chủ dự án quyết nhóm 1 (chặn A3.0/A4.0/A5.0).
7. Sau A2: A3.0 → A3, A4, A5, A6 theo kế hoạch (mỗi đợt có "chia đợt con" và "tệp chung dễ xung đột"). Chỉ một agent build tại một thời điểm.

## 5. Việc chờ chủ dự án
- **Push** các commit chưa push (`git log origin/main..HEAD`).
- **Câu hỏi A3/A4/A5 (24 câu):** `C:\Users\tsmda\Downloads\CAU-HOI-CHU-DU-AN-A3-A5.md`. **Nhóm 1 chặn đợt nền:** A3-Q9 (6 node quyền + 3 bảng khoá), A4-Q3 (7 node quyền), A5-Q2 (chống ghi đè bằng `row_version`, không `xmin`), A4-Q1 (phiếu khám vào viện trên `clinical_documents`), A4-Q2 (đồng bộ chẩn đoán chính).
- **Câu hỏi mở từ A1.8:** ngưỡng hiển thị tuổi (72 hay 36 tháng); ngưỡng quá hạn chờ tiếp nhận (120 phút; riêng Cấp cứu?); `AssignedDepartmentIds()` trả `null` (mọi khoa) khi tài khoản chưa có `account_departments`: giữ hay chặn (chặn việc gộp hàm phạm vi khoa ở A1.9/K6).
- **A2.2:** mã `reason_code` ở lịch trực hiện là hằng 1–9 agent tự đặt trong `NursingRosterCodes`: hằng ở code hay danh mục động.
- **A2.1a:** nguồn dữ liệu sơ sinh/đa thai cho nhãn vòng; người duyệt in lại trùng người thao tác.
- Việc cũ còn mở (xem file `…a1-6b-den-rt-2.md` mục 3): 12 DTO `Message` (RT-3), Docker Desktop (đừng buộc dừng, sẽ tắt container sẵn có), mở tay trang `/billing/Cashier`, `/billing/Payments`, ba quyết định RT-2, nhóm E giá ngày giường (GAP-2).

## 6. Agent, terminal, môi trường
- Dashboard: Agent 0 (bạn) + **agy-1** (code, đang A2.1a, Gemini 4 Argon **Medium**) + **agy-7** (kế hoạch A6). Đã đóng: agy-2 (code A2.2), agy-3 (A3), agy-4 (A4), agy-5 (A5), agy-6 (treo). Bạn chỉ đóng được terminal do chính bạn mở.
- Model mặc định của agy mới đã được đặt **Argon Medium** (lệnh `/model` lưu mặc định). Công cụ `send_to_terminal` chỉ gõ một dòng + Enter, **không gửi được phím mũi tên**; mỗi terminal mới đăng nhập mất vài giây (đợi dòng "Signing in…" qua rồi mới gửi). `open_terminal` giới hạn tốc độ (≥ 1,5 giây giữa hai lần).
- **Máy 15,8 GB RAM, thường chỉ còn 0,9–1,9 GB trống, CPU 100%** khi 6 agy + `dotnet` cùng chạy: agent bị treo/timeout (`stream idle timeout (5m0s)`). Quy tắc đã dùng: tối đa ~3 agy cùng lúc, chỉ MỘT agent build/lúc, đóng agent khi xong, kế hoạch dài chia nhỏ, khi một agent im lặng quá lâu mà không có tệp mới thì đọc terminal tìm dòng lỗi rồi đóng và mở lại.
- **Subagent của agy (thử ở A2.1b):** có `/agents`, `/tasks`; chạy trên cùng máy/cây (build vẫn tuần tự); agent chính phải đọc lại mã subagent; tôi không quan sát được bên trong subagent. Dùng subagent mặc định, KHÔNG dùng custom agent (nhiều báo cáo lỗi). Báo cáo A2.1b có mục số liệu đợt thử: đọc để quyết có dùng tiếp.
- **Prompt/báo cáo nằm ngoài repo (`C:\Users\tsmda\Downloads\`):** `PROMPT-A1.8*.md`, `PROMPT-A2.0a*.md`, `PROMPT-A2.1a.md`, `PROMPT-A2.1b.md` (chưa gửi), `PROMPT-A2.2.md`, `PROMPT-A2-HTML.md`, `PROMPT-PLAN-A3-A6.md`, `PROMPT-PLAN-A3-fix1.md`, `PROMPT-PLAN-A4-fix1.md`, `PROMPT-PLAN-A6-v2.md`, `PROMPT-PLAN-A6-fix1.md`; báo cáo `BAOCAO-A1.8-fix2.md`, `BAOCAO-A2.0a.md`, `BAOCAO-A2.2.md`, `BAOCAO-A2-HTML.md`, `BAOCAO-PLAN-A3…A6.md`. Mẫu tốt để copy: `PROMPT-A2.1a.md` (cấu trúc, tiêu chí đạt, báo cáo ra tệp) và `PROMPT-A2.1b.md` (giao thức subagent).

## 7. Cách nghiệm thu đã dùng (làm lại cho các đợt sau)
- **Kế hoạch:** `grep -c 'his\.[a-z]*\.'` (phải ~0, trừ câu "không dùng"); `grep 'RowLockTables.Allowed'` (phải 0); mọi tên `snake_case` trong tài liệu phải có trong `Database/**/*.sql` hoặc `tables.json` hoặc `Source/NET8/Services/**/*.cs` (script: lấy tên trong dấu `` ` ``, `grep -rqw`); **kiểm CẢ cột và giá trị enum** của từng bảng (liệt kê cột thật từ DDL rồi so; A6b lọt phép kiểm "tên bảng" nhưng sai cột); node quyền phải khớp `DefaultFeatures.cs`; truy vấn ngoài `_UseCases`; không còn "chờ chủ dự án quyết" cho điều đã chốt. **Chưa kiểm cấp cột cho A3, A4, A5** (A5 và A3 có vẻ sạch): nên làm.
- **Mã:** đọc `git show --stat`, đối chiếu chữ ký công khai, tên entity thật (`DutyRole`/`NursingRosterEntryStatus.Planned`… không phải từ báo cáo), kiểm SHA256 tệp CRUD sinh sẵn so với bản gốc (`git show <rev>:<path> | tr -d '\r' | sha256sum`), grep `DateTime.Now`, `ex.Message`, `.Remove(`.

## 8. Sai sót và bài học (thêm vào mục 5 của các file bàn giao trước)
- **Sai sót của PM:** (1) duyệt A1.8 quá sớm (bỏ sót vị trí truy vấn ngoài `_UseCases` và tệp CRUD sinh sẵn bị sửa tay) cho đến khi chủ dự án nhắc "đúng kiến trúc"; (2) kế hoạch A2 ban đầu ghi truy vấn trong `_UseCases` (sai với R2/R3), sửa sau; (3) chạy `agy --version` bằng Bash (bị chặn, đúng quy tắc không chạy `agy`/`claude`/`codex` bằng Bash); (4) dựng worktree `../HIS_EMR-verify` để build kiểm chứng: lỗi CS1705 EF Core 8.0.31/8.0.33 ở `Web.PACS` (worktree thiếu thứ gì đó của cây chính), kết quả không dùng được, đã xoá worktree; (5) tin dòng `[AO] đã xong` (báo sai/sớm rất nhiều lần): luôn đọc terminal/tệp; (6) gọi `Edit` khi chưa `Read` (lỗi).
- **Hành vi agent cần canh:** báo cáo ghi sai chi tiết (A2.2: `MEMBER`/`SCHEDULED`/`MinNurses`/`rotation_offset_days` không có trong mã dù mã đúng); kế hoạch A3/A4 dùng mã quyền `his.*`, A4 bịa bảng `department_transfers`, A3 mô tả sai `RowLockTables`, A5 nhắc `medication_return_requests`, **A6b bịa cột/enum**; agent tự nới luật (A1.8 ban đầu bỏ qua kiểm quyền khi `DenyAll` để qua một test); A2.2 commit trước A2.0a khiến commit `9b038068` một mình không biên dịch (dùng tham số khai ở A2.0a chưa commit): **thứ tự commit phải theo phụ thuộc**.
- **Bẫy kỹ thuật mới:** `ClockNow()` định nghĩa riêng ở hai service con (chưa có ở lớp nền: K2); không thêm `ClockNow` vào nền khi còn bản con (CS0108 làm tăng mốc cảnh báo); `sync-html.py` chỉ ghi các cặp có `.html` sẵn: tài liệu mới phải copy `.html` mẫu (khung giống nhau, tiêu đề lấy từ dòng `# ` đầu, bỏ phần sau dấu `—`); hook `IAdmissionHookHandler` chỉ nhận `(context, admissionId)` (không có người thao tác/giờ) và `NextSequence` là hàm `protected` (bài toán của W-06); agent không tự thấy thay đổi của PM giữa chừng: dòng gửi vào terminal xếp hàng theo lượt, nên đính chính gửi được ngay cả khi agent đang chạy.
- **Giới hạn nghiệm thu:** chưa tự đo build; chưa đọc hết thân 13 ca A2.2 và 40 ca nói chung; A2.1a chưa review.

## 9. Tệp tham chiếu
- **Kế hoạch (`Plan Coding/`):** `KE-HOACH-CODING-SERVICE-GD2.md` (3.1 đã sửa, 8.1, 13, 13A, **13B nợ kiến trúc**), `-A1.md` (có A1.9), `-A2.md` (mục 6 thứ tự, 8 câu hỏi đã chốt, 12 kiến trúc bắt buộc), `-A3.md`, `-A4.md`, `-A5.md`, `-A6a/b/c.md` (chưa commit), `KE-HOACH-CODING-SERVICE-RETURN-TYPE.md`.
- **Nhật ký (`NhatKyCongViec/`):** `2026-11-09-a1-8-truy-van.md` (mục 7, 8), `2026-11-09-a2-0a-nen.md`, `2026-11-09-a2-2-lich-truc.md`, các file bàn giao 06–09/11.
- **Mã chính của phiên:** `Service.Inpatient/Executes/{Admission,Bed}/…` (A1.8), `Service.Core/Components/{SnapshotEnvelope,RowLockTables,InpatientSettings}.cs`, `Service.Core/Executes/Base/ModuleServiceBase.Business.cs`, `Service.Nursing/Executes/Nursing/_UseCases/*` (A2.2), `Service.Nursing/Components/NursingRosterPermissions.cs`, `Service.Nursing/Executes/Base/NursingService.RosterCheck.cs`.
- **Bộ nhớ làm việc của PM:** `C:\Users\tsmda\.claude\projects\C--CongViec-agent-agent-orchestrator-selftest\memory\` (đã cập nhật `project-his-emr-pm-state.md` và `feedback-terminal-agent-handoff.md`).

## 10. QUY TẮC ĐIỀU PHỐI CMD AGENT (BẮT BUỘC, đọc đầu mỗi phiên; chủ dự án yêu cầu ghi 09/11/2026)
Bản đầy đủ: `QUY-TAC-DIEU-PHOI-CMD-AGENT.md` (cùng thư mục này). Tóm tắt những điều không được quên:
1. **Mở agent:** `open_terminal(provider="agy")`; model **Gemini 4 Argon, effort Medium** (đọc terminal xác nhận dòng `Gemini 4 Argon · medium`; sai thì gõ `/model` và nhờ chủ dự án bấm phím mũi tên); chờ đăng nhập xong rồi mới gửi; dặn agent `cd C:\CongViec\itc-git\HIS_EMR`.
2. **Giao việc:** prompt thành tệp `C:\Users\tsmda\Downloads\PROMPT-<đợt>.md`, dòng gõ vào terminal ngắn ("đọc tệp X và làm đúng theo đó"); agent ghi **báo cáo ra tệp** `BAOCAO-<đợt>.md`, terminal chỉ trả đường dẫn.
3. **Vòng lặp nghiệm thu:** không tin `[AO] đã xong`, đọc terminal + tệp + `git`; chưa đạt thì **Agent 0 viết prompt sửa** lần 1, lần 2 (tệp `-fix1.md`, `-fix2.md` hoặc điền thẳng khung chat nếu ngắn).
4. **SAU 2 LẦN SỬA VẪN CHƯA ĐẠT:** `close_terminal` cửa sổ đó → `open_terminal` cửa sổ **mới** → **Agent 0 VIẾT LẠI prompt cho chuẩn hơn** (ghi cái đã thử, vì sao chưa đạt, tiêu chí cụ thể hơn) → yêu cầu agent mới **xử lý tiếp**. Tối đa hai agent cho một việc, agent thứ hai cũng không đạt thì **báo chủ dự án**. Mâu thuẫn tài liệu/test hoặc điều thuộc quyết định chủ dự án thì dừng, hỏi, không tính vào số lần sửa.
5. **Treo/timeout:** nhắn một lần "chia nhỏ, ghi từng phần"; vẫn treo thì thay cửa sổ như mục 4.
6. **Tải máy:** tối đa ~3 agy cùng lúc, **chỉ một agent build tại một thời điểm**, đóng agent ngay khi nghiệm thu đạt.
7. **Subagent của agy:** dùng subagent mặc định, agent chính đọc lại toàn bộ mã subagent, chỉ agent chính build/commit.
8. Agent 0 không tự code, không chạy `agy`/`claude`/`codex` bằng Bash.
**Ràng buộc lặp lại:** đầu mỗi phiên đọc `QUY-TAC-DIEU-PHOI-CMD-AGENT.md` và file bàn giao này; bộ nhớ làm việc của Agent 0 có bản tóm tắt (`feedback-cmd-agent-orchestration-rules.md`). Quy tắc này **không** được thêm vào `CLAUDE.md` của source HIS_EMR (nhà phát triển khác không dùng công cụ). Việc biến nó thành tính năng của công cụ: `C:\CongViec\agent\agent-orchestrator\docs\TINH-NANG-QUY-TAC-DIEU-PHOI-AGENT.md` (agent khác sẽ cài đặt).
