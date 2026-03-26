import streamlit as st
from pymongo import MongoClient
import tempfile
from upload_image import upload_image_to_cloudinary
from datetime import datetime
import pandas as pd
import random, string
import os
import numpy as np
import matplotlib.pyplot as plt
import requests
from auth import require_login
from openai import OpenAI

require_login()

# ------------------ MongoDB ------------------
def get_db():
    url = os.getenv("MONGO_URL")
    client = MongoClient(url)
    db = client["handbook"]
    return db

db = get_db()
collection = db["errors"]

# ------------------ Streamlit config ------------------
st.set_page_config(page_title="Process Engineering Handbook", layout="wide")
st.title("Process Engineering Handbook")
mode=st.sidebar.radio("Select a feature:",["➕ Thêm lỗi mới", "🔍 Tra cứu lỗi", "📘 Quy Trình Phân tích", 
                                        "⚛ ERP System & WI","☯ Team Center & FAI","Production Schedule","Link Tham Khảo","Trang tính","Chat Bot"])


# ==========================================================
# 🧩 TAB 1: THÊM LỖI MỚI
# ==========================================================
if mode == "➕ Thêm lỗi mới":
    st.subheader("Thêm lỗi sản phẩm mới")

    def generate_error_code(model, timestamp):
        """Sinh mã lỗi tự động dựa trên model + ngày tháng + ký tự ngẫu nhiên"""
        try:
            model_part = model[3:6] if len(model) >= 6 else model
            date_obj = datetime.strptime(timestamp, "%Y-%m-%d")
            month_letter = chr(64 + date_obj.month)
            day = str(date_obj.day).zfill(2)
            random_part = ''.join(random.choices(string.ascii_uppercase, k=3))
            return f"{model_part}{month_letter}{day}{random_part}"
        except Exception as e:
            print("Lỗi tạo mã:", e)
            return "ERR000"

    model = st.text_input("Model Name", placeholder="VD: 030333011")
    timestamp = st.text_input("Timestamp (YYYY-MM-DD)", placeholder="VD: 2025-10-12")

    if model and timestamp:
        try:
            datetime.strptime(timestamp, "%Y-%m-%d")
            auto_error_code = generate_error_code(model, timestamp)
            st.text_input("Defect Mode (auto)", value=auto_error_code, disabled=True)
        except ValueError:
            st.error("⚠️ Định dạng ngày không hợp lệ! Vui lòng nhập dạng YYYY-MM-DD.")
            auto_error_code = ""
    else:
        auto_error_code = ""

    description = st.text_area("Description")
    root_cause = st.text_area("Root Cause")
    solution = st.text_area("Short-Term Action")
    improvement = st.text_area("Long-Term Action")

    image_files = st.file_uploader("Chọn hình ảnh lỗi", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    pdf_file = st.file_uploader("📎 Upload file báo cáo (PDF)", type=["pdf"])

    if st.button("💾 Lưu vào database"):
        if not all([model, auto_error_code, description]):
            st.error("⚠️ Cần nhập ít nhất model, timestamp và mô tả lỗi!")
        else:
            image_urls = []
            if image_files:
                for image_file in image_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                        tmp.write(image_file.getbuffer())
                        tmp_path = tmp.name
                    image_url = upload_image_to_cloudinary(tmp_path)
                    if image_url:
                        image_urls.append(image_url)
                if image_urls:
                    st.success(f"📸 Đã upload {len(image_urls)} ảnh thành công!")
                else:
                    st.warning("⚠️ Không có ảnh nào được upload thành công.")
            else:
                image_urls = []

            pdf_url = ""
            if pdf_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf_file.getbuffer())
                    tmp_path = tmp.name
                pdf_url = upload_image_to_cloudinary(tmp_path)
                if pdf_url:
                    st.success("📄 Upload file PDF thành công!")
                else:
                    st.warning("⚠️ Upload PDF thất bại.")

            new_error = {
                "model": model,
                "error_code": auto_error_code,
                "description": description,
                "root_cause": root_cause,
                "solution": solution,
                "improvement": improvement,
                "timestamp": timestamp,
                "images": image_urls,  # đổi thành list
                "pdf_report": pdf_url
            }

            collection.insert_one(new_error)
            st.success(f"✅ Đã thêm lỗi {auto_error_code} cho model {model}")

