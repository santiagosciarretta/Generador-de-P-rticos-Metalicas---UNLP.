import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd
from fractions import Fraction

# ============================================================================
# CONFIGURACIÓN Y CÁLCULOS
# ============================================================================
st.set_page_config(page_title="Generador de Pórticos - UNLP", layout="wide")

st.title("🏗️ Generador Automático de Pórticos - UNLP")
st.markdown("### Ing. Santiago Sciarretta")

# ============================================================================
# MOTOR DE DATOS: BASE DE PERFILES AISC
# ============================================================================
@st.cache_data
def cargar_base_perfiles():
    """Lee el Excel y limpia los nombres sin borrar ninguna columna para evitar desfasajes"""
    df = pd.read_excel("Perfiles AISC.xlsx", header=1)
    
    # Renombramos la columna 3 (índice 2) forzadamente para asegurar el Label
    df.rename(columns={df.columns[2]: 'AISC_Manual_Label'}, inplace=True)
    
    # Limpiamos todos los encabezados (quitamos espacios y saltos de línea molestos)
    df.columns = [str(col).replace('\n', '').replace(' ', '') for col in df.columns]
    
    # Nos quedamos solo con las filas que son perfiles reales
    df_metrico = df.dropna(subset=['AISC_Manual_Label'])
    
    return df_metrico

df_perfiles = cargar_base_perfiles()
lista_perfiles_totales = df_perfiles['AISC_Manual_Label'].tolist()

def obtener_propiedades_perfil(nombre_perfil):
    """Busca las propiedades leyendo celda por celda y asumiendo dimensiones en CENTÍMETROS"""
    try:
        datos = df_perfiles[df_perfiles['AISC_Manual_Label'] == nombre_perfil].iloc[0]
        
        def buscar_metrica(nombre_columna):
            for key, val in reversed(list(datos.items())):
                base_key = str(key).split('.')[0].lower()
                if base_key == nombre_columna.lower():
                    if pd.notna(val):
                        try:
                            numero = float(val)
                            if numero > 0:
                                return numero
                        except:
                            pass
            return 0.0

        # Dividimos por 100.0 porque la tabla está en cm (no en mm)
        props = {
            'd': buscar_metrica('d') / 100.0,       # Peralte (de cm a m)
            'bf': buscar_metrica('bf') / 100.0,     # Ancho ala (de cm a m)
            'tw': buscar_metrica('tw') / 100.0,     # Espesor alma (de cm a m)
            'tf': buscar_metrica('tf') / 100.0,     # Espesor ala (de cm a m)
            'Ix': buscar_metrica('ix'),             # Inercia X (queda en cm4)
            'Iy': buscar_metrica('iy')              # Inercia Y (queda en cm4)
        }
        
        # Rescate si por algún motivo la tabla no tenía la altura cargada
        if props['d'] == 0:
            return {'d': 0.40, 'bf': 0.20, 'tw': 0.01, 'tf': 0.015, 'Ix': 0, 'Iy': 0}
            
        return props
    except Exception as e:
        st.error(f"Error procesando {nombre_perfil}: {e}")
        return {'d': 0.40, 'bf': 0.20, 'tw': 0.01, 'tf': 0.015, 'Ix': 0, 'Iy': 0}

# ============================================================================
# FUNCIONES DE DIBUJO
# ============================================================================

def dibujar_apoyo_articulado(ax, x, y, escala=0.35):
    vertices = [[x, y], [x-escala, y-escala], [x+escala, y-escala]]
    triangle = patches.Polygon(vertices, closed=True, edgecolor='black', facecolor='white', linewidth=1.8, zorder=5)
    ax.add_patch(triangle)
    base_width = escala * 2.5
    ax.plot([x-base_width, x+base_width], [y-escala, y-escala], 'k', linewidth=1.5, zorder=4)
    for i in range(6):
        x_raya = x - base_width + (i * base_width * 2 / 5)
        ax.plot([x_raya, x_raya - 0.15], [y-escala, y-escala-0.2], 'k', linewidth=1)

def dibujar_apoyo_empotrado(ax, x, y, escala=0.35):
    ancho_base = escala * 2.5
    ax.plot([x - ancho_base, x + ancho_base], [y, y], 'k', linewidth=2.5, zorder=5)
    for i in range(8):
        x_raya = x - ancho_base + (i * ancho_base * 2 / 7)
        ax.plot([x_raya, x_raya - 0.15], [y, y - 0.25], 'k', linewidth=1)

