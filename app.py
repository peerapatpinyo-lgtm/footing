import streamlit as st
import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import plotly.graph_objects as go

# --- 1. INITIAL APP CONFIGURATION ---
st.set_page_config(page_title="Enterprise Footing Suite V5.8", page_icon="📐", layout="wide")

st.title("📐 Enterprise Footing Suite (V5.8 - Extended Structural Edition)")
st.markdown("### ระบบสถาปัตยกรรมวิเคราะห์และออกแบบฐานรากชั้นสูงขั้นประกอบวิชาชีพ")
st.markdown("---")

# --- 2. HELPERS FOR ADVANCED GEOMETRIC VALIDATION ---
def point_to_segment_dist(px, py, x1, y1, x2, y2):
    """คำนวณระยะทางที่สั้นที่สุดจากจุดพิกัดเสาเข็มไปยังเส้นตรงขอบคอนกรีต (Line Segment)"""
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.sqrt((px - x1)**2 + (py - y1)**2)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx*dx + dy*dy)
    t = max(0.0, min(1.0, t))
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)

# --- 3. SIDEBAR CONTROL INTERFACE ---
with st.sidebar:
    st.header("🏗️ ข้อกำหนดสถิตศาสตร์และวัสดุ")
    
    footing_shape_type = st.selectbox(
        "รูปทรงเรขาคณิตของฐานราก:", 
        ["ฐานรากสี่เหลี่ยม (Rectangular Footing)", "ฐานรากสามเหลี่ยม (Triangular Footing)"]
    )
    
    st.subheader("1. คุณสมบัติเสาเข็มและการรับน้ำหนัก")
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        n_piles = st.selectbox("จำนวนเสาเข็มในกลุ่ม:", [2, 3, 4, 5, 6, 8, 9], index=4)
    else:
        st.info("ℹ️ รูปทรงสามเหลี่ยมบังคับใช้กลุ่มเสาเข็ม 3 ต้นตามหลักสถิตศาสตร์")
        n_piles = 3
        
    pile_size = st.number_input("ขนาดหน้าตัด/เส้นผ่านศูนย์กลางเสาเข็ม (เมตร)", value=0.30, min_value=0.15, step=0.05)
    pile_cap = st.number_input("กำลังรับน้ำหนักบรรทุกปลอดภัยของเข็ม - แรงอัด (ตัน/ต้น)", value=30.0, min_value=1.0)
    pile_tension_cap = st.number_input("กำลังรับแรงถอนปลอดภัยของเข็ม - แรงดึง (ตัน/ต้น)", value=10.0, min_value=0.0)
    
    st.subheader("2. น้ำหนักบรรทุกใช้งานจากเสาตอม่อ (Service Loads)")
    DL = st.number_input("น้ำหนักคงที่ปลอดภัย (Dead Load, ตัน)", value=55.0, min_value=0.0)
    LL = st.number_input("น้ำหนักจรปลอดภัย (Live Load, ตัน)", value=30.0, min_value=0.0)
    Mcx = st.number_input("โมเมนต์ดัดใช้งานแกน X (M_cx, ตัน-เมตร)", value=10.0)
    Mcy = st.number_input("โมเมนต์ดัดใช้งานแกน Y (M_cy, ตัน-เมตร)", value=8.0)
    
    st.subheader("3. หน้าตัดตอม่อและพิกัดกำลังวัสดุ")
    cx = st.number_input("ความกว้างเสาตอม่อแกน X (เมตร)", value=0.35, min_value=0.15, step=0.05)
    cy = st.number_input("ความกว้างเสาตอม่อแกน Y (เมตร)", value=0.35, min_value=0.15, step=0.05)
    col_position = st.selectbox("ตำแหน่งเชิงพิกัดของตอม่อ:", ["เสาภายใน (Interior)", "เสาขอบ (Edge)", "เสามุม (Corner)"])
    fc_prime = st.number_input("กำลังอัดประลัยของคอนกรีต fc' (ksc)", value=280, min_value=150, step=10)
    fy = st.selectbox("กำลังครากของเหล็กเสริมหลัก fy (ksc)", [4000, 5000], index=0)
    bar_dia = st.selectbox("ขนาดเส้นผ่านศูนย์กลางเหล็กแกนหลัก (มม.)", [16, 20, 25], index=1)

    st.markdown("---")
    st.subheader("🎛️ 4. ระบบวิเคราะห์ความหนาคอนกรีต")
    thickness_mode = st.radio("ระเบียบวิธีหาความหนา:", ["คำนวณอัตโนมัติ (Auto-Optimize)", "กำหนดความหนาเอง (Manual Override)"])
    
    manual_t = 0.60
    if thickness_mode == "กำหนดความหนาเอง (Manual Override)":
        manual_t_cm = st.number_input("ระบุความหนาฐานราก t (ซม.)", min_value=30, max_value=300, value=65, step=5)
        manual_t = manual_t_cm / 100

