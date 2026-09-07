import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd

# ============================================================================
# CONFIGURACIÓN Y ESTÉTICA (CSS)
# ============================================================================
st.set_page_config(page_title="Generador de Pórticos - UNLP", layout="wide")

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #2E5A88 !important;
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
            'rX': buscar_metrica('rx'), 
            'rY': buscar_metrica('ry'),
            'A': buscar_metrica('a'),     # cm2
            'J': buscar_metrica('j'),     # cm4
            'Cw': buscar_metrica('cw')    # cm6
        }
        
        if props['J'] == 0:
            props['J'] = (1/3) * (2 * (props['bf']*100) * (props['tf']*100)**3 + ((props['d']*100) - 2*(props['tf']*100)) * (props['tw']*100)**3)
        if props['Cw'] == 0:
            h0_cm = (props['d'] - props['tf']) * 100
            props['Cw'] = (props['Iy'] * h0_cm**2) / 4.0

        if props['d'] == 0:
            return {'d': 0.40, 'bf': 0.20, 'tw': 0.01, 'tf': 0.015, 'Ix': 0, 'Iy': 0, 'rX': 0, 'rY': 0, 'A': 0, 'J': 0, 'Cw': 0}
        return props
    except Exception:
        return {'d': 0.40, 'bf': 0.20, 'tw': 0.01, 'tf': 0.015, 'Ix': 0, 'Iy': 0, 'rX': 0, 'rY': 0, 'A': 0, 'J': 0, 'Cw': 0}

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
    ax.text(x + (w/2 + 0.4), y - 0.1, 'X', fontsize=9, color=cx, fontweight='bold')
    ax.annotate('', xy=(x, y + (h/2 + 0.3)), xytext=(x, y), arrowprops=dict(arrowstyle='->', color=cy, lw=1.2))
    ax.text(x - 0.15, y + (h/2 + 0.4), 'Y', fontsize=9, color=cy, fontweight='bold')

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
    ax.text(x + dim_y + 0.4, y - 0.1, 'Y', fontsize=9, color=cy, fontweight='bold')
    ax.annotate('', xy=(x, y + dim_z + 0.3), xytext=(x, y), arrowprops=dict(arrowstyle='->', color=cz, lw=1.2))
    ax.text(x - 0.15, y + dim_z + 0.4, 'Z', fontsize=9, color=cz, fontweight='bold')

def dibujar_cotas(ax, x1, y1, x2, y2, texto, offset=0.8, orientacion='horizontal'):
    if orientacion == 'horizontal':
        ax.annotate('', xy=(x2, y1 + offset), xytext=(x1, y1 + offset), arrowprops=dict(arrowstyle='<->', lw=1.2))
        ax.text((x1 + x2) / 2, y1 + offset + 0.3, texto, ha='center', va='bottom', fontsize=10, fontweight='bold')
    else:
        ax.annotate('', xy=(x1 - offset, y2), xytext=(x1 - offset, y1), arrowprops=dict(arrowstyle='<->', lw=1.2))
        ax.text(x1 - offset - 0.3, (y1 + y2) / 2, texto, ha='right', va='center', fontsize=10, fontweight='bold', rotation=90)

