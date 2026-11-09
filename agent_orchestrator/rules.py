"""Quy tắc điều phối agent CMD do chủ máy cấu hình (docs/TINH-NANG-QUY-TAC-DIEU-PHOI-AGENT.md, Pha 1).

Quy tắc là dữ liệu của chủ máy (bảng settings của công cụ), không đọc từ repo đích và worker không sửa được. Chúng chỉ
*bổ sung chỉ dẫn / giới hạn chặt hơn* cho Agent 0: danh sách công cụ cho phép và AGENT0_DENIED nằm trong terminals.py và không
phụ thuộc vào module này.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .config import OrchError

SETTING_KEY = 'orchestration_rules'
HISTORY_KEY = 'orchestration_rules_history'
APPLIED_KEY = 'orchestration_rules_applied'
HISTORY_LIMIT = 20
TEXT_LIMIT = 15000
PROVIDERS = ('agy', 'claude', 'codex')
EFFORTS = ('', 'low', 'medium', 'high')
SUBAGENT_POLICIES = ('off', 'allowed')

DEFAULT_PARAMS = {
    'default_provider': 'agy',
    'provider_models': {'agy': {'model': 'Gemini 4 Argon', 'effort': 'medium'},
                        'claude': {'model': '', 'effort': ''},
                        'codex': {'model': '', 'effort': ''}},
    'max_fix_rounds': 2,
    'max_agents_per_task': 2,
    'max_concurrent_agents': 3,
    'concurrency_enforced': True,
    'single_builder': True,
    'close_on_success': True,
    'hang_minutes': 15,
    'prompt_in_file': True,
    'max_line_chars': 500,
    'report_in_file': True,
    'prompts_dir': '',
    'subagent_policy': 'allowed',
    'ram_free_warn_mb': 2000,
}
INT_RANGES = {'max_fix_rounds': (0, 10), 'max_agents_per_task': (1, 10), 'max_concurrent_agents': (1, 12), 'hang_minutes': (1, 240),
              'max_line_chars': (80, 4000), 'ram_free_warn_mb': (0, 1_000_000)}
BOOLS = ('concurrency_enforced', 'single_builder', 'close_on_success', 'prompt_in_file', 'report_in_file')

DEFAULT_RULES = """Quy tắc điều phối agent CMD (chủ máy cấu hình trong Cài đặt). Áp dụng mỗi khi bạn (Agent 0) giao việc cho agent ở cửa sổ CMD qua `open_terminal` / `send_to_terminal` / `read_terminal` / `close_terminal`.

**1. Vai trò.** Bạn chỉ điều phối và nghiệm thu bằng bằng chứng thật; không tự làm thay agent, không chạy `agy`/`claude`/`codex` bằng Bash (kể cả `--version`). Dòng `[AO] <terminal> đã xong` chỉ báo "terminal yên lặng", **không phải bằng chứng việc đã xong**: luôn đọc terminal và tệp kết quả.

**2. Khởi tạo agent.** Mở bằng `open_terminal(provider)` (mặc định `{PROVIDER}`), cách nhau ít nhất 1,5 giây. Model mong đợi của `{PROVIDER}` là **{PROVIDER_MODEL}**: đọc terminal xác nhận dòng model trước khi giao việc; sai thì gõ `/model` và nhờ chủ máy chỉnh (bạn không gửi được phím mũi tên). Chờ đăng nhập xong (hết "Signing in…", ô nhập trống) rồi mới gửi. Terminal mới mở ở repo của công cụ: luôn dặn agent chuyển tới `{REPO}` trước. Ô nhập có thể còn chữ nháp của chủ máy: đọc terminal trước khi gửi.

**3. Giao việc.** Viết prompt thành tệp `{PROMPTS_DIR}/PROMPT-<việc>.md`; dòng gõ vào terminal chỉ nói "đọc tệp X và làm đúng theo đó" (không quá {MAX_LINE} ký tự). Prompt có: mục tiêu; **tiêu chí đạt kiểm tra được** (tệp nào, lệnh nào phải pass, hành vi nào); phạm vi được chạm và **cấm chạm**; điều kiện bắt đầu; các lệnh kiểm; mẫu báo cáo; và toàn bộ "Ràng buộc chung" ở mục 7. Yêu cầu agent ghi **báo cáo ra tệp** `{PROMPTS_DIR}/BAOCAO-<việc>.md` và chỉ trả đường dẫn kèm tối đa 3 dòng. Việc dài (tài liệu hơn khoảng 250 dòng): bắt agent tạo tệp khung rồi **ghi từng phần dưới 150 dòng** (hoặc tách nhiều tệp), vì sinh một lần dài dễ bị timeout.

