import streamlit as st
import math
import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import plotly.graph_objects as go

# --- 1. INITIAL APP CONFIGURATION & THAI FONT ENGINE ---
st.set_page_config(page_title="Enterprise Footing Suite V6.2", page_icon="📐", layout="wide")

st.title("📐 Enterprise Footing Suite (V6.2 - Professional Production Edition)")
st.markdown("### ระบบสถาปัตยกรรมวิเคราะห์และออกแบบฐานรากขั้นสูง ปรองดองสถิตศาสตร์และสถาปัตยกรรมดิจิทัล")
st.markdown("---")

# ระบบแก้บั๊กตัวอักษรภาษาไทยแสดงผลเป็นรูปสี่เหลี่ยม (Font Tofu Bug Fix)
@st.cache_data(show_spinner=False)
def initialize_thai_font_system():
    """ดาวน์โหลดและลงทะเบียนฟอนต์ภาษาไทยสากลจาก Google Fonts เพื่อรองรับการทำ Cloud Deployment"""
    font_url = "https://github.com/google/fonts/raw/main/ofl/kanit/Kanit-Regular.ttf"
    font_name = "Kanit-Regular.ttf"
    
    if not os.path.exists(font_name):
        try:
            response = requests.get(font_url, timeout=10)
            if response.status_code == 200:
                with open(font_name, "wb") as f:
                    f.write(response.content)
        except Exception as e:
            st.sidebar.warning(f"⚠️ ระบบไม่สามารถดึงฟอนต์ภายนอกได้เนื่องจากข้อจำกัดเครือข่าย: {e}")
            
    if os.path.exists(font_name):
        try:
            fm.fontManager.addfont(font_name)
            registered_font = fm.FontProperties(fname=font_name).get_name()
            plt.rcParams['font.family'] = registered_font
            plt.rcParams['axes.unicode_minus'] = False  
            return registered_font
        except Exception:
            pass
    return "sans-serif"

# เปิดใช้งานระบบฟอนต์ภาษาไทยสากล
current_thai_font = initialize_thai_font_system()

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
        ["ฐานรากสามเหลี่ยมตัดมุม (Truncated Triangular)", "ฐานรากสี่เหลี่ยม (Rectangular Footing)"]
    )
    
    st.subheader("1. คุณสมบัติเสาเข็มและการรับน้ำหนัก")
    if footing_shape_type == "ฐานรากสามเหลี่ยมตัดมุม (Truncated Triangular)":
        st.info("ℹ️ รูปทรงสามเหลี่ยมตัดมุมตามตำรา บังคับใช้กลุ่มเสาเข็ม 3 ต้น")
        n_piles = 3
    else:
        n_piles = st.selectbox("จำนวนเสาเข็มในกลุ่ม:", [2, 3, 4, 5, 6, 8, 9], index=2)
        
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
    elif n_piles == 3: piles_ideal = [(-S_dist, 0), (0, 0), (S_dist, 0)]
    elif n_piles == 4: piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2), (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2)]
    elif n_piles == 5: piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2), (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2), (0, 0)]
    elif n_piles == 6: piles_ideal = [(-S_dist/2, -S_dist), (S_dist/2, -S_dist), (-S_dist/2, 0), (S_dist/2, 0), (-S_dist/2, S_dist), (S_dist/2, S_dist)]
    elif n_piles == 8: piles_ideal = [(-1.5*S_dist, -S_dist/2), (-0.5*S_dist, -S_dist/2), (0.5*S_dist, -S_dist/2), (1.5*S_dist, -S_dist/2), (-1.5*S_dist, S_dist/2), (-0.5*S_dist, S_dist/2), (0.5*S_dist, S_dist/2), (1.5*S_dist, S_dist/2)]
    else: piles_ideal = [(x, y) for x in [-S_dist, 0, S_dist] for y in [-S_dist, 0, S_dist]]
else:
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

piles_actual = [(piles_ideal[i][0] + deviations[i][0], piles_ideal[i][1] + deviations[i][1]) for i in range(n_piles)]
cg_actual_x = sum(p[0] for p in piles_actual) / n_piles
cg_actual_y = sum(p[1] for p in piles_actual) / n_piles

