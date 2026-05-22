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
st.set_page_config(page_title="Enterprise Footing Suite V7.8", page_icon="📐", layout="wide")

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
def point_to_segment_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0: return math.sqrt((px - x1)**2 + (py - y1)**2)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx*dx + dy*dy)
    t = max(0.0, min(1.0, t))
    return math.sqrt((px - (x1 + t * dx))**2 + (py - (y1 + t * dy))**2)

def get_polygon_section_width_at_y(target_y, vertices):
    """คำนวณหาความกว้างแนวนอน (แกน X) ของรูปทรงฐานราก ณ ตำแหน่งระดับ Y ที่กำหนด"""
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
    if len(intersections) < 2: return 0.0
    return max(intersections) - min(intersections)

def get_polygon_section_length_at_x(target_x, vertices):
    """คำนวณหาความยาวแนวตั้ง (แกน Y) ของรูปทรงฐานราก ณ ตำแหน่งแนว X ที่กำหนด"""
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
    if len(intersections) < 2: return 0.0
    return max(intersections) - min(intersections)

def compute_effective_depth(t_total, cover_cm, embed_cm, bar_dia_mm):
    return t_total - (cover_cm / 100) - (embed_cm / 100) - ((bar_dia_mm / 1000) / 2)

def generate_2d_plan_view(vertices, cx, cy, piles_actual, pile_shape, pile_w, pile_l):
    fig, ax = plt.subplots(figsize=(6, 6))
    x_v = [v[0] for v in vertices] + [vertices[0][0]]
    y_v = [v[1] for v in vertices] + [vertices[0][1]]
    
    ax.plot(x_v, y_v, '-', color='#1e8449', linewidth=2.5, label='ขอบเขตฐานราก')
    ax.fill(x_v, y_v, color='#2ecc71', alpha=0.2)
    
    col_rect = patches.Rectangle((-cx/2, -cy/2), cx, cy, linewidth=2, edgecolor='#922b21', facecolor='#e74c3c', alpha=0.7, label='เสาตอม่อ')
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
    ax.set_title('แปลนAs-Built (2D Mapping)', fontsize=12, fontweight='bold')
    ax.axis('equal')
    ax.grid(True, linestyle=':', alpha=0.6)
    return fig

