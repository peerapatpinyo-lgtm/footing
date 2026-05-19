import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import plotly.graph_objects as go

# --- 1. SET UP PAGE ---
st.set_page_config(page_title="Enterprise Footing Suite V5.8", page_icon="🏗️", layout="wide")

st.title("🏗️ Enterprise Footing Suite (V5.8 - Extended Structural Edition)")
st.markdown("ระบบวิเคราะห์ฐานรากชั้นสูง | รองรับฐานรากสี่เหลี่ยม & สามเหลี่ยมเยื้องศูนย์ | คำนวณ Truncated Shear ตามมาตรฐาน ACI/EIT")
st.markdown("---")

# --- 2. SIDEBAR PARAMETERS ---
with st.sidebar:
    st.header("⚙️ มาตรฐานและข้อกำหนดการออกแบบ")
    
    # [NEW] การเลือกประเภทรูปทรงฐานราก
    footing_shape_type = st.selectbox("รูปทรงฐานรากที่ต้องการออกแบบ:", ["ฐานรากสี่เหลี่ยม (Rectangular Footing)", "ฐานรากสามเหลี่ยม (Triangular Footing)"])
    
    st.subheader("1. รูปแบบกลุ่มเสาเข็ม & รูปทรงเรขาคณิต")
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        n_piles = st.selectbox("จำนวนเสาเข็มในฐานราก:", [2, 3, 4, 5, 6, 8, 9], index=4)
    else:
        st.info("ℹ️ ฐานรากสามเหลี่ยมกำหนดจำนวนเสาเข็มเริ่มต้นที่ 3 ต้น")
        n_piles = 3
        
    pile_shape = st.selectbox("รูปทรงหน้าตัดเสาเข็ม:", ["สี่เหลี่ยมตัน (Square Pile)", "กลมกลวง/สปัน (Spun Pile)", "กลมตัน/เข็มเจาะ (Solid Round Pile)"])
    pile_size = st.number_input("ขนาดเส้นผ่านศูนย์กลางภายนอก หรือความกว้างเสาเข็ม (เมตร)", value=0.30, step=0.05)
    
    wall_thickness = 0.0
    if pile_shape == "กลมกลวง/สปัน (Spun Pile)":
        wall_thickness_cm = st.slider("ความหนาของผนังเสาเข็ม Spun Pile (ซม.)", min_value=5, max_value=12, value=6, step=1)
        wall_thickness = wall_thickness_cm / 100
        
    pile_cap = st.number_input("กำลังรับน้ำหนักปลอดภัยของเข็ม - แรงอัด (ตัน/ต้น)", value=30.0, step=1.0)
    pile_tension_cap = st.number_input("กำลังรับแรงถอนปลอดภัยของเข็ม - แรงดึง (ตัน/ต้น)", value=10.0, step=1.0)
    
    st.subheader("2. แรงกระทำจากเสาตอม่อ (Service Loads)")
    DL = st.number_input("น้ำหนักคงที่ (DL, ตัน)", value=60.0, step=5.0)
    LL = st.number_input("น้ำหนักจร (LL, ตัน)", value=35.0, step=5.0)
    Mcx = st.number_input("โมเมนต์ดัดแกน X (M_cx, ตัน-เมตร)", value=12.0, step=0.5)
    Mcy = st.number_input("โมเมนต์ดัดแกน Y (M_cy, ตัน-เมตร)", value=9.0, step=0.5)
    
    st.subheader("3. มิติตอม่อและวัสดุ")
    cx = st.number_input("ความกว้างเสา cx (เมตร)", value=0.35, step=0.05)
    cy = st.number_input("ความยาวเสา cy (เมตร)", value=0.35, step=0.05)
    col_position = st.selectbox("ตำแหน่งตอม่อบนฐานราก:", ["เสาภายใน (Interior)", "เสาขอบ (Edge)", "เสามุม (Corner)"])
    fc_prime = st.number_input("กำลังอัดประลัยคอนกรีต fc' (ksc)", value=280, step=10)
    fy = st.selectbox("กำลังครากเหล็กเสริม fy (ksc)", [4000, 5000], index=0)
    bar_dia = st.selectbox("ขนาดเหล็กแกนหลัก (มม.)", [16, 20, 25], index=1)

    st.sidebar.markdown("---")
    st.subheader("🎛️ 4. ควบคุมความหนาฐานราก (t)")
    thickness_mode = st.radio("โหมดการคำนวณความหนา:", ["คำนวณอัตโนมัติ (Auto-Optimize)", "ป้อนความหนาเอง (Manual Override)"])
    
    manual_t = 0.60
    if thickness_mode == "ป้อนความหนาเอง (Manual Override)":
        manual_t_cm = st.number_input("ระบุความหนาฐานรากที่ต้องการ t (ซม.)", min_value=30, max_value=300, value=60, step=5)
        manual_t = manual_t_cm / 100

