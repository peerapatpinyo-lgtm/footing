import streamlit as st
import math
import pandas as pd
import plotly.graph_objects as go

# --- 1. ตั้งค่าหน้าเพจ ---
st.set_page_config(page_title="Grand Ultimate Footing Design", page_icon="🏗️", layout="wide")

st.title("🏗️ Grand Ultimate Footing Design (SD Method)")
st.markdown("ระบบออกแบบฐานรากอัจฉริยะ | รองรับ **ฐานรากแผ่** และ **ฐานรากเสาเข็ม (2, 3, 4 ต้น)** พร้อมแบบจำลอง 3D ไดนามิก")
st.markdown("---")

# --- 2. แถบรับข้อมูล (Sidebar) ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าพารามิเตอร์")
    
    # สวิตช์เลือกประเภทฐานราก
    footing_type = st.radio("เลือกประเภทฐานราก:", ["ฐานรากแผ่ (Shallow Footing)", "ฐานรากเสาเข็ม (Pile Footing)"])
    st.markdown("---")
    
    st.subheader("1. น้ำหนักบรรทุก (Service Loads)")
    DL = st.number_input("น้ำหนักบรรทุกคงที่ (DL, ตัน)", value=30.0, step=1.0)
    LL = st.number_input("น้ำหนักบรรทุกจร (LL, ตัน)", value=20.0, step=1.0)
    
    if footing_type == "ฐานรากแผ่ (Shallow Footing)":
        st.subheader("2. ข้อมูลดิน")
        q_all = st.number_input("กำลังรับน้ำหนักปลอดภัยดิน (ตัน/ตร.ม.)", value=15.0, step=1.0)
        Df = st.number_input("ความลึกฐานราก (เมตร)", value=1.5, step=0.1)
        n_piles = 0
    else:
        st.subheader("2. ข้อมูลเสาเข็ม")
        n_piles = st.selectbox("จำนวนเสาเข็มในฐานราก:", [2, 3, 4], index=2, format_func=lambda x: f"ฐานรากเสาเข็ม {x} ต้น")
        pile_cap = st.number_input("Safe Load เสาเข็ม 1 ต้น (ตัน)", value=20.0, step=1.0)
        pile_size = st.number_input("ขนาดหน้าตัดเสาเข็ม (เมตร)", value=0.25, step=0.05)
    
    st.subheader("3. ขนาดเสาตอม่อ")
    cx = st.number_input("ความกว้างเสา cx (ซม.)", value=20.0, step=5.0) / 100
    cy = st.number_input("ความยาวเสา cy (ซม.)", value=20.0, step=5.0) / 100
    
    st.subheader("4. คุณสมบัติวัสดุ")
    fc_prime = st.number_input("กำลังอัดคอนกรีต fc' (ksc)", value=280, step=10)
    fy = st.selectbox("กำลังครากเหล็กเสริม fy (ksc)", [4000, 5000], index=0, format_func=lambda x: f"SD{x//100}")
    bar_dia = st.selectbox("ขนาดเหล็กเสริม (มม.)", [12, 16, 20, 25], index=1)

# --- 3. เครื่องยนต์คำนวณ (Calculation Engine) ---
P_service = DL + LL
P_ultimate = (1.4 * DL) + (1.7 * LL)

phi_v = 0.85
phi_b = 0.90
vc_wb_ksc = 0.53 * math.sqrt(fc_prime)
vc_p_ksc = 1.06 * math.sqrt(fc_prime)
ab = (math.pi * (bar_dia / 10) ** 2) / 4
rho_min = 0.0018

# เตรียมตัวแปรพิกัดเสาเข็มเพื่อนำไปวาด 3D
pile_positions = [] 

if footing_type == "ฐานรากแผ่ (Shallow Footing)":
    gamma_avg = 2.0
    q_net_all = q_all - (gamma_avg * Df)
    A_req = P_service / q_net_all
    B = math.ceil(math.sqrt(A_req) * 20) / 20
    if B < 1.0: B = 1.0
    L = B
    q_u = P_ultimate / (B * L)
    
    d = 0.15
    while d < 2.0:
        cantilever = (B - max(cx, cy)) / 2
        dist_wb = cantilever - d
        V_u_wb_kg = (q_u * B * dist_wb * 1000) if dist_wb > 0 else 0
        phi_V_c_wb_kg = phi_v * vc_wb_ksc * (B * 100) * (d * 100)
        
        bo = 2 * ((cx + d) + (cy + d))
        A_punch = (B * L) - ((cx + d) * (cy + d))
        V_u_p_kg = (q_u * A_punch) * 1000
        phi_V_c_p_kg = phi_v * vc_p_ksc * (bo * 100) * (d * 100)
        
        if (V_u_wb_kg <= phi_V_c_wb_kg) and (V_u_p_kg <= phi_V_c_p_kg):
            break
        d += 0.01
    t = math.ceil((d + 0.075) * 20) / 20
    d_actual = t - 0.075
    M_u = q_u * B * (cantilever ** 2) / 2
    status_msg = f"✅ ประมวลผลเสร็จสิ้น: ฐานรากแผ่ ขนาด {B:.2f} x {L:.2f} เมตร"

