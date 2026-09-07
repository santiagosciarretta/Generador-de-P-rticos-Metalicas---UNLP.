import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd
from fractions import Fraction

# ============================================================================
# CONFIGURACIÓN Y ESTÉTICA (CSS)
# ============================================================================
st.set_page_config(page_title="Generador de Pórticos - UNLP", layout="wide")

# CSS Súper Agresivo (Multiversión) para forzar el tamaño de las pestañas
st.markdown("""
<style>
    div[data-testid="stTabs"] button p,
    div[data-baseweb="tab"] p,
    .stTabs button p,
    .stTabs [data-testid="stMarkdownContainer"] p {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #2E5A88 !important;
    }
    div[data-testid="stTabs"] button {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

st.header("🏗️ Generador Automático de Pórticos - UNLP")
st.markdown("**Ing. Santiago Sciarretta**")
st.markdown("---")

# ============================================================================
# MOTOR DE DATOS: BASE DE PERFILES AISC
# ============================================================================
@st.cache_data
def cargar_base_perfiles():
    df = pd.read_excel("Perfiles AISC.xlsx", header=1)
    df.rename(columns={df.columns[2]: 'AISC_Manual_Label'}, inplace=True)
    df.columns = [str(col).replace('\n', '').replace(' ', '') for col in df.columns]
    return df.dropna(subset=['AISC_Manual_Label'])

df_perfiles = cargar_base_perfiles()

def obtener_propiedades_perfil(nombre_perfil):
    try:
        datos = df_perfiles[df_perfiles['AISC_Manual_Label'] == nombre_perfil].iloc[0]
        
        def buscar_metrica(nombre_columna):
            for key, val in reversed(list(datos.items())):
                base_key = str(key).split('.')[0].lower()
                if base_key == nombre_columna.lower():
                    if pd.notna(val):
                        try:
                            numero = float(val)
                            if numero > 0: return numero
                        except: pass
            return 0.0

        props = {
            'd': buscar_metrica('d') / 100.0,
            'bf': buscar_metrica('bf') / 100.0,
            'tw': buscar_metrica('tw') / 100.0,
            'tf': buscar_metrica('tf') / 100.0,
            'Ix': buscar_metrica('ix'),
            'Iy': buscar_metrica('iy'),
            'rX': buscar_metrica('rx'), # en cm
            'rY': buscar_metrica('ry')  # en cm
        }
        
        if props['d'] == 0:
            return {'d': 0.40, 'bf': 0.20, 'tw': 0.01, 'tf': 0.015, 'Ix': 0, 'Iy': 0, 'rX': 0, 'rY': 0}
        return props
    except Exception as e:
        return {'d': 0.40, 'bf': 0.20, 'tw': 0.01, 'tf': 0.015, 'Ix': 0, 'Iy': 0, 'rX': 0, 'rY': 0}

# ============================================================================
# FUNCIONES DE DIBUJO 3D (Pórtico Global)
# ============================================================================
def dibujar_apoyo_articulado(ax, x, y, escala=0.35):
    vertices = [[x, y], [x-escala, y-escala], [x+escala, y-escala]]
    ax.add_patch(patches.Polygon(vertices, closed=True, edgecolor='black', facecolor='white', linewidth=1.8, zorder=5))
    base = escala * 2.5
    ax.plot([x-base, x+base], [y-escala, y-escala], 'k', linewidth=1.5, zorder=4)
    for i in range(6):
        xr = x - base + (i * base * 2 / 5)
        ax.plot([xr, xr - 0.15], [y-escala, y-escala-0.2], 'k', linewidth=1)

def dibujar_apoyo_empotrado(ax, x, y, escala=0.35):
    base = escala * 2.5
    ax.plot([x - base, x + base], [y, y], 'k', linewidth=2.5, zorder=5)
    for i in range(8):
        xr = x - base + (i * base * 2 / 7)
        ax.plot([xr, xr - 0.15], [y, y - 0.25], 'k', linewidth=1)

def dibujar_arriostramiento_y(ax, x, y):
    dx, dy = -0.45, -0.36
    xf, yf = x + dx, y + dy
    ax.plot([x, xf], [y, yf], color='#0066CC', linestyle='-', linewidth=1.2, zorder=1)
    ax.plot([x], [y], 'o', color='white', markeredgecolor='#0066CC', markeredgewidth=1.8, markersize=6, zorder=5)
    L_hip = np.hypot(dx, dy)
    ux, uy = dx/L_hip, dy/L_hip
    px, py = -uy, ux
    h, w = 0.3, 0.4
    mx, my = xf + ux * h, yf + uy * h
    p2x, p2y = mx + px * (w / 2), my + py * (w / 2)
    p3x, p3y = mx - px * (w / 2), my - py * (w / 2)
    ax.add_patch(patches.Polygon([[xf, yf], [p2x, p2y], [p3x, p3y]], closed=True, edgecolor='#0066CC', facecolor='white', linewidth=1.5, zorder=3))
    ax.plot([p2x, p3x], [p2y, p3y], color='#0066CC', linewidth=1.5, zorder=3)

def dibujar_seccion_ipe(ax, x, y, orientacion='FUERTE', escala=0.45):
    w, h = (1.0 * escala) * 1.5, (0.65 * escala) * 2.0
    ta, tm = 0.16 * escala * 1.5, 0.08 * escala * 1.5
    if orientacion == 'FUERTE':
        ax.add_patch(patches.Rectangle((x - w/2, y - tm/2), w, tm, facecolor='gray', edgecolor='black', alpha=0.7))
        ax.add_patch(patches.Rectangle((x - w/2, y - h/2), ta, h, facecolor='gray', edgecolor='black', alpha=0.7))
        ax.add_patch(patches.Rectangle((x + w/2 - ta, y - h/2), ta, h, facecolor='gray', edgecolor='black', alpha=0.7))
    else:
        ax.add_patch(patches.Rectangle((x - tm/2, y - h/2), tm, h, facecolor='gray', edgecolor='black', alpha=0.7))
        ax.add_patch(patches.Rectangle((x - w/2, y + h/2 - ta), w, ta, facecolor='gray', edgecolor='black', alpha=0.7))
        ax.add_patch(patches.Rectangle((x - w/2, y - h/2), w, ta, facecolor='gray', edgecolor='black', alpha=0.7))
    
    cx, cy = '#CC0000', '#008000'
    ax.annotate('', xy=(x + (w/2 + 0.3), y), xytext=(x, y), arrowprops=dict(arrowstyle='->', color=cx, lw=1.2))
    ax.text(x + (w/2 + 0.4), y - 0.1, 'x', fontsize=9, color=cx, fontweight='bold')
    ax.annotate('', xy=(x, y + (h/2 + 0.3)), xytext=(x, y), arrowprops=dict(arrowstyle='->', color=cy, lw=1.2))
    ax.text(x - 0.15, y + (h/2 + 0.4), 'y', fontsize=9, color=cy, fontweight='bold')

def dibujar_seccion_viga(ax, x, y, orientacion='FUERTE', escala=0.45):
    w, h = (1.0 * escala) * 1.5, (0.65 * escala) * 2.0
    ta, tm = 0.16 * escala * 1.5, 0.08 * escala * 1.5
    if orientacion == 'FUERTE':
        ax.add_patch(patches.Rectangle((x - tm/2, y - h/2), tm, h, facecolor='gray', edgecolor='black', alpha=0.7))
        ax.add_patch(patches.Rectangle((x - w/2, y + h/2 - ta), w, ta, facecolor='gray', edgecolor='black', alpha=0.7))
        ax.add_patch(patches.Rectangle((x - w/2, y - h/2), w, ta, facecolor='gray', edgecolor='black', alpha=0.7))
    else:
        ax.add_patch(patches.Rectangle((x - h/2, y - tm/2), h, tm, facecolor='gray', edgecolor='black', alpha=0.7))
        ax.add_patch(patches.Rectangle((x - h/2, y - w/2), ta, w, facecolor='gray', edgecolor='black', alpha=0.7))
        ax.add_patch(patches.Rectangle((x + h/2 - ta, y - w/2), ta, w, facecolor='gray', edgecolor='black', alpha=0.7))
        
    cy, cz = '#008000', '#0066CC'
    dim_y = w/2 if orientacion == 'FUERTE' else h/2
    dim_z = h/2 if orientacion == 'FUERTE' else w/2
    ax.annotate('', xy=(x + dim_y + 0.3, y), xytext=(x, y), arrowprops=dict(arrowstyle='->', color=cy, lw=1.2))
    ax.text(x + dim_y + 0.4, y - 0.1, 'y', fontsize=9, color=cy, fontweight='bold')
    ax.annotate('', xy=(x, y + dim_z + 0.3), xytext=(x, y), arrowprops=dict(arrowstyle='->', color=cz, lw=1.2))
    ax.text(x - 0.15, y + dim_z + 0.4, 'z', fontsize=9, color=cz, fontweight='bold')

def dibujar_cotas(ax, x1, y1, x2, y2, texto, offset=0.8, orientacion='horizontal'):
    if orientacion == 'horizontal':
        ax.annotate('', xy=(x2, y1 + offset), xytext=(x1, y1 + offset), arrowprops=dict(arrowstyle='<->', lw=1.2))
        ax.text((x1 + x2) / 2, y1 + offset + 0.3, texto, ha='center', va='bottom', fontsize=10, fontweight='bold')
    else:
        ax.annotate('', xy=(x1 - offset, y2), xytext=(x1 - offset, y1), arrowprops=dict(arrowstyle='<->', lw=1.2))
        ax.text(x1 - offset - 0.3, (y1 + y2) / 2, texto, ha='right', va='center', fontsize=10, fontweight='bold', rotation=90)

# ============================================================================
# FUNCIONES DE DIBUJO 2D (Cortes Dinámicos Didácticos - ACTUALIZADO)
# ============================================================================
def graficar_corte_cinematico(orientacion, eje_rotacion):
    """Dibuja la vista superior, perfil proporcionado y vector momento doble punta"""
    fig, ax = plt.subplots(figsize=(3, 3), dpi=100)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_xlim(-1.4, 1.4); ax.set_ylim(-1.4, 1.4)

    # Ejes Globales (Cruz central punteada)
    ax.axhline(0, color='gray', linestyle='--', linewidth=0.8)
    ax.axvline(0, color='gray', linestyle='--', linewidth=0.8)
    ax.text(1.25, 0.05, 'X', color='gray', fontsize=10, fontweight='bold')
    ax.text(0.05, 1.25, 'Y', color='gray', fontsize=10, fontweight='bold')

    # Geometría del Perfil (MUCHO MÁS ESTILIZADO)
    w, h, ta, tm = 0.5, 1.0, 0.08, 0.04 
    
    if orientacion == 'FUERTE':
        ax.add_patch(patches.Rectangle((-w/2, -tm/2), w, tm, facecolor='#A0A0A0', edgecolor='black'))
        ax.add_patch(patches.Rectangle((-w/2, -h/2), ta, h, facecolor='#606060', edgecolor='black'))
        ax.add_patch(patches.Rectangle((w/2-ta, -h/2), ta, h, facecolor='#606060', edgecolor='black'))
        # Textos de ejes locales limpios
        ax.text(0.1, -h/2 - 0.2, 'y', color='#606060', fontsize=11, fontstyle='italic')
        ax.text(-w/2 - 0.25, 0.1, 'x', color='#606060', fontsize=11, fontstyle='italic')
    else:
        ax.add_patch(patches.Rectangle((-tm/2, -h/2), tm, h, facecolor='#A0A0A0', edgecolor='black'))
        ax.add_patch(patches.Rectangle((-w/2, h/2-ta), w, ta, facecolor='#606060', edgecolor='black'))
        ax.add_patch(patches.Rectangle((-w/2, -h/2), w, ta, facecolor='#606060', edgecolor='black'))
        # Textos de ejes locales limpios
        ax.text(0.1, -h/2 - 0.2, 'x', color='#606060', fontsize=11, fontstyle='italic')
        ax.text(-w/2 - 0.25, 0.1, 'y', color='#606060', fontsize=11, fontstyle='italic')

    # DIBUJO DEL VECTOR MOMENTO (Doble punta)
    def dibujar_vector_momento(x0, y0, dx, dy, color, label):
        ax.plot([x0, x0+dx], [y0, y0+dy], color=color, lw=2.5)
        ax.annotate('', xy=(x0+dx, y0+dy), xytext=(x0+dx-dx*0.01, y0+dy-dy*0.01),
                    arrowprops=dict(arrowstyle="->", lw=2.5, color=color, mutation_scale=20))
        offset = 0.15 # Reducido para que las flechas queden más juntas y elegantes
        L = np.hypot(dx, dy)
        ux, uy = dx/L, dy/L
        ax.annotate('', xy=(x0+dx - ux*offset, y0+dy - uy*offset), xytext=(x0+dx - ux*(offset+0.01), y0+dy - uy*(offset+0.01)),
                    arrowprops=dict(arrowstyle="->", lw=2.5, color=color, mutation_scale=20))
        ax.text(x0+dx + ux*0.1 - uy*0.25, y0+dy + uy*0.1 + ux*0.25, label, color=color, fontsize=14, fontweight='bold', ha='center')

    if eje_rotacion == 'Y':
        dibujar_vector_momento(0, -0.65, 0, 1.3, '#CC0000', '$M_Y$')
    else:
        dibujar_vector_momento(-0.65, 0, 1.3, 0, '#0066CC', '$M_X$')

    return fig

# ============================================================================
# INTERFAZ SIDEBAR
# ============================================================================
st.sidebar.header("⚙️ Parámetros")
st.sidebar.markdown("### 1) Definición geométrica")

H = st.sidebar.number_input("Altura (H) [m]", value=5.5)
L = st.sidebar.number_input("Longitud (L) [m]", value=7.0)

SISTEMA = st.sidebar.radio("Sistema Lateral", ["No arriostrado (Translacional)", "Arriostrado (Intranslacional)"])

todas_las_series = df_perfiles.iloc[:, 0].dropna().unique().tolist()
series_permitidas = ["W", "IPE", "IPN", "HEB", "HEA", "UPN"]
series_disponibles = [s for s in series_permitidas if s in todas_las_series]

st.sidebar.markdown("**Columna**")
serie_col = st.sidebar.selectbox("Tipo de Perfil", series_disponibles, index=series_disponibles.index("W") if "W" in series_disponibles else 0, key="tipo_c")
lista_col_filtrada = df_perfiles[df_perfiles.iloc[:, 0] == serie_col]['AISC_Manual_Label'].tolist()
perfil_col = st.sidebar.selectbox("Tamaño", lista_col_filtrada, key="sc")
o_col = st.sidebar.radio("Orientación (Col)", ["FUERTE", "DEBIL"], key="oc", horizontal=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Viga**")
serie_viga = st.sidebar.selectbox("Tipo de Perfil", series_disponibles, index=series_disponibles.index("W") if "W" in series_disponibles else 0, key="tipo_v")
lista_viga_filtrada = df_perfiles[df_perfiles.iloc[:, 0] == serie_viga]['AISC_Manual_Label'].tolist()
perfil_viga = st.sidebar.selectbox("Tamaño", lista_viga_filtrada, key="sv")
o_viga = st.sidebar.radio("Orientación (Viga)", ["FUERTE", "DEBIL"], key="ov", horizontal=True)

st.sidebar.markdown("---")
with st.sidebar.expander("Arriostramientos"):
    NUDOS = st.checkbox("Nudos superior", value=True)
    CANT = st.number_input("Cant. Intermedios", min_value=0, value=2, step=1)
    FRAC = st.slider("Fracción H", 0.1, 1.0, 0.33)

T_APOYO = st.sidebar.selectbox("Apoyo Inferior", ["Empotrado", "Articulado"])

st.sidebar.markdown("---")
st.sidebar.markdown("### 2) Criterios de Cálculo")
CRITERIO = st.sidebar.radio("Condiciones de Borde", ["Sugeridos (AISC/CIRSOC)", "Teóricos Ideales"])

# ============================================================================
# MOTOR CENTRAL DE CÁLCULO Y DIBUJO GLOBAL
# ============================================================================
def generar_datos_y_grafico():
    props_col = obtener_propiedades_perfil(perfil_col)
    props_viga = obtener_propiedades_perfil(perfil_viga)
    
    D_C = props_col['d'] * (0.8/0.40)
    D_V = props_viga['d'] * (0.8/0.40)
    E_ALA_C = max(props_col['tf'] * (0.8/0.40), 0.06)
    E_ALA_V = max(props_viga['tf'] * (0.8/0.40), 0.06)
    
    # --- CÁLCULOS ESTÁTICOS ---
    I_c_plano = props_col['Ix'] if o_col == 'FUERTE' else props_col['Iy']
    I_v_plano = props_viga['Ix'] if o_viga == 'FUERTE' else props_viga['Iy']
    
    r_plano = props_col['rX'] if o_col == 'FUERTE' else props_col['rY']
    r_fuera = props_col['rY'] if o_col == 'FUERTE' else props_col['rX']
    
    G_Y_sup = None
    if I_c_plano > 0 and I_v_plano > 0:
        G_Y_sup = (I_c_plano / (H * 100)) / (I_v_plano / (L * 100))
        
    if T_APOYO == "Empotrado":
        G_Y_inf = 0.0 if CRITERIO == "Teóricos Ideales" else 1.0
        K_X_fuera = 0.70 if CRITERIO == "Teóricos Ideales" else 0.80
    else:
        G_Y_inf = 1000.0 if CRITERIO == "Teóricos Ideales" else 10.0
        K_X_fuera = 1.00 

    # --- DIBUJO ---
    fig, ax = plt.subplots(figsize=(12, 9), dpi=300) 
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_xlim(-4.01, L + 5); ax.set_ylim(-4.01, H + 2)

    cx, cy, cz = '#CC0000', '#008000', '#0066CC'
    xo, yo = -3.5, 0
    ax.annotate('', xy=(xo+1, yo), xytext=(xo, yo), arrowprops=dict(arrowstyle='->', lw=2, color=cx))
    ax.text(xo+1.2, yo, 'X', color=cx, fontweight='bold', va='center')
    ax.annotate('', xy=(xo, yo+1), xytext=(xo, yo), arrowprops=dict(arrowstyle='->', lw=2, color=cz))
    ax.text(xo, yo+1.3, 'Z', color=cz, fontweight='bold', ha='center')
    ax.annotate('', xy=(xo+0.5, yo+0.4), xytext=(xo, yo), arrowprops=dict(arrowstyle='->', lw=2, color=cy))
    ax.text(xo+0.7, yo+0.5, 'Y', color=cy, fontweight='bold', ha='left')
    ax.plot([xo], [yo], 'o', color='black', markersize=4)

    vs, vi = H + D_V/2, H - D_V/2
    for x in [0, L]:
        ax.plot([x-D_C/2, x-D_C/2], [0, vs], 'k', lw=1.5, zorder=1)
        ax.plot([x+D_C/2, x+D_C/2], [0, vs], 'k', lw=1.5, zorder=1)
        ax.plot([x-D_C/2, x+D_C/2], [0, 0], 'k', lw=1.5, zorder=1)
        ax.plot([x-D_C/2, x+D_C/2], [vs, vs], 'k', lw=1.5, zorder=1)
        ax.plot([x, x], [0, H], color='black', linestyle='-.', lw=0.8, zorder=4, snap=True)
        
        if o_col == 'FUERTE':
            ax.plot([x-D_C/2+E_ALA_C, x-D_C/2+E_ALA_C], [0, vs], 'k', lw=1.0, zorder=2)
            ax.plot([x+D_C/2-E_ALA_C, x+D_C/2-E_ALA_C], [0, vs], 'k', lw=1.0, zorder=2)
        else:
            off = max(props_col['tw'] * (0.8/0.40), 0.04) * 2 
            ax.plot([x - off/2, x - off/2], [0, vs], color='#222222', linestyle='--', lw=0.6, zorder=2)
            ax.plot([x + off/2, x + off/2], [0, vs], color='#222222', linestyle='--', lw=0.6, zorder=2)

        if T_APOYO == "Empotrado": dibujar_apoyo_empotrado(ax, x, 0)
        else: dibujar_apoyo_articulado(ax, x, 0)
        dibujar_seccion_ipe(ax, x, -1.5, orientacion=o_col)

    ax.plot([0, L], [H, H], color='black', linestyle='-.', lw=0.8, zorder=4, snap=True)
    xfi, xfd = D_C/2, L - D_C/2
    ax.plot([xfi, xfd], [vi, vi], 'k', lw=1.5, zorder=1)
    ax.plot([xfi, xfd], [vs, vs], 'k', lw=1.5, zorder=1)
    
    if o_viga == 'FUERTE':
        ax.plot([xfi, xfd], [vi+E_ALA_V, vi+E_ALA_V], 'k', lw=1.0, zorder=2)
        ax.plot([xfi, xfd], [vs-E_ALA_V, vs-E_ALA_V], 'k', lw=1.0, zorder=2)
    else:
        off_v = max(props_viga['tw'] * (0.8/0.40), 0.04) * 2
        ax.plot([xfi, xfd], [H - off_v/2, H - off_v/2], color='#222222', linestyle='--', lw=0.6, zorder=2)
        ax.plot([xfi, xfd], [H + off_v/2, H + off_v/2], color='#222222', linestyle='--', lw=0.6, zorder=2)

    dibujar_seccion_viga(ax, L + 1.8, H, orientacion=o_viga)

    if "Arriostrado" in SISTEMA:
        ax.plot([0, L], [0, H], color='#2E5A88', linestyle='--', lw=1.2, zorder=0, alpha=0.8)
        ax.plot([L, 0], [0, H], color='#2E5A88', linestyle='--', lw=1.2, zorder=0, alpha=0.8)

    pos = [H] if NUDOS else []
    dz = FRAC * H
    for i in range(1, int(CANT)+1):
        if i*dz < H-0.1: pos.append(i*dz)
    pos.sort()
    
    for yp in pos:
        dibujar_arriostramiento_y(ax, 0, yp)
        dibujar_arriostramiento_y(ax, L, yp)

    y_p, xc = 0, D_C/2 + 1.0
    for yp in pos:
        dist = yp - y_p
        if dist > 0.1:
            ax.annotate('', xy=(xc, yp), xytext=(xc, y_p), arrowprops=dict(arrowstyle='<->', lw=0.8))
            texto = f"{dist:.2f}m" if abs(dist - dz) >= 0.05 else (f"{FRAC:.2f} H" if abs(FRAC - 1/2) >= 0.001 and abs(FRAC - 1/3) >= 0.001 and abs(FRAC - 1/4) >= 0.001 and abs(FRAC - 1/5) >= 0.001 else f"H/{int(1/FRAC)}")
            ax.text(xc + 0.1, (y_p + yp) / 2, texto, rotation=90, va='center', ha='left', fontsize=9)
        y_p = yp

    dibujar_cotas(ax, 0, 0, 0, H, f'H={H:.2f}m', 1.2, 'vertical')
    dibujar_cotas(ax, 0, H, L, H, f'L={L:.2f}m', 1.0, 'horizontal')

    info = f"TP Nº1 - UNLP\nCol: {perfil_col} ({o_col})\nViga: {perfil_viga} ({o_viga})\nSistema: {SISTEMA.split(' ')[0]}"
    ax.text(L+1.5, 0, info, bbox=dict(boxstyle='round', fc='white', ec='black'), family='monospace', fontsize=10, va='bottom')
   
    return fig, G_Y_sup, G_Y_inf, I_c_plano, I_v_plano, r_plano, r_fuera, K_X_fuera

# ============================================================================
# RENDERIZADO DE PESTAÑAS (TABS)
# ============================================================================
pestana_1, pestana_2 = st.tabs(["📐 Definición Geométrica", "🧮 Cálculo de Esbelteces"])

fig_portico, G_Y_sup, G_Y_inf, I_c_plano, I_v_plano, r_plano, r_fuera, K_X_fuera = generar_datos_y_grafico()

with pestana_1:
    st.pyplot(fig_portico, use_container_width=True)

with pestana_2:
    if G_Y_sup is None or r_plano == 0:
        st.warning("⚠️ Faltan datos mecánicos en el catálogo para procesar los cálculos.")
    else:
        lbl_c_plano = "fuerte" if o_col == "FUERTE" else "débil"
        lbl_v_plano = "fuerte" if o_viga == "FUERTE" else "débil"
        lbl_c_fuera = "débil" if o_col == "FUERTE" else "fuerte"

        # --- SECCIÓN 1: PLANO DEL PÓRTICO ---
        st.header("1. Esbeltez en el plano del pórtico (Rotación s/ Eje Y Global)")
        st.markdown("---")
        
        col_img1, col_calc1 = st.columns([1, 2.5])
        
        with col_img1:
            # TÍTULO CORREGIDO SEGÚN TU PEDIDO
            st.markdown("**Eje de pandeo plano del pórtico ($M_Y$)**")
            fig_corte_y = graficar_corte_cinematico(o_col, 'Y')
            st.pyplot(fig_corte_y, use_container_width=True)
            
        with col_calc1:
            st.subheader("1.1 Cálculo de rigideces relativas ($G_Y$)")
            st.latex(r"G_Y = \frac{\sum (I_{col} / L_{col})}{\sum (I_{viga} / L_{viga})}")
            st.latex(rf"G_{{Y(sup)}} = \frac{{ I_{{\text{{{lbl_c_plano}(col)}}}} / H }}{{ I_{{\text{{{lbl_v_plano}(viga)}}}} / L }}")
            st.latex(rf"G_{{Y(sup)}} = \frac{{{I_c_plano:.1f} \text{{ cm}}^4 / {H*100:.0f} \text{{ cm}}}}{{{I_v_plano:.1f} \text{{ cm}}^4 / {L*100:.0f} \text{{ cm}}}} = {G_Y_sup:.3f}")
            st.info(f"**$G_{{Y(inf)}}$ (Apoyo Inferior) = {G_Y_inf:.2f}**")

            st.subheader("1.2 Factor de longitud efectiva ($K_Y$)")
            if "Arriostrado" in SISTEMA:
                K_Y = (3*G_Y_sup*G_Y_inf + 1.4*(G_Y_sup+G_Y_inf) + 0.64) / (3*G_Y_sup*G_Y_inf + 2.0*(G_Y_sup+G_Y_inf) + 1.28)
                st.latex(r"K_Y = \frac{3 G_A G_B + 1.4(G_A + G_B) + 0.64}{3 G_A G_B + 2.0(G_A + G_B) + 1.28}")
            else:
                K_Y = np.sqrt((1.6*G_Y_sup*G_Y_inf + 4.0*(G_Y_sup+G_Y_inf) + 7.5) / (G_Y_sup + G_Y_inf + 7.5))
                st.latex(r"K_Y = \sqrt{\frac{1.6 G_A G_B + 4.0(G_A + G_B) + 7.5}{G_A + G_B + 7.5}}")
            st.success(f"### $K_Y = {K_Y:.3f}$")

            st.subheader("1.3 Verificación de Esbelteces ($\lambda_Y$)")
            lambda_Y = (K_Y * (H*100)) / r_plano
            st.latex(rf"\lambda_Y = \frac{{K_Y \cdot L_{{col}}}}{{r_{{\text{{{lbl_c_plano}(col)}}}}}}")
            st.latex(rf"\lambda_Y = \frac{{{K_Y:.2f} \cdot {H*100:.0f} \text{{ cm}}}}{{{r_plano:.2f} \text{{ cm}}}} = {lambda_Y:.1f}")
            if lambda_Y <= 200: st.success("✅ Cumple límite de compresión ($\lambda \le 200$)")
            else: st.error("❌ Supera límite de compresión ($\lambda > 200$)")

        # --- SECCIÓN 2: FUERA DEL PLANO ---
        st.write("")
        st.header("2. Esbeltez perpendicular al plano (Rotación s/ Eje X Global)")
        st.markdown("---")
        
        col_img2, col_calc2 = st.columns([1, 2.5])
        
        with col_img2:
            # TÍTULO CORREGIDO SEGÚN TU PEDIDO
            st.markdown("**Eje de pandeo plano perpendicular al pórtico ($M_X$)**")
            fig_corte_x = graficar_corte_cinematico(o_col, 'X')
            st.pyplot(fig_corte_x, use_container_width=True)
            
        with col_calc2:
            st.subheader("2.1 Factor de longitud efectiva ($K_X$)")
            txt_apoyo = "Empotrado (base) - Articulado (riostra/viga)" if T_APOYO == "Empotrado" else "Articulado (base) - Articulado (riostra/viga)"
            st.info(f"**Tramo Evaluado:** Desde apoyo hasta el primer nudo arriostrado.\n\n**Condición:** {txt_apoyo}")
            st.success(f"### $K_X = {K_X_fuera:.2f}$")

            st.subheader("2.2 Verificación de Esbelteces ($\lambda_X$)")
            L_tramo_y = (FRAC * H) * 100
            lambda_X = (K_X_fuera * L_tramo_y) / r_fuera
            st.latex(rf"\lambda_X = \frac{{K_X \cdot L_{{tramo}}}}{{r_{{\text{{{lbl_c_fuera}(col)}}}}}}")
            st.latex(rf"\lambda_X = \frac{{{K_X_fuera:.2f} \cdot {L_tramo_y:.0f} \text{{ cm}}}}{{{r_fuera:.2f} \text{{ cm}}}} = {lambda_X:.1f}")
            if lambda_X <= 200: st.success("✅ Cumple límite de compresión ($\lambda \le 200$)")
            else: st.error("❌ Supera límite de compresión ($\lambda > 200$)")