def graficar_corte_cinematico_real(orientacion, eje_rotacion, d, bf, tw, tf):
    fig, ax = plt.subplots(figsize=(3, 3), dpi=100)
    ax.set_aspect('equal')
    ax.axis('off')
    
    limite = max(d, bf) * 0.75 
    ax.set_xlim(-limite, limite)
    ax.set_ylim(-limite, limite)

    ax.axhline(0, color='gray', linestyle='--', linewidth=0.8)
    ax.axvline(0, color='gray', linestyle='--', linewidth=0.8)
    ax.text(limite*0.85, 0.05*limite, 'X', color='gray', fontsize=10, fontweight='bold')
    ax.text(0.05*limite, limite*0.85, 'Y', color='gray', fontsize=10, fontweight='bold')

    if orientacion == 'FUERTE':
        w, h = d, bf 
        ax.add_patch(patches.Rectangle((-w/2 + tf, -tw/2), w - 2*tf, tw, facecolor='#A0A0A0', edgecolor='black'))
        ax.add_patch(patches.Rectangle((w/2 - tf, -h/2), tf, h, facecolor='#606060', edgecolor='black'))
        ax.add_patch(patches.Rectangle((-w/2, -h/2), tf, h, facecolor='#606060', edgecolor='black'))
    else:
        w, h = bf, d
        ax.add_patch(patches.Rectangle((-tw/2, -h/2 + tf), tw, h - 2*tf, facecolor='#A0A0A0', edgecolor='black'))
        ax.add_patch(patches.Rectangle((-w/2, h/2 - tf), w, tf, facecolor='#606060', edgecolor='black'))
        ax.add_patch(patches.Rectangle((-w/2, -h/2), w, tf, facecolor='#606060', edgecolor='black'))

    def dibujar_vector_rotacion(x0, y0, dx, dy, color, label):
        ax.plot([x0, x0+dx], [y0, y0+dy], color=color, lw=2.5)
        ax.annotate('', xy=(x0+dx, y0+dy), xytext=(x0+dx-dx*0.01, y0+dy-dy*0.01),
                    arrowprops=dict(arrowstyle="->", lw=2.5, color=color, mutation_scale=20))
        offset = limite * 0.12 
        L = np.hypot(dx, dy)
        ux, uy = dx/L, dy/L
        ax.annotate('', xy=(x0+dx - ux*offset, y0+dy - uy*offset), xytext=(x0+dx - ux*(offset+0.01), y0+dy - uy*(offset+0.01)),
                    arrowprops=dict(arrowstyle="->", lw=2.5, color=color, mutation_scale=20))
        ax.text(x0+dx + ux*limite*0.1 - uy*limite*0.2, y0+dy + uy*limite*0.1 + ux*limite*0.2, label, color=color, fontsize=14, fontweight='bold', ha='center')

    if eje_rotacion == 'Y':
        dibujar_vector_rotacion(0, -limite*0.7, 0, limite*1.4, '#CC0000', r'$\theta_Y$')
    else:
        dibujar_vector_rotacion(-limite*0.7, 0, limite*1.4, 0, '#0066CC', r'$\theta_X$')

    return fig

# ============================================================================
# INTERFAZ SIDEBAR
# ============================================================================
st.sidebar.header("⚙️ Parámetros")
st.sidebar.markdown("### 1) Materiales (Acero)")

region_acero = st.sidebar.selectbox("Norma / Región", ["Argentina (IRAM-IAS / CIRSOC)", "Americana (ASTM)", "Personalizado"])

if region_acero == "Argentina (IRAM-IAS / CIRSOC)":
    tipo_acero = st.sidebar.selectbox("Calidad", ["F-24 (Fy=235 MPa)", "F-26 (Fy=250 MPa)", "F-36 (Fy=355 MPa)"])
    if "F-24" in tipo_acero: Fy, Fu = 235, 370
    elif "F-26" in tipo_acero: Fy, Fu = 250, 400
    else: Fy, Fu = 355, 510
    E_acero = 200000
elif region_acero == "Americana (ASTM)":
    tipo_acero = st.sidebar.selectbox("Calidad", ["A36 (Fy=250 MPa)", "A572 Gr. 50 (Fy=345 MPa)", "A992 (Fy=345 MPa)"])
    if "A36" in tipo_acero: Fy, Fu = 250, 400
    else: Fy, Fu = 345, 450
    E_acero = 200000
else:
    Fy = st.sidebar.number_input("Fluencia Fy (MPa)", value=250)
    Fu = st.sidebar.number_input("Rotura Fu (MPa)", value=400)
    E_acero = st.sidebar.number_input("Módulo E (MPa)", value=200000)

