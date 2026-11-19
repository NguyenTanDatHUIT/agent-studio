# BÀN GIAO PHIÊN AGENT 0 (chiều 17/11/2026): dựng View NewUIKit song song, menu Nội trú/Điều dưỡng, chờ Seed `features`

**Làm tiếp tối nay.** Repo làm việc: `C:\CongViec\itc-git\HIS_EMR` (thư mục `NhiDong\`). Tệp này nối tiếp `2026-11-17-ban-giao-phien-agent0-tich-hop-dot-17-11-va-viec-tiep-theo.md` (phần DB và Service vẫn còn hiệu lực, xem mục 6).

## 0. Làm ngay khi mở phiên
1. `get_orchestration_rules`, `list_terminals`. Cuối phiên còn mở: `agy-1`, `agy-2`, `agy-3`, `agy-5`, `agy-6` (đều rảnh, worktree sạch), `claude-4` (cửa sổ BUILD, nhận dòng `BUILD <worktree> Web.HIS`).
2. Đọc `C:\AgentControl\studio-state\prompts\PROMPT-CHUNG.md`, `KHUON-VIEW-NEWUIKIT.md`, `QUY-LUAT-VIEW-RAZOR-LOI-BIEN-DICH.md`.
3. `git -C C:\CongViec\itc-git\HIS_EMR fetch origin`, so `origin/main` (`d60b2088`) với `main` (`3daf080e`).

## 1. Trạng thái nhánh
- **`main` = `3daf080e`**, cây chính sạch, **trước `origin/main` 25 commit, CHƯA PUSH** (chủ máy chưa yêu cầu). Toàn bộ là việc View/menu hôm nay, không lẫn commit của người khác. Khi push: chủ máy phải nói rõ; `origin` không đi trước nên `git push origin main` được, nhưng nên hỏi lại vì `main` chứa View chưa ai xem trên trình duyệt.
- Mọi nhánh việc đã gộp vào `main` bằng fast-forward qua `wt/view-int` (cùng `3daf080e`). Build `Web.HIS` trên chính nội dung này: **0 lỗi**, 3.496 cảnh báo (build đầy đủ, không so được với mốc 3.492 của B2). Phase4: **355 đạt / 0 lỗi / 1 bỏ qua**, `FeatureCoverageTests` 3/3.
- Worktree còn lại (xoá khi hết việc, đều đã nằm trong `main`): `C:\wt\view-v0`, `view-v1`, `view-v2`, `view-v3`, `view-v4`, `view-ph`, `view-menu`, `view-dev`, `view-int` (nhánh `wt/view-*`). Không xoá `apply-newuikit`, `ctrl-ddl`, worktree Codex.

## 2. Đã làm hôm nay (đều trong `main`)
| Nhóm | Nội dung | Commit chính |
|---|---|---|
| V0 nền | `UiKit.cshtml` thêm `@section Styles/Scripts`; `inpatient-core.css`; `MkReason` (hộp nhập lý do); màn mẫu `WaitingList`; `episode-detail.js` hết `window.prompt` | `efa17cb1`, `66edf9c2`, `db75058b` |
| V1 Nội trú | `Episodes`, `IdentityReconciliation` (+`Detail`), `EpisodeDetail`; wizard `Admission` + `AdmissionResult` (4 partial bước, `admission.js/css`) | `0a2d782f`, `6c99e8f9` |
| V2 Giường | `Bed/WaitingList`, `Bed/Board` | `04693ef2` |
| V3 Điều dưỡng | 9 màn: `Shifts`, `Teams`, `Roster`, `WristbandQueue`, `WristbandHistory`, `HandoverOut`, `IncomingPatients`, `ReceivePatient`, `MyPatients` | `b8013090`, `a3643480` (sửa `@using`), `61ba38e9` |
| V4 Workspace | `MyPatients` (bác sĩ), khung `PatientWorkspace`, tab `Overview`, `AdminInfo`, `Orders`, `Medication` | `577d5f57`, `c0edf40d` |
| Dược lô 1 | 6 trang: `Warehouses`, `FundingSources`, `StorageLocations`, `DrugCatalogs`, `MedicationOrders`, `PaidMedicationOrders` | `a8120d55` |
| Developer/Features | `/developer/features` sang NewUIKit (`Features.cshtml`, `FeatureEdit.cshtml`, `features.js`, `features-uikit.css`) | `a4a5eea9` |
| Menu | `DefaultFeatures.cs`: `Url/Relate/Sidebar` cho 9 nút (giường, bàn giao, vòng tay, workspace, 4 nút Điều dưỡng + cha `dieu_duong`) | `3c49ba1f` |
| Giao diện chung | bỏ `padding: 15px !important` của `main.uk-content.content` (`uikit-his-bridge.css:401`), `kitVer` 17 → 18 | `3daf080e` |
Prompt và báo cáo: `C:\AgentControl\studio-state\prompts\PROMPT-VIEW-*.md`, `BAOCAO-VIEW-*.md`, ma trận `BAOCAO-VIEW-MATRAN-{NOITRU,DIEUDUONG,WORKSPACE,CAPCUU-TIEN}.md`.

## 3. VIỆC DỞ QUAN TRỌNG NHẤT: Seed menu vào DB thật (chờ chủ máy bấm)
- Navbar dựng từ bảng `features`. DB `his_nhidong` (`192.168.1.214`) **vẫn 81 dòng, 0 dòng `noi_tru`, `dieu_duong`, `cap_cuu`, `cskh`** (kiểm lần cuối chiều 17/11). Nên menu Nội trú và Điều dưỡng **chưa hiện**.
- Chủ máy đã cho phép Seed trên DB thật ("chạy Seed trên DB thật đi"). Seed chạy bằng nút **"Khởi tạo từ menu mặc định"** ở `/developer/features`, cần phiên đăng nhập của chủ máy. **Phải chạy từ bản có mã mới** (`main` `3daf080e`): nếu bấm ở bản cũ, 9 nút sẽ chèn với `Sidebar: false` và không `Url`, lần Seed sau bỏ qua (`Seed` bỏ qua mã đã tồn tại) nên phải sửa bằng SQL.
- **Sao lưu ngay trước Seed:** `C:\AgentControl\studio-state\db-backups\his_nhidong_214_20261117_164821_truoc_seed_features.dump` (63,7 MB). Quay lui từ bản này nếu Seed sai.
- Sau khi chủ máy báo đã Seed: đối chiếu bằng truy vấn chỉ đọc (docker `postgres:16` `psql`, mật khẩu lấy từ `appsettings.Development.json`, đừng in ra): số dòng tăng; nút `noi_tru.*`, `dieu_duong.*` có mặt; 9 nút có `url` và `is_sidebar = true`; cha `noi_tru`, `dieu_duong` hiện; 81 dòng cũ không đổi.
- **Menu hiện cần quyền:** chủ máy phải được gán quyền xem trên các nút mới (màn nhóm quyền). Chưa gán cho vai trò nào. Có thể cần đăng xuất rồi đăng nhập lại.
- Quyết định chủ máy: **giữ hai nhóm gốc "Nội trú" và "Điều dưỡng"** (không gộp vào nhóm cũ). Muốn đổi vị trí thì kéo thả ở `/developer/features` sau Seed.
- Mỗi nút chỉ có một `Url`: màn phụ (`WristbandHistory`, `HandoverOut`, `Bed/WaitingList`, `ReceivePatient`) không có mục riêng, vào qua `Relate` hoặc liên kết trong màn. Muốn tách mục thì thêm nút mới vào `DefaultFeatures.cs`.
- **Tab Cấp cứu chưa có:** chưa có View Cấp cứu (`Views\Emergency` không tồn tại) và nút `cap_cuu` còn `Sidebar: false`. Chủ máy đã hỏi; chưa giao V5.

## 4. Câu hỏi chủ máy chưa trả lời (đang dùng mặc định thận trọng, đã ghi trong prompt)
- **Nội trú/Giường:** tab Điều dưỡng của `EpisodeDetail` (mặc định: ẩn); thêm 2 action GET partial `BedEdit`/`BedDayServiceEdit` cho `Category/Beds` (hiện chưa làm); `[AnyStaff]` giữ nguyên.
- **Điều dưỡng:** mở lại menu `phan-cong-dd` (chưa); xuất `.csv` hay `.xlsx` (giữ CSV); thẻ KPI "Quá 30 phút" của `ban-giao-di` (ẩn); polling hay SignalR (polling).
- **Workspace:** tab mặc định `ov`; ẩn nút In/PDF; chưa gộp chỉ số mini vào `HeroData`.
- **Cấp cứu/Tiền (chờ, chưa giao):** gộp `Exam`+`Disposition` vào tab Workspace cấp cứu; gắn `[Feature]` cho `BillingController`; khoá `ApproveSettlement` khi thiếu `PendingRecalculationChargeCount`.

## 5. Chưa kiểm / rủi ro (đừng nói "xong" cho các điểm này)
- **Chưa màn nào được chạy trên trình duyệt thật hoặc xem ảnh** (kể cả `WaitingList` mẫu, 1366/1024, sáng/tối). Theo kế hoạch V0, chủ máy phải duyệt ảnh `WaitingList` trước khi coi nền ổn. Biên dịch xanh chỉ bảo đảm hết lỗi cú pháp.
- Bỏ padding `uk-content` có thể làm card dính mép ở vài màn: chờ chủ máy xem.
- **Cần review độc lập trước khi dùng thật:** tab `Orders` (10 action ghi quyền `noi_tru.y_lenh`, nặng nhất `SignOrderBatch`, `OverrideOrderSafetyCheck`), thao tác giường (`AssignBed`, `TransferBed`, `LockBed`, `ReleaseBed`, `CorrectStay`).
- Wizard tiếp nhận ẩn nút "In vòng tay" và "Bàn giao lên khoa" ở bước 5; bật lại khi cần (làm riêng).
- `pharmacy-uikit.css` có 29 mã màu nhưng đều là giá trị dự phòng `var(--uk-..., #hex)`, không có `!important`.
- Dược còn 12 trang (nhập, xuất, chuyển kho, kiểm kê, tồn kho, cảnh báo, NHIC...) chưa làm; chưa có ma trận cho Dược.

## 6. Việc DB/Service còn nợ từ bàn giao sáng (không đổi)
Script vá quyền `cskh`, `cskh.xac_nhan_lich` (diễn tập 2 lần rồi chủ máy xác nhận); xoá cache nhãn `OptionValueBaseList_EncounterStatus.xml` hoặc khởi động lại `Web.HIS` để hiện "Chờ nhập viện"; 202 tài khoản chưa gán khoa; Service khu vực chăm sóc hoãn; in/PDF 7 action hoãn; `Url/Sidebar` cho `cap_cuu.*`, `cskh.*` chưa có.

## 7. Cách làm (đúc kết hôm nay)
- **Mỗi nhóm một worktree** tách từ nhánh nền (`git worktree add -b wt/view-<x> C:\wt\view-<x> <nền>`); tạo worktree mất 1 đến vài phút (24 nghìn tệp), nên chạy nền; `locked` nghĩa là đang checkout. Gộp bằng `wt/view-int` rồi `git merge --ff-only wt/view-int` vào `main` (cây chính sạch, chủ máy đã yêu cầu rõ). Không push.
- **agy không chạy được `dotnet`/`bash`/`git commit`:** Agent 0 commit hộ (từng tệp theo tên, `Co-Authored-By` theo hệ thống) và nhờ `claude-4` build: gõ `BUILD C:\wt\view-int Web.HIS`, log `LOI-BUILD-view-int-Web.HIS.txt`; **luôn tự đọc lại log** (`Build succeeded`, `Error(s)`). Chạy test: `build-slot.sh dotnet test '<Phase4.Tests.csproj>' [--no-build]`. Đường dẫn trong lệnh phải viết sẵn, không dùng `$(...)` trong chuỗi.
- **Lỗi lặp lại:** thiếu `@using` trong `.cshtml` (partial không thừa hưởng `@using` của View cha; `AccountBaseView` ở `DBContext.HIS.Entities`). Đã viết `QUY-LUAT-VIEW-RAZOR-LOI-BIEN-DICH.md` và buộc agy ghi dòng `TỰ KIỂM RAZOR` trong báo cáo.
- **Nghiệm thu nhanh mỗi nhánh:** `grep` các điều cấm (`style=`, `<style`, `!important`, lớp Limitless, `prompt/confirm/alert`, mã màu); đối chiếu action trong JS/View với `IActionResult <Tên>(`; kiểm `@using` theo kiểu dùng; đối chiếu tên trường ViewModel; đọc `git status` (chỉ tệp trong phạm vi).
- **Thông báo `[AO]`:** nhiều dòng "yên lặng" chỉ là gợi ý và hay tới trễ; "Chủ dự án xác nhận ... hoàn thành" là chủ máy bấm nút, có khi lặp lại việc đã nghiệm thu. Luôn đọc terminal và tệp trước khi kết luận.
- Model agy mặc định đang là Gemini 4 Hydrogen (Medium) (ghi nhớ của chủ máy: không chỉnh `/model`). Chủ máy vừa đặt `/model` của Claude Code thành "Opus plan, else Sonnet".

## 8. Việc kế tiếp gợi ý (theo thứ tự)
1. Chủ máy Seed (mục 3) rồi tôi đối chiếu DB; hướng dẫn gán quyền để menu hiện.
2. Chủ máy chạy `Web.HIS` từ cây chính, xem ảnh/duyệt các màn (đường dẫn: `/Inpatient/WaitingList|Episodes|IdentityReconciliation|EpisodeDetail?id=`, `/Bed/Board|WaitingList`, `/Nursing/Shifts|Teams|Roster|WristbandQueue|WristbandHistory|HandoverOut|IncomingPatients|MyPatients|ReceivePatient?handoverId=`, `/InpatientWorkspace/MyPatients|PatientWorkspace?admissionId=&tab=`, `/Pharmacy/...`, `/developer/features`). Chỉ xem, đừng bấm nút ghi (DB thật dùng chung).
3. Theo phản hồi: sửa lỗi runtime/bố cục (giao agy theo fix1/fix2, tối đa 2 lần mỗi việc).
4. Đợt viết View kế: V5 Cấp cứu (cần chủ máy chốt mục 4) và V6 thu tiền (review riêng); tab Workspace còn lại (`ProgressNotes`, `Lab`, `Imaging`, ...); Dược lô 2 (cần ma trận); `Category/Beds` (cần 2 action GET); tách mục menu nếu chủ máy muốn.
5. Review độc lập `Orders` và thao tác giường (mục 5).
6. Push khi chủ máy yêu cầu (tách kỹ vì `main` chứa 25 commit chưa ai xem).

## 9. QUYẾT ĐỊNH CHỦ MÁY (cuối chiều 17/11): View CŨ cũng phải chỉnh sang NewUIKit, không chỉ View mới
Chủ máy dặn: "không chỉ view mới, các view cũ cũng cần được chỉnh sửa lại". Điều này thay đổi kế hoạch cũ (`KE-HOACH-VIEW-THUC-HIEN.md` mục 5A: các nhóm có trong code nhưng không có trên mockup "không đụng"): nay phải rà **mọi** View đang chạy trên layout `UiKit.cshtml`.
- **Đo ngày 17/11 trên `main` `3daf080e`** (đếm tệp `.cshtml` còn lớp Limitless `panel*`, `label`, `btn-default`, `pull-right/left`, `text-semibold`, `position-left`, `nav-tabs-bottom`, `data-toggle/dismiss`, `iconify-icon`; tách theo token nên `form-label` của BS5 không bị tính): **124 tệp còn Limitless**:
  `Category` 37/57, `Pharmacy` 20/38 (còn 12 trang chưa làm lô nào cộng các tệp con), `Clinical` 18/18 (9 tệp có `<style>`), `QueueConfig` 8/16, `Account` 8/11, `Emr` 7/8, `General` 6/11, `Patient` 4/4, `EmrTemplate` 4/4, `Reception` 3/3, `Guardian` 3/5, `Queue` 2/2, `Developer` 2/4 (`Endpoints`, `LoginMethod`), `Signing` 1/1, `Billing` 1/3.
  Đã sạch: `Nursing`, `Inpatient`, `InpatientWorkspace`, `Bed`, `Home`, `GuardianPortal` (còn 1 tệp có `<style>`).
- Trước đây nhiều View cũ chỉ "chạy được nhờ lớp tương thích" (`his-legacy-compat.css`, `uikit-his-bridge.css`); chủ máy muốn chuyển thật. Với View cũ: GIỮ hành vi, URL, tên trường; chỉ đổi markup/CSS (khác View mới), dùng skill `newuikit-migrate` và `KHUON-VIEW-NEWUIKIT.md`; không có mockup thì lấy kit mẫu `C:\CongViec\itc-git\OfficeAI\Solution\UI templates\NewUIKit` (docs, demo) làm chuẩn.
- **Đề xuất thứ tự (làm lô nhỏ, mỗi lô một nhóm thư mục để không giẫm nhau):** `Developer` (2 tệp còn lại) → `Reception`, `Patient`, `Guardian`, `Billing` → `Account`, `General`, `Queue`/`QueueConfig` → `Pharmacy` 12 trang còn lại → `Emr`, `EmrTemplate`, `Signing` → `Clinical` (nhiều `<style>`) → `Category` (57 tệp, nhiều danh mục CRUD thuần, có thể dùng chung một khuôn). Mỗi lô: agy sửa → Agent 0 `grep` cấm + build → chủ máy xem ảnh.
- Chuẩn nghiệm thu giữ như View mới (không `style=`, `<style>`, `!important` mới, lớp Limitless, `prompt/confirm/alert`); thêm: không đổi id/lớp mà JS đang dùng (đối chiếu trước khi sửa), vì View cũ không có bộ test giao diện bắt lỗi.
- Chưa giao việc nào cho nhóm này; chờ chủ máy chốt thứ tự và số agy song song (RAM, giới hạn 8 cửa sổ).
