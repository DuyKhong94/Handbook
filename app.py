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
import unicodedata
import re
import urllib.parse
import textwrap
import webbrowser
from deep_translator import GoogleTranslator
from github_uploader import upload_file_to_github
from streamlit_autorefresh import st_autorefresh
require_login()

# ------------------ MongoDB ------------------
def get_db():
    url = os.getenv("MONGO_URL")
    client = MongoClient(url)
    db = client["handbook"]
    return db
@st.cache_data(ttl=60)
def load_excel(linedown_lending_manhour_url):
    return pd.read_excel(linedown_lending_manhour_url,sheet_name="Quality & Downtime",skiprows=1)

def load_csv(url1):
    return pd.read_csv(url1)
# def my_autopct(pct):
#     total = df_mat_sum["Value"].sum()
#     val = int(pct * total / 100)
#     return f'{pct:.1f}%\n({val})'
    
db = get_db()
collection = db["errors"]

# ------------------ Streamlit config ------------------
st.set_page_config(page_title="Process Engineering Handbook", layout="wide")
st.title("Process Engineering Handbook")
st.sidebar.image("https://raw.githubusercontent.com/DuyKhong94/1/aca558477a183490a42f138c9fb2c46b7caeb2ca/logo.png",use_container_width=True)
st.sidebar.markdown("---")
mode=st.sidebar.radio("APPLICATION FEATURES:",["📈 Dashboard","➕ Thêm lỗi mới", "📘 Quy Trình Phân tích",
                                        "🔍 ERP System & WI","☯ Team Center & FAI","📂Link Tham Khảo","📱Trang tính","🔥Trợ lý AI","📋Daily Pass Down"])
st.sidebar.markdown("---")
st.sidebar.text(" ⭐⭐⭐Feel free to contact me at ✉: khongtrungduy12@gmail.com")

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
    new_file =st.file_uploader("Chọn file báo cáo Lending & Linedown mới nhất")
    if st.button("Save & Sync PDN Report"):
        if new_file is not None:

        # tạo file tạm
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(new_file.read())
                temp_path = tmp.name    


    # 2. upload lên GitHub
            result = upload_file_to_github(
                token=st.secrets["GITHUB_TOKEN"],  # best practice 🔥
                owner="DuyKhong94",
                repo="Handbook",
                file_path_repo="Lending - Rework manhours data 2026.xlsx",
                file_path_local=temp_path,
                commit_message="update from streamlit app"
            )

        st.success("Uploaded to GitHub!")
        st.write(result)

    else:
        st.warning("Vui lòng chọn file trước!")

    new_file2 =st.file_uploader("Chọn file báo cáo EOL mới nhất")
    if st.button("Save & Sync EOL"):
        if new_file2 is not None:

        # tạo file tạm
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                tmp.write(new_file2.read())
                temp_path = tmp.name    


    # 2. upload lên GitHub
            result1= upload_file_to_github(
                token=st.secrets["GITHUB_TOKEN"],  # best practice 🔥
                owner="DuyKhong94",
                repo="Handbook",
                file_path_repo="EOL Daily Report Power Automate.csv",
                file_path_local=temp_path,
                commit_message="update from streamlit app"
            )

        st.success("Uploaded to GitHub!")
        st.write(result1)

    else:
        st.warning("Vui lòng chọn file trước!")

