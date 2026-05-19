import streamlit as st
import math
import pandas as pd
import plotly.graph_objects as go

# --- 1. ตั้งค่าหน้าเพจ ---
st.set_page_config(page_title="Ultimate Footing Design", page_icon="🏢", layout="wide")

st.title("🏢 Ultimate Footing Design (SD Method)")
st.markdown("รองรับการออกแบบ **ฐานรากแผ่ (Shallow)** และ **ฐานรากเสาเข็ม (Pile)** | แสดงผล 3 มิติ")
st.markdown("---")

# --- 2. แถบรับข้อมูล (Sidebar) ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าพารามิเตอร์")
    
    # 🌟 สวิตช์เลือกประเภทฐานราก
    footing_type = st.radio("เลือกประเภทฐานราก:", ["ฐานรากแผ่ (Shallow Footing)", "ฐานรากเสาเข็ม (Pile Footing)"])
    st.markdown("---")
    
    st.subheader("1. น้ำหนักบรรทุก (Service Loads)")
    DL = st.number_input("น้ำหนักบรรทุกคงที่ (DL, ตัน)", value=20.0, step=1.0)
    LL = st.number_input("น้ำหนักบรรทุกจร (LL, ตัน)", value=15.0, step=1.0)
    
    if footing_type == "ฐานรากแผ่ (Shallow Footing)":
        st.subheader("2. ข้อมูลดิน")
        q_all = st.number_input("กำลังรับน้ำหนักปลอดภัยดิน (ตัน/ตร.ม.)", value=15.0, step=1.0)
        Df = st.number_input("ความลึกฐานราก (เมตร)", value=1.5, step=0.1)
    else:
        st.subheader("2. ข้อมูลเสาเข็ม")
        pile_cap = st.number_input("Safe Load เสาเข็ม 1 ต้น (ตัน)", value=25.0, step=1.0)
        pile_size = st.number_input("ขนาดหน้าตัดเสาเข็ม (เมตร)", value=0.30, step=0.05)
    
    st.subheader("3. ขนาดเสาตอม่อ")
    cx = st.number_input("ความกว้างเสา (ซม.)", value=20.0, step=5.0) / 100
    cy = st.number_input("ความยาวเสา (ซม.)", value=20.0, step=5.0) / 100
    
    st.subheader("4. คุณสมบัติวัสดุ")
    fc_prime = st.number_input("กำลังอัดคอนกรีต fc' (ksc)", value=280, step=10)
    fy = st.selectbox("กำลังครากเหล็กเสริม fy (ksc)", [4000, 5000], index=0, format_func=lambda x: f"SD{x//100}")
    bar_dia = st.selectbox("ขนาดเหล็กเสริม (มม.)", [12, 16, 20, 25], index=1)

# --- 3. เครื่องยนต์คำนวณ (Calculation Engine) ---
P_service = DL + LL
P_ultimate = (1.4 * DL) + (1.7 * LL)

# ค่าคงที่สำหรับคอนกรีตและเหล็ก (SD Method)
phi_v = 0.85
phi_b = 0.90
vc_wb_ksc = 0.53 * math.sqrt(fc_prime)
vc_p_ksc = 1.06 * math.sqrt(fc_prime)
ab = (math.pi * (bar_dia / 10) ** 2) / 4
rho_min = 0.0018

# ตัวแปรผลลัพธ์
B = L = d_actual = t = M_u = As_req = As_min = num_bars = spacing = 0
V_u_wb_kg = phi_V_c_wb_kg = V_u_p_kg = phi_V_c_p_kg = 0
status_msg = ""

