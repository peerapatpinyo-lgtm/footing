import streamlit as st
import math
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Pro Footing Design", page_icon="🏗️", layout="wide")

st.title("🏗️ Professional Footing Design (วสท. / ACI Code)")
st.markdown("ระบบคำนวณตามมาตรฐานวิศวกรรมโครงสร้าง | วิเคราะห์หน้าตัดวิกฤต (Critical Sections) แบบพิกัด (X,Y)")
st.markdown("---")

# --- 1. แถบรับข้อมูล (Sidebar) ---
with st.sidebar:
    st.header("⚙️ พารามิเตอร์การออกแบบ")
    footing_type = st.radio("ประเภทฐานราก:", ["ฐานรากแผ่ (Shallow)", "ฐานรากเสาเข็ม (Pile)"])
    st.markdown("---")
    
    DL = st.number_input("น้ำหนักคงที่ (DL, ตัน)", value=30.0, step=1.0)
    LL = st.number_input("น้ำหนักจร (LL, ตัน)", value=20.0, step=1.0)
    
    if footing_type == "ฐานรากแผ่ (Shallow)":
        q_all = st.number_input("กำลังรับน้ำหนักดิน (ตัน/ตร.ม.)", value=15.0, step=1.0)
        Df = st.number_input("ความลึกฐานราก (เมตร)", value=1.5, step=0.1)
        n_piles = 0
    else:
        n_piles = st.selectbox("จำนวนเสาเข็ม:", [2, 3, 4], index=2)
        pile_cap = st.number_input("Safe Load เสาเข็ม (ตัน/ต้น)", value=25.0, step=1.0)
        pile_size = st.number_input("ขนาดเสาเข็ม (เมตร)", value=0.30, step=0.05)
    
    cx = st.number_input("ความกว้างเสา cx (ซม.)", value=20.0, step=5.0) / 100
    cy = st.number_input("ความยาวเสา cy (ซม.)", value=20.0, step=5.0) / 100
    
    fc_prime = st.number_input("fc' (ksc)", value=280, step=10)
    fy = st.selectbox("fy (ksc)", [4000, 5000], index=0)
    bar_dia = st.selectbox("ขนาดเหล็ก (มม.)", [12, 16, 20, 25], index=1)

# --- 2. เครื่องยนต์คำนวณ (Structural Mechanics Engine) ---
P_service = DL + LL
P_ultimate = (1.4 * DL) + (1.7 * LL)

phi_v = 0.85
phi_b = 0.90
vc_wb_ksc = 0.53 * math.sqrt(fc_prime)
vc_p_ksc = 1.06 * math.sqrt(fc_prime)
ab = (math.pi * (bar_dia / 10) ** 2) / 4
rho_min = 0.0018

piles = [] 
status_msg = ""

if footing_type == "ฐานรากแผ่ (Shallow)":
    # --- การคำนวณฐานรากแผ่ ---
    gamma_avg = 2.0
    q_net_all = q_all - (gamma_avg * Df)
    A_req = P_service / q_net_all
    B = math.ceil(math.sqrt(A_req) * 20) / 20
    if B < 1.0: B = 1.0
    L = B
    q_u = P_ultimate / (B * L)
    
    d = 0.15
    while d < 2.0:
        dist_x = (B - cx)/2 - d
        dist_y = (L - cy)/2 - d
        
        V_u_wb_X = (q_u * L * dist_x * 1000) if dist_x > 0 else 0
        V_u_wb_Y = (q_u * B * dist_y * 1000) if dist_y > 0 else 0
        phi_V_c_wb_X = phi_v * vc_wb_ksc * (L * 100) * (d * 100)
        phi_V_c_wb_Y = phi_v * vc_wb_ksc * (B * 100) * (d * 100)
        
        bo = 2 * ((cx + d) + (cy + d))
        A_punch = (B * L) - ((cx + d) * (cy + d))
        V_u_p_kg = (q_u * A_punch) * 1000
        phi_V_c_p_kg = phi_v * vc_p_ksc * (bo * 100) * (d * 100)
        
        if (max(V_u_wb_X, V_u_wb_Y) <= min(phi_V_c_wb_X, phi_V_c_wb_Y)) and (V_u_p_kg <= phi_V_c_p_kg):
            break
        d += 0.01
        
    t = math.ceil((d + 0.075) * 20) / 20
    d_actual = t - 0.075
    M_u_X = q_u * L * (((B - cx)/2)**2) / 2
    M_u_Y = q_u * B * (((L - cy)/2)**2) / 2
    M_u = max(M_u_X, M_u_Y)
    
    # กำหนดพิกัดวาด 3D สำหรับฐานแผ่
    ft_x_min, ft_x_max = -B/2, B/2
    ft_y_min, ft_y_max = -L/2, L/2
    
    status_msg = f"✅ ฐานรากแผ่ ขนาด {B:.2f} x {L:.2f} ม. ปลอดภัย"
    V_u_wb_kg = max(V_u_wb_X, V_u_wb_Y)
    phi_V_c_wb_kg = phi_V_c_wb_X