# ==========================================================
# 🔍 TAB 2: TRA CỨU LỖI
# ==========================================================
elif mode == "🔍 Tra cứu lỗi":
    st.subheader("Tra cứu mã lỗi hoặc model")
    images_model ={"030169": "https://raw.githubusercontent.com/DuyKhong94/Handbook/1f4108a9f27662a2537e76bb64a9d7ae9dee3747/C169.png",
                   "030247": "https://raw.githubusercontent.com/DuyKhong94/Handbook/ca5f659fc4822d59df0ee1b3bf7298eaa245ed18/C247.png",
                   "159196": "https://raw.githubusercontent.com/DuyKhong94/Handbook/b1d234339cb426a268b08c63e11e16aafb16ea76/A1196.jpg",
                   "030218": "https://raw.githubusercontent.com/DuyKhong94/Handbook/cb55b1d7b4e2004aa2b77657789297bfdb2fc4fd/C218.png",
                   "030191": "https://raw.githubusercontent.com/DuyKhong94/Handbook/134c295588204061468f4a0e736e1dfa228a924c/C191.png",
                   "030267": "https://raw.githubusercontent.com/DuyKhong94/Handbook/a94e869481e8c3e1e2f348989bbc20014a3f85ea/C267.png",
                   "030041": "https://raw.githubusercontent.com/DuyKhong94/Handbook/f8f952035fe6fa5c06607d6793a61172aa12a8c0/C041.png",
                   "030412": "https://raw.githubusercontent.com/DuyKhong94/Handbook/f8f952035fe6fa5c06607d6793a61172aa12a8c0/C412.png",
                   "030198": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C198.png",
                   "030333": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C333.png",
                   "030291": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C291.png",
                   "030227": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C227.png",
                   "030221": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C221.png",
                   "030287": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C287.png",
                   "030289": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C289.png",
                   "030290": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C290.png",
                   "030248": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C248.png",
                   "030369": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C369.png",
                   "030243": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C243.png",
                   "030319": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C319.png",
                   "030345": "https://raw.githubusercontent.com/DuyKhong94/Handbook/19e36c797d8d2264b3dfe079f12323b948bf12de/122047.jpg",
                   "030246": "https://raw.githubusercontent.com/DuyKhong94/Handbook/b910a6c94946b8621b70656132d6f0a76e540038/C246.png"
                    }
    with st.form("form_search_model_tab2"):
        search_model = st.text_input("Nhập model cần tra cứu:",key="search_model_tab2")
        submit_model= st.form_submit_button("🔍 Tra cứu Model")
    prefix=search_model[:6]
    if submit_model and search_model:
        model=search_model.strip()[:6]
        if model in images_model:
            st.image(images_model[model])
        cursor = collection.find({"model": {"$regex":f"^{prefix[:6]}"}})
        data = list(cursor)
        if data:
            for d in data:
                d.pop("_id", None)
            df = pd.DataFrame(data)
            df1 = df.drop(columns=["image", "images", "pdf_report"], errors='ignore')
            st.dataframe(df1)
        else:
            st.warning("Không tìm thấy dữ liệu cho model này.")
            
    
    
    with st.form("form_search_code_tab2"):
        search_code = st.text_input("Nhập mã lỗi cụ thể (VD: 333J12ABC):",key="search_code_tab2")
        submit_code= st.form_submit_button("🔍 Tra cứu lịch sử lỗi")
        st.divider()
        if submit_code and search_code:
            result = collection.find_one({"error_code": search_code})
            col1, col2 = st.columns(2)    
            if result:
                with col1:
                    st.markdown("<b><u>Model No</u></b>",unsafe_allow_html=True)   
                    st.write(f" 📘 Model: {result['model']}")
                    st.markdown("<b><u>Problem Statement</u></b>",unsafe_allow_html=True)
                    st.write(f"  Mã lỗi: {result['error_code']}")
                    st.write(f"  Thời gian: {result.get('timestamp', 'Chưa có thông tin')}")
                    st.write(f"  Mô tả hiện tượng lỗi: {result['description']}")
                with col2:
                    st.markdown("<b><u>Root Cause</u></b>",unsafe_allow_html=True)
                    st.write(f"{result.get('root_cause', 'Chưa có thông tin')}")
                    st.markdown("<b><u>Effective Action Taken</u></b>",unsafe_allow_html=True)
                    st.write(f"{result.get('solution', 'Chưa có thông tin')}")
                    st.write(f"{result.get('improvement', 'Chưa có thông tin')}")
        
                # --- Hiển thị danh sách hình ---
                images = result.get("images", [])
                if images:
                    st.write(f"📸 Có {len(images)} hình minh hoạ:")
                    cols = st.columns(min(3, len(images)))
                    for i, img_url in enumerate(images):
                        cols[i % 3].image(img_url, caption=f"Ảnh {i+1}")
                else:
                    st.info("Không có hình ảnh minh hoạ cho lỗi này.")
        
                # --- File PDF ---
                pdf_url = result.get("pdf_report")
                if pdf_url:
                    st.markdown(f"[📄 Tải báo cáo PDF tại đây]({pdf_url})")
                else:
                    st.info("Không có file báo cáo PDF cho lỗi này.")
        
            else:
                st.error("❌ Không tìm thấy mã lỗi trong database.")

