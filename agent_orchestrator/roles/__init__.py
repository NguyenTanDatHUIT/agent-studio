"""Thư viện vai trò chuyên môn (Role Profiles) và mẫu bàn giao chuẩn hóa cho Agent Studio.

Được chắt lọc và chuẩn hóa từ bộ Agency Agents (NEXUS) sang dạng tinh gọn, trung lập dự án,
tương thích với cả hai luồng của công cụ:
- Agent tương tác CMD (agy, claude, codex): đọc trực tiếp tệp trong {ROLES_DIR} (<prompts_dir>/roles).
- Worker hàng đợi (claude, codex trong worktree cô lập): công cụ nhúng trực tiếp nội dung vai trò vào worker_prompt.

Nguyên tắc an toàn: vai trò chỉ bổ sung kỷ luật chuyên môn chặt hơn; không bao giờ ghi đè
phạm vi allow_paths, ràng buộc chung của chủ máy hay chính sách cấm công cụ của Agent Studio.
"""
from __future__ import annotations

from pathlib import Path

from ..config import OrchError

PACKAGE_DIR = Path(__file__).resolve().parent

# Danh mục vai trò chuyên môn có thể gắn trực tiếp vào task (role=...) hoặc trỏ từ prompt terminal.
ROLES = (
    {
        'slug': 'minimal-change',
        'category': 'coding',
        'label': 'Sửa tối giản (Minimal Change)',
        'summary': 'Diff nhỏ nhất giải quyết đúng yêu cầu; cấm tự ý refactor, cấm thêm abstraction sớm hoặc sửa lan sang mã lân cận.',
        'relpath': 'coding/minimal-change.md',
    },
    {
        'slug': 'backend-architect',
        'category': 'coding',
        'label': 'Kiến trúc & Dịch vụ Backend',
        'summary': 'Thiết kế/viết API, nghiệp vụ Service, giao dịch (transaction), idempotency, xử lý lỗi biên và tương thích ngược.',
        'relpath': 'coding/backend-architect.md',
    },
    {
        'slug': 'database-optimizer',
        'category': 'coding',
        'label': 'Tối ưu CSDL & Truy vấn',
        'summary': 'Tối ưu truy vấn SQL/ORM, triệt tiêu N+1, lọc trước phân trang, đúng thứ tự khóa dòng chống deadlock và index an toàn.',
        'relpath': 'coding/database-optimizer.md',
    },
    {
        'slug': 'frontend-ui',
        'category': 'coding',
        'label': 'Giao diện & Hoàn thiện UI',
        'summary': 'Xây dựng UI theo design token sẵn có, đủ trạng thái rỗng/lỗi/focus, bố cục chuẩn trên màn rộng & hẹp, chống UI rập khuôn.',
        'relpath': 'coding/frontend-ui.md',
    },
    {
        'slug': 'code-reviewer',
        'category': 'review',
        'label': 'Review mã nguồn (Code Reviewer)',
        'summary': 'Đánh giá tính đúng đắn, bảo mật, hiệu năng, khả năng bảo trì; phân loại CAO/TRUNG/THẤP kèm tệp:dòng và bằng chứng.',
        'relpath': 'review/code-reviewer.md',
    },
    {
        'slug': 'reality-checker',
        'category': 'review',
        'label': 'Nghiệm thu thực chất (Reality Checker)',
        'summary': 'Cổng chặn duyệt ảo trước tích hợp: mặc định CHƯA ĐẠT cho tới khi có đủ bằng chứng đối chiếu đặc tả ↔ mã thật ↔ kết quả kiểm.',
        'relpath': 'review/reality-checker.md',
    },
    {
        'slug': 'security-auditor',
        'category': 'review',
        'label': 'Rà soát bảo mật mã AI (Security Auditor)',
        'summary': 'Săn lỗi bảo mật đặc trưng của mã do AI sinh: lộ secret, kiểm quyền dựa dữ liệu client, thiếu lọc phạm vi dữ liệu, injection.',
        'relpath': 'review/security-auditor.md',
    },
)

