# Remote MCP Server

Agent Orchestrator tích hợp sẵn một **MCP server** chạy trên HTTP, cho phép Claude Desktop, Gemini hoặc bất kỳ MCP client nào đọc/ghi file trong repo thông qua internet (qua Cloudflare Tunnel).

---

## Kiến trúc

```
MCP Client (Claude Desktop / Gemini web)
        │  HTTPS  Authorization: Bearer <token>
        ▼
┌─────────────────────────────┐
│  Cloudflare Quick Tunnel    │  (tools/cloudflared.exe)
│  https://xxxx.trycloudflare.com
└────────────┬────────────────┘
             │ HTTP  localhost
             ▼
┌─────────────────────────────┐
│  Agent Orchestrator         │  web.py  :8765
│  /api/mcp/tools/list        │
│  /api/mcp/tools/call        │
└────────────┬────────────────┘
             │
             ▼
   agent_orchestrator/mcp_server.py
   (list_files, read_file, write_file, replace_in_file)
```

---

## Lần đầu cài đặt

### 1. Tải cloudflared

```powershell
powershell -ExecutionPolicy Bypass -File tools\download-cloudflared.ps1
```

Script sẽ tải `cloudflared-windows-amd64.exe` từ GitHub về `tools\cloudflared.exe`.

> **Lưu ý:** `tools\cloudflared.exe` đã được thêm vào `.gitignore` — không commit binary này lên git.

### 2. Thêm `mcp_server` vào `studio.json`

Mở `studio.json` (file config của Agent Orchestrator) và thêm block sau vào object gốc:

```json
"mcp_server": {
  "enabled": true,
  "token": "DAT-TOKEN-RIENG-DAI-TOI-THIEU-16-KY-TU",
  "allow_paths": null
}
```

| Field | Mô tả |
|---|---|
| `enabled` | `true` để bật server, `false` để tắt |
| `token` | Token Bearer để xác thực. Tối thiểu 16 ký tự. **Đặt token riêng, không dùng token mẫu.** |
| `allow_paths` | Danh sách thư mục MCP client được phép đọc/ghi. `null` = chỉ trong repo. |

**Sinh token nhanh (PowerShell):**
```powershell
-join ((65..90)+(97..122)+(48..57) | Get-Random -Count 40 | % {[char]$_})
```

### 3. Khởi động Agent Orchestrator

Khởi động (hoặc restart) Agent Orchestrator để load config mới.

### 4. Khởi động tunnel

Double-click `tools\Start-MCP-Tunnel.cmd`.

Màn hình console sẽ hiện URL dạng:
```
Your quick Tunnel has been created! Visit it at: https://xxxx.trycloudflare.com
```

Copy URL đó để cấu hình MCP client.

> **URL thay đổi mỗi lần** bạn chạy lại tunnel. Với URL cố định cần đăng ký tài khoản Cloudflare và tạo Named Tunnel.

---

## Cấu hình MCP Client

### Claude Desktop

Thêm vào `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "url": "https://xxxx.trycloudflare.com/api/mcp/",
      "headers": {
        "Authorization": "Bearer DAT-TOKEN-RIENG-CUA-BAN"
      }
    }
  }
}
```

### Gemini / HTTP thủ công

```
POST https://xxxx.trycloudflare.com/api/mcp/tools/list
Authorization: Bearer DAT-TOKEN-RIENG-CUA-BAN
```

---

## Danh sách Tools

| Tool | Mô tả |
|---|---|
| `list_files` | Liệt kê file trong repo (tham số: `path` tương đối, mặc định `.`) |
| `read_file` | Đọc nội dung file (tham số: `path`, tùy chọn `start_line`, `end_line`) |
| `write_file` | Ghi/tạo file (tham số: `path`, `content`) |
| `replace_in_file` | Thay thế đoạn text trong file (tham số: `path`, `old_text`, `new_text`) |

---

## Ranh giới an toàn

- Tất cả đường dẫn đều **relative** với `repo` trong config — không thể truy cập ngoài repo.
- Các file được bảo vệ (ví dụ `CLAUDE.md`, `studio.json`) sẽ bị chặn khi ghi.
- `allow_paths` cho phép giới hạn thêm: chỉ các thư mục trong danh sách mới được thao tác.

---

## Test nhanh (PowerShell)

```powershell
# 1. Kiểm tra local (không cần tunnel)
$h = @{ Authorization = "Bearer TOKEN-CUA-BAN" }
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/mcp/tools/list" -Method POST -Headers $h | ConvertTo-Json -Depth 5

# 2. Đọc file
$h = @{ Authorization = "Bearer TOKEN-CUA-BAN" }
$b = '{"name":"read_file","arguments":{"path":"README.md","start_line":1,"end_line":10}}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/mcp/tools/call" -Method POST -Headers $h -Body $b -ContentType "application/json" | ConvertTo-Json

# 3. Sai token → phải trả 401
$h = @{ Authorization = "Bearer wrong-token" }
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/mcp/tools/list" -Method POST -Headers $h
```

---

## Troubleshooting

| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| `401 Unauthorized` | Token sai hoặc thiếu header | Kiểm tra `Authorization: Bearer <token>` |
| `403 Forbidden` | File bị bảo vệ hoặc ngoài `allow_paths` | Dùng file khác hoặc mở rộng `allow_paths` |
| `cloudflared.exe` không tìm thấy | Chưa tải | Chạy `tools\download-cloudflared.ps1` |
| URL tunnel không kết nối được | Tunnel chưa chạy | Double-click `tools\Start-MCP-Tunnel.cmd` |
| Config không nhận | Agent Orchestrator chưa restart | Restart Agent Orchestrator sau khi sửa `studio.json` |

---

## File liên quan

| File | Mô tả |
|---|---|
| `agent_orchestrator/mcp_server.py` | Logic 4 tools MCP |
| `agent_orchestrator/web.py` | HTTP route `/api/mcp/*`, xác thực token |
| `agent_orchestrator/config.py` | Validate config `mcp_server` |
| `tools/Start-MCP-Tunnel.cmd` | Script khởi động Cloudflare tunnel |
| `tools/download-cloudflared.ps1` | Script tải cloudflared binary |
| `examples/config.windows.json` | Ví dụ config đầy đủ |
