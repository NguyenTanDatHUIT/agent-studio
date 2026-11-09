# Tính năng: "Quy tắc điều phối CMD agent" cấu hình được trong Cài đặt của Agent Studio

Trạng thái: **Pha 1 đã cài đặt (09/11/2026, xem `NhatKyCongViec/2026-11-09-quy-tac-dieu-phoi-agent-pha-1.md`); Pha 2 và Pha 3 chưa làm.** Bên dưới là đặc tả gốc. Người viết: Agent 0 (Claude Code) theo yêu cầu của chủ máy, 09/11/2026. Người cài đặt: một agent khác (đọc tài liệu này rồi làm trong repo này).
Phần "đã kiểm trong mã" ở mục 9 là điều Agent 0 đã mở và đọc; phần ghi **[chưa kiểm]** là suy đoán cần agent cài đặt xác nhận trước khi dựa vào.

## 1. Vì sao cần tính năng này
- Agent 0 (Claude Code do công cụ này mở) điều phối các agent CMD (`agy`, `claude`, `codex`). Cách điều phối hiện nằm **cứng** trong tệp `examples/AGENT0-PROMPT.md` (mục "Giao việc cho agent tương tác rồi đánh giá, sửa, thay cửa sổ", 7 bước), một bản cho mọi người dùng.
- Qua một dự án thật (HIS_EMR, hơn 60 lượt giao việc cho `agy` trong một ngày) chủ máy rút ra thêm nhiều quy tắc cần Agent 0 **tuân thủ lặp lại ở mọi phiên chat mới**: chọn model, vòng lặp sửa/thay cửa sổ, giới hạn đồng thời theo tải máy, một agent build tại một thời điểm, báo cáo bằng tệp, cách nghiệm thu... (chi tiết mục 4 và phụ lục A).
- **Không đưa vào `CLAUDE.md` của repo nguồn người dùng**: các nhà phát triển khác trong cùng repo không dùng công cụ này nên không được bị ràng buộc bởi quy tắc này. Quy tắc phải thuộc về **công cụ và chủ máy** (cài đặt của Agent Studio), không thuộc về mã nguồn dự án.
- Mục tiêu: chủ máy **xem và sửa** bộ quy tắc ngay trong giao diện Cài đặt; công cụ **tiêm bộ quy tắc vào Agent 0 ở mọi lần mở, khởi động lại, mở lại phiên (resume)**; một số quy tắc được **công cụ tự thực thi** (giới hạn số agent, nhận diện treo...), không chỉ là chữ.

## 2. Phạm vi và nguyên tắc
- Tính năng chung cho **mọi dự án** dùng Agent Studio: nội dung mặc định **không được chứa tên tệp, tên bảng, đường dẫn hay thuật ngữ riêng của HIS_EMR** (dùng biến thay thế, mục 4.1).
- Quy tắc là **dữ liệu của chủ máy**, không phải của repo: không đọc từ tệp trong repo đích, không để agent (worker) sửa được (kẻ đưa dữ liệu vào repo không được nới quy tắc).
- Không làm yếu các ràng buộc an toàn đã có: `AGENT0_DENIED` (cấm `Agent`/`Task`/`Workflow` và `Bash(agy|claude|codex:*)`), `acknowledge_local_execution`, danh sách công cụ cho phép `AGENT0_TOOLS`. Quy tắc tuỳ chỉnh **không thể thêm công cụ hay gỡ lệnh cấm**; chỉ bổ sung chỉ dẫn và giới hạn **chặt hơn**.
- Tuân thủ `CLAUDE.md` của repo này (đọc `docs/UI-RULES.md` trước khi sửa UI; không push/merge vào `main` nếu chưa được yêu cầu; ghi nhật ký vào `NhatKyCongViec/`).

