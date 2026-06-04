import streamlit as st
import math
import os
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
from matplotlib.path import Path
import plotly.graph_objects as go

# =========================================================================
# SYSTEM STABILITY & FONT MANAGEMENT
# =========================================================================
st.set_page_config(page_title="Enterprise Footing Suite V8.5 - Flexible Engine", page_icon="📐", layout="wide")

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
# ADVANCED ENGINEERING SOLVER: WINKLER FOUNDATION (FDM GRID ENGINE)
# =========================================================================
def compute_flexible_reactions(vertices, piles_act, columns_list, P_total, M_x, M_y, t_actual, fc_prime, pile_ks):
    """
    วิเคราะห์เสาเข็มและฐานรากแบบยืดหยุ่น (Flexible Winkler Foundation)
    จำลองพฤติกรรมแผ่นคอนกรีตที่มีการโก่งตัวจริง และเสาเข็มเป็นฐานรองรับแบบสปริง
    """
    x_coords = [v[0] for v in vertices]
    y_coords = [v[1] for v in vertices]
    xmin, xmax = min(x_coords), max(x_coords)
    ymin, ymax = min(y_coords), max(y_coords)
    
    margin = 0.05
    xmin -= margin; xmax += margin
    ymin -= margin; ymax += margin
    
    nx, ny = 20, 20
    dx = (xmax - xmin) / (nx - 1)
    dy = (ymax - ymin) / (ny - 1)
    
    fc_mpa = fc_prime * 0.0980665
    E_c_mpa = 4700 * math.sqrt(fc_mpa)
    E_concrete = E_c_mpa * 101.9716 
    
    nu = 0.15
    D = (E_concrete * (t_actual**3)) / (12 * (1 - nu**2))
    
    poly_path = Path(vertices)
    active_nodes = []
    grid_to_global = {}
    node_idx = 0
    
    for i in range(nx):
        for j in range(ny):
            x = xmin + i * dx
            y = ymin + j * dy
            if poly_path.contains_point((x, y)) or poly_path.contains_point((x, y), radius=0.01):
                grid_to_global[(i, j)] = node_idx
                active_nodes.append((i, j, x, y))
                node_idx += 1
                
    M = len(active_nodes)
    if M == 0:
        return [P_total / max(1, len(piles_act))] * len(piles_act)
        
    K = np.zeros((M, M))
    F = np.zeros(M)
    
    factor_x = (D * dy) / (dx**3)
    for j in range(ny):
        for i in range(nx - 2):
            g0 = grid_to_global.get((i, j))
            g1 = grid_to_global.get((i+1, j))
            g2 = grid_to_global.get((i+2, j))
            if g0 is not None and g1 is not None and g2 is not None:
                idx = [g0, g1, g2]
                coeffs = [1.0, -2.0, 1.0]
                for r in range(3):
                    for c in range(3):
                        K[idx[r], idx[c]] += coeffs[r] * coeffs[c] * factor_x
                        
    factor_y = (D * dx) / (dy**3)
    for i in range(nx):
        for j in range(ny - 2):
            g0 = grid_to_global.get((i, j))
            g1 = grid_to_global.get((i, j+1))
            g2 = grid_to_global.get((i, j+2))
            if g0 is not None and g1 is not None and g2 is not None:
                idx = [g0, g1, g2]
                coeffs = [1.0, -2.0, 1.0]
                for r in range(3):
                    for c in range(3):
                        K[idx[r], idx[c]] += coeffs[r] * coeffs[c] * factor_y
                        
    pile_node_indices = []
    for px, py in piles_act:
        min_dist = float('inf')
        best_g = 0
        for g_idx, (i, j, x, y) in enumerate(active_nodes):
            d = (x - px)**2 + (y - py)**2
            if d < min_dist:
                min_dist = d
                best_g = g_idx
        K[best_g, best_g] += pile_ks
        pile_node_indices.append(best_g)
        
    for col_x, col_y in columns_list:
        P_col = P_total / len(columns_list)
        Mx_col = M_x / len(columns_list)
        My_col = M_y / len(columns_list)
        
        min_dist = float('inf')
        best_g = 0
        best_i, best_j = 0, 0
        for g_idx, (i, j, x, y) in enumerate(active_nodes):
            d = (x - col_x)**2 + (y - col_y)**2
            if d < min_dist:
                min_dist = d
                best_g = g_idx
                best_i, best_j = i, j
        F[best_g] += P_col
        
        g_north = grid_to_global.get((best_i, min(ny-1, best_j + 1)))
        g_south = grid_to_global.get((best_i, max(0, best_j - 1)))
        if g_north is not None and g_south is not None:
            F[g_north] += Mx_col / (2 * dy)
            F[g_south] -= Mx_col / (2 * dy)
            
        g_east = grid_to_global.get((min(nx-1, best_i + 1), best_j))
        g_west = grid_to_global.get((max(0, best_i - 1), best_j))
        if g_east is not None and g_west is not None:
            F[g_east] += My_col / (2 * dx)
            F[g_west] -= My_col / (2 * dx)
            
    K += np.eye(M) * 1e-3  
    try:
        w_disp = np.linalg.solve(K, F)
    except np.linalg.LinAlgError:
        return [P_total / len(piles_act)] * len(piles_act)
        
    reactions = [w_disp[g_idx] * pile_ks for g_idx in pile_node_indices]
    
    sum_r = sum(reactions) if sum(reactions) > 0 else 1.0
    return [r * (P_total / sum_r) for r in reactions]