st.sidebar.markdown("---")
st.sidebar.markdown("### 2) Definición geométrica")

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
st.sidebar.markdown("### 3) Criterios de Cálculo")
CRITERIO = st.sidebar.radio("Condiciones de Borde (para cálculo de G y K)", ["Sugeridos (AISC/CIRSOC)", "Teóricos Ideales"])
CW_CRITERIO = st.selectbox("Constante de Alabeo ($C_w$)", ["Exacto (Catálogo AISC)", "Teórico Simplificado (Doble T)"])

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
    
    I_c_plano = props_col['Ix'] if o_col == 'FUERTE' else props_col['Iy']
    I_v_plano = props_viga['Ix'] if o_viga == 'FUERTE' else props_viga['Iy']
    
    r_plano = props_col['rX'] if o_col == 'FUERTE' else props_col['rY']
    r_fuera = props_col['rY'] if o_col == 'FUERTE' else props_col['rX']
    
    G_Y_sup = None
    if I_c_plano > 0 and I_v_plano > 0:
        G_Y_sup = (I_c_plano / (H * 100)) / (I_v_plano / (L * 100))
        
    if T_APOYO == "Empotrado":
        G_Y_inf = 0.0 if CRITERIO == "Teóricos Ideales" else 1.0
        K_X_base = 0.70 if CRITERIO == "Teóricos Ideales" else 0.80
    else:
        G_Y_inf = 1000.0 if CRITERIO == "Teóricos Ideales" else 10.0
        K_X_base = 1.00 

    # --- ANÁLISIS MULTI-TRAMO FUERA DEL PLANO (EJE X) ---
    pos_y = [0.0]
    if NUDOS: pos_y.append(H)
    dz = FRAC * H
    for i in range(1, int(CANT)+1):
        if i*dz < H-0.1: pos_y.append(i*dz)
    pos_y.append(H)
    pos_y = sorted(list(set(pos_y)))
    
    tramos_fuera = []
    for i in range(len(pos_y)-1):
        y_ini, y_fin = pos_y[i], pos_y[i+1]
        long_tramo_cm = (y_fin - y_ini) * 100
        if i == 0:
            k_tramo = K_X_base
            desc_tramo = f"Inferior ({y_ini:.2f}m - {y_fin:.2f}m)"
        else:
            k_tramo = 1.00
            desc_tramo = f"Superior/Intermedio ({y_ini:.2f}m - {y_fin:.2f}m)"
        kl_tramo = k_tramo * long_tramo_cm
        tramos_fuera.append({'desc': desc_tramo, 'k': k_tramo, 'L': long_tramo_cm, 'KL': kl_tramo})
    
    tramo_peor = max(tramos_fuera, key=lambda t: t['KL'])
    K_X_fuera = tramo_peor['k']
    L_tramo_y = tramo_peor['L']

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
   
    return fig, G_Y_sup, G_Y_inf, I_c_plano, I_v_plano, r_plano, r_fuera, K_X_fuera, props_col, tramos_fuera, tramo_peor, L_tramo_y

# ============================================================================
# RENDERIZADO DE PESTAÑAS (TABS)
# ============================================================================
pestana_1, pestana_2, pestana_3 = st.tabs(["📐 Geometría", "🧮 Esbelteces", "🛡️ Resistencia de Diseño"])

fig_portico, G_Y_sup, G_Y_inf, I_c_plano, I_v_plano, r_plano, r_fuera, K_X_fuera, props_col, tramos_fuera, tramo_peor, L_tramo_y = generar_datos_y_grafico()

with pestana_1:
    st.pyplot(fig_portico, use_container_width=True)

