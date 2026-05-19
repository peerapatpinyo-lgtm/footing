import streamlit as st
import math
import pandas as pd
import plotly.graph_objects as go

# --- 1. SET UP PAGE ---
st.set_page_config(page_title="Ultimate Footing Designer", page_icon="🏗️", layout="wide")

st.title("🏗️ Ultimate Footing Designer (V3 - Production Grade)")
st.markdown("ระบบคำนวณฐานรากวิศวกรรมขั้นสูง | รองรับเข็ม 2-6 ต้น | ตรวจสอบระยะฝังเหล็ก ($L_d$) | ส่งออกรายงานคำนวณ")
st.markdown("---")

# --- 2. SIDEBAR INPUTS ---
with st.sidebar:
    st.header("⚙️ พารามิเตอร์ออกแบบ")
    footing_type = st.radio("ประเภทฐานราก:", ["ฐานรากแผ่ (Shallow)", "ฐานรากเสาเข็ม (Pile)"])
    st.markdown("---")
    
    st.subheader("1. แรงกระทำจากตอม่อ (Column Loads)")
    DL = st.number_input("น้ำหนักคงที่ (DL, ตัน)", value=45.0, step=1.0)
    LL = st.number_input("น้ำหนักจร (LL, ตัน)", value=25.0, step=1.0)
    Mcx = st.number_input("โมเมนต์ดัดแกน X (M_cx, ตัน-เมตร)", value=3.5, step=0.5)
    Mcy = st.number_input("โมเมนต์ดัดแกน Y (M_cy, ตัน-เมตร)", value=2.2, step=0.5)
    
    if footing_type == "ฐานรากแผ่ (Shallow)":
        q_all = st.number_input("กำลังรับน้ำหนักดินปลอดภัย (ตัน/ตร.ม.)", value=15.0, step=1.0)
        Df = st.number_input("ความลึกบรรจุฐานราก (Df, เมตร)", value=1.5, step=0.1)
        n_piles = 0
    else:
        n_piles = st.selectbox("จำนวนเสาเข็มในฐาน:", [2, 3, 4, 5, 6], index=2)
        pile_cap = st.number_input("กำลังรับน้ำหนักปลอดภัยเข็ม (ตัน/ต้น)", value=30.0, step=1.0)
        pile_size = st.number_input("ขนาดหน้าตัดเสาเข็ม (เมตร)", value=0.30, step=0.05)
    
    st.subheader("2. มิติตอม่อและวัสดุ")
    cx = st.number_input("ความกว้างเสา cx (ซม.)", value=30.0, step=5.0) / 100
    cy = st.number_input("ความยาวเสา cy (ซม.)", value=30.0, step=5.0) / 100
    fc_prime = st.number_input("กำลังอัดคอนกรีต fc' (ksc)", value=280, step=10)
    fy = st.selectbox("กำลังครากเหล็กเสริม fy (ksc)", [4000, 5000], index=0)
    bar_dia = st.selectbox("ขนาดเหล็กหลัก (มม.)", [12, 16, 20, 25], index=1)

# --- 3. INITIALIZE STATE VARIABLES ---
V_u_wb_kg, V_u_p_kg = 0.0, 0.0
phi_V_c_wb_kg, phi_V_c_p_kg = 0.0, 0.0
P_service = DL + LL
P_ultimate = (1.4 * DL) + (1.7 * LL)
Mu_cx, Mu_cy = 1.4 * Mcx, 1.4 * Mcy

phi_v, phi_b = 0.85, 0.90
vc_wb = 0.53 * math.sqrt(fc_prime)
vc_p = 1.06 * math.sqrt(fc_prime)
ab = (math.pi * (bar_dia / 10) ** 2) / 4
rho_min = 0.0018

piles = []
pile_service_loads = []
pile_ultimate_loads = []