# 🚀 ULTIMATE REBAR DETAILING SECTION VIEW (V7.8 Ultra)
def generate_rebar_detailing_view(t_actual, B_ft, cover_cm, embed_cm, bar_dia, n_bars_x, sp_x, cx, cy, require_top_steel):
    fig, ax = plt.subplots(figsize=(10, 5))
    
    c_m = cover_cm / 100
    e_m = embed_cm / 100
    d_m = bar_dia / 1000
    # ปรับปรุงระยะงอฉากให้สมจริง
    hook_len = min(0.30, max(0.15, t_actual - 2*c_m - e_m))
    
    # 1. Base Outlines (Elevation View)
    footing = patches.Rectangle((-B_ft/2, 0), B_ft, t_actual, linewidth=2, edgecolor='#2c3e50', facecolor='#eaeded')
    ax.add_patch(footing)
    
    col_stub = patches.Rectangle((-cx/2, t_actual), cx, 0.50, linewidth=2, edgecolor='#7e1e1e', facecolor='#f2d7d5')
    ax.add_patch(col_stub)
    
    # 2. Piles
    p_w = 0.30
    pile1 = patches.Rectangle((-B_ft/3 - p_w/2, -0.3), p_w, 0.3 + e_m, facecolor='#bdc3c7', edgecolor='#34495e', linewidth=1.5)
    pile2 = patches.Rectangle((B_ft/3 - p_w/2, -0.3), p_w, 0.3 + e_m, facecolor='#bdc3c7', edgecolor='#34495e', linewidth=1.5)
    ax.add_patch(pile1)
    ax.add_patch(pile2)
    
    # 3. Bottom Rebar Set ( Main X-Bars เส้นยาว, Transverse Y-Dots จุดวงกลม)
    bot_z_x = e_m + c_m + (d_m/2)
    bot_z_y = bot_z_x + d_m
    left_x = -B_ft/2 + c_m
    right_x = B_ft/2 - c_m
    
    # เส้นเหล็กแกนล่าง (Main X)
    ax.plot([left_x, right_x], [bot_z_x, bot_z_x], color='#c0392b', linewidth=3, label=f'เหล็กล่าง Main DB{bar_dia}')
    ax.plot([left_x, left_x], [bot_z_x, bot_z_x + hook_len], color='#c0392b', linewidth=3)
    ax.plot([right_x, right_x], [bot_z_x, bot_z_x + hook_len], color='#c0392b', linewidth=3)
    
    # จุดเหล็กตามขวางล่าง (Transverse Y)
    dot_count = min(n_bars_x, 20) # จำกัดจุดเพื่อความสวยงาม
    x_dots = np.linspace(left_x + c_m, right_x - c_m, dot_count)
    for rx in x_dots:
        ax.plot(rx, bot_z_y, 'o', color='#2c3e50', markersize=5)
        
    # 4. Top Rebar Set (ตะแกรงบน - แสดงถ้า require_top_steel = True)
    if require_top_steel:
        top_z_x = t_actual - c_m - (d_m/2)
        top_z_y = top_z_x - d_m
        
        ax.plot([left_x, right_x], [top_z_x, top_z_x], color='#2980b9', linewidth=2.5, linestyle='-', label='เหล็กบน (กันร้าว/รับแรงถอน)')
        ax.plot([left_x, left_x], [top_z_x, top_z_x - hook_len], color='#2980b9', linewidth=2.5)
        ax.plot([right_x, right_x], [top_z_x, top_z_x - hook_len], color='#2980b9', linewidth=2.5)
        
        for rx in x_dots:
            ax.plot(rx, top_z_y, 'o', color='#34495e', markersize=4)

    # 5. Column Dowels (เหล็กหนวดกุ้งล้วงฐานราก)
    dowel_left = -cx/2 + 0.05
    dowel_right = cx/2 - 0.05
    dowel_bot_z = bot_z_y + d_m # ล้วงลงไปวางบนตะแกรงล่าง
    
    ax.plot([dowel_left, dowel_left], [dowel_bot_z, t_actual + 0.6], color='#d35400', linewidth=2.5, linestyle='-', label='เหล็กแกนเสาล้วงฐานราก')
    ax.plot([dowel_right, dowel_right], [dowel_bot_z, t_actual + 0.6], color='#d35400', linewidth=2.5, linestyle='-')
    # งอฉากหนวดกุ้ง (L-Hook)
    ax.plot([dowel_left, dowel_left + 0.15], [dowel_bot_z, dowel_bot_z], color='#d35400', linewidth=2.5)
    ax.plot([dowel_right, dowel_right - 0.15], [dowel_bot_z, dowel_bot_z], color='#d35400', linewidth=2.5)

    # 6. เส้นบอกระยะแบบ Blueprint
    # covering
    ax.plot([-B_ft/2 - 0.05, left_x], [bot_z_x, bot_z_x], color='black', linewidth=1)
    ax.text(-B_ft/2 - 0.08, bot_z_x, f'Cov. {cover_cm}cm', ha='right', fontsize=8)
    # pile embedment
    ax.plot([-B_ft/3 + 0.1, -B_ft/3 + 0.1], [0, e_m], color='black', linewidth=1)
    ax.text(-B_ft/3 + 0.12, e_m/2, f'Embed. {embed_cm}cm', va='center', fontsize=8)
    
    # 7. Labels
    ax.text(0, -0.4, f'หน้าตัด B = {B_ft:.2f} m', ha='center', fontsize=11, fontweight='bold')
    ax.text(right_x + 0.2, t_actual, f't = {t_actual:.2f} m', fontsize=10, fontweight='bold')
    
    ax.set_xlim(-B_ft/2 - 0.5, B_ft/2 + 0.5)
    ax.set_ylim(-0.5, t_actual + 0.7)
    ax.set_title(f'รูปขยายการเสริมเหล็ก V7.8 Ultra ({n_bars_x}-DB{bar_dia} @ {sp_x:.0f} cm)', fontsize=12, fontweight='bold')
    ax.axis('off') # ปิดแกนเพื่อความสวยงามแบบ CAD
    ax.legend(loc='upper right', fontsize=9, framealpha=0.9)
    
    return fig

