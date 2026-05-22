import streamlit as st
import math
import os
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import plotly.graph_objects as go

# =========================================================================
# SYSTEM STABILITY & FONT MANAGEMENT
# =========================================================================
st.set_page_config(page_title="Enterprise Footing Suite V8.1", page_icon="📐", layout="wide")

@st.cache_resource(show_spinner=False)
def initialize_thai_font_system():
    font_dir = "fonts"
    font_name = "Kanit-Regular.ttf"
    font_path = os.path.join(font_dir, font_name)
    if not os.path.exists(font_dir): os.makedirs(font_dir, exist_ok=True)
    if not os.path.exists(font_path):
        try:
            font_url = "https://github.com/google/fonts/raw/main/ofl/kanit/Kanit-Regular.ttf"
            response = requests.get(font_url, timeout=5)
            if response.status_code == 200:
                with open(font_path, "wb") as f: f.write(response.content)
        except Exception: pass
    if os.path.exists(font_path):
        try:
            fm.fontManager.addfont(font_path)
            registered_font = fm.FontProperties(fname=font_path).get_name()
            plt.rcParams['font.family'] = registered_font
            plt.rcParams['axes.unicode_minus'] = False  
            return registered_font
        except Exception: pass
    return "sans-serif"

current_thai_font = initialize_thai_font_system()

# =========================================================================
# HELPER FUNCTIONS (MATH, GEOMETRY & VISUALIZATION)
# =========================================================================
def polygon_area(vertices):
    """คำนวณพื้นที่รูปหลายเหลี่ยมใดๆ (Polygon Area)"""
    n = len(vertices)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2.0

def compute_polygon_advanced_properties(vertices):
    """คำนวณหาจุด C.G. และ Moment of Inertia แบบละเอียดรองรับรูปทรงอิสระ (Green's Theorem)"""
    n = len(vertices)
    area = 0.0
    cx = 0.0
    cy = 0.0
    Ixx = 0.0
    Iyy = 0.0
    Ixy = 0.0
    
    for i in range(n):
        j = (i + 1) % n
        factor = (vertices[i][0] * vertices[j][1]) - (vertices[j][0] * vertices[i][1])
        area += factor
        cx += (vertices[i][0] + vertices[j][0]) * factor
        cy += (vertices[i][1] + vertices[j][1]) * factor
        Ixx += (vertices[i][1]**2 + vertices[i][1]*vertices[j][1] + vertices[j][1]**2) * factor
        Iyy += (vertices[i][0]**2 + vertices[i][0]*vertices[j][0] + vertices[j][0]**2) * factor
        Ixy += (vertices[i][0]*vertices[j][1] + 2*vertices[i][0]*vertices[i][1] + 2*vertices[j][0]*vertices[j][1] + vertices[j][0]*vertices[i][1]) * factor

    area = area / 2.0
    if abs(area) < 1e-6: return 1.0, 0.0, 0.0, 1.0, 1.0, 0.0
    area = abs(area)
    cx /= (6.0 * area)
    cy /= (6.0 * area)
    Ixx = abs(Ixx / 12.0) - area * cy**2
    Iyy = abs(Iyy / 12.0) - area * cx**2
    Ixy = abs(Ixy / 24.0) - area * cx * cy
    return area, cx, cy, max(0.001, Ixx), max(0.001, Iyy), Ixy

def get_polygon_section_width_at_y(target_y, vertices):
    """หาความกว้างหน้าตัดคอนกรีต bw ที่แกน Y ใดๆ"""
    intersections = []
    n = len(vertices)
    for i in range(n):
        p1 = vertices[i]
        p2 = vertices[(i + 1) % n]
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]
        if min(y1, y2) <= target_y <= max(y1, y2):
            if abs(y2 - y1) > 1e-6:
                t = (target_y - y1) / (y2 - y1)
                x_interp = x1 + t * (x2 - x1)
                intersections.append(x_interp)
            else:
                intersections.extend([x1, x2])
    if len(intersections) < 2: return 0.1
    return max(intersections) - min(intersections)

def get_polygon_section_height_at_x(target_x, vertices):
    """หาความยาวหน้าตัดคอนกรีตที่แกน X ใดๆ (สำหรับแกน Y)"""
    intersections = []
    n = len(vertices)
    for i in range(n):
        p1 = vertices[i]
        p2 = vertices[(i + 1) % n]
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]
        if min(x1, x2) <= target_x <= max(x1, x2):
            if abs(x2 - x1) > 1e-6:
                t = (target_x - x1) / (x2 - x1)
                y_interp = y1 + t * (y2 - y1)
                intersections.append(y_interp)
            else:
                intersections.extend([y1, y2])
    if len(intersections) < 2: return 0.1
    return max(intersections) - min(intersections)

def compute_effective_depth(t_total, cover_cm, embed_cm, bar_dia_mm):
    return t_total - (cover_cm / 100) - (embed_cm / 100) - ((bar_dia_mm / 1000) / 2)