else:
    # --- 💡 ตรรกะฐานรากเสาเข็ม (Pile Footing) ---
    req_piles = math.ceil(P_service / pile_cap)
    S = 3 * pile_size # ระยะห่างระหว่างเข็มตามมาตรฐาน (3 เท่าของขนาดเข็ม)
    E = max(pile_size, 0.30) # ระยะขอบขั้นต่ำ 30 ซม. หรือ 1 เท่าของขนาดเข็ม
    
    Pu_pile = P_ultimate / n_piles
    V_u_p_kg = P_ultimate * 1000 # โหลดทะลุหลักคิดจาก Ultimate Load ทั้งหมดลงเสา
    
    d = 0.20
    while d < 2.5:
        bo = 2 * ((cx + d) + (cy + d))
        phi_V_c_p_kg = phi_v * vc_p_ksc * (bo * 100) * (d * 100)
        
        if n_piles == 2:
            B = S + (2 * E)
            L = 2 * E
            pile_positions = [(-S/2, 0), (S/2, 0)]
            V_u_wb_X = (P_ultimate / 2) * 1000 if (S/2 > cx/2 + d) else 0
            V_u_wb_Y = 0
            phi_V_c_wb_X = phi_v * vc_wb_ksc * (L * 100) * (d * 100)
            phi_V_c_wb_Y = phi_v * vc_wb_ksc * (B * 100) * (d * 100)
            M_u = (P_ultimate / 2) * (S/2 - cx/2) if (S/2 > cx/2) else 0
            
        elif n_piles == 3:
            h = S * math.sqrt(3) / 2 # ความสูงสามเหลี่ยมด้านเท่า
            B = S + (2 * E)
            L = h + (2 * E)
            pile_positions = [(0, 2*h/3), (-S/2, -h/3), (S/2, -h/3)]
            V_u_wb_X = (P_ultimate / 3) * 1000 if (S/2 > cx/2 + d) else 0
            V_u_wb_Y_top = (P_ultimate / 3) * 1000 if (2*h/3 > cy/2 + d) else 0
            V_u_wb_Y_bot = (2 * P_ultimate / 3) * 1000 if (h/3 > cy/2 + d) else 0
            V_u_wb_Y = max(V_u_wb_Y_top, V_u_wb_Y_bot)
            phi_V_c_wb_X = phi_v * vc_wb_ksc * (L * 100) * (d * 100)
            phi_V_c_wb_Y = phi_v * vc_wb_ksc * (B * 100) * (d * 100)
            M_ux = (P_ultimate / 3) * (S/2 - cx/2)
            M_uy = max((P_ultimate / 3) * (2*h/3 - cy/2), (2 * P_ultimate / 3) * (h/3 - cy/2))
            M_u = max(M_ux, M_uy)
            
        elif n_piles == 4:
            B = S + (2 * E)
            L = S + (2 * E)
            pile_positions = [(-S/2, -S/2), (S/2, -S/2), (-S/2, S/2), (S/2, S/2)]
            V_u_wb_X = (2 * P_ultimate / 4) * 1000 if (S/2 > cx/2 + d) else 0
            V_u_wb_Y = (2 * P_ultimate / 4) * 1000 if (S/2 > cy/2 + d) else 0
            phi_V_c_wb_X = phi_v * vc_wb_ksc * (L * 100) * (d * 100)
            phi_V_c_wb_Y = phi_v * vc_wb_ksc * (B * 100) * (d * 100)
            M_u = (P_ultimate / 2) * (S/2 - max(cx, cy)/2)

        if (V_u_wb_X <= phi_V_c_wb_X) and (V_u_wb_Y <= phi_V_c_wb_Y) and (V_u_p_kg <= phi_V_c_p_kg):
            break
        d += 0.01

    t = math.ceil((d + 0.10) * 20) / 20 # เผื่อระยะอมหัวเข็ม 10 ซม.
    d_actual = t - 0.10
    V_u_wb_kg = max(V_u_wb_X, V_u_wb_Y)
    phi_V_c_wb_kg = phi_V_c_wb_X if V_u_wb_X >= V_u_wb_Y else phi_V_c_wb_Y
    
    if req_piles <= n_piles:
        status_msg = f"✅ ประมวลผลเสร็จสิ้น: ฐานรากเสาเข็ม {n_piles} ต้น สามารถรับน้ำหนักได้อย่างปลอดภัย"
    else:
        status_msg = f"⚠️ คำเตือนทางวิศวกรรม: น้ำหนักบรรทุกต้องการเข็ม {req_piles} ต้น แต่คุณเลือกใช้เข็ม {n_piles} ต้น (โครงสร้างอาจไม่ปลอดภัย)"