## 3. Mô tả chức năng (nhìn từ chủ máy)
1. Trong **Cài đặt** có mục mới **"Quy tắc điều phối agent"** gồm: (a) nhóm tham số có cấu trúc, (b) ba ô văn bản Markdown, (c) xem trước, (d) lịch sử, (e) khôi phục mặc định, (f) nhập/xuất `.md`.
2. Bấm **Lưu** ⇒ quy tắc có hiệu lực cho **phiên Agent 0 kế tiếp** (mở mới, khởi động lại, hoặc resume). Có nút **"Khởi động lại Agent 0 để áp dụng"** (đã có sẵn `restart_agent0`) và dòng cảnh báo "Agent 0 đang chạy chưa nhận bản mới".
3. Agent 0 còn có công cụ MCP chỉ-đọc **`get_orchestration_rules`** để **đọc lại bản hiện hành** bất cứ lúc nào (đầu phiên, sau khi chủ máy đổi quy tắc, hoặc sau khi cuộc trò chuyện bị nén ngữ cảnh).
4. Một số tham số được công cụ **tự thực thi** (mục 6): giới hạn số agent tương tác chạy cùng lúc, nhận diện agent treo/lỗi, cảnh báo thiếu RAM, và **sổ vòng nghiệm thu** ghi nhớ trạng thái giữa các phiên chat.

## 4. Nội dung bộ quy tắc

### 4.1 Tham số có cấu trúc (có mặc định, có kiểm giá trị)
| Khoá | Mặc định | Ý nghĩa |
|---|---|---|
| `default_provider` | `agy` | CLI dùng khi chủ máy không nói rõ (`agy`/`claude`/`codex`). |
| `provider_models.agy` | `{model: "Gemini 4 Argon", effort: "medium"}` | Model/mức suy luận mong đợi cho `agy`. Agent 0 phải **đọc terminal xác nhận** trước khi giao việc; nếu sai, gõ `/model` và nhờ chủ máy chỉnh (công cụ `send_to_terminal` chỉ gõ một dòng + Enter, **không gửi được phím mũi tên**). Với `claude`/`codex` để trống được. |
| `max_fix_rounds` | `2` | Số lần yêu cầu **sửa** trước khi **thay cửa sổ** (đóng cửa sổ, mở cửa sổ mới). |
| `max_agents_per_task` | `2` | Số cửa sổ tối đa cho **một việc**; quá số này Agent 0 **dừng và báo chủ máy** kèm bằng chứng, không lặp vô hạn. |
| `max_concurrent_agents` | `3` | Số agent tương tác chạy cùng lúc (xem 6.1: công cụ chặn mở thêm). |
| `single_builder` | `true` | Chỉ **một** agent được build/chạy test nặng tại một thời điểm (các agent khác viết mã, chờ lệnh). |
| `close_on_success` | `true` | Đóng cửa sổ agent ngay khi việc đã được nghiệm thu đạt (trừ khi còn việc kế tiếp cho chính nó). |
| `hang_minutes` | `15` | Agent im lặng/không tạo tệp mới quá số phút này (hoặc có dòng lỗi timeout) ⇒ coi là treo: nhắn **một lần** "chia nhỏ việc", vẫn treo ⇒ thay cửa sổ. |
| `prompt_in_file` | `true` | Prompt giao việc phải **ghi thành tệp**; dòng gõ vào terminal chỉ trỏ tới tệp. |
| `max_line_chars` | `500` | Độ dài tối đa dòng gõ vào terminal (dòng dài bị terminal thu gọn thành văn bản dán và mất phần đầu). |
| `report_in_file` | `true` | Agent ghi **báo cáo cuối ra tệp**; trong terminal chỉ trả đường dẫn + tối đa 3 dòng tóm tắt. |
| `prompts_dir` | thư mục tạm của chủ máy ngoài repo (ví dụ `<state>/prompts`) | Nơi lưu tệp prompt/báo cáo; **ngoài** repo đích, không bị commit. Dùng làm biến `{PROMPTS_DIR}`. |
| `subagent_policy` | `allowed` | `off` / `allowed`: cho phép agent dùng **subagent tích hợp** của CLI (không mở thêm cửa sổ), với ràng buộc ở 4.3. |
| `ram_free_warn_mb` | `2000` | Dưới ngưỡng này công cụ cảnh báo và (tuỳ chọn) chặn mở agent mới (6.3). |
Biến thay thế dùng trong các ô văn bản: `{REPO}` (repo đang chọn), `{PROMPTS_DIR}`, `{MAX_FIX_ROUNDS}`, `{MAX_AGENTS_PER_TASK}`, `{MAX_CONCURRENT}`, `{PROVIDER_MODEL}`… (công cụ thay trước khi tiêm).