# =========================================================================
# V8.1 FIX 1: SERVICEABILITY CRACK CONTROL (GERGELY-LUTZ IN SI UNITS)
# =========================================================================
def evaluate_gergely_lutz_crack(Mu_ton_m, As_cm2, d_cm, cover_cm, bar_mm, spacing_cm):
    """คำนวณความกว้างรอยร้าวตามข้อกำหนดสภาวะใช้งาน (ACI Gergely-Lutz) [SI Unitsแท้]"""
    if Mu_ton_m <= 0 or As_cm2 <= 0: return 0.0
    
    fs_ksc = (Mu_ton_m * 1000 * 100) / (As_cm2 * 0.85 * d_cm) # Service Stress Approximation (ksc)
    
    # แปลงหน่วย fs จาก ksc เป็น MPa
    fs_mpa = fs_ksc * 0.0980665
    fy_mpa = 400.0
    # จำกัดค่า fs ไม่ให้เกิน 0.6 fy
    if fs_mpa > 0.6 * fy_mpa: 
        fs_mpa = 0.6 * fy_mpa
        
    # แปลง dc และ spacing เป็น mm
    dc_mm = (cover_cm * 10.0) + (bar_mm / 2.0)
    s_mm = (spacing_cm * 10.0) if spacing_cm > 0 else 150.0
    
    A_eff_mm2 = 2.0 * dc_mm * s_mm
    beta = 1.20
    
    # Gergely-Lutz SI Equation: 11.0e-6 -> ผลลัพธ์เป็น mm
    w_crack = 11.0e-6 * beta * fs_mpa * ((dc_mm * A_eff_mm2)**(1/3))
    return w_crack

# =========================================================================
# VISUALIZATION FUNCTIONS 
# =========================================================================
def generate_2d_plan_view(vertices, cx, cy, piles_actual, pile_shape, pile_w, pile_l, columns_list=[(0,0)]):
    fig, ax = plt.subplots(figsize=(6, 6))
    x_v = [v[0] for v in vertices] + [vertices[0][0]]
    y_v = [v[1] for v in vertices] + [vertices[0][1]]
    
    ax.plot(x_v, y_v, '-', color='#1e8449', linewidth=2.5, label='ขอบเขตฐานราก')
    ax.fill(x_v, y_v, color='#2ecc71', alpha=0.2)
    
    for c_idx, (col_x, col_y) in enumerate(columns_list):
        col_rect = patches.Rectangle((col_x - cx/2, col_y - cy/2), cx, cy, linewidth=2, edgecolor='#922b21', facecolor='#e74c3c', alpha=0.7, label='เสาตอม่อ' if c_idx==0 else "")
        ax.add_patch(col_rect)
    
    for i, (px, py) in enumerate(piles_actual):
        if pile_shape == "Circular Pile":
            pile_shape_patch = patches.Circle((px, py), pile_w/2, linewidth=1.5, edgecolor='#2c3e50', facecolor='#34495e', alpha=0.6)
        else:
            pile_shape_patch = patches.Rectangle((px - pile_w/2, py - pile_l/2), pile_w, pile_l, linewidth=1.5, edgecolor='#2c3e50', facecolor='#34495e', alpha=0.6)
        ax.add_patch(pile_shape_patch)
        ax.text(px, py, f"P{i+1}", ha='center', va='center', color='white', fontsize=9, fontweight='bold')
        
    ax.axhline(0, color='black', linewidth=0.5, linestyle='--')
    ax.axvline(0, color='black', linewidth=0.5, linestyle='--')
    ax.set_xlabel('พิกัด X (ม.)')
    ax.set_ylabel('พิกัด Y (ม.)')
    ax.set_title('แปลน As-Built (2D Mapping)', fontsize=12, fontweight='bold')
    ax.axis('equal')
    ax.grid(True, linestyle=':', alpha=0.6)
    return fig