# =========================================================================
# HELPER FUNCTIONS (MATH, GEOMETRY & VISUALIZATION)
# =========================================================================
def polygon_area(vertices):
    n = len(vertices)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2.0

def compute_polygon_advanced_properties(vertices):
    n = len(vertices)
    area = 0.0
    cx, cy = 0.0, 0.0
    Ixx, Iyy, Ixy = 0.0, 0.0, 0.0
    
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
    intersections = []
    n = len(vertices)
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        if (y1 <= target_y and y2 > target_y) or (y2 <= target_y and y1 > target_y):
            x_int = x1 + (target_y - y1) * (x2 - x1) / (y2 - y1)
            intersections.append(x_int)
    
    if len(intersections) >= 2:
        intersections.sort()
        width = sum(intersections[i+1] - intersections[i] for i in range(0, len(intersections)-1, 2))
        return max(width, 0.01)
    return 0.01

def get_polygon_section_height_at_x(target_x, vertices):
    intersections = []
    n = len(vertices)
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        if (x1 <= target_x and x2 > target_x) or (x2 <= target_x and x1 > target_x):
            y_int = y1 + (target_x - x1) * (y2 - y1) / (x2 - x1)
            intersections.append(y_int)
            
    if len(intersections) >= 2:
        intersections.sort()
        height = sum(intersections[i+1] - intersections[i] for i in range(0, len(intersections)-1, 2))
        return max(height, 0.01)
    return 0.01

def compute_effective_depth(t_total, cover_cm, embed_cm, bar_dia_mm):
    effective_cover = max(cover_cm / 100, embed_cm / 100)
    return t_total - effective_cover - ((bar_dia_mm / 1000) / 2)

def point_to_segment_dist(px, py, x1, y1, x2, y2):
    l2 = (x1 - x2)**2 + (y1 - y2)**2
    if l2 == 0: return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1)*(x2 - x1) + (py - y1)*(y2 - y1)) / l2))
    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)
    return math.hypot(px - proj_x, py - proj_y)

def calculate_b0_reduced_for_pile(px, py, pile_w, eval_d, vertices):
    dist_to_edges = []
    n = len(vertices)
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i+1)%n]
        dist_to_edges.append(point_to_segment_dist(px, py, x1, y1, x2, y2))
    
    min_dist = min(dist_to_edges) if dist_to_edges else 999
    crit_dist = (pile_w / 2) + (eval_d / 2)
    b0_standard = 4 * (pile_w + eval_d)
    
    if min_dist < crit_dist:
        if min_dist > pile_w / 2: return 3 * (pile_w + eval_d)
        else: return 2 * (pile_w + eval_d)
    return b0_standard

def get_dynamic_s_max(t_actual_m, env_condition):
    t_cm = t_actual_m * 100
    s_max_thickness = 3 * t_cm
    s_max_absolute = 45.0
    if "กันน้ำ" in env_condition or "กัดกร่อนสูง" in env_condition:
        s_max_absolute = 30.0
    return min(s_max_thickness, s_max_absolute)

def evaluate_development_length(fy_ksc, fc_ksc, bar_dia_mm, available_length_m, cover_cm):
    db_cm = bar_dia_mm / 10.0
    ld_cm = (fy_ksc / (2.1 * math.sqrt(fc_ksc))) * db_cm
    ld_cm = max(ld_cm, 30.0)
    actual_available_cm = (available_length_m * 100) - cover_cm
    is_adequate = actual_available_cm >= ld_cm
    return is_adequate, ld_cm, actual_available_cm

