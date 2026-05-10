# Dữ liệu văn bản — fill các trường có dữ liệu, để trống / "???" cho trường chưa có

loai_van_ban: ""           # Vd: "Công văn xin ý kiến" / "Phiếu biểu quyết"

# --- Khối thông tin cơ quan (góc trái) ---
co_quan_chu_quan: ""       # Vd: UBND TỈNH TUYÊN QUANG
co_quan_ban_hanh: ""       # Vd: SỞ GIÁO DỤC VÀ ĐÀO TẠO

# --- Số / ký hiệu ---
so_van_ban: ""             # Vd: "1488/VP-KH&CĐS" — để "" nếu chưa vào sổ

# --- Trích yếu (V/v đối với CV, hoặc tên VB đối với loại khác) ---
trich_yeu: ""              # Vd: "tham gia ý kiến đối với dự thảo Nghị quyết..."

# --- Người ký ---
nguoi_ky:
  ho_ten: ""               # Vd: "Vũ Đình Hưng"
  chuc_vu: ""               # Vd: "GIÁM ĐỐC SỞ GIÁO DỤC VÀ ĐÀO TẠO"
  quyen_han: ""            # "" / "KT." / "TL." / "TUQ."
  chuc_vu_thay: ""          # Nếu KT./TL., chức vụ người được ký thay (vd: "CHÁNH VĂN PHÒNG")

# --- Địa danh + ngày tháng ---
dia_danh: ""               # Vd: "Tuyên Quang"
ngay: 0
thang: 0
nam: 0

# --- Người nhận chính ---
kinh_gui: ""               # Vd: "Các đồng chí Thành viên Ủy ban nhân dân tỉnh"

# --- Nơi nhận (sao gửi) ---
noi_nhan:
  - "Như trên"
  - "Lưu: VT, [Đơn vị soạn]"

# --- Nội dung chính ---
noi_dung_chinh: |
  <Bullet point hoặc đoạn văn ngắn — AI sẽ viết lại theo chuẩn ND30>

# --- Căn cứ pháp lý / VB nguồn ---
can_cu:
  - ""                     # Vd: "Nghị định số 30/2020/NĐ-CP ngày 05/3/2020..."

# --- Phần đặc thù theo loại VB ---

# Phiếu biểu quyết
bieu_quyet:
  dong_y: null             # true / false / null (chưa quyết)
  ly_do_khong_thong_qua: ""
  y_kien_khac: ""

# Tờ trình
to_trinh:
  trinh_len: ""            # "UBND tỉnh" / "Sở X" / "Bộ Y"
  noi_dung_trinh: ""
  de_xuat_phuong_an: 1     # số phương án (1 / nhiều)

# Quyết định
quyet_dinh:
  loai: ""                 # "ca-biet" / "qppl"
  doi_tuong: ""            # cá nhân / đơn vị / phạm vi
  hieu_luc_tu_ngay: ""     # "ngay-ky" / "DD/MM/YYYY"
  bai_bo_vb_cu: []         # ["QĐ số X ngày Y", ...]

# Báo cáo
bao_cao:
  ky: ""                   # "thang" / "quy" / "6-thang" / "nam" / "dot-xuat"
  ky_so: 0                 # vd: 1 (quý 1)

# --- Hạn / thời gian (nếu có) ---
han_phan_hoi: ""           # "DD/MM/YYYY" hoặc "" nếu không có