**4. Vòng lặp nghiệm thu (bắt buộc).**
1. Chờ tín hiệu rồi tự kiểm: đọc terminal (đã làm sạch), tệp báo cáo và thay đổi thật (diff, tệp mới). Không tin lời agent.
2. Nghiệm thu bằng bằng chứng (mã, tệp, lệnh kiểm theo "Checklist nghiệm thu" ở mục 8).
3. **Chưa đạt thì sửa lần 1:** viết **prompt sửa** (tệp `PROMPT-<việc>-fix1.md`, hoặc điền thẳng vào khung chat nếu rất ngắn) nêu từng mục chưa đạt kèm bằng chứng cụ thể và phần giữ nguyên. Vẫn chưa đạt thì **sửa lần 2** (`-fix2.md`), và cứ thế đến lần thứ {MAX_FIX_ROUNDS}.
4. **Sau {MAX_FIX_ROUNDS} lần sửa vẫn chưa đạt:** `close_terminal` (chỉ đóng được cửa sổ do chính bạn mở; cửa sổ cũ vẫn nằm trong Lịch sử), rồi `open_terminal` **cửa sổ mới**, rồi **bạn VIẾT LẠI prompt cho chuẩn hơn** (không chép lại nguyên văn): thêm những gì đã thử, vì sao chưa đạt (bằng chứng), tiêu chí cụ thể hơn, ví dụ đúng, điều cấm, cắt việc nhỏ hơn nếu cần; yêu cầu agent mới **xử lý tiếp** (nêu rõ phần đã đạt, giữ nguyên).
5. Tối đa **{MAX_AGENTS_PER_TASK} agent cho một việc**. Agent cuối cũng không đạt thì **dừng và báo chủ máy** (agent nào, mấy lần sửa, bằng chứng, đề xuất). Không lặp vô hạn.
6. **Ngoại lệ không tính vào số lần sửa:** nguyên nhân là mâu thuẫn giữa tài liệu/quy ước với test, hoặc điều thuộc quyết định của chủ máy: dừng, hỏi chủ máy, ghi quyết định rồi mới tiếp. Agent dừng-và-báo đúng chỗ này là làm đúng.
7. **Treo/timeout** (không có tệp mới và terminal im hoặc hiện lỗi quá {HANG_MINUTES} phút): nhắn **một lần** "chia nhỏ, ghi từng phần"; vẫn treo thì coi là thất bại và thay cửa sổ như bước 4.
8. **Khi đạt:** đóng cửa sổ (trừ khi còn việc kế tiếp cho chính nó, hoặc chủ máy chưa cho đóng) và báo chủ máy: agent nào, mấy lần sửa, tiêu chí nào đã kiểm bằng cách nào, rủi ro còn lại.

**5. Tải máy và đồng thời.** Tối đa **{MAX_CONCURRENT}** agent tương tác cùng lúc. Chỉ **một** agent build/chạy test nặng tại một thời điểm (chung cây làm việc, chung thư mục build): các agent khác chỉ viết mã, chưa build, chờ lệnh của bạn. Việc song song chỉ khi thư mục được ghi không giao nhau; nêu rõ tệp dùng chung dễ xung đột. Đóng agent ngay khi việc đã được nghiệm thu. Khi nghi ngờ treo, kiểm RAM/CPU trước khi mở thêm.

**6. Subagent.** Chính sách hiện hành: **{SUBAGENT_POLICY}**. Nếu `allowed`: chỉ dùng **subagent mặc định** của CLI (ví dụ `/agents`, `/tasks` của `agy`), **không** dùng "custom agent". Agent chính viết phần dùng chung trước; subagent chỉ ghi đúng thư mục được giao, **không build, không test, không commit**, không sửa tệp dùng chung; **agent chính đọc lại toàn bộ kết quả của subagent** rồi mới build/commit; báo cáo cuối nêu việc nào do subagent làm. Subagent vẫn chạy chung máy và chung cây làm việc nên **không** miễn các giới hạn ở mục 5. Nếu `off`: dặn agent không dùng subagent.

