# Workflow 6 pha — chi tiết thực thi

> Đây là playbook AI chạy mỗi khi skill `soan-thao-vbhc` được kích hoạt.

## Pha 1 — Phân loại loại văn bản

**Input:** mô tả của user (1-3 câu) hoặc danh sách file nguồn.

**Logic:**
1. Đọc `resources/danh-muc-loai-vb.md` để biết các loại phổ biến.
2. Match keyword:
   - "xin ý kiến", "lấy ý kiến", "tham gia ý kiến" → **Công văn xin ý kiến**
   - "biểu quyết", "phiếu", "đồng ý/không đồng ý" → **Phiếu biểu quyết / Phiếu ghi ý kiến**
   - "trình", "đề nghị phê duyệt", "kính trình" → **Tờ trình**
   - "quyết định", "ban hành", "thành lập", "bổ nhiệm" → **Quyết định**
   - "báo cáo", "tổng kết", "kết quả thực hiện" → **Báo cáo**
   - "thông báo", "kết luận của ..." → **Thông báo / Kết luận**
   - "kế hoạch thực hiện ..." → **Kế hoạch**
   - "hướng dẫn ..." → **Hướng dẫn**
3. Nếu match 1 loại rõ → confirm 1 dòng: *"Tôi hiểu bạn cần soạn 1 [Loại]. Đúng chứ?"* — đợi user gật đầu rồi tiếp.
4. Nếu match 2-3 loại → AskUserQuestion với các option đó.
5. Nếu KHÔNG match nào → hỏi user mục đích cụ thể: *"Văn bản này dùng để làm gì? (xin ý kiến / trình lên / quyết định ban hành / báo cáo kết quả / thông báo cho ai)"*

**Output:** `loai_vb` (string) — lưu tạm trong context, sẽ ghi vào `2-du-lieu.yaml` ở pha 2.

---

## Pha 2 — Tổ chức hồ sơ công việc

**Input:** `loai_vb` từ pha 1, hoặc folder bừa user đã đưa.

### Trường hợp A — User nói miệng, chưa có folder

1. Xác định parent dir:
   - Nếu cwd có folder `cong-viec/` → dùng làm parent.
   - Nếu không → tạo `cong-viec/` ngay tại cwd.
2. Đếm folder bắt đầu bằng số trong `cong-viec/` để lấy `<NNNN>` tiếp theo.
3. Sinh tên folder: `<NNNN>-<mô-tả-không-dấu-từ-loai-vb-và-chủ-đề>`.
   - Ví dụ: `0003-cong-van-xin-y-kien-so-tai-chinh`, `0004-quyet-dinh-thanh-lap-to-cong-tac`.
   - Tối đa 6 từ trong phần mô tả.
4. Tạo cấu trúc qua tool MCP `vbhc_create_workfolder` HOẶC bash `mkdir -p`.

### Trường hợp B — User đưa folder bừa có sẵn file nguồn

1. `ls` folder để liệt kê file.
2. Đọc lướt 1-3 file quan trọng nhất (PDF/.docx) để hiểu việc.
3. Đề xuất tên folder mới với user trước khi đổi (1 dòng): *"Tôi sẽ đổi tên thành `<NNNN>-<đề-xuất>` và move 11 file vào `3-tham-chieu/`. OK chứ?"*
4. Sau khi user OK → dùng `scripts/reorganize_folder.py` hoặc MCP `vbhc_reorganize`.

### Cấu trúc kết quả (cố định)

```
<NNNN>-<mô-tả>/
├── 1-yeu-cau.md          # mô tả + quan điểm
├── 2-du-lieu.yaml        # dữ liệu cụ thể
├── 3-tham-chieu/         # file nguồn
└── (sau pha 5: file .docx kết quả)
```

---

## Pha 3 — Phỏng vấn user (lấy mô tả + quan điểm + dữ liệu)

**Mục tiêu:** điền đủ `1-yeu-cau.md` + `2-du-lieu.yaml` để có thể fill template.

### 4 nhóm câu hỏi BẮT BUỘC

Hỏi tuần tự, mỗi lượt 1 nhóm. Có thể skip nhóm nào nếu đã rõ từ file nguồn.

#### Nhóm 1 — Mục đích & Quan điểm
- *"Mục đích cụ thể của văn bản này là gì? (1 câu)"*
- *"Bạn muốn văn bản thể hiện quan điểm thế nào?"* — đặc biệt quan trọng với:
  - Phiếu biểu quyết: Đồng ý / Không đồng ý / Có điều kiện
  - Tờ trình: đề nghị phê duyệt / phê duyệt có điều kiện / xin ý kiến
  - Báo cáo: hoàn thành / chưa hoàn thành / vướng mắc cần xin chỉ đạo
  - Công văn: thông báo / yêu cầu / xin ý kiến / phối hợp