# Procedures Tab
elif mode == "📘 Quy Trình Phân tích":
    st.subheader("Quy Trình Xử Lý Lỗi Sản Phẩm RYOBI")
    st.divider()
    st.markdown("**Quy Trình Xử Lý Hàng Lỗi Trên Line Sản Xuất** ")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/5d53967118908656d91d073f0f723b3653267d95/3.jpg")
    st.markdown("""
    1. *Sản xuất:* Vai trò làm đúng thao tác theo WI, nếu phát sinh hàng lỗi về chức năng tại trạm thao tác phải thông báo cho PIE và điền Form"RPDNF0020".
    2. *IPQC:* Vai trò xác nhận bất thường về ngoại quan và cùng với MQA hoặc PIE phán định bất thường đó có là lỗi hay không.
    3. *PIE:* Vai trò chính phân tích lỗi ảnh hưởng tới chức năng sản phẩm và nếu phát hiện lỗi đó liên quan tới bộ phận nào thì báo đến bộ phận đó tìm cách cải thiện & hỗ trợ sản xuất & cùng với MQA tìm giải pháp tạm thời để tránh đứt quãng sản xuất .
    4. *MQA:* Vai trò hỗ trợ cùng với PIE phân tích & xác nhận kết quả & xác nhận bất thường có phải là lỗi hay không & đưa ra mức độ cho phép nếu bất thường đó không ảnh hưởng tới chức năng sản phẩm .
    5. *SQE:* Chịu trách nhiệm phân loại vật tư NG nếu lỗi đến từ vật tư đầu vào sau khi PIE/MQA phân tích & cải thiện vật tư đầu vào .
    """)
    st.markdown("""**Lưu ý: Hàng sau khi phân tích phải đánh dấu tròn "O" lên phích cắm trước khi trả lại cho sản xuất**""")         
    
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/7d1b28335ebbd203552ea93084496b16ff2946a7/2.jpg")

    st.divider()
    st.markdown("Quy trình Cảnh Báo Line Down")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/346bf96fec732bc713c93e9749bfa64d29509de8/1.jpg")
    st.markdown("***Điều Kiện Dừng Line***")
    st.markdown("""
    1. *Vấn đề an toàn*
    2. *Vấn đề chức năng sản phẩm nghiêm trọng*
    3. *Tỉ lệ sản phẩm AC/DC/BP/Charger không đạt 2pcs/giờ*
    4. *Nhân lực sản xuất nhàn rỗi quá 10 phút*
    """)
    st.markdown("***Quy Trình Xử Lý***")
    st.markdown("""
    1. Đối với vấn đề 4M thông thường thì PIE chủ đạo & MQA hỗ trợ cùng với PIE đánh giá đối sách cải thiện và kết quả.
    2. Đối với vấn đề liên quan tới thiết kế và thông số PCP/PM/Check Card: PIE/MQA/Engineering/QE phải cùng tạo 1 nhóm để giải quyết vấn đề.
    """)
    st.markdown("***Vai trò sau khi biết nguyên nhân***")
    st.markdown("""
    1. Vật tư đầu vào/sai liệu trong thùng nguyên: SQE/IQC
    2. Vấn đề thiết bị & Khuôn: Mass Production: PM or EB/QB/1stMP: PM/APE
    3. Vấn đề thiếu liệu: PMC
    4. Phát Sai liệu/phát liệu không kịp/Sai liệu trong thùng lẻ: RWH
    5. Vấn đề thao tác: PROD
    6. Vấn đề vẫn chưa ra nguyên nhân: PIE/MQA tiếp tục phân tích
    7. Vấn đề về phương pháp: IE
    """)
    st.markdown("***Lưu ý nếu sau 30 phút vấn đề được giải quyết và đảm bảo những yếu tố cho line sản xuất hoạt động thì sản xuất phải khôi phục hoạt động và bỏ cảnh báo line down này đi.***")
    st.markdown("***Lưu ý nếu vẫn chưa ra nguyên nhân và nguy cơ cao ảnh hưởng chất lượng thì sản xuất sắp xếp nhân lực qua khu vực khác để giảm tổn thất cho nhà máy và bộ phận PC điều chỉnh kế hoạch nếu có thể.***")

    st.divider()
    st.subheader("Sơ đồ liên hệ - Hotline:")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/276302b6f5a16ba5f5db7089cabe410b7cf19206/MQAchart.jpg")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/710c394ac305c7c018753d3bd5ec1dc58c541d7e/094237.jpg")