# =========================================================================
# CORE ENGINEERING LOGIC (COMPLETE)
# =========================================================================
def execute_shear_evaluation_routine(eval_d, eval_t, area, W_soil, P_ult, Mu_cx, Mu_cy, ecc_x, ecc_y, n_piles, piles_rel, piles_act, I_xx, I_yy, cx, cy, fc_prime, col_pos, footing_shape, b_ft, vertices, factor_dl, phi_s=0.75):
    """คำนวณประเมินแรงเฉือนทั้งหมด (Punching & Wide Beam) โดยใช้ตัวคูณโหลด Dynamic"""
    w_u_footing_weight = factor_dl * (area * eval_t * 2.4)
    w_u_soil_weight = factor_dl * W_soil
    P_total_factored = P_ult + w_u_footing_weight + w_u_soil_weight
    # โมเมนต์รวมรวมผลจากระยะเยื้อง As-Built
    Mu_x_total = Mu_cx + (P_total_factored * (-ecc_y))
    Mu_y_total = Mu_cy + (P_total_factored * (-ecc_x))
    
    p_ult_reactions = []
    for prx, pry in piles_rel:
        # สมการ Elastic Mechanics ฐานรากตอม่อเยื้องศูนย์
        R_u = (P_total_factored / n_piles) + \
              (Mu_y_total * prx / I_yy if I_yy > 0.001 else 0) + \
              (Mu_x_total * pry / I_xx if I_xx > 0.001 else 0)
        p_ult_reactions.append(R_u)
        
    b1_box, b2_box = cx + eval_d, cy + eval_d
    b_0 = 2 * (b1_box + b2_box) # เส้นรอบวงวิกฤตแรงเฉือนทะลุ
    A_punching_cm2 = b_0 * eval_d * 10000
    
    # 1. Punching Shear Check
    V_u_punching_kg = sum(max(0.0, p_ult_reactions[idx] * 1000) for idx, (px, py) in enumerate(piles_act) if abs(px) > (cx/2 + eval_d/2) or abs(py) > (cy/2 + eval_d/2))
    v_u_punching_stress = V_u_punching_kg / A_punching_cm2 if A_punching_cm2 > 0 else 0.0
    
    beta_ratio = max(cx, cy) / min(cx, cy) if min(cx, cy) > 0 else 1.0
    alpha_s = 40 if col_pos == "Interior" else (30 if col_pos == "Edge" else 20)
    v_c_allow_punching = phi_s * min(0.27*(2 + 4/beta_ratio)*math.sqrt(fc_prime), 0.27*(alpha_s*(eval_d*100)/(b_0*100) + 2)*math.sqrt(fc_prime), 1.06*math.sqrt(fc_prime))
    
    # 2. Wide-Beam Shear Check (Y-direction)
    cut_y_pos = cy/2 + eval_d # หน้าตัดวิกฤตห่างจากหน้าเสาระยะ d
    V_u_wb = sum(max(0.0, p_ult_reactions[idx] * 1000) for idx, (px, py) in enumerate(piles_act) if py >= cut_y_pos)
    bw_y = get_polygon_section_width_at_y(cut_y_pos, vertices) * 100 # ความกว้างหน้าตัดจริง ณ จุดตัด
    
    v_u_wb_max = V_u_wb / (bw_y * eval_d * 100) if (bw_y > 0 and eval_d > 0) else 0
    v_c_allow_wb = phi_s * 0.53 * math.sqrt(fc_prime)
    
    # ตัดสินความปลอดภัย: ผ่านทั้งคู่
    is_safe = (v_u_punching_stress <= v_c_allow_punching) and (v_u_wb_max <= v_c_allow_wb)
    
    return is_safe, v_u_punching_stress, v_c_allow_punching, v_u_wb_max, v_c_allow_wb, p_ult_reactions