# =========================================================================
# EVALUATION ROUTINES
# =========================================================================
def evaluate_gergely_lutz_crack(Ms_ton_m, As_cm2, d_cm, cover_cm, bar_mm, spacing_cm):
    if Ms_ton_m <= 0 or As_cm2 <= 0: return 0.0
    fs_ksc = (Ms_ton_m * 1000 * 100) / (As_cm2 * 0.85 * d_cm) 
    fs_mpa = fs_ksc * 0.0980665
    fy_mpa = 400.0
    if fs_mpa > 0.6 * fy_mpa: fs_mpa = 0.6 * fy_mpa
        
    dc_mm = (cover_cm * 10.0) + (bar_mm / 2.0)
    s_mm = (spacing_cm * 10.0) if spacing_cm > 0 else 150.0
    A_eff_mm2 = 2.0 * dc_mm * s_mm
    beta = 1.20
    
    w_crack = 11.0e-6 * beta * fs_mpa * ((dc_mm * A_eff_mm2)**(1/3))
    return w_crack

def execute_shear_evaluation_routine(eval_d, eval_t, area, W_soil, P_ult, Mu_cx, Mu_cy, ecc_x, ecc_y, n_piles_act, piles_rel, piles_act, I_xx, I_yy, cx, cy, fc_prime, col_pos, vertices, factor_dl, columns_list, pile_dia=0.3, I_xy=0.0, phi_s=0.75, pile_ks=20000.0):
    w_u_footing_weight = factor_dl * (area * eval_t * 2.4)
    w_u_soil_weight = factor_dl * W_soil
    P_total_factored = P_ult + w_u_footing_weight + w_u_soil_weight
    Mu_x_total = Mu_cx + (P_total_factored * (-ecc_y))
    Mu_y_total = Mu_cy + (P_total_factored * (-ecc_x))
    
    p_ult_reactions = compute_flexible_reactions(vertices, piles_act, columns_list, P_total_factored, Mu_x_total, Mu_y_total, eval_t, fc_prime, pile_ks)
        
    # 1. Column Punching Shear
    b1_box, b2_box = cx + eval_d, cy + eval_d
    b_0 = 2 * (b1_box + b2_box)
    A_punching_cm2 = b_0 * eval_d * 10000
    
    V_u_punching_kg = 0.0
    for idx, (px, py) in enumerate(piles_act):
        is_outside = True
        for col_x, col_y in columns_list:
            if abs(px - col_x) <= (cx/2 + eval_d/2) and abs(py - col_y) <= (cy/2 + eval_d/2):
                is_outside = False
                break
        if is_outside:
            V_u_punching_kg += max(0.0, p_ult_reactions[idx] * 1000)

    v_u_punching_stress = V_u_punching_kg / A_punching_cm2 if A_punching_cm2 > 0 else 0.0
    beta_ratio = max(cx, cy) / min(cx, cy) if min(cx, cy) > 0 else 1.0
    alpha_s = 40 if col_pos == "Interior" else (30 if col_pos == "Edge" else 20)
    
    v_c_allow_punching = phi_s * min(
        0.53 * (1 + 2 / beta_ratio) * math.sqrt(fc_prime), 
        0.27 * (alpha_s * (eval_d * 100) / (b_0 * 100) + 2) * math.sqrt(fc_prime), 
        1.06 * math.sqrt(fc_prime)
    )
    
    # 2. Pile Punching Shear
    v_u_pile_punching_max = 0.0
    for idx, (px, py) in enumerate(piles_act):
        if p_ult_reactions[idx] > 0:
            b0_pile = calculate_b0_reduced_for_pile(px, py, pile_dia, eval_d, vertices)
            A_punch_pile_cm2 = b0_pile * eval_d * 10000
            if A_punch_pile_cm2 > 0:
                stress = (p_ult_reactions[idx] * 1000) / A_punch_pile_cm2
                v_u_pile_punching_max = max(v_u_pile_punching_max, stress)

    v_u_punching_stress = max(v_u_punching_stress, v_u_pile_punching_max)

    # 3. Wide-Beam Shear
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

def design_rebar_by_axis(Mu_ton_m, width_cm, d_cm, t_cm, fc_prime, fy, phi_flex, ab_area, cover_cm, env_cond="ทั่วไป"):
    width_cm = max(width_cm, 30.0)
    As_min = 0.0018 * width_cm * t_cm
    cover_deduction = cover_cm * 2 
    s_max = get_dynamic_s_max(t_cm / 100, env_cond)

    if Mu_ton_m <= 0 or d_cm <= 0:
        n_bars = max(math.ceil(As_min / ab_area), 4)
        spacing = math.floor((width_cm - cover_deduction) / (n_bars - 1)) if n_bars > 1 else 15
        return n_bars, min(spacing, s_max), False, As_min
        
    Mu_kg_cm = Mu_ton_m * 1000 * 100
    Rn = Mu_kg_cm / (phi_flex * width_cm * d_cm**2)
    val_sqrt = 1 - (2 * Rn) / (0.85 * fc_prime)
    if val_sqrt < 0: return 0, 0, True, 0.0
    rho = (0.85 * fc_prime / fy) * (1 - math.sqrt(val_sqrt))
    
    As_req = max(rho * width_cm * d_cm, As_min)
    n_bars = max(math.ceil(As_req / ab_area), 4)
    spacing = math.floor((width_cm - cover_deduction) / (n_bars - 1)) if n_bars > 1 else 15
    return n_bars, min(spacing, s_max), False, As_req