def generate_rebar_detailing_view(t_actual, b_max, cover_cm, embed_cm, bar_dia, n_bars_x, sp_x, cx, cy, require_top_steel):
    fig, ax = plt.subplots(figsize=(10, 5))
    c_m, e_m, d_m = cover_cm / 100, embed_cm / 100, bar_dia / 1000
    hook_len = min(0.30, max(0.15, t_actual - 2*c_m - e_m))
    
    footing = patches.Rectangle((-b_max/2, 0), b_max, t_actual, linewidth=2, edgecolor='#2c3e50', facecolor='#eaeded')
    ax.add_patch(footing)
    col_stub = patches.Rectangle((-cx/2, t_actual), cx, 0.50, linewidth=2, edgecolor='#7e1e1e', facecolor='#f2d7d5')
    ax.add_patch(col_stub)
    
    p_w = 0.30
    pile1 = patches.Rectangle((-b_max/3 - p_w/2, -0.3), p_w, 0.3 + e_m, facecolor='#bdc3c7', edgecolor='#34495e', linewidth=1.5)
    pile2 = patches.Rectangle((b_max/3 - p_w/2, -0.3), p_w, 0.3 + e_m, facecolor='#bdc3c7', edgecolor='#34495e', linewidth=1.5)
    ax.add_patch(pile1)
    ax.add_patch(pile2)
    
    bot_z_x = e_m + c_m + (d_m/2)
    bot_z_y = bot_z_x + d_m
    left_x, right_x = -b_max/2 + c_m, b_max/2 - c_m
    
    ax.plot([left_x, right_x], [bot_z_x, bot_z_x], color='#c0392b', linewidth=3, label=f'เหล็กล่าง Main DB{bar_dia}')
    ax.plot([left_x, left_x], [bot_z_x, bot_z_x + hook_len], color='#c0392b', linewidth=3)
    ax.plot([right_x, right_x], [bot_z_x, bot_z_x + hook_len], color='#c0392b', linewidth=3)
    
    dot_count = min(n_bars_x, 20)
    x_dots = np.linspace(left_x + c_m, right_x - c_m, dot_count)
    for rx in x_dots: ax.plot(rx, bot_z_y, 'o', color='#2c3e50', markersize=5)
        
    if require_top_steel:
        top_z_x = t_actual - c_m - (d_m/2)
        top_z_y = top_z_x - d_m
        ax.plot([left_x, right_x], [top_z_x, top_z_x], color='#2980b9', linewidth=2.5, linestyle='-', label='เหล็กบน (กันร้าว/รับแรงถอน)')
        ax.plot([left_x, left_x], [top_z_x, top_z_x - hook_len], color='#2980b9', linewidth=2.5)
        ax.plot([right_x, right_x], [top_z_x, top_z_x - hook_len], color='#2980b9', linewidth=2.5)
        for rx in x_dots: ax.plot(rx, top_z_y, 'o', color='#34495e', markersize=4)

    dowel_left, dowel_right = -cx/2 + 0.05, cx/2 - 0.05
    dowel_bot_z = bot_z_y + d_m
    
    ax.plot([dowel_left, dowel_left], [dowel_bot_z, t_actual + 0.6], color='#d35400', linewidth=2.5, linestyle='-', label='เหล็กแกนเสาล้วงฐานราก')
    ax.plot([dowel_right, dowel_right], [dowel_bot_z, t_actual + 0.6], color='#d35400', linewidth=2.5, linestyle='-')
    ax.plot([dowel_left, dowel_left + 0.15], [dowel_bot_z, dowel_bot_z], color='#d35400', linewidth=2.5)
    ax.plot([dowel_right, dowel_right - 0.15], [dowel_bot_z, dowel_bot_z], color='#d35400', linewidth=2.5)

    ax.plot([-b_max/2 - 0.05, left_x], [bot_z_x, bot_z_x], color='black', linewidth=1)
    ax.text(-b_max/2 - 0.08, bot_z_x, f'Cov. {cover_cm}cm', ha='right', fontsize=8)
    ax.plot([-b_max/3 + 0.1, -b_max/3 + 0.1], [0, e_m], color='black', linewidth=1)
    ax.text(-b_max/3 + 0.12, e_m/2, f'Embed. {embed_cm}cm', va='center', fontsize=8)
    
    ax.text(0, -0.4, f'ความกว้างฐาน B_max = {b_max:.2f} m', ha='center', fontsize=11, fontweight='bold')
    ax.text(right_x + 0.2, t_actual, f't = {t_actual:.2f} m', fontsize=10, fontweight='bold')
    
    ax.set_xlim(-b_max/2 - 0.5, b_max/2 + 0.5)
    ax.set_ylim(-0.5, t_actual + 0.7)
    ax.set_title(f'รูปขยายการเสริมเหล็ก V8.1 ({n_bars_x}-DB{bar_dia} @ {sp_x:.0f} cm)', fontsize=12, fontweight='bold')
    ax.axis('off')
    ax.legend(loc='upper right', fontsize=9, framealpha=0.9)
    return fig

# =========================================================================
# CORE EVALUATION ROUTINE (ADVANCED Ixy & LATERAL)
# =========================================================================
def execute_shear_evaluation_routine(eval_d, eval_t, area, W_soil, P_ult, Mu_cx, Mu_cy, ecc_x, ecc_y, n_piles_act, piles_rel, piles_act, I_xx, I_yy, cx, cy, fc_prime, col_pos, vertices, factor_dl, I_xy=0.0, phi_s=0.75):
    w_u_footing_weight = factor_dl * (area * eval_t * 2.4)
    w_u_soil_weight = factor_dl * W_soil
    P_total_factored = P_ult + w_u_footing_weight + w_u_soil_weight
    Mu_x_total = Mu_cx + (P_total_factored * (-ecc_y))
    Mu_y_total = Mu_cy + (P_total_factored * (-ecc_x))
    
    p_ult_reactions = []
    denom = (I_xx * I_yy) - I_xy**2
    if abs(denom) < 1e-5: denom = max(0.001, I_xx * I_yy)
        
    for prx, pry in piles_rel:
        # ระบบคำนวณแบบหน้าตัดอสมมาตร (Asymmetric Section Engine)
        R_u = (P_total_factored / n_piles_act) + \
              ((Mu_x_total * I_yy - Mu_y_total * I_xy) / denom) * pry + \
              ((Mu_y_total * I_xx - Mu_x_total * I_xy) / denom) * prx
        p_ult_reactions.append(R_u)
        
    # 1. Punching Shear
    b1_box, b2_box = cx + eval_d, cy + eval_d
    b_0 = 2 * (b1_box + b2_box)
    A_punching_cm2 = b_0 * eval_d * 10000
    
    V_u_punching_kg = sum(max(0.0, p_ult_reactions[idx] * 1000) for idx, (px, py) in enumerate(piles_act) if abs(px) > (cx/2 + eval_d/2) or abs(py) > (cy/2 + eval_d/2))
    v_u_punching_stress = V_u_punching_kg / A_punching_cm2 if A_punching_cm2 > 0 else 0.0
    
    beta_ratio = max(cx, cy) / min(cx, cy) if min(cx, cy) > 0 else 1.0
    alpha_s = 40 if col_pos == "Interior" else (30 if col_pos == "Edge" else 20)
    v_c_allow_punching = phi_s * min(0.27*(2 + 4/beta_ratio)*math.sqrt(fc_prime), 0.27*(alpha_s*(eval_d*100)/(b_0*100) + 2)*math.sqrt(fc_prime), 1.06*math.sqrt(fc_prime))
    
    # 2. Wide-Beam Shear
    cut_y_top = cy/2 + eval_d
    V_u_wb_top = sum(max(0.0, p_ult_reactions[idx] * 1000) for idx, (px, py) in enumerate(piles_act) if py >= cut_y_top)
    bw_top = get_polygon_section_width_at_y(cut_y_top, vertices) * 100
    v_u_wb_top_stress = V_u_wb_top / (bw_top * eval_d * 100) if (bw_top > 0 and eval_d > 0) else 0

    cut_y_bot = -(cy/2 + eval_d)
    V_u_wb_bot = sum(max(0.0, p_ult_reactions[idx] * 1000) for idx, (px, py) in enumerate(piles_act) if py <= cut_y_bot)
    bw_bot = get_polygon_section_width_at_y(cut_y_bot, vertices) * 100
    v_u_wb_bot_stress = V_u_wb_bot / (bw_bot * eval_d * 100) if (bw_bot > 0 and eval_d > 0) else 0
    
    v_u_wb_max = max(v_u_wb_top_stress, v_u_wb_bot_stress)
    v_c_allow_wb = phi_s * 0.53 * math.sqrt(fc_prime)
    
    is_safe = (v_u_punching_stress <= v_c_allow_punching) and (v_u_wb_max <= v_c_allow_wb)
    return is_safe, v_u_punching_stress, v_c_allow_punching, v_u_wb_max, v_c_allow_wb, p_ult_reactions