# --- 3. STRENGTH DESIGN METHOD (SDM) CONFIG ---
P_service = DL + LL
P_ultimate = (1.2 * DL) + (1.6 * LL)
load_factor_avg = P_ultimate / P_service if P_service > 0 else 1.4
Mu_cx_direct = Mcx * load_factor_avg
Mu_cy_direct = Mcy * load_factor_avg

phi_v = 0.75  
phi_b = 0.90  
ab = (math.pi * (bar_dia / 10) ** 2) / 4

# --- 4. PILE LAYOUT GENERATOR ---
S_dist = 3.0 * pile_size
E_dist = max(pile_size, 0.35)

if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
    if n_piles == 2: piles_ideal = [(-S_dist/2, 0), (S_dist/2, 0)]
    elif n_piles == 3: piles_ideal = [(0, S_dist/math.sqrt(3)), (-S_dist/2, -S_dist/(2*math.sqrt(3))), (S_dist/2, -S_dist/(2*math.sqrt(3)))]
    elif n_piles == 4: piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2), (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2)]
    elif n_piles == 5: piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2), (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2), (0, 0)]
    elif n_piles == 6: piles_ideal = [(-S_dist/2, -S_dist), (S_dist/2, -S_dist), (-S_dist/2, 0), (S_dist/2, 0), (-S_dist/2, S_dist), (S_dist/2, S_dist)]
    elif n_piles == 8: piles_ideal = [(-1.5*S_dist, -S_dist/2), (-0.5*S_dist, -S_dist/2), (0.5*S_dist, -S_dist/2), (1.5*S_dist, -S_dist/2), (-1.5*S_dist, S_dist/2), (-0.5*S_dist, S_dist/2), (0.5*S_dist, S_dist/2), (1.5*S_dist, S_dist/2)]
    elif n_piles == 9: piles_ideal = [(x, y) for x in [-S_dist, 0, S_dist] for y in [-S_dist, 0, S_dist]]
else:
    # [NEW FEATURE 2] สมการพิกัดรูปทรงสามเหลี่ยมด้านเท่าแท้รอบจุด (0,0)
    piles_ideal = [
        (0, S_dist / math.sqrt(3)),                                # Pile 1 (ยอดบน)
        (-S_dist / 2, -S_dist / (2 * math.sqrt(3))),               # Pile 2 (ล่างซ้าย)
        (S_dist / 2, -S_dist / (2 * math.sqrt(3)))                # Pile 3 (ล่างขวา)
    ]

# --- 5. AS-BUILT DEVIATION ENGINE ---
st.markdown("### 📍 1. ระบบประมวลผลเสาเข็มเยื้องศูนย์หน้างานจริง (True Center of Gravity)")
exp_dev = st.expander("🛠️ คลิกเพื่อใส่ค่ารังวัดความคลาดเคลื่อนของเสาเข็ม (As-Built Coordinate Deviations)", expanded=False)
deviations = []
with exp_dev:
    cc1, cc2, cc3 = st.columns(3)
    for i in range(n_piles):
        if i % 3 == 0: col = cc1
        elif i % 3 == 1: col = cc2
        else: col = cc3
        with col:
            dx_cm = st.number_input(f"เข็มต้นที่ {i+1} หนีศูนย์แกน X (ซม.)", value=0.0, step=1.0, key=f"dev_x_{i}")
            dy_cm = st.number_input(f"เข็มต้นที่ {i+1} หนีศูนย์แกน Y (ซม.)", value=0.0, step=1.0, key=f"dev_y_{i}")
            deviations.append((dx_cm / 100, dy_cm / 100))

piles_actual = [(piles_ideal[i][0] + deviations[i][0], piles_ideal[i][1] + deviations[i][1]) for i in range(n_piles)]
cg_new_x = sum(p[0] for p in piles_actual) / n_piles
cg_new_y = sum(p[1] for p in piles_actual) / n_piles

e_x = 0.0 - cg_new_x
e_y = 0.0 - cg_new_y

piles_relative = [(p[0] - cg_new_x, p[1] - cg_new_y) for p in piles_actual]
sum_x2_new = sum(p[0]**2 for p in piles_relative)
sum_y2_new = sum(p[1]**2 for p in piles_relative)

# กำหนดมิติทรงเรขาคณิตขอบนอกของคอนกรีตฐานราก
if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
    B_ft = (max(p[0] for p in piles_actual) - min(p[0] for p in piles_actual)) + 2*E_dist
    L_ft = (max(p[1] for p in piles_actual) - min(p[1] for p in piles_actual)) + 2*E_dist
    x_max_edge = max(p[0] for p in piles_actual) + E_dist
    x_min_edge = min(p[0] for p in piles_actual) - E_dist
    y_max_edge = max(p[1] for p in piles_actual) + E_dist
    y_min_edge = min(p[1] for p in piles_actual) - E_dist
    footing_area = B_ft * L_ft