def dibujar_arriostramiento_y(ax, x, y):
    dx, dy = -0.45, -0.36
    xf, yf = x + dx, y + dy
    ax.plot([x, xf], [y, yf], color='#0066CC', linestyle='-', linewidth=1.2, zorder=1)
    ax.plot([x], [y], 'o', color='white', markeredgecolor='#0066CC', markeredgewidth=1.8, markersize=6, zorder=5)
    L_hip = np.hypot(dx, dy)
    ux, uy = dx/L_hip, dy/L_hip
    px, py = -uy, ux
    h_tri, w_tri = 0.3, 0.4
    mx, my = xf + ux * h_tri, yf + uy * h_tri
    p2x, p2y = mx + px * (w_tri / 2), my + py * (w_tri / 2)
    p3x, p3y = mx - px * (w_tri / 2), my - py * (w_tri / 2)
    tri = patches.Polygon([[xf, yf], [p2x, p2y], [p3x, p3y]], closed=True, edgecolor='#0066CC', facecolor='white', linewidth=1.5, zorder=3)
    ax.add_patch(tri)
    ax.plot([p2x, p3x], [p2y, p3y], color='#0066CC', linewidth=1.5, zorder=3)

def dibujar_seccion_ipe(ax, x, y, orientacion='FUERTE', escala=0.45):
    """Sección en planta de la columna"""
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
    
    # Ejes Locales en la Planta (X=Rojo, Y=Verde)
    color_x, color_y = '#CC0000', '#008000'
    ax.annotate('', xy=(x + (w/2 + 0.3), y), xytext=(x, y), arrowprops=dict(arrowstyle='->', color=color_x, lw=1.2))
    ax.text(x + (w/2 + 0.4), y - 0.1, 'x', fontsize=9, color=color_x, fontweight='bold')
    ax.annotate('', xy=(x, y + (h/2 + 0.3)), xytext=(x, y), arrowprops=dict(arrowstyle='->', color=color_y, lw=1.2))
    ax.text(x - 0.15, y + (h/2 + 0.4), 'y', fontsize=9, color=color_y, fontweight='bold')

def dibujar_seccion_viga(ax, x, y, orientacion='FUERTE', escala=0.45):
    """Sección lateral de la viga (Vista en el plano Y-Z)"""
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
        
    color_y, color_z = '#008000', '#0066CC'
    dim_y = w/2 if orientacion == 'FUERTE' else h/2
    dim_z = h/2 if orientacion == 'FUERTE' else w/2
    
    ax.annotate('', xy=(x + dim_y + 0.3, y), xytext=(x, y), arrowprops=dict(arrowstyle='->', color=color_y, lw=1.2))
    ax.text(x + dim_y + 0.4, y - 0.1, 'y', fontsize=9, color=color_y, fontweight='bold')
    ax.annotate('', xy=(x, y + dim_z + 0.3), xytext=(x, y), arrowprops=dict(arrowstyle='->', color=color_z, lw=1.2))
    ax.text(x - 0.15, y + dim_z + 0.4, 'z', fontsize=9, color=color_z, fontweight='bold')

def dibujar_cotas(ax, x1, y1, x2, y2, texto, offset=0.8, orientacion='horizontal'):
    if orientacion == 'horizontal':
        ax.annotate('', xy=(x2, y1 + offset), xytext=(x1, y1 + offset), arrowprops=dict(arrowstyle='<->', lw=1.2))
        ax.text((x1 + x2) / 2, y1 + offset + 0.3, texto, ha='center', va='bottom', fontsize=10, fontweight='bold')
    else:
        ax.annotate('', xy=(x1 - offset, y2), xytext=(x1 - offset, y1), arrowprops=dict(arrowstyle='<->', lw=1.2))
        ax.text(x1 - offset - 0.3, (y1 + y2) / 2, texto, ha='right', va='center', fontsize=10, fontweight='bold', rotation=90)

# ============================================================================
# INTERFAZ SIDEBAR
# ============================================================================
st.sidebar.header("⚙️ Parámetros")
st.sidebar.markdown("### 1) Definición geométrica")

H = st.sidebar.number_input("Altura (H) [m]", value=5.5)
L = st.sidebar.number_input("Longitud (L) [m]", value=7.0)

SISTEMA = st.sidebar.radio("Sistema Lateral", 
                           ["No arriostrado (Translacional)", "Arriostrado (Intranslacional)"],
                           help="Define si el pórtico permite o no el desplazamiento lateral.")

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

T_APOYO = st.sidebar.selectbox("Apoyo", ["Empotrado", "Articulado"])

# ============================================================================
# MOTOR DE DIBUJO Y CÁLCULO
# ============================================================================