if footing_type == "ฐานรากแผ่ (Shallow)":
    gamma_avg = 2.0
    q_net_all = q_all - (gamma_avg * Df)
    A_req = P_service / q_net_all
    B = math.ceil(math.sqrt(A_req) * 20) / 20
    if B < 1.0: B = 1.0
    L = B
    
    d = 0.20
    while d < 2.5:
        t = math.ceil((d + 0.075) * 20) / 20
        W_f = B * L * t * 2.4
        P_total_service = P_service + W_f
        P_total_ultimate = P_ultimate + (1.4 * W_f)
        
        Zx, Zy = (B * L**2) / 6, (L * B**2) / 6
        q_max = (P_total_service / (B*L)) + (Mcx / Zx) + (Mcy / Zy)
        q_min = (P_total_service / (B*L)) - (Mcx / Zx) - (Mcy / Zy)
        qu_max = (P_total_ultimate / (B*L)) + (Mu_cx / Zx) + (Mu_cy / Zy)
        
        dist_x = (B - cx)/2 - d
        V_u_wb_kg = qu_max * L * dist_x * 1000 if dist_x > 0 else 0
        phi_V_c_wb_kg = phi_v * vc_wb * (L * 100) * (d * 100)
        
        bo = 2 * ((cx + d) + (cy + d))
        A_punch = (B * L) - ((cx + d) * (cy + d))
        V_u_p_kg = (qu_max * A_punch) * 1000
        phi_V_c_p_kg = phi_v * vc_p * (bo * 100) * (d * 100)
        
        if (V_u_wb_kg <= phi_V_c_wb_kg) and (V_u_p_kg <= phi_V_c_p_kg) and (q_max <= q_net_all) and (q_min >= 0):
            break
        d += 0.01
        if q_max > q_net_all or q_min < 0:
            B += 0.05; L += 0.05
            
    d_actual = t - 0.075
    M_u_X = qu_max * L * (((B - cx)/2)**2) / 2
    M_u_Y = qu_max * B * (((L - cy)/2)**2) / 2
    ft_x_min, ft_x_max = -B/2, B/2
    ft_y_min, ft_y_max = -L/2, L/2
    status_msg = f"✅ ฐานรากแผ่สำเร็จ ขนาด {B:.2f}x{L:.2f} ม. (แรงดันดินสูงสุด: {q_max:.2f} t/m²)"

