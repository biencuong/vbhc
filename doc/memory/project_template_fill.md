---
name: Template fill — kỹ thuật & quy ước
description: Cách fill .docx template VBHC trong project SoanThaoVB_ — convention folder + workaround kỹ thuật khi MCP word search_and_replace không hoạt động
type: project
originSessionId: d2678777-08f3-4e95-9a55-7c3501505901
---
## Convention folder công việc (đã có trong codebase)
- `cong-viec/_mau-ho-so/HD-AI-tu-sap-xep.md` — quy trình AI tự sắp xếp folder bừa thành chuẩn `<NNNN>-<mô-tả>` + 1-yeu-cau.md + 2-du-lieu.yaml + 3-tham-chieu/. **Đọc file này trước khi reorganize folder.**
- Trigger: user nói "sắp xếp folder X" / "tự đặt tên + tạo metadata" / "đọc file rồi tự làm".

**Why:** Đã thiết lập workflow một lần (session 09/5/2026, hồ sơ Phiếu biểu quyết NQ KH&CN cho GĐ Sở GD&ĐT) — không cần thiết kế lại convention mỗi lần.

**How to apply:** Khi user quăng folder bừa, đọc HD-AI-tu-sap-xep.md trước, theo 7 bước trong đó. KHÔNG tự ý đặt tên kiểu `XinYKenTVUBNDT` (không dấu liền nhau) — phải dùng `<NNNN>-<mô-tả-có-gạch-ngang>`.

## Workaround: search_and_replace fail trên text trong table cell
`mcp__word__search_and_replace` thường fail (trả "no occurrences found") khi text nằm trong **cell của table** sau khi file được Word convert từ .doc → .docx — vì text bị split thành nhiều runs.

**Why:** python-docx (backend của MCP word) tìm theo run text, không gộp; convert .doc tạo ra runs phân mảnh ngẫu nhiên.

**How to apply:** Khi search_and_replace fail trên file convert từ .doc:
1. Verify text tồn tại bằng `mcp__word__find_text_in_document` (tool này gộp runs trước khi search).
2. Nếu found mà replace fail → fallback sang script python-docx (đã có v1.1.2). Pattern: lấy `paragraph.runs[0]`, set text mới, clear `runs[1:]`. Code mẫu trong file `_edit.py` đã xóa nhưng có thể tái tạo nhanh.
3. Cell có thể có nhiều paragraphs — gộp về paragraph[0], xóa các paragraph sau bằng `p._element.getparent().remove(p._element)`.

## Encoding khi chạy script Python với tiếng Việt
Mặc định stdout Windows = cp1252 → crash với ký tự Việt. Luôn thêm đầu script:
```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
```