# # ==========================================================
# # 🔍 TAB 2: TRA CỨU LỖI
# # ==========================================================
# elif mode == "🔍 Tra cứu lỗi":
#     st.subheader("Tra cứu mã lỗi hoặc model")
#     images_model ={"030169": "https://raw.githubusercontent.com/DuyKhong94/Handbook/1f4108a9f27662a2537e76bb64a9d7ae9dee3747/C169.png",
#                    "030247": "https://raw.githubusercontent.com/DuyKhong94/Handbook/ca5f659fc4822d59df0ee1b3bf7298eaa245ed18/C247.png",
#                    "159196": "https://raw.githubusercontent.com/DuyKhong94/Handbook/b1d234339cb426a268b08c63e11e16aafb16ea76/A1196.jpg",
#                    "030218": "https://raw.githubusercontent.com/DuyKhong94/Handbook/cb55b1d7b4e2004aa2b77657789297bfdb2fc4fd/C218.png",
#                    "030191": "https://raw.githubusercontent.com/DuyKhong94/Handbook/134c295588204061468f4a0e736e1dfa228a924c/C191.png",
#                    "030267": "https://raw.githubusercontent.com/DuyKhong94/Handbook/a94e869481e8c3e1e2f348989bbc20014a3f85ea/C267.png",
#                    "030041": "https://raw.githubusercontent.com/DuyKhong94/Handbook/f8f952035fe6fa5c06607d6793a61172aa12a8c0/C041.png",
#                    "030412": "https://raw.githubusercontent.com/DuyKhong94/Handbook/f8f952035fe6fa5c06607d6793a61172aa12a8c0/C412.png",
#                    "030198": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C198.png",
#                    "030333": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C333.png",
#                    "030291": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C291.png",
#                    "030227": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C227.png",
#                    "030221": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C221.png",
#                    "030287": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C287.png",
#                    "030289": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C289.png",
#                    "030290": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C290.png",
#                    "030248": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C248.png",
#                    "030369": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C369.png",
#                    "030243": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C243.png",
#                    "030319": "https://raw.githubusercontent.com/DuyKhong94/Handbook/586c5365ff38d3e678931ca84c162cf4a6743967/C319.png",
#                    "030345": "https://raw.githubusercontent.com/DuyKhong94/Handbook/19e36c797d8d2264b3dfe079f12323b948bf12de/122047.jpg",
#                    "030246": "https://raw.githubusercontent.com/DuyKhong94/Handbook/b910a6c94946b8621b70656132d6f0a76e540038/C246.png"
#                     }
#     with st.form("form_search_model_tab2"):
#         search_model = st.text_input("Nhập model cần tra cứu:",key="search_model_tab2")
#         submit_model= st.form_submit_button("🔍 Tra cứu Model")
#     prefix=search_model[:6]
#     if submit_model and search_model:
#         model=search_model.strip()[:6]
#         if model in images_model:
#             st.image(images_model[model])
#         cursor = collection.find({"model": {"$regex":f"^{prefix[:6]}"}})
#         data = list(cursor)
#         if data:
#             for d in data:
#                 d.pop("_id", None)
#             df = pd.DataFrame(data)
#             df1 = df.drop(columns=["image", "images", "pdf_report"], errors='ignore')
#             st.dataframe(df1)
#         else:
#             st.warning("Không tìm thấy dữ liệu cho model này.")
            
    
    
#     with st.form("form_search_code_tab2"):
#         search_code = st.text_input("Nhập mã lỗi cụ thể (VD: 333J12ABC):",key="search_code_tab2")
#         submit_code= st.form_submit_button("🔍 Tra cứu lịch sử lỗi")
#         st.divider()
#         if submit_code and search_code:
#             result = collection.find_one({"error_code": search_code})
#             col1, col2 = st.columns(2)    
#             if result:
#                 with col1:
#                     st.markdown("<b><u>Model No</u></b>",unsafe_allow_html=True)   
#                     st.write(f" 📘 Model: {result['model']}")
#                     st.markdown("<b><u>Problem Statement</u></b>",unsafe_allow_html=True)
#                     st.write(f"  Mã lỗi: {result['error_code']}")
#                     st.write(f"  Thời gian: {result.get('timestamp', 'Chưa có thông tin')}")
#                     st.write(f"  Mô tả hiện tượng lỗi: {result['description']}")
#                 with col2:
#                     st.markdown("<b><u>Root Cause</u></b>",unsafe_allow_html=True)
#                     st.write(f"{result.get('root_cause', 'Chưa có thông tin')}")
#                     st.markdown("<b><u>Effective Action Taken</u></b>",unsafe_allow_html=True)
#                     st.write(f"{result.get('solution', 'Chưa có thông tin')}")
#                     st.write(f"{result.get('improvement', 'Chưa có thông tin')}")
        