ecc_x = 0.0 - cg_actual_x
ecc_y = 0.0 - cg_actual_y

piles_relative = [(p[0] - cg_actual_x, p[1] - cg_actual_y) for p in piles_actual]
I_yy_group = sum(p[0]**2 for p in piles_relative)  
I_xx_group = sum(p[1]**2 for p in piles_relative)  

# --- 7. DEFINING CONCRETE GEOMETRY BOUNDARIES ---
if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
    B_ft = (max(p[0] for p in piles_ideal) - min(p[0] for p in piles_ideal)) + 2*E_dist
    L_ft = (max(p[1] for p in piles_ideal) - min(p[1] for p in piles_ideal)) + 2*E_dist
    footing_area = B_ft * L_ft
    x_max_edge, x_min_edge = B_ft / 2, -B_ft / 2
    y_max_edge, y_min_edge = L_ft / 2, -L_ft / 2
    concrete_vertices = [
        (x_min_edge, y_min_edge), (x_max_edge, y_min_edge),
        (x_max_edge, y_max_edge), (x_min_edge, y_max_edge)
    ]
else:
    y_p1 = S_dist / math.sqrt(3)
    y_p23 = -S_dist / (2 * math.sqrt(3))
    
    v1_tri = (-E_dist / math.sqrt(3), y_p1 + E_dist) 
    v2_tri = (E_dist / math.sqrt(3), y_p1 + E_dist)  
    v3_tri = (S_dist / 2 + 2 * E_dist / math.sqrt(3), y_p23) 
    v4_tri = (S_dist / 2 + E_dist / math.sqrt(3), y_p23 - E_dist) 
    v5_tri = (-S_dist / 2 - E_dist / math.sqrt(3), y_p23 - E_dist) 
    v6_tri = (-S_dist / 2 - 2 * E_dist / math.sqrt(3), y_p23) 
    
    concrete_vertices = [v1_tri, v2_tri, v3_tri, v4_tri, v5_tri, v6_tri]
    footing_area = (math.sqrt(3)/4)*(S_dist**2) + (3*S_dist*E_dist) + (2*math.sqrt(3)*(E_dist**2))

# ตรวจสอบระยะขอบเสาเข็มที่สั้นที่สุด (Net Edge Distance Validation)
net_min_edge_dist = float('inf')
segments = []
for i in range(len(concrete_vertices)):
    segments.append((concrete_vertices[i], concrete_vertices[(i+1)%len(concrete_vertices)]))

for p_act in piles_actual:
    px, py = p_act
    p_radius = pile_size / 2
    current_min = float('inf')
    for seg in segments:
        d_seg = point_to_segment_dist(px, py, seg[0][0], seg[0][1], seg[1][0], seg[1][1]) - p_radius
        if d_seg < current_min:
            current_min = d_seg
    if current_min < net_min_edge_dist:
        net_min_edge_dist = current_min

if net_min_edge_dist < 0.10:
    st.error(f"🚨 **[As-Built Edge Distance Alert]** ตรวจพบเสาเข็มมีระยะห่างผิวสัมผัสสุทธิถึงขอบคอนกรีตเพียง {net_min_edge_dist*100:.1f} ซม. ซึ่งน้อยกว่าเกณฑ์จำกัดด้านความปลอดภัย (10 ซม.)!")

# --- 8. GEOMETRIC INTERSECTION CALCULATION FOR ADVANCED SHEAR ANALYSIS ---
def get_triangular_width_at_y(target_y):
    if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
        return B_ft
    y_top_bound = S_dist / math.sqrt(3) + E_dist
    y_bot_bound = -S_dist / (2 * math.sqrt(3)) - E_dist
    if target_y > y_top_bound or target_y < y_bot_bound:
        return 0.0
    if target_y >= -S_dist / (2 * math.sqrt(3)):
        x_inter = (S_dist / math.sqrt(3) + 2 * E_dist - target_y) / math.sqrt(3)
    else:
        x_inter = (2 / math.sqrt(3)) * (S_dist / math.sqrt(3) + E_dist + 0.5 * target_y)
    return 2 * max(0.0, x_inter)