# --- 4. FACTORED DESIGN LOAD CONVERSION ---
P_service = DL + LL
P_ultimate = (1.2 * DL) + (1.6 * LL)
load_factor_avg = P_ultimate / P_service if P_service > 0 else 1.4
Mu_cx = Mcx * load_factor_avg
Mu_cy = Mcy * load_factor_avg

phi_shear = 0.75  
phi_flexure = 0.90  
ab_area = (math.pi * (bar_dia / 10) ** 2) / 4  # cm^2

# --- 5. INITIAL IDEAL PILE PATTERN GENERATION ---
S_dist = 3.0 * pile_size
E_dist = max(pile_size, 0.35)

if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
    if n_piles == 2: piles_ideal = [(-S_dist/2, 0), (S_dist/2, 0)]
    elif n_piles == 3: piles_ideal = [(0, S_dist/math.sqrt(3)), (-S_dist/2, -S_dist/(2*math.sqrt(3))), (S_dist/2, -S_dist/(2*math.sqrt(3)))]
    elif n_piles == 4: piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2), (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2)]
    elif n_piles == 5: piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2), (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2), (0, 0)]
    elif n_piles == 6: piles_ideal = [(-S_dist/2, -S_dist), (S_dist/2, -S_dist), (-S_dist/2, 0), (S_dist/2, 0), (-S_dist/2, S_dist), (S_dist/2, S_dist)]
    elif n_piles == 8: piles_ideal = [(-1.5*S_dist, -S_dist/2), (-0.5*S_dist, -S_dist/2), (0.5*S_dist, -S_dist/2), (1.5*S_dist, -S_dist/2), (-1.5*S_dist, S_dist/2), (-0.5*S_dist, S_dist/2), (0.5*S_dist, S_dist/2), (1.5*S_dist, S_dist/2)]
    else: piles_ideal = [(x, y) for x in [-S_dist, 0, S_dist] for y in [-S_dist, 0, S_dist]]
else:
    # พิกัดกลุ่มเข็ม 3 ต้นแบบสามเหลี่ยมด้านเท่าสมบูรณ์รอบจุดศูนย์ถ่วง (0,0)
    piles_ideal = [
        (0, S_dist / math.sqrt(3)),
        (-S_dist / 2, -S_dist / (2 * math.sqrt(3))),
        (S_dist / 2, -S_dist / (2 * math.sqrt(3)))
    ]

# --- 6. FIELD AS-BUILT DEVIATION MANAGEMENT ENGINE ---
st.markdown("### 📍 1. ข้อมูลสำรวจเสาเข็มหนีศูนย์หน้างานจริง (As-Built Field Survey Analysis)")
exp_dev = st.expander("🛠️ ตารางบันทึกค่าการเบี่ยงเบนพิกัดเสาเข็ม (Field Deviation Input)", expanded=False)
deviations = []
with exp_dev:
    c_split1, c_split2, c_split3 = st.columns(3)
    for idx in range(n_piles):
        if idx % 3 == 0: col_target = c_split1
        elif idx % 3 == 1: col_target = c_split2
        else: col_target = c_split3
        with col_target:
            dx_cm = st.number_input(f"เข็ม P{idx+1} หนีศูนย์ ΔX (ซม.)", value=0.0, step=1.0, key=f"x_dev_{idx}")
            dy_cm = st.number_input(f"เข็ม P{idx+1} หนีศูนย์ ΔY (ซม.)", value=0.0, step=1.0, key=f"y_dev_{idx}")
            deviations.append((dx_cm / 100, dy_cm / 100))

# คำนวณพิกัดสัมบูรณ์และการเคลื่อนตัวของจุดศูนย์ถ่วง (True Center of Gravity)
piles_actual = [(piles_ideal[i][0] + deviations[i][0], piles_ideal[i][1] + deviations[i][1]) for i in range(n_piles)]
cg_actual_x = sum(p[0] for p in piles_actual) / n_piles
cg_actual_y = sum(p[1] for p in piles_actual) / n_piles