### 4.2 Ba ô văn bản Markdown (chủ máy sửa tự do, có giới hạn kích thước, ví dụ 20.000 ký tự mỗi ô)
1. **"Quy tắc điều phối"** — nội dung mặc định: mục 5 của tài liệu này.
2. **"Ràng buộc chung dán vào mọi prompt giao agent code"** — danh sách điều cấm/bắt buộc mà Agent 0 phải chép vào **mọi** tệp prompt (mục 5.7). Mặc định chỉ chứa các ràng buộc **chung** (không push, không `git add -A`, không `--amend`, không sửa tệp ngoài phạm vi, build tuần tự...). Từng dự án bổ sung ràng buộc riêng ở đây (ví dụ mốc cảnh báo build, thư mục không được sửa).
3. **"Checklist nghiệm thu"** — những phép kiểm Agent 0 phải làm trước khi tuyên bố đạt (mặc định mục 5.8; từng dự án thêm phép kiểm riêng như đối chiếu schema).

### 4.3 Chính sách subagent (khi `subagent_policy = allowed`)
Dùng **subagent mặc định** của CLI (ví dụ `/agents`, `/tasks` của `agy`), **không** dùng "custom agent" (nhiều báo cáo lỗi). Agent chính viết phần dùng chung trước; subagent chỉ ghi đúng thư mục được giao, **không build, không test, không commit**, không sửa tệp dùng chung; **agent chính đọc lại toàn bộ kết quả của subagent** rồi mới build/commit; báo cáo cuối nêu việc nào do subagent làm. Subagent vẫn chạy chung máy và chung cây làm việc nên **không** miễn các giới hạn ở 4.1.

## 5. Nội dung mặc định của ô "Quy tắc điều phối" (dự án-trung-lập; công cụ nạp khi khởi tạo hoặc "khôi phục mặc định")

> Quy tắc điều phối agent CMD (chủ máy cấu hình trong Cài đặt). Áp dụng mỗi khi bạn (Agent 0) giao việc cho agent ở cửa sổ CMD qua `open_terminal` / `send_to_terminal` / `read_terminal` / `close_terminal`.

**5.1 Vai trò.** Bạn chỉ điều phối và nghiệm thu bằng bằng chứng thật; không tự làm thay agent, không chạy `agy`/`claude`/`codex` bằng Bash (kể cả `--version`). Dòng `[AO] <terminal> đã xong` chỉ báo "terminal yên lặng", **không phải bằng chứng việc đã xong**: luôn đọc terminal và tệp kết quả.

**5.2 Khởi tạo agent.** Mở bằng `open_terminal(provider)` (mặc định `{PROVIDER}`), cách nhau ít nhất 1,5 giây. Với `agy` model mong đợi là **{PROVIDER_MODEL}**: đọc terminal xác nhận dòng model trước khi giao việc; sai thì gõ `/model` và nhờ chủ máy chỉnh (bạn không gửi được phím mũi tên). Chờ đăng nhập xong (hết "Signing in…", ô nhập trống) rồi mới gửi. Terminal mới mở ở repo của công cụ: luôn dặn agent chuyển tới `{REPO}` trước. Ô nhập có thể còn chữ nháp của chủ máy: đọc terminal trước khi gửi.

**5.3 Giao việc.** Viết prompt thành tệp `{PROMPTS_DIR}/PROMPT-<việc>.md`; dòng gõ vào terminal chỉ nói "đọc tệp X và làm đúng theo đó" (không quá {MAX_LINE} ký tự). Prompt có: mục tiêu; **tiêu chí đạt kiểm tra được** (tệp nào, lệnh nào phải pass, hành vi nào); phạm vi được chạm và **cấm chạm**; điều kiện bắt đầu; các lệnh kiểm; mẫu báo cáo; và toàn bộ "Ràng buộc chung" (5.7). Yêu cầu agent ghi **báo cáo ra tệp** `{PROMPTS_DIR}/BAOCAO-<việc>.md` và chỉ trả đường dẫn kèm tối đa 3 dòng. Việc dài (tài liệu > khoảng 250 dòng): bắt agent tạo tệp khung rồi **ghi từng phần < 150 dòng** (hoặc tách nhiều tệp), vì sinh một lần dài dễ bị timeout.