with pestana_2:
    st.write("<br>", unsafe_allow_html=True)
    
    if G_Y_sup is None or r_plano == 0:
        st.warning("⚠️ Faltan datos mecánicos en el catálogo para procesar los cálculos.")
    else:
        lbl_c_plano = "fuerte" if o_col == "FUERTE" else "débil"
        lbl_v_plano = "fuerte" if o_viga == "FUERTE" else "débil"
        lbl_c_fuera = "débil" if o_col == "FUERTE" else "fuerte"

        # --- SECCIÓN 1: PLANO DEL PÓRTICO ---
        st.subheader("1. Esbeltez en el plano del pórtico (Rotación s/ Eje Y Global)")
        st.markdown("---")
        
        col_img1, col_calc1 = st.columns([1, 2.5])
        
        with col_img1:
            st.markdown("**Eje de pandeo plano del pórtico**")
            fig_corte_y = graficar_corte_cinematico_real(o_col, 'Y', props_col['d'], props_col['bf'], props_col['tw'], props_col['tf'])
            st.pyplot(fig_corte_y, use_container_width=True)
            
        with col_calc1:
            st.markdown("**1.1 Cálculo de rigideces relativas ($G_Y$)**")
            st.latex(r"G_Y = \frac{\sum (I_{col} / L_{col})}{\sum (I_{viga} / L_{viga})}")
            st.latex(rf"G_{{Y(sup)}} = \frac{{ I_{{\text{{{lbl_c_plano}(col)}}}} / H }}{{ I_{{\text{{{lbl_v_plano}(viga)}}}} / L }}")
            st.latex(rf"G_{{Y(sup)}} = \frac{{{I_c_plano:.1f} \text{{ cm}}^4 / {H*100:.0f} \text{{ cm}}}}{{{I_v_plano:.1f} \text{{ cm}}^4 / {L*100:.0f} \text{{ cm}}}}")
            st.latex(rf"G_{{Y(sup)}} = {G_Y_sup:.3f}")
            st.latex(rf"G_{{Y(inf)}} = {G_Y_inf:.2f} \quad \text{{(Apoyo {T_APOYO})}}")

            st.write("")
            st.markdown("**1.2 Factor de longitud efectiva ($K_Y$)**")
            if "Arriostrado" in SISTEMA:
                K_Y = (3*G_Y_sup*G_Y_inf + 1.4*(G_Y_sup+G_Y_inf) + 0.64) / (3*G_Y_sup*G_Y_inf + 2.0*(G_Y_sup+G_Y_inf) + 1.28)
                st.latex(r"K_Y = \frac{3 G_A G_B + 1.4(G_A + G_B) + 0.64}{3 G_A G_B + 2.0(G_A + G_B) + 1.28}")
            else:
                K_Y = np.sqrt((1.6*G_Y_sup*G_Y_inf + 4.0*(G_Y_sup+G_Y_inf) + 7.5) / (G_Y_sup + G_Y_inf + 7.5))
                st.latex(r"K_Y = \sqrt{\frac{1.6 G_A G_B + 4.0(G_A + G_B) + 7.5}{G_A + G_B + 7.5}}")
            
            st.latex(rf"K_Y = {K_Y:.3f}")

            st.write("")
            st.markdown("**1.3 Verificación de Esbelteces ($\lambda_Y$)**")
            lambda_Y = (K_Y * (H*100)) / r_plano
            st.latex(rf"\lambda_Y = \frac{{K_Y \cdot L_{{col}}}}{{r_{{\text{{{lbl_c_plano}(col)}}}}}}")
            st.latex(rf"\lambda_Y = \frac{{{K_Y:.2f} \cdot {H*100:.0f} \text{{ cm}}}}{{{r_plano:.2f} \text{{ cm}}}}")
            st.latex(rf"\lambda_Y = {lambda_Y:.1f}")
            if lambda_Y <= 200: st.success("✅ Cumple límite de compresión ($\lambda \le 200$)")
            else: st.error("❌ Supera límite de compresión ($\lambda > 200$)")

        # --- SECCIÓN 2: FUERA DEL PLANO ---
        st.write("<br><br>", unsafe_allow_html=True)
        st.subheader("2. Esbeltez perpendicular al plano (Rotación s/ Eje X Global)")
        st.markdown("---")
        
        col_img2, col_calc2 = st.columns([1, 2.5])
        
        with col_img2:
            st.markdown("**Eje de pandeo plano perpendicular al pórtico**")
            fig_corte_x = graficar_corte_cinematico_real(o_col, 'X', props_col['d'], props_col['bf'], props_col['tw'], props_col['tf'])
            st.pyplot(fig_corte_x, use_container_width=True)
            
        with col_calc2:
            st.markdown("**2.1 Análisis de tramos y Factor de longitud efectiva ($K_X$)**")
            
            resumen_tramos = ""
            for t in tramos_fuera:
                resumen_tramos += f"- **Tramo {t['desc']}:** $L = {t['L']:.1f}\\text{{ cm}}$, $K = {t['k']:.2f} \\implies K \\cdot L = {t['KL']:.1f}\\text{{ cm}}$\n"
            st.markdown(resumen_tramos)
            st.info(f"👉 **Tramo Crítico Adoptado:** {tramo_peor['desc']} con $K_X = {K_X_fuera:.2f}$")

            st.write("")
            st.markdown("**2.2 Verificación de Esbelteces ($\lambda_X$)**")
            lambda_X = (K_X_fuera * L_tramo_y) / r_fuera
            st.latex(rf"\lambda_X = \frac{{K_X \cdot L_{{tramo}}}}{{r_{{\text{{{lbl_c_fuera}(col)}}}}}}")
            st.latex(rf"\lambda_X = \frac{{{K_X_fuera:.2f} \cdot {L_tramo_y:.0f} \text{{ cm}}}}{{{r_fuera:.2f} \text{{ cm}}}}")
            st.latex(rf"\lambda_X = {lambda_X:.1f}")
            if lambda_X <= 200: st.success("✅ Cumple límite de compresión ($\lambda \le 200$)")
            else: st.error("❌ Supera límite de compresión ($\lambda > 200$)")

        # --- SECCIÓN 3: ESBELTEZ DE DISEÑO ---
        st.write("<br><br>", unsafe_allow_html=True)
        st.subheader("3. Cálculo de Esbeltez de Diseño Máxima ($\lambda_{max}$)")
        st.markdown("---")
        lambda_max = max(lambda_X, lambda_Y)
        st.latex(rf"\lambda_{{max}} = \max(\lambda_X, \lambda_Y) = \max({lambda_X:.1f}, {lambda_Y:.1f}) = {lambda_max:.1f}")
        st.success(f"### Valor adoptado para control global: $\lambda_{{max}} = {lambda_max:.1f}$")