# ค่าความเยื้องศูนย์กลางเทียบกับตอม่อ (0,0)
ecc_x = 0.0 - cg_actual_x
ecc_y = 0.0 - cg_actual_y

# แปลงระบบพิกัดเสาเข็มเข้าสู่พิกัดสัมพัทธ์รอบจุดศูนย์ถ่วงกลุ่มเข็มจริง
piles_relative = [(p[0] - cg_actual_x, p[1] - cg_actual_y) for p in piles_actual]
I_yy_group = sum(p[0]**2 for p in piles_relative)  # Sum(X^2)
I_xx_group = sum(p[1]**2 for p in piles_relative)  # Sum(Y^2)

# --- 7. DEFINING CONCRETE GEOMETRY BOUNDARIES ---
if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
    B_ft = (max(p[0] for p in piles_ideal) - min(p[0] for p in piles_ideal)) + 2*E_dist
    L_ft = (max(p[1] for p in piles_ideal) - min(p[1] for p in piles_ideal)) + 2*E_dist
    H_geometric = L_ft
    footing_area = B_ft * L_ft
    x_max_edge, x_min_edge = B_ft / 2, -B_ft / 2
    y_max_edge, y_min_edge = L_ft / 2, -L_ft / 2
    concrete_vertices = [
        (x_min_edge, y_min_edge), (x_max_edge, y_min_edge),
        (x_max_edge, y_max_edge), (x_min_edge, y_max_edge)
    ]
else:
    # RULE 1: Enforcing Pure Equilateral Triangle Geometry Formulas
    H_ft = (math.sqrt(3) / 2) * S_dist + (2 * E_dist) # สมการควบคุมตัวแปรตามข้อกำหนด
    B_ft = S_dist + (2 * math.sqrt(3) * E_dist)     # สมการควบคุมตัวแปรตามข้อกำหนด
    
    # ปรับสัดส่วนมิติเพื่อความสมบูรณ์แบบทางเรขาคณิตสามเหลี่ยมด้านเท่าแท้ (ไม่แบนตามรูปทรงเดิม)
    H_geometric = (math.sqrt(3) / 2) * B_ft
    footing_area = 0.5 * B_ft * H_geometric
    
    # พิกัดจุดยอด 3 มุม กระจายตัวสมมาตรรอบจุดศูนย์ถ่วง (0,0) แท้จริง ไม่กลับแกน
    v1_tri = (0, (2 / 3) * H_geometric)
    v2_tri = (-B_ft / 2, -(1 / 3) * H_geometric)
    v3_tri = (B_ft / 2, -(1 / 3) * H_geometric)
    concrete_vertices = [v2_tri, v3_tri, v1_tri]

# --- RULE 4: NET EDGE DISTANCE VALIDATION (SPALLING GUARD) ---
net_min_edge_dist = float('inf')
for p_act in piles_actual:
    px, py = p_act
    p_radius = pile_size / 2
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        d_left = px - p_radius - x_min_edge
        d_right = x_max_edge - (px + p_radius)
        d_bottom = py - p_radius - y_min_edge
        d_top = y_max_edge - (py + p_radius)
        current_min = min(d_left, d_right, d_bottom, d_top)
    else:
        # คำนวณระยะห่างสั้นที่สุดจากจุดเข็มไปยังขอบเฉือนสามเหลี่ยมทั้ง 3 ด้านบนรูปทรงเรขาคณิตจริง
        d_b = py - v2_tri[1] - p_radius
        d_r = point_to_segment_dist(px, py, v3_tri[0], v3_tri[1], v1_tri[0], v1_tri[1]) - p_radius
        d_l = point_to_segment_dist(px, py, v2_tri[0], v2_tri[1], v1_tri[0], v1_tri[1]) - p_radius
        current_min = min(d_b, d_r, d_l)
        
    if current_min < net_min_edge_dist:
        net_min_edge_dist = current_min

if net_min_edge_dist < 0.10:
    st.error(f"🚨 **[As-Built Edge Distance Alert]** ตรวจพบเสาเข็มมีระยะห่างผิวสัมผัสสุทธิถึงขอบคอนกรีตเพียง {net_min_edge_dist*100:.1f} ซม. ซึ่งน้อยกว่าเกณฑ์จำกัดด้านความปลอดภัย (10 ซม.) เสี่ยงต่อการเกิด Concrete Spalling รุนแรงระหว่างก่อสร้าง!")