# =========================================================================
# VISUALIZATION FUNCTIONS (ENHANCED 2D/3D)
# =========================================================================
def generate_2d_plan_view(vertices, cx, cy, piles_actual, pile_shape, pile_w, pile_l, columns_list, cg_x, cg_y):
    fig, ax = plt.subplots(figsize=(6, 6))
    x_v = [v[0] for v in vertices] + [vertices[0][0]]
    y_v = [v[1] for v in vertices] + [vertices[0][1]]
    
    ax.plot(x_v, y_v, '-', color='#1e8449', linewidth=2.5, label='ขอบเขตฐานราก')
    ax.fill(x_v, y_v, color='#2ecc71', alpha=0.15)
    
    for c_idx, (col_x, col_y) in enumerate(columns_list):
        col_rect = patches.Rectangle((col_x - cx/2, col_y - cy/2), cx, cy, linewidth=2, edgecolor='#922b21', facecolor='#e74c3c', alpha=0.7, label='เสาตอม่อ' if c_idx==0 else "")
        ax.add_patch(col_rect)
    
    for i, (px, py) in enumerate(piles_actual):
        if pile_shape == "Circular Pile":
            pile_patch = patches.Circle((px, py), pile_w/2, linewidth=1.5, edgecolor='#2c3e50', facecolor='#34495e', alpha=0.6)
        else:
            pile_patch = patches.Rectangle((px - pile_w/2, py - pile_l/2), pile_w, pile_l, linewidth=1.5, edgecolor='#2c3e50', facecolor='#34495e', alpha=0.6)
        ax.add_patch(pile_patch)
        ax.text(px, py, f"P{i+1}", ha='center', va='center', color='white', fontsize=9, fontweight='bold')
        
    ax.plot(cg_x, cg_y, 'X', color='#e67e22', markersize=10, label=f'C.G. เข็มเยื้องจริง ({cg_x:.2f}, {cg_y:.2f})')
    ax.plot([0, cg_x], [0, cg_y], ':', color='#d35400', linewidth=1.5)

    ax.axhline(0, color='black', linewidth=0.5, linestyle='--')
    ax.axvline(0, color='black', linewidth=0.5, linestyle='--')
    ax.set_xlabel('พิกัด X (ม.)')
    ax.set_ylabel('พิกัด Y (ม.)')
    ax.set_title('แปลน As-Built Mapping & Eccentricity', fontsize=12, fontweight='bold')
    ax.axis('equal')
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='upper right', fontsize=8)
    return fig