else:
    # มิติสามเหลี่ยมด้านเท่าที่ขยายด้วยขอบ E_dist สมบูรณ์แบบทางคณิตศาสตร์
    r_center_to_side = S_dist / (2 * math.sqrt(3))
    r_prime = r_center_to_side + E_dist
    B_ft = S_dist + (2 * E_dist * math.sqrt(3))
    H_ft = (S_dist * math.sqrt(3) / 2) + (3 * E_dist) # ปรับให้สอดคล้องกับระนาบขอบจริง
    
    # พิกัดจุดยอดทั้ง 3 ของฐานรากสามเหลี่ยมเนื้อคอนกรีตจริงรอบจุดอ้างอิง C.G.
    v1_tri = (0, 2 * r_prime)
    v2_tri = (-(S_dist / 2 + math.sqrt(3) * E_dist), -r_prime)
    v3_tri = ((S_dist / 2 + math.sqrt(3) * E_dist), -r_prime)
    footing_area = 0.5 * B_ft * (3 * r_prime)

# --- 🛑 [FEATURE 3] AS-BUILT EDGE DISTANCE CHECK ENGINE ---
min_edge_dist = float('inf')
for px, py in piles_actual:
    r_outer = pile_size / 2
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        d_left = px - r_outer - x_min_edge
        d_right = x_max_edge - (px + r_outer)
        d_bottom = py - r_outer - y_min_edge
        d_top = y_max_edge - (py + r_outer)
        local_min = min(d_left, d_right, d_bottom, d_top)
    else:
        # ระยะห่างสั้นที่สุดไปยังเส้นตรงขอบสามเหลี่ยมทั้ง 3 ด้าน
        d_bottom = py - (-r_prime) - r_outer
        # สมการเส้นตรงขอบเอียงด้านขวาและซ้าย
        m_right = (v1_tri[1] - v3_tri[1]) / (v1_tri[0] - v3_tri[0])
        d_right = abs(m_right * px - py + (v1_tri[1] - m_right * v1_tri[0])) / math.sqrt(m_right**2 + 1) - r_outer
        m_left = (v1_tri[1] - v2_tri[1]) / (v1_tri[0] - v2_tri[0])
        d_left = abs(m_left * px - py + (v1_tri[1] - m_left * v1_tri[0])) / math.sqrt(m_left**2 + 1) - r_outer
        local_min = min(d_bottom, d_right, d_left)
        
    if local_min < min_edge_dist:
        min_edge_dist = local_min

edge_distance_alert = min_edge_dist < 0.10
if edge_distance_alert:
    st.error(f"⚠️ [Edge Distance Alert] ตรวจพบระยะห่างจากผิวเสาเข็มถึงขอบฐานรากสั้นที่สุดคือ {min_edge_dist*100:.1f} ซม. ซึ่งน้อยกว่า 10 ซม. เสี่ยงต่อการเกิด Concrete Spalling หน้างาน!")

# --- 6. CORE STRUCTURAL EVALUATION ENGINE ---
d = 0.40 if thickness_mode == "คำนวณอัตโนมัติ (Auto-Optimize)" else (manual_t - 0.15)
t = 0.55 if thickness_mode == "คำนวณอัตโนมัติ (Auto-Optimize)" else manual_t

has_tension = False
pile_overload_warning = False
shear_fail_manual = False

v_u_stress, v_c_allowable = 0.0, 0.0
v_u_wb_stress, v_c_wb_allowable = 0.0, 0.0
pile_service_loads = [0.0] * n_piles
pile_ultimate_loads = [0.0] * n_piles
r_outer = pile_size / 2

# ฟังก์ชันย่อยสำหรับหาความกว้างหน้าตัดสามเหลี่ยมที่ระดับระนาบ Y ใดๆ
def get_triangle_width_at_y(target_y):
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        return B_ft
    if target_y < -r_prime or target_y > 2*r_prime:
        return 0.0
    return 2 * (S_dist / 2 + math.sqrt(3) * E_dist) * (2 * r_prime - target_y) / (3 * r_prime)

# ฟังก์ชันย่อยสำหรับหาความกว้างระนาบดิ่ง X ใดๆ ในสามเหลี่ยม
def get_triangle_height_at_x(target_x):
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        return L_ft
    x_bound = S_dist / 2 + math.sqrt(3) * E_dist
    if abs(target_x) > x_bound:
        return 0.0
    y_top = 2 * r_prime - (3 * r_prime) * (abs(target_x) / x_bound)
    return max(0.0, y_top - (-r_prime))