#                 # --- Hiển thị danh sách hình ---
#                 images = result.get("images", [])
#                 if images:
#                     st.write(f"📸 Có {len(images)} hình minh hoạ:")
#                     cols = st.columns(min(3, len(images)))
#                     for i, img_url in enumerate(images):
#                         cols[i % 3].image(img_url, caption=f"Ảnh {i+1}")
#                 else:
#                     st.info("Không có hình ảnh minh hoạ cho lỗi này.")
        
#                 # --- File PDF ---
#                 pdf_url = result.get("pdf_report")
#                 if pdf_url:
#                     st.markdown(f"[📄 Tải báo cáo PDF tại đây]({pdf_url})")
#                 else:
#                     st.info("Không có file báo cáo PDF cho lỗi này.")
        
#             else:
#                 st.error("❌ Không tìm thấy mã lỗi trong database.")

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
elif mode == "🔍 ERP System & WI":
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


elif mode == "📂Link Tham Khảo":
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
elif mode == "📱Trang tính":
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
        
elif mode == "🔥Trợ lý AI":

    client = OpenAI(
        api_key=st.secrets["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1"
    )

    # ================= NORMALIZE TEXT =================
    def normalize_text(text):
        text = text.lower()
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        return text

    def detect_intent(prompt):
        prompt_lower = prompt.lower().strip()
        if re.fullmatch(r"\d{5,}", prompt_lower):
            return "search_defect", prompt_lower
        if re.search(r"(check|tra cứu|tìm lỗi|lịch sử)\s*\d{5,}", prompt_lower):
            model = re.search(r"\d{5,}", prompt_lower).group()
            return "search_defect", model
    
        return "chat", None

    # ================= SEARCH FUNCTION =================
    def search_defect(query):
        if not query:
            return []

        query = str(query)
        query_norm = normalize_text(query.strip())

        # CASE 1: MODEL
        if query_norm.isdigit():
            prefix = query_norm[:6]
            return list(collection.find({
                "model": {"$regex": f"^{prefix}"}
            }).limit(20))

        # CASE 2: ERROR CODE
        result = collection.find_one({
            "error_code": {"$regex": f"^{query.strip()}", "$options": "i"}
        })
        if result:
            return [result]

        # CASE 3: TEXT SEARCH
        keywords = query_norm.split()
        results = list(collection.find())

        scored = []
        for r in results:
            text = normalize_text(
                r.get("description", "") +
                r.get("root_cause", "")
            )
            score = sum(k in text for k in keywords)

            if score > 0:
                scored.append((score, r))

        scored.sort(reverse=True, key=lambda x: x[0])
        return [r for _, r in scored[:5]]

    # ================= SESSION =================
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ================= INPUT =================
    prompt = st.chat_input("You type here...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user", avatar="https://raw.githubusercontent.com/DuyKhong94/Handbook/6c191b5d17d7df6d3c4778a62a0d1cba4f1bd5f7/19948569.jpg"):
            st.markdown("Thợ cơ khí: " + prompt)

        intent, model = detect_intent(prompt)
        results = []
        top_result = None

        # ================= CASE 1: SEARCH MODEL =================
        if intent == "search_defect" and model:
            results = search_defect(model)

            with st.chat_message("assistant"):
                st.markdown(f"## 📋 Danh sách lỗi model {prompt}")

                if not results:
                    st.warning("Không tìm thấy dữ liệu")
                else:
                    for r in results:
                        error_code = r.get("error_code")

                        with st.expander(f"🔧 {error_code} - {r.get('description', '')}"):
                            st.write(f"📌 {r.get('description')}")
                            st.write(f"🔍 {r.get('root_cause')}")
                            st.write(f"🛠 {r.get('solution')}")
                            st.write(f"{r.get('improvement')}")

                            images = r.get("images") or []
                            if images:
                                cols = st.columns(min(3, len(images)))
                                for i, img in enumerate(images):
                                    cols[i % 3].image(img, caption=error_code)

            reply = f"Tìm thấy {len(results)} lỗi cho model {prompt}"

        # ================= CASE 2: AI =================
        else:

            with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/DuyKhong94/Handbook/32e2602963f4b3a1e668fa9b6c4ea4310577838e/6244668958904618602_109.jpg"):

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "you are a helpful asistant"},
                        {"role": "user", "content": str(prompt)}
                    ]
                )

                reply = response.choices[0].message.content
                st.markdown("Eimi Fukada: " + reply)

                # ================= SHOW IMAGE =================
                if top_result:
                    st.markdown(f"### 🔧 {top_result.get('error_code')}")

                    images = top_result.get("images") or []

                    if images:
                        cols = st.columns(min(3, len(images)))
                        for i, img in enumerate(images):
                            cols[i % 3].image(img, caption=top_result.get('error_code'))
                    else:
                        st.info("Không có ảnh minh hoạ")

        st.session_state.messages.append({"role": "assistant", "content": reply})

