import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from collections import defaultdict
from sistema_financeiro import (
    GerenciadorContas,
    ContaCorrente,
    ContaInvestimento,
    CartaoCredito,
    Ativo,
)

# --- Configuração da Página ---
st.set_page_config(
    page_title="Super Carteira",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Funções de Formatação e Estilo ---
def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _cor_pl(val):
    if isinstance(val, (int, float)):
        color = "green" if val >= 0 else "red"
        return f"color: {color}"
    return ""

# --- Inicialização do Gerenciador ---
def inicializar_gerenciador():
    if "gerenciador" not in st.session_state:
        st.session_state.gerenciador = GerenciadorContas("dados_v15.json")
        st.session_state.gerenciador.carregar_dados()
    if "cache_posicoes" not in st.session_state:
        st.session_state.cache_posicoes = {}
    if "cache_faturas" not in st.session_state:
        st.session_state.cache_faturas = {}
    if "selected_account_id" not in st.session_state:
        st.session_state.selected_account_id = None
    if "selected_card_id" not in st.session_state:
        st.session_state.selected_card_id = None
    if "current_month_year" not in st.session_state:
        st.session_state.current_month_year = (date.today().year, date.today().month)

# --- Funções de Cache para Streamlit ---
@st.cache_data(ttl=3600) # Cache por 1 hora
def obter_posicao_conta_investimento_cached(gerenciador_instance, conta_id):
    return gerenciador_instance.calcular_posicao_conta_investimento(conta_id)

@st.cache_data(ttl=3600) # Cache por 1 hora
def obter_faturas_cartao_cached(gerenciador_instance, id_cartao):
    # Este método não existe no gerenciador, é um placeholder para cachear faturas se implementado
    # Por enquanto, retorna uma lista vazia ou um dicionário de faturas
    return [] # ou gerenciador_instance.obter_faturas_cartao(id_cartao) se existir

# --- Funções de Ação Rápida ---
def criar_acao_rapida(label, icon, key, callback, *args, **kwargs):
    if st.button(label, key=key, use_container_width=True):
        callback(*args, **kwargs)
        st.session_state.gerenciador.salvar_dados()
        st.session_state.cache_posicoes = {} # Limpa cache de posições
        st.session_state.cache_faturas = {} # Limpa cache de faturas
        # st.rerun() # Removido conforme otimização, deixa o Streamlit re-renderizar naturalmente

# --- Main Application Logic ---
def main():
    inicializar_gerenciador()
    gerenciador = st.session_state.gerenciador

    # --- Sidebar ---
    st.sidebar.title("Minhas Contas")
    contas_disponiveis = {c.id_conta: c.nome for c in gerenciador.contas}
    
    if contas_disponiveis:
        selected_account_name = st.sidebar.selectbox(
            "Selecione uma conta:",
            options=list(contas_disponiveis.values()),
            key="sidebar_account_select"
        )
        st.session_state.selected_account_id = next(
            (id for id, name in contas_disponiveis.items() if name == selected_account_name),
            None
        )
    else:
        st.sidebar.info("Nenhuma conta cadastrada.")
        st.session_state.selected_account_id = None

    saldo_total = sum(
        c.saldo
        if isinstance(c, ContaCorrente)
        else (obter_posicao_conta_investimento_cached(gerenciador, c.id_conta)["patrimonio_atualizado"] if c.id_conta in contas_disponiveis else c.saldo)
        for c in gerenciador.contas
    )
    st.sidebar.metric("Saldo Total Consolidado", formatar_moeda(saldo_total))

    # --- Tabs ---
    tab_dashboard, tab_historico, tab_contas, tab_cartoes, tab_config = st.tabs(
        ["Dashboard", "Histórico", "Contas", "Cartões", "Configurações"]
    )

    # --- Tab Dashboard ---
    with tab_dashboard:
        st.header("Dashboard Financeiro")

        if st.session_state.selected_account_id:
            conta_selecionada = gerenciador.buscar_conta_por_id(st.session_state.selected_account_id)
            if conta_selecionada:
                st.subheader(f"Visão Geral: {conta_selecionada.nome}")

                if isinstance(conta_selecionada, ContaCorrente):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Saldo Atual", formatar_moeda(conta_selecionada.saldo))
                    col2.metric("Limite Cheque Especial", formatar_moeda(conta_selecionada.limite_cheque_especial))
                    col3.metric("Saldo Disponível", formatar_moeda(conta_selecionada.saldo + conta_selecionada.limite_cheque_especial))

                    st.subheader("Ações Rápidas")
                    col_compra, col_venda, col_transf = st.columns(3)
                    with col_compra:
                        with st.expander("Registrar Receita"):
                            with st.form("form_receita_cc"):
                                descricao = st.text_input("Descrição da Receita", key="desc_rec_cc")
                                valor = st.number_input("Valor", min_value=0.01, format="%.2f", key="val_rec_cc")
                                data_transacao = st.date_input("Data", value="today", key="data_rec_cc")
                                categoria = st.selectbox("Categoria", gerenciador.categorias, key="cat_rec_cc")
                                observacao = st.text_area("Observação (opcional)", key="obs_rec_cc")
                                if st.form_submit_button("Registrar Receita"):
                                    if gerenciador.registrar_transacao(
                                        conta_selecionada.id_conta, descricao, valor, "Receita", data_transacao, categoria, observacao
                                    ):
                                        st.success("Receita registrada com sucesso!")
                                        gerenciador.salvar_dados()
                                        st.session_state.cache_posicoes = {}
                                        # st.rerun()
                                    else:
                                        st.error("Erro ao registrar receita.")
                    with col_venda:
                        with st.expander("Registrar Despesa"):
                            with st.form("form_despesa_cc"):
                                descricao = st.text_input("Descrição da Despesa", key="desc_desp_cc")
                                valor = st.number_input("Valor", min_value=0.01, format="%.2f", key="val_desp_cc")
                                data_transacao = st.date_input("Data", value="today", key="data_desp_cc")
                                categoria = st.selectbox("Categoria", gerenciador.categorias, key="cat_desp_cc")
                                observacao = st.text_area("Observação (opcional)", key="obs_desp_cc")
                                if st.form_submit_button("Registrar Despesa"):
                                    if gerenciador.registrar_transacao(
                                        conta_selecionada.id_conta, descricao, valor, "Despesa", data_transacao, categoria, observacao
                                    ):
                                        st.success("Despesa registrada com sucesso!")
                                        gerenciador.salvar_dados()
                                        st.session_state.cache_posicoes = {}
                                        # st.rerun()
                                    else:
                                        st.error("Erro ao registrar despesa. Verifique o saldo.")
                    with col_transf:
                        with st.expander("Transferir entre Contas"):
                            with st.form("form_transferencia_cc"):
                                contas_destino = {c.id_conta: c.nome for c in gerenciador.contas if c.id_conta != conta_selecionada.id_conta}
                                if contas_destino:
                                    selected_destino_name = st.selectbox("Conta Destino", options=list(contas_destino.values()), key="transf_destino_cc")
                                    id_destino = next((id for id, name in contas_destino.items() if name == selected_destino_name), None)
                                    valor = st.number_input("Valor da Transferência", min_value=0.01, format="%.2f", key="val_transf_cc")
                                    if st.form_submit_button("Transferir"):
                                        if id_destino and gerenciador.realizar_transferencia(conta_selecionada.id_conta, id_destino, valor):
                                            st.success("Transferência realizada com sucesso!")
                                            gerenciador.salvar_dados()
                                            st.session_state.cache_posicoes = {}
                                            # st.rerun()
                                        else:
                                            st.error("Erro ao realizar transferência. Verifique o saldo ou conta destino.")
                                else:
                                    st.warning("Nenhuma outra conta disponível para transferência.")

                elif isinstance(conta_selecionada, ContaInvestimento):
                    posicao = obter_posicao_conta_investimento_cached(gerenciador, conta_selecionada.id_conta)
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Saldo em Caixa", formatar_moeda(posicao["saldo_caixa"]))
                    col2.metric("Valor Total em Ativos", formatar_moeda(posicao["total_valor_atual_ativos"]))
                    col3.metric("Patrimônio Atualizado", formatar_moeda(posicao["patrimonio_atualizado"]))

                    st.subheader("Ações Rápidas")
                    col_compra, col_venda, col_atualizar = st.columns(3)
                    with col_compra:
                        with st.expander("Comprar Ativo"):
                            with st.form("form_comprar_ativo"):
                                ticker = st.text_input("Ticker do Ativo", key="ticker_compra")
                                tipo_ativo = st.selectbox("Tipo de Ativo", ["Ação BR", "Ação EUA", "FII", "Cripto", "Tesouro Direto", "Outro"], key="tipo_compra")
                                quantidade = st.number_input("Quantidade", min_value=0.000001, format="%.6f", key="qtd_compra")
                                preco_unitario = st.number_input("Preço Unitário", min_value=0.01, format="%.8f", key="preco_compra")
                                data_compra = st.date_input("Data da Compra", value="today", key="data_compra")
                                if st.form_submit_button("Comprar"):
                                    if gerenciador.comprar_ativo(
                                        conta_selecionada.id_conta, ticker, quantidade, preco_unitario, tipo_ativo, data_compra
                                    ):
                                        st.success(f"Compra de {ticker} registrada com sucesso!")
                                        gerenciador.salvar_dados()
                                        st.session_state.cache_posicoes = {}
                                        # st.rerun()
                                    else:
                                        st.error("Erro ao registrar compra. Verifique o saldo em caixa.")
                    with col_venda:
                        with st.expander("Vender Ativo"):
                            with st.form("form_vender_ativo"):
                                ativos_disponiveis = {a.ticker: a for a in conta_selecionada.ativos}
                                if ativos_disponiveis:
                                    selected_ticker = st.selectbox("Ativo para Vender", options=list(ativos_disponiveis.keys()), key="ticker_venda")
                                    ativo_venda = ativos_disponiveis[selected_ticker]
                                    
                                    st.info(f"Quantidade disponível: {ativo_venda.quantidade:.6f}")
                                    quantidade = st.number_input("Quantidade", min_value=0.000001, max_value=ativo_venda.quantidade, format="%.6f", key="qtd_venda")
                                    preco_venda = st.number_input("Preço de Venda", min_value=0.01, format="%.8f", key="preco_venda")
                                    data_venda = st.date_input("Data da Venda", value="today", key="data_venda").isoformat()
                                    observacao = st.text_area("Observação (opcional)", key="obs_venda")
                                    
                                    if st.form_submit_button("Vender"):
                                        sucesso, mensagem = gerenciador.vender_ativo(
                                            conta_selecionada.id_conta, selected_ticker, quantidade, preco_venda, data_venda, observacao
                                        )
                                        if sucesso:
                                            st.success(mensagem)
                                            gerenciador.salvar_dados()
                                            st.session_state.cache_posicoes = {}
                                            # st.rerun()
                                        else:
                                            st.error(mensagem)
                                else:
                                    st.warning("Nenhum ativo disponível para venda.")
                    with col_atualizar:
                        if st.button("Atualizar Cotações", key="btn_atualizar_cotacoes", use_container_width=True):
                            st.session_state.cache_posicoes = {} # Força recálculo
                            # st.rerun() # Removido conforme otimização

                st.subheader("Últimas Transações")
                transacoes_conta = [t for t in gerenciador.transacoes if t.id_conta == conta_selecionada.id_conta]
                if transacoes_conta:
                    df_transacoes = pd.DataFrame([t.para_dict() for t in transacoes_conta])
                    df_transacoes["data"] = pd.to_datetime(df_transacoes["data"]).dt.date
                    df_transacoes = df_transacoes.sort_values(by="data", ascending=False).head(10)
                    st.dataframe(df_transacoes.drop(columns=["id_transacao", "id_conta"]), width='stretch')
                else:
                    st.info("Nenhuma transação recente nesta conta.")
            else:
                st.warning("Conta selecionada não encontrada.")
        else:
            st.info("Selecione uma conta na barra lateral para ver o dashboard.")

    # --- Tab Histórico ---
    with tab_historico:
        st.header("Histórico de Transações")
        
        if gerenciador.transacoes:
            df_transacoes = pd.DataFrame([t.para_dict() for t in gerenciador.transacoes])
            df_transacoes["data"] = pd.to_datetime(df_transacoes["data"]).dt.date
            df_transacoes["valor"] = df_transacoes["valor"].apply(formatar_moeda)
            
            contas_map = {c.id_conta: c.nome for c in gerenciador.contas}
            df_transacoes["conta"] = df_transacoes["id_conta"].map(contas_map)
            
            df_transacoes_display = df_transacoes[[
                "data", "conta", "descricao", "tipo", "categoria", "valor", "observacao", "id_transacao"
            ]].sort_values(by="data", ascending=False)

            st.dataframe(
                df_transacoes_display,
                hide_index=True,
                column_config={
                    "id_transacao": st.column_config.Column(
                        "ID",
                        help="ID único da transação",
                        width="small"
                    )
                },
                width='stretch'
            )

            st.subheader("Remover Transação")
            transacoes_para_remover = {t.id_transacao: f"{t.data.isoformat()} - {t.descricao} ({t.valor})" for t in gerenciador.transacoes}
            if transacoes_para_remover:
                id_transacao_selecionada = st.selectbox(
                    "Selecione a transação para remover:",
                    options=list(transacoes_para_remover.keys()),
                    format_func=lambda x: transacoes_para_remover[x],
                    key="select_remover_transacao"
                )
                if st.button("Confirmar Remoção", key="btn_remover_transacao"):
                    if gerenciador.remover_transacao(id_transacao_selecionada):
                        st.success("Transação removida com sucesso!")
                        gerenciador.salvar_dados()
                        st.session_state.cache_posicoes = {}
                        st.session_state.cache_faturas = {}
                        st.rerun() # Rerun aqui é necessário para atualizar o dataframe exibido e o selectbox
                    else:
                        st.error("Erro ao remover transação.")
            else:
                st.info("Nenhuma transação para remover.")
        else:
            st.info("Nenhuma transação registrada ainda.")

    # --- Tab Contas ---
    with tab_contas:
        st.header("Gerenciar Contas")

        st.subheader("Contas Cadastradas")
        if gerenciador.contas:
            dados_contas = []
            for c in gerenciador.contas:
                if isinstance(c, ContaCorrente):
                    dados_contas.append({
                        "ID": c.id_conta,
                        "Nome": c.nome,
                        "Tipo": "Corrente",
                        "Saldo": formatar_moeda(c.saldo),
                        "Limite Cheque Especial": formatar_moeda(c.limite_cheque_especial),
                        "Patrimônio Atualizado": formatar_moeda(c.saldo)
                    })
                elif isinstance(c, ContaInvestimento):
                    posicao = obter_posicao_conta_investimento_cached(gerenciador, c.id_conta)
                    dados_contas.append({
                        "ID": c.id_conta,
                        "Nome": c.nome,
                        "Tipo": "Investimento",
                        "Saldo em Caixa": formatar_moeda(posicao["saldo_caixa"]),
                        "Valor Total em Ativos": formatar_moeda(posicao["total_valor_atual_ativos"]),
                        "Patrimônio Atualizado": formatar_moeda(posicao["patrimonio_atualizado"])
                    })
            df_contas = pd.DataFrame(dados_contas)
            st.dataframe(df_contas, width='stretch')

            st.subheader("Detalhes e Posição de Investimento")
            contas_investimento = {c.id_conta: c.nome for c in gerenciador.contas if isinstance(c, ContaInvestimento)}
            if contas_investimento:
                selected_inv_account_name = st.selectbox(
                    "Selecione uma conta de investimento:",
                    options=list(contas_investimento.values()),
                    key="select_inv_account"
                )
                selected_inv_account_id = next(
                    (id for id, name in contas_investimento.items() if name == selected_inv_account_name),
                    None
                )
                if selected_inv_account_id:
                    conta_inv = gerenciador.buscar_conta_por_id(selected_inv_account_id)
                    if conta_inv and isinstance(conta_inv, ContaInvestimento):
                        posicao = obter_posicao_conta_investimento_cached(gerenciador, conta_inv.id_conta)
                        
                        st.markdown(f"### Posição Atual de {conta_inv.nome}")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Saldo em Caixa", formatar_moeda(posicao["saldo_caixa"]))
                        col2.metric("Valor Total em Ativos", formatar_moeda(posicao["total_valor_atual_ativos"]))
                        col3.metric("Patrimônio Atualizado", formatar_moeda(posicao["patrimonio_atualizado"]))

                        if posicao["ativos"]:
                            df_ativos = pd.DataFrame(posicao["ativos"])
                            df_ativos["preco_medio"] = df_ativos["preco_medio"].apply(formatar_moeda)
                            df_ativos["preco_atual"] = df_ativos["preco_atual"].apply(formatar_moeda)
                            df_ativos["valor_atual"] = df_ativos["valor_atual"].apply(formatar_moeda)
                            df_ativos["pl"] = df_ativos["pl"].apply(formatar_moeda)
                            df_ativos["pl_pct"] = df_ativos["pl_pct"].apply(lambda x: f"{x:+.2f}%")

                            st.dataframe(
                                df_ativos.style.map(_cor_pl, subset=["pl", "pl_pct"]),
                                hide_index=True,
                                width='stretch'
                            )
                        else:
                            st.info("Nenhum ativo nesta conta de investimento.")
            else:
                st.info("Nenhuma conta de investimento cadastrada.")
        else:
            st.info("Nenhuma conta cadastrada ainda.")

        st.subheader("Adicionar Nova Conta")
        tipo_nova_conta = st.radio("Tipo de Conta", ["Corrente", "Investimento"], key="tipo_nova_conta")
        with st.form("form_nova_conta"):
            nome_nova_conta = st.text_input("Nome da Conta", key="nome_nova_conta")
            logo_url_nova_conta = st.text_input("URL do Logo (opcional)", key="logo_nova_conta")
            if tipo_nova_conta == "Corrente":
                saldo_inicial = st.number_input("Saldo Inicial", value=0.0, format="%.2f", key="saldo_inicial_cc")
                limite_cheque_especial = st.number_input("Limite Cheque Especial", value=0.0, format="%.2f", key="limite_cc")
            else: # Investimento
                saldo_inicial = st.number_input("Saldo Inicial em Caixa", value=0.0, format="%.2f", key="saldo_inicial_inv")
            
            if st.form_submit_button("Adicionar Conta"):
                if nome_nova_conta:
                    if tipo_nova_conta == "Corrente":
                        nova_conta = ContaCorrente(nome_nova_conta, saldo_inicial, limite_cheque_especial, logo_url_nova_conta)
                    else:
                        nova_conta = ContaInvestimento(nome_nova_conta, logo_url_nova_conta, saldo_inicial)
                    gerenciador.adicionar_conta(nova_conta)
                    gerenciador.salvar_dados()
                    st.success(f"Conta '{nome_nova_conta}' adicionada com sucesso!")
                    st.session_state.cache_posicoes = {}
                    st.rerun() # Rerun aqui é necessário para atualizar a sidebar e os selectboxes
                else:
                    st.error("O nome da conta não pode ser vazio.")

        st.subheader("Remover Conta")
        if contas_disponiveis:
            id_conta_remover = st.selectbox(
                "Selecione a conta para remover:",
                options=list(contas_disponiveis.keys()),
                format_func=lambda x: contas_disponiveis[x],
                key="select_remover_conta"
            )
            if st.button("Confirmar Remoção da Conta", key="btn_remover_conta"):
                if gerenciador.remover_conta(id_conta_remover):
                    st.success("Conta e transações associadas removidas com sucesso!")
                    gerenciador.salvar_dados()
                    st.session_state.cache_posicoes = {}
                    st.session_state.cache_faturas = {}
                    st.rerun() # Rerun aqui é necessário para atualizar a sidebar e os selectboxes
                else:
                    st.error("Erro ao remover conta.")
        else:
            st.info("Nenhuma conta para remover.")

    # --- Tab Cartões ---
    with tab_cartoes:
        st.header("Gerenciar Cartões de Crédito")

        st.subheader("Cartões Cadastrados")
        if gerenciador.cartoes_credito:
            df_cartoes = pd.DataFrame([c.para_dict() for c in gerenciador.cartoes_credito])
            st.dataframe(df_cartoes.drop(columns=["id_cartao"]), width='stretch')

            cartoes_disponiveis = {c.id_cartao: c.nome for c in gerenciador.cartoes_credito}
            selected_card_name = st.selectbox(
                "Selecione um cartão:",
                options=list(cartoes_disponiveis.values()),
                key="select_card_tab_cartoes"
            )
            st.session_state.selected_card_id = next(
                (id for id, name in cartoes_disponiveis.items() if name == selected_card_name),
                None
            )
            
            if st.session_state.selected_card_id:
                cartao_selecionado = gerenciador.buscar_cartao_por_id(st.session_state.selected_card_id)
                if cartao_selecionado:
                    st.markdown(f"### Faturas de {cartao_selecionado.nome}")

                    # Navegação entre ciclos
                    ciclos_disponiveis = gerenciador.listar_ciclos_navegacao(cartao_selecionado.id_cartao)
                    
                    if ciclos_disponiveis:
                        ciclo_formatado = [f"{calendar.month_name[m].capitalize()}/{a}" for a, m in ciclos_disponiveis]
                        
                        # Tenta manter o ciclo atual se ele ainda estiver disponível
                        if st.session_state.current_month_year in ciclos_disponiveis:
                            idx_selecionado = ciclos_disponiveis.index(st.session_state.current_month_year)
                        else:
                            # Se não, seleciona o ciclo mais recente
                            idx_selecionado = len(ciclos_disponiveis) - 1

                        selected_ciclo_str = st.selectbox(
                            "Selecione o ciclo:",
                            options=ciclo_formatado,
                            index=idx_selecionado,
                            key="select_ciclo_cartao"
                        )
                        st.session_state.current_month_year = ciclos_disponiveis[ciclo_formatado.index(selected_ciclo_str)]
                        
                        ano_ciclo, mes_ciclo = st.session_state.current_month_year

                        # Faturas fechadas para o ciclo
                        faturas_fechadas = [
                            f for f in gerenciador.faturas
                            if f.id_cartao == cartao_selecionado.id_cartao
                            and f.data_vencimento.year == ano_ciclo
                            and f.data_vencimento.month == mes_ciclo
                        ]

                        if faturas_fechadas:
                            fatura_atual = faturas_fechadas[0] # Pega a primeira (deve ser única por ciclo)
                            st.info(f"Fatura fechada para {calendar.month_name[mes_ciclo].capitalize()}/{ano_ciclo}:")
                            col_f1, col_f2, col_f3 = st.columns(3)
                            col_f1.metric("Valor Total", formatar_moeda(fatura_atual.valor_total))
                            col_f2.metric("Vencimento", fatura_atual.data_vencimento.strftime("%d/%m/%Y"))
                            col_f3.metric("Status", fatura_atual.status)

                            if fatura_atual.status == "Fechada":
                                contas_corrente = {c.id_conta: c.nome for c in gerenciador.contas if isinstance(c, ContaCorrente)}
                                if contas_corrente:
                                    with st.form(f"form_pagar_fatura_{fatura_atual.id_fatura}"):
                                        st.subheader("Pagar Fatura")
                                        conta_pagamento_name = st.selectbox(
                                            "Conta para Pagamento",
                                            options=list(contas_corrente.values()),
                                            key=f"conta_pagamento_{fatura_atual.id_fatura}"
                                        )
                                        id_conta_pagamento = next(
                                            (id for id, name in contas_corrente.items() if name == conta_pagamento_name),
                                            None
                                        )
                                        data_pagamento = st.date_input("Data do Pagamento", value="today", key=f"data_pagamento_{fatura_atual.id_fatura}")
                                        if st.form_submit_button("Confirmar Pagamento"):
                                            if id_conta_pagamento and gerenciador.pagar_fatura(fatura_atual.id_fatura, id_conta_pagamento, data_pagamento):
                                                st.success("Fatura paga com sucesso!")
                                                gerenciador.salvar_dados()
                                                st.session_state.cache_posicoes = {}
                                                st.session_state.cache_faturas = {}
                                                st.rerun() # Rerun para atualizar o status da fatura
                                            else:
                                                st.error("Erro ao pagar fatura. Verifique o saldo da conta.")
                                else:
                                    st.warning("Nenhuma conta corrente disponível para pagamento de fatura.")
                            
                            st.markdown("#### Compras desta fatura")
                            compras_fatura = [c for c in gerenciador.compras_cartao if c.id_fatura == fatura_atual.id_fatura]
                            if compras_fatura:
                                df_compras_fatura = pd.DataFrame([c.para_dict() for c in compras_fatura])
                                df_compras_fatura["data_compra"] = pd.to_datetime(df_compras_fatura["data_compra"]).dt.date
                                df_compras_fatura["data_compra_real"] = pd.to_datetime(df_compras_fatura["data_compra_real"]).dt.date
                                df_compras_fatura["valor"] = df_compras_fatura["valor"].apply(formatar_moeda)
                                st.dataframe(df_compras_fatura.drop(columns=["id_compra", "id_cartao", "id_compra_original", "id_fatura"]), width='stretch')
                            else:
                                st.info("Nenhuma compra nesta fatura.")

                        else: # Fatura aberta
                            st.info(f"Fatura aberta para {calendar.month_name[mes_ciclo].capitalize()}/{ano_ciclo}.")
                            compras_abertas = gerenciador.obter_lancamentos_do_ciclo(cartao_selecionado.id_cartao, ano_ciclo, mes_ciclo)
                            
                            if compras_abertas:
                                total_aberto = sum(c.valor for c in compras_abertas)
                                st.metric("Valor Total da Fatura Aberta", formatar_moeda(total_aberto))
                                
                                df_compras_abertas = pd.DataFrame([c.para_dict() for c in compras_abertas])
                                df_compras_abertas["data_compra"] = pd.to_datetime(df_compras_abertas["data_compra"]).dt.date
                                df_compras_abertas["data_compra_real"] = pd.to_datetime(df_compras_abertas["data_compra_real"]).dt.date
                                df_compras_abertas["valor"] = df_compras_abertas["valor"].apply(formatar_moeda)
                                st.dataframe(df_compras_abertas.drop(columns=["id_compra", "id_cartao", "id_compra_original", "id_fatura"]), width='stretch')

                                st.subheader("Fechar Fatura")
                                with st.form(f"form_fechar_fatura_{cartao_selecionado.id_cartao}_{ano_ciclo}_{mes_ciclo}"):
                                    data_fechamento = st.date_input("Data de Fechamento", value="today", key=f"data_fechamento_{ano_ciclo}_{mes_ciclo}")
                                    data_vencimento = st.date_input("Data de Vencimento", value=data_fechamento + timedelta(days=10), key=f"data_vencimento_{ano_ciclo}_{mes_ciclo}")
                                    if st.form_submit_button("Confirmar Fechamento da Fatura"):
                                        fatura_fechada = gerenciador.fechar_fatura(cartao_selecionado.id_cartao, data_fechamento, data_vencimento)
                                        if fatura_fechada:
                                            st.success(f"Fatura fechada com sucesso! Valor: {formatar_moeda(fatura_fechada.valor_total)}")
                                            gerenciador.salvar_dados()
                                            st.session_state.cache_faturas = {}
                                            st.rerun() # Rerun para atualizar o status da fatura
                                        else:
                                            st.error("Erro ao fechar fatura.")
                            else:
                                st.info(f"Nenhuma compra na fatura aberta de {calendar.month_name[mes_ciclo].capitalize()}/{ano_ciclo}.")
                    else:
                        st.info("Nenhum ciclo de fatura disponível para este cartão.")
                else:
                    st.warning("Cartão selecionado não encontrado.")
            else:
                st.info("Selecione um cartão para ver suas faturas.")

            st.subheader("Registrar Compra no Cartão")
            with st.form("form_nova_compra_cartao"):
                cartoes_para_compra = {c.id_cartao: c.nome for c in gerenciador.cartoes_credito}
                if cartoes_para_compra:
                    selected_card_compra_name = st.selectbox(
                        "Cartão de Crédito",
                        options=list(cartoes_para_compra.values()),
                        key="card_compra_select"
                    )
                    id_cartao_compra = next(
                        (id for id, name in cartoes_para_compra.items() if name == selected_card_compra_name),
                        None
                    )
                    descricao = st.text_input("Descrição da Compra", key="desc_compra_cartao")
                    valor_total = st.number_input("Valor Total da Compra", min_value=0.01, format="%.2f", key="val_compra_cartao")
                    data_compra_real = st.date_input("Data da Compra (real)", value="today", key="data_compra_real_cartao")
                    categoria = st.selectbox("Categoria", gerenciador.categorias, key="cat_compra_cartao")
                    num_parcelas = st.number_input("Número de Parcelas", min_value=1, value=1, step=1, key="parcelas_compra_cartao")
                    observacao = st.text_area("Observação (opcional)", key="obs_compra_cartao")
                    if st.form_submit_button("Registrar Compra"):
                        if id_cartao_compra and gerenciador.registrar_compra_cartao(
                            id_cartao_compra, descricao, valor_total, data_compra_real, categoria, num_parcelas, observacao
                        ):
                            st.success("Compra registrada com sucesso!")
                            gerenciador.salvar_dados()
                            st.session_state.cache_faturas = {}
                            # st.rerun()
                        else:
                            st.error("Erro ao registrar compra.")
                else:
                    st.warning("Nenhum cartão de crédito cadastrado para registrar compras.")

            st.subheader("Adicionar Novo Cartão de Crédito")
            with st.form("form_novo_cartao"):
                nome_novo_cartao = st.text_input("Nome do Cartão", key="nome_novo_cartao")
                logo_url_novo_cartao = st.text_input("URL do Logo (opcional)", key="logo_novo_cartao")
                dia_fechamento = st.number_input("Dia de Fechamento da Fatura", min_value=1, max_value=31, value=28, key="dia_fechamento_cartao")
                dia_vencimento = st.number_input("Dia de Vencimento da Fatura", min_value=1, max_value=31, value=10, key="dia_vencimento_cartao")
                if st.form_submit_button("Adicionar Cartão"):
                    if nome_novo_cartao:
                        novo_cartao = CartaoCredito(nome_novo_cartao, logo_url_novo_cartao, dia_fechamento, dia_vencimento)
                        gerenciador.adicionar_cartao_credito(novo_cartao)
                        gerenciador.salvar_dados()
                        st.success(f"Cartão '{nome_novo_cartao}' adicionado com sucesso!")
                        st.session_state.cache_faturas = {}
                        st.rerun() # Rerun para atualizar os selectboxes
                    else:
                        st.error("O nome do cartão não pode ser vazio.")

            st.subheader("Remover Cartão de Crédito")
            if cartoes_disponiveis:
                id_cartao_remover = st.selectbox(
                    "Selecione o cartão para remover:",
                    options=list(cartoes_disponiveis.keys()),
                    format_func=lambda x: cartoes_disponiveis[x],
                    key="select_remover_cartao"
                )
                if st.button("Confirmar Remoção do Cartão", key="btn_remover_cartao"):
                    if gerenciador.remover_cartao_credito(id_cartao_remover):
                        st.success("Cartão, compras e faturas associadas removidas com sucesso!")
                        gerenciador.salvar_dados()
                        st.session_state.cache_faturas = {}
                        st.rerun() # Rerun para atualizar os selectboxes
                    else:
                        st.error("Erro ao remover cartão.")
            else:
                st.info("Nenhum cartão para remover.")

    # --- Tab Configurações ---
    with tab_config:
        st.header("Configurações")

        st.subheader("Categorias")
        if gerenciador.categorias:
            st.write("Categorias Atuais:")
            st.write(", ".join(gerenciador.categorias))
        
        with st.form("form_add_categoria"):
            nova_categoria = st.text_input("Adicionar Nova Categoria", key="nova_categoria_input")
            if st.form_submit_button("Adicionar Categoria"):
                if nova_categoria:
                    gerenciador.adicionar_categoria(nova_categoria)
                    gerenciador.salvar_dados()
                    st.success(f"Categoria '{nova_categoria}' adicionada.")
                    st.rerun()
                else:
                    st.error("O nome da categoria não pode ser vazio.")
        
        if gerenciador.categorias:
            with st.form("form_remover_categoria"):
                categoria_remover = st.selectbox("Remover Categoria", gerenciador.categorias, key="remover_categoria_select")
                if st.form_submit_button("Remover Categoria"):
                    gerenciador.remover_categoria(categoria_remover)
                    gerenciador.salvar_dados()
                    st.success(f"Categoria '{categoria_remover}' removida.")
                    st.rerun()

        st.subheader("Salvar/Carregar Dados")
        if st.button("Salvar Dados Agora", key="btn_salvar_dados"):
            gerenciador.salvar_dados()
            st.success("Dados salvos com sucesso!")
        
        st.info(f"Os dados são salvos automaticamente em '{gerenciador.caminho_arquivo}'.")

if __name__ == "__main__":
    main()