if footing_type == "ฐานรากแผ่ (Shallow Footing)":
    # ---------------------------------------------
    # ตรรกะการคำนวณ: ฐานรากแผ่ (Shallow Footing)
    # ---------------------------------------------
    gamma_avg = 2.0
    q_net_all = q_all - (gamma_avg * Df)
    
    A_req = P_service / q_net_all
    B_init = math.sqrt(A_req)
    B = math.ceil(B_init * 20) / 20
    if B < 1.0: B = 1.0
    L = B
    
    q_u = P_ultimate / (B * L)
    
    d = 0.15
    while d < 2.0:
        cantilever = (B - max(cx, cy)) / 2
        
        # Wide Beam
        dist_wb = cantilever - d
        V_u_wb = q_u * B * dist_wb if dist_wb > 0 else 0
        V_u_wb_kg = V_u_wb * 1000
        phi_V_c_wb_kg = phi_v * vc_wb_ksc * (B * 100) * (d * 100)
        
        # Punching
        bo = 2 * ((cx + d) + (cy + d))
        A_punch = (B * B) - ((cx + d) * (cy + d))
        V_u_p_kg = (q_u * A_punch) * 1000
        phi_V_c_p_kg = phi_v * vc_p_ksc * (bo * 100) * (d * 100)
        
        if (V_u_wb_kg <= phi_V_c_wb_kg) and (V_u_p_kg <= phi_V_c_p_kg):
            break
        d += 0.01

    t = math.ceil((d + 0.075) * 20) / 20
    d_actual = t - 0.075
    
    M_u = q_u * B * (cantilever ** 2) / 2
    status_msg = f"✅ ประมวลผลเสร็จสิ้น: ฐานรากแผ่ ขนาด {B:.2f}x{L:.2f} ม."

else:
    # ---------------------------------------------
    # ตรรกะการคำนวณ: ฐานรากเสาเข็ม (Pile Footing - 4 Piles)
    # ---------------------------------------------
    req_piles = math.ceil(P_service / pile_cap)
    n_piles = 4 # สำหรับตัวอย่างนี้บังคับออกแบบเป็น 4 เข็มเพื่อความสมมาตร
    
    # ระยะห่างเสาเข็ม (Spacing) = 3 เท่าของขนาดเข็ม
    S = 3 * pile_size
    # ระยะขอบ (Edge distance)
    E = pile_size if pile_size > 0.3 else 0.3 
    
    # ขนาดฐานราก
    B = L = S + (2 * E)
    
    # โหลดประลัยลงเข็มแต่ละต้น
    Pu_pile = P_ultimate / n_piles
    
    # เริ่มหาความหนา d
    d = 0.20
    while d < 2.5:
        # Punching Shear (แรงเฉือนทะลุที่ d/2)
        bo = 2 * ((cx + d) + (cy + d))
        # สำหรับฐานราก 4 เข็ม เข็มมักจะอยู่นอกระยะทะลุ จึงเอาโหลดเข็มทั้งหมดมาคิด
        V_u_p_kg = P_ultimate * 1000 
        phi_V_c_p_kg = phi_v * vc_p_ksc * (bo * 100) * (d * 100)
        
        # Wide Beam Shear (คานกว้างที่ d)
        # เช็คว่าเสาเข็มอยู่นอกระยะ d หรือไม่
        cantilever = (B - max(cx, cy)) / 2
        dist_pile_center = S / 2 # ระยะจากศูนย์กลางเสาถึงศูนย์กลางเข็ม
        if (dist_pile_center - pile_size/2) > (cx/2 + d):
            V_u_wb_kg = (2 * Pu_pile) * 1000 # โหลดจากเข็ม 2 ต้นในฝั่งนั้น
        else:
            V_u_wb_kg = 0 # ถ้าเข็มอยู่ในระยะ d ไม่คิดแรงเฉือน
            
        phi_V_c_wb_kg = phi_v * vc_wb_ksc * (B * 100) * (d * 100)
        
        if (V_u_wb_kg <= phi_V_c_wb_kg) and (V_u_p_kg <= phi_V_c_p_kg):
            break
        d += 0.05 # ปัดขึ้นทีละ 5 ซม. สำหรับฐานรากเข็ม

    t = math.ceil((d + 0.10) * 20) / 20 # ฐานรากเข็มมักใช้ Cover 10 ซม. (อมหัวเข็ม)
    d_actual = t - 0.10
    
    # Moment ที่ขอบเสา
    # โมเมนต์ = แรงจากเข็ม 2 ต้น * ระยะจากศูนย์กลางเข็มถึงขอบเสา
    arm_length = (S / 2) - (cx / 2)
    M_u = (2 * Pu_pile) * arm_length if arm_length > 0 else 0
    
    if req_piles <= 4:
        status_msg = f"✅ ประมวลผลเสร็จสิ้น: ใช้ฐานรากชนิด 4 เสาเข็ม (P_service = {P_service}t, ต้องการเข็ม {req_piles} ต้น)"
    else:
        status_msg = f"⚠️ คำเตือน: น้ำหนักบรรทุก ({P_service}t) เกินกว่าเข็ม 4 ต้นจะรับได้ (ต้องการ {req_piles} ต้น) *โปรแกรมกำลังแสดงผลสำหรับเข็ม 4 ต้น*"