elif mode == "⚛ ERP System & WI":
    st.subheader("Xử lý trên hệ thống ERP")
    st.markdown("***Công dụng của ERP***")
    st.markdown("""
    1. *ERP dùng để tra cứu BOM theo mã model được ghi trên bảng sản lượng đầu line, ví dụ: 030383007, 030247012...*
    2. *ERP dùng để tra cứu ECO xem BOM job hoặc mã liệu đó có ECO hay không, thông thường để tra cứu phiên bản của mã vật tư đó có được sử dụng hay không.*
    3. *ERP cũng được dùng để tra cứu lý do và lịch sử thay đổi của mã vật tư.*
    4. *ERP dùng để tra cứu On Hand/ vật tư đó sử dụng cho model gì? và tra cứu model đó chạy từ bao lâu.*
    """)
    st.write(" Link: http://hkerpapp.hk.globaltti.net:8068/OA_HTML/AppsLocalLogin.jsp")
    st.write(" Link WI - copy & paste on thư mục: V:\Ryobi_PIE\Share\VN-WI")
    st.divider()
    st.markdown("**Tra cứu BOM & Mã WI của Console và Packing**")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/64b2d8e6548a748ac417d222ef945b5e821bb936/ERP.jpg")
    st.divider()
    st.markdown("**Tra cứu ECO**")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/283f48edd8d4c515187a5eab35f2a5215f29e03d/ECO.jpg")
    st.divider()
    st.markdown("**Tra cứu lượng vật tư tồn kho**")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/108246c370090edbf580a1021b98d1e6d912c6cd/091950.jpg")
    st.divider()
    st.subheader("Tra cứu số lượng sản phẩm của model bất kỳ đã sản xuất")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/029dc4e5fbd3e0ab1e5a18ec37bd5f8e2f311f2d/131254.jpg")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/eefaa55da7818f3bb86579da9312cca31c944f71/131834.jpg")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/a36d828ee14aa1e21e5ef68bc4a4f033554508df/134527.jpg")
elif mode == "☯ Team Center & FAI":
    st.subheader("Tra cứu Bản vẽ trên Team Center")
    st.write(" Link: https://cnstclb01.cn.globaltti.net/awc/#/showHome")
    st.markdown("""
    1. **Phải tra cứu BOM theo model đang chạy hoặc tìm đến tem nhãn của thùng vật tư để lấy mã vật tư và phiên bản
    2. **Đảm bảo tra cứu đúng mã, đúng phiên bản của vật tư để phân tích chính xác nhất.
    """)
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/e20c0fccc62799dad6c71c31240d7e284b60d26f/174513.jpg")
    st.divider()
    st.subheader("Tra cứu FAI Report")
    st.write(" Link: https://grd.cn.globaltti.net/")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/54a6630ad2224f86f85dc8beb2f33fb1670d9b17/131859.jpg")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/b6fb7809341b8a50b781037f300749dc273a1bf4/133456.jpg")
    st.divider()
    st.subheader("Tra cứu bản đồ nổ")
    st.write(" Link: https://intranet.cn.globaltti.net/QA/Repair_Sheet/Forms/AllItems.aspx?View={D501D1D9-93CE-4F94-B685-0F1B8E10B498}#InplviewHashd501d1d9-93ce-4f94-b685-0f1b8e10b498=")
    st.image("https://raw.githubusercontent.com/DuyKhong94/Handbook/96b1f43ef6b902a8c1c108f7af2bec47e1e7ae0a/123618.png")


