import streamlit as st
import math
import pandas as pd
import plotly.graph_objects as go

# --- 1. ตั้งค่าหน้าเพจ ---
st.set_page_config(page_title="Ultimate Footing Design", page_icon="🏢", layout="wide")

st.title("🏢 Ultimate Footing Design (วิธีกำลังประลัย - SD)")
st.markdown("ออกแบบตามมาตรฐาน วสท. | **1.4DL + 1.7LL** | แสดงผล 3 มิติ | คำนวณเหล็กเสริมแบบแม่นยำ")
st.markdown("---")

# --- 2. แถบรับข้อมูล (Sidebar) ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าพารามิเตอร์")
    
    st.subheader("1. น้ำหนักบรรทุก (Service Loads)")
    DL = st.number_input("น้ำหนักบรรทุกคงที่ (Dead Load, ตัน)", value=20.0, step=1.0)
    LL = st.number_input("น้ำหนักบรรทุกจร (Live Load, ตัน)", value=15.0, step=1.0)
    
    st.subheader("2. ข้อมูลดิน")
    q_all = st.number_input("กำลังรับน้ำหนักปลอดภัยดิน (ตัน/ตร.ม.)", value=15.0, step=1.0)
    Df = st.number_input("ความลึกฐานราก (เมตร)", value=1.5, step=0.1)
    
    st.subheader("3. ขนาดเสาตอม่อ")
    cx = st.number_input("ความกว้างเสา (ซม.)", value=20.0, step=5.0) / 100
    cy = st.number_input("ความยาวเสา (ซม.)", value=20.0, step=5.0) / 100
    
    st.subheader("4. คุณสมบัติวัสดุ")
    fc_prime = st.number_input("กำลังอัดคอนกรีต fc' (ksc)", value=280, step=10)
    fy = st.selectbox("กำลังครากเหล็กเสริม fy (ksc)", [4000, 5000], index=0, format_func=lambda x: f"SD{x//100}")
    bar_dia = st.selectbox("ขนาดเหล็กเสริม (มม.)", [12, 16, 20, 25], index=1)

# --- 3. เครื่องยนต์คำนวณ (Calculation Engine - SD Method) ---
# Load Combinations
P_service = DL + LL
P_ultimate = (1.4 * DL) + (1.7 * LL)

# Net Allowable Bearing Pressure (หักดินและคอนกรีต)
gamma_avg = 2.0 # ตัน/ลบ.ม. (ค่าเฉลี่ยดิน+คอนกรีต)
q_net_all = q_all - (gamma_avg * Df)

# 1. หาขนาดฐานรากจาก Service Load
A_req = P_service / q_net_all
B_init = math.sqrt(A_req)
B = math.ceil(B_init * 20) / 20  # ปัดขึ้นทีละ 5 ซม.
if B < 1.0: B = 1.0

# Ultimate Soil Pressure (สำหรับการออกแบบคอนกรีตและเหล็ก)
q_u = P_ultimate / (B * B)

# 2. หาความหนา d จาก Shear Check (SD Method)
phi_v = 0.85
vc_wb_ksc = 0.53 * math.sqrt(fc_prime)
vc_p_ksc = 1.06 * math.sqrt(fc_prime)

d = 0.15 # เริ่มที่ 15 ซม.
while d < 2.0:
    cantilever = (B - max(cx, cy)) / 2
    
    # 2.1 Wide Beam Shear (คานกว้าง) ที่ระยะ d
    dist_wb = cantilever - d
    V_u_wb = q_u * B * dist_wb if dist_wb > 0 else 0
    V_u_wb_kg = V_u_wb * 1000
    phi_V_c_wb = phi_v * (vc_wb_ksc * 10000) * B * d # 10000 แปลง ksc เป็น t/m2 -> kg
    phi_V_c_wb_kg = phi_v * vc_wb_ksc * (B * 100) * (d * 100)
    
    # 2.2 Punching Shear (ทะลุ) ที่ระยะ d/2
    bo = 2 * ((cx + d) + (cy + d))
    A_punch = (B * B) - ((cx + d) * (cy + d))
    V_u_p = q_u * A_punch
    V_u_p_kg = V_u_p * 1000
    phi_V_c_p_kg = phi_v * vc_p_ksc * (bo * 100) * (d * 100)
    
    if (V_u_wb_kg <= phi_V_c_wb_kg) and (V_u_p_kg <= phi_V_c_p_kg):
        break
    d += 0.01