# --- การคำนวณเหล็กเสริม (ใช้ร่วมกัน) ---
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

# --- 4. ส่วนแสดงผล (Main Display) ---
st.success(status_msg)

tab1, tab2 = st.tabs(["🚀 Dashboard", "🎲 3D Model View"])

with tab1:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ขนาดฐานราก", f"{B:.2f} x {L:.2f} ม.")
    col2.metric("ความหนารวม (t)", f"{t*100:.0f} ซม.")
    col3.metric("ปริมาณเหล็ก", f"{num_bars} เส้น")
    col4.metric("น้ำหนักประลัย ($P_u$)", f"{P_ultimate:.1f} ตัน")
    
    st.info(f"**ตะแกรงล่าง (Bottom Mesh):** ใช้เหล็ก **DB{bar_dia} จำนวน {num_bars} เส้น @ {spacing} ซม.** (ทั้งแกน X และ Y)")
    
    st.markdown("### ⚔️ สรุปสถานะแรงเฉือน (kg)")
    df_shear = pd.DataFrame({
        "ประเภทแรงเฉือน": ["Wide Beam Shear (คานกว้าง)", "Punching Shear (ทะลุ)"],
        "แรงที่เกิดขึ้น $V_u$": [f"{V_u_wb_kg:,.0f}", f"{V_u_p_kg:,.0f}"],
        "กำลังต้านทาน $\\phi V_c$": [f"{phi_V_c_wb_kg:,.0f}", f"{phi_V_c_p_kg:,.0f}"]
    })
    st.table(df_shear)

with tab2:
    st.subheader("Interactive 3D Foundation Model")
    fig = go.Figure()
    
    # วาดฐานราก (Footing)
    fig.add_trace(go.Mesh3d(
        x=[-B/2, B/2, B/2, -B/2, -B/2, B/2, B/2, -B/2],
        y=[-L/2, -L/2, L/2, L/2, -L/2, -L/2, L/2, L/2],
        z=[0, 0, 0, 0, t, t, t, t],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='lightblue', opacity=0.8, name='Footing'
    ))
    
    # วาดเสาตอม่อ (Column)
    fig.add_trace(go.Mesh3d(
        x=[-cx/2, cx/2, cx/2, -cx/2, -cx/2, cx/2, cx/2, -cx/2],
        y=[-cy/2, -cy/2, cy/2, cy/2, -cy/2, -cy/2, cy/2, cy/2],
        z=[t, t, t, t, t+1.0, t+1.0, t+1.0, t+1.0],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='orange', opacity=1.0, name='Column'
    ))

    # วาดเสาเข็ม (ถ้ามี)
    if footing_type == "ฐานรากเสาเข็ม (Pile Footing)":
        p_len = 1.0 # ความยาวจำลองของเสาเข็มใน 3D
        p_offset = S/2
        pile_positions = [(-p_offset, -p_offset), (p_offset, -p_offset), (-p_offset, p_offset), (p_offset, p_offset)]
        
        for px, py in pile_positions:
            fig.add_trace(go.Mesh3d(
                x=[px-pile_size/2, px+pile_size/2, px+pile_size/2, px-pile_size/2, px-pile_size/2, px+pile_size/2, px+pile_size/2, px-pile_size/2],
                y=[py-pile_size/2, py-pile_size/2, py+pile_size/2, py+pile_size/2, py-pile_size/2, py-pile_size/2, py+pile_size/2, py+pile_size/2],
                z=[0.1, 0.1, 0.1, 0.1, -p_len, -p_len, -p_len, -p_len], # เสาเข็มอมในฐานราก 0.1m
                i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
                color='gray', opacity=1.0, name='Pile'
            ))

    fig.update_layout(scene=dict(
        xaxis=dict(title='X (m)', range=[-B, B]), yaxis=dict(title='Y (m)', range=[-L, L]), zaxis=dict(title='Z (m)', range=[-1.5, t+1.5]),
        aspectmode='data'
    ), margin=dict(l=0, r=0, b=0, t=0))
    
    st.plotly_chart(fig, use_container_width=True)