**5.4 Vòng lặp nghiệm thu (bắt buộc).**
1. Chờ tín hiệu rồi tự kiểm: đọc terminal (đã làm sạch), tệp báo cáo và thay đổi thật (diff, tệp mới). Không tin lời agent.
2. Nghiệm thu bằng bằng chứng (mã, tệp, lệnh kiểm theo "Checklist nghiệm thu").
3. **Chưa đạt ⇒ sửa lần 1:** viết **prompt sửa** (tệp `PROMPT-<việc>-fix1.md`, hoặc điền thẳng vào khung chat nếu rất ngắn) nêu từng mục chưa đạt kèm bằng chứng cụ thể và phần giữ nguyên. Vẫn chưa đạt ⇒ **sửa lần 2** (`-fix2.md`).
4. **Sau {MAX_FIX_ROUNDS} lần sửa vẫn chưa đạt:** `close_terminal` (chỉ đóng được cửa sổ do chính bạn mở; cửa sổ cũ vẫn nằm trong Lịch sử) ⇒ `open_terminal` **cửa sổ mới** ⇒ **bạn VIẾT LẠI prompt cho chuẩn hơn** (không chép lại nguyên văn): thêm những gì đã thử, vì sao chưa đạt (bằng chứng), tiêu chí cụ thể hơn, ví dụ đúng, điều cấm, cắt việc nhỏ hơn nếu cần ⇒ yêu cầu agent mới **xử lý tiếp** (nêu rõ phần đã đạt, giữ nguyên).
5. Tối đa **{MAX_AGENTS_PER_TASK} agent cho một việc**. Agent cuối cũng không đạt ⇒ **dừng và báo chủ máy** (agent nào, mấy lần sửa, bằng chứng, đề xuất). Không lặp vô hạn.
6. **Ngoại lệ không tính vào số lần sửa:** nguyên nhân là mâu thuẫn giữa tài liệu/quy ước với test, hoặc điều thuộc quyết định của chủ máy ⇒ dừng, hỏi chủ máy, ghi quyết định rồi mới tiếp. Agent dừng-và-báo đúng chỗ này là làm đúng.
7. **Treo/timeout** (không có tệp mới và terminal im/hiện lỗi quá {HANG_MINUTES} phút): nhắn **một lần** "chia nhỏ, ghi từng phần"; vẫn treo ⇒ coi là thất bại và thay cửa sổ như bước 4.
8. **Khi đạt:** đóng cửa sổ (trừ khi còn việc kế tiếp cho chính nó) và báo chủ máy: agent nào, mấy lần sửa, tiêu chí nào đã kiểm bằng cách nào, rủi ro còn lại.

**5.5 Tải máy và đồng thời.** Tối đa **{MAX_CONCURRENT}** agent tương tác cùng lúc. Chỉ **một** agent build/chạy test nặng tại một thời điểm (chung cây làm việc, chung thư mục build): các agent khác chỉ viết mã, chưa build, chờ lệnh của bạn. Việc song song chỉ khi thư mục được ghi không giao nhau; nêu rõ tệp dùng chung dễ xung đột. Đóng agent ngay khi việc đã được nghiệm thu. Khi nghi ngờ treo, kiểm RAM/CPU trước khi mở thêm.

**5.6 Subagent.** Theo chính sách ở Cài đặt (`{SUBAGENT_POLICY}`): nếu cho phép, áp dụng đúng mục 4.3 của tài liệu tính năng (tóm tắt: subagent mặc định, chỉ ghi thư mục được giao, không build/test/commit, agent chính đọc lại toàn bộ trước khi báo cáo).

**5.7 Ràng buộc chung dán vào mọi prompt.** Nội dung lấy từ ô "Ràng buộc chung" (chủ máy sửa). Mặc định: không push/merge nếu chủ máy chưa yêu cầu; không `git add -A`, không `--no-verify`, không `--amend`, không `checkout/reset/stash`; chỉ thêm tệp theo tên và kiểm trước khi commit; không sửa/commit tệp của người khác hay của phiên khác; commit theo **thứ tự phụ thuộc** (cái dùng đến phải commit trước); không kill tiến trình không phải của mình; chỉ một agent build tại một thời điểm; không bịa tên tệp/hàm/cột (không thấy sau hai lần tìm thì dừng và hỏi); báo cáo ra tệp (5.3).