with pestana_3:
    st.write("<br>", unsafe_allow_html=True)
    if G_Y_sup is None or r_plano == 0:
        st.warning("⚠️ Calcula primero las esbelteces en la pestaña anterior.")
    else:
        st.subheader("Resumen de Parámetros Intermedios de Cálculo")
        with st.expander("🔍 Ver desglose de inercias, radios de giro y longitudes efectivas", expanded=True):
            col_res1, col_res2, col_res3 = st.columns(3)
            with col_res1:
                st.markdown(f"**Geometría Global:**\n- Altura $H = {H*100:.0f}$ cm\n- Longitud $L = {L*100:.0f}$ cm\n- Perfil Columna: `{perfil_col}` ({o_col})")
            with col_res2:
                st.markdown(f"**Inercias y Radios:**\n- $I_{{col}} = {I_c_plano:.1f}$ cm$^4$\n- $I_{{viga}} = {I_v_plano:.1f}$ cm$^4$\n- $r_{{fuerte}} = {r_plano:.2f}$ cm\n- $r_{{débil}} = {r_fuera:.2f}$ cm")
            with col_res3:
                st.markdown(f"**Factores y Esbelteces:**\n- $G_Y$ sup/inf = {G_Y_sup:.3f} / {G_Y_inf:.2f}\n- $K_Y = {K_Y:.3f}$ | $\\lambda_Y = {lambda_Y:.1f}$\n- $K_X = {K_X_fuera:.2f}$ | $\\lambda_X = {lambda_X:.1f}$\n- **$\\lambda_{{max}} = {lambda_max:.1f}$**")

        st.markdown("---")
        st.subheader("4. Verificación y Resistencia de Diseño a Compresión")

        col_mat, col_local = st.columns(2)
        
        with col_mat:
            st.markdown("**4.1 Propiedades del Material**")
            st.info(f"**Acero:** {tipo_acero if 'tipo_acero' in locals() else 'Personalizado'}")
            st.latex(rf"F_y = {Fy} \text{{ MPa}}")
            st.latex(rf"E = {E_acero} \text{{ MPa}}")
        
        with col_local:
            st.markdown("**4.2 Clasificación de la Sección (Esbeltez Local)**")
            
            bf_cm, tf_cm, tw_cm, d_cm = props_col['bf']*100, props_col['tf']*100, props_col['tw']*100, props_col['d']*100
            
            # Alas (Tabla B4.1.A - Caso 2)
            lambda_f = bf_cm / (2 * tf_cm)
            lambda_rf = 0.56 * np.sqrt(E_acero / Fy)
            st.markdown("*(Tabla B4.1.A - Caso 2)*")
            st.latex(rf"\lambda_f = \frac{{b_f}}{{2 t_f}} = \frac{{{bf_cm:.1f}}}{{{2} \cdot {tf_cm:.2f}}} = {lambda_f:.2f}")
            st.latex(rf"\lambda_{{r}} = 0.56 \\sqrt{{\frac{{E}}{{F_y}}}} = {lambda_rf:.2f}")
            ala_esbelta = lambda_f > lambda_rf
            if not ala_esbelta: st.success("Alas: No Esbeltas ✅")
            else: st.error("Alas: Esbeltas ❌")
            
            # Alma (Tabla B4.1.A - Caso 5)
            hw_cm = d_cm - 2*tf_cm
            lambda_w = hw_cm / tw_cm
            lambda_rw = 1.49 * np.sqrt(E_acero / Fy)
            st.markdown("*(Tabla B4.1.A - Caso 5)*")
            st.latex(rf"\lambda_w = \frac{{h_w}}{{t_w}} = \frac{{{hw_cm:.1f}}}{{{tw_cm:.2f}}} = {lambda_w:.2f}")
            st.latex(rf"\lambda_{{r}} = 1.49 \\sqrt{{\frac{{E}}{{F_y}}}} = {lambda_rw:.2f}")
            alma_esbelta = lambda_w > lambda_rw
            if not alma_esbelta: st.success("Alma: No Esbelta ✅")
            else: st.error("Alma: Esbelta ❌")
            
            if not ala_esbelta and not alma_esbelta:
                st.info("**Clasificación Global:** SECCIÓN NO ESBELTA *(Alas y alma no esbeltas)*")
            else:
                st.warning("**Clasificación Global:** SECCIÓN ESBELTA *(Elementos esbeltos presentes)*")

        st.markdown("---")
        
        col_Fe, col_Fcr = st.columns(2)
        
        with col_Fe:
            st.markdown("**4.3 Tensiones Elásticas de Pandeo ($F_e$)**")
            
            st.markdown("*a) Pandeo Flexional (AISC Eq. E3-4)*")
            Fe_flex = (np.pi**2 * E_acero) / (lambda_max**2)
            st.latex(r"F_{{e(\text{{flex}})}} = \frac{\pi^2 E}{(K_y L_y / r)^2}")
            st.latex(rf"F_{{e(\text{{flex}})}} = \frac{{\pi^2 \cdot {E_acero}}}{{{lambda_max:.1f}^2}} = {Fe_flex:.1f} \text{{ MPa}}")
            
            st.markdown("*b) Pandeo Torsional / Flexotorsional (AISC Eq. E4-4)*")
            G_acero = E_acero / (2 * (1 + 0.3)) 
            Ix_cm4, Iy_cm4, J_cm4 = props_col['Ix'], props_col['Iy'], props_col['J']
            
            if CW_CRITERIO == "Exacto (Catálogo AISC)":
                Cw_cm6 = props_col['Cw']
                st.caption(f"Valor extraído de catálogo: $C_w = {Cw_cm6:.1f} \\text{{ cm}}^6$")
            else:
                h0_cm = d_cm - tf_cm
                Cw_cm6 = (Iy_cm4 * (h0_cm)**2) / 4.0
                st.latex(rf"C_w \approx \frac{{I_y \cdot h_0^2}}{{4}} = \frac{{{Iy_cm4:.1f} \cdot {h0_cm:.1f}^2}}{{4}} = {Cw_cm6:.1f} \text{{ cm}}^6")
            
            E_cm = E_acero / 10
            G_cm = G_acero / 10
            Lz_cm = L_tramo_y
            Kz_Lz = K_X_fuera * Lz_cm
            
            st.latex(r"F_{{e(\text{{tors}})}} = \left[ \frac{\pi^2 E C_w}{(K_z L_z)^2} + G J \right] \frac{1}{I_x + I_y}")
            
            Fe_tors_cm = (((np.pi**2 * E_cm * Cw_cm6) / (Kz_Lz**2)) + (G_cm * J_cm4)) / (Ix_cm4 + Iy_cm4)
            Fe_tors = Fe_tors_cm * 10 
            st.latex(rf"F_{{e(\text{{tors}})}} = {Fe_tors:.1f} \text{{ MPa}}")

        with col_Fcr:
            st.markdown("**4.4 Tensión Crítica ($F_{cr}$) y Resistencia Nominal ($P_n$)**")
            Fe = min(Fe_flex, Fe_tors)
            relacion = Fy / Fe
            
            st.info(f"**Tensión elástica mínima gobernante:** $F_e = {Fe:.1f}$ MPa")
            st.latex(rf"\frac{{F_y}}{{F_e}} = \frac{{{Fy}}}{{{Fe:.1f}}} = {relacion:.2f}")
            
            if relacion <= 2.25:
                Fcr = (0.658 ** relacion) * Fy
                st.markdown("*(AISC Eq. E3-2: Pandeo Inelástico)*")
                st.latex(r"F_{{cr}} = \left[ 0.658^{{F_y/F_e}} \right] F_y")
                st.latex(rf"F_{{cr}} = \left( 0.658^{{{relacion:.2f}}} \right) \cdot {Fy} = {Fcr:.1f} \text{{ MPa}}")
            else:
                Fcr = 0.877 * Fe
                st.markdown("*(AISC Eq. E3-3: Pandeo Elástico)*")
                st.latex(r"F_{{cr}} = 0.877 F_e")
                st.latex(rf"F_{{cr}} = 0.877 \cdot {Fe:.1f} = {Fcr:.1f} \text{{ MPa}}")

            st.markdown("*(AISC Eq. E3-1: Resistencia Nominal)*")
            Ag = props_col['A']
            Pn_kN = (Fcr * Ag) / 10
            st.latex(rf"P_n = F_{{cr}} \cdot A_g = {Fcr:.1f} \text{{ MPa}} \cdot {Ag:.2f} \text{{ cm}}^2 / 10 = {Pn_kN:.1f} \text{{ kN}}")

        st.markdown("---")
        st.markdown("**4.5 Resistencia de Diseño ($P_d$)**")
        Pd_kN = 0.90 * Pn_kN
        st.latex(r"P_d = \phi_c \cdot P_n \quad (\phi_c = 0.90)")
        st.latex(rf"P_d = 0.90 \cdot {Pn_kN:.1f} \text{{ kN}} = {Pd_kN:.1f} \text{{ kN}}")