def generate_rebar_detailing_view(t_actual, b_max, cover_cm, embed_cm, bar_dia, n_bars_x, sp_x, cx, cy, require_top_steel):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_aspect('equal') 
    c_m, e_m, d_m = cover_cm / 100, embed_cm / 100, bar_dia / 1000
    hook_len = min(0.30, max(0.15, t_actual - 2*c_m - e_m))
    
    footing = patches.Rectangle((-b_max/2, 0), b_max, t_actual, linewidth=2, edgecolor='#2c3e50', facecolor='#eaeded')
    ax.add_patch(footing)
    col_stub = patches.Rectangle((-cx/2, t_actual), cx, 0.40, linewidth=2, edgecolor='#7e1e1e', facecolor='#f2d7d5')
    ax.add_patch(col_stub)
    
    p_w = 0.30
    pile1 = patches.Rectangle((-b_max/3 - p_w/2, -0.2), p_w, 0.2 + e_m, facecolor='#bdc3c7', edgecolor='#34495e', linewidth=1.5)
    pile2 = patches.Rectangle((b_max/3 - p_w/2, -0.2), p_w, 0.2 + e_m, facecolor='#bdc3c7', edgecolor='#34495e', linewidth=1.5)
    ax.add_patch(pile1)
    ax.add_patch(pile2)
    
    bot_z_x = e_m + c_m + (d_m/2)
    bot_z_y = bot_z_x + d_m
    left_x, right_x = -b_max/2 + c_m, b_max/2 - c_m
    
    ax.plot([left_x, right_x], [bot_z_x, bot_z_x], color='#c0392b', linewidth=2.5, label=f'เหล็กล่าง DB{bar_dia}')
    ax.plot([left_x, left_x], [bot_z_x, bot_z_x + hook_len], color='#c0392b', linewidth=2.5)
    ax.plot([right_x, right_x], [bot_z_x, bot_z_x + hook_len], color='#c0392b', linewidth=2.5)
    
    dot_count = min(n_bars_x, 15)
    x_dots = np.linspace(left_x + c_m, right_x - c_m, dot_count)
    for rx in x_dots: ax.plot(rx, bot_z_y, 'o', color='#2c3e50', markersize=4)
        
    if require_top_steel:
        top_z_x = t_actual - c_m - (d_m/2)
        top_z_y = top_z_x - d_m
        ax.plot([left_x, right_x], [top_z_x, top_z_x], color='#2980b9', linewidth=2, label='เหล็กบน (กันร้าว/รับแรงถอน)')
        ax.plot([left_x, left_x], [top_z_x, top_z_x - hook_len], color='#2980b9', linewidth=2)
        ax.plot([right_x, right_x], [top_z_x, top_z_x - hook_len], color='#2980b9', linewidth=2)
        for rx in x_dots: ax.plot(rx, top_z_y, 'o', color='#34495e', markersize=3.5)

    dowel_left, dowel_right = -cx/2 + 0.05, cx/2 - 0.05
    dowel_bot_z = bot_z_y + d_m
    ax.plot([dowel_left, dowel_left], [dowel_bot_z, t_actual + 0.5], color='#d35400', linewidth=2, label='เหล็กเดือยตอม่อ (Dowel Bars)')
    ax.plot([dowel_right, dowel_right], [dowel_bot_z, t_actual + 0.5], color='#d35400', linewidth=2)
    ax.plot([dowel_left, dowel_left + 0.15], [dowel_bot_z, dowel_bot_z], color='#d35400', linewidth=2)
    ax.plot([dowel_right, dowel_right - 0.15], [dowel_bot_z, dowel_bot_z], color='#d35400', linewidth=2)

    ax.text(-b_max/2 - 0.1, bot_z_x, f'Cov. {cover_cm}cm', ha='right', fontsize=8)
    ax.text(-b_max/3 + 0.15, e_m/2, f'Embed. {embed_cm}cm', va='center', fontsize=8)
    ax.text(0, -0.3, f'B_max = {b_max:.2f} m', ha='center', fontsize=10, fontweight='bold')
    ax.text(right_x + 0.1, t_actual/2, f't = {t_actual:.2f} m', fontsize=9, fontweight='bold', va='center')
    
    ax.set_xlim(-b_max/2 - 0.4, b_max/2 + 0.4)
    ax.set_ylim(-0.4, t_actual + 0.6)
    ax.set_title(f'รูปขยายการจัดเหล็กเสริม ({n_bars_x}-DB{bar_dia} @ {sp_x:.0f} cm)', fontsize=11, fontweight='bold')
    ax.axis('off')
    ax.legend(loc='upper right', fontsize=8, framealpha=0.8)
    return fig

@st.cache_data(show_spinner=False)
def generate_3d_mesh(concrete_vertices_tuple, t_actual, cx, cy, piles_actual_tuple, pile_shape, pile_w, pile_l, embed_m, columns_list_tuple):
    concrete_vertices = list(concrete_vertices_tuple)
    piles_actual = list(piles_actual_tuple)
    columns_list = list(columns_list_tuple)
    
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
        
        return go.Mesh3d(
            x=x_coords, y=y_coords, z=z_coords, i=i_idx, j=j_idx, k=k_idx, 
            color=face_color, opacity=opacity, name=name, showlegend=show_legend,
            lighting=dict(ambient=0.6, diffuse=0.8, roughness=0.4, specular=0.3, fresnel=0.2)
        )

    fig_3d = go.Figure()
    footing_bottom_z = -t_actual
    pile_top_z = footing_bottom_z + embed_m
    pile_bottom_z = footing_bottom_z - 0.8 
    
    fig_3d.add_trace(create_3d_prism_trace(concrete_vertices, footing_bottom_z, 0, '#2ecc71', 0.45, 'คอนกรีตฐานราก'))
    
    for col_x, col_y in columns_list:
        column_vertices = [(col_x-cx/2, col_y-cy/2), (col_x+cx/2, col_y-cy/2), (col_x+cx/2, col_y+cy/2), (col_x-cx/2, col_y+cy/2)]
        fig_3d.add_trace(create_3d_prism_trace(column_vertices, 0, 0.40, '#e74c3c', 0.75, 'เสาตอม่อ', show_legend=False))
    
    for index, p in enumerate(piles_actual):
        px, py = p[0], p[1]
        if pile_shape == "Circular Pile":
            sides = 8
            rad = pile_w / 2
            p_angles = np.linspace(0, 2*np.pi, sides, endpoint=False)
            pile_verts = [(px + rad*math.cos(a), py + rad*math.sin(a)) for a in p_angles]
        else:
            pile_verts = [(px-pile_w/2, py-pile_l/2), (px+pile_w/2, py-pile_l/2), (px+pile_w/2, py+pile_l/2), (px-pile_w/2, py+pile_l/2)]
            
        fig_3d.add_trace(create_3d_prism_trace(pile_verts, pile_bottom_z, pile_top_z, '#7f8c8d', 0.8, f'เสาเข็ม P{index+1}', show_legend=False))
        
        fig_3d.add_trace(go.Scatter3d(
            x=[px], y=[py], z=[pile_top_z + 0.05],
            mode='text', text=[f"P{index+1}"], textposition="top center",
            textfont=dict(color='black', size=10, family="sans-serif"), showlegend=False
        ))

    fig_3d.update_layout(
        scene=dict(
            aspectmode='data',
            xaxis_title='แกน X (ม.)',
            yaxis_title='แกน Y (ม.)',
            zaxis_title='แกน Z (ม.)'
        ),
        margin=dict(l=0, r=0, b=0, t=30)
    )
    return fig_3d

