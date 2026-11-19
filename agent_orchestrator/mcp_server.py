"""Remote MCP Server module — Streamable HTTP transport, MCP spec 2025-03-26.

Exposes 4 WorkspaceExecutor tools over Bearer-authenticated HTTP endpoints
that web.py routes from /api/mcp/*.
"""
from __future__ import annotations

import json

PROTOCOL_VERSION = "2025-03-26"

TOOLS: list[dict] = [
    {
        "name": "list_files",
        "description": "Liệt kê các tệp trong thư mục làm việc (hoặc thư mục con).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subdir": {
                    "type": "string",
                    "description": "Thư mục con tương đối (tuỳ chọn). Mặc định là thư mục gốc."
                }
            },
            "additionalProperties": False
        }
    },
    {
        "name": "read_file",
        "description": "Đọc nội dung một tệp trong thư mục làm việc.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Đường dẫn tương đối đến tệp cần đọc."
                },
                "start_line": {
                    "type": "integer",
                    "description": "Dòng bắt đầu (tính từ 1, tuỳ chọn)."
                },
                "end_line": {
                    "type": "integer",
                    "description": "Dòng kết thúc (tuỳ chọn)."
                }
            },
            "required": ["path"],
            "additionalProperties": False
        }
    },
    {
        "name": "write_file",
        "description": "Ghi nội dung vào một tệp (tạo mới hoặc ghi đè).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Đường dẫn tương đối đến tệp cần ghi."
                },
                "content": {
                    "type": "string",
                    "description": "Nội dung cần ghi vào tệp."
                }
            },
            "required": ["path", "content"],
            "additionalProperties": False
        }
    },
    {
        "name": "replace_in_file",
        "description": "Thay thế một đoạn văn bản duy nhất trong tệp bằng đoạn văn bản mới.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Đường dẫn tương đối đến tệp."
                },
                "search": {
                    "type": "string",
                    "description": "Đoạn văn bản cần tìm (phải xuất hiện đúng 1 lần)."
                },
                "replace": {
                    "type": "string",
                    "description": "Đoạn văn bản thay thế."
                }
            },
            "required": ["path", "search", "replace"],
            "additionalProperties": False
        }
    }
]

# Map MCP tool name -> WorkspaceExecutor action name
_TOOL_ACTION: dict[str, str] = {
    "list_files": "list_files",
    "read_file": "read_file",
    "write_file": "write_file",
    "replace_in_file": "replace_in_file",
}


def handle_mcp(path_parts: list[str], body: dict, executor) -> tuple[int, dict]:
    """Route an MCP request and return (http_status, response_dict).

    path_parts: segments after /api/mcp/, e.g. ["tools", "list"] or ["tools", "call"].
    body: parsed JSON body (may be empty dict for list).
    executor: a WorkspaceExecutor instance; its .execute(call_dict) method is used.

    Per MCP spec errors are returned as HTTP 200 with isError: True.
    """
    route = "/".join(path_parts)

    # --- tools/list ---
    if route == "tools/list":
        return 200, {"tools": TOOLS}

    # --- tools/call ---
    if route == "tools/call":
        tool_name = body.get("name")
        if not isinstance(tool_name, str) or not tool_name:
            return 200, _error("Thiếu hoặc sai kiểu trường 'name'.")
        action = _TOOL_ACTION.get(tool_name)
        if action is None:
            return 200, _error(f"Tool không tồn tại: '{tool_name}'. Các tool hợp lệ: {', '.join(_TOOL_ACTION)}.")
        arguments = body.get("arguments", {})
        if not isinstance(arguments, dict):
            return 200, _error("Trường 'arguments' phải là object.")
        # Build the call dict that WorkspaceExecutor.execute() expects
        call: dict = {"action": action, **arguments}
        try:
            result = executor.execute(call)
        except Exception as exc:  # noqa: BLE001
            return 200, _error(f"Lỗi khi thực thi tool: {exc}")
        is_error = not bool(result.get("ok", True))
        text = result.get("error") if is_error else _format_result(result)
        return 200, {"content": [{"type": "text", "text": str(text)}], "isError": is_error}

    # --- unknown route ---
    return 200, _error(f"Endpoint MCP không hỗ trợ: '{route}'. Dùng tools/list hoặc tools/call.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error(message: str) -> dict:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def _format_result(result: dict) -> str:
    """Convert a WorkspaceExecutor result dict to a readable string for MCP callers."""
    # For list_files: show file list
    if "files" in result:
        files = result["files"]
        lines = [f"Tổng: {len(files)} tệp" + (" (đã cắt bớt)" if result.get("truncated") else "")]
        lines.extend(files)
        return "\n".join(lines)
    # For read_file: show content
    if "content" in result and result.get("action") == "read_file":
        return result["content"]
    # Fallback: serialize as JSON
    try:
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception:  # noqa: BLE001
        return str(result)