**5.8 Checklist nghiệm thu.** Nội dung lấy từ ô "Checklist" (chủ máy sửa). Mặc định: đọc `git status`/`git diff` của thay đổi thật; đối chiếu tên tệp/hàm/trường trong báo cáo với mã thật (từng có báo cáo ghi sai tên dù mã đúng); chạy lại lệnh kiểm quan trọng thay vì chỉ tin số agent báo (nếu không đo lại được thì nói rõ "số do agent báo"); kiểm agent có tự nới một luật hay một test để qua; kiểm tệp ngoài phạm vi không bị đụng.

**5.9 Lặp lại ở phiên mới.** Đầu mỗi phiên bạn đọc lại bộ quy tắc này (có thể gọi `get_orchestration_rules`), xem sổ vòng nghiệm thu (nếu có, 6.4), rồi `list_terminals` để biết agent nào đang chạy trước khi giao việc mới.

## 6. Phần công cụ tự thực thi (ngoài chữ trong prompt)
Chia pha để cài đặt dần; **Pha 1 là bắt buộc**, các pha sau là mong muốn.

### 6.1 Pha 1 — lưu, sửa, tiêm, giới hạn đồng thời
- Lưu cấu hình (4.1, 4.2) trong CSDL của công cụ; API chỉ cho chủ máy sửa (cùng cơ chế xác thực/chống CSRF của `/api/settings`).
- Soạn **tệp prompt Agent 0 đã ghép** = nội dung `examples/AGENT0-PROMPT.md` (phần lõi cố định) + mục "Quy tắc điều phối" đã thay biến + ba ô văn bản; ghi vào thư mục trạng thái (ví dụ `state/agent0-prompt.generated.md`) và truyền cho Claude Code qua `--append-system-prompt-file` (hiện chỉ một tệp: ghép thành một tệp). Gọi mỗi lần `agent0_argv` chạy (mở mới, khởi động lại, resume).
- **Kiểm chứng bắt buộc (chưa kiểm):** khi dùng `--resume <session>`, Claude Code có áp lại system prompt bổ sung mới hay giữ bản cũ của phiên? Nếu giữ bản cũ, phải có cách khiến Agent 0 nhận quy tắc mới (ví dụ buộc `get_orchestration_rules`, hoặc gửi một dòng nhắc khi resume). Ghi kết quả vào nhật ký.
- Công cụ MCP mới `get_orchestration_rules` (chỉ-đọc; thêm vào `AGENT0_TOOLS`) trả bản hiện hành đã thay biến.
- **Chặn mở quá `max_concurrent_agents`:** `open_terminal` cho agent tương tác trả lỗi tiếng Việt rõ ràng ("Đã đạt giới hạn N agent đang chạy; đóng bớt một cửa sổ đã xong rồi thử lại") khi vượt giới hạn; giới hạn tính trên cửa sổ agent đang sống, không tính Agent 0. Đã có hằng `MAX_SESSIONS` và `evict_finished()` trong `terminals.py`: dùng/ghép, đừng làm trùng.

### 6.2 Pha 2 — nhận diện treo/lỗi và model
- Mở rộng `notify_agent0`/`terminal_looks_busy` để nhận diện các dấu hiệu lỗi đã gặp ở `agy` (ví dụ dòng `agent executor error` / `stream idle timeout`) và gửi dòng thông báo **khác** "đã xong": ví dụ `[AO] agy-N có lỗi: <rút gọn>` (không bắn lặp). Giữ nguyên thông báo "đã xong" cho tương thích test hiện có.
- Với mỗi agent tương tác, **đọc model từ footer** (ví dụ `Gemini 4 Argon · medium`) và đưa vào kết quả `list_terminals` (trường mới, chỉ đọc, có thể rỗng) cùng huy hiệu trên giao diện, để Agent 0 và chủ máy thấy ngay agent đang chạy sai model.