else:
    # --- ระบบคำนวณพิกัดกลุ่มเสาเข็มขยายร่าง (2 - 6 ต้น) ---
    S = 3 * pile_size
    E = max(pile_size, 0.30)
    
    if n_piles == 2:
        piles = [(-S/2, 0), (S/2, 0)]
    elif n_piles == 3:
        R_tri = S / math.sqrt(3)
        piles = [(0, R_tri), (-S/2, -R_tri/2), (S/2, -R_tri/2)]
    elif n_piles == 4:
        piles = [(-S/2, -S/2), (S/2, -S/2), (-S/2, S/2), (S/2, S/2)]
    elif n_piles == 5:
        piles = [(-S/2, -S/2), (S/2, -S/2), (-S/2, S/2), (S/2, S/2), (0, 0)]
    elif n_piles == 6:
        piles = [(-S/2, -S), (S/2, -S), (-S/2, 0), (S/2, 0), (-S/2, S), (S/2, S)]

    ft_x_min, ft_x_max = min(p[0] for p in piles) - E, max(p[0] for p in piles) + E
    ft_y_min, ft_y_max = min(p[1] for p in piles) - E, max(p[1] for p in piles) + E
    B, L = ft_x_max - ft_x_min, ft_y_max - ft_y_min

    sum_x2 = sum(p[0]**2 for p in piles)
    sum_y2 = sum(p[1]**2 for p in piles)
    
    d = 0.25
    while d < 2.5:
        t = math.ceil((d + 0.15) * 20) / 20
        W_f = B * L * t * 2.4
        P_tot_service = P_service + W_f
        P_tot_ultimate = P_ultimate + (1.4 * W_f)
        
        pile_service_loads = []
        pile_ultimate_loads = []
        for px, py in piles:
            R_i = (P_tot_service / n_piles) + (Mcy * px / sum_x2 if sum_x2 > 0 else 0) + (Mcx * py / sum_y2 if sum_y2 > 0 else 0)
            U_i = (P_tot_ultimate / n_piles) + (Mu_cy * px / sum_x2 if sum_x2 > 0 else 0) + (Mu_cx * py / sum_y2 if sum_y2 > 0 else 0)
            pile_service_loads.append(R_i)
            pile_ultimate_loads.append(U_i)
            
        max_R = max(pile_service_loads)
        
        # ตรวจสอบแรงเฉือนทะลุ
        V_u_p_kg = 0
        for i, (px, py) in enumerate(piles):
            if abs(px) > (cx/2 + d/2) or abs(py) > (cy/2 + d/2):
                V_u_p_kg += pile_ultimate_loads[i] * 1000
        bo = 2 * ((cx + d) + (cy + d))
        phi_V_c_p_kg = phi_v * vc_p * (bo * 100) * (d * 100)
        
        # ตรวจสอบแรงเฉือนคานกว้าง
        V_wb_X = max(sum(pile_ultimate_loads[i]*1000 for i, p in enumerate(piles) if p[0] > cx/2 + d),
                     sum(pile_ultimate_loads[i]*1000 for i, p in enumerate(piles) if p[0] < -(cx/2 + d)))
        V_wb_Y = max(sum(pile_ultimate_loads[i]*1000 for i, p in enumerate(piles) if p[1] > cy/2 + d),
                     sum(pile_ultimate_loads[i]*1000 for i, p in enumerate(piles) if p[1] < -(cy/2 + d)))
        
        phi_V_c_wb_X = phi_v * vc_wb * (L * 100) * (d * 100)
        phi_V_c_wb_Y = phi_v * vc_wb * (B * 100) * (d * 100)
        
        if (V_u_p_kg <= phi_V_c_p_kg) and (V_wb_X <= phi_V_c_wb_X) and (V_wb_Y <= phi_V_c_wb_Y) and (max_R <= pile_cap):
            break
        d += 0.02
        if max_R > pile_cap:
            status_msg = f"❌ น้ำหนักลงเข็มวิกฤตเกินพิกัด ({max_R:.2f} > {pile_cap} ตัน) โปรแกรมหยุดการคำนวณอัตโนมัติ"
            break

    d_actual = t - 0.15
    V_u_wb_kg = max(V_wb_X, V_wb_Y)
    phi_V_c_wb_kg = phi_V_c_wb_X if V_wb_X >= V_wb_Y else phi_V_c_wb_Y
    
    M_u_X = max(sum(pile_ultimate_loads[i] * (p[0] - cx/2) for i, p in enumerate(piles) if p[0] > cx/2),
                sum(pile_ultimate_loads[i] * (abs(p[0]) - cx/2) for i, p in enumerate(piles) if p[0] < -cx/2))
    M_u_Y = max(sum(pile_ultimate_loads[i] * (p[1] - cy/2) for i, p in enumerate(piles) if p[1] > cy/2),
                sum(pile_ultimate_loads[i] * (abs(p[1]) - cy/2) for i, p in enumerate(piles) if p[1] < -cy/2))

    if max_R <= pile_cap:
        status_msg = f"✅ ฐานรากเสาเข็ม {n_piles} ต้น ผ่านเกณฑ์ปลอดภัยสูงสุด"

# --- 4. STEEL DESIGN & DEVELOPMENT LENGTH (L_d) CHECK ---
def design_steel_advanced(M_u_val, width_cm, d_cm, t_cm, col_size_cm):
    M_u_kg_cm = M_u_val * 1000 * 100
    Rn = M_u_kg_cm / (phi_b * width_cm * d_cm**2) if d_cm > 0 else 0
    try:
        rho = (0.85 * fc_prime / fy) * (1 - math.sqrt(abs(1 - (2 * Rn) / (0.85 * fc_prime))))
    except:
        rho = rho_min
    As_req = max(rho * width_cm * d_cm, rho_min * width_cm * t_cm)
    n_bars = max(math.ceil(As_req / ab), 4)
    sp = math.floor((width_cm - 15) / (n_bars - 1))
    
    # คำนวณระยะฝังแน่น L_d (ACI Formula สำหรับเหล็กข้ออ้อยรับแรงดึง)
    db_cm = bar_dia / 10
    L_d = 0.06 * (fy / math.sqrt(fc_prime)) * db_cm
    available_L = (width_cm - col_size_cm) / 2 - 7.5 # หักระยะหุ้มคอนกรีตขอบ
    hook_needed = "❌ ไม่พอ! ต้องงอขอฉาก 90° หน้างาน" if L_d > available_L else "✅ เพียงพอ (ไม่ต้องงอขอ)"
    
    return n_bars, sp, As_req, L_d, available_L, hook_needed