# --- 9. SHEAR EVALUATION ROUTINE ENGINE ---
def execute_shear_evaluation_routine(eval_d, eval_t):
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
        
    # A. PUNCHING SHEAR ANALYSIS
    b1_box = cx + eval_d
    b2_box = cy + eval_d
    b_0 = 2 * (b1_box + b2_box)
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
    
    # B. WIDE BEAM SHEAR WITH VARIABLE WIDTH
    cut_y_pos = cy/2 + eval_d
    V_u_wb = 0.0
    for idx, (px, py) in enumerate(piles_actual):
        if py >= cut_y_pos:
            V_u_wb += max(0.0, p_ult_reactions[idx] * 1000)
            
    bw_y = get_triangular_width_at_y(cut_y_pos) * 100
    v_u_wb_max = V_u_wb / (bw_y * eval_d * 100) if bw_y > 0 else 0
    v_c_allow_wb = phi_shear * 0.53 * math.sqrt(fc_prime)
    
    punching_safe = (v_u_punching_stress <= v_c_allow_punching)
    wide_beam_safe = (v_u_wb_max <= v_c_allow_wb)
    
    return punching_safe and wide_beam_safe, v_u_punching_stress, v_c_allow_punching, v_u_wb_max, v_c_allow_wb, p_ult_reactions

# ลูปขับเคลื่อนความปลอดภัยแรงเฉือน (Shear-First Optimization Loop)
if thickness_mode == "คำนวณอัตโนมัติ (Auto-Optimize)":
    d_opt = 0.30
    step_safe = False
    p_ult_out = [0.0] * n_piles
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