def design_rebar_by_axis(Mu_ton_m, width_cm, d_cm, t_cm, fc_prime, fy, phi_flex, ab_area):
    width_cm = max(width_cm, 30.0)
    As_min = 0.0018 * width_cm * t_cm
    if Mu_ton_m <= 0 or d_cm <= 0:
        n_bars = max(math.ceil(As_min / ab_area), 4)
        spacing = math.floor((width_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
        return n_bars, min(spacing, 45.0), False, As_min
        
    Mu_kg_cm = Mu_ton_m * 1000 * 100
    Rn = Mu_kg_cm / (phi_flex * width_cm * d_cm**2)
    val_sqrt = 1 - (2 * Rn) / (0.85 * fc_prime)
    if val_sqrt < 0: return 0, 0, True, 0.0
    rho = (0.85 * fc_prime / fy) * (1 - math.sqrt(val_sqrt))
    
    As_req = max(rho * width_cm * d_cm, As_min)
    n_bars = max(math.ceil(As_req / ab_area), 4)
    spacing = math.floor((width_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
    return n_bars, min(spacing, 45.0), False, As_req

# =========================================================================
# V8.1 FIX 5: Z-AXIS COORDINATE FIX FOR 3D INTERACTIVE MESH
# =========================================================================
@st.cache_data(show_spinner=False)
def generate_3d_mesh(concrete_vertices_tuple, t_actual, cx, cy, piles_actual_tuple, pile_shape, pile_w, pile_l, embed_m):
    concrete_vertices = list(concrete_vertices_tuple)
    piles_actual = list(piles_actual_tuple)
    
    def create_3d_prism_trace(vertices, z_start, z_end, face_color, opacity, name, show_legend=True):
        n = len(vertices)
        x_coords = [v[0] for v in vertices] * 2
        y_coords = [v[1] for v in vertices] * 2
        z_coords = [z_start] * n + [z_end] * n
        i_idx, j_idx, k_idx = [], [], []
        for idx in range(1, n - 1): i_idx.append(0); j_idx.append(idx); k_idx.append(idx + 1)
        for idx in range(1, n - 1): i_idx.append(n); j_idx.append(n + idx + 1); k_idx.append(n + idx)
        for idx in range(n):
            next_idx = (idx + 1) % n
            i_idx.extend([idx, idx]); j_idx.extend([next_idx, n + next_idx]); k_idx.extend([n + next_idx, n + idx])
        return go.Mesh3d(x=x_coords, y=y_coords, z=z_coords, i=i_idx, j=j_idx, k=k_idx, color=face_color, opacity=opacity, name=name, showlegend=show_legend)

    fig_3d = go.Figure()
    
    # เซ็ตพิกัด Z ให้สมจริง: ท็อปฐานรากคือ 0, ใต้ท้องฐานรากคือ -t_actual
    footing_bottom_z = -t_actual
    pile_top_z = footing_bottom_z + embed_m
    pile_bottom_z = footing_bottom_z - 1.0 # ความยาวเสาเข็มที่แสดงผล
    
    # คอนกรีตฐานราก
    fig_3d.add_trace(create_3d_prism_trace(concrete_vertices, footing_bottom_z, 0, '#2ecc71', 0.5, 'คอนกรีตฐานราก'))
    
    # เสาตอม่อ (ยื่นขึ้นจาก 0 ไป 0.5 ม.)
    column_vertices = [(-cx/2, -cy/2), (cx/2, -cy/2), (cx/2, cy/2), (-cx/2, cy/2)]
    fig_3d.add_trace(create_3d_prism_trace(column_vertices, 0, 0.50, '#e74c3c', 0.7, 'เสาตอม่อ'))
    
    # เสาเข็ม As-Built
    for index, p in enumerate(piles_actual):
        px, py = p[0], p[1]
        
        # วาดเส้นทรงกระบอกแกนดิ่งแทนตัวเสาเข็ม
        fig_3d.add_trace(go.Scatter3d(
            x=[px, px], y=[py, py], z=[pile_bottom_z, pile_top_z],
            mode='lines', line=dict(color='gray', width=8),
            name=f"Pile P{index+1}", showlegend=False
        ))
        # พล็อตจุดตำแหน่งหัวเสาเข็ม
        fig_3d.add_trace(go.Scatter3d(
            x=[px], y=[py], z=[pile_top_z],
            mode='markers+text', marker=dict(size=6, color='#2c3e50', symbol='circle'),
            text=[f"P{index+1}"], textposition="top center",
            name=f"หัวเข็ม P{index+1}", showlegend=False
        ))

    fig_3d.update_layout(scene=dict(aspectmode='data'), margin=dict(l=0, r=0, b=0, t=30))
    return fig_3d

# =========================================================================
# APPLICATION LAYOUT & UI SIGNATURE
# =========================================================================
with st.sidebar:
    st.header("🏗️ ข้อมูลการออกแบบฐานรากตอม่อ V8.1")
    footing_shape_type = st.selectbox("รูปทรงเรขาคณิตและชนิดฐานราก:", 
        ["Truncated Triangular Footing", "Rectangular Footing", "Combined Footing (>= 2 Columns)", "Strap Footing (ชิดเขต)", "Arbitrary Freeform Polygon"], index=0)
    col_position = st.selectbox("ตำแหน่งเสาตอม่อ (Column Position):", ["Interior", "Edge", "Corner"], index=0)
    
    st.subheader("🛠️ User-Defined Load Factors")
    factor_dl = st.number_input("γ_DL (Dead Load Factor)", value=1.2, step=0.1)
    factor_ll = st.number_input("γ_LL (Live Load Factor)", value=1.6, step=0.1)
    
    st.subheader("🌪️ เพิ่มฟังก์ชัน: แรงเฉือนแนวราบ & แผ่นดินไหว")
    V_x = st.number_input("แรงเฉือนระดับแนวราบ V_x (ตัน)", value=0.0)
    V_y = st.number_input("แรงเฉือนระดับแนวราบ V_y (ตัน)", value=0.0)
    T_z = st.number_input("แรงบิดบิดหมุนที่หัวเสา T_z (ตัน-เมตร)", value=0.0)

    st.subheader("💧 เพิ่มฟังก์ชัน: การควบคุมความกว้างรอยร้าว")
    environmental_condition = st.selectbox("สภาวะการใช้งานควบคุมรอยร้าว:", ["ทั่วไป (สภาวะปกติ - Max 0.30mm)", "โครงสร้างกันน้ำ / กัดกร่อนสูง (Max 0.15mm)"])
    w_allowable = 0.15 if "โครงสร้างกันน้ำ" in environmental_condition else 0.30

    st.subheader("1. การตั้งค่าเสาเข็มและพิกัด As-Built")
    pile_shape = st.selectbox("รูปทรงเสาเข็ม:", ["Circular Pile", "Square/Rectangular Pile"], index=0)
    pile_dia = st.number_input("เส้นผ่านศูนย์กลาง/ความกว้างเสาเข็ม (ม.)", value=0.30, min_value=0.15)
    pile_w = pile_dia; pile_l = pile_dia 
    
    pile_cap = st.number_input("กำลังรับแรงอัดที่ปลอดภัยของเข็ม (ตัน/ต้น)", value=30.0)
    pile_tension_cap = st.number_input("กำลังรับแรงถอนที่ปลอดภัยของเข็ม (ตัน/ต้น)", value=10.0)
    
    S_dist = 3.0 * pile_w
    E_dist = 0.40 

    columns_list = [(0.0, 0.0)]
    I_xy_geom = 0.0
    
    if footing_shape_type == "Truncated Triangular Footing":
        n_piles = 3
        piles_ideal = [(0, S_dist / math.sqrt(3)), 
                       (-S_dist / 2, -S_dist / (2 * math.sqrt(3))), 
                       (S_dist / 2, -S_dist / (2 * math.sqrt(3)))]
        R_top = (S_dist / math.sqrt(3)) + E_dist
        Y_bot = -(S_dist / (2 * math.sqrt(3))) - E_dist
        X_side = (S_dist / 2) + E_dist
        trunc = 0.20
        concrete_vertices_base = [
            (-trunc, R_top), (trunc, R_top),
            (X_side, Y_bot + trunc), (X_side - trunc, Y_bot),
            (-X_side + trunc, Y_bot), (-X_side, Y_bot + trunc)
        ]
        B_max_visual = X_side * 2
    elif footing_shape_type == "Rectangular Footing":
        n_piles = st.selectbox("จำนวนเสาเข็มในกลุ่ม:", [2, 4, 5, 6, 8, 9], index=1)
        if n_piles == 2: piles_ideal = [(-S_dist/2, 0), (S_dist/2, 0)]
        elif n_piles == 4: piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2), (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2)]
        else: piles_ideal = [(0,0)] * n_piles 
        B_min_geometry = S_dist + 2*E_dist
        L_min_geometry = S_dist + 2*E_dist
        B_ft = B_min_geometry; L_ft = L_min_geometry
        concrete_vertices_base = [(-B_ft/2, -L_ft/2), (B_ft/2, -L_ft/2), (B_ft/2, L_ft/2), (-B_ft/2, L_ft/2)]
        B_max_visual = B_ft
    elif footing_shape_type == "Combined Footing (>= 2 Columns)":
        st.info("📊 โมดูลฐานรากร่วมรับเสาตอม่อ 2 ต้น")
        n_piles = 6
        piles_ideal = [(-1.2, -0.6), (0.0, -0.6), (1.2, -0.6), (-1.2, 0.6), (0.0, 0.6), (1.2, 0.6)]
        columns_list = [(-1.0, 0.0), (1.0, 0.0)]
        concrete_vertices_base = [(-2.0, -1.2), (2.0, -1.2), (2.0, 1.2), (-2.0, 1.2)]
        B_max_visual = 4.0
    elif footing_shape_type == "Strap Footing (ชิดเขต)":
        st.info("🔗 โมดูลระบบคานรัดส่งถ่ายโมเมนต์สมดุล")
        n_piles = 4
        piles_ideal = [(-1.5, -0.5), (-1.5, 0.5), (1.5, -0.5), (1.5, 0.5)]
        columns_list = [(-1.8, 0.0), (1.5, 0.0)] 
        concrete_vertices_base = [(-2.3, -1.0), (2.3, -1.0), (2.3, 1.0), (-2.3, 1.0)]
        B_max_visual = 4.6
    else: 
        st.info("🗺️ ปลดล็อกวาดรูปทรงอิสระ (ระบุจุดต่อจุด)")
        n_piles = 4
        piles_ideal = [(-0.8, -0.8), (0.8, -0.8), (0.8, 0.8), (-0.8, 0.8)]
        concrete_vertices_base = [(-1.5, 1.5), (0.5, 1.5), (0.5, -0.5), (1.5, -0.5), (1.5, -1.5), (-1.5, -1.5)]
        _, _, _, _, _, I_xy_geom = compute_polygon_advanced_properties(concrete_vertices_base)
        B_max_visual = 3.0

    st.subheader("3. นน.บรรทุกตอม่อและวัสดุ")
    DL = st.number_input("Dead Load (ตัน)", value=55.0)
    LL = st.number_input("Live Load (ตัน)", value=30.0)
    
    Mcx_dl, Mcy_dl, Mcx_ll, Mcy_ll = 6.0, 5.0, 4.0, 3.0
    soil_depth = 1.0; soil_density = 1.8
    cx, cy = 0.35, 0.35
    fc_prime = 280; fy = 4000 
    bar_dia = st.selectbox("ขนาดเหล็กแกน DB (มม.)", [12, 16, 20, 25, 28, 32], index=2)
    
    thickness_mode = st.radio("โหมดกำหนดความหนา t:", ["Auto-Optimize", "Manual Override"])
    manual_t = 0.65
    if thickness_mode == "Manual Override":
        manual_t = st.number_input("กำหนดความหนาฐานราก t (ม.)", value=0.65, min_value=0.30)
        
    pile_embed_cm = 5.0; concrete_cover_cm = 7.5

phi_shear, phi_flexure = 0.75, 0.90 
ab_area = (math.pi * (bar_dia / 10) ** 2) / 4 

# =========================================================================
# MAIN DATA PROCESSING FLOW 
# =========================================================================
st.markdown("### 📍 1. การวิเคราะห์ As-Built Field Survey เข็มตอม่อ")
st.info("💡 **ระบบวิเคราะห์ความปลอดภัยเชิงพิกัดร่วม:** โค้ดจะดักจับแรงเยื้องศูนย์จริงรวมกับผลของแรงแผ่นดินไหว/แรงลมแนวราบ")

# =========================================================================
# V8.1 FIX 2: UI STATE PERSISTENCE & GUARD CLAUSE
# =========================================================================
if "prev_footing" not in st.session_state:
    st.session_state.prev_footing = footing_shape_type
    st.session_state.prev_piles = n_piles
    st.session_state.pile_data = pd.DataFrame({
        'ชื่อเข็ม': [f"P{i+1}" for i in range(n_piles)],
        'Ideal X (ม.)': [round(p[0], 3) for p in piles_ideal],
        'Ideal Y (ม.)': [round(p[1], 3) for p in piles_ideal],
        'ΔX (ม.) - หน้างาน': [0.00] * n_piles,
        'ΔY (ม.) - หน้างาน': [0.00] * n_piles
    })

# Guard Clause เช็คความเปลี่ยนแปลงจาก Sidebar
if (st.session_state.prev_footing != footing_shape_type) or (st.session_state.prev_piles != n_piles):
    st.session_state.prev_footing = footing_shape_type
    st.session_state.prev_piles = n_piles
    st.session_state.pile_data = pd.DataFrame({
        'ชื่อเข็ม': [f"P{i+1}" for i in range(n_piles)],
        'Ideal X (ม.)': [round(p[0], 3) for p in piles_ideal],
        'Ideal Y (ม.)': [round(p[1], 3) for p in piles_ideal],
        'ΔX (ม.) - หน้างาน': [0.00] * n_piles,
        'ΔY (ม.) - หน้างาน': [0.00] * n_piles
    })

# ใช้ Static Key ร่วมกับ st.session_state ป้องกัน Widget Destruction
edited_df = st.data_editor(
    st.session_state.pile_data, 
    disabled=['ชื่อเข็ม', 'Ideal X (ม.)', 'Ideal Y (ม.)'], 
    hide_index=True, 
    use_container_width=True,
    key="static_piles_editor_key" 
)
st.session_state.pile_data = edited_df

piles_actual = []
for _, row in edited_df.iterrows():
    piles_actual.append((row['Ideal X (ม.)'] + row['ΔX (ม.) - หน้างาน'], row['Ideal Y (ม.)'] + row['ΔY (ม.) - หน้างาน']))

cg_actual_x = sum(p[0] for p in piles_actual) / n_piles
cg_actual_y = sum(p[1] for p in piles_actual) / n_piles
ecc_x, ecc_y = cg_actual_x - 0.0, cg_actual_y - 0.0 

piles_relative = [(p[0] - cg_actual_x, p[1] - cg_actual_y) for p in piles_actual]
I_yy_group = max(0.001, sum(p[0]**2 for p in piles_relative))
I_xx_group = max(0.001, sum(p[1]**2 for p in piles_relative))

E_c = 4700 * math.sqrt(fc_prime) * 10
t_check = manual_t if thickness_mode == "Manual Override" else 0.65
rigidity_index = (E_c * t_check**3) / 12

P_ultimate = (factor_dl * DL) + (factor_ll * LL)
Mu_cx = (factor_dl * Mcx_dl) + (factor_ll * Mcx_ll)
Mu_cy = (factor_dl * Mcy_dl) + (factor_ll * Mcy_ll)

Ms_cx = Mcx_dl + Mcx_ll
Ms_cy = Mcy_dl + Mcy_ll

concrete_vertices = [(v[0] - ecc_x, v[1] - ecc_y) for v in concrete_vertices_base]
footing_area = polygon_area(concrete_vertices)
W_soil = max(0.0, footing_area - (cx*cy)) * soil_depth * soil_density

# =========================================================================
# V8.1 FIX 3: INFINITE LOOP VERIFICATION 
# =========================================================================
if thickness_mode == "Auto-Optimize":
    d_opt = 0.30; safe = False; p_ult_out = [0.0] * n_piles
    
    max_d = 3.0
    step = 0.02
    loop_counter = 0
    max_loops = int((max_d - 0.30) / step) + 10 # บัฟเฟอร์ป้องกันลูปค้าง
    
    while d_opt <= max_d and loop_counter < max_loops:
        loop_counter += 1
        t_opt = d_opt + (concrete_cover_cm/100) + (pile_embed_cm/100) + ((bar_dia/1000)/2)
        safe, v_up, v_cp, v_uwb, v_cwb, p_ult_out = execute_shear_evaluation_routine(
            d_opt, t_opt, footing_area, W_soil, P_ultimate, Mu_cx, Mu_cy, ecc_x, ecc_y, n_piles, piles_relative, piles_actual, I_xx_group, I_yy_group, cx, cy, fc_prime, col_position, concrete_vertices, factor_dl, I_xy=I_xy_geom
        )
        if safe: break
        d_opt += step
        
    if not safe:
        st.error("🚨 วิกฤต: ไม่สามารถหาความหนาฐานรากที่ปลอดภัยได้ (ความหนาชนขีดจำกัดสูงสุด 3.0 m หรือเกินจำนวนรอบคำนวณ) อาจเกิดจากแรงเฉือนทะลุหรือแรงเยื้องศูนย์สูงเกินไป แนะนำให้ขยายขนาดขอบเขตฐานราก (Footing Plan Dimensions) หรือเพิ่มจำนวนเสาเข็ม")
        st.stop() # หลุดลูปอย่างปลอดภัย
        
    t_actual = math.ceil(t_opt * 20) / 20; d_actual = d_opt
else:
    t_actual = manual_t
    d_actual = compute_effective_depth(t_actual, concrete_cover_cm, pile_embed_cm, bar_dia)
    safe, v_up, v_cp, v_uwb, v_cwb, p_ult_out = execute_shear_evaluation_routine(
        d_actual, t_actual, footing_area, W_soil, P_ultimate, Mu_cx, Mu_cy, ecc_x, ecc_y, n_piles, piles_relative, piles_actual, I_xx_group, I_yy_group, cx, cy, fc_prime, col_position, concrete_vertices, factor_dl, I_xy=I_xy_geom
    )

polar_R_sum = sum(prx**2 + pry**2 for prx, pry in piles_relative)
if polar_R_sum == 0: polar_R_sum = 1.0

pile_horizontal_shear = []
for prx, pry in piles_relative:
    V_ix = (V_x / n_piles) - (T_z * pry / polar_R_sum)
    V_iy = (V_y / n_piles) + (T_z * prx / polar_R_sum)
    pile_horizontal_shear.append(math.sqrt(V_ix**2 + V_iy**2))

P_u_total = P_ultimate + factor_dl * ( (footing_area*t_actual*2.4) + W_soil)
P_service_total = DL + LL + (footing_area * t_actual * 2.4) + W_soil
Ms_cx_total = Ms_cx + P_service_total * ecc_y
Ms_cy_total = Ms_cy + P_service_total * ecc_x

pile_service_reactions = []
denom_s = (I_xx_group * I_yy_group) - I_xy_geom**2
if abs(denom_s) < 1e-5: denom_s = max(0.001, I_xx_group * I_yy_group)

for prx, pry in piles_relative:
    R_s = (P_service_total / n_piles) + \
          ((Ms_cx_total * I_yy_group - Ms_cy_total * I_xy_geom) / denom_s) * pry + \
          ((Ms_cy_total * I_xx_group - Ms_cx_total * I_xy_geom) / denom_s) * prx
    pile_service_reactions.append(R_s)

has_tension = any(r < 0 for r in p_ult_out)
require_top_steel = has_tension or (t_actual >= 0.60) 

# คำนวณโมเมนต์ดัดออกแบบเหล็กเสริม (X-Axis)
Mu_x_top = abs(sum(p_ult_out[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2))
Mu_x_bot = abs(sum(p_ult_out[i] * (abs(p[1]) - cy/2) for i, p in enumerate(piles_actual) if p[1] < -cy/2))
Mu_x_max = max(Mu_x_top, Mu_x_bot)

w_flex_x = get_polygon_section_width_at_y(0, concrete_vertices) * 100
n_bars_x, sp_x, _, as_req_x = design_rebar_by_axis(Mu_x_max, w_flex_x, d_actual*100, t_actual*100, fc_prime, fy, phi_flexure, ab_area)

# =========================================================================
# V8.1 FIX 4: TWO-WAY ACTION EFFECTIVE WIDTH FOR Y-AXIS 
# =========================================================================
Mu_y_top = abs(sum(p_ult_out[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2))
Mu_y_bot = abs(sum(p_ult_out[i] * (abs(p[0]) - cx/2) for i, p in enumerate(piles_actual) if p[0] < -cx/2))
Mu_y_max = max(Mu_y_top, Mu_y_bot)

# ตรวจสอบความกว้างหน้าตัดที่ขอบผิวเสาทั้งสองฝั่ง (ซ้ายและขวา) แล้วเลือกค่าต่ำสุด
w_flex_left = get_polygon_section_height_at_x(-cx/2.0, concrete_vertices) * 100
w_flex_right = get_polygon_section_height_at_x(cx/2.0, concrete_vertices) * 100
w_flex_y = min(w_flex_left, w_flex_right)

n_bars_y, sp_y, _, as_req_y = design_rebar_by_axis(Mu_y_max, w_flex_y, d_actual*100, t_actual*100, fc_prime, fy, phi_flexure, ab_area)

# ตรวจสอบขีดจำกัดรอยร้าวหน้าตัดวิกฤต (Crack Control Validation)
calculated_w = evaluate_gergely_lutz_crack(Mu_x_max, n_bars_x * ab_area, d_actual*100, concrete_cover_cm, bar_dia, sp_x)

st.markdown("---")

# =========================================================================
# DISPLAY & INTERFACE REPORT (REFACTORED WITH TABS)
# =========================================================================
tab_report, tab_visuals = st.tabs(["📊 2. รายงานผลการวิเคราะห์ & Serviceability", "🗺️ 3. Engineering Visual Twin Plots (2D/3D)"])

with tab_report:
    tension_warnings = []
    for idx, r_s in enumerate(pile_service_reactions):
        if r_s < 0 and abs(r_s) > pile_tension_cap:
            tension_warnings.append(f"P{idx+1} (แรงถอน {abs(r_s):.2f} ตัน)")
            
    if tension_warnings:
        st.error(f"🚨 **อันตราย!** มีเสาเข็มรับแรงถอน (Tension) เกินค่าพิกัดปลอดภัยที่ตั้งไว้ ({pile_tension_cap} ตัน/ต้น): {', '.join(tension_warnings)}")
    
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.write("**Factored Loads & Geometries**")
        st.write(f"* พื้นที่หน้าตัดฐานรากประมวลผลจริง: `{footing_area:.2f}` ตร.ม.")
        st.write(f"* P_u_total (รวมนน.ดิน+ฐานราก): `{P_u_total:.2f}` ตัน")
        st.write(f"**สมรรถนะการควบคุมรอยร้าว & พฤติกรรมโครงสร้าง**")
        st.write(f"* ความกว้างรอยร้าวผิวคอนกรีต: `{calculated_w:.3f}` มม. (ค่าขีดจำกัดยอมให้: `{w_allowable}` มม.)")
        if calculated_w <= w_allowable:
            st.success("✅ Crack Width Control: Passed")
        else:
            st.error("❌ Crack Width Control: Exceeded ขอบเขตความกว้างรอยร้าวเกินมาตรฐานสำหรับสภาพแวดล้อมนี้")
            
        st.write(f"**Flexural Design (เหล็กเสริมรับโมเมนต์ดัด)**")
        st.write(f"* แกน X (Mu_x = {Mu_x_max:.2f} t-m): ใช้ `{n_bars_x}-DB{bar_dia} @ {sp_x:.0f} cm`")
        st.write(f"* แกน Y (Mu_y = {Mu_y_max:.2f} t-m): ใช้ `{n_bars_y}-DB{bar_dia} @ {sp_y:.0f} cm`")
        
        st.write(f"**Shear Check (d = {d_actual:.2f} m)**")
        st.write(f"* v_up (Punching): `{v_up:.2f}` KSC (≤ {v_cp:.2f} KSC) [{'✅ Safe' if v_up <= v_cp else '❌ Overstressed'}]")
        st.write(f"* v_uwb (Wide-beam): `{v_uwb:.2f}` KSC (≤ {v_cwb:.2f} KSC) [{'✅ Safe' if v_uwb <= v_cwb else '❌ Overstressed'}]")

    with col_res2:
        st.write("**ตารางสรุปผลแรงปฏิกิริยาหัวเสาเข็มรอบทิศทาง**")
        df_react = pd.DataFrame({
            'ชื่อเข็ม': st.session_state.pile_data['ชื่อเข็ม'], 
            'R_u (ดิ่ง-ตัน)': p_ult_out,
            'R_s (ดิ่งใช้งาน-ตัน)': pile_service_reactions,
            'V_i (ราบแผ่นดินไหว-ตัน)': pile_horizontal_shear
        })
        st.dataframe(df_react.style.highlight_max(subset=['V_i (ราบแผ่นดินไหว-ตัน)'], color='#f5b041'), hide_index=True, use_container_width=True)

with tab_visuals:
    col_plot1, col_plot2 = st.columns(2)

    with col_plot1:
        st.markdown("#### 📐 A) As-Built Plan View (Polygon Based)")
        fig_2d = generate_2d_plan_view(concrete_vertices, cx, cy, piles_actual, pile_shape, pile_w, pile_l, columns_list=columns_list)
        st.pyplot(fig_2d)

    with col_plot2:
        st.markdown("#### 🟥 B) Ultra Section Detailing View")
        if require_top_steel:
            st.info(f"💡 **Top Rebar Activated:** {'เนื่องจากมีเข็มรับแรงถอน (Tension)' if has_tension else f'เนื่องจากฐานรากหนา t={t_actual:.2f}m ≥ 0.60m (กันร้าว)'}")
        fig_rebar = generate_rebar_detailing_view(t_actual, B_max_visual, concrete_cover_cm, pile_embed_cm, bar_dia, n_bars_x, sp_x, cx, cy, require_top_steel)
        st.pyplot(fig_rebar)

    st.markdown("#### 🧊 C) 3D Interactive Mesh (Exact Geometry)")
    fig_3d = generate_3d_mesh(tuple(concrete_vertices), t_actual, cx, cy, tuple(piles_actual), pile_shape, pile_w, pile_l, pile_embed_cm / 100)
    st.plotly_chart(fig_3d, use_container_width=True)