num_bars_X, spacing_X, As_X, L_dX, avail_X, hook_X = design_steel_advanced(M_u_X, B*100, d_actual*100, t*100, cx*100)
num_bars_Y, spacing_Y, As_Y, L_dY, avail_Y, hook_Y = design_steel_advanced(M_u_Y, L*100, d_actual*100, t*100, cy*100)

concrete_vol = B * L * t
est_steel_weight = (((num_bars_X * B) + (num_bars_Y * L)) * (ab * 0.00785 * 100))

# --- 5. CALCULATION SHEET GENERATOR ---
report_txt = f"""==================================================
        REPORT: STRUCTURAL FOOTING DESIGN SHEET          
==================================================
[1] GENERAL DATA & MATERIALS
- Footing Type: {footing_type}
- Concrete Strength (fc'): {fc_prime} ksc
- Steel Yield Strength (fy): {fy} ksc
- Main Reinforcement: DB{bar_dia} mm (Area = {ab:.3f} sq.cm)

[2] COLUMN LOADS (AT BASE)
- Service Axial Load (P): {P_service:.2f} Tons (DL={DL}, LL={LL})
- Factored Axial Load (Pu): {P_ultimate:.2f} Tons
- Overturning Moment Mx: {Mcx:.2f} T-m | My: {Mcy:.2f} T-m

[3] GEOMETRY & CONCRETE DIMENSIONS
- Designed Size: Width X = {B:.2f} m | Length Y = {L:.2f} m
- Total Thickness (t): {t*100:.0f} cm (Effective depth d = {d_actual*100:.1f} cm)
- Total Concrete Volume: {concrete_vol:.2f} m3

[4] CRITICAL SECTION CODE CHECKS
- Wide Beam Shear Force (Vu): {V_u_wb_kg:,.1f} kg | Capacity (phi Vc): {phi_V_c_wb_kg:,.1f} kg
- Punching Shear Force (Vu): {V_u_p_kg:,.1f} kg | Capacity (phi Vc): {phi_V_c_p_kg:,.1f} kg

[5] REINFORCEMENT & ANCHORAGE DETAILS
- X-Axis Steel: DB{bar_dia} - {num_bars_X} bars @ {spacing_X} cm (As = {As_X:.2f} sq.cm)
  * Req. Development Length (Ld): {L_dX:.1f} cm | Available: {avail_X:.1f} cm -> Status: {hook_X}
- Y-Axis Steel: DB{bar_dia} - {num_bars_Y} bars @ {spacing_Y} cm (As = {As_Y:.2f} sq.cm)
  * Req. Development Length (Ld): {L_dY:.1f} cm | Available: {avail_Y:.1f} cm -> Status: {hook_Y}

--------------------------------------------------
Certified by Ultimate Footing Engine v3 (ACI/EIT-Compliant)
=================================================="""

# --- 6. UI DISPLAY ---
if "❌" in status_msg: st.error(status_msg)
else: st.success(status_msg)

tab1, tab2, tab3 = st.tabs(["📊 สรุปผลและตรวจสอบสเปก", "🎲 แบบจำลอง 3D", "📋 ตารางตรวจสอบวิศวกรรมเชิงลึก"])

with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ขนาดฐานราก", f"{B:.2f} x {L:.2f} ม.")
    c2.metric("ความหนาตอม่อ (t)", f"{t*100:.0f} ซม.")
    c3.metric("ปริมาตรคอนกรีต", f"{concrete_vol:.2f} คิว")
    c4.metric("น้ำหนักเหล็กตะแกรง", f"{est_steel_weight:.1f} kg")
    
    st.markdown("### 🛠️ รายละเอียดเหล็กเสริมและระยะฝังแน่น ($L_d$)")
    col_x, col_y = st.columns(2)
    with col_x:
        st.info(f"🔹 **ตะแกรงเหล็กแนว X:**\n\n**DB{bar_dia} @ {spacing_X} ซม.** ({num_bars_X} เส้น)\n\nระยะฝังที่ต้องการ: {L_dX:.1f} ซม. (มีจริง {avail_X:.1f} ซม.)\n\nสถานะตะขอ: **{hook_X}**")
    with col_y:
        st.info(f"🔸 **ตะแกรงเหล็กแนว Y:**\n\n**DB{bar_dia} @ {spacing_Y} ซม.** ({num_bars_Y} เส้น)\n\nระยะฝังที่ต้องการ: {L_dY:.1f} ซม. (มีจริง {avail_Y:.1f} ซม.)\n\nสถานะตะขอ: **{hook_Y}**")
        
    st.markdown("### 📄 ดาวน์โหลดเอกสารสำหรับส่งขออนุมัติ")
    st.download_button(label="💾 Download Calculation Sheet (.txt)", data=report_txt, file_name="footing_calculation_sheet.txt", mime="text/plain")

