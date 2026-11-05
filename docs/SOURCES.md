# Nguồn đối chiếu

Đối chiếu ngày 2026-11-05. Flag CLI được kiểm tra thêm bằng `codex exec --help`
và `claude --help` cài trên máy xây dựng. Giao diện CLI có thể thay đổi; phiên
bản không hỗ trợ flag sẽ fail, không chuyển sang bypass.

* [OpenAI Codex CLI reference](https://developers.openai.com/codex/cli/reference/)
  — exec, JSON output, sandbox và config overrides.
* [OpenAI cookbook: iterative repair loops](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex)
  — ví dụ gọi CLI qua stdin, workspace-write và kết quả có cấu trúc.
* [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference)
  — print/JSON, restricted, permission modes, tools, MCP configuration.
* [Claude Code sandboxing](https://code.claude.com/docs/en/sandboxing)
  — native Windows không sandbox shell; WSL2 có cơ chế khác.
* [MCP stdio transport 2025-03-26](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
  — một thông điệp JSON-RPC trên mỗi dòng; stdout dành riêng cho protocol.

Không chốt model, giá, quyền gói thuê bao hoặc tổng chi phí từ tài liệu. Chỉ ghi
số liệu do CLI thực tế trả. Offline fixture có số usage minh họa và được ghi rõ
là dữ liệu kiểm thử, không phải đo model thật.