elif mode == "Production Schedule":
    with st.container():

        uploaded_file = st.file_uploader("Chọn file DPS mới nhất", type=["xlsx", "xlsb"])

        if uploaded_file is not None:

            # Đọc sheet Combine (chỉ 1 lần)
            df_raw = pd.read_excel(uploaded_file, sheet_name="Combine", skiprows=3)
            df_raw.columns = df_raw.columns.str.strip()
            df_raw2 = pd.read_excel(uploaded_file, sheet_name="Combine", skiprows=2)
            df_raw2.columns = df_raw2.columns.str.strip()
            # Lấy bảng trái
            left_cols = ['TTI Model No', 'Job No', 'Curent line']
            #st.write("Columns in df_raw:", df_raw.columns.tolist())
            #st.write("Columns in df_raw:", df_raw2.columns.tolist())
            #st.write("Columns in df_raw:", df_raw3.columns.tolist())
            df_left = df_raw[left_cols].dropna(how='all')

            # Lấy bảng phải
            right_cols = ['Cur Date', 'Completion date']
            df_right = df_raw2[right_cols].dropna(how='all')

            # Đồng bộ index cho chắc chắn
            df_left = df_left.reset_index(drop=True)
            df_right = df_right.reset_index(drop=True)

            # Ghép 2 bảng chính xác theo index
            df2 = pd.concat([df_left, df_right], axis=1)

            # Loại bỏ các dòng hoàn toàn rỗng nếu có
            df2 = df2.dropna(how='all')

            
            # UI filter
            df2['Cur Date']=pd.to_datetime(df2['Cur Date'],errors='coerce')
            df2['Completion date']=pd.to_datetime(df2['Completion date'],errors='coerce')
            df2['Progress Time'] = (df2['Completion date'] - df2['Cur Date']).dt.total_seconds() / 86400
            selected_date = st.date_input("Chọn ngày muốn xem job chạy:")
            if selected_date:
                day_start = pd.to_datetime(str(selected_date) + " 00:00:00")
                day_end   = pd.to_datetime(str(selected_date) + " 23:59:59")
            
                df_filtered_by_date = df2[
                    (df2['Cur Date'] <= day_end) &
                    (df2['Completion date'] >= day_start)
                ]
            df_filtered_by_date=df_filtered_by_date[df_filtered_by_date['TTI Model No'].str.startswith(('030','011104','001457','001350','106','001597','001','001606','001540','001514','001406','011196','159196','054196','056196','PR001'),na=False)
                                & df_filtered_by_date['Job No'].str.startswith(('001','011104','030','QB','PR','MP','EB','ESB','106','054','056','159196','SAM','313','316','307','319','318','290','300003120','291','292'), na=False)]
            
            
            #st.dataframe(df_filtered_by_date[['TTI Model No','Job No','Curent line']])   
            df_calc = df_filtered_by_date.sort_values(by=['Curent line', 'Cur Date'])
            
            df_calc['change_flag'] = (
                df_calc['TTI Model No'] != df_calc.groupby('Curent line')['TTI Model No'].shift(1)
            ).astype(int)
            
            changeover_by_line = df_calc.groupby('Curent line')['change_flag'].sum() - 1
            
            total_changeover = changeover_by_line.sum()
            
            total_line = len(df_filtered_by_date['Curent line'].unique())
            total_model = df_filtered_by_date['TTI Model No'].count()
            

            model_list = df_filtered_by_date['Job No'].dropna().str[:9].unique().tolist()
            line_list=df_filtered_by_date['Curent line'].dropna().unique().tolist()
            prefixes_AC=('C2-012','C2-013','C2-032','C2-033')
            prefixes_pneu=('C2-055','C2-053')
            prefixes_PK=('C2-035','C2-036','C2-037','C2-038','C2-039','C2-056','C2-057','C2-058','C2-059')
            prefixes_sub=('C2-015','C2-020','C2-016','C2-017','C2-018','C2-019')
            prefixes_dc196=('C2-027','C2-028','C2-029','C2-034')
            prefixes_qb_ac=('C2-005')
            groups={"AC":['C2-012','C2-013','C2-032','C2-033'] ,
                    "Pneu Tool":['C2-055','C2-053'],
                    "Packing":['C2-035','C2-036','C2-037','C2-038','C2-039','C2-056','C2-057','C2-058','C2-059'],
                    "SUB":['C2-015','C2-020','C2-016','C2-017','C2-018','C2-019'],
                    "DC A1196":['C2-027','C2-028','C2-029','C2-034'],"QB":['C2-005']}
            group_values = {}
            for group_name, prefix_list in groups.items():
                mask=df_filtered_by_date['Curent line'].astype(str).str.startswith(tuple(prefix_list))
                count=df_filtered_by_date.loc[mask,'Curent line'].nunique()
                group_values[group_name]=count
            #st.write(group_values)
            names=list(group_values.keys())
            values=list(group_values.values())
            fig,ax=plt.subplots(figsize=(10, 3))
            bars=ax.bar(names, values, color="#90EE90")
            ax.set_xlabel("Khu Vực")
            ax.set_ylabel("Số lượng")
            ax.set_title(f"Số lượng Line theo khu vực: {selected_date}")
            ax.set_ylim([0,15])
            for bar in bars:
                height=bar.get_height()
                width=bar.get_x() + bar.get_width() /2
                
                ax.text(width,height +0.1,str(int(height)),ha='center',va='bottom')
            fig.tight_layout()
            st.pyplot(fig)
            
            
            mask_AC=(df_filtered_by_date['Curent line'].dropna().str.startswith(prefixes_AC))
            mask_pneu=(df_filtered_by_date['Curent line'].dropna().str.startswith(prefixes_pneu))
            mask_pk=(df_filtered_by_date['Curent line'].dropna().str.startswith(prefixes_PK))
            mask_sub=(df_filtered_by_date['Curent line'].dropna().str.startswith(prefixes_sub))
            mask_dc196=(df_filtered_by_date['Curent line'].dropna().str.startswith(prefixes_dc196))
            mask_qb=(df_filtered_by_date['Curent line'].dropna().str.startswith(prefixes_qb_ac))
            
            total_line_AC=df_filtered_by_date.loc[mask_AC,'Curent line'].nunique()
            line_list_AC=df_filtered_by_date.loc[mask_AC,'Curent line'].unique().tolist()
            total_line_pneu=df_filtered_by_date.loc[mask_pneu,'Curent line'].nunique()
            line_list_pneu=df_filtered_by_date.loc[mask_pneu,'Curent line'].unique().tolist()
            total_line_pk=df_filtered_by_date.loc[mask_pk,'Curent line'].nunique()
            line_list_pk=df_filtered_by_date.loc[mask_pk,'Curent line'].unique().tolist()
            total_line_sub=df_filtered_by_date.loc[mask_sub,'Curent line'].nunique()
            line_list_sub=df_filtered_by_date.loc[mask_sub,'Curent line'].unique().tolist()
            total_line_dc196=df_filtered_by_date.loc[mask_dc196,'Curent line'].nunique()
            line_list_dc196=df_filtered_by_date.loc[mask_dc196,'Curent line'].unique().tolist()
            line_list_qb=df_filtered_by_date.loc[mask_qb,'Curent line'].unique().tolist()     
            
            st.markdown(f"**Tổng số line trong ngày (Bao gồm line QB ): {total_line}**")
            st.markdown(f"**Tổng số changeover trong ngày(Bao gồm line QB ): {int(total_changeover)}**")
            #st.markdown(f"**Danh sách model trong ngày: {model_list}**")
            #st.markdown(f"**Danh sách line: {line_list}**")
            #st.markdown(f"**Tổng số line AC: {total_line_AC} | Danh sách line AC: {line_list_AC}**")
            #st.markdown(f"**Tổng số line Pneumactic tool: {total_line_pneu} | Danh sách line Pneumatic: {line_list_pneu}**")
            #st.markdown(f"**Tổng số line PK: {total_line_pk} | Danh sách line PK: {line_list_pk}**")
            #st.markdown(f"**Tổng số line Sub: {total_line_sub} | Danh sách line Sub: {line_list_sub}**")
            #st.markdown(f"**Tổng số line DC A1196: {total_line_dc196} | Danh sách line DC A1196: {line_list_dc196}**")
            df_filtered_by_date['Job9'] = df_filtered_by_date['Job No'].astype(str).str[:11]

            line_job_dict = (
                df_filtered_by_date
                .groupby('Curent line')['Job9']
                .apply(lambda x: sorted(x.unique()))
                .to_dict()
            )
            df_line_model = pd.DataFrame([
                {"Curent line": line, "Danh sách model": ", ".join(models)}
                for line, models in line_job_dict.items()
            ])

            # Tạo mapping line → type
            line_type_map = {}
            
            for line in line_list_AC:
                line_type_map[line] = "AC"
            
            for line in line_list_pneu:
                line_type_map[line] = "Pneumatic"
            
            for line in line_list_pk:
                line_type_map[line] = "PK"
            
            for line in line_list_sub:
                line_type_map[line] = "SUB"
            
            for line in line_list_dc196:
                line_type_map[line] = "DC A1196"
            for line in line_list_qb:
                line_type_map[line] = "QB AC"
            
            # Thêm cột Type vào df_line_model
            df_line_model["Category"] = df_line_model["Curent line"].map(line_type_map).fillna("")
            df_line_model["Changeover"] = df_line_model["Danh sách model"].apply(
                lambda s: "YES" if len(s.split(", ")) > 1 else "NO"
            )
        
            st.dataframe(df_line_model, use_container_width=True)

            
            st.divider()
            selected_line = st.selectbox("Chọn số line", df2['Curent line'].dropna().unique())

            
            df3 = df2[df2['Curent line'] == selected_line]
            df4=pd.read_excel(uploaded_file,sheet_name=selected_line,skiprows=3)
            quantity_col=['Job No','Need Bulit QTY']
            df_left2=df4[quantity_col].dropna(how='all')
            df5=pd.merge(df3,df_left2, on='Job No',how='left')
            
            
            st.subheader(f"{selected_line}: thống kê số liệu sản xuất")
            
            
            # Tính tổng QTY
            total_quantity_sum = df5['Need Bulit QTY'].astype(float).sum()

            # Tính số job EB / QB / MP / PR
            total_verification_job = df5[df5['Job No'].str.startswith(('EB','QB','MP','PR'), na=False)]
            total_verification_job_count = len(total_verification_job['Job No'].unique())

            #Hiển thị
            st.markdown(f"**Tổng số lượng (pcs): {int(total_quantity_sum):,}**")
            st.markdown(f"**Tổng số job EB QB 1stMP PR: {total_verification_job_count}**")
            
            import matplotlib.dates as mdates
            from datetime import timedelta
            
            # --- Chuẩn hoá dữ liệu trước khi plot ---
            # 1) convert datetime, loại bỏ các dòng thiếu start hoặc end
            df5['Cur Date'] = pd.to_datetime(df5['Cur Date'], errors='coerce')
            df5['Completion date'] = pd.to_datetime(df5['Completion date'], errors='coerce')
            
            # Drop hoặc giữ nhưng width = 0 cho các dòng thiếu
            df_plot = df5.dropna(subset=['Cur Date', 'Completion date']).copy()
            
            # 2) (tùy chọn) sắp xếp theo Cur Date để bars nối nhau hợp lý
            df_plot = df_plot.sort_values(by='Cur Date').reset_index(drop=True)
            
            # 3) convert to matplotlib numeric dates (1.0 = 1 day)
            start_nums = mdates.date2num(df_plot['Cur Date'])
            end_nums = mdates.date2num(df_plot['Completion date'])
            widths = end_nums - start_nums  # width in days (float)
            
            # nếu có negative widths (end < start), bạn có thể log / set thành 0
            neg_idx = widths < 0
            if neg_idx.any():
                # bạn có thể in ra các Job No sai để debug
                st.warning(f"Có {neg_idx.sum()} job có Completion date < Cur Date (đã set width = 0).")
                widths[neg_idx] = 0
            
            # --- Plot ---
            fig, ax = plt.subplots(figsize=(12,6))
            
            # vị trí y: dùng range(len(df_plot)) để đảm bảo mapping đúng (1:1 với label)
            y_pos = range(len(df_plot))
            
            # vẽ barh: left cần là start_nums (numeric), width là widths (numeric)
            ax.barh(y=y_pos, width=widths, left=start_nums, height=0.6, color='#90EE90', align='center')
            qty_list = df_plot['Need Bulit QTY'].fillna(0).astype(int).tolist()

            for i, (start, width, qty) in enumerate(zip(start_nums, widths, qty_list)):
                if width > 0:
                    x_text = start + width / 2
                    y_text = i
                    label = f"{qty:,}"     # hiển thị số có dấu phẩy
        
                    ax.text(x_text, y_text, label,
                            ha='center', va='center', fontsize=9,
                            fontweight='bold', color='black')
            
            # set y ticks thành Job No (theo cùng thứ tự)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(df_plot['Job No'])
            
            # Format trục x là datetime
            ax.xaxis_date()
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))   # tùy chỉnh interval
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
            plt.xticks(rotation=90)
            
            ax.set_xlabel('Days')
            ax.set_ylabel('Job No')
            ax.set_title('Plan Schedule')
            plt.tight_layout()
            
            st.pyplot(fig)
            st.dataframe(df5[['TTI Model No','Job No','Curent line','Cur Date','Completion date','Need Bulit QTY','Progress Time']])
            st.divider()
            #st.dataframe(df2)