# # ==========================================================
# # 🔍 TAB : PASSDOWN
# # ==========================================================
elif mode == "📋Daily Pass Down":
    st.header("📋 Daily Pass Down")
    def remove_vietnamese_accents(text):
    
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        text = text.replace('đ', 'd').replace('Đ', 'D')
        return text
    col1, col2=st.columns([1,1])
    cases=["0 Case","1 Case","2 Cases","3 Cases","4 Cases","5 Cases"]
   
    
    with col1:
        shifts=["Day Shift","Night Shift"]
        shift=st.selectbox("Chọn ca",shifts)
        quality=st.selectbox("Quality Issues",cases)
        linedown=st.selectbox("Linedown Issues",cases)
        document=st.selectbox("Document Findings",cases)
        pending=st.selectbox("Pending Analysis",cases)
        outstanding=st.selectbox("Outstanding EOL Issues",cases)
    with col2:
        
        areas=["EEC","ACPK"]
        area=st.selectbox("Focused Factory",areas)
        names =["Nguyen Si Phu","Ha Thanh Dien","Dong Dinh Chanh","Nguyen Ngoc Dinh"]
        name = st.selectbox("Select Your name", names)
          
 
        text = st.text_area("Nhập notes (xin hãy nhập tiếng việt, bạn không cần cố gắng dịch đâu để mình giúp bạn nhé 😊)",height=320)
        translated_text=GoogleTranslator(source='vi',target='en').translate(text)
        # Xóa dòng trống ở đầu
        lines=translated_text.split("\n")
        if len(lines)>1:
            indented_lines=[lines[0]] + [f"    {line}" for line in lines[1:]]
        else:
            indented_lines=lines
        result = "\n".join(indented_lines)
            

        
    
        # Date + Name (optional)
        today = datetime.today().strftime("%d/%m/%Y")

  
   #body of email
    body =f"""
    Dear ACBP Team & Leaders,
    I would like to pass down {area}-{shift}-{today}:
    💠Quality issues: {quality}
    💠Linedown issues: {linedown}
    💠Document issue findings: {document}
    💠Pending analysis: {pending}
    💠Outstanding Issues:{outstanding}

    
    📝{shift} Notes:       
    {result}
    
    Wishing the team great things and a productive day ahead 😘
    
    Thanks & Best Regards,
    {name}
    """
    body_encoded = urllib.parse.quote(body,encoding="utf-8")
    subject_encoded = urllib.parse.quote(f"Daily Pass Down - {name} - {today} - {shift}",encoding="utf-8")
    mail_to_link=f"mailto:ryobiacbppe@ttigroup.com.vn?subject={subject_encoded}&body={body_encoded}&cc=VinhNghi.Luu@ttigroup.com.vn;DJ.Dong@ttigroup.com.vn"
    


    #st.markdown(f'<a href="{mail_to_link}" target="_blank">📩 Send Passdown Email</a>',
    # unsafe_allow_html=True
    # )
    st.markdown(
        f"""
        <a href="{mail_to_link}" target="_blank">
            <button style="
                background-color:#4CAF50;
                color:white;
                padding:10px 20px;
                border:none;
                border-radius:5px;
                cursor:pointer;
                font-size:16px;">
                📩 Send Passdown Email
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )
elif mode == "📈 Dashboard":
    #st.write("working on it")
    st_autorefresh(interval=60000)
    linedown_lending_manhour_url="https://raw.githubusercontent.com/DuyKhong94/Handbook/main/Lending%20-%20Rework%20manhours%20data%202026.xlsx"
    #df=pd.read_excel(linedown_lending_manhour_url,sheet_name="Quality & Downtime",skiprows=1)
    df=load_excel(linedown_lending_manhour_url)
    df1=df[df["Initial Owner"] == "PIE - Analysis"] # lọc theo PIE - Analysis
    df2=df1[df1["Confirm Owner"] =="PIE"] # Lọc 1 lần nữa về PIE confirmed
    acpk_models=["030","106","001597","001406","001606","001504","001997","053","30","011104","159196"] # list về AC PK models
    dc_models=["011","159","010","095","096","000","010","95","96","108","109","040"] # list ve DC models
    df4=df2[df2["Product"].astype(str).str.startswith(tuple(dc_models))] # lọc theo list dc_models với 3 số bắt đầu theo hàm startswith
    df3=df2[df2["Product"].astype(str).str.startswith(tuple(acpk_models))] # lọc theo list acpk_models với 3 số bắt đầu theo hàm startswith
    #ACPK
    sum_manhours_acpk=df3["Total Man. Hour"].sum() # tổng số giờ công 
    sum_manhours_acpk_usd =round(sum_manhours_acpk * 4.52,2)
    # st.markdown(f"Total Line Down Man Hours ACPK: {sum_manhours_acpk}")
    # st.markdown(f"Total Line Down Man Hours ACPK USD Exchanged: {sum_manhours_acpk_usd:.3f} $$")
    #DC    
    sum_manhours_dc=df4["Total Man. Hour"].sum() # tổng số giờ công 
    sum_manhours_dc_usd =round(sum_manhours_dc * 4.52,2)
    # st.markdown(f"Total Line Down Man Hours DC: {sum_manhours_dc}")
    # st.markdown(f"Total Line Down Man Hours DC USD Exchanged: {sum_manhours_dc_usd:.3f} $$")
    #EEC
    eec_models=["130","240417"]
    df5=df2[df2["Product"].astype(str).str.startswith(tuple(eec_models))] # lọc theo list eec_models với 3 số bắt đầu theo hàm startswith
    sum_manhours_eec=df5["Total Man. Hour"].sum() # tổng số giờ công 
    sum_manhours_eec_usd =round(sum_manhours_eec * 4.52,2) # tinh tien
    # st.markdown(f"Total Line Down Man Hours EEC: {sum_manhours_eec}")
    # st.markdown(f"Total Line Down Man Hours EEC USD Exchanged: {sum_manhours_eec_usd:.3f} $$")

    df_pie=pd.DataFrame({
        "Area":["ACPK","DC","EEC"],
        "Value":[sum_manhours_acpk_usd,sum_manhours_dc_usd,sum_manhours_eec_usd],
        "Value2":[sum_manhours_acpk,sum_manhours_dc,sum_manhours_eec]})
        
    fig, axs = plt.subplots(3,3, figsize=(10, 5))
    bars=axs[0,0].bar(df_pie["Area"],df_pie["Value2"],color='green')
    axs[0,0].tick_params(axis='x', labelsize=8)
    #axs[0].bar_label(bars, fontsize=8,padding=3)
    axs[0,0].set_title("AREA & LOSS")
    for bar in bars:
        height=bar.get_height()
        x=bar.get_x() + bar.get_width()/2
        axs[0,0].text(x,height*1.01,f"{height:.2f}",ha='center',va='bottom',fontsize=8)
    axs[0,0].set_ylim(0, max(df_pie["Value2"]) + 50)


        
    #PIE CHART
    wedges, texts = axs[0,1].pie(df_pie["Value"], startangle=90)
     
    for i, (p, val, area) in enumerate(zip(wedges, df_pie["Value"], df_pie["Area"])):
        ang = (p.theta2 - p.theta1)/2. + p.theta1
        y = np.sin(np.deg2rad(ang))
        x = np.cos(np.deg2rad(ang))
    
        # 👇 ép ACPK sang trái, EEC sang phải
        if area == "ACPK":
            x_text = -1.5
        elif area == "EEC":
            x_text = 1.7
        else:
            x_text = 1.4 * np.sign(x)
        horizontalalignment = "left" if x_text > 0 else "right"
        axs[0,1].annotate(
            f" PE-{df_pie["Area"].iloc[i]}: {df_pie["Value"].iloc[i]} $",
            xy=(x, y),                      # điểm trên pie
            xytext=(x_text,1.4*y), # vị trí text (ra xa)
            horizontalalignment=horizontalalignment,
            fontsize=8,
            arrowprops=dict(
                arrowstyle="-",
                connectionstyle=f"angle,angleA=0,angleB={ang}"
                )
            )
    centre_circle = plt.Circle((0, 0), 0.5, fc='white')
    fig.gca().add_artist(centre_circle)
        
    axs[0,1].legend(df_pie["Area"],loc='lower right',bbox_to_anchor=(1.8, 0),title="Dollars Cont.",fontsize=5,title_fontsize=5)
    


    ## Scatter Plot
    url1="https://raw.githubusercontent.com/DuyKhong94/Handbook/main/EOL%20Daily%20Report%20Power%20Automate.csv"
    #df6=pd.read_csv(url1)
    df6=load_csv(url1)
    
    #AC Ha Thanh Dien
    df6=df6[df6["Focused Factory"].isin(["High Mix","EEC"])] #loc theo khu vuc high mix
    df6["Target Date"] = pd.to_datetime(df6["Target Date"], errors="coerce")

    df6 = df6[df6["Target Date"] >= "2026-01-01"]
    models=acpk_models + eec_models
    #df11=df6[df6["Model"].astype(str).str.startswith(tuple(models))]
    df7=df6[df6["Model"].astype(str).str.startswith(tuple(models))] # loc theo model acpk + eec
    df8=df7[df7["PE PIC"]=="Ha Thanh Dien (VN.RYOBI-PIE)"]
    eol_count_dien=df8["PE PIC"].count() + 12
    #st.markdown(eol_count)
    #st.dataframe(df11)
    
    #AC Dong Dinh Chanh
    df9=df7[df7["PE PIC"]=="Dong Dinh Chanh (VN.RYOBI-PIE)"]
    eol_count_chanh=df9["PE PIC"].count()+ 12

    #AC Nguyen Si Phu
    df10=df7[df7["PE PIC"]=="Nguyen Si Phu (VN.RYOBI-PIE)"]
    eol_count_phu=df10["PE PIC"].count() + 12

    #AC Nguyen Ngoc Dinh
    df10=df7[df7["PE PIC"]=="Nguyen Ngoc Dinh (VN.RYOBI-PIE)"]
    eol_count_dinh=df10["PE PIC"].count() + 12 


    df_eol={
    "Name":["Chánh","Điền","Định","Phú"],
    "EOL Cases":[eol_count_chanh,eol_count_dien,eol_count_dinh,eol_count_phu]
    }

    bars=axs[1,0].bar(df_eol["Name"],df_eol["EOL Cases"],color='skyblue')
    axs[1,0].tick_params(axis='x', labelsize=8)
    #axs[1,0].bar_label(bars, fontsize=6, padding=3)
    axs[1,0].set_title("ANALYSIS")
    for bar in bars:
        height=bar.get_height()
        xtext=bar.get_x() + bar.get_width()/2
        axs[1,0].text(xtext,height*1.01,f"{height}",ha='center',va='bottom',fontsize=8)
    axs[1,0].set_ylim(0, max(df_eol["EOL Cases"]) + 20 )

    #KAIZEN
    df_kaizen={
    "Name":["Chánh","Điền","Định","Phú"],
    "Kaizen":[1, 2, 0, 0]}
    bars=axs[0,2].bar(df_kaizen["Name"],df_kaizen["Kaizen"],color='red')
    axs[0,2].tick_params(axis='x', labelsize=8)
    for bar in bars:
        height=bar.get_height()
        x=bar.get_x() + bar.get_width()/2
        axs[0,2].text(x,height*1.01,f"{height}",ha='center',va='bottom',fontsize=8)
    axs[0,2].set_title("KAIZEN")
    axs[0,2].set_ylim(0, max(df_kaizen["Kaizen"]) + 1)

    #Main Factor
    factors=df7["5M1D"].unique()
    material=len(df7[df7["5M1D"] =="Material issue"])
    man=len(df7[df7["5M1D"] =="Man issue"])
    machine=len(df7[df7["5M1D"] =="Machine issue"])
    method=len(df7[df7["5M1D"] =="Method issue"])
    measurement=len(df7[df7["5M1D"] =="Measurement issue"])
    df_mainfactors={
    "Name":["Material","Man","Machine","Method","Measurement"],
    "Factors":[material,man,machine,method,measurement]}
    #Main Factor Chart
    bars=axs[1,2].bar(df_mainfactors["Name"],df_mainfactors["Factors"],color='purple')
    for bar in bars:
        height=bar.get_height()
        x=bar.get_x() + bar.get_width()/2
        axs[1,2].text(x,height*1.01,f"{height}",ha='center',va='bottom',fontsize=8)
    axs[1,2].set_title("ISSUE FACTORS")
    axs[1,2].set_ylim(0,max(df_mainfactors["Factors"])+20)
    axs[1,2].tick_params(axis='x', labelsize=5)


    #RANK OF MODEL
    df15=df1[df1["Product"].astype(str).str.startswith(tuple(models))]
    df_top5 = df15.nlargest(5, "Total Man. Hour")
    df_top5["Product"]=df_top5["Product"].astype(str)
    df_top5["Total Man. Hour"] = pd.to_numeric(df_top5["Total Man. Hour"], errors="coerce")
    bars=axs[1,1].bar(df_top5["Product"],df_top5["Total Man. Hour"],color='pink')
    for bar in bars:
        height=bar.get_height()
        x=bar.get_x() + bar.get_width()/2
        axs[1,1].text(x,height*1.01,f"{height}",ha='center',va='bottom',fontsize=8)
    axs[1,1].set_title("TOP 5 LOSS")
    axs[1,1].set_ylim(0,max(df_top5["Total Man. Hour"])+20)
    axs[1,1].tick_params(axis='x', labelsize=6,labelrotation=90)
    
    ## material factors
    # factors=df7["Material Category"].unique()
    # st.write(factors)
    metal=len(df7[df7["Material Category"]=="Metal"])
    plastic=len(df7[df7["Material Category"]=="Plastic"])
    motor=len(df7[df7["Material Category"]=="Motor"])
    packing=len(df7[df7["Material Category"]=="Packing"])
    pcba=len(df7[df7["Material Category"]=="PCBA"])
    switch=len(df7[df7["Material Category"]=="Switch"])
    #st.write(metal,plastic,motor,packing,pcba,switch)
    df_mat_sum={
    "Name":["Metal","Plastic","Motor","Packing","PCBA","Switch"],
    "Value":[metal,plastic,motor,packing,pcba,switch]}
    df_mat_sum = pd.DataFrame(df_mat_sum)
    df_mat_sum=df_mat_sum.nlargest(6,"Value")
    bars=axs[2,2].bar(df_mat_sum["Name"],df_mat_sum["Value"],color='grey')
    for bar in bars:
        height=bar.get_height()
        x=bar.get_x() + bar.get_width()/2
        axs[2,2].text(x,height*1.01,f"{height}",fontsize=8,ha='center',va='bottom')
    axs[2,2].set_title("MATERIAL ISSUE CATEGORIES")
    axs[2,2].set_ylim(0,max(df_mat_sum["Value"])+10)
    axs[2,2].tick_params(axis='x', labelsize=6,labelrotation=90)



    ## TOTAL LINEDOWN RESOLVED
    df1a=df1[df1["Product"].astype(str).str.startswith(tuple(acpk_models))]
    st.dataframe(df1a)
    df1b=df1[df1["Product"].astype(str).str.startswith(tuple(dc_models))]
    st.dataframe(df1b)
    df1c=df1[df1["Product"].astype(str).str.startswith(tuple(eec_models))]
    st.dataframe(df1c)
    plt.tight_layout()
    st.pyplot(fig)













































































































































































































































































































































































