def generar_grafico():
    props_col = obtener_propiedades_perfil(perfil_col)
    props_viga = obtener_propiedades_perfil(perfil_viga)
    
    D_COL_R = props_col['d']
    D_VIGA_R = props_viga['d']
    
    esc = 0.8 / 0.40
    D_C, D_V = D_COL_R * esc, D_VIGA_R * esc
    E_ALA_C = max(props_col['tf'] * esc, 0.06) 
    E_ALA_V = max(props_viga['tf'] * esc, 0.06)
    
    # ============================================================================
    # CÁLCULO DE RIGIDEZ (G Superior e Inferior)
    # ============================================================================
    I_c = props_col['Ix'] if o_col == 'FUERTE' else props_col['Iy']
    I_v = props_viga['Ix'] if o_viga == 'FUERTE' else props_viga['Iy']
    
    if I_c > 0 and I_v > 0:
        rigidez_columna = I_c / (H * 100) 
        rigidez_viga = I_v / (L * 100)    
        G_sup = rigidez_columna / rigidez_viga
    else:
        G_sup = None
        
    G_inf = 1.0 if T_APOYO == "Empotrado" else 10.0
    
    # ============================================================================
    # DIBUJO
    # ============================================================================
    lw_ext = 1.5
    lw_int = 1.0

    fig, ax = plt.subplots(figsize=(12, 9), dpi=300) 
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_xlim(-4.01, L + 5); ax.set_ylim(-4.01, H + 2)

    color_x, color_y, color_z = '#CC0000', '#008000', '#0066CC'
    xo, yo = -3.5, 0
    ax.annotate('', xy=(xo+1, yo), xytext=(xo, yo), arrowprops=dict(arrowstyle='->', lw=2, color=color_x))
    ax.text(xo+1.2, yo, 'X', color=color_x, fontweight='bold', va='center')
    ax.annotate('', xy=(xo, yo+1), xytext=(xo, yo), arrowprops=dict(arrowstyle='->', lw=2, color=color_z))
    ax.text(xo, yo+1.3, 'Z', color=color_z, fontweight='bold', ha='center')
    dx_y, dy_y = 0.5, 0.4
    ax.annotate('', xy=(xo+dx_y, yo+dy_y), xytext=(xo, yo), arrowprops=dict(arrowstyle='->', lw=2, color=color_y))
    ax.text(xo+dx_y+0.2, yo+dy_y+0.1, 'Y', color=color_y, fontweight='bold', ha='left')
    ax.plot([xo], [yo], 'o', color='black', markersize=4)

    vs, vi = H + D_V/2, H - D_V/2
    GROSOR_EJE = 0.8
    GROSOR_ALMA_OCULTA = 0.6
    COLOR_ALMA_GRIS = '#222222' 
    
    for x in [0, L]:
        ax.plot([x-D_C/2, x-D_C/2], [0, vs], 'k', lw=lw_ext, zorder=1)
        ax.plot([x+D_C/2, x+D_C/2], [0, vs], 'k', lw=lw_ext, zorder=1)
        ax.plot([x-D_C/2, x+D_C/2], [0, 0], 'k', lw=lw_ext, zorder=1)
        ax.plot([x-D_C/2, x+D_C/2], [vs, vs], 'k', lw=lw_ext, zorder=1)
        
        ax.plot([x, x], [0, H], color='black', linestyle='-.', lw=GROSOR_EJE, zorder=4, snap=True)
        
        if o_col == 'FUERTE':
            ax.plot([x-D_C/2+E_ALA_C, x-D_C/2+E_ALA_C], [0, vs], 'k', lw=lw_int, zorder=2)
            ax.plot([x+D_C/2-E_ALA_C, x+D_C/2-E_ALA_C], [0, vs], 'k', lw=lw_int, zorder=2)
        else:
            off = max(props_col['tw'] * esc, 0.04) * 2 
            ax.plot([x - off/2, x - off/2], [0, vs], color=COLOR_ALMA_GRIS, linestyle='--', lw=GROSOR_ALMA_OCULTA, zorder=2)
            ax.plot([x + off/2, x + off/2], [0, vs], color=COLOR_ALMA_GRIS, linestyle='--', lw=GROSOR_ALMA_OCULTA, zorder=2)

        if T_APOYO == "Empotrado": 
            dibujar_apoyo_empotrado(ax, x, 0)
        else: 
            dibujar_apoyo_articulado(ax, x, 0)
        
        dibujar_seccion_ipe(ax, x, -1.5, orientacion=o_col)

    ax.plot([0, L], [H, H], color='black', linestyle='-.', lw=GROSOR_EJE, zorder=4, snap=True)
    
    xfi, xfd = D_C/2, L - D_C/2
    ax.plot([xfi, xfd], [vi, vi], 'k', lw=lw_ext, zorder=1)
    ax.plot([xfi, xfd], [vs, vs], 'k', lw=lw_ext, zorder=1)
    
    if o_viga == 'FUERTE':
        ax.plot([xfi, xfd], [vi+E_ALA_V, vi+E_ALA_V], 'k', lw=lw_int, zorder=2)
        ax.plot([xfi, xfd], [vs-E_ALA_V, vs-E_ALA_V], 'k', lw=lw_int, zorder=2)
    else:
        off_v = max(props_viga['tw'] * esc, 0.04) * 2
        ax.plot([xfi, xfd], [H - off_v/2, H - off_v/2], color=COLOR_ALMA_GRIS, linestyle='--', lw=GROSOR_ALMA_OCULTA, zorder=2)
        ax.plot([xfi, xfd], [H + off_v/2, H + off_v/2], color=COLOR_ALMA_GRIS, linestyle='--', lw=GROSOR_ALMA_OCULTA, zorder=2)

    x_viga_sec = L + 1.8
    ax.plot([xfd, x_viga_sec], [H, H], 'k-.', lw=0.8, alpha=0.4) 
    dibujar_seccion_viga(ax, x_viga_sec, H, orientacion=o_viga)

    if "Arriostrado" in SISTEMA:
        color_x = '#2E5A88' 
        ax.plot([0, L], [0, H], color=color_x, linestyle='--', lw=1.2, zorder=0, alpha=0.8)
        ax.plot([L, 0], [0, H], color=color_x, linestyle='--', lw=1.2, zorder=0, alpha=0.8)

    pos = []
    if NUDOS: pos.append(H)
    dz = FRAC * H
    for i in range(1, int(CANT)+1):
        if i*dz < H-0.1: pos.append(i*dz)
    pos.sort()
    
    for yp in pos:
        dibujar_arriostramiento_y(ax, 0, yp)
        dibujar_arriostramiento_y(ax, L, yp)

    y_p = 0
    xc = D_C/2 + 1.0
    for yp in pos:
        dist = yp - y_p
        if dist > 0.1:
            y_mid = (y_p + yp) / 2
            ax.annotate('', xy=(xc, yp), xytext=(xc, y_p), arrowprops=dict(arrowstyle='<->', lw=0.8))
            
            if abs(dist - dz) < 0.05:
                texto_h = ""
                if abs(FRAC - 1/2) < 0.001: texto_h = "H/2"
                elif abs(FRAC - 1/3) < 0.001: texto_h = "H/3"
                elif abs(FRAC - 1/4) < 0.001: texto_h = "H/4"
                elif abs(FRAC - 1/5) < 0.001: texto_h = "H/5"
                else: 
                    texto_h = f"{FRAC:.2f} H"
                
                ax.text(xc - 0.1, y_mid, texto_h, rotation=90, va='center', ha='right', fontsize=9, color='#0066CC', fontweight='bold')
                ax.text(xc + 0.1, y_mid, f"{dist:.2f}m", rotation=90, va='center', ha='left', fontsize=9)
            else:
                ax.text(xc + 0.1, y_mid, f"{dist:.2f}m", rotation=90, va='center', ha='left', fontsize=9)
        y_p = yp

    dibujar_cotas(ax, 0, 0, 0, H, f'H={H:.2f}m', 1.2, 'vertical')
    dibujar_cotas(ax, 0, H, L, H, f'L={L:.2f}m', 1.0, 'horizontal')

    texto_nudos = "Sí" if NUDOS else "No"
    tipo_portico_txt = "Arriostrado" if "Arriostrado" in SISTEMA else "No arriostrado"
    
    info = (
        f"TP Nº1 - ESTRUCTURAS METÁLICAS\n"
        f"Tipo de Pórtico: {tipo_portico_txt}\n"
        f"Col: {perfil_col} ({o_col})\n"
        f"Viga: {perfil_viga} ({o_viga})\n"
        f"Arriostramientos nudos sup.: {texto_nudos}\n"
        f"Arriostramientos intermedios: {int(CANT)}"
    )

    ax.text(L+1.5, 0, info, bbox=dict(boxstyle='round', fc='white', ec='black'), family='monospace', fontsize=10, va='bottom')
   
    st.pyplot(fig, use_container_width=True)
    
    return G_sup, G_inf

# ============================================================================
# RENDERIZADO DE PESTAÑAS (TABS)
# ============================================================================
pestana_1, pestana_2 = st.tabs(["📐 Definición Geométrica", "🧮 Cálculo de Esbelteces"])

with pestana_1:
    G_sup, G_inf = generar_grafico()

with pestana_2:
    st.header("Resultados del Análisis de Rigidez")
    
    if G_sup is not None:
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Nudo Superior ($G_A$)**\n\nValor: {G_sup:.3f}")
        with col2:
            st.info(f"**Nudo Inferior ($G_B$)**\n\nValor: {G_inf:.3f}")
            
        st.markdown("---")
        st.markdown("*(Acá próximamente vamos a programar el cálculo de K y las esbelteces $\lambda$)*")
    else:
        st.warning("Faltan datos de inercia para calcular los coeficientes de rigidez.")
