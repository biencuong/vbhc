# Ví dụ end-to-end: Soạn Phiếu biểu quyết Thành viên UBND

> Hội thoại mẫu giữa user (cán bộ hành chính) và AI có skill `soan-thao-vbhc`.

## Bối cảnh

User là Giám đốc Sở GD&ĐT, vừa nhận Công văn 1488/VP-KH&CĐS xin ý kiến biểu quyết về dự thảo Nghị quyết HĐND về mức chi KHCN. Cần điền phiếu biểu quyết gửi về VP UBND tỉnh trước hạn.

## Hội thoại

**User:**
> Tôi cần soạn phiếu biểu quyết Thành viên UBND tỉnh

**AI** (kích hoạt skill, gọi `vbhc_classify`):
> Tôi hiểu bạn cần soạn **Phiếu biểu quyết / Phiếu ghi ý kiến**. Trước khi tôi tạo hồ sơ, cho tôi biết: phiếu này biểu quyết về dự thảo gì? (1 câu là đủ)

**User:**
> Dự thảo Nghị quyết HĐND tỉnh quy định nội dung và mức chi NSNN cho KHCN, ĐMST tỉnh Tuyên Quang. Tôi có đủ tài liệu trong folder D:/work/UBND-xin-y-kien/

**AI** (gọi `vbhc_reorganize`):
> Tôi sẽ:
> - Tạo folder mới `cong-viec/0003-phieu-bieu-quyet-nq-khcn-dmst/`
> - Move 11 file từ `D:/work/UBND-xin-y-kien/` vào `3-tham-chieu/`
> - Tạo `1-yeu-cau.md` + `2-du-lieu.yaml` rỗng
>
> OK chứ?

**User:**
> OK

[AI thực thi, báo lại 11 file đã move]

**AI** (đọc lướt 2-3 file quan trọng nhất trong `3-tham-chieu/`, vào pha 3):
> Đã đọc Công văn xin ý kiến và Biểu tiếp thu. Bây giờ phỏng vấn nhanh:
>
> **Q1:** Ai sẽ ký phiếu này? (cần Họ tên + chức vụ chính xác)

**User:**
> Vũ Đình Hưng — Giám đốc Sở Giáo dục và Đào tạo tỉnh Tuyên Quang

**AI:**
> **Q2:** Quan điểm biểu quyết: **Đồng ý** hay **Không đồng ý**?

**User:**
> Đồng ý

**AI:**
> **Q3:** Có ý kiến bổ sung gì cụ thể không? (vd: "đề nghị bỏ cụm từ X tại Điều Y") — hoặc bỏ trống nếu nhất trí toàn văn.

**User:**
> Không, nhất trí dự thảo

**AI** (cập nhật `1-yeu-cau.md` + `2-du-lieu.yaml`):
> Đã ghi đầy đủ. Tóm tắt trước khi soạn:
>
> - **Loại:** Phiếu ghi ý kiến Thành viên UBND
> - **Người ký:** Vũ Đình Hưng — Giám đốc Sở GD&ĐT
> - **Đối tượng biểu quyết:** dự thảo NQ HĐND về mức chi KHCN ĐMST
> - **Quan điểm:** Đồng ý
> - **Ý kiến khác:** Nhất trí dự thảo
> - **Ngày:** 09/5/2026 (trước hạn 11/5)
>
> File mẫu sẽ dùng: `3-tham-chieu/Mau phieu bieu quyet than vien UBND tinh.docx`. OK soạn?

**User:**
> OK

**AI** (gọi `vbhc_fill_template`):
> Đã xuất: `cong-viec/0003-phieu-bieu-quyet-nq-khcn-dmst/Phieu-bieu-quyet-NQ-KHCN-DMST-Vu-Dinh-Hung.docx`
>
> Validate (`vbhc_validate`):
> ```
> ✓ Quốc hiệu + Tiêu ngữ
> ✓ Tên cơ quan ban hành
> ✓ Số/ký hiệu — Không cần (biểu mẫu nội bộ)
> ✓ Tên loại + Trích yếu: PHIẾU GHI Ý KIẾN
> ✓ Nội dung — không còn placeholder
> ✓ Người ký: GIÁM ĐỐC
> ⚠ Dấu / chữ ký số — kiểm tra thủ công
> ✓ Nơi nhận + Lưu — Không cần (biểu mẫu nội bộ)
> ✓ Phụ lục — Không có
>
> Tổng: 8/9 ✓, 1 ⚠
> ```
>
> Bước tiếp:
> 1. Mở file kiểm tra
> 2. In + ký + đóng dấu
> 3. Gửi về VP UBND tỉnh trước 11/5

## Ghi chú

- AI **không tự đặt** "Đồng ý" — phải hỏi user (theo anti-pattern trong SKILL.md).
- AI **không bịa** số phiếu — phiếu biểu quyết là biểu mẫu nội bộ, không có số.
- AI **đọc file nguồn** trước khi soạn (không chỉ dựa vào mô tả của user).
- AI **đề xuất** tên folder + cấu trúc trước khi move file (user có quyền veto).
