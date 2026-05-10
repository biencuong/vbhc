# Deploy assets

File phục vụ deploy MCP `vbhc` lên VPS Linux.

| File | Mục đích |
|---|---|
| `install-server.sh` | Script bash idempotent: cài deps, tạo venv, ORG dir, systemd service, start+verify |
| `vbhc-mcp.service` | Template systemd service (path mặc định: `/home/mcp-soan-thao-vbhc`) |

## Cài 1 lệnh từ đầu

```bash
cd /home && \
git clone https://github.com/biencuong/vbhc.git mcp-soan-thao-vbhc && \
bash mcp-soan-thao-vbhc/deploy/install-server.sh
```

Script tự làm:
1. `apt install python3-full python3-venv apache2-utils` (skip nếu đã có)
2. Tạo venv `/home/mcp-soan-thao-vbhc/venv`
3. `pip install mcp python-docx openpyxl pyyaml`
4. Tạo ORG dir `/root/.vbhc/org` + copy template YAML (skip nếu đã có file)
5. Ghi `/etc/systemd/system/vbhc-mcp.service` (path tự detect từ vị trí script)
6. `systemctl daemon-reload && enable + start`
7. Test HTTP `127.0.0.1:8765/mcp` phải trả 405/406

Sau khi xong:
- Sửa YAML trong `/root/.vbhc/org/` cho cơ quan
- `systemctl restart vbhc-mcp`
- Setup site + reverse proxy + SSL + Basic Auth trong aaPanel — xem [INSTALL-AAPANEL.md](../INSTALL-AAPANEL.md)

## Update sau này

```bash
cd /home/mcp-soan-thao-vbhc
git pull
bash deploy/install-server.sh    # idempotent — chỉ làm phần thay đổi
```

Hoặc nhanh hơn nếu chỉ sửa code (không thay deps):
```bash
cd /home/mcp-soan-thao-vbhc && git pull && systemctl restart vbhc-mcp
```

## Custom path / port

Mặc định:
- Skill dir: thư mục chứa script (`$(dirname $0)/..`)
- ORG dir: `/root/.vbhc/org`
- Bind: `127.0.0.1:8765`

Override bằng env var trước khi chạy:

```bash
VBHC_ORG_DIR=/etc/vbhc-org \
VBHC_PORT=8800 \
VBHC_HOST=127.0.0.1 \
bash deploy/install-server.sh
```