# --- 8. GEOMETRIC INTERSECTION CALCULATION FOR ADVANCED SHEAR ANALYSIS ---
def get_triangular_width_at_y(target_y):
    """หาความกว้างหน้าตัดประสิทธิผลแปรผันตามพิกัดระนาบ Y"""
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        return B_ft
    if target_y < v2_tri[1] or target_y > v1_tri[1]:
        return 0.0
    return B_ft * (v1_tri[1] - target_y) / H_geometric

def get_triangular_height_at_x(target_x):
    """หาความสูงหน้าตัดประสิทธิผลแปรผันตามพิกัดระนาบ X"""
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        return H_geometric
    if abs(target_x) > B_ft / 2:
        return 0.0
    y_top_limit = v1_tri[1] - (2 * H_geometric / B_ft) * abs(target_x)
    return max(0.0, y_top_limit - v2_tri[1])

# --- 9. RULE 2: SHEAR-FIRST OPTIMIZATION LOOP ENGINE ---
def execute_shear_evaluation_routine(eval_d, eval_t):
    """ฟังก์ชันแกนหลักสำหรับประเมินแรงเฉือนประลัยเพื่อป้อนเข้าลูป Optimization"""
    w_u_footing_weight = 1.2 * (footing_area * eval_t * 2.4)
    P_total_factored = P_ultimate + w_u_footing_weight
    
    Mu_x_total = Mu_cx + (P_total_factored * (-ecc_y))
    Mu_y_total = Mu_cy + (P_total_factored * (-ecc_x))
    
    p_ult_reactions = []
    for prx, pry in piles_relative:
        R_u = (P_total_factored / n_piles) + \
              (Mu_y_total * prx / I_yy_group if I_yy_group > 0 else 0) + \
              (Mu_x_total * pry / I_xx_group if I_xx_group > 0 else 0)
        p_ult_reactions.append(R_u)
        
    # A. CRITICAL PUNCHING SHEAR WITH GEOMETRIC CLIPPING
    b1_box = cx + eval_d
    b2_box = cy + eval_d
    
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        b_0 = 2 * (b1_box + b2_box)
    else:
        p_top, p_bot = cy/2 + eval_d/2, -cy/2 - eval_d/2
        p_right, p_left = cx/2 + eval_d/2, -cx/2 - eval_d/2
        
        w_top_plane = get_triangular_width_at_y(p_top)
        w_bot_plane = get_triangular_width_at_y(p_bot)
        
        len_top_segment = max(0.0, min(p_right, w_top_plane/2) - max(p_left, -w_top_plane/2)) if v2_tri[1] <= p_top <= v1_tri[1] else 0
        len_bot_segment = max(0.0, min(p_right, w_bot_plane/2) - max(p_left, -w_bot_plane/2)) if v2_tri[1] <= p_bot <= v1_tri[1] else 0
        
        y_lim_left = v1_tri[1] - (2 * H_geometric / B_ft) * abs(p_left)
        y_lim_right = v1_tri[1] - (2 * H_geometric / B_ft) * abs(p_right)
        
        len_left_segment = max(0.0, min(p_top, y_lim_left) - max(p_bot, v2_tri[1])) if abs(p_left) <= B_ft/2 else 0
        len_right_segment = max(0.0, min(p_top, y_lim_right) - max(p_bot, v2_tri[1])) if abs(p_right) <= B_ft/2 else 0
        
        b_0 = len_top_segment + len_bot_segment + len_left_segment + len_right_segment

    A_punching_cm2 = b_0 * eval_d * 10000
    
    V_u_punching_kg = 0.0
    for idx, (px, py) in enumerate(piles_actual):
        if abs(px) > (cx/2 + eval_d/2) or abs(py) > (cy/2 + eval_d/2):
            V_u_punching_kg += max(0.0, p_ult_reactions[idx] * 1000)
            
    v_u_punching_stress = V_u_punching_kg / A_punching_cm2 if A_punching_cm2 > 0 else 0.0
    
    beta_ratio = max(cx, cy) / min(cx, cy)
    alpha_s = 40 if col_position == "เสาภายใน (Interior)" else (30 if col_position == "เสาขอบ (Edge)" else 20)
    v_c_1 = 0.27 * (2 + 4 / beta_ratio) * math.sqrt(fc_prime)
    v_c_2 = 0.27 * (alpha_s * (eval_d * 100) / (b_0 * 100) + 2) * math.sqrt(fc_prime)
    v_c_3 = 1.06 * math.sqrt(fc_prime)
    v_c_allow_punching = phi_shear * min(v_c_1, v_c_2, v_c_3)
    
    # B. WIDE BEAM SHEAR WITH VARIABLE TRAIN/TRUNCATED WIDTH
    cut_x_pos = cx/2 + eval_d
    cut_x_neg = -cx/2 - eval_d
    cut_y_pos = cy/2 + eval_d
    cut_y_neg = -cy/2 - eval_d
    
    V_u_wb_x_pos, V_u_wb_x_neg, V_u_wb_y_pos, V_u_wb_y_neg = 0.0, 0.0, 0.0, 0.0
    for idx, (px, py) in enumerate(piles_actual):
        p_force = max(0.0, p_ult_reactions[idx] * 1000)
        if px >= cut_x_pos: V_u_wb_x_pos += p_force
        if px <= cut_x_neg: V_u_wb_x_neg += p_force
        if py >= cut_y_pos: V_u_wb_y_pos += p_force
        if py <= cut_y_neg: V_u_wb_y_neg += p_force
        
    bw_x_pos = get_triangular_height_at_x(cut_x_pos) * 100
    bw_x_neg = get_triangular_height_at_x(cut_x_neg) * 100
    bw_y_pos = get_triangular_width_at_y(cut_y_pos) * 100
    bw_y_neg = get_triangular_width_at_y(cut_y_neg) * 100
    
    v_u_wb_x_pos = V_u_wb_x_pos / (bw_x_pos * eval_d * 100) if bw_x_pos > 0 else 0
    v_u_wb_x_neg = V_u_wb_x_neg / (bw_x_neg * eval_d * 100) if bw_x_neg > 0 else 0
    v_u_wb_y_pos = V_u_wb_y_pos / (bw_y_pos * eval_d * 100) if bw_y_pos > 0 else 0
    v_u_wb_y_neg = V_u_wb_y_neg / (bw_y_neg * eval_d * 100) if bw_y_neg > 0 else 0
    
    v_u_wb_max = max(v_u_wb_x_pos, v_u_wb_x_neg, v_u_wb_y_pos, v_u_wb_y_neg)
    v_c_allow_wb = phi_shear * 0.53 * math.sqrt(fc_prime)
    
    punching_safe = (v_u_punching_stress <= v_c_allow_punching)
    wide_beam_safe = (v_u_wb_max <= v_c_allow_wb)
    
    return punching_safe and wide_beam_safe, v_u_punching_stress, v_c_allow_punching, v_u_wb_max, v_c_allow_wb, p_ult_reactions