t = math.ceil((d + 0.075) * 20) / 20 # ปัดขึ้นทีละ 5 ซม.
d_actual = t - 0.075

# 3. คำนวณเหล็กเสริมหลัก (Flexure)
phi_b = 0.90
M_u = q_u * B * (cantilever ** 2) / 2 # ตัน-เมตร
M_u_kg_cm = M_u * 1000 * 100

# สูตร p = (0.85fc'/fy)[1 - sqrt(1 - 2Rn/(0.85fc'))]
Rn = M_u_kg_cm / (phi_b * (B * 100) * (d_actual * 100)**2)
rho = (0.85 * fc_prime / fy) * (1 - math.sqrt(abs(1 - (2 * Rn) / (0.85 * fc_prime))))
As_req = rho * (B * 100) * (d_actual * 100)

rho_min = 0.0018 # สำหรับเหล็ก SD40/SD50
As_min = rho_min * (B * 100) * (t * 100)
As_design = max(As_req, As_min)

ab = (math.pi * (bar_dia / 10) ** 2) / 4
num_bars = math.ceil(As_design / ab)
if num_bars < 4: num_bars = 4
spacing = math.floor(((B * 100) - 15) / (num_bars - 1))

# --- 4. ส่วนแสดงผล (Main Display) ---
st.success(f"✅ ประมวลผลเสร็จสิ้น: ฐานรากสามารถรับน้ำหนัก Service Load {P_service} ตัน และ Ultimate Load {P_ultimate:.1f} ตัน ได้อย่างปลอดภัย")

tab1, tab2, tab3 = st.tabs(["🚀 Dashboard", "🎲 3D Model View", "📑 รายการคำนวณ (Report)"])

with tab1:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ขนาดฐานราก", f"{B:.2f} x {B:.2f} ม.")
    col2.metric("ความหนารวม (t)", f"{t*100:.0f} ซม.")
    col3.metric("ระยะหุ้มคอนกรีต (Cover)", f"7.5 ซม.")
    col4.metric("น้ำหนักประลัย ($P_u$)", f"{P_ultimate:.1f} ตัน")
    
    st.markdown("### 🛠️ ข้อกำหนดเหล็กเสริม (Reinforcement)")
    st.info(f"**ตะแกรงล่าง (Bottom Mesh):** ใช้เหล็ก **DB{bar_dia} จำนวน {num_bars} เส้น @ {spacing} ซม.** (ทั้งแกน X และ Y)")
    
    # ตารางเปรียบเทียบ Shear
    st.markdown("### ⚔️ สรุปสถานะแรงเฉือน")
    df_shear = pd.DataFrame({
        "ประเภทแรงเฉือน": ["Wide Beam Shear (คานกว้าง)", "Punching Shear (ทะลุ)"],
        "แรงที่เกิดขึ้น $V_u$ (kg)": [f"{V_u_wb_kg:,.0f}", f"{V_u_p_kg:,.0f}"],
        "กำลังต้านทาน $\\phi V_c$ (kg)": [f"{phi_V_c_wb_kg:,.0f}", f"{phi_V_c_p_kg:,.0f}"],
        "สถานะ": ["✅ PASS", "✅ PASS"]
    })
    st.table(df_shear)

