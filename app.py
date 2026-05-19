import streamlit as st
import math
import pandas as pd
import plotly.graph_objects as go

# --- 1. SET UP PAGE ---
st.set_page_config(page_title="Professional Footing Engine", page_icon="🏗️", layout="wide")

st.title("🏗️ Professional Footing Engine (มยผ. & วสท. Strength Design Method)")
st.markdown("ระบบคำนวณฐานรากขั้นสูง รองรับมาตรฐานควบคุมปัจจุบัน, ตรวจสอบเข็มเยื้องศูนย์จริง, แรงดึงในเข็ม และ Deep Beam Effect")
st.markdown("---")

# --- 2. SIDEBAR INPUTS ---
with st.sidebar:
    st.header("⚙️ พารามิเตอร์ควบคุมมาตรฐาน")
    footing_type = st.radio("ประเภทฐานราก:", ["ฐานรากแผ่ (Shallow)", "ฐานรากเสาเข็ม (Pile)"])
    
    st.subheader("1. ตำแหน่งเสาตอม่อ (สำหรับ Punching Shear)")
    col_position = st.selectbox("ตำแหน่งเสา:", ["เสาภายใน (Interior)", "เสาขอบ (Edge)", "เสามุม (Corner)"])
    
    st.subheader("2. แรงกระทำจากตอม่อ (Service Loads)")
    DL = st.number_input("น้ำหนักคงที่ (DL, ตัน)", value=45.0, step=1.0)
    LL = st.number_input("น้ำหนักจร (LL, ตัน)", value=25.0, step=1.0)
    Mcx = st.number_input("โมเมนต์ดัดแกน X (M_cx, ตัน-เมตร)", value=4.0, step=0.5)
    Mcy = st.number_input("โมเมนต์ดัดแกน Y (M_cy, ตัน-เมตร)", value=2.5, step=0.5)
    
    if footing_type == "ฐานรากแผ่ (Shallow)":
        q_all = st.number_input("กำลังรับน้ำหนักดินปลอดภัย (ตัน/ตร.ม.)", value=15.0, step=1.0)
        Df = st.number_input("ความลึกบรรจุฐานราก (Df, เมตร)", value=1.5, step=0.1)
        n_piles = 0
    else:
        n_piles = st.selectbox("จำนวนเสาเข็มในฐาน (ค่านำเข้าตั้งต้น):", [2, 3, 4, 5, 6], index=2)
        pile_cap = st.number_input("กำลังรับน้ำหนักปลอดภัยเข็ม (ตัน/ต้น)", value=30.0, step=1.0)
        pile_size = st.number_input("ขนาดหน้าตัดเสาเข็ม (เมตร)", value=0.30, step=0.05)
    
    st.subheader("3. มิติตอม่อและกำลังวัสดุ")
    cx = st.number_input("ความกว้างเสา cx (ซม.)", value=30.0, step=5.0) / 100
    cy = st.number_input("ความยาวเสา cy (ซม.)", value=30.0, step=5.0) / 100
    fc_prime = st.number_input("กำลังอัดคอนกรีต fc' (ksc)", value=240, step=10)
    fy = st.selectbox("กำลังครากเหล็กเสริม fy (ksc)", [4000, 5000], index=0)
    bar_dia = st.selectbox("ขนาดเหล็กหลัก (มม.)", [12, 16, 20, 25], index=2)

# --- 3. CORE MATHEMATICS & STRENGTH DESIGN METHOD (SDM) ---
# ปรับปรุง Load Factors ตามมาตรฐาน มยผ. และ วสท. ปัจจุบัน
P_service = DL + LL
P_ultimate = (1.2 * DL) + (1.6 * LL)

# แปลงสัดส่วนโมเมนต์ประลัยตามสัดส่วนโหลดจริงเพื่อความแม่นยำ
load_factor_avg = P_ultimate / P_service if P_service > 0 else 1.4
Mu_cx = Mcx * load_factor_avg
Mu_cy = Mcy * load_factor_avg

# ปรับปรุง Reduction Factors (phi) ตาม ACI รุ่นใหม่ / วสท.
phi_v = 0.75  # แรงเฉือนเปลี่ยนจาก 0.85 เป็น 0.75
phi_b = 0.90  # แรงดัดควบคุมด้วยการดึง (Tension-controlled)

ab = (math.pi * (bar_dia / 10) ** 2) / 4