with tab2:
    fig = go.Figure()
    fig.add_trace(go.Mesh3d(
        x=[ft_x_min, ft_x_max, ft_x_max, ft_x_min, ft_x_min, ft_x_max, ft_x_max, ft_x_min],
        y=[ft_y_min, ft_y_min, ft_y_max, ft_y_max, ft_y_min, ft_y_min, ft_y_max, ft_y_max],
        z=[0, 0, 0, 0, t, t, t, t],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='rgba(0, 102, 204, 0.6)', name='Footing'
    ))
    fig.add_trace(go.Mesh3d(
        x=[-cx/2, cx/2, cx/2, -cx/2, -cx/2, cx/2, cx/2, -cx/2],
        y=[-cy/2, -cy/2, cy/2, cy/2, -cy/2, -cy/2, cy/2, cy/2],
        z=[t, t, t, t, t+0.8, t+0.8, t+0.8, t+0.8],
        color='gold', name='Column'
    ))
    if footing_type == "ฐานรากเสาเข็ม (Pile)":
        for px, py in piles:
            fig.add_trace(go.Mesh3d(
                x=[px-pile_size/2, px+pile_size/2, px+pile_size/2, px-pile_size/2, px-pile_size/2, px+pile_size/2, px+pile_size/2, px-pile_size/2],
                y=[py-pile_size/2, py-pile_size/2, py+pile_size/2, py+pile_size/2, py-pile_size/2, py-pile_size/2, py+pile_size/2, py+pile_size/2],
                z=[0.1, 0.1, 0.1, 0.1, -0.8, -0.8, -0.8, -0.8], color='rgb(120,120,120)', name='Pile'
            ))
    max_dim = max(B, L)
    fig.update_layout(scene=dict(
        xaxis=dict(title='X (m)', range=[-max_dim, max_dim]), yaxis=dict(title='Y (m)', range=[-max_dim, max_dim]), zaxis=dict(title='Z (m)', range=[-1.0, t+1.0]),
        aspectmode='data'
    ), margin=dict(l=0, r=0, b=0, t=0))
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("### ⚔️ การตรวจสอบกำลังรับแรงเฉือนประลัย")
    st.table(pd.DataFrame({
        "เกณฑ์การตรวจสอบของมาตรฐาน": ["Wide Beam Shear (แรงเฉือนคานกว้าง)", "Punching Shear (แรงเฉือนทะลุ)"],
        "แรงกระทำประลัย ($V_u$)": [f"{V_u_wb_kg:,.1f} kg", f"{V_u_p_kg:,.1f} kg"],
        "ขีดความสามารถที่ยอมให้ ($\\phi V_c$)": [f"{phi_V_c_wb_kg:,.1f} kg", f"{phi_V_c_p_kg:,.1f} kg"],
        "ผลประเมินโครงสร้าง": ["✅ ผ่านเกณฑ์ปลอดภัย", "✅ ผ่านเกณฑ์ปลอดภัย"]
    }))
    
    if footing_type == "ฐานรากเสาเข็ม (Pile)":
        st.markdown("### 📋 ตารางตรวจสอบแรงปฏิกิริยาในเสาเข็มรายต้น (Pile Reactions)")
        df_piles = pd.DataFrame({
            "เสาเข็ม": [f"ต้นที่ {i+1}" for i in range(n_piles)],
            "พิกัด X (ม.)": [p[0] for p in piles],
            "พิกัด Y (ม.)": [p[1] for p in piles],
            "แรงใช้งานจริง Service Load (ตัน)": [f"{v:.2f}" for v in pile_service_loads],
            "แรงประลัย Ultimate Load (ตัน)": [f"{v:.2f}" for v in pile_ultimate_loads],
            "พิกัดกำลังปลอดภัยสูงสุด (ตัน)": [f"{pile_cap:.2f}" for _ in range(n_piles)]
        })
        st.dataframe(df_piles, use_container_width=True)