# =========================================================================
# APPLICATION LAYOUT & UI 
# =========================================================================
with st.sidebar:
    st.header("🏗️ ข้อมูลการออกแบบฐานรากตอม่อ V8.5")
    footing_shape_type = st.selectbox("รูปทรงเรขาคณิตและชนิดฐานราก:", 
        ["Truncated Triangular Footing", "Rectangular Footing", "Combined Footing (>= 2 Columns)", "Strap Footing (ชิดเขต)", "Arbitrary Freeform Polygon"], index=0)
    col_position = st.selectbox("ตำแหน่งเสาตอม่อ (Column Position):", ["Interior", "Edge", "Corner"], index=0)
    
    st.subheader("🛠️ User-Defined Load Factors")
    factor_dl = st.number_input("γ_DL (Dead Load Factor)", value=1.2, step=0.1)
    factor_ll = st.number_input("γ_LL (Live Load Factor)", value=1.6, step=0.1)
    
    st.subheader("🌪️ แรงเฉือนแนวราบ & แผ่นดินไหว")
    V_x = st.number_input("แรงเฉือนระดับแนวราบ V_x (ตัน)", value=0.0)
    V_y = st.number_input("แรงเฉือนระดับแนวราบ V_y (ตัน)", value=0.0)
    T_z = st.number_input("แรงบิดบิดหมุนที่หัวเสา T_z (ตัน-เมตร)", value=0.0)

    st.subheader("💧 การควบคุมความกว้างรอยร้าว")
    environmental_condition = st.selectbox("สภาวะการใช้งานควบคุมรอยร้าว:", ["ทั่วไป (สภาวะปกติ - Max 0.30mm)", "โครงสร้างกันน้ำ / กัดกร่อนสูง (Max 0.15mm)"])
    w_allowable = 0.15 if "โครงสร้างกันน้ำ" in environmental_condition else 0.30

    st.subheader("1. การตั้งค่าเสาเข็มและพิกัด As-Built")
    pile_shape = st.selectbox("รูปทรงเสาเข็ม:", ["Circular Pile", "Square/Rectangular Pile"], index=0)
    pile_dia = st.number_input("เส้นผ่านศูนย์กลาง/ความกว้างเสาเข็ม (ม.)", value=0.30, min_value=0.15)
    pile_w = pile_dia; pile_l = pile_dia 
    
    pile_cap = st.number_input("กำลังรับแรงอัดที่ปลอดภัยของเข็ม (ตัน/ต้น)", value=30.0)
    pile_tension_cap = st.number_input("กำลังรับแรงถอนที่ปลอดภัยของเข็ม (ตัน/ต้น)", value=10.0)
    pile_ks = st.number_input("ความแข็งแรงสปริงเสาเข็ม k_s (ตัน/ม.)", value=20000.0, step=1000.0)
    
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
        B_ft = S_dist + 2*E_dist; L_ft = S_dist + 2*E_dist
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
st.markdown("### 📍 1. การวิเคราะห์ As-Built Field Survey เข็มตอม่อ (Flexible Winkler Matrix Method)")
st.info("💡 **ระบบวิเคราะห์ความยืดหยุ่น Winkler Foundation:** ระบบจะคำนวณการกระจายแรงสู่หัวเข็มโดยคำนึงถึงความแอ่นตัวของหน้าตัดคอนกรีตจริง")

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