# --- 10. FLEXURAL DESIGN MODULE (CRITICAL FACE MOMENT) ---
if footing_shape_type == "ฐานรากสี่เหลี่ยม (Rectangular Footing)":
    Mu_x_top = sum(p_ult_out[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2)
    Mu_x_bot = sum(p_ult_out[i] * (-cy/2 - p[1]) for i, p in enumerate(piles_actual) if p[1] < -cy/2)
    Mu_x = max(abs(Mu_x_top), abs(Mu_x_bot))
    
    Mu_y_right = sum(p_ult_out[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2)
    Mu_y_left = sum(p_ult_out[i] * (-cx/2 - p[0]) for i, p in enumerate(piles_actual) if p[0] < -cx/2)
    Mu_y = max(abs(Mu_y_right), abs(Mu_y_left))
    
    if Mu_x >= Mu_y:
        Mu_design = Mu_x
        w_flex = B_ft * 100
    else:
        Mu_design = Mu_y
        w_flex = L_ft * 100
else:
    Mu_top = sum(p_ult_out[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2)
    Mu_bot = sum(p_ult_out[i] * (-cy/2 - p[1]) for i, p in enumerate(piles_actual) if p[1] < -cy/2)
    
    if abs(Mu_top) >= abs(Mu_bot):
        Mu_design = abs(Mu_top)
        w_flex = get_triangular_width_at_y(cy/2) * 100
    else:
        Mu_design = abs(Mu_bot)
        w_flex = get_triangular_width_at_y(-cy/2) * 100

def design_rebar_logic(Mu_ton_m, width_cm, d_cm, t_cm):
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
    if Rn > (rho_max * fy * (1 - 0.59 * rho_max * fy / fc_prime)):
        return 0, 0, True
    rho = (0.85 * fc_prime / fy) * (1 - math.sqrt(1 - (2 * Rn) / (0.85 * fc_prime)))
    As_req = max(rho * width_cm * d_cm, As_min)
    n_bars = max(math.ceil(As_req / ab_area), 6)
    spacing = math.floor((width_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
    return n_bars, min(spacing, 45.0), False

n_main_bars, sp_main, crash_f = design_rebar_logic(Mu_design, w_flex, d_actual*100, t_actual*100)
is_structure_crashed = crash_f or (not step_safe)

# --- 11. BLUEPRINT RENDERING ---
if is_structure_crashed:
    st.error("🚨 **[CRITICAL ERROR]** โครงสร้างรับหน่วยแรงไม่ผ่านเกณฑ์การคำนวณ กรุณาเพิ่มความหนาฐานรากในแถบควบคุม!")
else:
    st.success("✅ **[Structural Integrity Passed]** ผ่านเกณฑ์รูปทรงและสถิตศาสตร์ทางวิศวกรรมเรียบร้อยแล้ว")
    
    st.markdown("### 📊 2. แบบวิศวกรรมสถาปัตยกรรมฐานราก (2D Engineering Blueprint)")
    fig, (ax_plan, ax_sec) = plt.subplots(1, 2, figsize=(14, 6))
    
    # วาดแปลนฐานรากคอนกรีต
    footing_shape_patch = patches.Polygon(concrete_vertices, closed=True, linewidth=2.5, edgecolor='#2c3e50', facecolor='#eaeded', zorder=1)
    ax_plan.add_patch(footing_shape_patch)
    
    x_coords = [v[0] for v in concrete_vertices]
    y_coords = [v[1] for v in concrete_vertices]
    ax_plan.set_xlim(min(x_coords) - 0.3, max(x_coords) + 0.3)
    ax_plan.set_ylim(min(y_coords) - 0.3, max(y_coords) + 0.3)
        
    ax_plan.add_patch(patches.Rectangle((-cx/2, -cy/2), cx, cy, linewidth=1.8, edgecolor='#e74c3c', facecolor='#f1948a', zorder=4))
    ax_plan.scatter(cg_actual_x, cg_actual_y, color='#f39c12', marker='X', s=120, label='True C.G.', zorder=5)
    
    for idx, (px, py) in enumerate(piles_actual):
        pile_draw = patches.Circle((px, py), pile_size/2, linewidth=1.5, edgecolor='#34495e', facecolor='#7f8c8d', alpha=0.9, zorder=3)
        ax_plan.add_patch(pile_draw)
        ax_plan.text(px, py, f"P{idx+1}", ha='center', va='center', color='white', fontsize=9, fontweight='bold', zorder=4)
        
    ax_plan.set_aspect('equal')
    ax_plan.grid(True, linestyle=':', alpha=0.6)
    ax_plan.set_title("แปลนแสดงตำแหน่งฐานรากและเสาเข็มสำรวจจริง (Top View)", fontsize=11, fontweight='bold')
    
    # รูปตัดและรายละเอียดการจัดเหล็กเสริม
    sec_w = max(x_coords) - min(x_coords)
    ax_sec.add_patch(patches.Rectangle((-sec_w/2, 0), sec_w, t_actual, linewidth=2, edgecolor='#2c3e50', facecolor='#f2f4f4'))
    ax_sec.plot([-sec_w/2 + 0.075, sec_w/2 - 0.075], [0.075, 0.075], color='#1f618d', linewidth=3.0, label='Bottom Rebar')
    ax_sec.text(0, t_actual/2, f"ความหนา t = {t_actual*100:.0f} cm\nเหล็กเสริมหลักตะแกรงล่าง:\nDB{bar_dia} มม. @ {sp_main:.0f} cm\nจำนวนรวม {n_main_bars} เส้น", ha='center', va='center', color='#232b2b', fontsize=10, fontweight='bold')
    ax_sec.set_xlim(-sec_w/2 - 0.2, sec_w/2 + 0.2)
    ax_sec.set_ylim(-0.1, t_actual + 0.4)
    ax_sec.set_aspect('equal')
    ax_sec.axis('off')
    ax_sec.set_title("รูปตัดแสดงรายละเอียดการเสริมเหล็กวิเคราะห์ (Section View)", fontsize=11, fontweight='bold')
    st.pyplot(fig)

# --- 12. INTERACTIVE MULTI-TAB MATRIX OUTPUTS ---
tab1, tab2, tab3 = st.tabs(["📝 สรุปพิกัดความปลอดภัยสถิตศาสตร์", "🌐 แบบจำลองพิกัด 3D Solid Model Mesh", "📋 รายการคำนวณและหน่วยแรงเชิงเลข"])

with tab1:
    st.subheader("📋 บทสรุปมิติรูปทรงวิศวกรรม")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("ความหนารวมฐานรากที่เลือกใช้ (t)", f"{t_actual*100:.1f} ซม.")
    with col_m2:
        st.metric("ระยะลึกประสิทธิผลหน้าตัด (d)", f"{d_actual*100:.1f} ซม.")
    with col_m3:
        st.metric("เนื้อที่ผิวคอนกรีตจริงฐานราก", f"{footing_area:.3f} ตร.ม.")

with tab2:
    st.subheader("🌐 Interactive 3D Solid Model Mesh (Advanced Parametric View)")
    
    # ฟังก์ชันช่วยสร้างโครงข่าย 3D Prism สำหรับฐานราก เสาตอม่อ และเสาเข็ม
    def create_3d_prism_trace(vertices, z_start, z_end, face_color, opacity, name, show_legend=True):
        n = len(vertices)
        x_coords = [v[0] for v in vertices] * 2
        y_coords = [v[1] for v in vertices] * 2
        z_coords = [z_start] * n + [z_end] * n
        
        i_idx, j_idx, k_idx = [], [], []
        # แผ่นพื้นล่าง (Bottom Cap)
        for idx in range(1, n - 1):
            i_idx.append(0); j_idx.append(idx); k_idx.append(idx + 1)
        # แผ่นพื้นบน (Top Cap)
        for idx in range(1, n - 1):
            i_idx.append(n); j_idx.append(n + idx + 1); k_idx.append(n + idx)
        # ผิวด้านข้าง (Side Walls)
        for idx in range(n):
            next_idx = (idx + 1) % n
            i_idx.append(idx); j_idx.append(next_idx); k_idx.append(n + next_idx)
            i_idx.append(idx); j_idx.append(n + next_idx); k_idx.append(n + idx)
            
        return go.Mesh3d(
            x=x_coords, y=y_coords, z=z_coords, 
            i=i_idx, j=j_idx, k=k_idx, 
            color=face_color, opacity=opacity, 
            name=name, showlegend=show_legend
        )

    def draw_3d_wireframe_lines(fig, vertices, z_start, z_end, line_color='#2c3e50'):
        n = len(vertices)
        # วงขอบล่าง
        bx = [v[0] for v in vertices] + [vertices[0][0]]
        by = [v[1] for v in vertices] + [vertices[0][1]]
        bz = [z_start] * (n + 1)
        fig.add_trace(go.Scatter3d(x=bx, y=by, z=bz, mode='lines', line=dict(color=line_color, width=2.5), showlegend=False))
        # วงขอบบน
        tx = [v[0] for v in vertices] + [vertices[0][0]]
        ty = [v[1] for v in vertices] + [vertices[0][1]]
        tz = [z_end] * (n + 1)
        fig.add_trace(go.Scatter3d(x=tx, y=ty, z=tz, mode='lines', line=dict(color=line_color, width=2.5), showlegend=False))
        # เส้นแนวตั้งเชื่อมมุม
        for v in vertices:
            fig.add_trace(go.Scatter3d(x=[v[0], v[0]], y=[v[1], v[1]], z=[z_start, z_end], mode='lines', line=dict(color=line_color, width=2), showlegend=False))

    fig_3d = go.Figure()

    # A) พล็อตโมเดล 3มิติ: ก้อนคอนกรีตฐานราก (Footing Body Mesh)
    footing_trace = create_3d_prism_trace(concrete_vertices, 0, t_actual, '#2ecc71', 0.65, 'ฐานรากคอนกรีต (Footing)')
    fig_3d.add_trace(footing_trace)
    draw_3d_wireframe_lines(fig_3d, concrete_vertices, 0, t_actual, '#1e8449')

    # B) พล็อตโมเดล 3มิติ: เสาตอม่อ (3D Column Box Mesh)
    column_height = 0.60  # ความสูงต่อยอดตอม่อจำลองขึ้นจากผิวบนฐานราก
    column_vertices = [
        (-cx/2, -cy/2), (cx/2, -cy/2), 
        (cx/2, cy/2), (-cx/2, cy/2)
    ]
    column_trace = create_3d_prism_trace(column_vertices, t_actual, t_actual + column_height, '#e74c3c', 0.85, 'เสาตอม่อตอม่อ (Column Stub)')
    fig_3d.add_trace(column_trace)
    draw_3d_wireframe_lines(fig_3d, column_vertices, t_actual, t_actual + column_height, '#922b21')

    # C) พล็อตโมเดล 3มิติ: กลุ่มเสาเข็มจริง (3D Pile Cylinders) ยื่นลงใต้ดิน Z=0 ถึง Z=-1.50 เมตร
    pile_embedded_depth = 1.50
    for idx, (px, py) in enumerate(piles_actual):
        # สร้างพิกัดรูปทรงกระบอก 8 เหลี่ยมจำลองเส้นรอบรูปเสาเข็ม圓
        segments_count = 8
        pile_nodes = []
        radius = pile_size / 2
        for s in range(segments_count):
            angle = s * (2 * math.pi / segments_count)
            pile_nodes.append((px + radius * math.cos(angle), py + radius * math.sin(angle)))
            
        pile_trace = create_3d_prism_trace(
            pile_nodes, -pile_embedded_depth, 0, '#34495e', 0.80, 
            'กลุ่มเสาเข็มจริง (As-Built Piles)', show_legend=(idx == 0)
        )
        fig_3d.add_trace(pile_trace)
        draw_3d_wireframe_lines(fig_3d, pile_nodes, -pile_embedded_depth, 0, '#2c3e50')

    # ปรับแต่งมุมมองพิกัดและแกน Layout ให้สมสัดส่วนสถิตศาสตร์ (Aspect Ratio Scale Metric)
    fig_3d.update_layout(
        scene=dict(
            xaxis=dict(title='แกน X (เมตร)', gridcolor='rgb(220,220,220)'),
            yaxis=dict(title='แกน Y (เมตร)', gridcolor='rgb(220,220,220)'),
            zaxis=dict(title='แกน Z ระดับความสูง (เมตร)', gridcolor='rgb(220,220,220)'),
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=30),
        legend=dict(yanchor="top", y=0.95, xanchor="left", x=0.05)
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
    
    st.subheader("📊 ตารางสรุปแรงปฏิกิริยากระจายลงเสาเข็มรายต้น (Pile Reactions & Tension Analysis)")
    
    pile_status = []
    for r_s in pile_service_reactions:
        if r_s > pile_cap:
            pile_status.append("❌ แรงอัดเกินพิกัดบรรทุกปลอดภัย")
        elif r_s < 0 and abs(r_s) > pile_tension_cap:
            pile_status.append("❌ แรงถอนเกินพิกัดปลอดภัย")
        elif r_s < 0:
            pile_status.append("⚠️ มีแรงดึงสุทธิ (Tension Pass)")
        else:
            pile_status.append("✅ ผ่านเกณฑ์ปกติ (Compression Pass)")

    df_pile_output = pd.DataFrame({
        "เสาเข็มลำดับ": [f"เสาเข็มต้นที่ {i+1}" for i in range(n_piles)],
        "พิกัด X สัมบูรณ์ (ม.)": [p[0] for p in piles_actual],
        "พิกัด Y สัมบูรณ์ (ม.)": [p[1] for p in piles_actual],
        "แรงใช้งานจริง Service Load (ตัน)": pile_service_reactions,
        "แรงประลัยรวมเกณฑ์ Ultimate Load (ตัน)": p_ult_out,
        "สถานะวิศวกรรมปฏิกิริยา": pile_status
    })
    
    def highlight_pile_rows(val):
        if "❌" in val:
            return 'background-color: #fad1d1; color: #721c24; font-weight: bold;'
        elif "⚠️" in val:
            return 'background-color: #fff3cd; color: #856404;'
        return 'background-color: #d4edda; color: #155724;'

    st.dataframe(df_pile_output.style.map(highlight_pile_rows, subset=['สถานะวิศวกรรมปฏิกิริ']), use_container_width=True, hide_index=True)
