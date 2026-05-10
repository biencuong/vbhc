# Ví dụ end-to-end: Báo cáo góp ý dự thảo Thông tư + tổng hợp Excel khảo sát

> Loại VB phức tạp: cần ingest dữ liệu khảo sát (Excel Google Forms),
> tuân theo đề cương cứng do cấp trên ban hành, sinh báo cáo có bảng dài.

## Bối cảnh

Bộ GD&ĐT ban hành CV xin ý kiến góp ý dự thảo Thông tư Học bạ số, kèm đề cương báo cáo. Sở GD&ĐT đã thu thập 235 phản hồi từ giáo viên/CBQL qua Google Forms (file Excel). Cần soạn báo cáo gửi Bộ.

## Hội thoại

**User:**
> Có folder `D:/work/Gop-y-TT-HBS/` chứa CV của Bộ + file mẫu + Excel khảo sát. Soạn báo cáo góp ý gửi Bộ giúp tôi.

**AI** (Pha 1 — phân loại):
> `vbhc_classify("góp ý dự thảo Thông tư Bộ GD")` → match "Báo cáo góp ý dự thảo theo đề cương cứng"
>
> Đây là loại VB đặc biệt: cần đọc cả 3 file (CV cấp trên, dự thảo, đề cương) và tuân theo đề cương cứng. Tôi sẽ làm:
> 1. Sắp xếp folder
> 2. Đọc 3 file
> 3. Tổng hợp Excel khảo sát
> 4. Hỏi quan điểm của bạn
> 5. Soạn theo đề cương Bộ
>
> OK?

**User:**
> OK

**AI** (Pha 2 — tổ chức):
> `vbhc_reorganize` → tạo `0003-gop-y-du-thao-tt-hoc-ba-so/` với 3 file vào `3-tham-chieu/`.

**AI** (Pha 4 — đọc + ingest):
> Đã đọc CV 2250 + dự thảo (23 điều, 8 chương) + đề cương (Phần I bảng 4 cột + Phần II đề xuất).
>
> Đang aggregate Excel...
> `vbhc_aggregate_survey(...)` → 235 phản hồi, 13 chỉ số avg 4.25-4.36/5, 120 góp ý phù hợp/khả thi, 104 góp ý trách nhiệm, 95 góp ý bảo mật.
>
> Top 8 đề xuất nổi bật:
> 1. Đơn giản hóa quy trình ký số GV
> 2. Tài liệu hướng dẫn ngắn + video
> 3. Triển khai theo lộ trình từ lớp đầu cấp
> 4. Bảo mật: MFA, mã hóa, OTP
> 5. Quyền HS tiểu học: chỉ PH/người đỡ đầu hợp pháp
> 6. Phân định "Quản lý chuyên môn" vs "Vận hành kỹ thuật"
> 7. Liên thông VNeID
> 8. Điều 11: "yêu cầu chỉnh sửa" → "đề nghị rà soát"

**AI** (Pha 3 — phỏng vấn):
> ⚠ Hạn 8/5/2026 — đã quá 1 ngày (hôm nay 9/5). Cần soạn gấp.
>
> 2 câu hỏi quan trọng:
> 1. Cấu trúc: Báo cáo theo đề cương Bộ / Công văn ngắn / Cả hai?
> 2. Quan điểm: Cơ bản nhất trí + 5-8 ý kiến / Nhất trí toàn bộ / Tự chọn?

**User:**
> Đề cương Bộ. Cơ bản nhất trí, lấy ý 6, 8 từ Excel + thêm 4 đề xuất riêng: số hóa giữa cấp, cơ chế phối hợp ATTT, kinh phí từ Bộ TC, tận dụng CSDL ngành.

**AI** (Pha 5 — soạn):
> Generate báo cáo với 7 ý kiến trong bảng + 4 đề xuất kiến nghị.
> Output: `Bao-cao-gop-y-du-thao-TT-HBS-So-GDDT-Tuyen-Quang.docx`

**AI** (Pha 6 — validate):
> `vbhc_validate(...)` → 7/9 ✓, 2/9 ⚠ (số VB trống cho VPHC, dấu kiểm tra thủ công).
>
> Bước tiếp:
> 1. Mở file kiểm tra nội dung bảng
> 2. VPHC điền số VB
> 3. Ký + đóng dấu
> 4. Gửi gấp về Bộ qua email `hvthang@moet.edu.vn` + chuyển phát nhanh giấy về 35 Đại Cồ Việt, Bạch Mai, HN

## Insight rút ra cho skill

1. **Loại VB này KHÔNG có template chung** — mỗi đề cương khác nhau. Phải generate from scratch.
2. **Phải đọc đề cương trước khi soạn** — không được tự sáng tạo cấu trúc.
3. **Excel khảo sát thường có 80%+ phản hồi "Không có ý kiến"** — phải lọc trivial.
4. **User CHỌN ý kiến đưa vào bảng** — không tự ý paste 100+ comment.
5. **Có thể có ý kiến BỔ SUNG ngoài Excel** — user có quan điểm riêng cần đưa vào.