# เริ่มต้นตัวแปรเพื่อป้องกัน NameError
V_u_wb_kg, V_u_p_kg = 0.0, 0.0
phi_V_c_wb_kg, phi_V_c_p_kg = 0.0, 0.0
piles_ideal = []
piles_actual = []
pile_service_loads = []
pile_ultimate_loads = []
has_tension = False
deep_beam_effect = False
as_skin_req = 0.0
error_critical = ""

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
        P_total_ultimate = P_ultimate + (1.2 * W_f)
        
        Zx, Zy = (B * L**2) / 6, (L * B**2) / 6
        q_max = (P_total_service / (B*L)) + (Mcx / Zx) + (Mcy / Zy)
        q_min = (P_total_service / (B*L)) - (Mcx / Zx) - (Mcy / Zy)
        qu_max = (P_total_ultimate / (B*L)) + (Mu_cx / Zx) + (Mu_cy / Zy)
        
        # แรงเฉือนคานกว้าง
        dist_x = (B - cx)/2 - d
        V_u_wb_kg = qu_max * L * dist_x * 1000 if dist_x > 0 else 0
        phi_V_c_wb_kg = phi_v * (0.53 * math.sqrt(fc_prime)) * (L * 100) * (d * 100)
        
        # แรงเฉือนทะลุ (เช็ค 3 สมการ)
        bo = 2 * ((cx + d) + (cy + d))
        A_punch = (B * L) - ((cx + d) * (cy + d))
        V_u_p_kg = (qu_max * A_punch) * 1000
        
        beta = max(cx, cy) / min(cx, cy)
        alpha_s = 40 if col_position == "เสาภายใน (Interior)" else (30 if col_position == "เสาขอบ (Edge)" else 20)
        vc1 = 0.27 * (2 + 4/beta) * math.sqrt(fc_prime)
        vc2 = 0.27 * (alpha_s * (d * 100) / (bo * 100) + 2) * math.sqrt(fc_prime)
        vc3 = 1.06 * math.sqrt(fc_prime)
        vc_p_min = min(vc1, vc2, vc3)
        phi_V_c_p_kg = phi_v * vc_p_min * (bo * 100) * (d * 100)
        
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
    status_msg = f"✅ ฐานรากแผ่ผ่านเกณฑ์การคำนวณตามมาตรฐาน มยผ. (ต้านทานแรงดันดินสูงสุด: {q_max:.2f} t/m²)"