P_ultimate = (factor_dl * DL) + (factor_ll * LL)
Mu_cx = (factor_dl * Mcx_dl) + (factor_ll * Mcx_ll)
Mu_cy = (factor_dl * Mcy_dl) + (factor_ll * Mcy_ll)

Ms_cx = Mcx_dl + Mcx_ll
Ms_cy = Mcy_dl + Mcy_ll

concrete_vertices = [(v[0] - ecc_x, v[1] - ecc_y) for v in concrete_vertices_base]
footing_area = polygon_area(concrete_vertices)
W_soil = max(0.0, footing_area - (cx*cy)) * soil_depth * soil_density

if thickness_mode == "Auto-Optimize":
    d_opt = 0.30; safe = False; p_ult_out = [0.0] * n_piles
    max_d = 3.0; step = 0.02; loop_counter = 0
    max_loops = int((max_d - 0.30) / step) + 10 
    
    while d_opt <= max_d and loop_counter < max_loops:
        loop_counter += 1
        t_opt = d_opt + max(concrete_cover_cm/100, pile_embed_cm/100) + ((bar_dia/1000)/2)
        safe, v_up, v_cp, v_uwb, v_cwb, p_ult_out = execute_shear_evaluation_routine(
            d_opt, t_opt, footing_area, W_soil, P_ultimate, Mu_cx, Mu_cy, ecc_x, ecc_y, n_piles, piles_relative, piles_actual, I_xx_group, I_yy_group, cx, cy, fc_prime, col_position, concrete_vertices, factor_dl, columns_list, pile_dia=pile_w, I_xy=I_xy_geom, pile_ks=pile_ks
        )
        if safe: break
        d_opt += step
        
    if not safe:
        st.error("🚨 วิกฤต: ไม่สามารถหาความหนาฐานรากที่ปลอดภัยได้ แนะนำให้ขยายขนาดขอบเขตฐานราก หรือเพิ่มจำนวนเสาเข็ม")
        st.stop() 
        
    t_actual = math.ceil(t_opt * 20) / 20; d_actual = d_opt
    # [FIXED] รันซ้ำอีกครั้งด้วยความหนาที่ทำการปัดเศษจริง เพื่อให้แรงเฉือนและปฏิกิริยาสอดคล้องถูกต้อง
    safe, v_up, v_cp, v_uwb, v_cwb, p_ult_out = execute_shear_evaluation_routine(
        d_actual, t_actual, footing_area, W_soil, P_ultimate, Mu_cx, Mu_cy, ecc_x, ecc_y, n_piles, piles_relative, piles_actual, I_xx_group, I_yy_group, cx, cy, fc_prime, col_position, concrete_vertices, factor_dl, columns_list, pile_dia=pile_w, I_xy=I_xy_geom, pile_ks=pile_ks
    )
else:
    t_actual = manual_t
    d_actual = compute_effective_depth(t_actual, concrete_cover_cm, pile_embed_cm, bar_dia)
    safe, v_up, v_cp, v_uwb, v_cwb, p_ult_out = execute_shear_evaluation_routine(
        d_actual, t_actual, footing_area, W_soil, P_ultimate, Mu_cx, Mu_cy, ecc_x, ecc_y, n_piles, piles_relative, piles_actual, I_xx_group, I_yy_group, cx, cy, fc_prime, col_position, concrete_vertices, factor_dl, columns_list, pile_dia=pile_w, I_xy=I_xy_geom, pile_ks=pile_ks
    )

# [FIXED] ประกาศตัวแปร P_u_total ใน Global Scope เพื่อป้องกันข้อผิดพลาด NameError ใน Report Tab
w_u_footing_weight = factor_dl * (footing_area * t_actual * 2.4)
w_u_soil_weight = factor_dl * W_soil
P_u_total = P_ultimate + w_u_footing_weight + w_u_soil_weight

polar_R_sum = sum(prx**2 + pry**2 for prx, pry in piles_relative)
if polar_R_sum == 0: polar_R_sum = 1.0

pile_horizontal_shear = []
for prx, pry in piles_relative:
    V_ix = (V_x / n_piles) - (T_z * pry / polar_R_sum)
    V_iy = (V_y / n_piles) + (T_z * prx / polar_R_sum)
    pile_horizontal_shear.append(math.sqrt(V_ix**2 + V_iy**2))

P_service_total = DL + LL + (footing_area * t_actual * 2.4) + W_soil
Ms_cx_total = Ms_cx + P_service_total * ecc_y
Ms_cy_total = Ms_cy + P_service_total * ecc_x