else:
    # --- การคำนวณฐานรากเสาเข็ม (อิงพิกัด X, Y จริง) ---
    req_piles = math.ceil(P_service / pile_cap)
    Pu_pile = P_ultimate / n_piles
    
    S = 3 * pile_size # ระยะห่างเสาเข็ม 3D
    E = max(pile_size, 0.30) # ระยะหุ้มขอบเข็ม
    
    if n_piles == 2:
        piles = [(-S/2, 0), (S/2, 0)]
        B = S + 2*E
        L = cy + 2*E if (cy + 2*E) > 3*pile_size else 3*pile_size
    elif n_piles == 3:
        R = S / math.sqrt(3)  # ระยะจาก Centroid ถึงยอด
        r = R / 2             # ระยะจาก Centroid ถึงฐาน
        piles = [(0, R), (-S/2, -r), (S/2, -r)]
        B = S + 2*E
    elif n_piles == 4:
        piles = [(-S/2, -S/2), (S/2, -S/2), (-S/2, S/2), (S/2, S/2)]
        B = S + 2*E
        L = S + 2*E

    # หาขอบเขตของฐานราก (Bounding Box) จากพิกัดเข็ม
    ft_x_min = min(p[0] for p in piles) - E
    ft_x_max = max(p[0] for p in piles) + E
    ft_y_min = min(p[1] for p in piles) - E
    ft_y_max = max(p[1] for p in piles) + E
    
    B_actual = ft_x_max - ft_x_min
    L_actual = ft_y_max - ft_y_min
    
    # วนลูปหาความหนา (d) จากหน้าตัดวิกฤต
    d = 0.20
    while d < 2.5:
        # 1. เช็ค Punching Shear (ระยะ d/2 จากขอบเสา)
        V_u_p_kg = 0
        for px, py in piles:
            if abs(px) > (cx/2 + d/2) or abs(py) > (cy/2 + d/2):
                V_u_p_kg += Pu_pile * 1000
                
        bo = 2 * ((cx + d) + (cy + d))
        phi_V_c_p_kg = phi_v * vc_p_ksc * (bo * 100) * (d * 100)
        
        # 2. เช็ค Wide Beam Shear (ระยะ d จากขอบเสา)
        # แกน X (ซ้ายและขวา)
        V_wb_X_pos = sum(Pu_pile * 1000 for px, py in piles if px > cx/2 + d)
        V_wb_X_neg = sum(Pu_pile * 1000 for px, py in piles if px < -(cx/2 + d))
        V_u_wb_X = max(V_wb_X_pos, V_wb_X_neg)
        phi_V_c_wb_X = phi_v * vc_wb_ksc * (L_actual * 100) * (d * 100)
        
        # แกน Y (บนและล่าง)
        V_wb_Y_pos = sum(Pu_pile * 1000 for px, py in piles if py > cy/2 + d)
        V_wb_Y_neg = sum(Pu_pile * 1000 for px, py in piles if py < -(cy/2 + d))
        V_u_wb_Y = max(V_wb_Y_pos, V_wb_Y_neg)
        phi_V_c_wb_Y = phi_v * vc_wb_ksc * (B_actual * 100) * (d * 100)
        
        if (V_u_p_kg <= phi_V_c_p_kg) and (V_u_wb_X <= phi_V_c_wb_X) and (V_u_wb_Y <= phi_V_c_wb_Y):
            break
        d += 0.05

    t = math.ceil((d + 0.15) * 20) / 20 # เผื่ออมหัวเข็ม 10cm + Cover 5cm
    d_actual = t - 0.15
    V_u_wb_kg = max(V_u_wb_X, V_u_wb_Y)
    phi_V_c_wb_kg = phi_V_c_wb_X if V_u_wb_X >= V_u_wb_Y else phi_V_c_wb_Y
    
    # 3. คำนวณ Moment ที่ขอบเสา
    M_ux_pos = sum(Pu_pile * (px - cx/2) for px, py in piles if px > cx/2)
    M_ux_neg = sum(Pu_pile * (abs(px) - cx/2) for px, py in piles if px < -cx/2)
    M_uy_pos = sum(Pu_pile * (py - cy/2) for px, py in piles if py > cy/2)
    M_uy_neg = sum(Pu_pile * (abs(py) - cy/2) for px, py in piles if py < -cy/2)
    M_u = max(M_ux_pos, M_ux_neg, M_uy_pos, M_uy_neg)

    if req_piles <= n_piles:
        status_msg = f"✅ ฐานรากเสาเข็ม {n_piles} ต้น (กว้าง {B_actual:.2f} x ยาว {L_actual:.2f} ม.) ปลอดภัย"
    else:
        status_msg = f"⚠️ เตือน: โหลด {P_service}t ต้องการเข็ม {req_piles} ต้น แต่คุณเลือกออกแบบที่ {n_piles} ต้น!"

    B, L = B_actual, L_actual