### 6.3 Pha 2 — giám sát tài nguyên
- Lấy mẫu RAM trống/CPU của máy chủ máy (nhẹ, theo chu kỳ) và hiện ở thanh trạng thái; khi RAM trống < `ram_free_warn_mb` thì (a) hiện cảnh báo, (b) kèm vào thông báo `[AO]`, (c) tuỳ chọn chặn `open_terminal` mới. Chỉ **đọc** số liệu hệ điều hành, không can thiệp tiến trình khác. Windows là môi trường chính; trên hệ khác trả "không có số liệu".

### 6.4 Pha 3 — sổ vòng nghiệm thu (nhớ giữa các phiên chat)
- Bảng mới trong CSDL (ví dụ `review_ledger`): mỗi dòng = một **việc** (tên ngắn, repo, tệp prompt, agent đang giữ, số lần sửa, số cửa sổ đã dùng, trạng thái ∈ `đang làm` / `sửa 1` / `sửa 2` / `đã thay cửa sổ` / `đạt` / `báo chủ máy`, thời điểm, ghi chú/bằng chứng ngắn).
- Công cụ MCP cho Agent 0: `ledger_list`, `ledger_upsert` (tên/trạng thái/ghi chú; **công cụ tự tăng bộ đếm** khi Agent 0 báo "sửa" hoặc "thay cửa sổ" và **cảnh báo khi vượt `max_fix_rounds`/`max_agents_per_task`**, không chỉ nhờ Agent 0 nhớ). Hiện trong giao diện thành bảng "Vòng nghiệm thu".
- Mục đích: phiên chat mới của Agent 0 đọc sổ là biết việc nào đang sửa lần mấy, agent nào đã bị thay, không phải dựa vào bản ghi tay.

## 7. Giao diện (theo `docs/UI-RULES.md`)
- Mục "Quy tắc điều phối agent" trong khu Cài đặt hiện có (hiện có biểu tượng cài đặt cửa sổ CMD và các công tắc `default_remember`, `notify_agent0`). Mọi `input`/`select`/`textarea` theo token `--ao-*` và khối "QUY TẮC FORM CONTROL" trong `style.css`.
- Thành phần: các trường tham số (4.1) với giá trị mặc định hiển thị mờ và kiểm giá trị ngay; ba vùng soạn Markdown (4.2) kèm bộ đếm ký tự; nút **Xem trước** (nội dung Agent 0 sẽ nhận sau khi thay biến, dạng chỉ đọc); **Lưu**, **Khôi phục mặc định** (hỏi xác nhận), **Lịch sử** (giữ ví dụ 20 bản gần nhất, xem và khôi phục), **Xuất `.md`** và **Nhập `.md`** (kiểm cấu trúc); dòng trạng thái "Agent 0 đang chạy đã/chưa nhận bản này" + nút khởi động lại.
- Mỗi tham số có chú thích một dòng tiếng Việt. Văn bản thân thiện, không lộ chi tiết nội bộ (đường dẫn trạng thái, SQL).
- Sau khi sửa UI: chụp ảnh thật ở khổ rộng và hẹp bằng `node tools/ui_shots.cjs` và xem ảnh (jsdom không bắt được lỗi bố cục), đúng yêu cầu của `CLAUDE.md` repo này.

## 8. API (đề xuất; theo phong cách `web.py` hiện có: kiểm tra chặt khoá và kiểu)
- `GET /api/orchestration-rules` → toàn bộ cấu hình + bản đã ghép + `default` + `applied_to_agent0` (bool).
- `PUT /api/orchestration-rules` → ghi (chỉ các khoá trong danh sách cho phép, kiểm kiểu/miền giá trị/kích thước; trả lỗi tiếng Việt cụ thể; không nhận khoá lạ).
- `POST /api/orchestration-rules/reset` → khôi phục mặc định.
- `GET /api/orchestration-rules/history` và `POST …/restore`.
- (Pha 3) `GET/POST /api/ledger…`.
- Mở rộng (hoặc không đụng) `/api/settings` hiện chỉ nhận **một** khoá boolean trong `{default_remember, notify_agent0}`: **không** nhồi cấu hình mới vào endpoint đó; dùng endpoint riêng ở trên.
- Có thể cho **ghi đè theo repo** (`cfg.repos` có nhiều repo): khoá cấu hình thêm `repo` tuỳ chọn; thiếu thì dùng bản chung.