def run_structural_calculation_core(current_d, current_t):
    global v_u_stress, v_c_allowable, v_u_wb_stress, v_c_wb_allowable, pile_service_loads, pile_ultimate_loads, has_tension
    W_f_actual = footing_area * current_t * 2.4
    P_tot_s = P_service + W_f_actual
    P_tot_u = P_ultimate + (1.2 * W_f_actual)
    
    Mu_x_loop = Mu_cx_direct + (P_tot_u * (-e_y))
    Mu_y_loop = Mu_cy_direct + (P_tot_u * (-e_x))
    Mx_loop = Mcx + (P_tot_s * (-e_y))
    My_loop = Mcy + (P_tot_s * (-e_x))

    pile_service_loads = []
    pile_ultimate_loads = []
    for prx, pry in piles_relative:
        R_i = (P_tot_s / n_piles) + (My_loop * prx / sum_x2_new if sum_x2_new > 0 else 0) + (Mx_loop * pry / sum_y2_new if sum_y2_new > 0 else 0)
        U_i = (P_tot_u / n_piles) + (Mu_y_loop * prx / sum_x2_new if sum_x2_new > 0 else 0) + (Mu_x_loop * pry / sum_y2_new if sum_y2_new > 0 else 0)
        pile_service_loads.append(R_i)
        pile_ultimate_loads.append(U_i)
        
    # [FEATURE 4] CRITICAL PUNCHING SHEAR WITH GEOMETRIC CLIPPING
    b1 = cx + current_d
    b2 = cy + current_d
    
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        bo = 2 * (b1 + b2)
    else:
        # ระบบโคลนนิ่งและตัดเศษความยาวเส้นรอบรูปเจาะทะลุที่ยื่นออกนอกขอบสามเหลี่ยมจริง
        p_top = cy / 2 + current_d / 2
        p_bot = -cy / 2 - current_d / 2
        p_right = cx / 2 + current_d / 2
        p_left = -cx / 2 - current_d / 2
        
        w_top = get_triangle_width_at_y(p_top)
        w_bot = get_triangle_width_at_y(p_bot)
        h_left = get_triangle_height_at_x(p_left)
        h_right = get_triangle_height_at_x(p_right)
        
        len_top = max(0.0, min(p_right, w_top/2) - max(p_left, -w_top/2))
        len_bot = max(0.0, min(p_right, w_bot/2) - max(p_left, -w_bot/2))
        
        x_bound = S_dist / 2 + math.sqrt(3) * E_dist
        y_top_l = 2 * r_prime - (3 * r_prime) * (abs(p_left) / x_bound) if abs(p_left) <= x_bound else -r_prime
        y_top_r = 2 * r_prime - (3 * r_prime) * (abs(p_right) / x_bound) if abs(p_right) <= x_bound else -r_prime
        
        len_left = max(0.0, min(p_top, y_top_l) - max(p_bot, -r_prime))
        len_right = max(0.0, min(p_top, y_top_r) - max(p_bot, -r_prime))
        bo = len_top + len_bot + len_left + len_right

    A_c = bo * current_d * 10000  
    V_u_p_kg = sum(max(0, pile_ultimate_loads[i] * 1000) for i, (px, py) in enumerate(piles_actual) if abs(px) > (cx/2 + current_d/2) or abs(py) > (cy/2 + current_d/2))
    
    # Combined Stresses Calculation
    v_u_stress = (V_u_p_kg / A_c)
    beta_col = max(cx, cy) / min(cx, cy)
    alpha_s = 40 if col_position == "เสาภายใน (Interior)" else (30 if col_position == "เสาขอบ (Edge)" else 20)
    vc1 = 0.27 * (2 + 4/beta_col) * math.sqrt(fc_prime)
    vc2 = 0.27 * (alpha_s * (current_d * 100) / (bo * 100) + 2) * math.sqrt(fc_prime)
    vc3 = 1.06 * math.sqrt(fc_prime)
    v_c_allowable = phi_v * min(vc1, vc2, vc3)
    
    # [FEATURE 4] FRACTIONAL WIDE BEAM SHEAR AT DISTANCE d (VARIABLE WIDTH)
    X_crit_pos = cx/2 + current_d
    X_crit_neg = -cx/2 - current_d
    Y_crit_pos = cy/2 + current_d
    Y_crit_neg = -cy/2 - current_d
    
    V_wb_X_pos, V_wb_X_neg, V_wb_Y_pos, V_wb_Y_neg = 0.0, 0.0, 0.0, 0.0
    for i, (px, py) in enumerate(piles_actual):
        pu_load = max(0.0, pile_ultimate_loads[i] * 1000)
        if px - r_outer >= X_crit_pos: V_wb_X_pos += pu_load
        if px + r_outer <= X_crit_neg: V_wb_X_neg += pu_load
        if py - r_outer >= Y_crit_pos: V_wb_Y_pos += pu_load
        if py + r_outer <= Y_crit_neg: V_wb_Y_neg += pu_load

    # หน้าตัดรับแรงเฉือนปรับลดความกว้างตามระนาบเรขาคณิตสามเหลี่ยมคางหมูจริง
    bw_X_pos = get_triangle_height_at_x(X_crit_pos) * 100
    bw_X_neg = get_triangle_height_at_x(X_crit_neg) * 100
    bw_Y_pos = get_triangle_width_at_y(Y_crit_pos) * 100
    bw_Y_neg = get_triangle_width_at_y(Y_crit_neg) * 100
    
    v_wb_X_pos = V_wb_X_pos / (bw_X_pos * current_d * 100) if bw_X_pos > 0 else 0
    v_wb_X_neg = V_wb_X_neg / (bw_X_neg * current_d * 100) if bw_X_neg > 0 else 0
    v_wb_Y_pos = V_wb_Y_pos / (bw_Y_pos * current_d * 100) if bw_Y_pos > 0 else 0
    v_wb_Y_neg = V_wb_Y_neg / (bw_Y_neg * current_d * 100) if bw_Y_neg > 0 else 0
    
    v_u_wb_stress = max(v_wb_X_pos, v_wb_X_neg, v_wb_Y_pos, v_wb_Y_neg)
    v_c_wb_allowable = phi_v * 0.53 * math.sqrt(fc_prime)
    
    return (v_u_stress <= v_c_allowable) and (v_u_wb_stress <= v_c_wb_allowable)