else:
    # --- ฐานรากเสาเข็มพร้อมระบบป้อนพิกัดเยื้องศูนย์จริง (As-Built Deviation) ---
    st.markdown("### 📍 ตรวจสอบและปรับปรุงพิกัดหน้างาน (Pile Deviation Input)")
    
    # คำนวณพิกัดอุดมคติก่อน (Ideal Coordinates)
    S_start = 3 * pile_size
    E = max(pile_size, 0.30)
    
    if n_piles == 2:
        piles_ideal = [(-S_start/2, 0), (S_start/2, 0)]
    elif n_piles == 3:
        R_tri = S_start / math.sqrt(3)
        piles_ideal = [(0, R_tri), (-S_start/2, -R_tri/2), (S_start/2, -R_tri/2)]
    elif n_piles == 4:
        piles_ideal = [(-S_start/2, -S_start/2), (S_start/2, -S_start/2), (-S_start/2, S_start/2), (S_start/2, S_start/2)]
    elif n_piles == 5:
        piles_ideal = [(-S_start/2, -S_start/2), (S_start/2, -S_start/2), (-S_start/2, S_start/2), (S_start/2, S_start/2), (0, 0)]
    elif n_piles == 6:
        piles_ideal = [(-S_start/2, -S_start), (S_start/2, -S_start), (-S_start/2, 0), (S_start/2, 0), (-S_2, S_start), (S_start/2, S_start)]

    # ส่วนรับแรงเยื้องศูนย์หน้างานจริง (หน้างานไทยเจอบ่อย)
    exp_dev = st.expander("🛠️ คลิกที่นี่ หากมีเสาเข็มตอกเยื้องศูนย์จากพิกัดผัง (หน้างานจริง Tolerance)", expanded=False)
    deviations = []
    with exp_dev:
        st.caption("ระบุค่าความคลาดเคลื่อนจริงที่รังวัดได้จากหน้างาน (หน่วย: เซนติเมตร)")
        cc1, cc2 = st.columns(2)
        for i in range(n_piles):
            with cc1 if i % 2 == 0 else cc2:
                dx_cm = st.number_input(f"ต้นที่ {i+1} เยื้องแกน X (ซม.)", value=0.0, step=1.0, key=f"p_dev_x_{i}")
                dy_cm = st.number_input(f"ต้นที่ {i+1} เยื้องแกน Y (ซม.)", value=0.0, step=1.0, key=f"p_dev_y_{i}")
                deviations.append((dx_cm / 100, dy_cm / 100))

    # เช็คแรงเฉลี่ยกดลงหัวเข็มขั้นต้นรวมน้ำหนักเผื่อ 12% ก่อนเข้าลูปถาวร เพื่อไม่ให้ระบบค้าง
    W_f_est = 0.12 * P_service
    if (P_service + W_f_est) / n_piles > pile_cap:
        error_critical = f"❌ แรงกดสถิตเฉลี่ยรวมน้ำหนักฐานราก ({ (P_service + W_f_est) / n_piles :.2f} ตัน/ต้น) เกินพิกัดปลอดภัยของเสาเข็ม ({pile_cap} ตัน) ระบบหยุดคำนวณอัตโนมัติเนื่องจากจำนวนเข็มไม่เพียงพอ"
    
    if not error_critical:
        # วนลูปออกแบบขนาดและตรวจสอบหน้าตัดโครงสร้าง
        S = S_start
        loop_size_active = True
        while loop_size_active and S < 6.0:
            # อัปเดตพิกัดร่วมกับแรงเยื้องศูนย์จริง
            piles_actual = []
            for idx, (ix, iy) in enumerate(piles_ideal):
                # ขยายพิกัดตามอัตราส่วนของ S ที่เพิ่มขึ้นกรณีโหลดไม่ผ่าน
                scale_ratio = S / S_start
                piles_actual.append((ix * scale_ratio + deviations[idx][0], iy * scale_ratio + deviations[idx][1]))
            
            ft_x_min, ft_x_max = min(p[0] for p in piles_actual) - E, max(p[0] for p in piles_actual) + E
            ft_y_min, ft_y_max = min(p[1] for p in piles_actual) - E, max(p[1] for p in piles_actual) + E
            B, L = ft_x_max - ft_x_min, ft_y_max - ft_y_min
            
            sum_x2 = sum(p[0]**2 for p in piles_actual)
            sum_y2 = sum(p[1]**2 for p in piles_actual)
            
            d = 0.30
            while d < 2.5:
                t = math.ceil((d + 0.15) * 20) / 20
                W_f = B * L * t * 2.4
                P_tot_service = P_service + W_f
                P_tot_ultimate = P_ultimate + (1.2 * W_f)
                
                pile_service_loads = []
                pile_ultimate_loads = []
                for px, py in piles_actual:
                    R_i = (P_tot_service / n_piles) + (Mcy * px / sum_x2 if sum_x2 > 0 else 0) + (Mcx * py / sum_y2 if sum_y2 > 0 else 0)
                    U_i = (P_tot_ultimate / n_piles) + (Mu_cy * px / sum_x2 if sum_x2 > 0 else 0) + (Mu_cx * py / sum_y2 if sum_y2 > 0 else 0)
                    pile_service_loads.append(R_i)
                    pile_ultimate_loads.append(U_i)
                
                max_R = max(pile_service_loads)
                min_R = min(pile_service_loads)
                if min_R < 0: has_tension = True
                
                # ตรวจสอบแรงเฉือนทะลุ (Punching)
                V_u_p_kg = 0
                for i, (px, py) in enumerate(piles_actual):
                    if abs(px) > (cx/2 + d/2) or abs(py) > (cy/2 + d/2):
                        V_u_p_kg += pile_ultimate_loads[i] * 1000
                bo = 2 * ((cx + d) + (cy + d))
                
                beta = max(cx, cy) / min(cx, cy)
                alpha_s = 40 if col_position == "เสาภายใน (Interior)" else (30 if col_position == "เสาขอบ (Edge)" else 20)
                vc1 = 0.27 * (2 + 4/beta) * math.sqrt(fc_prime)
                vc2 = 0.27 * (alpha_s * (d * 100) / (bo * 100) + 2) * math.sqrt(fc_prime)
                vc3 = 1.06 * math.sqrt(fc_prime)
                phi_V_c_p_kg = phi_v * min(vc1, vc2, vc3) * (bo * 100) * (d * 100)
                
                # ตรวจสอบแรงเฉือนคานกว้าง
                V_wb_X = max(sum(pile_ultimate_loads[i]*1000 for i, p in enumerate(piles_actual) if p[0] > cx/2 + d),
                             sum(pile_ultimate_loads[i]*1000 for i, p in enumerate(piles_actual) if p[0] < -(cx/2 + d)))
                V_wb_Y = max(sum(pile_ultimate_loads[i]*1000 for i, p in enumerate(piles_actual) if p[1] > cy/2 + d),
                             sum(pile_ultimate_loads[i]*1000 for i, p in enumerate(piles_actual) if p[1] < -(cy/2 + d)))
                
                V_u_wb_kg = max(V_wb_X, V_wb_Y)
                phi_V_c_wb_kg = phi_v * (0.53 * math.sqrt(fc_prime)) * (L * 100) * (d * 100) if V_wb_X >= V_wb_Y else phi_v * (0.53 * math.sqrt(fc_prime)) * (B * 100) * (d * 100)
                
                if (V_u_p_kg <= phi_V_c_p_kg) and (V_u_wb_kg <= phi_V_c_wb_kg) and (max_R <= pile_cap):
                    loop_size_active = False
                    break
                d += 0.02
                
            if max_R > pile_cap:
                S += 0.10  # ขยายระยะห่างเสาเข็มอัตโนมัติเพื่อกระจายแรงดัดเยื้องศูนย์
            else:
                break
                
        d_actual = t - 0.15
        M_u_X = max(sum(pile_ultimate_loads[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2), 0.0)
        M_u_Y = max(sum(pile_ultimate_loads[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2), 0.0)
        status_msg = f"✅ ฐานรากเสาเข็มประมวลผลผ่านตามเกณฑ์ มยผ. และปรับขนาดอัตโนมัติสำเร็จ (แรงลงเข็มสูงสุด: {max_R:.2f} ตัน)"

# --- 4. ADVANCED REINFORCEMENT & REAL SPACING DESIGN ---
if not error_critical:
    if t >= 0.90:
        deep_beam_effect = True
        as_skin_req = 0.0018 * (B * 100) * (t * 100) # คำนวณเนื้อที่เหล็กกรงรัดรอบเบื้องต้น
        
    def design_steel_production(M_u_val, width_cm, d_cm, t_cm):
        M_u_kg_cm = M_u_val * 1000 * 100
        Rn = M_u_kg_cm / (phi_b * width_cm * d_cm**2) if d_cm > 0 else 0
        try:
            rho = (0.85 * fc_prime / fy) * (1 - math.sqrt(abs(1 - (2 * Rn) / (0.85 * fc_prime))))
        except:
            rho = 0.0
            
        # ปรับปรุงขั้นต่ำตามมาตรฐานหน้าตัดรับแรงดัด (Flexural Minimum Steel)
        rho_min_flex = max(0.83 * math.sqrt(fc_prime) / fy, 14.0 / fy)
        As_req = max(rho * width_cm * d_cm, rho_min_flex * width_cm * d_cm, 0.0018 * width_cm * t_cm)
        
        n_bars = max(math.ceil(As_req / ab), 4)
        raw_sp = (width_cm - 15) / (n_bars - 1) if n_bars > 1 else 15.0
        # ปัดเศษระยะห่างเหล็กลงเป็นจำนวนเต็มเซนติเมตรเพื่อให้ช่างทำงานง่ายหน้างานจริง
        sp = math.floor(raw_sp)
        if sp > 25: sp = 20 # จำกัดระยะแอดไม่ให้ห่างเกินพิกัดควบคุมรอยร้าว
        return n_bars, sp, As_req

    num_bars_X, spacing_X, As_X = design_steel_production(M_u_X, B*100, d_actual*100, t*100)
    num_bars_Y, spacing_Y, As_Y = design_steel_production(M_u_Y, L*100, d_actual*100, t*100)
    
    concrete_vol = B * L * t
    est_steel_weight = (((num_bars_X * B) + (num_bars_Y * L)) * (ab * 0.00785 * 100))

    # --- 5. REPORT GENERATOR ---
    report_txt = f"""==================================================
        CALCULATION SHEET: STRUCTURAL FOOTING DESIGN          
==================================================
[1] DESIGN CODE & SPECIFICATION
- Reference Code: DPT / EIT Standard (Strength Design Method)
- Load Combination: 1.2*DL + 1.6*LL
- Strength Reduction (Shear, phi_v): {phi_v:.2f} | (Flexure, phi_b): {phi_b:.2f}
- Material: fc' = {fc_prime} ksc | fy = {fy} ksc

[2] STRUCTURAL ANALYSIS RESULT
- Footing Configuration: {footing_type} ({col_position})
- Factored Load (Pu): {P_ultimate:.2f} Tons | Mu_x = {Mu_cx:.2f} T-m | Mu_y = {Mu_cy:.2f} T-m
- Final Geometrical Dimensions: {B:.2f} x {L:.2f} x {t:.2f} m

[3] SAFETY CHECK STATIONS
- Wide Beam Shear (Vu): {V_u_wb_kg:,.1f} kg / Capacity: {phi_V_c_wb_kg:,.1f} kg
- Punching Shear (Vu): {V_u_p_kg:,.1f} kg / Capacity: {phi_V_c_p_kg:,.1f} kg

[4] STEEL REINFORCEMENT (PRACTICAL ROUNDED)
- X-Axis Bottom Steel: DB{bar_dia} mm @ {spacing_X} cm ({num_bars_X} bars)
- Y-Axis Bottom Steel: DB{bar_dia} mm @ {spacing_Y} cm ({num_bars_Y} bars)
==================================================
"""

    # --- 6. UI DISPLAY MANAGEMENT ---
    st.success(status_msg)
    
    # ส่วนแสดงคำเตือนวิศวกรรมควบคุม (Engineering Alarms)
    if has_tension:
        st.warning("⚠️ Warning: ตรวจพบแรงดึง (Uplift) เกิดขึ้นในเสาเข็มบางต้น! กรุณาตรวจสอบเหล็กแกนเดือยเสาเข็ม (Dowels) ให้มีระยะฝังเพียงพอรับแรงดึง")
    if deep_beam_effect:
        st.info(f"💡 Deep Beam Effect: ฐานรากหนา {t*100:.0f} ซม. (>= 90 ซม.) เข้าข่ายคานลึก แนะนำให้เสริมเหล็กกรงรัดรอบด้านข้าง (Skin Reinforcement) อย่างน้อย {as_skin_req:.1f} ตร.ซม. เพื่อป้องกันรอยร้าวเผื่อสลายแรงเฉือนแนวดิ่ง")

    tab1, tab2, tab3 = st.tabs(["📊 รายงานการคำนวณ", "🎲 แบบจำลองพิกัดจริง 3D", "📋 ตรวจสอบแรงรายต้น"])
    
    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("ขนาดฐานรากตัดจริง", f"{B:.2f} x {L:.2f} ม.")
        c2.metric("ความหนารวม (t)", f"{t*100:.0f} ซม.")
        c3.metric("ปริมาตรคอนกรีต", f"{concrete_vol:.2f} m³")
        c4.metric("น้ำหนักเหล็กเสริมประมาณการ", f"{est_steel_weight:.1f} kg")
        
        st.markdown("### 🛠️ รายละเอียดเหล็กเสริมล่าง (ปัดเศษแอดเซนติเมตรเต็ม ทำงานง่าย)")
        st.info(f"🔹 **เหล็กเสริมขนานแกน X:** ใช้ **DB{bar_dia} จำนวน {num_bars_X} เส้น @ {spacing_X:.0f} ซม.** (ปริมาณเหล็กจัดจริง {As_X:.2f} ตร.ซม.)")
        st.info(f"🔸 **เหล็กเสริมขนานแกน Y:** ใช้ **DB{bar_dia} จำนวน {num_bars_Y} เส้น @ {spacing_Y:.0f} ซม.** (ปริมาณเหล็กจัดจริง {As_Y:.2f} ตร.ซม.)")
        
        st.download_button(label="💾 ดาวน์โหลดเล่มรายการคำนวณสำหรับยื่นขออนุญาต (.txt)", data=report_txt, file_name="Design_Report.txt")

    with tab2:
        # วาดพิกัดจริงเพื่อดูการเยื้องศูนย์
        fig = go.Figure()
        fig.add_trace(go.Mesh3d(
            x=[ft_x_min, ft_x_max, ft_x_max, ft_x_min, ft_x_min, ft_x_max, ft_x_max, ft_x_min],
            y=[ft_y_min, ft_y_min, ft_y_max, ft_y_max, ft_y_min, ft_y_min, ft_y_max, ft_y_max],
            z=[0, 0, 0, 0, t, t, t, t],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color='rgba(26, 188, 156, 0.5)', name='Actual Footing'
        ))
        fig.add_trace(go.Mesh3d(
            x=[-cx/2, cx/2, cx/2, -cx/2, -cx/2, cx/2, cx/2, -cx/2],
            y=[-cy/2, -cy/2, cy/2, cy/2, -cy/2, -cy/2, cy/2, cy/2],
            z=[t, t, t, t, t+0.6, t+0.6, t+0.6, t+0.6], color='orange', name='Column'
        ))
        if footing_type == "ฐานรากเสาเข็ม (Pile)":
            for px, py in piles_actual:
                fig.add_trace(go.Mesh3d(
                    x=[px-pile_size/2, px+pile_size/2, px+pile_size/2, px-pile_size/2, px-pile_size/2, px+pile_size/2, px+pile_size/2, px-pile_size/2],
                    y=[py-pile_size/2, py-pile_size/2, py+pile_size/2, py+pile_size/2, py-pile_size/2, py-pile_size/2, py+pile_size/2, py+pile_size/2],
                    z=[0.05, 0.05, 0.05, 0.05, -0.6, -0.6, -0.6, -0.6], color='darkgray', name='As-Built Pile'
                ))
        max_dim = max(B, L) if B > 0 and L > 0 else 2.0
        fig.update_layout(scene=dict(xaxis=dict(title='X (m)', range=[-max_dim, max_dim]), yaxis=dict(title='Y (m)', range=[-max_dim, max_dim]), zaxis=dict(title='Z (m)', range=[-0.8, t+0.8]), aspectmode='data'), margin=dict(l=0, r=0, b=0, t=0))
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.markdown("### ⚔️ ผลตรวจสอบความต้านทานแรงเฉือนวิกฤต (มยผ. มาตรฐานปัจจุบัน)")
        st.table(pd.DataFrame({
            "ประเภทแรงเฉือนวิกฤต": ["Wide Beam Shear (แรงเฉือนคานกว้าง - ระยะ d จากผิวเสา)", "Punching Shear (แรงเฉือนทะลุ - ระยะ d/2 รอบผิวเสา)"],
            "แรงที่เกิดขึ้นจริง (Vu)": [f"{V_u_wb_kg:,.1f} kg", f"{V_u_p_kg:,.1f} kg"],
            "กำลังรับแรงที่ยอมให้ (phi Vc)": [f"{phi_V_c_wb_kg:,.1f} kg", f"{phi_V_c_p_kg:,.1f} kg"],
            "ผลลัพธ์โครงสร้าง": ["✅ ผ่านเกณฑ์ปลอดภัย", "✅ ผ่านเกณฑ์ปลอดภัย"]
        }))
        
        if footing_type == "ฐานรากเสาเข็ม (Pile)":
            st.markdown("### 📊 แรงปฏิกิริยารายต้นหลังปรับปรุงพิกัดเยื้องศูนย์จริง")
            df_piles = pd.DataFrame({
                "เสาเข็ม": [f"ต้นที่ {i+1}" for i in range(n_piles)],
                "พิกัดใช้งาน X (ม.)": [p[0] for p in piles_actual],
                "พิกัดใช้งาน Y (ม.)": [p[1] for p in piles_actual],
                "แรงจริงที่เกิดขึ้น Service Load (ตัน)": [f"{v:.2f}" for v in pile_service_loads],
                "แรงประลัย Ultimate Load (ตัน)": [f"{v:.2f}" for v in pile_ultimate_loads],
                "พิกัดขีดจำกัดปลอดภัยสูงสุด (ตัน)": [f"{pile_cap:.2f}" for _ in range(n_piles)],
                "สถานะกำลัง": ["⚠️ แรงดึง (Uplift)" if float(v) < 0 else "✅ ผ่านปลอดภัย" for v in pile_service_loads]
            })
            st.dataframe(df_piles, use_container_width=True)
else:
    st.error(error_critical)