## 9. Đã kiểm trong mã (09/11/2026), làm điểm bám cho người cài đặt
- `agent_orchestrator/terminals.py`: `AGENT0_TOOLS` (dòng ~38), `AGENT0_DENIED` (~41, gồm `Bash(agy:*)`…), `agent0_argv(resume, session_id)` (~1209–1233; ghi `agent0-mcp.json`, thêm `--append-system-prompt-file examples/AGENT0-PROMPT.md` nếu tệp tồn tại), `restart_agent0` (~1499), `notify_agent0` (~1037–1100, tôn trọng `db.setting('notify_agent0', True)`), `agent0_opened` (~898, chỉ đóng được cửa sổ do Agent 0 mở), `close` (~1154–1165), `MAX_SESSIONS` và `evict_finished` (~1355).
- `agent_orchestrator/store.py`: bảng `settings(key, value)` (~48), `setting(key, default)` và `set_setting(key, value)` (~290–296, giá trị lưu JSON), `agents.settings` (JSON theo agent) và `agent_setting` (~278–287).
- `agent_orchestrator/web.py`: `/api/settings` (~438–445, chỉ nhận **một** khoá `default_remember` hoặc `notify_agent0`, kiểu bool); `/api/agents/<n>/settings` (~446–454, chỉ `remember_context`; ghi chú "Whitelisted keys only; add new per-agent options here and in the dashboard's settingDefs list").
- `examples/AGENT0-PROMPT.md` (122 dòng): mục "Giao việc cho agent tương tác rồi đánh giá, sửa, thay cửa sổ" (dòng ~91–101) hiện chứa phiên bản rút gọn của vòng lặp; tính năng này **thay phần cứng đó bằng nội dung cấu hình được** (giữ lại bản mặc định tương đương để không mất hành vi hiện có).
- `agent_orchestrator/web_assets/index.html`: khung cài đặt cửa sổ CMD `ao-console-settings-panel` (~78); `app.js`: nút mở/đóng (~1359–1362) và danh sách `settingDefs`.
- `NhatKyCongViec/2026-11-08-thong-bao-xong-va-vong-lap-agent0.md`: lịch sử vì sao dòng `[AO] đã xong` chỉ là gợi ý và vì sao `close_terminal` chỉ đóng cửa sổ do Agent 0 mở.
- Quy ước repo (`CLAUDE.md`): chạy test Python `.\.runtime\python\python.exe -m unittest discover -s tests -p "test_*.py"` (khoảng 5–8 phút), test UI `node tests/flow_ui.cjs`, `node tests/layout_ui.cjs`; không push/merge `main` nếu chưa được yêu cầu; ghi nhật ký vào `NhatKyCongViec/`.
- **[chưa kiểm]**: `--append-system-prompt-file` có nhận nhiều tệp không; hành vi system prompt khi `--resume`; chính xác tên/khuôn dạng footer model của từng CLI; `agy` có cờ dòng lệnh chọn model/effort không (nếu có, công cụ có thể tự đặt thay vì chỉ nhờ chủ máy chỉnh).

## 10. Tiêu chí chấp nhận
**Pha 1**
1. Chủ máy mở Cài đặt, thấy mục "Quy tắc điều phối agent" với giá trị mặc định đúng mục 4.1 và 5; sửa một tham số và một ô văn bản, bấm Lưu, tải lại trang vẫn còn.
2. Khôi phục mặc định trả về đúng nội dung mục 5 và tham số mặc định.
3. Mở/khởi động lại/resume Agent 0 ⇒ tệp prompt đã ghép được truyền và **chứa** bản mới (test đọc tệp ghép và đối số dòng lệnh; không cần chạy Claude thật). Có kết quả kiểm chứng `--resume` (mục 9, ghi nhật ký).
4. `get_orchestration_rules` có trong `AGENT0_TOOLS`, chỉ-đọc, trả bản hiện hành đã thay biến; **không** có công cụ ghi quy tắc cho Agent 0 (Agent 0 không được tự sửa quy tắc của chủ máy).
5. Đặt `max_concurrent_agents = 2`: mở agent tương tác thứ ba bị từ chối với thông báo tiếng Việt rõ; đóng một cái thì mở được.
6. Quy tắc tuỳ chỉnh **không** làm mất `AGENT0_DENIED`/danh sách công cụ cho phép (test).
7. API từ chối khoá lạ, kiểu sai, giá trị ngoài miền, nội dung quá lớn; test đủ nhánh. Không rò rỉ đường dẫn nội bộ trong lỗi.
8. Toàn bộ test Python hiện có vẫn xanh; thêm test mới cho: lưu/đọc/mặc định/lịch sử, ghép prompt (có và không có tệp phụ), thay biến (kể cả biến không tồn tại ⇒ giữ nguyên hoặc báo lỗi rõ), giới hạn đồng thời, kiểm giá trị API. Test UI jsdom mới cho luồng sửa/lưu/xem trước/khôi phục; ảnh chụp thật hai khổ đã xem.
**Pha 2/3:** theo mục 6.2–6.4 (có test riêng: nhận diện dòng lỗi giả lập không bắn lặp; trường `model` đúng từ footer mẫu; số liệu RAM giả lập; sổ vòng nghiệm thu tăng bộ đếm đúng và cảnh báo khi vượt giới hạn).