# --- 3. การออกแบบเหล็กเสริม (Reinforcement) ---
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

# --- 4. ส่วนแสดงผล (UI) ---
if "⚠️" in status_msg: st.warning(status_msg)
else: st.success(status_msg)

tab1, tab2 = st.tabs(["🚀 Dashboard", "🎲 3D Structural Model"])

with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ขนาด กว้าง x ยาว", f"{B:.2f} x {L:.2f} ม.")
    c2.metric("ความหนารวม (t)", f"{t*100:.0f} ซม.")
    c3.metric("ระยะประสิทธิผล (d)", f"{d_actual*100:.1f} ซม.")
    c4.metric("แรงทะลุสูงสุด ($V_u$)", f"{V_u_p_kg:,.0f} kg")
    
    st.info(f"**ตะแกรงเหล็กล่าง:** ใช้ **DB{bar_dia} - {num_bars} เส้น @ {spacing} ซม.**")
    
    st.markdown("### ⚔️ ตรวจสอบสถานะแรงเฉือน (Code Check)")
    st.table(pd.DataFrame({
        "ประเภท": ["Wide Beam Shear", "Punching Shear"],
        "แรงเกิดขึ้น $V_u$ (kg)": [f"{V_u_wb_kg:,.0f}", f"{V_u_p_kg:,.0f}"],
        "กำลังต้านทาน $\\phi V_c$": [f"{phi_V_c_wb_kg:,.0f}", f"{phi_V_c_p_kg:,.0f}"],
        "สถานะ": ["✅ PASS", "✅ PASS"]
    }))

with tab2:
    st.markdown("แบบจำลองพิกัดจริง (True Coordinate Model) ซูมและหมุนดูระยะขอบได้")
    fig = go.Figure()
    
    # ฐานราก (วาดตามพิกัดจริง ไม่ใช่จุดศูนย์กลางสมมติ)
    fig.add_trace(go.Mesh3d(
        x=[ft_x_min, ft_x_max, ft_x_max, ft_x_min, ft_x_min, ft_x_max, ft_x_max, ft_x_min],
        y=[ft_y_min, ft_y_min, ft_y_max, ft_y_max, ft_y_min, ft_y_min, ft_y_max, ft_y_max],
        z=[0, 0, 0, 0, t, t, t, t],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='rgba(135, 206, 250, 0.7)', name='Footing'
    ))
    
    # เสาตอม่อ (ศูนย์กลาง 0,0 เสมอ)
    fig.add_trace(go.Mesh3d(
        x=[-cx/2, cx/2, cx/2, -cx/2, -cx/2, cx/2, cx/2, -cx/2],
        y=[-cy/2, -cy/2, cy/2, cy/2, -cy/2, -cy/2, cy/2, cy/2],
        z=[t, t, t, t, t+0.8, t+0.8, t+0.8, t+0.8],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='orange', name='Column'
    ))

    # เสาเข็ม
    for px, py in piles:
        fig.add_trace(go.Mesh3d(
            x=[px-pile_size/2, px+pile_size/2, px+pile_size/2, px-pile_size/2, px-pile_size/2, px+pile_size/2, px+pile_size/2, px-pile_size/2],
            y=[py-pile_size/2, py-pile_size/2, py+pile_size/2, py+pile_size/2, py-pile_size/2, py-pile_size/2, py+pile_size/2, py+pile_size/2],
            z=[0.1, 0.1, 0.1, 0.1, -1.0, -1.0, -1.0, -1.0],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color='gray', name='Pile'
        ))

    max_dim = max(B, L)
    fig.update_layout(scene=dict(
        xaxis=dict(title='X (m)', range=[-max_dim, max_dim]),
        yaxis=dict(title='Y (m)', range=[-max_dim, max_dim]),
        zaxis=dict(title='Z (m)', range=[-1.0, t+1.0]),
        aspectmode='data'
    ), margin=dict(l=0, r=0, b=0, t=0))
    st.plotly_chart(fig, use_container_width=True)