elif mode == "Link Tham Khảo":
    st.markdown("[1. Six Sigma Black Belt Handbook Third Edition - Source: American Society of Quality](https://raw.githubusercontent.com/DuyKhong94/Handbook/90925edaa2a9c904df7d211e738daf0826aacee0/0.%20MUST%20READ_Hand%20Book%20Black.pdf)")
    st.markdown("[2. The Certificated Six Sigma Master Black Belt Handbook - Source: American Society of Quality](https://raw.githubusercontent.com/DuyKhong94/Handbook/16ee5e98e6aa24b76739705150bb37cf4fff3584/01%20The%20Certified%20Six%20Sigma%20Master%20Blac%20T.M.Kubiak%20(002)%201.pdf)")
    st.markdown("[3. Quy trình xử lý hàng lỗi trên line - Author: Ni Nguyen](https://res.cloudinary.com/dij9ajlgm/image/upload/v1764746424/ROIPIE0016B_In-process_Reject_Operating_Instruction_4Mar.25_glp8ci.pdf)")
    st.markdown("[4. Quy trình & Điều Kiện phát cảnh báo Line Down - Author: Ni Nguyen](https://res.cloudinary.com/dij9ajlgm/image/upload/v1764746737/ROIPIE0015_A-_Line_Down_Alarm_Operating_Instruction_xuthwd.pdf)")
    st.markdown("[5. Giới thiệu sản phẩm Battery - Author: Ryan](https://res.cloudinary.com/dij9ajlgm/image/upload/v1764748575/22-1_Battery_Pack_Design_and_Process_-_new_Format_ubypxc.pdf)")
    st.markdown("[6. Giới thiệu sản phẩm Battery(2) - Author: Ryan](https://res.cloudinary.com/dij9ajlgm/image/upload/v1764749441/26_BP_EE_Trainning_fhupid.pdf)")
    st.markdown("[7. Giới thiệu sản phẩm Máy Khoan & Máy Siết Bu Lông DC - Author: PEDC](https://res.cloudinary.com/dij9ajlgm/image/upload/v1764748763/22-2._Training_of_drill_driver_design_and_process_Tuan_english_version_new_format_vi4i02.pdf)")
    st.markdown("[8. Giới thiệu sản phẩm Máy Cắt DC - Author: PEDC](https://res.cloudinary.com/dij9ajlgm/image/upload/v1764749206/22-3._Training_of_Cutting_tools_Tuan_english_version_new_format_v0ihcz.pdf)")
    st.markdown("[9. Giới thiệu sản phẩm máy mài DC - Author: PEDC](https://res.cloudinary.com/dij9ajlgm/image/upload/v1764749208/22-4._Training_of_grinder_design_and_process_Tuan_english_version_new_format_vqnlsn.pdf)")
    st.markdown("[10. Giới thiệu sản phẩm AC - Author: Duy Khong](https://res.cloudinary.com/dij9ajlgm/image/upload/v1764749440/28._AC_Failure_Analysis_-_RYOBI_1_gzh635.pdf)")
    st.markdown("[11. Giới thiệu sản phẩm Pneumatic Nailer - Author: ME](https://res.cloudinary.com/dij9ajlgm/image/upload/v1764823583/22-5_Pneumatic_Tools_Design_and_Process_ENG_version_Red_new_format_nsi8lz.pdf)")
    st.markdown("[12. Tài liệu DOE - Author: Ni Nguyen ](https://res.cloudinary.com/dij9ajlgm/image/upload/v1764749441/27._DOE_-_RYOBI_slbk44.pdf)")
    st.markdown("[13. Tài liệu MSA GR&R - Author: Ni Nguyen](https://res.cloudinary.com/dij9ajlgm/image/upload/v1764749440/30_MSA_GRR_tn740z.pdf)")