# Khung mẫu chuẩn cho Agent 0 khi soạn tệp giao việc, yêu cầu sửa và bàn giao cửa sổ.
TEMPLATES = (
    {
        'slug': 'prompt-task',
        'category': 'template',
        'label': 'Mẫu giao việc mới (PROMPT-việc)',
        'summary': 'Khung chuẩn khi Agent 0 viết tệp giao việc lần đầu: mục tiêu, phạm vi, cấm chạm, tiêu chí đạt kiểm được và báo cáo.',
        'relpath': 'templates/prompt-task.md',
    },
    {
        'slug': 'prompt-fix',
        'category': 'template',
        'label': 'Mẫu yêu cầu sửa (PROMPT-fixN)',
        'summary': 'Khung chuẩn cho vòng sửa 1..N khi nghiệm thu chưa đạt: kỳ vọng vs thực tế, bằng chứng lỗi, phần bắt buộc giữ nguyên.',
        'relpath': 'templates/prompt-fix.md',
    },
    {
        'slug': 'escalation-handoff',
        'category': 'template',
        'label': 'Mẫu đổi cửa sổ / Báo chặn (Escalation)',
        'summary': 'Khung bàn giao ngữ cảnh khi thay cửa sổ agent mới sau nhiều lần sửa thất bại hoặc dừng báo chủ máy quyết định.',
        'relpath': 'templates/escalation-handoff.md',
    },
)

ROLE_MAP = {item['slug']: item for item in ROLES}
ROLE_SLUGS = tuple(ROLE_MAP)
ALL_ITEMS = ROLES + TEMPLATES


def validate_role(slug):
    """Kiểm tra tên vai trò hợp lệ. Trả None nếu rỗng/None, hoặc trả slug chuẩn; sai thì báo OrchError."""
    if slug is None or slug == '':
        return None
    if not isinstance(slug, str) or slug not in ROLE_MAP:
        raise OrchError('Vai trò không hợp lệ. Vai trò hỗ trợ: ' + ', '.join(ROLE_SLUGS))
    return slug


def get_role(slug):
    checked = validate_role(slug)
    return ROLE_MAP[checked] if checked else None


def read_item(relpath):
    target = (PACKAGE_DIR / relpath).resolve()
    if PACKAGE_DIR not in target.parents or not target.is_file():
        raise OrchError(f'Không tìm thấy tệp vai trò/mẫu: {relpath}')
    return target.read_text(encoding='utf-8').replace('\r\n', '\n').strip()


def role_prompt(slug):
    """Đoạn chỉ dẫn vai trò để ghép vào worker_prompt cho agent hàng đợi."""
    info = get_role(slug)
    if info is None:
        return ''
    body = read_item(info['relpath'])
    return (
        f"VAI TRÒ CHUYÊN MÔN ({info['label']} · `{info['slug']}` — chỉ bổ sung kỷ luật chuyên môn, "
        f"không mở rộng allow_paths và không ghi đè quy tắc của chủ máy):\n{body}"
    )


def role_choices():
    """Danh sách gọn cho dropdown tạo nhiệm vụ và cấu hình API."""
    return [
        {'slug': r['slug'], 'category': r['category'], 'label': r['label'], 'summary': r['summary']}
        for r in ROLES
    ]


def catalog_with_content(target_dir=None):
    """Danh mục đầy đủ (vai trò + mẫu + INDEX) kèm nội dung để hiển thị và xem trước trong Cài đặt."""
    base = Path(target_dir) if target_dir else PACKAGE_DIR
    items = [
        {
            'slug': 'index',
            'category': 'index',
            'label': 'Bảng điều hướng',
            'summary': 'Hướng dẫn nhanh cho Agent 0 chọn đúng vai trò và mẫu theo từng tình huống.',
            'relpath': 'INDEX.md',
            'path': str(base / 'INDEX.md'),
            'content': read_item('INDEX.md'),
        }
    ]
    for entry in ALL_ITEMS:
        items.append({
            **entry,
            'path': str(base / Path(entry['relpath'])),
            'content': read_item(entry['relpath']),
        })
    return items


def sync_to_dir(dest_dir):
    """Đồng bộ các tệp vai trò và mẫu chuẩn ra thư mục ngoài repo (ví dụ <prompts_dir>/roles).

    Chỉ ghi khi tệp chưa có hoặc nội dung đã thay đổi để không làm nhiễu dấu thời gian tệp.
    Không xoá các tệp riêng do chủ máy tự thêm vào thư mục đó.
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    relpaths = ['INDEX.md', *(item['relpath'] for item in ALL_ITEMS)]
    written = []
    for rel in relpaths:
        content = read_item(rel) + '\n'
        out = dest / Path(rel)
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            if out.is_file() and out.read_text(encoding='utf-8') == content:
                continue
        except OSError:
            pass
        out.write_text(content, encoding='utf-8')
        written.append(str(out))
    return dest, written