**7. Ràng buộc chung dán vào mọi prompt.** Chép nguyên văn phần "Ràng buộc chung" (bên dưới) vào **mọi** tệp prompt giao cho agent code.

**8. Checklist nghiệm thu.** Trước khi tuyên bố đạt, làm đủ phần "Checklist nghiệm thu" (bên dưới).

**9. Lặp lại ở phiên mới.** Đầu mỗi phiên bạn đọc lại bộ quy tắc này (gọi `get_orchestration_rules`; nhất là sau khi cuộc trò chuyện bị nén hoặc mở lại), rồi `list_terminals` để biết agent nào đang chạy trước khi giao việc mới."""

DEFAULT_CONSTRAINTS = """- Không push, không merge nếu chủ máy chưa yêu cầu.
- Không `git add -A`, không `--no-verify`, không `--amend`, không `checkout`/`reset`/`stash`; chỉ thêm tệp theo tên và kiểm trước khi commit.
- Không sửa hay commit tệp của người khác hoặc của phiên khác; không sửa tệp ngoài phạm vi được giao.
- Commit theo **thứ tự phụ thuộc** (cái được dùng đến phải commit trước).
- Không kill tiến trình không phải của mình; chỉ một agent build tại một thời điểm.
- Không bịa tên tệp/hàm/cột: không thấy sau hai lần tìm thì dừng và hỏi.
- Báo cáo cuối ghi ra tệp, trong terminal chỉ trả đường dẫn kèm tối đa 3 dòng."""

DEFAULT_CHECKLIST = """- Đọc `git status` và `git diff` của thay đổi thật.
- Đối chiếu tên tệp/hàm/trường trong báo cáo với mã thật (từng có báo cáo ghi sai tên dù mã đúng).
- Chạy lại lệnh kiểm quan trọng thay vì chỉ tin số agent báo; nếu không đo lại được thì nói rõ "số do agent báo".
- Kiểm agent có tự nới một luật hay một test để qua.
- Kiểm tệp ngoài phạm vi không bị đụng."""

DEFAULT_TEXTS = {'rules': DEFAULT_RULES, 'constraints': DEFAULT_CONSTRAINTS, 'checklist': DEFAULT_CHECKLIST}
TEXT_TITLES = {'rules': 'Quy tắc điều phối', 'constraints': 'Ràng buộc chung', 'checklist': 'Checklist nghiệm thu'}
VARIABLES = ('REPO', 'PROMPTS_DIR', 'PROVIDER', 'PROVIDER_MODEL', 'MAX_FIX_ROUNDS', 'MAX_AGENTS_PER_TASK', 'MAX_CONCURRENT', 'MAX_LINE',
             'HANG_MINUTES', 'SUBAGENT_POLICY')
_VAR = re.compile(r'\{([A-Z_]+)\}')


def defaults():
    return json.loads(json.dumps({'params': DEFAULT_PARAMS, 'texts': DEFAULT_TEXTS}))


def _text(value, name):
    if not isinstance(value, str):
        raise OrchError(f'"{name}" phải là chuỗi văn bản')
    if '\x00' in value:
        raise OrchError(f'"{name}" chứa ký tự không hợp lệ')
    if len(value) > TEXT_LIMIT:
        raise OrchError(f'"{name}" dài quá {TEXT_LIMIT} ký tự (hiện {len(value)})')
    return value.replace('\r\n', '\n')


def _prompts_dir(value, repos):
    if not isinstance(value, str) or len(value) > 260 or any(ord(c) < 32 for c in value):
        raise OrchError('Thư mục prompt không hợp lệ')
    value = value.strip()
    if not value:
        return ''
    path = Path(value)
    if not path.is_absolute():
        raise OrchError('Thư mục prompt phải là đường dẫn tuyệt đối (hoặc để trống để dùng thư mục mặc định)')
    try:
        resolved = path.resolve()
        for repo in repos or ():
            root = Path(repo).resolve()
            if resolved == root or root in resolved.parents:
                raise OrchError('Thư mục prompt phải nằm ngoài repo để không bị commit nhầm')
    except OSError:
        raise OrchError('Thư mục prompt không hợp lệ') from None
    return str(path)


def validate(data, repos=()):
    """Kiểm chặt bản cấu hình gửi lên. Chỉ nhận khoá đã biết, đúng kiểu, đúng miền giá trị. Trả bản đầy đủ đã chuẩn hoá."""
    if not isinstance(data, dict) or set(data) - {'params', 'texts'}:
        raise OrchError('Chỉ nhận "params" và "texts"')
    out = defaults()
    params = data.get('params', {})
    texts = data.get('texts', {})
    if not isinstance(params, dict) or not isinstance(texts, dict):
        raise OrchError('"params" và "texts" phải là đối tượng')
    unknown = set(params) - set(DEFAULT_PARAMS)
    if unknown:
        raise OrchError('Tham số không được hỗ trợ: ' + ', '.join(sorted(map(str, unknown)))[:200])
    unknown = set(texts) - set(DEFAULT_TEXTS)
    if unknown:
        raise OrchError('Ô văn bản không được hỗ trợ: ' + ', '.join(sorted(map(str, unknown)))[:200])
    p = out['params']
    for key, value in params.items():
        if key == 'default_provider':
            if value not in PROVIDERS:
                raise OrchError('default_provider phải là một trong: ' + ', '.join(PROVIDERS))
            p[key] = value
        elif key == 'provider_models':
            if not isinstance(value, dict) or set(value) - set(PROVIDERS):
                raise OrchError('provider_models chỉ nhận ' + ', '.join(PROVIDERS))
            for prov, item in value.items():
                if not isinstance(item, dict) or set(item) - {'model', 'effort'}:
                    raise OrchError(f'provider_models.{prov} chỉ nhận model và effort')
                model, effort = item.get('model', ''), item.get('effort', '')
                if not isinstance(model, str) or len(model) > 80 or any(ord(c) < 32 for c in model):
                    raise OrchError(f'Tên model của {prov} không hợp lệ (tối đa 80 ký tự)')
                if effort not in EFFORTS:
                    raise OrchError(f'Mức suy luận của {prov} phải là: trống, low, medium hoặc high')
                p['provider_models'][prov] = {'model': model.strip(), 'effort': effort}
        elif key in INT_RANGES:
            lo, hi = INT_RANGES[key]
            if type(value) is not int or not lo <= value <= hi:
                raise OrchError(f'{key} phải là số nguyên từ {lo} đến {hi}')
            p[key] = value
        elif key in BOOLS:
            if not isinstance(value, bool):
                raise OrchError(f'{key} phải là true hoặc false')
            p[key] = value
        elif key == 'subagent_policy':
            if value not in SUBAGENT_POLICIES:
                raise OrchError('subagent_policy phải là off hoặc allowed')
            p[key] = value
        elif key == 'prompts_dir':
            p[key] = _prompts_dir(value, repos)
    for key, value in texts.items():
        out['texts'][key] = _text(value, TEXT_TITLES[key])
    return out


def load(db):
    """Cấu hình hiện hành = mặc định + phần chủ máy đã lưu (khoá mới thêm sau này tự lấy mặc định)."""
    out = defaults()
    saved = db.setting(SETTING_KEY, None)
    if isinstance(saved, dict):
        for key, value in (saved.get('params') or {}).items():
            if key == 'provider_models' and isinstance(value, dict):
                for prov, item in value.items():
                    if prov in out['params']['provider_models'] and isinstance(item, dict):
                        out['params']['provider_models'][prov].update({k: v for k, v in item.items() if k in ('model', 'effort')})
            elif key in out['params']:
                out['params'][key] = value
        for key, value in (saved.get('texts') or {}).items():
            if key in out['texts'] and isinstance(value, str):
                out['texts'][key] = value
    return out


def history(db):
    items = db.setting(HISTORY_KEY, [])
    return items if isinstance(items, list) else []


def save(db, data, repos=()):
    """Ghi bản mới (đã kiểm). Bản cũ được đẩy vào lịch sử (tối đa HISTORY_LIMIT) nếu có khác biệt."""
    new = validate(data, repos)
    old = load(db)
    if new != old:
        items = history(db)
        items.insert(0, {'time': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'params': old['params'], 'texts': old['texts']})
        db.set_setting(HISTORY_KEY, items[:HISTORY_LIMIT])
    db.set_setting(SETTING_KEY, new)
    return new


def reset(db):
    return save(db, defaults())


def restore(db, index, repos=()):
    items = history(db)
    if type(index) is not int or not 0 <= index < len(items):
        raise OrchError('Không có bản lịch sử này')
    item = items[index]
    return save(db, {'params': item.get('params', {}), 'texts': item.get('texts', {})}, repos)


def prompts_dir(cfg, params):
    chosen = params.get('prompts_dir') or ''
    return Path(chosen) if chosen else Path(cfg.state) / 'prompts'


def render(cfg, rules):
    """Nội dung Agent 0 sẽ nhận sau khi thay biến. Trả (markdown, danh sách biến lạ)."""
    p = rules['params']
    prov = p['default_provider']
    model = p['provider_models'].get(prov, {})
    model_text = (model.get('model') or 'không chỉ định') + (f' ({model["effort"]})' if model.get('effort') else '')
    values = {'REPO': str(cfg.repo), 'PROMPTS_DIR': str(prompts_dir(cfg, p)), 'PROVIDER': prov, 'PROVIDER_MODEL': model_text,
              'MAX_FIX_ROUNDS': str(p['max_fix_rounds']), 'MAX_AGENTS_PER_TASK': str(p['max_agents_per_task']),
              'MAX_CONCURRENT': str(p['max_concurrent_agents']), 'MAX_LINE': str(p['max_line_chars']),
              'HANG_MINUTES': str(p['hang_minutes']), 'SUBAGENT_POLICY': p['subagent_policy']}
    unknown = set()

    def sub(match):
        name = match.group(1)
        if name in values:
            return values[name]
        unknown.add(name)
        return match.group(0)

    def fill(text):
        return _VAR.sub(sub, text)

    yes = lambda flag: 'bật' if flag else 'tắt'
    settings = [
        f'- Agent tương tác chạy cùng lúc tối đa: {p["max_concurrent_agents"]} ({"công cụ chặn mở thêm" if p["concurrency_enforced"] else "chỉ cảnh báo, không chặn"}).',
        f'- Chỉ một agent build/chạy test nặng tại một thời điểm: {yes(p["single_builder"])}.',
        f'- Đóng cửa sổ ngay khi việc đã nghiệm thu đạt: {yes(p["close_on_success"])}.',
        f'- Prompt giao việc phải ghi thành tệp (dòng gõ vào terminal chỉ trỏ tới tệp): {yes(p["prompt_in_file"])}.',
        f'- Báo cáo cuối ghi ra tệp: {yes(p["report_in_file"])}.',
        f'- Thư mục tệp prompt/báo cáo: {values["PROMPTS_DIR"]}',
        f'- Cảnh báo khi RAM trống dưới {p["ram_free_warn_mb"]} MB.']
    parts = [fill(rules['texts']['rules']).strip(),
             '### Ràng buộc chung (chép vào mọi prompt giao agent code)\n\n' + fill(rules['texts']['constraints']).strip(),
             '### Checklist nghiệm thu\n\n' + fill(rules['texts']['checklist']).strip(),
             '### Thiết lập hiện hành\n\n' + '\n'.join(settings)]
    return '\n\n'.join(parts) + '\n', sorted(unknown)


def digest(markdown):
    return hashlib.sha256(markdown.encode('utf-8')).hexdigest()[:16]


def current(cfg, db):
    rules = load(db)
    markdown, unknown = render(cfg, rules)
    return rules, markdown, unknown


def write_generated(cfg, db, core_file):
    """Ghép prompt lõi (examples/AGENT0-PROMPT.md) với quy tắc hiện hành, ghi vào thư mục trạng thái. Trả đường dẫn tệp."""
    rules, markdown, _ = current(cfg, db)
    core = ''
    try:
        if core_file and Path(core_file).is_file():
            core = Path(core_file).read_text(encoding='utf-8').rstrip() + '\n\n'
    except OSError:
        core = ''
    text = core + '## Quy tắc điều phối agent CMD (chủ máy cấu hình)\n\n' + markdown
    try:
        prompts_dir(cfg, rules['params']).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    path = Path(cfg.state) / 'agent0-prompt.generated.md'
    path.write_text(text, encoding='utf-8')
    db.set_setting(APPLIED_KEY, digest(markdown))
    return path
