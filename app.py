import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURAÇÃO DA PÁGINA (Deve ser o primeiro comando) ---
st.set_page_config(page_title="CRM Executive 2026", layout="wide", initial_sidebar_state="expanded")

# --- 2. SISTEMA DE LOGIN (Bloqueio) ---
def check_password():
    """Retorna True se o usuário tiver a senha correta."""
    def password_entered():
        if st.session_state["password"] == "rhc122436":  # <--- TROQUE SUA SENHA AQUI
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Primeiro acesso, mostra o input
        st.text_input("🔒 Digite a senha de acesso:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Senha incorreta
        st.text_input("🔒 Digite a senha de acesso:", type="password", on_change=password_entered, key="password")
        st.error("😕 Senha incorreta.")
        return False
    else:
        # Senha correta
        return True

if not check_password():
    st.stop()  # PARE TUDO AQUI se a senha não for válida.

# =========================================================
# --- AQUI COMEÇA O SEU DASHBOARD ORIGINAL (LIBERADO) ---
# =========================================================

# --- ESTILO CSS (MODE EXECUTIVE) ---
st.markdown("""
<style>
    /* Estilo dos Números (Branco e Grande) */
    [data-testid="stMetricValue"] {
        font-size: 24px;
        color: #FFFFFF !important;
        font-weight: 700;
    }
    /* Estilo dos Rótulos (Cinza Claro) */
    [data-testid="stMetricLabel"] {
        font-size: 13px;
        color: #cfcfcf !important;
        font-weight: 500;
    }
    /* Estilo dos Deltas (Setinhas) */
    [data-testid="stMetricDelta"] {
        font-size: 13px;
    }
    /* Fundo dos Cards de Métrica */
    div[data-testid="metric-container"] {
        background-color: #1e293b; /* Azul Escuro Profundo */
        border: 1px solid #334155;
        padding: 10px;
        border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }
    /* Títulos de Seção */
    h3 {
        color: #f8fafc;
        border-bottom: 2px solid #334155;
        padding-bottom: 10px;
        margin-top: 30px;
    }
    h4 {
        color: #94a3b8;
        margin-top: 15px;
    }
    /* Ajuste da Tabela */
    .stDataFrame {
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. ETL (EXTRAÇÃO E TRATAMENTO) ---
@st.cache_data
def load_data():
    # --- CARREGAMENTO PRINCIPAL (CLIENTES) ---
    file_path = 'todos_os_30_12_2025.csv'
    try:
        df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    except:
        df = pd.read_csv(file_path, sep=';', encoding='latin1')

    # Limpeza Monetária
    cols_fin = ['Total', '2020', '2021', '2022', '2023', '2024', '2025']
    for col in cols_fin:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if 'Total' in df.columns:
        df = df.rename(columns={'Total': 'LTV'})

    # Normalização
    if 'Estado' in df.columns:
        df['Estado'] = df['Estado'].astype(str).str.upper().str.strip()
    if 'Cidade' in df.columns:
        df['Cidade'] = df['Cidade'].astype(str).str.title().str.strip()

    # Datas
    cols_data = ['Data cadastro', 'Última compra']
    for col in cols_data:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')

    ref_date = pd.Timestamp('2025-12-30')

    # --- TRATAMENTO DE IDADE E FAIXA ETÁRIA ---
    if 'Data nascimento' in df.columns:
        df['Data nascimento'] = pd.to_datetime(df['Data nascimento'], format='%d/%m/%Y', errors='coerce')
        
        def calcular_idade(nasc):
            if pd.isnull(nasc): return 0
            # Filtra erros de cadastro (anos muito antigos ou futuros)
            if nasc.year < 1930 or nasc.year > 2025: return 0
            hoje = datetime(2025, 12, 30)
            return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))

        df['Idade'] = df['Data nascimento'].apply(calcular_idade)
        
        def definir_faixa_etaria(idade):
            if idade == 0: return "Não Informado"
            if idade < 18: return "Jovens (<18)"
            if idade <= 30: return "Jovens Adultos (18-30)"
            if idade <= 50: return "Adultos (31-50)"
            return "Seniors (50+)"
            
        df['Faixa_Etaria'] = df['Idade'].apply(definir_faixa_etaria)
    else:
        df['Idade'] = 0
        df['Faixa_Etaria'] = "Não Informado"

    # Engenharia
    df['Dias_Inativo'] = (ref_date - df['Última compra']).dt.days
    df['Ano_Cadastro'] = df['Data cadastro'].dt.year
    df['Safra'] = df['Ano_Cadastro'].apply(lambda x: "Novos (2025)" if x == 2025 else "Recorrentes")
    
    # KPI: Status de Evolução
    def definir_evolucao(row):
        v24 = row['2024']
        v25 = row['2025']
        
        if row['Ano_Cadastro'] == 2025: return "🌱 Novo Cliente"
        if v25 > v24: return "🚀 Crescendo (+)"
        if v25 > 0 and v25 < v24: return "📉 Em Queda (-)"
        if v24 > 0 and v25 == 0: return "🛑 Parou de Comprar"
        return "💤 Estável/Inativo"

    df['Evolucao'] = df.apply(definir_evolucao, axis=1)

    # Lista para o Sparkline
    df['Tendencia_Anual'] = df[['2022', '2023', '2024', '2025']].values.tolist()

    # KPI: Ticket Médio por Pedido
    df['Total pedidos'] = pd.to_numeric(df['Total pedidos'], errors='coerce').fillna(0)
    df['TM_Pedido'] = df.apply(lambda x: x['LTV'] / x['Total pedidos'] if x['Total pedidos'] > 0 else 0, axis=1)

    # Status Detalhado (Lógica Corrigida)
    def get_status(row):
        dias = row['Dias_Inativo']
        ltv = row['LTV']
        
        if pd.isna(dias): 
            if ltv > 0: return "5. Sem Data (Com Compra) ❓"
            return "Sem Compra"
            
        if dias <= 90: return "1. Ativo (Quente) 🔥"
        if dias <= 180: return "2. Em Risco ⚠️"
        if dias <= 365: return "3. Inativo ❄️"
        return "4. Churn (Perdido) ☠️"
    
    df['Status'] = df.apply(get_status, axis=1)

    # Perfil Avançado (Lógica Ticket Médio Histórico)
    def definir_perfil(row):
        ltv = row['LTV']
        tipo = str(row['Tipo cliente']).lower()
        official = 'revenda' in tipo
        
        # LTV > 6000: Revendedor Oculto (Se não for oficial)
        if ltv > 6000:
            if not official: return "Revendedor Oculto 🕵️"
            return "Baleia VIP 🐋" # Oficial com LTV alto
        
        # LTV entre 2400 e 6000
        if ltv >= 2400: 
            return "Baleia VIP 🐋"
            
        # LTV < 2400
        return "Consumidor Padrão 👤"

    df['Perfil'] = df.apply(definir_perfil, axis=1)

    # --- NOVO: CARREGAMENTO SECUNDÁRIO (INVESTIMENTOS DE MÍDIA) ---
    try:
        df_ads = pd.read_csv('investimentos_midia.csv', sep=';', encoding='utf-8')
        # Tratamento básico para garantir que 'Investimento' seja número
        if 'Investimento' in df_ads.columns:
            df_ads['Investimento'] = df_ads['Investimento'].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df_ads['Investimento'] = pd.to_numeric(df_ads['Investimento'], errors='coerce').fillna(0)
    except:
        # Se não achar o arquivo, cria um DataFrame vazio com as colunas esperadas para não quebrar
        df_ads = pd.DataFrame(columns=['Ano', 'Investimento'])

    return df, df_ads

# Carregar (Agora desempacota dois dataframes)
try:
    df, df_ads = load_data()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

# --- SIDEBAR ---
st.sidebar.header("🔍 Filtros Executivos")

# Botão de Atualizar
if st.sidebar.button("🔄 Atualizar Dados"):
    st.cache_data.clear()
    st.rerun()

status_opts = sorted(df['Status'].unique())
perfil_opts = df['Perfil'].unique()
evolucao_opts = df['Evolucao'].unique()
estado_opts = sorted(df['Estado'].astype(str).unique())

sel_status = st.sidebar.multiselect("Status:", status_opts, default=status_opts)
sel_perfil = st.sidebar.multiselect("Perfil:", perfil_opts, default=perfil_opts)
sel_evolucao = st.sidebar.multiselect("Evolução (24 vs 25):", evolucao_opts)
sel_estado = st.sidebar.multiselect("Estado:", estado_opts)

# Filtragem
df_filt = df[
    (df['Status'].isin(sel_status)) & 
    (df['Perfil'].isin(sel_perfil))
]
if sel_evolucao:
    df_filt = df_filt[df_filt['Evolucao'].isin(sel_evolucao)]
if sel_estado:
    df_filt = df_filt[df_filt['Estado'].isin(sel_estado)]

# --- CÁLCULOS GERAIS ---
fat_total_historico = df_filt['LTV'].sum()
fat_2025 = df_filt['2025'].sum()
fat_2024 = df_filt['2024'].sum()
delta_25 = ((fat_2025 - fat_2024) / fat_2024 * 100) if fat_2024 > 0 else 0

ltv_medio = df_filt['LTV'].mean()
tm_pedido = df_filt[df_filt['Total pedidos'] > 0]['TM_Pedido'].mean()
crescendo_count = len(df_filt[df_filt['Evolucao'] == "🚀 Crescendo (+)"])
share_rec = (df_filt[df_filt['Safra']=='Recorrentes']['2025'].sum() / fat_2025 * 100) if fat_2025 > 0 else 0

# Oportunidades
b2b_oculto = df_filt[df_filt['Perfil'] == "Revendedor Oculto 🕵️"]
val_b2b = b2b_oculto['LTV'].sum()
avg_ticket_b2b = b2b_oculto['TM_Pedido'].mean() if len(b2b_oculto) > 0 else 0
avg_ticket_geral = df_filt['TM_Pedido'].mean() if len(df_filt) > 0 else 0

baleias_risco = df_filt[
    (df_filt['Perfil'] == "Baleia VIP 🐋") & 
    (~df_filt['Status'].str.contains("Ativo"))
]
val_risco = baleias_risco['LTV'].sum()

# Formatação
def fmt_money(val):
    if val >= 1_000_000: return f"R$ {val/1_000_000:,.2f}M"
    return f"R$ {val/1_000:,.1f}k"

# --- LAYOUT DASHBOARD ---
st.title("🚀 Command Center: Estratégia & Histórico")

# --- DISCLAIMER / LEGENDA ---
with st.expander("ℹ️  Guia de Leitura: Como interpretar os Status e Perfis (Clique para abrir)", expanded=True):
    col_help1, col_help2 = st.columns(2)
    
    with col_help1:
        st.markdown("#### 📌 Classificação de Status (Recência)")
        st.markdown("""
        * **1. Ativo (Quente) 🔥:** Comprou nos últimos **90 dias**.
        * **2. Em Risco ⚠️:** Última compra entre **91 e 180 dias**.
        * **3. Inativo ❄️:** Última compra entre **181 e 365 dias**.
        * **4. Churn (Perdido) ☠️:** Sem compras há **mais de 1 ano**.
        * **5. Sem Data (Com Compra) ❓:** Clientes com LTV > 0 mas sem data de registro (Erro de Cadastro).
        * **Sem Compra:** Leads cadastrados que nunca compraram (LTV = 0).
        """)
        
    with col_help2:
        st.markdown("#### 👤 Perfil do Cliente (Baseado no LTV)")
        st.markdown("""
        * **👤 Consumidor Padrão:** LTV Total abaixo de **R\$ 2.400,00**.
        * **🐋 Baleia VIP:** LTV Total entre **R\$ 2.400,00 e R\$ 6.000,00** (Bons compradores).
        * **🕵️ Revendedor Oculto:** LTV Total acima de **R\$ 6.000,00** (Alta probabilidade de revenda, se não for oficial).
        """)
        st.info("**Nota:** O LTV (Lifetime Value) considera a soma de compras de todo o histórico (2020-2025).")

st.markdown(f"**Visão Consolidada:** {len(df_filt)} clientes filtrados")

# --- SEÇÃO 1: BIG NUMBERS GERAIS ---
st.markdown("### 1. Visão Macro Financeira")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Faturamento Acumulado", fmt_money(fat_total_historico), "Desde o início")
col2.metric("LTV Médio (Vitalício)", f"R$ {ltv_medio:,.2f}")
col3.metric("Potencial B2B Oculto", fmt_money(val_b2b), f"{len(b2b_oculto)} Revendedores")
col4.metric("Dinheiro em Risco (VIP)", fmt_money(val_risco), f"{len(baleias_risco)} Baleias Paradas", delta_color="inverse")

# --- SEÇÃO 2: DETALHAMENTO ANUAL (COM LÓGICA CASCATA CORRIGIDA) ---
st.markdown("### 2. Performance Anual Detalhada")

def exibir_ano(ano, df_f):
    col_str = str(ano)
    col_prev = str(ano - 1)
    
    if col_str not in df_f.columns: return 0
    
    # --- CÁLCULOS ANO ATUAL ---
    compradores_ano = df_f[df_f[col_str] > 0]
    fat_ano = df_f[col_str].sum()
    ativos_ano = len(compradores_ano)
    tm_ano = compradores_ano[col_str].mean() if ativos_ano > 0 else 0
    novos_ano = len(compradores_ano[compradores_ano['Ano_Cadastro'] == ano])
    rec_ano = len(compradores_ano[compradores_ano['Ano_Cadastro'] < ano])
    
    # --- CÁLCULOS ANO ANTERIOR (Para Deltas) ---
    if col_prev in df_f.columns:
        compradores_prev = df_f[df_f[col_prev] > 0]
        fat_prev = df_f[col_prev].sum()
        ativos_prev = len(compradores_prev)
        tm_prev = compradores_prev[col_prev].mean() if ativos_prev > 0 else 0
        novos_prev = len(compradores_prev[compradores_prev['Ano_Cadastro'] == (ano - 1)])
        rec_prev = len(compradores_prev[compradores_prev['Ano_Cadastro'] < (ano - 1)])
    else:
        fat_prev = ativos_prev = tm_prev = novos_prev = rec_prev = 0

    # --- CÁLCULO RECEITA PERDIDA (LÓGICA CASCATA/CHURN DEFINITIVO) ---
    lost_revenue = 0
    pct_lost = 0
    
    if ano < 2025:
        condicao_churn = (df_f[col_str] > 0)
        for y_future in range(ano + 1, 2026):
            if str(y_future) in df_f.columns:
                condicao_churn = condicao_churn & (df_f[str(y_future)] == 0)
        
        lost_revenue = df_f.loc[condicao_churn, col_str].sum()
        if fat_ano > 0:
            pct_lost = (lost_revenue / fat_ano) * 100
    else:
        lost_revenue = 0

    def calc_delta(atual, anterior):
        if anterior > 0:
            val = (atual - anterior) / anterior * 100
            return f"{val:+.1f}%"
        return None

    # --- LAYOUT ---
    c1, c2, c3, c4, c5, c6, c7 = st.columns([0.8, 1.2, 1.2, 1.0, 1.0, 1.0, 1.0])
    
    c1.markdown(f"#### {ano}")
    c2.metric("Faturamento", fmt_money(fat_ano), calc_delta(fat_ano, fat_prev))
    
    if ano < 2025:
        c3.metric("Receita Perdida (Churn)", fmt_money(lost_revenue), f"{pct_lost:.1f}% do fat. {ano}", delta_color="inverse", help=f"Valor gerado em {ano} por clientes que pararam de comprar depois.")
    else:
        c3.metric("Receita Perdida", "---", "---", help="Não aplicável ao ano corrente")
        
    c4.metric("Ticket Médio", f"R$ {tm_ano:,.2f}", calc_delta(tm_ano, tm_prev))
    c5.metric("Ativos", ativos_ano, calc_delta(ativos_ano, ativos_prev))
    c6.metric("🔄 Recorrentes", rec_ano, calc_delta(rec_ano, rec_prev))
    c7.metric("🌱 Novos", novos_ano, calc_delta(novos_ano, novos_prev))
    
    st.divider()
    return fat_ano

# Renderiza os anos
exibir_ano(2025, df_filt)
exibir_ano(2024, df_filt)
exibir_ano(2023, df_filt)
exibir_ano(2022, df_filt)
exibir_ano(2021, df_filt)
exibir_ano(2020, df_filt)

# --- SEÇÃO 3: SAÚDE E DETALHAMENTO DA BASE ---
st.markdown("### 3. Saúde & Detalhamento da Base")

# Cálculo dos KPIs de Saúde
total_base = len(df_filt)
nunca_comprou = len(df_filt[df_filt['LTV'] == 0])
ja_comprou = len(df_filt[df_filt['LTV'] > 0])
ativos_30 = len(df_filt[df_filt['Dias_Inativo'] <= 30])
ativos_90 = len(df_filt[df_filt['Dias_Inativo'] <= 90])
ativos_180 = len(df_filt[df_filt['Dias_Inativo'] <= 180])
ativos_25_total = len(df_filt[df_filt['2025'] > 0])
inativos_total = len(df_filt[df_filt['Dias_Inativo'] > 365])
risco_24_25 = len(df_filt[ (df_filt['2024'] > 0) & (df_filt['2025'] == 0) ])

# Linha 3.1: Composição da Base
st.markdown("#### Composição da Carteira")
k_base, k_leads, k_clientes = st.columns(3)
k_base.metric("Total da Base (CPFs/CNPJs)", total_base)
k_leads.metric("Leads (Sem Compra)", nunca_comprou, help="Cadastrados com LTV zerado")
k_clientes.metric("Compradores Reais", ja_comprou, help="Clientes com pelo menos 1 compra na história")

# Linha 3.2: Termômetro de Atividade
st.markdown("#### 🌡️ Termômetro de Atividade (Recência)")
r1, r2, r3, r4 = st.columns(4)
r1.metric("🔥 Super Ativos (30d)", ativos_30, "Último Mês")
r2.metric("⚡ Ativos (90d)", ativos_90, "Último Trimestre")
r3.metric("⚠️ Mornos (180d)", ativos_180, "Último Semestre")
r4.metric("📅 Ativos em 2025", ativos_25_total, "Comprou este ano")

# Linha 3.3: Alertas de Risco
st.markdown("#### 🚨 Alertas de Risco")
a1, a2 = st.columns(2)
a1.metric("Risco Imediato (Churn 2025)", risco_24_25, "Comprou em 2024 -> Zero em 2025", delta_color="inverse")
a2.metric("Inativos Totais (>1 Ano)", inativos_total, "Sem compras há +365 dias", delta_color="inverse")

st.markdown("---")

# --- ABAS DETALHADAS ---
# Adicionada aba "💰 Ticket Médio" na lista
tab_lista, tab_graficos, tab_geo, tab_cac, tab_ticket, tab_b2b, tab_risco, tab_acoes = st.tabs(["📋 Raio-X", "📈 Gráficos", "🗺️ Geografia", "💸 CAC & ROI", "💰 Ticket Médio", "🕵️ Deep Dive: Revendedores Ocultos", "🚨 Detalhe de Risco", "⚡ Ações"])

with tab_lista:
    st.subheader("Base de Clientes Detalhada")
    cols_show = ['Nome cliente', 'Status', 'Perfil', 'Evolucao', 'Tendencia_Anual', '2024', '2025', 'LTV', 'Data cadastro', 'Última compra', 'Dias_Inativo', 'Faixa_Etaria']
    st.dataframe(
        df_filt[cols_show].sort_values(by='LTV', ascending=False),
        column_config={
            "Nome cliente": st.column_config.TextColumn("Cliente", width="medium"),
            "Status": st.column_config.TextColumn("Status Atual", width="small"),
            "Perfil": st.column_config.TextColumn("Perfil", width="small"),
            "Evolucao": st.column_config.TextColumn("Momento", width="small"),
            "Tendencia_Anual": st.column_config.LineChartColumn("Tendência (22-25)", width="medium", y_min=0, y_max=None),
            "2024": st.column_config.NumberColumn("Gasto 2024", format="R$ %.2f"),
            "2025": st.column_config.NumberColumn("Gasto 2025", format="R$ %.2f"),
            "LTV": st.column_config.ProgressColumn("LTV Total", format="R$ %.2f", min_value=0, max_value=df['LTV'].max()),
            "Data cadastro": st.column_config.DateColumn("Desde", format="DD/MM/YYYY"),
            "Última compra": st.column_config.DateColumn("Última", format="DD/MM/YYYY"),
            "Dias_Inativo": st.column_config.NumberColumn("Dias Ausente", format="%d dias"),
        }, use_container_width=True, height=600
    )

with tab_graficos:
    c1, c2, c3 = st.columns(3)
    with c1:
        fig1 = px.pie(
            df_filt, 
            names='Status', 
            hole=0.6, 
            title="Status da Base", 
            color='Status', 
            color_discrete_map={
                '1. Ativo (Quente) 🔥': '#10b981', 
                '2. Em Risco ⚠️': '#f59e0b', 
                '3. Inativo ❄️': '#3b82f6', 
                '4. Churn (Perdido) ☠️': '#ef4444',
                '5. Sem Data (Com Compra) ❓': '#8b5cf6'
            }
        )
        st.plotly_chart(fig1, use_container_width=True)
    with c2:
        df_mix = df_filt.groupby('Safra')['2025'].sum().reset_index()
        fig_mix = px.pie(df_mix, values='2025', names='Safra', title="Mix de Faturamento '25", hole=0.6, color='Safra', color_discrete_map={'Recorrentes': '#10b981', 'Novos (2025)': '#3b82f6'})
        st.plotly_chart(fig_mix, use_container_width=True)
    with c3:
        fig_evo = px.pie(df_filt, names='Evolucao', hole=0.6, title="Matriz de Evolução", color='Evolucao', color_discrete_map={"🚀 Crescendo (+)": "#2ecc71", "📉 Em Queda (-)": "#f1c40f", "🛑 Parou de Comprar": "#e74c3c", "🌱 Novo Cliente": "#3498db", "💤 Estável/Inativo": "#95a5a6"})
        st.plotly_chart(fig_evo, use_container_width=True)

with tab_geo:
    st.subheader("🗺️ Onde está o dinheiro?")
    df_estado = df_filt.groupby('Estado')['LTV'].sum().reset_index().sort_values('LTV', ascending=False)
    df_cidade = df_filt.groupby(['Cidade', 'Estado'])['LTV'].sum().reset_index().sort_values('LTV', ascending=False).head(20)
    c_geo1, c_geo2 = st.columns([1, 1])
    with c_geo1:
        st.markdown("#### Top Estados (Faturamento)")
        fig_est = px.bar(df_estado.head(10), x='LTV', y='Estado', orientation='h', text_auto='.2s', color='LTV', color_continuous_scale='Bluyl')
        fig_est.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_est, use_container_width=True)
        st.dataframe(df_estado, column_config={"LTV": st.column_config.ProgressColumn("Faturamento Total", format="R$ %.2f", max_value=df_estado['LTV'].max())}, use_container_width=True, height=300)
    with c_geo2:
        st.markdown("#### Top 20 Cidades")
        st.dataframe(df_cidade, column_config={"Cidade": st.column_config.TextColumn("Cidade", width="medium"), "LTV": st.column_config.ProgressColumn("Faturamento Total", format="R$ %.2f", max_value=df_cidade['LTV'].max())}, use_container_width=True, height=600)

# --- NOVA ABA: CAC & ROI (ATUALIZADA, FILTRADA E COM CAC GLOBAL) ---
with tab_cac:
    st.subheader("💸 Análise de Investimentos em Mídia, CAC e ROI")
    
    if len(df_ads) > 0:
        # Prepara os dados de Investimento (usado em ambas as visões)
        df_invest_group = df_ads.groupby('Ano')['Investimento'].sum().reset_index()
        
        # Cria as Sub-abas
        tab_aq, tab_blended = st.tabs(["🎣 Eficiência de Aquisição (Novos)", "🏢 Eficiência Global (Blended)"])
        
        # --- SUB-ABA 1: AQUISIÇÃO (COHORT) ---
        with tab_aq:
            st.markdown("##### 🎣 ROI da Aquisição (Cohort)")
            st.info("Analisa se os clientes adquiridos em um ano 'se pagaram' com o tempo. \n\n* **Receita (LTV):** Soma total gasta APENAS pelos clientes que entraram naquele ano (durante toda a vida deles).")
            
            # 1. Filtra Novos Clientes Compradores (LTV > 0)
            df_compradores = df[df['LTV'] > 0]
            novos_por_ano = df_compradores.groupby('Ano_Cadastro').size().reset_index(name='Novos_Clientes')
            novos_por_ano = novos_por_ano.rename(columns={'Ano_Cadastro': 'Ano'})
            
            # 2. Receita da Safra/Cohort (LTV acumulado de quem entrou no ano)
            ltv_cohort = df.groupby('Ano_Cadastro')['LTV'].sum().reset_index(name='Receita_Cohort')
            ltv_cohort = ltv_cohort.rename(columns={'Ano_Cadastro': 'Ano'})
            
            # 3. Merge
            df_acq = pd.merge(df_invest_group, novos_por_ano, on='Ano', how='inner')
            df_acq = pd.merge(df_acq, ltv_cohort, on='Ano', how='left')
            
            # 4. KPIs
            df_acq['CAC'] = df_acq['Investimento'] / df_acq['Novos_Clientes']
            df_acq['ROAS_Acq'] = df_acq['Receita_Cohort'] / df_acq['Investimento']
            
            # Gráficos Aquisição
            c1, c2 = st.columns(2)
            with c1:
                fig_cac = px.line(df_acq, x='Ano', y='CAC', markers=True, title="Evolução do CAC (Custo por Cliente Novo)")
                fig_cac.update_traces(line_color='#ef4444', line_width=3)
                st.plotly_chart(fig_cac, use_container_width=True)
            with c2:
                fig_roas_acq = px.bar(df_acq, x='Ano', y='ROAS_Acq', text_auto='.2f', title="ROAS de Aquisição (Receita da Cohort / Investimento)")
                fig_roas_acq.add_hline(y=1, line_dash="dash", line_color="white")
                st.plotly_chart(fig_roas_acq, use_container_width=True)
                
            st.dataframe(df_acq.style.format({'Investimento': 'R$ {:.2f}', 'Receita_Cohort': 'R$ {:.2f}', 'CAC': 'R$ {:.2f}', 'ROAS_Acq': '{:.2f}x'}), use_container_width=True)

        # --- SUB-ABA 2: BLENDED (GLOBAL) ---
        with tab_blended:
            st.markdown("##### 🏢 ROI Global (Eficiência do Caixa)")
            st.success("Analisa a eficiência do marketing no faturamento total do ano. \n\n* **Faturamento Total:** Soma de TUDO que entrou no caixa naquele ano (Novos + Recorrentes).")
            
            # 1. Calcula Faturamento Total por Ano Calendário (Colunas 2020..2025)
            rev_data = []
            anos_disponiveis = [y for y in [2020, 2021, 2022, 2023, 2024, 2025] if str(y) in df.columns]
            
            for y in anos_disponiveis:
                total_ano = df[str(y)].sum()
                rev_data.append({'Ano': y, 'Faturamento_Total': total_ano})
            
            df_revenue_global = pd.DataFrame(rev_data)
            
            # 2. Merge com Investimento
            df_blended = pd.merge(df_invest_group, df_revenue_global, on='Ano', how='inner')
            
            # 3. KPIs
            df_blended['ROAS_Blended'] = df_blended['Faturamento_Total'] / df_blended['Investimento']
            df_blended['Perc_Marketing'] = (df_blended['Investimento'] / df_blended['Faturamento_Total']) * 100
            
            # Big Numbers Blended
            tot_inv_g = df_blended['Investimento'].sum()
            tot_rev_g = df_blended['Faturamento_Total'].sum()
            roas_g_medio = tot_rev_g / tot_inv_g if tot_inv_g > 0 else 0
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Investimento Total", fmt_money(tot_inv_g))
            k2.metric("Faturamento Total (Caixa)", fmt_money(tot_rev_g))
            k3.metric("ROAS Global (Média)", f"{roas_g_medio:.2f}x")
            
            # Gráficos Blended
            cb1, cb2 = st.columns(2)
            with cb1:
                fig_rev = px.bar(df_blended, x='Ano', y='Faturamento_Total', text_auto='.2s', title="Faturamento Total (Novos + Antigos)")
                st.plotly_chart(fig_rev, use_container_width=True)
            with cb2:
                fig_roas_b = px.line(df_blended, x='Ano', y='ROAS_Blended', markers=True, title="Evolução do ROAS Global (Blended)")
                fig_roas_b.update_traces(line_color='#10b981', line_width=4) # Verde
                fig_roas_b.add_hline(y=1, line_dash="dash", line_color="white", annotation_text="Break Even")
                st.plotly_chart(fig_roas_b, use_container_width=True)
                
            st.dataframe(df_blended.style.format({'Investimento': 'R$ {:.2f}', 'Faturamento_Total': 'R$ {:.2f}', 'ROAS_Blended': '{:.2f}x', 'Perc_Marketing': '{:.1f}%'}), use_container_width=True)

    else:
        st.warning("⚠️ Arquivo 'investimentos_midia.csv' não encontrado ou vazio. Adicione o arquivo na pasta com as colunas 'Ano' e 'Investimento'.")

# --- NOVA ABA: TICKET MÉDIO E COMPORTAMENTO (ATUALIZADA) ---
with tab_ticket:
    st.subheader("💰 Inteligência de Ticket Médio & Comportamento")
    st.markdown("Análise profunda da qualidade da venda e perfil do comprador.")
    
    # Preparação dos dados (filtra LTV > 0 e TM > 0)
    df_tm = df_filt[ (df_filt['LTV'] > 0) & (df_filt['TM_Pedido'] > 0) ].copy()
    
    if len(df_tm) > 0:
        # 1. KPIs Estatísticos (Realidade vs Média)
        tm_medio = df_tm['TM_Pedido'].mean()
        tm_mediano = df_tm['TM_Pedido'].median()
        tm_max = df_tm['TM_Pedido'].max()
        
        col_tm1, col_tm2, col_tm3 = st.columns(3)
        col_tm1.metric("Ticket Médio (Geral)", f"R$ {tm_medio:,.2f}", help="Média simples de todos os pedidos")
        col_tm2.metric("Ticket Mediano (Realidade)", f"R$ {tm_mediano:,.2f}", help="Valor central: metade dos clientes gasta menos que isso, metade gasta mais. Remove distorção de baleias.", delta_color="off")
        col_tm3.metric("Maior Pedido (Teto)", f"R$ {tm_max:,.2f}")
        
        st.divider()
        
        # 2. Zona de Lucro (Histograma)
        st.markdown("#### 📊 Distribuição de Preço: Onde está a massa de clientes?")
        fig_hist = px.histogram(df_tm, x="TM_Pedido", nbins=50, title="Frequência por Faixa de Valor", color_discrete_sequence=['#3b82f6'])
        fig_hist.update_layout(xaxis_title="Valor do Pedido (Ticket)", yaxis_title="Quantidade de Clientes")
        st.plotly_chart(fig_hist, use_container_width=True)
        
        st.divider()
        
        # 3. Perfil Detalhado (3 Colunas: Safra, Status, Idade)
        c_perfil1, c_perfil2, c_perfil3 = st.columns(3)
        
        with c_perfil1:
            st.markdown("##### 1. Novos vs Recorrentes")
            df_safra_tm = df_tm.groupby('Safra')['TM_Pedido'].mean().reset_index()
            fig_safra = px.bar(df_safra_tm, x='Safra', y='TM_Pedido', text_auto='.2f', title="TM por Safra", color='Safra')
            fig_safra.update_layout(showlegend=False)
            st.plotly_chart(fig_safra, use_container_width=True)
            
        with c_perfil2:
            st.markdown("##### 2. Ativos vs Churn")
            df_status_tm = df_tm.groupby('Status')['TM_Pedido'].mean().reset_index()
            fig_stat_tm = px.bar(df_status_tm, x='Status', y='TM_Pedido', text_auto='.2f', title="TM por Status", color='Status')
            fig_stat_tm.update_layout(showlegend=False)
            st.plotly_chart(fig_stat_tm, use_container_width=True)

        with c_perfil3:
            st.markdown("##### 3. Demografia (Idade)")
            # Filtra quem não tem idade informada para não sujar o gráfico
            df_age = df_tm[df_tm['Faixa_Etaria'] != "Não Informado"]
            if len(df_age) > 0:
                df_age_tm = df_age.groupby('Faixa_Etaria')['TM_Pedido'].mean().reset_index()
                # Ordenar as faixas
                ordem_idade = ["Jovens (<18)", "Jovens Adultos (18-30)", "Adultos (31-50)", "Seniors (50+)"]
                fig_age = px.bar(df_age_tm, x='Faixa_Etaria', y='TM_Pedido', text_auto='.2f', title="TM por Idade", category_orders={"Faixa_Etaria": ordem_idade}, color_discrete_sequence=['#f59e0b'])
                st.plotly_chart(fig_age, use_container_width=True)
            else:
                st.warning("Dados de Idade insuficientes.")
        
        st.divider()
        
        # --- FEATURE NOVA: GEOGRAFIA DO TICKET ---
        st.markdown("##### 4. Geografia do Valor (Onde o Ticket é maior?)")
        c_geo_tm1, c_geo_tm2 = st.columns(2)
        
        with c_geo_tm1:
            st.markdown("**Top Estados por Ticket Médio**")
            df_uf_tm = df_tm.groupby('Estado')['TM_Pedido'].mean().reset_index().sort_values('TM_Pedido', ascending=False)
            fig_uf_tm = px.bar(df_uf_tm, x='TM_Pedido', y='Estado', orientation='h', text_auto='.2f', color='TM_Pedido', color_continuous_scale='Greens')
            fig_uf_tm.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
            st.plotly_chart(fig_uf_tm, use_container_width=True)
            
        with c_geo_tm2:
            st.markdown("**Top 20 Cidades (Maior Ticket)**")
            df_city_tm = df_tm.groupby(['Cidade', 'Estado'])['TM_Pedido'].mean().reset_index().sort_values('TM_Pedido', ascending=False).head(20)
            st.dataframe(
                df_city_tm, 
                column_config={
                    "Cidade": st.column_config.TextColumn("Cidade"),
                    "Estado": st.column_config.TextColumn("UF"),
                    "TM_Pedido": st.column_config.ProgressColumn("Ticket Médio", format="R$ %.2f", min_value=0, max_value=df_city_tm['TM_Pedido'].max())
                }, 
                use_container_width=True, 
                height=400
            )
        
        st.divider()
        
        # 5. Matriz de Oportunidade (Scatter)
        st.markdown("#### 💎 Matriz de Oportunidade: Frequência x Valor")
        st.info("Eixo X: Quantas vezes comprou | Eixo Y: Valor Médio por Compra")
        fig_scat = px.scatter(df_tm, x='Total pedidos', y='TM_Pedido', color='Perfil', size='LTV', hover_data=['Nome cliente', 'Cidade'], log_x=True, title="Mapa de Clientes")
        st.plotly_chart(fig_scat, use_container_width=True)
        
    else:
        st.warning("Não há dados suficientes de vendas (LTV > 0) para análise de Ticket Médio.")

with tab_b2b:
    st.subheader("🕵️ Deep Dive: Revendedores Ocultos")
    st.info("**ℹ️ Metodologia:** LTV > R$ 6.000,00 (Excluindo revendas oficiais).")
    if len(b2b_oculto) > 0:
        kb1, kb2, kb3, kb4 = st.columns(4)
        kb1.metric("Total Revendedores", len(b2b_oculto))
        kb2.metric("Receita 'Escondida'", fmt_money(val_b2b), "Potencial")
        delta_ticket = ((avg_ticket_b2b - avg_ticket_geral) / avg_ticket_geral * 100) if avg_ticket_geral > 0 else 0
        kb3.metric("Ticket Médio (B2B)", f"R$ {avg_ticket_b2b:,.2f}", f"{delta_ticket:+.1f}% vs Geral")
        kb4.metric("Média de Pedidos", f"{b2b_oculto['Total pedidos'].mean():.1f}")
        st.markdown("---")
        c_b2b_1, c_b2b_2 = st.columns([2, 1])
        with c_b2b_1:
            fig_scatter_b2b = px.scatter(b2b_oculto, x='Total pedidos', y='LTV', color='Status', size='LTV', hover_data=['Nome cliente'], title="Matriz: Frequência vs Valor")
            st.plotly_chart(fig_scatter_b2b, use_container_width=True)
        with c_b2b_2:
            df_geo_b2b = b2b_oculto['Estado'].value_counts().reset_index()
            fig_geo_b2b = px.bar(df_geo_b2b, x='count', y='Estado', orientation='h', title="Geografia", color_discrete_sequence=['#8b5cf6'])
            st.plotly_chart(fig_geo_b2b, use_container_width=True)
        st.dataframe(b2b_oculto[['Nome cliente', 'Cidade', 'Estado', 'Total pedidos', 'LTV', 'Dias_Inativo', 'Status']].sort_values('LTV', ascending=False), use_container_width=True)
    else:
        st.warning("Nenhum cliente encontrado com estes filtros.")

with tab_risco:
    st.subheader("🚨 Controle de Danos: Cascata de Perda")
    st.markdown("Clientes que **pararam de comprar**. A aba '🔥 2024' é a mais crítica (Risco Imediato).")
    
    RISK_GUIDE = {
        2024: {
            "logica": "Comprou em 2024 ➔ Parou em 2025.",
            "diag": "🔥 **O Incêndio:** Cliente recente. O relacionamento ainda existe e ele lembra da marca.",
            "acao": "📞 **Ligação urgente.** 'Vi que você não renovou seu pedido este ano.'"
        },
        2023: {
            "logica": "Comprou em 2023 ➔ Zero em 2024 e 2025.",
            "diag": "🚑 **O Resgate:** Faz mais de 1 ano que não compra. Já criou hábito com o concorrente.",
            "acao": "🎁 **Oferta de Reativação.** Desconto agressivo ou condição especial."
        },
        2022: {
            "logica": "Comprou em 2022 ➔ Zero em 2023, 2024 e 2025.",
            "diag": "❄️ **A Reconquista:** Cliente frio. O comprador pode ter mudado.",
            "acao": "📧 **E-mail Marketing.** 'Veja as novidades que você perdeu.'"
        },
        2021: {
            "logica": "Comprou em 2021 ➔ Zero desde então.",
            "diag": "🧊 **Deep Dive:** Muito frio. Risco alto de dados desatualizados.",
            "acao": "🕵️ **Enriquecimento de Dados** antes de tentar contato."
        },
        2020: {
            "logica": "Comprou em 2020 ➔ Nunca mais voltou.",
            "diag": "☠️ **Arquivo Morto:** Clientes da origem da base.",
            "acao": "♻️ **Limpeza ou Prospecção Zero.** Tratar como Lead novo."
        }
    }

    tab_r24, tab_r23, tab_r22, tab_r21, tab_r20 = st.tabs(["🔥 2024 (Imediato)", "🚑 2023", "❄️ 2022", "🧊 2021", "☠️ 2020"])
    
    def render_risk_tab(df_source, year_lost):
        guide = RISK_GUIDE.get(year_lost, {})
        st.info(f"""
        **🧠 Lógica:** {guide.get('logica')}  
        **🩺 Diagnóstico:** {guide.get('diag')}  
        **⚡ Ação Recomendada:** {guide.get('acao')}
        """)
        
        condicao = df_source['2025'] == 0 
        for y in range(year_lost + 1, 2025):
            condicao = condicao & (df_source[str(y)] == 0)
        condicao = condicao & (df_source[str(year_lost)] > 0)
        
        df_risk_year = df_source[condicao]
        
        if len(df_risk_year) > 0:
            perda = df_risk_year[str(year_lost)].sum()
            avg_perda = perda / len(df_risk_year)
            
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Receita Perdida ({year_lost})", fmt_money(perda))
            c2.metric("Clientes Perdidos", len(df_risk_year))
            c3.metric("Ticket Médio da Perda", f"R$ {avg_perda:,.2f}")
            
            cols_possible = [
                'Nome cliente', 
                'Telefone principal', 'Telefone', 'Telefone 2', 'Celular', 'Celular 2', 'Whatsapp',
                'Email', 'E-mail',
                'Cidade', 'Estado', 
                str(year_lost), 'LTV', 'Dias_Inativo'
            ]
            cols_show = [c for c in cols_possible if c in df_source.columns]
            
            st.dataframe(
                df_risk_year[cols_show].sort_values(str(year_lost), ascending=False),
                column_config={
                    "Nome cliente": st.column_config.TextColumn("Cliente"),
                    "Telefone principal": st.column_config.TextColumn("Tel. Principal"),
                    "Telefone 2": st.column_config.TextColumn("Tel. Secundário"),
                    "Celular": st.column_config.TextColumn("Celular"),
                    "Whatsapp": st.column_config.TextColumn("WhatsApp"),
                    str(year_lost): st.column_config.ProgressColumn(f"Gasto em {year_lost}", format="R$ %.2f", max_value=df_source[str(year_lost)].max()),
                    "LTV": st.column_config.NumberColumn("LTV Total", format="R$ %.2f"),
                    "Dias_Inativo": st.column_config.NumberColumn("Dias Ausente", format="%d")
                },
                use_container_width=True
            )
        else:
            st.success(f"Nenhum cliente perdido identificado exclusivamente em {year_lost}.")

    with tab_r24: render_risk_tab(df_filt, 2024)
    with tab_r23: render_risk_tab(df_filt, 2023)
    with tab_r22: render_risk_tab(df_filt, 2022)
    with tab_r21: render_risk_tab(df_filt, 2021)
    with tab_r20: render_risk_tab(df_filt, 2020)

with tab_acoes:
    st.subheader("Listas de Trabalho (Vendas)")
    col_b2b, col_vip = st.columns(2)
    with col_b2b:
        st.success(f"🕵️ **Revendedores Ocultos ({len(b2b_oculto)})**")
        st.dataframe(b2b_oculto[['Nome cliente', 'Telefone principal', 'Total pedidos', 'LTV']].sort_values('LTV', ascending=False).head(100), use_container_width=True)
    with col_vip:
        st.error(f"🐋 **Baleias VIP em Risco ({len(baleias_risco)})**")
        st.dataframe(baleias_risco[['Nome cliente', 'Telefone principal', 'Dias_Inativo', 'LTV']].sort_values('LTV', ascending=False).head(100), use_container_width=True)

st.markdown("---")
st.caption("Sistema de Inteligência CRM 2026 | Desenvolvido via Python & Streamlit")