#### Nhóm 2 — Người ký
- *"Ai sẽ ký văn bản này? (Họ tên đầy đủ + chức vụ)"*
- Nếu là project có `tri-thuc/05-thong-tin-co-quan.yaml` → liệt kê các người ký
  có sẵn để user chọn (AskUserQuestion).
- Cảnh báo: nếu user nói "GĐ Sở" mà có 2 GĐ trong cơ quan → hỏi tên cụ thể.

#### Nhóm 3 — Nơi gửi / Đối tượng
- *"Văn bản gửi cho ai? (cá nhân / cơ quan)"*
- Hỏi cả `Nơi nhận` (phần dưới VB, nhỏ): có gửi báo cáo lên cấp trên không?
  có lưu VT, đơn vị soạn không?

#### Nhóm 4 — Nội dung chính + Căn cứ
- *"Nội dung chính bạn muốn truyền đạt? (gạch đầu dòng cũng được, tôi viết lại cho chuẩn)"*
- *"Có căn cứ pháp lý nào cần viện dẫn không? (Nghị định, Thông tư, Quyết định nội bộ...)"*
- → Nếu user nói có VB căn cứ → chuyển sang Pha 4 yêu cầu file.

### Quy tắc hỏi

- **Mỗi lượt 1 câu** — không hỏi dồn 5 câu/1 message.
- Ưu tiên `AskUserQuestion` với option khi câu hỏi có set lựa chọn rõ.
- Câu hỏi mở → đặt trong text message bình thường.
- Sau mỗi câu trả lời → cập nhật ngay `1-yeu-cau.md` / `2-du-lieu.yaml`.
- Tóm tắt 1 dòng sau khi user trả lời: *"Đã ghi: [tóm tắt]. Tiếp theo: [câu hỏi sau]"*

---

## Pha 4 — Yêu cầu file nguồn / làm rõ

**Khi nào kích hoạt:** mỗi lần user nhắc tới 1 trong các thứ sau MÀ chưa thấy
file tương ứng trong `3-tham-chieu/`:

| User nói... | AI cần... |
|---|---|
| "Theo Nghị định 30/2020" | File NĐ 30 PDF, hoặc xác nhận user OK với việc viện dẫn theo trí nhớ |
| "Tờ trình số X" | File tờ trình PDF/.docx |
| "Quyết định Y trước đây" | File QĐ gốc |
| "Theo chỉ đạo của ..." | Văn bản chỉ đạo gốc |
| "Báo cáo của Sở X" | Báo cáo gốc |
| "Biểu tiếp thu ý kiến" | File biểu mẫu |

**Câu hỏi mẫu:**
> *"Bạn nhắc tới [Tờ trình số 111/TTr-SKHCN]. Tôi chưa thấy file này trong
> `3-tham-chieu/`. Bạn có sẵn để gửi tôi không? Nếu không, tôi sẽ viện dẫn
> theo mô tả của bạn và đánh dấu chỗ đó để bạn rà lại."*

**Xử lý mâu thuẫn:** nếu 2 file nguồn nói khác nhau (vd: tên cơ quan trong
TiepThuYKien.pdf khác với trong CV xin ý kiến) → liệt kê 2 phiên bản, hỏi user
chọn.

---

## Pha 5 — Generate / fill .docx

**Quyết định dùng phương pháp nào:**

### Phương pháp A — `vbhc_doc_builder` (KHUYẾN NGHỊ cho VB tạo mới)

Dùng khi tạo VB từ đầu — header chuẩn ND 30 với gạch chân ngắn, font 12-14pt đúng quy định, no border table, padding = 0, column widths sticky.

```python
import sys
sys.path.insert(0, r"D:\SKILL_AI\skills\soan-thao-vbhc\scripts")
from vbhc_doc_builder import (
    Document, setup_page,
    add_header_section, add_so_vb_and_date_section,
    add_title_block, add_kinh_gui,
    add_body_paragraph, add_section_heading,
    add_gop_y_table, add_bieu_quyet_table,
    add_signature_noi_nhan, add_centered_title_with_underline,
)

doc = Document()
setup_page(doc)
add_header_section(doc, co_quan_chu_quan="UBND TỈNH X", co_quan_ban_hanh="SỞ Y")
add_so_vb_and_date_section(doc, ky_hieu="BC-SY", dia_danh="X", ngay=10, thang=5, nam=2026)
add_title_block(doc, ten_loai="BÁO CÁO", trich_yeu="...")
add_kinh_gui(doc, "Bộ Z (Vụ ABC).")
add_body_paragraph(doc, "Nội dung mở đầu...")
add_signature_noi_nhan(doc, noi_nhan_items=[...], chuc_vu="GIÁM ĐỐC", nguoi_ky="...")
doc.save(out_path)
```