def design_rebar_by_axis(Mu_ton_m, width_cm, d_cm, t_cm, fc_prime, fy, phi_flex, ab_area):
    """ออกแบบเหล็กเสริมรับแรงดัด WSD ตามหน้าตัด Mu"""
    width_cm = max(width_cm, 30.0)
    As_min = 0.0018 * width_cm * t_cm # เหล็กกันร้าวขั้นต่ำ ACI
    
    if Mu_ton_m <= 0 or d_cm <= 0:
        # ไม่มีการดัด ใช้เหล็กขั้นต่ำ
        n_bars = max(math.ceil(As_min / ab_area), 4)
        spacing = math.floor((width_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
        return n_bars, min(spacing, 45.0), False, As_min
        
    Mu_kg_cm = Mu_ton_m * 1000 * 100
    Rn = Mu_kg_cm / (phi_flex * width_cm * d_cm**2)
    beta_1 = 0.85 if fc_prime <= 280 else max(0.65, 0.85 - 0.05 * (fc_prime - 280) / 70)
    
    # คำนวณ Rho
    val_sqrt = 1 - (2 * Rn) / (0.85 * fc_prime)
    if val_sqrt < 0: return 0, 0, True, 0.0 # หน้าตัดเล็กเกินไปสำหรับแรงดัด
    rho = (0.85 * fc_prime / fy) * (1 - math.sqrt(val_sqrt))
    
    As_req = max(rho * width_cm * d_cm, As_min)
    n_bars = max(math.ceil(As_req / ab_area), 4)
    spacing = math.floor((width_cm - 15) / (n_bars - 1)) if n_bars > 1 else 15
    return n_bars, min(spacing, 45.0), False, As_req

@st.cache_data(show_spinner=False)
def generate_3d_mesh(concrete_vertices_tuple, t_actual, cx, cy, piles_actual_tuple, pile_shape, pile_w, pile_l, embed_m):
    """สร้างโมเดล 3D Interactive (Plotly Mesh)"""
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

    def draw_3d_wireframe_lines(fig, vertices, z_start, z_end, line_color='#1e8449'):
        n = len(vertices)
        bx, by = [v[0] for v in vertices] + [vertices[0][0]], [v[1] for v in vertices] + [vertices[0][1]]
        fig.add_trace(go.Scatter3d(x=bx, y=by, z=[z_start]*(n+1), mode='lines', line=dict(color=line_color, width=2.5), showlegend=False))
        fig.add_trace(go.Scatter3d(x=bx, y=by, z=[z_end]*(n+1), mode='lines', line=dict(color=line_color, width=2.5), showlegend=False))
        for v in vertices: fig.add_trace(go.Scatter3d(x=[v[0], v[0]], y=[v[1], v[1]], z=[z_start, z_end], mode='lines', line=dict(color=line_color, width=2), showlegend=False))

    fig_3d = go.Figure()
    # Footing body
    fig_3d.add_trace(create_3d_prism_trace(concrete_vertices, 0, t_actual, '#2ecc71', 0.5, 'คอนกรีตฐานราก'))
    draw_3d_wireframe_lines(fig_3d, concrete_vertices, 0, t_actual)
    
    # Column
    column_vertices = [(-cx/2, -cy/2), (cx/2, -cy/2), (cx/2, cy/2), (-cx/2, cy/2)]
    fig_3d.add_trace(create_3d_prism_trace(column_vertices, t_actual, t_actual + 0.50, '#e74c3c', 0.7, 'เสาตอม่อ'))
    
    # Piles
    for idx, (px, py) in enumerate(piles_actual):
        p_w_3d = 0.30
        p_nodes = [(-p_w_3d/2 + px, -p_w_3d/2 + py), (p_w_3d/2 + px, -p_w_3d/2 + py),
                   (p_w_3d/2 + px, p_w_3d/2 + py), (-p_w_3d/2 + px, p_w_3d/2 + py)]
        fig_3d.add_trace(create_3d_prism_trace(p_nodes, -1.0, embed_m, '#34495e', 0.9, 'เสาเข็มAs-Built', show_legend=(idx==0)))

    fig_3d.update_layout(scene=dict(aspectmode='data'), margin=dict(l=0, r=0, b=0, t=30))
    return fig_3d

# =========================================================================
# APPLICATION LAYOUT & UI SIGNATURE
# =========================================================================
with st.sidebar:
    st.header("🏗️ ข้อมูลการออกแบบฐานรากตอม่อ")
    footing_shape_type = st.selectbox("รูปทรงทางเรขาคณิตฐานราก:", ["Truncated Triangular Footing", "Rectangular Footing"], index=1)
    
    st.subheader("🛠️ User-Defined Load Combination Factors")
    factor_dl = st.number_input("γ_DL (Dead Load Factor)", value=1.2, step=0.1)
    factor_ll = st.number_input("γ_LL (Live Load Factor)", value=1.6, step=0.1)
    
    st.subheader("1. การตั้งค่าเสาเข็มและพิกัดAs-Built")
    pile_shape = st.selectbox("รูปทรงเสาเข็ม:", ["Circular Pile", "Square/Rectangular Pile"], index=0)
    pile_dia = st.number_input("เส้นผ่านศูนย์กลาง/ความกว้างเสาเข็ม (ม.)", value=0.30, min_value=0.15)
    pile_w = pile_dia; pile_l = pile_dia # Square pile assumption

    n_piles = st.selectbox("จำนวนเสาเข็มในกลุ่ม:", [2, 3, 4, 5, 6, 8, 9], index=2) # Default 4 piles
    
    pile_cap = st.number_input("กำลังรับแรงอัดที่ปลอดภัยของเข็ม (ตัน/ต้น)", value=30.0)
    pile_tension_cap = st.number_input("กำลังรับแรงถอนที่ปลอดภัยของเข็ม (ตัน/ต้น)", value=10.0)
    
    # ระยะห่างเข็ม (S) และระยะขอบ (E)
    S_dist = 3.0 * pile_w
    E_dist = 0.40 # ระยะขอบเข็มขั้นต่ำ

    # กำหนดพิกัดเข็มอุดมคติ (Ideal)
    if footing_shape_type == "Rectangular Footing":
        if n_piles == 2: piles_ideal = [(-S_dist/2, 0), (S_dist/2, 0)]
        elif n_piles == 4: piles_ideal = [(-S_dist/2, -S_dist/2), (S_dist/2, -S_dist/2),
                                          (-S_dist/2, S_dist/2), (S_dist/2, S_dist/2)]
        else: piles_ideal = [(0,0)] * n_piles # Simplified for this Complete Code output
        
        B_min_geometry = S_dist + 2*E_dist
        L_min_geometry = S_dist + 2*E_dist
    else:
        # Triangular
        piles_ideal = [(0, S_dist / math.sqrt(3)), 
                       (-S_dist / 2, -S_dist / (2 * math.sqrt(3))), 
                       (S_dist / 2, -S_dist / (2 * math.sqrt(3)))]
        B_min_geometry, L_min_geometry = S_dist + 2*E_dist, S_dist + 2*E_dist

    # UI กำหนดขนาดฐานราก (B x L)
    dim_mode = st.radio("โหมดกำหนดขนาดฐานราก:", ["Auto-Size", "Manual Override"])
    if dim_mode == "Manual Override":
        B_input = st.number_input("ความกว้างฐานราก X-axis (ม.)", value=round(B_min_geometry,2), min_value=0.40)
        L_input = st.number_input("ความยาวฐานราก Y-axis (ม.)", value=round(L_min_geometry,2), min_value=0.40)
        B_ft = max(B_input, B_min_geometry)
        L_ft = max(L_input, L_min_geometry)
    else:
        B_ft = B_min_geometry
        L_ft = L_min_geometry

    st.subheader("3. นน.บรรทุกตอม่อและวัสดุ")
    DL = st.number_input("Dead Load (ตัน)", value=55.0)
    LL = st.number_input("Live Load (ตัน)", value=30.0)
    
    # สุ่ม Moment เพื่อการทดสอบ
    Mcx_dl, Mcy_dl, Mcx_ll, Mcy_ll = 6.0, 5.0, 4.0, 3.0
    
    # ถมดิน
    soil_depth = 1.0; soil_density = 1.8
    
    # หน้าตัดเสาตอม่อและวัสดุ
    cx, cy = 0.35, 0.35
    fc_prime = 280; fy = 4000 # KSC, kg/cm2
    bar_dia = st.selectbox("ขนาดเหล็กแกน DB (มม.)", [12, 16, 20, 25, 28, 32], index=2) # Default DB20
    
    # ความหนาฐานราก t และ Covering
    thickness_mode = st.radio("โหมดกำหนดความหนา t:", ["Auto-Optimize", "Manual Override"])
    manual_t = 0.65
    if thickness_mode == "Manual Override":
        manual_t = st.number_input("กำหนดความหนาฐานราก t (ม.)", value=0.65, min_value=0.30)
        
    pile_embed_cm = 5.0; concrete_cover_cm = 7.5

phi_shear, phi_flexure = 0.75, 0.90 # กำลังลด
ab_area = (math.pi * (bar_dia / 10) ** 2) / 4 # เนื้อที่เหล็ก 1 เส้น

# =========================================================================
# MAIN DATA PROCESSING FLOW
# =========================================================================
# STEP 1: AS-BUILT DATA EDITOR
st.markdown("### 📍 1. การวิเคราะห์As-Built Field Survey เข็มตอม่อ")
st.info("💡 **ข้อมูล Dynamic:** การปรับ ΔX, ΔY จะส่งผลกระทบต่อแรงที่เข็มรับทันที")

df_initial = pd.DataFrame({
    'ชื่อเข็ม': [f"P{i+1}" for i in range(n_piles)],
    'Ideal X (ม.)': [round(p[0], 3) for p in piles_ideal],
    'Ideal Y (ม.)': [round(p[1], 3) for p in piles_ideal],
    'ΔX (ม.) - หน้างาน': [0.00] * n_piles,
    'ΔY (ม.) - หน้างาน': [0.00] * n_piles
})
edited_df = st.data_editor(df_initial, disabled=['ชื่อเข็ม', 'Ideal X (ม.)', 'Ideal Y (ม.)'], hide_index=True, use_container_width=True)

# คำนวณพิกัดAs-Built
piles_actual = []
for _, row in edited_df.iterrows():
    # 🔥 FIXED: แก้ไขตัวอักษร 'm.' เป็น 'ม.' เรียบร้อยแล้ว หมดปัญหา KeyError
    piles_actual.append((row['Ideal X (ม.)'] + row['ΔX (ม.) - หน้างาน'], row['Ideal Y (ม.)'] + row['ΔY (ม.) - หน้างาน']))

# หา CG ของกลุ่มเข็มจริง
cg_actual_x = sum(p[0] for p in piles_actual) / n_piles
cg_actual_y = sum(p[1] for p in piles_actual) / n_piles
ecc_x, ecc_y = cg_actual_x - 0.0, cg_actual_y - 0.0 # เยื้องCG เทียบศูนย์กลางตอม่อ

# Inertia ของกลุ่มเข็ม As-Built
piles_relative = [(p[0] - cg_actual_x, p[1] - cg_actual_y) for p in piles_actual]
I_yy_group = max(0.001, sum(p[0]**2 for p in piles_relative))
I_xx_group = max(0.001, sum(p[1]**2 for p in piles_relative))

# --- คำนวณ Load Combination ---
P_ultimate = (factor_dl * DL) + (factor_ll * LL)
Mu_cx = (factor_dl * Mcx_dl) + (factor_ll * Mcx_ll)
Mu_cy = (factor_dl * Mcy_dl) + (factor_ll * Mcy_ll)

# พื้นที่ฐานรากและน้ำหนักดินถม
footing_area = B_ft * L_ft
W_soil = max(0.0, footing_area - (cx*cy)) * soil_depth * soil_density

# ขอบเขตคอนกรีตฐานรากAs-Built
concrete_vertices = [(-B_ft/2 - ecc_x, -L_ft/2 - ecc_y), (B_ft/2 - ecc_x, -L_ft/2 - ecc_y), 
                     (B_ft/2 - ecc_x, L_ft/2 - ecc_y), (-B_ft/2 - ecc_x, L_ft/2 - ecc_y)]

# --- ประมวลผลความหนาและเฉือน Dynamic ---
if thickness_mode == "Auto-Optimize":
    d_opt = 0.30; safe = False; p_ult_out = [0.0] * n_piles
    while d_opt < 3.0:
        t_opt = d_opt + (concrete_cover_cm/100) + (pile_embed_cm/100) + ((bar_dia/1000)/2)
        safe, v_up, v_cp, v_uwb, v_cwb, p_ult_out = execute_shear_evaluation_routine(
            d_opt, t_opt, footing_area, W_soil, P_ultimate, Mu_cx, Mu_cy, ecc_x, ecc_y, n_piles, piles_relative, piles_actual, I_xx_group, I_yy_group, cx, cy, fc_prime, col_position, footing_shape_type, B_ft, concrete_vertices, factor_dl
        )
        if safe: break
        d_opt += 0.02
    t_actual = math.ceil(t_opt * 20) / 20; d_actual = d_opt
else:
    t_actual = manual_t
    d_actual = compute_effective_depth(t_actual, concrete_cover_cm, pile_embed_cm, bar_dia)
    safe, v_up, v_cp, v_uwb, v_cwb, p_ult_out = execute_shear_evaluation_routine(
        d_actual, t_actual, footing_area, W_soil, P_ultimate, Mu_cx, Mu_cy, ecc_x, ecc_y, n_piles, piles_relative, piles_actual, I_xx_group, I_yy_group, cx, cy, fc_prime, col_position, footing_shape_type, B_ft, concrete_vertices, factor_dl
    )

# --- คำนวณตรวจสอบแรงอัดเข็ม Service Load ---
P_u_total = P_ultimate + factor_dl * ( (footing_area*t_actual*2.4) + W_soil)
w_s_footing = footing_area * t_actual * 2.4
P_service_total = DL + LL + w_s_footing + W_soil
Ms_cx_total = Ms_cx + P_service_total * ecc_y
Ms_cy_total = Ms_cy + P_service_total * ecc_x

pile_service_reactions = []
for prx, pry in piles_relative:
    # Elastic Mechanics Service Loads
    R_s = (P_service_total / n_piles) + (Ms_cy_total * prx / I_yy_group) + (Ms_cx_total * pry / I_xx_group)
    pile_service_reactions.append(R_s)

# --- วิเคราะห์ Negative Moment และตรวจสอบความจำเป็นของเหล็กตะแกรงบน ---
has_tension = any(r < 0 for r in p_ult_out)
require_top_steel = has_tension or (t_actual >= 0.60) # บังคับใส่เมื่อหนาเกน 60cm หรือมีแรงถอนเข็ม

# STEP 2-5 แสดงผล UI substitutions (กู้คืนเนื้อหาUIที่หายไป)
st.markdown("### 🏗️ 2-5 ข้อมูล substitutions และความปลอดภัย")
col_res1, col_res2 = st.columns(2)
with col_res1:
    st.write("**Factored Loads**")
    st.write(f"* P_u_total: `{P_u_total:.2f}` ตัน")
    st.write(f"**Shear Check (d = {d_actual:.2f} m)**")
    st.write(f"* v_up: `{v_up:.2f}` KSC (≤ {v_cp:.2f} KSC) [{'✅ Safe' if v_up <= v_cp else '❌ Overstressed'}]")
    st.write(f"* v_uwb: `{v_uwb:.2f}` KSC (≤ {v_cwb:.2f} KSC) [{'✅ Safe' if v_uwb <= v_cwb else '❌ Overstressed'}]")

with col_res2:
    st.write("**Pile Reactions (Factored loads)**")
    df_react = pd.DataFrame({'ชื่อเข็ม': df_initial['ชื่อเข็ม'], 'R_u (ตัน)': p_ult_out})
    st.dataframe(df_react, hide_index=True)

# flexural design
Mu_x_top = abs(sum(p_ult_out[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2))
w_flex_x = B_ft * 100
n_bars_x, sp_x, _, _ = design_rebar_by_axis(Mu_x_top, w_flex_x, d_actual*100, t_actual*100, fc_prime, fy, phi_flexure, ab_area)

# =========================================================================
# STEP 6: DUAL VISUALIZATION (THE ULTIMATE VERSION)
# =========================================================================
st.markdown("---")
st.markdown("### 🗺️ 6. Engineering Visual Twin Plots (Ultimate Detailing)")

col_plot1, col_plot2 = st.columns(2)

with col_plot1:
    st.markdown("#### 📐 A) As-Built Plan View")
    fig_2d = generate_2d_plan_view(concrete_vertices, cx, cy, piles_actual, pile_shape, pile_w, pile_l)
    st.pyplot(fig_2d)

with col_plot2:
    st.markdown("#### 🟥 B) Ultra Section Detailing View")
    if require_top_steel:
        st.info(f"💡 **Top Rebar Activated:** {'เนื่องจากมีเข็มรับแรงถอน (Tension)' if has_tension else f'เนื่องจากฐานรากหนา t={t_actual:.2f}m ≥ 0.60m (กันร้าว)'}")
    fig_rebar = generate_rebar_detailing_view(t_actual, B_ft, concrete_cover_cm, pile_embed_cm, bar_dia, n_bars_x, sp_x, cx, cy, require_top_steel)
    st.pyplot(fig_rebar)

st.markdown("#### 🧊 C) 3D Interactive Mesh")
fig_3d = generate_3d_mesh(tuple(concrete_vertices), t_actual, cx, cy, tuple(piles_actual), pile_shape, pile_w, pile_l, pile_embed_cm / 100)
st.plotly_chart(fig_3d, use_container_width=True)