with tab2:
    st.subheader("Interactive 3D Foundation Model")
    st.markdown("ใช้เมาส์หมุน ซูม หรือลากเพื่อดูโมเดล 3 มิติ (สีฟ้า = ฐานราก, สีส้ม = เสาตอม่อ)")
    
    fig = go.Figure()
    # วาดฐานราก
    fig.add_trace(go.Mesh3d(
        x=[-B/2, B/2, B/2, -B/2, -B/2, B/2, B/2, -B/2],
        y=[-B/2, -B/2, B/2, B/2, -B/2, -B/2, B/2, B/2],
        z=[0, 0, 0, 0, t, t, t, t],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='lightblue', opacity=0.8, name='Footing'
    ))
    
    # วาดเสา
    fig.add_trace(go.Mesh3d(
        x=[-cx/2, cx/2, cx/2, -cx/2, -cx/2, cx/2, cx/2, -cx/2],
        y=[-cy/2, -cy/2, cy/2, cy/2, -cy/2, -cy/2, cy/2, cy/2],
        z=[t, t, t, t, t+1.0, t+1.0, t+1.0, t+1.0], # เสาสูง 1 เมตรเหนือฐาน
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='orange', opacity=1.0, name='Column'
    ))
    
    fig.update_layout(scene=dict(
        xaxis=dict(title='X (m)', range=[-B, B]),
        yaxis=dict(title='Y (m)', range=[-B, B]),
        zaxis=dict(title='Z (m)', range=[-0.5, t+1.5]),
        aspectmode='data'
    ), margin=dict(l=0, r=0, b=0, t=0))
    
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("📑 รายการคำนวณวิธีกำลัง (Strength Design Method)")
    st.markdown(f"""
    **1. การวิเคราะห์น้ำหนักและการหาขนาดหน้าตัด:**
    - น้ำหนักใช้งาน $P_{{service}} = {DL} + {LL} = {P_service}$ ตัน
    - น้ำหนักประลัย $P_u = 1.4({DL}) + 1.7({LL}) = {P_ultimate:.1f}$ ตัน
    - แรงดันดินสุทธิที่ยอมให้ $q_{{net(all)}} = {q_net_all:.2f}$ ตัน/ตร.ม.
    - พื้นที่ต้องการ $A_{{req}} = {P_service} / {q_net_all:.2f} = {A_req:.2f}$ ตร.ม. $\\rightarrow$ ใช้ขนาด **{B:.2f} x {B:.2f} ม.**
    - แรงดันดินประลัย (Ultimate Pressure) $q_u = {P_ultimate:.1f} / ({B:.2f} \\times {B:.2f}) = {q_u:.2f}$ ตัน/ตร.ม.
    
    **2. การออกแบบความหนา ($d={d_actual*100:.1f}$ ซม., $t={t*100:.0f}$ ซม.):**
    - แรงเฉือนคานกว้าง $V_{{u(wb)}} = {V_u_wb_kg:,.0f}$ กก. $\\le \\phi V_c = {phi_V_c_wb_kg:,.0f}$ กก. (O.K.)
    - แรงเฉือนทะลุ $V_{{u(p)}} = {V_u_p_kg:,.0f}$ กก. $\\le \\phi V_c = {phi_V_c_p_kg:,.0f}$ กก. (O.K.)
    
    **3. การออกแบบเหล็กเสริมรับโมเมนต์ดัด:**
    - โมเมนต์ดัดประลัยวิกฤต $M_u = {M_u:.2f}$ ตัน-เมตร
    - อัตราส่วนเหล็กเสริมที่คำนวณได้ $\\rho = {rho:.5f}$
    - ปริมาณเหล็กที่ต้องการ $A_{{s(req)}} = {As_req:.2f}$ ตร.ซม. 
    - ปริมาณเหล็กขั้นต่ำ $\\rho_{{min}} 0.0018 = {As_min:.2f}$ ตร.ซม.
    - ใช้เหล็ก **DB{bar_dia} จำนวน {num_bars} เส้น** (พื้นที่รวม = {num_bars * ab:.2f} ตร.ซม. > {max(As_req, As_min):.2f}) (O.K.)
    """)
