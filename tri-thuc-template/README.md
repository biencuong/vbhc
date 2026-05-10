# Template ORG tier — config chung của cơ quan

Folder này chứa các file YAML mẫu để 1 cơ quan (Sở, Bộ, UBND...) cấu hình:
- Thông tin cơ quan (tên, người ký, phòng)
- Phân công nhiệm vụ (để gợi ý nơi nhận VB chính xác)
- Căn cứ pháp lý mẫu (danh sách Luật/NĐ/TT thường viện dẫn — verify hiệu lực)

## Cài đặt

1. Tạo ORG dir trên máy của bạn (hoặc trên server share):
   ```powershell
   # Mặc định:
   New-Item -ItemType Directory -Path "$HOME\.vbhc\org" -Force
   # Hoặc thư mục riêng (nếu dùng cho team):
   New-Item -ItemType Directory -Path "D:\SoGDDT_TQ_VBHC_Org" -Force
   ```

2. Copy các file template vào ORG dir:
   ```powershell
   Copy-Item "D:\SKILL_AI\skills\soan-thao-vbhc\tri-thuc-template\*.yaml" `
             -Destination "$HOME\.vbhc\org\"
   ```

3. (Tùy chọn) Set env var nếu ORG dir không phải mặc định `~/.vbhc/org/`:
   ```powershell
   [Environment]::SetEnvironmentVariable("VBHC_ORG_DIR", "D:\SoGDDT_TQ_VBHC_Org", "User")
   ```

4. Sửa nội dung từng file theo cơ quan của bạn.

## 3 tier storage

| Tier  | Vị trí | Mục đích | Sửa đổi |
|---|---|---|---|
| **SKILL** | `D:\SKILL_AI\skills\soan-thao-vbhc\` | Code + danh-muc-loai-vb chuẩn | Read-only (chỉ owner skill update) |
| **ORG**   | `$VBHC_ORG_DIR` (default `~/.vbhc/org/`) | Cấu hình chung cơ quan | Cơ quan tự sửa, share cho nội bộ |
| **USER**  | `cong-viec/<NNNN>-...` (tham số trong tool call) | File công việc cụ thể + tham chiếu | Mỗi user/máy riêng |

## File trong template

- `05-thong-tin-co-quan.yaml` — bản mẫu (cụ thể cho Sở GDĐT Tuyên Quang nằm ở
  `D:\SKILL_AI\SoanThaoVB_\tri-thuc\05-thong-tin-co-quan.yaml`).
- `phan-cong-nhiem-vu.yaml` — danh sách phòng/đơn vị + chức năng nhiệm vụ.
- `can-cu-phap-ly-mau.yaml` — danh sách Luật/NĐ/TT thường viện dẫn, kèm trạng
  thái hiệu lực để AI biết VB nào còn dùng được.