**Đặc điểm header chuẩn (đã verify qua PDF render):**
- Cell trái 7cm + cell phải 9cm (tổng 16cm = vùng nội dung A4 NĐ 30)
- Cell padding = 0 (full width)
- Quốc hiệu **12pt** (NĐ 30: 12-13pt, chọn 12 để fit 1 dòng 9cm)
- Tiêu ngữ **14pt** (NĐ 30: 13-14pt, chọn 14 cho cân đối)
- Tên cơ quan **13pt** (regular cho chủ quản, bold cho ban hành)
- Gạch chân ngắn ở giữa dưới: tên CQ ban hành (indent 1.2cm) + tiêu ngữ (indent 2.5cm)
- Line spacing 1.15 trong header, 1.5 trong body

### Phương pháp B — Fill template có sẵn

Dùng khi user đã đưa template `.docx` chuẩn và chỉ cần điền chỗ trống.

- **TEXT trong paragraph thường:** `mcp__word__search_and_replace` OK.
- **TEXT trong cell của table:** `mcp__word__search_and_replace` THƯỜNG FAIL
  (text bị split runs sau convert .doc). → Fallback python-docx:
  ```python
  from docx import Document
  doc = Document(path)
  cell = doc.tables[T_IDX].rows[R].cells[C]
  p = cell.paragraphs[0]
  p.runs[0].text = NEW_TEXT
  for r in p.runs[1:]: r.text = ""
  for p_extra in cell.paragraphs[1:]:
      p_extra._element.getparent().remove(p_extra._element)
  doc.save(path)
  ```
- **Đặt X vào ô checkbox:** set text "X" vào ô tương ứng.

### Encoding script Python với tiếng Việt

Luôn thêm đầu file:
```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
```

### Verify layout sau khi gen

**LUÔN render PDF để verify** (Word lookup khác PDF lookup):
```python
mcp__word__convert_to_pdf(filename=path, output_filename=path.replace('.docx', '.pdf'))
```
Đọc PDF kiểm tra: header có wrap không, gạch chân có không, bảng đẹp chứ.

**Bước 3 — Đặt tên file kết quả:**
- Format: `<Loai-VB>-<chu-de>-<nguoi-ky>.docx`
- Ví dụ: `Phieu-bieu-quyet-NQ-KHCN-Vu-Dinh-Hung.docx`, `Cong-van-xin-y-kien-NQ-KHCN.docx`
- Đặt ở root folder công việc (cùng cấp với `1-yeu-cau.md`).

---

## Pha 6 — Validate + bàn giao

**Bước 1 — Chạy validate:**
- MCP: `vbhc_validate(<file.docx>)`
- Hoặc bash: `python scripts/validate_thethuc.py <file.docx>`

Trả về checklist 9 thành phần thể thức (xem `the-thuc-vbhc-checklist.md`):
- ✅ / ❌ cho từng mục
- Cảnh báo: chỗ "???" hoặc "<placeholder>" còn sót
- Cảnh báo: số VB / ngày ký để trống

**Bước 2 — Báo cáo user:**

Format chuẩn:
```
✓ Đã xuất: <đường-dẫn-file>.docx
✓ Thể thức: <X>/9 thành phần đạt
⚠ Cần kiểm tra thủ công:
  - [ ] Số văn bản (đang trống — VPHC điền sau khi vào sổ)
  - [ ] Ngày ký thật (file đang ghi ngày <X>, có thể cần cập nhật)
  - [ ] Chữ ký + đóng dấu

Bước tiếp:
1. Mở file để xem.
2. Sửa thủ công nếu cần (hoặc bảo tôi sửa).
3. In + ký + đóng dấu.
4. Vào sổ + cấp số.
```

**Bước 3 — Cleanup:**
- Xóa các file tạm `_inspect.py`, `_edit.py` nếu có.
- KHÔNG xóa file nguồn trong `3-tham-chieu/`.
- KHÔNG xóa `1-yeu-cau.md` / `2-du-lieu.yaml` — giữ làm log.

---

## Tổng quát: nguyên tắc giao tiếp

1. **Mỗi lần lên tiếng 1 câu chính + 1 câu hỏi.** Không lecture.
2. **Khi cần làm việc → cứ làm.** Không hỏi xin phép cho mỗi tool call nhỏ.
3. **Khi cần quyết định không reverse được → HỎI.** (Xóa file, sửa file user mở,
   gửi mail...).
4. **Khi không chắc → THÚ NHẬN, đừng đoán.** "Tôi không biết NĐ này có khoản
   nào — bạn có file gốc không?" tốt hơn bịa.
5. **Tracked changes ON khi sửa file Word đang có nội dung.** Để user dễ undo.