# รันลูปขับเคลื่อนความปลอดภัยแรงเฉือนก่อน (Shear-First Optimization Loop)
if thickness_mode == "คำนวณอัตโนมัติ (Auto-Optimize)":
    d_opt = 0.30
    step_safe = False
    while d_opt < 3.0:
        t_opt = d_opt + 0.15
        step_safe, v_up, v_cp, v_uwb, v_cwb, p_ult_out = execute_shear_evaluation_routine(d_opt, t_opt)
        if step_safe:
            break
        d_opt += 0.02
    d_actual = d_opt
    t_actual = math.ceil((d_opt + 0.15) * 20) / 20
else:
    t_actual = manual_t
    d_actual = t_actual - 0.15
    step_safe, v_up, v_cp, v_uwb, v_cwb, p_ult_out = execute_shear_evaluation_routine(d_actual, t_actual)

# เรียกใช้สมดุลน้ำหนักบรรทุกเพื่อหาแรงปฏิกิริยาเสาเข็มภายใต้สถานะใช้งาน (Service Loads)
w_s_footing = footing_area * t_actual * 2.4
P_service_total = P_service + w_s_footing
Ms_x_total = Mcx + (P_service_total * (-ecc_y))
Ms_y_total = Mcy + (P_service_total * (-ecc_x))

pile_service_reactions = []
for prx, pry in piles_relative:
    R_s = (P_service_total / n_piles) + \
          (Ms_y_total * prx / I_yy_group if I_yy_group > 0 else 0) + \
          (Ms_x_total * pry / I_xx_group if I_xx_group > 0 else 0)
    pile_service_reactions.append(R_s)

# --- 10. FLEXURAL DESIGN MODULE WITH RULE 3 SAFETY GUARDS ---
w_u_selfweight = 1.2 * t_actual * 2.4