# --- 🛑 [FEATURE 2] AMENDED AUTO-OPTIMIZE LOOP (SHEAR-FIRST ENFORCEMENT) ---
if thickness_mode == "คำนวณอัตโนมัติ (Auto-Optimize)":
    while d < 3.0:
        t = math.ceil((d + 0.15) * 20) / 20
        shear_safe = run_structural_calculation_core(d, t)
        if not shear_safe:
            d += 0.02
            continue
        max_R = max(pile_service_loads)
        min_R = min(pile_service_loads)
        pile_overloaded = (max_R > pile_cap) or (min_R < 0 and abs(min_R) > pile_tension_cap)
        if pile_overloaded:
            pile_overload_warning = True
            break
        else:
            break
else:
    t = manual_t
    d = t - 0.15
    shear_safe = run_structural_calculation_core(d, t)
    if not shear_safe:
        shear_fail_manual = True
    max_R = max(pile_service_loads)
    min_R = min(pile_service_loads)
    if (max_R > pile_cap) or (min_R < 0 and abs(min_R) > pile_tension_cap):
        pile_overload_warning = True

d_actual = t - 0.15
w_u_sw_floor = 1.2 * t * 2.4 

# --- 5. FLEXURE MOMENT ENGINEERING AT COLUMN FACES ---
if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
    M_u_X_pos_plane = sum(pile_ultimate_loads[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2) - 0.5 * w_u_sw_floor * ((x_max_edge - cx/2)**2) * L_ft
    M_u_X_neg_plane = sum(pile_ultimate_loads[i] * (-cx/2 - p[0]) for i, p in enumerate(piles_actual) if p[0] < -cx/2) - 0.5 * w_u_sw_floor * ((-cx/2 - x_min_edge)**2) * L_ft
    M_u_Y_pos_plane = sum(pile_ultimate_loads[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2) - 0.5 * w_u_sw_floor * ((y_max_edge - cy/2)**2) * B_ft
    M_u_Y_neg_plane = sum(pile_ultimate_loads[i] * (-cy/2 - p[1]) for i, p in enumerate(piles_actual) if p[1] < -cy/2) - 0.5 * w_u_sw_floor * ((-cy/2 - y_min_edge)**2) * B_ft
    width_flex_X = L_ft * 100
    width_flex_Y = B_ft * 100
else:
    # สำหรับระบบสามเหลี่ยม: แตกแรงหาโมเมนต์ดัดรอบระนาบขอบเสาทั้ง 4 ทิศทางตามจริง
    M_u_X_pos_plane = sum(pile_ultimate_loads[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2) - 0.15 * w_u_sw_floor * (cx/2)**2 # ปรับลดตามพื้นที่แปรผัน
    M_u_X_neg_plane = sum(pile_ultimate_loads[i] * (-cx/2 - p[0]) for i, p in enumerate(piles_actual) if p[0] < -cx/2) - 0.15 * w_u_sw_floor * (-cx/2)**2
    M_u_Y_pos_plane = sum(pile_ultimate_loads[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2)
    M_u_Y_neg_plane = sum(pile_ultimate_loads[i] * (-cy/2 - p[1]) for i, p in enumerate(piles_actual) if p[1] < -cy/2)
    width_flex_X = get_triangle_height_at_x(cx/2) * 100
    width_flex_Y = get_triangle_width_at_y(cy/2) * 100

M_u_X_bot = max(0.0, M_u_X_pos_plane, M_u_X_neg_plane)
M_u_X_top = max(0.0, -M_u_X_pos_plane, -M_u_X_neg_plane)
M_u_Y_bot = max(0.0, M_u_Y_pos_plane, M_u_Y_neg_plane)
M_u_Y_top = max(0.0, -M_u_Y_pos_plane, -M_u_Y_neg_plane)

def design_steel_flexure_v58(M_u_val, w_cm, d_cm, t_cm, f_c, f_y):
    w_cm = max(w_cm, 30.0) # ป้องกันหน้าตัดเป็นศูนย์ที่ปลายแหลม
    As_min = 0.0018 * w_cm * t_cm
    if M_u_val <= 0:
        n_bars = max(math.ceil(As_min / ab), 6)
        sp = math.floor((w_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
        return n_bars, sp, False, False

    M_u_kg_cm = M_u_val * 1000 * 100
    Rn = M_u_kg_cm / (phi_b * w_cm * d_cm**2)
    beta_1 = 0.85 if f_c <= 280 else max(0.65, 0.85 - 0.05 * (f_c - 280) / 70)
    rho_b = 0.85 * beta_1 * (f_c / f_y) * (6120 / (6120 + f_y))
    rho_max = 0.75 * rho_b  
    Rn_max = rho_max * f_y * (1 - 0.59 * rho_max * f_y / f_c)
    
    if (2 * Rn) / (0.85 * f_c) >= 1.0 or Rn > Rn_max:
        return 0, 0, False, True  
        
    rho = (0.85 * f_c / f_y) * (1 - math.sqrt(1 - (2 * Rn) / (0.85 * f_c)))
    if rho > rho_max: return 0, 0, False, True

    rho_min_flex = max(0.83 * math.sqrt(f_c) / f_y, 14.0 / f_y)
    As_req = max(rho * w_cm * d_cm, rho_min_flex * w_cm * d_cm, As_min)
    
    n_bars = max(math.ceil(As_req / ab), 6)
    sp = math.floor((w_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
    max_allowable_sp = min(3 * t_cm, 45.0)
    while sp > max_allowable_sp:
        n_bars += 1
        sp = math.floor((w_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
    return n_bars, sp, (sp < max(1.5 * (bar_dia / 10), 2.5)), False

num_X_bot, sp_X_bot, cong_X_bot, err_X_bot = design_steel_flexure_v58(M_u_X_bot, width_flex_X, d_actual*100, t*100, fc_prime, fy)
num_Y_bot, sp_Y_bot, cong_Y_bot, err_Y_bot = design_steel_flexure_v58(M_u_Y_bot, width_flex_Y, d_actual*100, t*100, fc_prime, fy)
num_X_top, sp_X_top, cong_X_top, err_X_top = design_steel_flexure_v58(M_u_X_top, width_flex_X, d_actual*100, t*100, fc_prime, fy)
num_Y_top, sp_Y_top, cong_Y_top, err_Y_top = design_steel_flexure_v58(M_u_Y_top, width_flex_Y, d_actual*100, t*100, fc_prime, fy)

any_over_reinforced = err_X_bot or err_Y_bot or err_X_top or err_Y_top

# --- 7. 2D ENGINEERING BLUEPRINT ---
st.markdown("### 📊 2. แบบวิศวกรรมและการจัดเหล็กเสริมโครงสร้าง (2D Engineering Blueprint)")
fig_2d, (ax_plan, ax_sec) = plt.subplots(1, 2, figsize=(15, 6))

if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
    rect_cap = patches.Rectangle((min(p[0] for p in piles_actual)-E_dist, min(p[1] for p in piles_actual)-E_dist), B_ft, L_ft, linewidth=2, edgecolor='#2c3e50', facecolor='#ecf0f1', zorder=1)
    ax_plan.add_patch(rect_cap)
else:
    # วาดรูปทรงขอบเขตฐานรากเป็นรูปสามเหลี่ยมแท้จริงตามพิกัดวิศวกรรมควบคุม
    polygon_tri = patches.Polygon([v2_tri, v3_tri, v1_tri], closed=True, linewidth=2, edgecolor='#2c3e50', facecolor='#ecf0f1', zorder=1)
    ax_plan.add_patch(polygon_tri)

# วาดตอม่อและจุดศูนย์ถ่วง C.G.
ax_plan.add_patch(patches.Rectangle((-cx/2, -cy/2), cx, cy, linewidth=1.5, edgecolor='#e74c3c', facecolor='#f1948a', zorder=4))
ax_plan.scatter(cg_new_x, cg_new_y, color='#f39c12', marker='X', s=100, zorder=5)

for i, (px, py) in enumerate(piles_actual):
    if "กลม" in pile_shape:
        ax_plan.add_patch(patches.Circle((px, py), r_outer, linewidth=1.2, edgecolor='#7f8c8d', facecolor='#bdc3c7', zorder=3))
    else:
        ax_plan.add_patch(patches.Rectangle((px-r_outer, py-r_outer), pile_size, pile_size, linewidth=1.2, edgecolor='#7f8c8d', facecolor='#bdc3c7', zorder=3))
    ax_plan.text(px, py, f"P{i+1}", ha='center', va='center', color='#2c3e50', fontsize=9, fontweight='bold', zorder=4)

# จัดสเกลกราฟตามขนาดโครงสร้างจริง
if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
    ax_plan.set_xlim(x_min_edge-0.3, x_max_edge+0.3)
    ax_plan.set_ylim(y_min_edge-0.3, y_max_edge+0.3)
else:
    ax_plan.set_xlim(v2_tri[0]-0.3, v3_tri[0]+0.3)
    ax_plan.set_ylim(v2_tri[1]-0.3, v1_tri[1]+0.3)
    
ax_plan.set_aspect('equal')
ax_plan.grid(True, linestyle=':', alpha=0.5)

# 2D Cross Section Plot
ax_sec.add_patch(patches.Rectangle((-B_ft/2, 0), B_ft, t, linewidth=2, edgecolor='#2c3e50', facecolor='#eaeded'))

# --- 🛑 [FEATURE 1] SAFETY GRAPH GUARD FOR OVER-REINFORCED CRASH ---
if any_over_reinforced:
    ax_sec.text(0, t/2, "CROSS-SECTION OVER-REINFORCED:\nPLEASE INCREASE THICKNESS", ha='center', va='center', color='#c0392b', fontsize=11, fontweight='bold')
else:
    ax_sec.plot([-B_ft/2+0.075, B_ft/2-0.075], [0.075, 0.075], color='#1f618d', linewidth=2.5)
    ax_sec.plot([-B_ft/2+0.075, B_ft/2-0.075], [t-0.075, t-0.075], color='#27ae60', linewidth=2.0, linestyle='--')
    ax_sec.text(0, t/2, f"Thickness t = {t*100:.0f} cm\nBot X: DB{bar_dia} @ {sp_X_bot} cm\nTop X: DB{bar_dia} @ {sp_X_top} cm", ha='center', va='center', color='#2c3e50', fontsize=9, fontweight='bold')

ax_sec.set_xlim(-B_ft/2 - 0.3, B_ft/2 + 0.3)
ax_sec.set_ylim(-0.1, t + 0.5)
ax_sec.set_aspect('equal')
ax_sec.axis('off')
st.pyplot(fig_2d)

# --- 8. OUTPUT DATA TABS ---
tab1, tab2, tab3 = st.tabs(["📝 ผลการประเมินสถิตศาสตร์เชิงลึก", "🎮 มิติและรูปร่าง 3D Solid Render", "📋 ตารางสรุปหน่วยแรงและการจัดเรียงตัวเลข"])

with tab1:
    st.markdown("### 🏢 สรุปความหนาและมิติโครงสร้างควบคุม")
    st.info(f"📐 **ความหนาฐานรากทั้งหมด (Total Thickness, t):** {t*100:.0f} ซม. | **ความหนาประสิทธิผล (Effective Depth, d):** {d_actual*100:.0f} ซม.")
    
    if any_over_reinforced:
        st.error("🚨 [CRITICAL FLEXURE ERROR - OVER-REINFORCED SECTION] ปริมาณเหล็กเสริมดึงหน้าตัดวิกฤตสูงเกินพิกัดควบคุม (rho > rho_max) เสี่ยงต่อการวิบัติพังทลายแบบเปราะในเนื้อคอนกรีตทันที! แก้ไข: กรุณาเพิ่มความหนาฐานราก t ในช่องกรอกไซด์บาร์ทันที")
    elif shear_fail_manual:
        st.error("🚨 [OVERSTRESS ALERT] ในโหมดกรอกมือ ความหนาที่ใส่เข้ามาต่ำเกินไปจนหน่วยแรงเฉือนทะลุพังลิมิต! กรุณาเพิ่มค่าตัวเลขหนา t")
    else:
        st.success("✅ พฤติกรรมแรงเฉือนและสัดส่วนปริมาณเหล็กเสริมผ่านเกณฑ์ตามมาตรฐานวิศวกรรมควบคุมความปลอดภัย")

    if pile_overload_warning:
        st.warning("⚠️ [Pile Overload Warning] น้ำหนักบรรทุกในเสาเข็มบางต้นเกินพิกัดระบุปลอดภัยปลอดภัย (Pile Capacity Overloaded) เนื่องจากน้ำหนักฐานรากหนาขึ้น กรุณาพิจารณาเพิ่มจำนวนเข็มหรือปรับ Grid เสาเข็ม")

    c1, c2, c3 = st.columns(3)
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        c1.metric("ขนาดฐานราก กว้าง x ยาว", f"{B_ft:.2f} x {L_ft:.2f} ม.")
    else:
        c1.metric("มิติฐานรากสามเหลี่ยม (กว้างฐาน x สูง)", f"{B_ft:.2f} x {H_ft:.2f} ม.")
    c2.metric("แรงอัดเข็มสูงสุด (Max Compression)", f"{max(pile_service_loads):.2f} ตัน/ต้น")
    c3.metric("แรงดึงเข็มสูงสุด (Max Uplift/Tension)", f"{min(pile_service_loads):.2f} ตัน/ต้น")

    if not any_over_reinforced:
        st.markdown("### 🧾 รายละเอียดปริมาณเหล็กเส้นสั่งตัดหน้างาน")
        st.markdown(f"* 🔹 **เหล็กเสริมล่าง (ทิศทางหลัก X):** DB{bar_dia} จำนวน **{num_X_bot}** เส้น @ **{sp_X_bot:.0f}** ซม.")
        st.markdown(f"* 🔹 **เหล็กเสริมล่าง (ทิศทางหลัก Y):** DB{bar_dia} จำนวน **{num_Y_bot}** เส้น @ **{sp_Y_bot:.0f}** ซม.")
        st.markdown(f"* 🔸 **เหล็กเสริมบน (ทิศทางหลัก X):** DB{bar_dia} จำนวน **{num_X_top}** เส้น @ **{sp_X_top:.0f}** ซม.")
        st.markdown(f"* 🔸 **เหล็กเสริมบน (ทิศทางหลัก Y):** DB{bar_dia} จำนวน **{num_Y_top}** เส้น @ **{sp_Y_top:.0f}** ซม.")

with tab2:
    # [NEW FEATURE 6] วาดเส้นขอบฐานราก (Footing Boundary) 3D ตามรูปทรงเรขาคณิตจริv
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        x_cap = [x_min_edge, x_max_edge]
        y_cap = [y_min_edge, y_max_edge]
        v_x = [x_cap[0], x_cap[1], x_cap[1], x_cap[0], x_cap[0], x_cap[1], x_cap[1], x_cap[0]]
        v_y = [y_cap[0], y_cap[0], y_cap[1], y_cap[1], y_cap[0], y_cap[0], y_cap[1], y_cap[1]]
        v_z = [0, 0, 0, 0, t, t, t, t]
        mesh_i = [0, 0, 4, 4, 0, 1, 2, 3, 0, 1, 5, 4]
        mesh_j = [1, 2, 5, 6, 4, 5, 6, 7, 3, 2, 6, 7]
        mesh_k = [2, 3, 6, 7, 1, 2, 3, 0, 4, 5, 2, 3]
    else:
        # พิกัด 3D Mesh รูปทรงสามเหลี่ยมปริมาตร (Prism) มี 6 Vertex
        v_x = [v2_tri[0], v3_tri[0], v1_tri[0], v2_tri[0], v3_tri[0], v1_tri[0]]
        v_y = [v2_tri[1], v3_tri[1], v1_tri[1], v2_tri[1], v3_tri[1], v1_tri[1]]
        v_z = [0, 0, 0, t, t, t]
        mesh_i = [0, 0, 3, 3, 0, 1, 4, 3, 1, 2, 5, 4]
        mesh_j = [1, 2, 4, 5, 3, 4, 5, 5, 2, 0, 3, 3]
        mesh_k = [2, 0, 5, 3, 1, 2, 1, 4, 0, 1, 4, 5]
    
    fig_3d = go.Figure(data=[
        go.Mesh3d(
            x=v_x, y=v_y, z=v_z,
            i=mesh_i, j=mesh_j, k=mesh_k,
            opacity=0.6, color='#3498db', name='Footing Body'
        )
    ])
    fig_3d.update_layout(scene=dict(xaxis_title='X (m)', yaxis_title='Y (m)', zaxis_title='Z (m)'), title="3D Interactive Real Geometry View")
    st.plotly_chart(fig_3d, use_container_width=True)

with tab3:
    st.markdown("### ⚔️ ตารางสรุปหน่วยแรงเฉือนวิกฤต")
    df_shear = pd.DataFrame({
        "ประเภทการตรวจสอบ": ["Punching Shear (Truncated Boundary Method)", "Wide Beam Shear (Variable Section Area Method)"],
        "หน่วยแรงเกิดขึ้นจริง": [v_u_stress, v_u_wb_stress],
        "กำลังต้านทานคอนกรีตที่ยอมให้": [v_c_allowable, v_c_wb_allowable]
    })
    st.dataframe(df_shear, column_config={
        "หน่วยแรงเกิดขึ้นจริง": st.column_config.NumberColumn("หน่วยแรงเกิดขึ้นจริง (v_u)", format="%.2f ksc"),
        "กำลังต้านทานคอนกรีตที่ยอมให้": st.column_config.NumberColumn("กำลังที่ยอมให้ (phi * vc)", format="%.2f ksc")
    }, use_container_width=True, hide_index=True)
    
    st.markdown("### 📊 ตารางแสดงแรงปฏิกิริยารายต้น (Copy ไปลง Excel ได้เลย)")
    df_piles_report = pd.DataFrame({
        "เสาเข็ม": [f"ต้นที่ {i+1}" for i in range(n_piles)],
        "พิกัด X จริง (ม.)": [p[0] for p in piles_actual],
        "พิกัด Y จริง (ม.)": [p[1] for p in piles_actual],
        "แรงใช้งาน Service Load": pile_service_loads,
        "แรงประลัย Ultimate Load": pile_ultimate_loads
    })
    st.dataframe(df_piles_report, column_config={
        "พิกัด X จริง (ม.)": st.column_config.NumberColumn("พิกัด Xจริง", format="%.3f ม."),
        "พิกัด Y จริง (ม.)": st.column_config.NumberColumn("พิกัด Yจริง", format="%.3f ม."),
        "แรงใช้งาน Service Load": st.column_config.NumberColumn("แรงใช้งาน Service Load", format="%.2f ตัน"),
        "แรงประลัย Ultimate Load": st.column_config.NumberColumn("แรงประลัย Ultimate Load", format="%.2f ตัน")
    }, use_container_width=True, hide_index=True)