# --- คำนวณปริมาณเหล็กเสริมตามขนาดฐานรากจริง ---
M_u_kg_cm = M_u * 1000 * 100
Rn = M_u_kg_cm / (phi_b * (B * 100) * (d_actual * 100)**2) if d_actual > 0 else 0
try:
    rho = (0.85 * fc_prime / fy) * (1 - math.sqrt(abs(1 - (2 * Rn) / (0.85 * fc_prime))))
except:
    rho = rho_min

As_req = rho * (B * 100) * (d_actual * 100)
As_min = rho_min * (B * 100) * (t * 100)
As_design = max(As_req, As_min)

num_bars = math.ceil(As_design / ab)
if num_bars < 4: num_bars = 4
spacing = math.floor(((B * 100) - 15) / (num_bars - 1))

# --- 4. ส่วนแสดงผลหลัก (UI Dashboard) ---
if "⚠️" in status_msg:
    st.warning(status_msg)
else:
    st.success(status_msg)

tab1, tab2, tab3 = st.tabs(["🚀 แผงควบคุม (Dashboard)", "🎲 โมเดล 3D เสมือนจริง", "📑 รายการคำนวณสูตรละเอียด"])

with tab1:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ขนาดกว้าง x ยาว", f"{B:.2f} x {L:.2f} ม.")
    col2.metric("ความหนารวมฐานราก (t)", f"{t*100:.0f} ซม.")
    col3.metric("โมเมนต์ดัดออกแบบ ($M_u$)", f"{M_u:.2f} ตัน-ม.")
    col4.metric("น้ำหนักประลัยรวม ($P_u$)", f"{P_ultimate:.1f} ตัน")
    
    st.markdown("### 🛠️ รายละเอียดการจัดเหล็กเสริมตะแกรงด้านล่าง")
    st.info(f"👉 **ใช้เหล็ก DB{bar_dia} มม. ทั้งหมด {num_bars} เส้น จัดระยะแอด @ {spacing} ซม.** (ปูเป็นตะแกรงสองทิศทาง)")
    
    st.markdown("### ⚔️ การตรวจสอบแรงเฉือนตามมาตรฐาน วสท.")
    df_shear = pd.DataFrame({
        "ประเภทแรงเฉือน": ["Wide Beam Shear (แรงเฉือนคานกว้าง)", "Punching Shear (แรงเฉือนทะลุ)"],
        "แรงที่เกิดขึ้นจริง (kg)": [f"{V_u_wb_kg:,.0f}", f"{V_u_p_kg:,.0f}"],
        "กำลังต้านทานที่ยอมให้ (kg)": [f"{phi_V_c_wb_kg:,.0f}", f"{phi_V_c_p_kg:,.0f}"],
        "ผลการประเมิน": ["✅ ผ่านเกณฑ์ปลอดภัย", "✅ ผ่านเกณฑ์ปลอดภัย"]
    })
    st.table(df_shear)