pile_service_reactions = compute_flexible_reactions(concrete_vertices, piles_actual, columns_list, P_service_total, Ms_cx_total, Ms_cy_total, t_actual, fc_prime, pile_ks)

has_tension = any(r < 0 for r in p_ult_out)
require_top_steel = has_tension or (t_actual >= 0.60) 

Mu_x_top = abs(sum(p_ult_out[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2))
Mu_x_bot = abs(sum(p_ult_out[i] * (abs(p[1]) - cy/2) for i, p in enumerate(piles_actual) if p[1] < -cy/2))
Mu_x_max = max(Mu_x_top, Mu_x_bot)

w_flex_x = get_polygon_section_width_at_y(0, concrete_vertices) * 100
n_bars_x, sp_x, _, as_req_x = design_rebar_by_axis(Mu_x_max, w_flex_x, d_actual*100, t_actual*100, fc_prime, fy, phi_flexure, ab_area, concrete_cover_cm, env_cond=environmental_condition)

Mu_y_top = abs(sum(p_ult_out[i] * (p[0] - cx/2) for i, p in enumerate(piles_actual) if p[0] > cx/2))
Mu_y_bot = abs(sum(p_ult_out[i] * (abs(p[0]) - cx/2) for i, p in enumerate(piles_actual) if p[0] < -cx/2))
Mu_y_max = max(Mu_y_top, Mu_y_bot)

w_flex_left = get_polygon_section_height_at_x(-cx/2.0, concrete_vertices) * 100
w_flex_right = get_polygon_section_height_at_x(cx/2.0, concrete_vertices) * 100
w_flex_y = min(w_flex_left, w_flex_right)

n_bars_y, sp_y, _, as_req_y = design_rebar_by_axis(Mu_y_max, w_flex_y, d_actual*100, t_actual*100, fc_prime, fy, phi_flexure, ab_area, concrete_cover_cm, env_cond=environmental_condition)

Ms_x_top = abs(sum(pile_service_reactions[i] * (p[1] - cy/2) for i, p in enumerate(piles_actual) if p[1] > cy/2))
Ms_x_bot = abs(sum(pile_service_reactions[i] * (abs(p[1]) - cy/2) for i, p in enumerate(piles_actual) if p[1] < -cy/2))
Ms_x_max = max(Ms_x_top, Ms_x_bot)

calculated_w = evaluate_gergely_lutz_crack(Ms_x_max, n_bars_x * ab_area, d_actual*100, concrete_cover_cm, bar_dia, sp_x)

st.markdown("---")

# =========================================================================
# L_d WARNING SECTION
# =========================================================================
max_cantilever_x = max([abs(v[0]) for v in concrete_vertices]) - cx/2
is_ld_ok, req_ld_cm, act_ld_cm = evaluate_development_length(fy, fc_prime, bar_dia, max_cantilever_x, concrete_cover_cm)

if not is_ld_ok:
    st.warning(f"⚠️ **แจ้งเตือนระยะล้วงเกาะ (Development Length):** ระยะยื่นฐานรากฝั่งวิกฤตสั้นเกินไป (ต้องการ L_d = {req_ld_cm:.1f} cm แต่มีระยะเพียง {act_ld_cm:.1f} cm) ระบบแนะนำให้ออกแบบเป็น**งอขอมาตรฐาน (Standard Hook)** หรือปรับขยายขนาดขอบเขตฐานราก")

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
        fig_2d = generate_2d_plan_view(concrete_vertices, cx, cy, piles_actual, pile_shape, pile_w, pile_l, columns_list=columns_list, cg_x=cg_actual_x, cg_y=cg_actual_y)
        st.pyplot(fig_2d)
        plt.close(fig_2d)

    with col_plot2:
        st.markdown("#### 🟥 B) Ultra Section Detailing View")
        if require_top_steel:
            st.info(f"💡 **Top Rebar Activated:** {'เนื่องจากมีเข็มรับแรงถอน (Tension)' if has_tension else f'เนื่องจากฐานรากหนา t={t_actual:.2f}m ≥ 0.60m (กันร้าว)'}")
        fig_rebar = generate_rebar_detailing_view(t_actual, B_max_visual, concrete_cover_cm, pile_embed_cm, bar_dia, n_bars_x, sp_x, cx, cy, require_top_steel)
        st.pyplot(fig_rebar)
        plt.close(fig_rebar)

    st.markdown("#### 🧊 C) 3D Interactive Mesh (Exact Geometry)")
    fig_3d = generate_3d_mesh(tuple(concrete_vertices), t_actual, cx, cy, tuple(piles_actual), pile_shape, pile_w, pile_l, pile_embed_cm / 100, tuple(columns_list))
    st.plotly_chart(fig_3d, use_container_width=True)
