import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

# 1. Configuração da Página
st.set_page_config(page_title="Mostra Tec - UNIUBE", page_icon="🔬", layout="wide")

# 2. Conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Inicializar variáveis de controle de login no estado do Streamlit
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario = ""
    st.session_state.perfil = ""

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🔬 Mostra Tecnológica - UNIUBE")
    st.subheader("Acesso ao Sistema")
    
    with st.form("form_login"):
        user_input = st.text_input("Usuário:")
        pass_input = st.text_input("Senha:", type="password")
        botao_login = st.form_submit_button("Entrar")
        
    if botao_login:
        try:
            # Busca os usuários direto da aba 'Usuarios'
            df_usuarios = conn.read(worksheet="Usuarios", ttl=0)
            
            # Valida se o usuário e senha existem combinados
            usuario_valido = df_usuarios[(df_usuarios['usuario'] == user_input) & (df_usuarios['senha'] == str(pass_input))]
            
            if not usuario_valido.empty:
                st.session_state.logado = True
                st.session_state.usuario = user_input
                st.session_state.perfil = usuario_valido.iloc[0]['perfil']
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos.")
        except Exception as e:
            st.error(f"Erro ao conectar ao banco de dados dos usuários: {e}")

# --- SISTEMA LOGADO ---
else:
    # Barra lateral para Logout e Boas-vindas
    st.sidebar.title(f"👤 Olá, {st.session_state.usuario}!")
    st.sidebar.write(f"Perfil: **{st.session_state.perfil.upper()}**")
    if st.sidebar.button("Sair / Logout"):
        st.session_state.logado = False
        st.session_state.usuario = ""
        st.session_state.perfil = ""
        st.rerun()

    # Carregamento prévio dos trabalhos para ambos os perfis (Avaliador e Admin)
    try:
        df_trabalhos_cadastrados = conn.read(worksheet="Trabalhos", ttl=60)
        # Cria um mapeamento rápido de ID para Nome e Categoria
        dict_trabalhos = df_trabalhos_cadastrados.set_index('id_trabalho').to_dict('index')
    except Exception as e:
        st.error(f"Erro ao carregar a lista de trabalhos da planilha: {e}")
        dict_trabalhos = {}

    # -------------------------------------------------------------
    # PERFIL: AVALIADOR (Formulário de Lançamento de Notas)
    # -------------------------------------------------------------
    if st.session_state.perfil == "avaliador":
        st.title("📝 Lançamento de Notas")
        st.write("Selecione o trabalho e atribua as notas inteiras (1 a 10).")
        
        if not dict_trabalhos:
            st.warning("Nenhum trabalho cadastrado na planilha para avaliação.")
        else:
            with st.form(key="form_notas", clear_on_submit=True):
                # Caixa de seleção mostrando ID, Título e Categoria para o avaliador não errar
                id_trabalho = st.selectbox(
                    "Escolha o Trabalho:", 
                    options=list(dict_trabalhos.keys()), 
                    format_func=lambda x: f"{x} - {dict_trabalhos[x]['titulo_trabalho']} ({dict_trabalhos[x]['categoria']})"
                )
                
                # Mostra visualmente a categoria do trabalho selecionado fora da caixa
                st.info(f"**Categoria do Trabalho Selecionado:** {dict_trabalhos[id_trabalho]['categoria']}")
                st.divider()
                
                # Sliders configurados apenas para números inteiros (1 a 10)
                criterio_1 = st.slider("Inovação e Originalidade (1 a 10):", 1, 10, 5, step=1)
                criterio_2 = st.slider("Fundamentação Científica (1 a 10):", 1, 10, 5, step=1)
                criterio_3 = st.slider("Apresentação e Clareza (1 a 10):", 1, 10, 5, step=1)
                
                comentarios = st.text_area("Comentários / Justificativa (Opcional):")
                
                enviar_nota = st.form_submit_button("Submeter Avaliação")
                
            if enviar_nota:
                # Média final calculada (pode gerar float, arredondado a 2 casas)
                nota_final = round((criterio_1 + criterion_2 + criterio_3) / 3, 2)
                
                # Monta a linha incluindo a categoria correspondente do trabalho
                nova_avaliacao = pd.DataFrame([{
                    "ID": str(int(datetime.timestamp(datetime.now()))),
                    "Avaliador": st.session_state.usuario,
                    "ID_Trabalho": id_trabalho,
                    "Titulo_Trabalho": dict_trabalhos[id_trabalho]['titulo_trabalho'],
                    "Categoria": dict_trabalhos[id_trabalho]['categoria'], # Salva a categoria junto com a nota
                    "Criterio_1": int(criterio_1),
                    "Criterio_2": int(criterio_2),
                    "Criterio_3": int(criterio_3),
                    "Nota_Final": nota_final,
                    "Comentarios": comentarios,
                    "Data_Hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                }])
                
                try:
                    dados_atuais = conn.read(worksheet="Avaliacoes", ttl=0)
                    dados_novos = pd.concat([dados_atuais, nova_avaliacao], ignore_index=True)
                    conn.update(worksheet="Avaliacoes", data=dados_novos)
                    
                    st.success(f"✅ Sucesso! Nota {nota_final} enviada para o trabalho {id_trabalho}.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar na planilha: {e}")

    # -------------------------------------------------------------
    # PERFIL: ADMIN (Dashboard em Tempo Real com Filtro de Categoria)
    # -------------------------------------------------------------
    elif st.session_state.perfil == "admin":
        st.title("📊 Painel do Administrador - Tempo Real")
        st.write("Acompanhe o andamento e a premiação por categorias da feira de ciências.")
        
        try:
            # Carrega os dados reais das avaliações
            df_notas = conn.read(worksheet="Avaliacoes", ttl=0)
            
            if df_notas.empty or len(df_notas) == 0:
                st.warning("Ainda não foram enviadas avaliações pelos jurados.")
            else:
                # Garantir que os tipos numéricos estão corretos
                df_notas["Nota_Final"] = pd.to_numeric(df_notas["Nota_Final"])
                
                # FILTRO DE CATEGORIA NO DASHBOARD
                categorias_disponiveis = ["Todas"] + list(df_notas["Categoria"].unique())
                categoria_selecionada = st.selectbox("Filtrar Dashboard por Categoria (Para Premiação):", categorias_disponiveis)
                
                # Aplica o filtro se não for "Todas"
                if categoria_selecionada != "Todas":
                    df_filtrado = df_notas[df_notas["Categoria"] == categoria_selecionada]
                else:
                    df_filtrado = df_notas
                
                # Indicadores rápidos baseados no filtro selecionado
                total_avaliacoes = len(df_filtrado)
                trabalhos_avaliados = df_filtrado["ID_Trabalho"].nunique()
                media_geral = round(df_filtrado["Nota_Final"].mean(), 2)
                
                col1, col2, col3 = st.columns(3)
                col1.metric(f"Notas em '{categoria_selecionada}'", total_avaliacoes)
                col2.metric(f"Trabalhos Avaliados", trabalhos_avaliados)
                col3.metric(f"Média do Grupo", media_geral)
                
                st.divider()
                
                # Gráfico do Ranking (Média por trabalho) baseado na categoria filtrada
                st.subheader(f"🏆 Ranking de Premiação - Categoria: {categoria_selecionada}")
                
                ranking = df_filtrado.groupby(["ID_Trabalho", "Titulo_Trabalho", "Categoria"])["Nota_Final"].mean().reset_index()
                ranking = ranking.sort_values(by="Nota_Final", ascending=False)
                
                # Destaca os 3 primeiros lugares adicionando uma coluna visual se houver dados
                ranking["Posição"] = range(1, len(ranking) + 1)
                
                fig = px.bar(ranking, x="Nota_Final", y="Titulo_Trabalho", orientation='h',
                             text="Nota_Final", title=f"Classificação Atual ({categoria_selecionada})",
                             labels={"Nota_Final": "Média das Notas", "Titulo_Trabalho": "Trabalho"},
                             color="Nota_Final", color_continuous_scale="Blugrn")
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
                
                st.divider()
                
                # Tabela detalhada com posições
                st.subheader("📋 Tabela de Classificação Detalhada")
                st.dataframe(ranking.set_index("Posição"), use_container_width=True)
                
                st.divider()
                st.subheader("⏱️ Últimos Votos Computados (Histórico Geral)")
                st.dataframe(df_notas.sort_values(by="Data_Hora", ascending=False), use_container_width=True)
                
        except Exception as e:
            st.error(f"Erro ao carregar o Dashboard: {e}")