## 11. Việc ngoài phạm vi
- Không tự động đổi model của CLI nếu CLI không cung cấp cờ (chỉ nhắc/kiểm).
- Không sửa quyền của Claude Code, không nới `AGENT0_DENIED`, không cài dịch vụ nền, không tự push/merge.
- Không đồng bộ quy tắc vào `CLAUDE.md`/`AGENTS.md` của repo đích (chủ ý: cấu hình thuộc công cụ).
- Không đổi cách Agent 0 gọi công cụ hiện có.

## 12. Câu hỏi mở cho chủ máy (người cài đặt hỏi trước khi làm)
1. Thư mục mặc định cho tệp prompt/báo cáo: thư mục tạm riêng của công cụ (đề xuất `<state>/prompts`) hay thư mục do chủ máy chọn (đang dùng `Downloads` thủ công)? Agent worker phải đọc/ghi được thư mục này.
2. Có cần ghi đè quy tắc **theo từng repo** ngay từ Pha 1 không, hay chung toàn công cụ trước?
3. Pha 3 (sổ vòng nghiệm thu) có làm ngay sau Pha 1 không, hay chờ dùng thử?
4. `max_concurrent_agents` là cứng (chặn) hay mềm (cảnh báo)? Đề xuất cứng, có công tắc "cho vượt tạm thời" cho chủ máy.
5. Danh sách model hợp lệ cho `agy` lấy ở đâu (gõ tay hay đọc từ CLI)?

## Phụ lục A — Bài học thực tế dẫn tới các quy tắc (dự án HIS_EMR, 09/11/2026; tham khảo, không đưa vào mặc định)
- **Tải máy:** 6 cửa sổ `agy` + nhiều tiến trình `dotnet` ⇒ RAM trống 0,9/15,8 GB, CPU 100%; một agent báo `stream idle timeout (5m0s)` khi sinh tài liệu dài, một agent treo ~40 phút. ⇒ giới hạn đồng thời, chia nhỏ việc, nhận diện treo, đóng khi xong.
- **`[AO] đã xong` sai/sớm** hàng chục lần (terminal chỉ yên lặng). ⇒ luôn đọc terminal và tệp; thêm thông báo lỗi riêng (6.2).
- **Agent bịa chi tiết** (tên bảng/cột không có trong schema, mã quyền sai cơ chế, báo cáo ghi sai tên dù mã đúng). ⇒ nghiệm thu bằng bằng chứng, checklist có phép đối chiếu.
- **Hai agent build cùng cây** làm lỗi biên dịch giả. ⇒ `single_builder`.
- **Commit sai thứ tự phụ thuộc** làm một commit không biên dịch riêng. ⇒ ràng buộc "commit theo thứ tự phụ thuộc".
- **Mâu thuẫn tài liệu/test** (agent dừng đúng và báo, không tự nới test). ⇒ ngoại lệ không tính vào số lần sửa (5.4.6).
- **Prompt dài gõ một dòng** bị cắt mất phần đầu. ⇒ prompt thành tệp, dòng ngắn (`max_line_chars`).
- **Báo cáo dán dài trong terminal** khó đọc. ⇒ báo cáo ra tệp (`report_in_file`).