elif mode == "Trang tính":
    col1, col2 = st.columns(2)
    with col1:
        dimension=st.number_input("Nhập Kích thước danh nghĩa(mm)",format="%.3f")
        upper_tollerence=st.number_input("Nhập dung sai trên",format="%.3f")
        lower_tollerence=st.number_input("Nhập dung sai dưới",format="%.3f")

        
        result_upper= dimension + upper_tollerence
        result_lower= dimension + lower_tollerence
    with col2:
        if st.button("🧮 Tính Toán"):
            if result_upper <= result_lower:
                st.error("Cần xem lại nhập đúng cận trên/cận dưới hay chưa")
            else: 
                st.write(f"🔼 Upper Limit: **{result_upper:.3f} mm**")
                st.write(f"🔽 Lower Limit: **{result_lower:.3f} mm**")
                st.info(
                    f"📌 Nếu đo bằng **PIN GAUGE**:\n"
                    f"- GO PIN = {result_lower - 0.01:.2f} mm\n"
                    f"- NO-GO PIN = {result_upper + 0.01:.2f} mm"
                )
        
elif mode == "Chat Bot":
    
   
    #st.title("I'm Curious Bot")

    client = OpenAI(api_key=st.secrets["OPENROUTER_API_KEY"],
                   base_url="https://openrouter.ai/api/v1")
    

    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
  
    

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if prompt := st.chat_input("you type here"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown("Anh PE May Mắn:  " + prompt)
    
        with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/DuyKhong94/Handbook/94fe8517a617d2b97cd20bd0ad834220d36b63f2/OIP.jpg"):
            response = client.chat.completions.create(
                model="z-ai/glm-4.5-air:free",
                messages=st.session_state.messages
                )
            reply = response.choices[0].message.content
            st.markdown("Idol Tập Sự:  " + reply)         
        st.session_state.messages.append({"role": "assistant", "content": reply})

    

  
    




















































































































































































































































































































































































