if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
    Mu_face_x_pos = sum(p_ult_out[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2) - 0.5 * w_u_selfweight * ((B_ft/2 - cx/2)**2) * H_geometric
    Mu_face_y_pos = sum(p_ult_out[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2) - 0.5 * w_u_selfweight * ((H_geometric/2 - cy/2)**2) * B_ft
    w_flex_x = H_geometric * 100
    w_flex_y = B_ft * 100
else:
    Mu_face_x_pos = sum(p_ult_out[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2)
    Mu_face_y_pos = sum(p_ult_out[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2)
    w_flex_x = get_triangular_height_at_x(cx/2) * 100
    w_flex_y = get_triangular_width_at_y(cy/2) * 100

Mu_design_x = max(0.0, Mu_face_x_pos)
Mu_design_y = max(0.0, Mu_face_y_pos)

def design_rebar_logic(Mu_ton_m, width_cm, d_cm, t_cm):
    """วิเคราะห์คำนวณปริมาณเหล็กเส้นและตรวจจับสภาวะวิบัติแบบเปราะ (Over-reinforced Guard)"""
    width_cm = max(width_cm, 30.0)
    As_min = 0.0018 * width_cm * t_cm
    
    if Mu_ton_m <= 0:
        n_bars = max(math.ceil(As_min / ab_area), 6)
        spacing = math.floor((width_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
        return n_bars, spacing, False
        
    Mu_kg_cm = Mu_ton_m * 1000 * 100
    Rn = Mu_kg_cm / (phi_flexure * width_cm * d_cm**2)
    
    beta_1 = 0.85 if fc_prime <= 280 else max(0.65, 0.85 - 0.05 * (fc_prime - 280) / 70)
    rho_b = 0.85 * beta_1 * (fc_prime / fy) * (6120 / (6120 + fy))
    rho_max = 0.75 * rho_b
    Rn_max = rho_max * fy * (1 - 0.59 * rho_max * fy / fc_prime)
    
    if Rn > Rn_max or (2 * Rn) / (0.85 * fc_prime) >= 1.0:
        return 0, 0, True  
        
    rho = (0.85 * fc_prime / fy) * (1 - math.sqrt(1 - (2 * Rn) / (0.85 * fc_prime)))
    if rho > rho_max:
        return 0, 0, True
        
    As_req = max(rho * width_cm * d_cm, As_min)
    n_bars = max(math.ceil(As_req / ab_area), 6)
    spacing = math.floor((width_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
    return n_bars, min(spacing, 45.0), False

n_x_bars, sp_x, crash_x = design_rebar_logic(Mu_design_x, w_flex_x, d_actual*100, t_actual*100)
n_y_bars, sp_y, crash_y = design_rebar_logic(Mu_design_y, w_flex_y, d_actual*100, t_actual*100)
is_structure_crashed = crash_x or crash_y or (not step_safe)

# --- 11. RULE 3: INTERCEPT AND HALT UI BLUEPRINT RENDERING IF CRASHED ---
if is_structure_crashed:
    st.error("🚨 **[CRITICAL FLEXURE ERROR - OVER-REINFORCED SECTION]** หน้าตัดคอนกรีตเกิดสภาวะแรงดัดเกินพิกัดควบคุมวิกฤต หรือแรงเฉือนไม่สามารถหาค่าที่ปลอดภัยได้ โครงสร้างมีความเสี่ยงขั้นวิบัติพังทลายแบบเปราะ! ระบบได้ทำการระงับการวาดแผ่นแบบพิมพ์เขียวเพื่อความปลอดภัยทางวิศวกรรม กรุณาเพิ่มความหนาฐานราก (t) ที่แถบควบคุมด้านซ้ายเพื่อกระจายแรงใหม่")
else:
    st.success("✅ **[Structural Integrity Passed]** การตรวจสอบหน่วยแรงเฉือนและปริมาณเหล็กเสริมหลักผ่านเกณฑ์ความปลอดภัยขั้นสูงสุด")
    
    # --- 12. 2D CAD-LIKE BLUEPRINT DISPLAY (MATPLOTLIB) ---
    st.markdown("### 📊 2. แบบวิศวกรรมสถาปัตยกรรมฐานราก (2D Engineering Blueprint)")
    fig, (ax_plan, ax_sec) = plt.subplots(1, 2, figsize=(14, 5.5))
    
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        footing_shape_patch = patches.Rectangle((x_min_edge, y_min_edge), B_ft, H_geometric, linewidth=2.5, edgecolor='#2c3e50', facecolor='#eaeded', zorder=1)
        ax_plan.add_patch(footing_shape_patch)
        ax_plan.set_xlim(x_min_edge - 0.4, x_max_edge + 0.4)
        ax_plan.set_ylim(y_min_edge - 0.4, y_max_edge + 0.4)
    else:
        # พล็อตสามเหลี่ยมด้านเท่าแท้สมบูรณ์แบบไม่บิดเบี้ยวตามสัดส่วนคณิตศาสตร์วิศวกรรม
        footing_shape_patch = patches.Polygon(concrete_vertices, closed=True, linewidth=2.5, edgecolor='#2c3e50', facecolor='#eaeded', zorder=1)
        ax_plan.add_patch(footing_shape_patch)
        ax_plan.set_xlim(-B_ft/2 - 0.4, B_ft/2 + 0.4)
        ax_plan.set_ylim(-H_geometric/3 - 0.4, 2*H_geometric/3 + 0.4)
        
    ax_plan.add_patch(patches.Rectangle((-cx/2, -cy/2), cx, cy, linewidth=1.8, edgecolor='#e74c3c', facecolor='#f1948a', zorder=4))
    ax_plan.scatter(cg_actual_x, cg_actual_y, color='#f39c12', marker='X', s=120, label='True C.G.', zorder=5)
    
    for idx, (px, py) in enumerate(piles_actual):
        pile_draw = patches.Circle((px, py), pile_size/2, linewidth=1.5, edgecolor='#34495e', facecolor='#7f8c8d', alpha=0.9, zorder=3)
        ax_plan.add_patch(pile_draw)
        ax_plan.text(px, py, f"P{idx+1}", ha='center', va='center', color='white', fontsize=9, fontweight='bold', zorder=4)
        
    ax_plan.set_aspect('equal')
    ax_plan.grid(True, linestyle=':', alpha=0.6)
    ax_plan.set_title("แปลนแสดงตำแหน่งกลุ่มเสาเข็มและตอม่อ (Top View)")
    
    ax_sec.add_patch(patches.Rectangle((-B_ft/2, 0), B_ft, t_actual, linewidth=2, edgecolor='#2c3e50', facecolor='#f2f4f4'))
    ax_sec.plot([-B_ft/2 + 0.075, B_ft/2 - 0.075], [0.075, 0.075], color='#1f618d', linewidth=3.0, label='Bottom Rebar')
    ax_sec.text(0, t_actual/2, f"ความหนา t = {t_actual*100:.0f} cm\nเหล็กหลักแกน X: DB{bar_dia} @ {sp_x:.0f} cm\nเหล็กหลักแกน Y: DB{bar_dia} @ {sp_y:.0f} cm", ha='center', va='center', color='#232b2b', fontsize=9, fontweight='bold')
    ax_sec.set_xlim(-B_ft/2 - 0.2, B_ft/2 + 0.2)
    ax_sec.set_ylim(-0.1, t_actual + 0.4)
    ax_sec.set_aspect('equal')
    ax_sec.axis('off')
    ax_sec.set_title("รูปตัดแสดงรายละเอียดการจัดเหล็กเสริม (Section View)")
    st.pyplot(fig)

# --- 13. INTERACTIVE MULTI-TAB MATRIX OUTPUTS ---
tab1, tab2, tab3 = st.tabs(["📝 สรุปพิกัดความปลอดภัยสถิตศาสตร์", "🎮 แบบจำลองพิกัด 3D Solid Model Mesh", "📋 รายการคำนวณและหน่วยแรงเชิงเลข"])

with tab1:
    st.subheader("📋 บทสรุปมิติรูปทรงวิศวกรรม")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("ความหนารวมฐานรากที่เลือกใช้ (t)", f"{t_actual*100:.1f} ซม.")
    with col_m2:
        st.metric("ระยะลึกประสิทธิผลหน้าตัด (d)", f"{d_actual*100:.1f} ซม.")
    with col_m3:
        st.metric("เนื้อที่ผิวคอนกรีตฐานราก", f"{footing_area:.3f} ตร.ม.")
        
    if not is_structure_crashed:
        st.markdown("#### 🧾 ใบรายการวัสดุและระยะการจัดเหล็กเสริมเหล็กเส้น")
        st.info(f"🔹 **เหล็กตะแกรงล่างหลัก (แกน X):** DB{bar_dia} มม. จำนวน **{n_x_bars}** เส้น จัดระยะ Spacing @ **{sp_x:.0f}** ซม.\n\n"
                f"🔹 **เหล็กตะแกรงล่างหลัก (แกน Y):** DB{bar_dia} มม. จำนวน **{n_y_bars}** เส้น จัดระยะ Spacing @ **{sp_y:.0f}** ซม.")

with tab2:
    st.subheader("🌐 Interactive 3D Real-Scale Boundary Solid Mesh")
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        mesh_x = [x_min_edge, x_max_edge, x_max_edge, x_min_edge, x_min_edge, x_max_edge, x_max_edge, x_min_edge]
        mesh_y = [y_min_edge, y_min_edge, y_max_edge, y_max_edge, y_min_edge, y_min_edge, y_max_edge, y_max_edge]
        mesh_z = [0, 0, 0, 0, t_actual, t_actual, t_actual, t_actual]
        i_idx = [0, 0, 4, 4, 0, 1, 2, 3, 0, 1, 5, 4]
        j_idx = [1, 2, 5, 6, 4, 5, 6, 7, 3, 2, 6, 7]
        k_idx = [2, 3, 6, 7, 1, 2, 3, 0, 4, 5, 2, 3]
    else:
        # พิกัดโครงข่าย Prism 3 มิติสำหรับสามเหลี่ยมด้านเท่าแท้หลังการปรับอัตราส่วนสัดส่วนสัมพันธ์
        mesh_x = [v2_tri[0], v3_tri[0], v1_tri[0], v2_tri[0], v3_tri[0], v1_tri[0]]
        mesh_y = [v2_tri[1], v3_tri[1], v1_tri[1], v2_tri[1], v3_tri[1], v1_tri[1]]
        mesh_z = [0, 0, 0, t_actual, t_actual, t_actual]
        i_idx = [0, 0, 3, 3, 0, 1, 4, 3, 1, 2, 5, 4]
        j_idx = [1, 2, 4, 5, 3, 4, 5, 5, 2, 0, 3, 3]
        k_idx = [2, 0, 5, 3, 1, 2, 1, 4, 0, 1, 4, 5]
        
    fig_3d = go.Figure(data=[
        go.Mesh3d(
            x=mesh_x, y=mesh_y, z=mesh_z,
            i=i_idx, j=j_idx, k=k_idx,
            opacity=0.7, color='#2980b9', name='Footing Concrete Body'
        )
    ])
    fig_3d.update_layout(
        scene=dict(xaxis_title='X (เมตร)', yaxis_title='Y (เมตร)', zaxis_title='Z Thickness (เมตร)'),
        margin=dict(l=0, r=0, b=0, t=40)
    )
    st.plotly_chart(fig_3d, use_container_width=True)

with tab3:
    st.subheader("📊 ตารางวิเคราะห์หน่วยแรงเฉือนประลัยควบคุม (Critical Shear Sections)")
    df_shear_matrix = pd.DataFrame({
        "รายการดักจับแรงเฉือนวิกฤต": ["Punching Shear (แรงเฉือนทะลุรอบขอบตอม่อ)", "Wide Beam Shear (แรงเฉือนคานกว้างหน้าตัดแปรผัน)"],
        "หน่วยแรงเกิดขึ้นจริง (v_u)": [v_up, v_uwb],
        "พิกัดกำลังคอนกรีตที่ยอมให้ (phi * v_c)": [v_cp, v_cwb],
        "สถานะความปลอดภัย": ["ผ่านเกณฑ์ (Passed)" if v_up<=v_cp else "วิบัติ (FAILED)", "ผ่านเกณฑ์ (Passed)" if v_uwb<=v_cwb else "วิบัติ (FAILED)"]
    })
    st.dataframe(df_shear_matrix, use_container_width=True, hide_index=True)
    
    st.subheader("📊 ตารางสรุปแรงปฏิกิริยากระจายลงเสาเข็มรายต้น (Pile Reactions)")
    df_pile_output = pd.DataFrame({
        "เสาเข็มลำดับ": [f"เสาเข็มต้นที่ {i+1}" for i in range(n_piles)],
        "พิกัด X สัมบูรณ์ (ม.)": [p[0] for p in piles_actual],
        "พิกัด Y สัมบูรณ์ (ม.)": [p[1] for p in piles_actual],
        "แรงใช้งานจริง Service Load (ตัน)": pile_service_reactions,
        "แรงประลัยรวมเกณฑ์ Ultimate Load (ตัน)": p_ult_out
    })
    st.dataframe(
        df_pile_output.style.format({
            "พิกัด X สัมบูรณ์ (ม.)": "{:.3f}",
            "พิกัด Y สัมบูรณ์ (ม.)": "{:.3f}",
            "แรงใช้งานจริง Service Load (ตัน)": "{:.2f}",
            "แรงประลัยรวมเกณฑ์ Ultimate Load (ตัน)": "{:.2f}"
        }), use_container_width=True, hide_index=True
    )