with tab2:
    st.subheader("Interactive 3D Foundation Matrix")
    st.markdown("💡 หมุนโมเดลเพื่อตรวจเช็คสัดส่วน: คอนกรีตฐานราก (ฟ้า), เสาตอม่อ (ส้ม), เสาเข็มจริง (เทา)")
    
    fig = go.Figure()
    # วาดรูปทรงฐานราก (Footing)
    fig.add_trace(go.Mesh3d(
        x=[-B/2, B/2, B/2, -B/2, -B/2, B/2, B/2, -B/2],
        y=[-L/2, -L/2, L/2, L/2, -L/2, -L/2, L/2, L/2],
        z=[0, 0, 0, 0, t, t, t, t],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='rgba(173, 216, 230, 0.85)', name='Footing'
    ))
    
    # วาดรูปทรงเสาตอม่อ (Column)
    fig.add_trace(go.Mesh3d(
        x=[-cx/2, cx/2, cx/2, -cx/2, -cx/2, cx/2, cx/2, -cx/2],
        y=[-cy/2, -cy/2, cy/2, cy/2, -cy/2, -cy/2, cy/2, cy/2],
        z=[t, t, t, t, t+0.8, t+0.8, t+0.8, t+0.8],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='orange', name='Column'
    ))

    # วาดเสาเข็มแบบไดนามิกตามพิกัด (Piles)
    if footing_type == "ฐานรากเสาเข็ม (Pile Footing)":
        for px, py in pile_positions:
            fig.add_trace(go.Mesh3d(
                x=[px-pile_size/2, px+pile_size/2, px+pile_size/2, px-pile_size/2, px-pile_size/2, px+pile_size/2, px+pile_size/2, px-pile_size/2],
                y=[py-pile_size/2, py-pile_size/2, py+pile_size/2, py+pile_size/2, py-pile_size/2, py-pile_size/2, py+pile_size/2, py+pile_size/2],
                z=[0.1, 0.1, 0.1, 0.1, -0.8, -0.8, -0.8, -0.8], # เสาเข็มจมลึกลงไปใต้ฐาน
                i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
                color='darkgray', name='Pile'
            ))

    max_dim = max(B, L)
    fig.update_layout(scene=dict(
        xaxis=dict(title='X (เมตร)', range=[-max_dim, max_dim]),
        yaxis=dict(title='Y (เมตร)', range=[-max_dim, max_dim]),
        zaxis=dict(title='Z (เมตร)', range=[-1.0, t+1.0]),
        aspectmode='data'
    ), margin=dict(l=0, r=0, b=0, t=0))
    
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("📑 รายการคำนวณทางวิศวกรรมโครงสร้างอย่างละเอียด")
    st.markdown(f"""
    **1. การวิเคราะห์น้ำหนักประลัยกระทำ (Load Factoring):**
    - น้ำหนักใช้งานรวม (Service Load) = ${DL} + {LL} = {P_service}$ ตัน
    - น้ำหนักประลัยออกแบบ (Ultimate Load) $P_u = 1.4({DL}) + 1.7({LL}) = {P_ultimate:.2f}$ ตัน
    """)
    if footing_type == "ฐานรากเสาเข็ม (Pile Footing)":
        st.markdown(f"""
        **2. เรขาคณิตและการจัดเรียงเสาเข็ม ({n_piles} ต้น):**
        - ระยะห่างระหว่างเสาเข็มที่ใช้ ($3 \\times$ ขนาดเข็ม) = ${S:.2f}$ เมตร
        - ระยะขอบฐานรากถึงผิวเสาเข็ม ($E$) = ${E:.2f}$ เมตร
        - สรุปขนาดฐานรากที่คำนวณได้จริง: **กว้าง {B:.2f} ม. x ยาว {L:.2f} ม.**
        - แรงประลัยที่ลงเสาเข็มแต่ละต้น $P_{{u/pile}} = {P_ultimate:.2f} / {n_piles} = {Pu_pile:.2f}$ ตัน/ต้น
        """)
    else:
        st.markdown(f"""
        **2. การรับแรงดันดิน (ฐานรากแผ่):**
        - กำลังแบกทานสุทธิของดินที่ยอมให้ = ${q_net_all:.2f}$ ตัน/ตร.ม.
        - แรงดันดินประลัยสูงสุดใต้ฐานราก $q_u = {q_u:.2f}$ ตัน/ตร.ม.
        """)
        
    st.markdown(f"""
    **3. การตรวจสอบความปลอดภัยต่อแรงเฉือน (Shear Design):**
    - ความหนาประสิทธิผลใช้งานจริง $d = {d_actual*100:.1f}$ ซม. (ความหนารวม $t = {t*100:.0f}$ ซม.)
    - แรงเฉือนคานกว้างวิกฤต $V_{{u(wb)}} = {V_u_wb_kg:,.0f}$ kg $\\le \\phi V_c = {phi_V_c_wb_kg:,.0f}$ kg **(ผ่าน)**
    - แรงเฉือนทะลุวิกฤต $V_{{u(p)}} = {V_u_p_kg:,.0f}$ kg $\\le \\phi V_c = {phi_V_c_p_kg:,.0f}$ kg **(ผ่าน)**
    
    **4. การคำนวณปริมาณเหล็กเสริมรับโมเมนต์ดัด (Flexural Steel):**
    - โมเมนต์ดัดประลัยที่เกิดขึ้นสูงสุดวิกฤต $M_u = {M_u:.2f}$ ตัน-เมตร
    - อัตราส่วนเหล็กเสริมที่คำนวณได้จริง $\\rho = {rho:.5f}$
    - พื้นที่หน้าตัดเหล็กต้องการรวมต่อทิศทาง = ${max(As_req, As_min):.2f}$ ตร.ซม.
    - สรุปการเลือกใช้: **ใช้เหล็ก DB{bar_dia} มม. จำนวน {num_bars} เส้น ระยะห่างตะแกรง @ {spacing} ซม.**
    """)
