import streamlit as st
from datetime import date, datetime
from sistema_financeiro import (
    GerenciadorContas,
    ContaCorrente,
    ContaInvestimento,
    CartaoCredito,
    Transacao,
    Fatura,
    Ativo, # Importar Ativo para reconstruir objetos na venda
)
import pandas as pd
import plotly.express as px # Importado mas não usado no código fornecido
import calendar

# --- Configurações Iniciais ---
st.set_page_config(layout="wide", page_title="Super Carteira")

# Inicializa o gerenciador de contas
if "gerenciador" not in st.session_state:
    st.session_state.gerenciador = GerenciadorContas("dados_v15.json")

# --- Otimização: Cache de Posições (Session-based) ---
# Este cache armazena os resultados de calcular_posicao_conta_investimento
# para evitar recálculos caros em cada re-renderização.
if 'cache_posicoes' not in st.session_state:
    st.session_state.cache_posicoes = {}

def get_cached_position(conta_id: str) -> dict:
    """Retorna a posição da conta de investimento do cache ou calcula e armazena."""
    if conta_id not in st.session_state.cache_posicoes:
        st.session_state.cache_posicoes[conta_id] = st.session_state.gerenciador.calcular_posicao_conta_investimento(conta_id)
    return st.session_state.cache_posicoes[conta_id]

def clear_position_cache():
    """Limpa o cache de posições após modificações nos dados financeiros."""
    st.session_state.cache_posicoes = {}

# --- Funções Auxiliares de UI ---
def _cor_pl(val):
    color = "green" if val >= 0 else "red"
    return f"color: {color}"

def _format_currency(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _format_percentage(val):
    return f"{val:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")

def _format_quantity(val):
    return f"{val:,.6f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- Sidebar ---
st.sidebar.title("Navegação")
pagina_selecionada = st.sidebar.radio(
    "Ir para", ["Dashboard", "Histórico", "Contas", "Cartões", "Configurações"]
)

# --- Dashboard ---
if pagina_selecionada == "Dashboard":
    st.title("📊 Dashboard Financeiro")

    # Visão Geral
    st.header("Visão Geral")
    total_patrimonio = 0.0
    total_saldo_corrente = 0.0
    total_saldo_investimento = 0.0

    for conta in st.session_state.gerenciador.contas:
        if isinstance(conta, ContaCorrente):
            total_saldo_corrente += conta.saldo
            total_patrimonio += conta.saldo
        elif isinstance(conta, ContaInvestimento):
            # Usar a função de cache para obter a posição
            posicao = get_cached_position(conta.id_conta)
            total_saldo_investimento += posicao["patrimonio_atualizado"]
            total_patrimonio += posicao["patrimonio_atualizado"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Patrimônio Total", _format_currency(total_patrimonio))
    with col2:
        st.metric("Saldo Contas Correntes", _format_currency(total_saldo_corrente))
    with col3:
        st.metric("Saldo Investimentos", _format_currency(total_saldo_investimento))
    with col4:
        # Calcular total de despesas e receitas do mês atual
        hoje = date.today()
        primeiro_dia_mes = hoje.replace(day=1)
        ultimo_dia_mes = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])

        # @st.cache_data para otimizar o cálculo de transações do mês
        @st.cache_data(ttl=3600) # Cache por 1 hora
        def get_monthly_summary(transacoes_list, p_dia_mes, u_dia_mes):
            transacoes_mes = [
                t for t in transacoes_list
                if p_dia_mes <= t.data <= u_dia_mes
            ]
            total_receitas_mes = sum(t.valor for t in transacoes_mes if t.tipo == "Receita")
            total_despesas_mes = sum(t.valor for t in transacoes_mes if t.tipo == "Despesa")
            return total_receitas_mes, total_despesas_mes

        total_receitas_mes, total_despesas_mes = get_monthly_summary(
            st.session_state.gerenciador.transacoes, primeiro_dia_mes, ultimo_dia_mes
        )
        saldo_mes = total_receitas_mes - total_despesas_mes
        st.metric("Saldo do Mês", _format_currency(saldo_mes))

    st.markdown("---")

    # --------------------------
    # Comprar Ativo (por ID, exibindo apenas nome)
    # --------------------------
    with st.expander("📈 Comprar Ativo"):
        contas_investimento = [
            c for c in st.session_state.gerenciador.contas if isinstance(c, ContaInvestimento)
        ]
        if not contas_investimento:
            st.warning("Crie uma Conta de Investimento na aba 'Contas' para comprar ativos.")
        else:
            # Mapa por ID, exibindo apenas nome
            mapa_ci = {c.id_conta: c for c in contas_investimento}
            ids_ci = list(mapa_ci.keys())
            with st.form("buy_asset_form", clear_on_submit=True):
                st.write("Registrar Compra de Ativo")
                conta_destino_id = st.selectbox(
                    "Comprar na corretora:",
                    options=ids_ci,
                    format_func=lambda cid: mapa_ci[cid].nome,
                    key="buy_asset_conta_destino_id"
                )
                ticker_input = st.text_input("Ticker do Ativo (ex: PETR4, AAPL, Tesouro Selic 2029)")
                tipo_ativo = st.selectbox("Tipo de Ativo", ["Ação BR", "FII", "Ação EUA", "Cripto", "Tesouro Direto", "Outro"])

                # Instruções de formato do ticker por tipo
                if tipo_ativo == "Tesouro Direto":
                    st.info("💡 **Formato:** Digite o nome completo do título. Exemplos: 'Tesouro Selic 2029', 'Tesouro IPCA+ 2035', 'Tesouro Prefixado 2027'")
                elif tipo_ativo == "Cripto":
                    st.info("💡 **Formato:** Use o símbolo da criptomoeda. Exemplos: 'BTC', 'ETH', 'PEPE', 'DOGE'")
                elif tipo_ativo == "Ação BR" or tipo_ativo == "FII":
                    st.info("💡 **Formato:** Use o código da B3. Exemplos: 'PETR4', 'VALE3', 'MXRF11'")
                elif tipo_ativo == "Ação EUA":
                    st.info("💡 **Formato:** Use o ticker da NYSE/NASDAQ. Exemplos: 'AAPL', 'MSFT', 'GOOGL'")

                # Normaliza ticker conforme o tipo
                if tipo_ativo == "Tesouro Direto":
                    ticker = ticker_input.strip()  # Mantém maiúsculas/minúsculas
                else:
                    ticker = ticker_input.upper()  # Converte para maiúsculas

                col_qnt, col_preco = st.columns(2)
                with col_qnt:
                    quantidade = st.number_input("Quantidade", min_value=0.000001, format="%.6f")
                with col_preco:
                    preco_unitario = st.number_input("Preço por Unidade (R$)", min_value=0.00000001, format="%.8f")
                data_compra = st.date_input("Data da Compra", value=datetime.today(), format="DD/MM/YYYY")
                if st.form_submit_button("Confirmar Compra"):
                    if not all([ticker, quantidade > 0, preco_unitario > 0]):
                        st.error("Preencha todos os detalhes da compra do ativo.")
                    else:
                        sucesso = st.session_state.gerenciador.comprar_ativo(
                            id_conta_destino=conta_destino_id,
                            ticker=ticker,
                            quantidade=quantidade,
                            preco_unitario=preco_unitario,
                            tipo_ativo=tipo_ativo,
                            data_compra=data_compra,
                        )
                        if sucesso:
                            st.session_state.gerenciador.salvar_dados()
                            clear_position_cache() # Limpa o cache de posições
                            st.success(f"Compra de {ticker} registrada!")
                            # st.rerun() # Removido: o formulário limpa e o estado da sessão atualiza naturalmente
                        else:
                            st.error("Falha na compra. Verifique o saldo em caixa da corretora.")


    # Vender Ativo
    with st.expander("📊 Vender Ativo", expanded=False):
        contas_inv_venda = [c for c in st.session_state.gerenciador.contas if isinstance(c, ContaInvestimento)]

        if not contas_inv_venda:
            st.info("Crie uma Conta de Investimento para vender ativos.")
        else:
            conta_venda_sel = st.selectbox("Conta de Investimento", contas_inv_venda, format_func=lambda x: x.nome, key="conta_venda_sel")

            # Lista os ativos disponíveis para venda
            # Usar a função de cache para obter os ativos da conta
            posicao_conta_venda = get_cached_position(conta_venda_sel.id_conta)
            # Reconstruir objetos Ativo a partir do dicionário para compatibilidade com selectbox
            ativos_disponiveis = [Ativo(a['ticker'], a['quantidade'], a['preco_medio'], a['tipo']) for a in posicao_conta_venda['ativos']]

            if not ativos_disponiveis:
                st.info("Não há ativos nesta conta para vender.")
            else:
                ticker_venda = st.selectbox("Ativo para Vender", ativos_disponiveis, format_func=lambda x: f"{x.ticker} ({x.quantidade:.6f} disponível)", key="ticker_venda")

                col_venda1, col_venda2 = st.columns(2)
                with col_venda1:
                    qtd_venda = st.number_input("Quantidade a Vender", min_value=0.000001, max_value=float(ticker_venda.quantidade), value=float(ticker_venda.quantidade), step=0.01, format="%.6f", key="qtd_venda")
                with col_venda2:
                    preco_venda = st.number_input("Preço de Venda (R$ por unidade)", min_value=0.01, value=float(ticker_venda.preco_medio), step=0.01, format="%.2f", key="preco_venda")

                # Calcula preview do P/L
                valor_venda_preview = qtd_venda * preco_venda
                custo_medio_preview = qtd_venda * ticker_venda.preco_medio
                pl_preview = valor_venda_preview - custo_medio_preview
                pl_pct_preview = (pl_preview / custo_medio_preview * 100) if custo_medio_preview > 0 else 0

                if pl_preview >= 0:
                    st.success(f"💰 **Lucro Estimado:** R$ {pl_preview:.2f} ({pl_pct_preview:+.2f}%)")
                else:
                    st.error(f"📉 **Prejuízo Estimado:** R$ {abs(pl_preview):.2f} ({pl_pct_preview:.2f}%)")

                data_venda = st.date_input("Data da Venda", value=datetime.today(), format="DD/MM/YYYY", key="data_venda")
                obs_venda = st.text_input("Observação (opcional)", key="obs_venda")

                if st.button("✅ Confirmar Venda", type="primary", key="vender_btn"):
                    sucesso, mensagem = st.session_state.gerenciador.vender_ativo(
                        id_conta=conta_venda_sel.id_conta,
                        ticker=ticker_venda.ticker,
                        quantidade=qtd_venda,
                        preco_venda=preco_venda,
                        data_venda=data_venda.strftime("%Y-%m-%d"),
                        observacao=obs_venda
                    )
                    if sucesso:
                        st.session_state.gerenciador.salvar_dados()
                        clear_position_cache() # Limpa o cache de posições
                        st.success(mensagem)
                        # st.rerun() # Removido: o estado da sessão atualiza naturalmente
                    else:
                        st.error(mensagem)

    st.markdown("---")

    # --------------------------
    # Registrar Transação
    # --------------------------
    with st.expander("💸 Registrar Transação"):
        contas_disponiveis = st.session_state.gerenciador.contas
        if not contas_disponiveis:
            st.warning("Crie uma conta na aba 'Contas' para registrar transações.")
        else:
            mapa_contas = {c.id_conta: c for c in contas_disponiveis}
            ids_contas = list(mapa_contas.keys())
            with st.form("transaction_form", clear_on_submit=True):
                st.write("Nova Transação")
                conta_selecionada_id = st.selectbox(
                    "Conta:",
                    options=ids_contas,
                    format_func=lambda cid: mapa_contas[cid].nome,
                    key="trans_conta_selecionada_id"
                )
                descricao = st.text_input("Descrição")
                valor = st.number_input("Valor", min_value=0.01, format="%.2f")
                tipo = st.radio("Tipo", ["Receita", "Despesa"])
                categoria = st.selectbox("Categoria", st.session_state.gerenciador.categorias)
                data_transacao = st.date_input("Data da Transação", value=datetime.today(), format="DD/MM/YYYY")
                observacao = st.text_input("Observação (opcional)")

                if st.form_submit_button("Registrar"):
                    if not all([descricao, valor > 0]):
                        st.error("Preencha todos os campos obrigatórios.")
                    else:
                        sucesso = st.session_state.gerenciador.registrar_transacao(
                            id_conta=conta_selecionada_id,
                            descricao=descricao,
                            valor=valor,
                            tipo=tipo,
                            data_transacao=data_transacao,
                            categoria=categoria,
                            observacao=observacao,
                        )
                        if sucesso:
                            st.session_state.gerenciador.salvar_dados()
                            clear_position_cache() # Limpa o cache de posições
                            st.success("Transação registrada com sucesso!")
                            # st.rerun() # Removido: o formulário limpa e o estado da sessão atualiza naturalmente
                        else:
                            st.error("Falha ao registrar transação. Verifique o saldo da conta.")

    st.markdown("---")

    # --------------------------
    # Registrar Compra no Cartão de Crédito
    # --------------------------
    with st.expander("💳 Registrar Compra no Cartão de Crédito"):
        cartoes_disponiveis = st.session_state.gerenciador.cartoes_credito
        if not cartoes_disponiveis:
            st.warning("Crie um cartão de crédito na aba 'Cartões' para registrar compras.")
        else:
            mapa_cartoes = {cc.id_cartao: cc for cc in cartoes_disponiveis}
            ids_cartoes = list(mapa_cartoes.keys())
            with st.form("card_purchase_form", clear_on_submit=True):
                st.write("Nova Compra no Cartão")
                cartao_selecionado_id = st.selectbox(
                    "Cartão:",
                    options=ids_cartoes,
                    format_func=lambda cid: mapa_cartoes[cid].nome,
                    key="card_purchase_cartao_selecionado_id"
                )
                descricao_compra = st.text_input("Descrição da Compra")
                valor_compra = st.number_input("Valor Total da Compra", min_value=0.01, format="%.2f")
                data_compra_real = st.date_input("Data da Compra", value=datetime.today(), format="DD/MM/YYYY")
                categoria_compra = st.selectbox("Categoria", st.session_state.gerenciador.categorias, key="card_purchase_categoria")
                num_parcelas = st.number_input("Número de Parcelas", min_value=1, value=1)
                observacao_compra = st.text_input("Observação (opcional)", key="card_purchase_observacao")

                if st.form_submit_button("Registrar Compra"):
                    if not all([descricao_compra, valor_compra > 0]):
                        st.error("Preencha todos os campos obrigatórios.")
                    else:
                        sucesso = st.session_state.gerenciador.registrar_compra_cartao(
                            id_cartao=cartao_selecionado_id,
                            descricao=descricao_compra,
                            valor_total=valor_compra,
                            data_compra=data_compra_real,
                            categoria=categoria_compra,
                            num_parcelas=num_parcelas,
                            observacao=observacao_compra,
                        )
                        if sucesso:
                            st.session_state.gerenciador.salvar_dados()
                            st.success("Compra no cartão registrada com sucesso!")
                            # st.rerun() # Removido: o formulário limpa e o estado da sessão atualiza naturalmente
                        else:
                            st.error("Falha ao registrar compra no cartão.")

    st.markdown("---")

    # --------------------------
    # Transferência entre Contas
    # --------------------------
    with st.expander("➡️ Transferência entre Contas"):
        contas_transferencia = st.session_state.gerenciador.contas
        if len(contas_transferencia) < 2:
            st.warning("Crie pelo menos duas contas para realizar transferências.")
        else:
            mapa_contas_transf = {c.id_conta: c for c in contas_transferencia}
            ids_contas_transf = list(mapa_contas_transf.keys())
            with st.form("transfer_form", clear_on_submit=True):
                st.write("Nova Transferência")
                conta_origem_id = st.selectbox(
                    "Conta de Origem:",
                    options=ids_contas_transf,
                    format_func=lambda cid: mapa_contas_transf[cid].nome,
                    key="transfer_conta_origem_id"
                )
                conta_destino_id = st.selectbox(
                    "Conta de Destino:",
                    options=ids_contas_transf,
                    format_func=lambda cid: mapa_contas_transf[cid].nome,
                    key="transfer_conta_destino_id"
                )
                valor_transferencia = st.number_input("Valor da Transferência", min_value=0.01, format="%.2f")

                if st.form_submit_button("Confirmar Transferência"):
                    if conta_origem_id == conta_destino_id:
                        st.error("Conta de origem e destino não podem ser as mesmas.")
                    elif valor_transferencia <= 0:
                        st.error("O valor da transferência deve ser maior que zero.")
                    else:
                        sucesso = st.session_state.gerenciador.realizar_transferencia(
                            id_origem=conta_origem_id,
                            id_destino=conta_destino_id,
                            valor=valor_transferencia,
                        )
                        if sucesso:
                            st.session_state.gerenciador.salvar_dados()
                            clear_position_cache() # Limpa o cache de posições
                            st.success("Transferência realizada com sucesso!")
                            # st.rerun() # Removido: o formulário limpa e o estado da sessão atualiza naturalmente
                        else:
                            st.error("Falha ao realizar transferência. Verifique o saldo da conta de origem.")

# --- Histórico ---
elif pagina_selecionada == "Histórico":
    st.title("📜 Histórico de Transações")

    if not st.session_state.gerenciador.transacoes:
        st.info("Nenhuma transação registrada ainda.")
    else:
        # @st.cache_data para otimizar a criação do DataFrame de transações
        @st.cache_data(ttl=3600) # Cache por 1 hora
        def get_transactions_df(transacoes_list, contas_list):
            df = pd.DataFrame([t.para_dict() for t in transacoes_list])
            df["data"] = pd.to_datetime(df["data"])
            df = df.sort_values(by="data", ascending=False)
            mapa_nomes_contas = {c.id_conta: c.nome for c in contas_list}
            df["conta_nome"] = df["id_conta"].map(mapa_nomes_contas)
            return df

        df_transacoes = get_transactions_df(st.session_state.gerenciador.transacoes, st.session_state.gerenciador.contas)

        st.dataframe(df_transacoes.drop(columns=["id_conta", "id_transacao"]), width='stretch') # use_container_width=True -> width='stretch'

        st.markdown("---")
        st.subheader("Remover Transação")
        transacoes_para_remover = {t.id_transacao: f"{t.data.strftime('%d/%m/%Y')} - {t.descricao} ({t.valor:.2f})" for t in st.session_state.gerenciador.transacoes}
        if transacoes_para_remover:
            id_transacao_selecionada = st.selectbox("Selecione a transação para remover", options=list(transacoes_para_remover.keys()), format_func=lambda x: transacoes_para_remover[x])
            if st.button("🗑️ Confirmar Remoção"):
                if st.session_state.gerenciador.remover_transacao(id_transacao_selecionada):
                    st.session_state.gerenciador.salvar_dados()
                    clear_position_cache() # Limpa o cache de posições
                    st.success("Transação removida com sucesso!")
                    st.rerun() # Necessário para atualizar o selectbox e o dataframe de transações
                else:
                    st.error("Falha ao remover transação.")
        else:
            st.info("Nenhuma transação para remover.")


# --- Contas ---
elif pagina_selecionada == "Contas":
    st.title("🏦 Gerenciar Contas")

    # Adicionar Conta
    with st.expander("➕ Adicionar Nova Conta"):
        with st.form("add_account_form", clear_on_submit=True):
            st.write("Nova Conta")
            nome_conta = st.text_input("Nome da Conta")
            tipo_conta = st.radio("Tipo de Conta", ["Corrente", "Investimento"])
            logo_url = st.text_input("URL do Logo (opcional)")

            if tipo_conta == "Corrente":
                saldo_inicial = st.number_input("Saldo Inicial", value=0.0, format="%.2f")
                limite_cheque_especial = st.number_input("Limite Cheque Especial", value=0.0, format="%.2f")
            else:
                saldo_inicial = 0.0 # Não usado diretamente para Investimento
                limite_cheque_especial = 0.0 # Não usado para Investimento

            if st.form_submit_button("Criar Conta"):
                if not nome_conta:
                    st.error("O nome da conta é obrigatório.")
                else:
                    if tipo_conta == "Corrente":
                        nova_conta = ContaCorrente(nome_conta, saldo_inicial, limite_cheque_especial, logo_url)
                    else:
                        nova_conta = ContaInvestimento(nome_conta, logo_url, saldo_caixa=saldo_inicial) # saldo_caixa para inv
                    st.session_state.gerenciador.adicionar_conta(nova_conta)
                    st.session_state.gerenciador.salvar_dados()
                    clear_position_cache() # Limpa o cache de posições
                    st.success(f"Conta '{nome_conta}' criada com sucesso!")
                    st.rerun() # Necessário para atualizar a lista de contas e selectboxes
    st.markdown("---")

    # Listar e Gerenciar Contas Existentes
    st.subheader("Contas Existentes")
    if not st.session_state.gerenciador.contas:
        st.info("Nenhuma conta registrada ainda.")
    else:
        for conta in st.session_state.gerenciador.contas:
            with st.expander(f"⚙️ {conta.nome} ({'Corrente' if isinstance(conta, ContaCorrente) else 'Investimento'})"):
                st.write(f"**ID da Conta:** `{conta.id_conta}`")
                st.write(f"**Nome:** {conta.nome}")
                st.write(f"**Logo URL:** {conta.logo_url}")

                if isinstance(conta, ContaCorrente):
                    st.write(f"**Saldo:** {_format_currency(conta.saldo)}")
                    st.write(f"**Limite Cheque Especial:** {_format_currency(conta.limite_cheque_especial)}")

                    with st.form(f"edit_cc_form_{conta.id_conta}"):
                        st.subheader("Editar Conta Corrente")
                        novo_nome = st.text_input("Novo Nome", value=conta.nome, key=f"edit_cc_nome_{conta.id_conta}")
                        nova_logo_url = st.text_input("Nova URL do Logo", value=conta.logo_url, key=f"edit_cc_logo_{conta.id_conta}")
                        novo_limite = st.number_input("Novo Limite Cheque Especial", value=conta.limite_cheque_especial, format="%.2f", key=f"edit_cc_limite_{conta.id_conta}")
                        if st.form_submit_button("Salvar Alterações", key=f"save_cc_{conta.id_conta}"):
                            conta.editar_nome(novo_nome)
                            conta.editar_logo_url(nova_logo_url)
                            conta.editar_limite(novo_limite)
                            st.session_state.gerenciador.salvar_dados()
                            st.success("Conta Corrente atualizada com sucesso!")
                            st.rerun() # Necessário para atualizar o título do expander e selectboxes
                
                elif isinstance(conta, ContaInvestimento):
                    # Usar a função de cache para obter a posição
                    posicao = get_cached_position(conta.id_conta)
                    st.write(f"**Saldo em Caixa:** {_format_currency(posicao['saldo_caixa'])}")
                    st.write(f"**Valor Total em Ativos:** {_format_currency(posicao['total_valor_atual_ativos'])}")
                    st.write(f"**Patrimônio Atualizado:** {_format_currency(posicao['patrimonio_atualizado'])}")

                    with st.form(f"edit_ci_form_{conta.id_conta}"):
                        st.subheader("Editar Conta Investimento")
                        novo_nome = st.text_input("Novo Nome", value=conta.nome, key=f"edit_ci_nome_{conta.id_conta}")
                        nova_logo_url = st.text_input("Nova URL do Logo", value=conta.logo_url, key=f"edit_ci_logo_{conta.id_conta}")
                        if st.form_submit_button("Salvar Alterações", key=f"save_ci_{conta.id_conta}"):
                            conta.editar_nome(novo_nome)
                            conta.editar_logo_url(nova_logo_url)
                            st.session_state.gerenciador.salvar_dados()
                            st.success("Conta Investimento atualizada com sucesso!")
                            st.rerun() # Necessário para atualizar o título do expander e selectboxes

                    st.subheader("Cotações e Posição Atual")
                    if st.button(f"🔄 Atualizar Cotações ({conta.nome})", key=f"update_quotes_{conta.id_conta}"):
                        # Força o recálculo da posição, limpando o cache para esta conta
                        if conta.id_conta in st.session_state.cache_posicoes:
                            del st.session_state.cache_posicoes[conta.id_conta]
                        # Recalcula e exibe (a próxima chamada a get_cached_position fará o cálculo)
                        st.success("Cotações atualizadas!")
                        # st.rerun() # Removido: a exibição de dados já está ligada ao estado da sessão

                    if posicao["ativos"]:
                        # @st.cache_data para otimizar a criação do DataFrame de ativos
                        @st.cache_data(ttl=3600) # Cache por 1 hora
                        def get_ativos_df(ativos_data):
                            df = pd.DataFrame(ativos_data)
                            df = df.rename(columns={
                                "ticker": "Ticker",
                                "tipo": "Tipo",
                                "quantidade": "Quantidade",
                                "preco_medio": "Preço Médio",
                                "preco_atual": "Preço Atual",
                                "valor_atual": "Valor Atual",
                                "pl": "P/L (R$)",
                                "pl_pct": "P/L (%)",
                            })
                            df["Quantidade"] = df["Quantidade"].apply(_format_quantity)
                            df["Preço Médio"] = df["Preço Médio"].apply(_format_currency)
                            df["Preço Atual"] = df["Preço Atual"].apply(_format_currency)
                            df["Valor Atual"] = df["Valor Atual"].apply(_format_currency)
                            df["P/L (R$)"] = df["P/L (R$)"].apply(_format_currency)
                            df["P/L (%)"] = df["P/L (%)"].apply(_format_percentage)
                            return df

                        df_ativos = get_ativos_df(posicao["ativos"])

                        st.dataframe(
                            df_ativos.style.map(_cor_pl, subset=["P/L (R$)", "P/L (%)"]),
                            width='stretch' # use_container_width=True -> width='stretch'
                        )
                    else:
                        st.info("Nenhum ativo nesta conta.")

                st.markdown("---")
                if st.button(f"🗑️ Remover Conta ({conta.nome})", key=f"remove_account_{conta.id_conta}"):
                    if st.session_state.gerenciador.remover_conta(conta.id_conta):
                        st.session_state.gerenciador.salvar_dados()
                        clear_position_cache() # Limpa o cache de posições
                        st.success(f"Conta '{conta.nome}' removida com sucesso!")
                        st.rerun() # Necessário para atualizar a lista de contas e selectboxes

# --- Cartões ---
elif pagina_selecionada == "Cartões":
    st.title("💳 Gerenciar Cartões de Crédito")

    # Adicionar Cartão
    with st.expander("➕ Adicionar Novo Cartão de Crédito"):
        with st.form("add_card_form", clear_on_submit=True):
            st.write("Novo Cartão")
            nome_cartao = st.text_input("Nome do Cartão (ex: Nubank, Inter)")
            logo_url_cartao = st.text_input("URL do Logo (opcional)", key="card_logo_url")
            dia_fechamento = st.number_input("Dia de Fechamento da Fatura", min_value=1, max_value=31, value=28)
            dia_vencimento = st.number_input("Dia de Vencimento da Fatura", min_value=1, max_value=31, value=10)

            if st.form_submit_button("Criar Cartão"):
                if not nome_cartao:
                    st.error("O nome do cartão é obrigatório.")
                else:
                    novo_cartao = CartaoCredito(nome_cartao, logo_url_cartao, dia_fechamento, dia_vencimento)
                    st.session_state.gerenciador.adicionar_cartao_credito(novo_cartao)
                    st.session_state.gerenciador.salvar_dados()
                    st.success(f"Cartão '{nome_cartao}' criado com sucesso!")
                    st.rerun() # Necessário para atualizar a lista de cartões e selectboxes

    st.markdown("---")

    # Listar e Gerenciar Cartões Existentes
    st.subheader("Cartões Existentes")
    if not st.session_state.gerenciador.cartoes_credito:
        st.info("Nenhum cartão de crédito registrado ainda.")
    else:
        for cartao in st.session_state.gerenciador.cartoes_credito:
            with st.expander(f"⚙️ {cartao.nome}"):
                st.write(f"**ID do Cartão:** `{cartao.id_cartao}`")
                st.write(f"**Nome:** {cartao.nome}")
                st.write(f"**Logo URL:** {cartao.logo_url}")
                st.write(f"**Dia de Fechamento:** {cartao.dia_fechamento}")
                st.write(f"**Dia de Vencimento:** {cartao.dia_vencimento}")

                with st.form(f"edit_card_form_{cartao.id_cartao}"):
                    st.subheader("Editar Cartão de Crédito")
                    novo_nome_cartao = st.text_input("Novo Nome", value=cartao.nome, key=f"edit_card_nome_{cartao.id_cartao}")
                    nova_logo_url_cartao = st.text_input("Nova URL do Logo", value=cartao.logo_url, key=f"edit_card_logo_{cartao.id_cartao}")
                    novo_dia_fechamento = st.number_input("Novo Dia de Fechamento", min_value=1, max_value=31, value=cartao.dia_fechamento, key=f"edit_card_fechamento_{cartao.id_cartao}")
                    novo_dia_vencimento = st.number_input("Novo Dia de Vencimento", min_value=1, max_value=31, value=cartao.dia_vencimento, key=f"edit_card_vencimento_{cartao.id_cartao}")

                    if st.form_submit_button("Salvar Alterações", key=f"save_card_{cartao.id_cartao}"):
                        cartao.editar_nome(novo_nome_cartao)
                        cartao.editar_logo_url(nova_logo_url_cartao)
                        cartao.dia_fechamento = novo_dia_fechamento
                        cartao.dia_vencimento = novo_dia_vencimento
                        st.session_state.gerenciador.salvar_dados()
                        st.success("Cartão de crédito atualizado com sucesso!")
                        st.rerun() # Necessário para atualizar o título do expander e selectboxes

                st.markdown("---")
                st.subheader("Faturas")

                # Navegação entre ciclos de fatura
                # @st.cache_data para otimizar a listagem de ciclos
                @st.cache_data(ttl=3600) # Cache por 1 hora
                def get_ciclos_navegacao(gerenciador_obj, card_id):
                    return gerenciador_obj.listar_ciclos_navegacao(card_id)

                ciclos_navegacao = get_ciclos_navegacao(st.session_state.gerenciador, cartao.id_cartao)

                if ciclos_navegacao:
                    ciclos_formatados = [f"{calendar.month_name[mes]} de {ano}" for ano, mes in ciclos_navegacao]
                    ciclo_selecionado_idx = st.selectbox(
                        "Selecione o ciclo da fatura",
                        options=range(len(ciclos_navegacao)),
                        format_func=lambda x: ciclos_formatados[x],
                        key=f"ciclo_fatura_select_{cartao.id_cartao}"
                    )
                    ano_fatura, mes_fatura = ciclos_navegacao[ciclo_selecionado_idx]

                    # Exibir compras do ciclo
                    # @st.cache_data para otimizar a obtenção de lançamentos
                    @st.cache_data(ttl=3600) # Cache por 1 hora
                    def get_compras_ciclo_df(gerenciador_obj, card_id, ano, mes):
                        compras = gerenciador_obj.obter_lancamentos_do_ciclo(card_id, ano, mes)
                        if compras:
                            df = pd.DataFrame([c.para_dict() for c in compras])
                            df["data_compra"] = pd.to_datetime(df["data_compra"])
                            df["data_compra_real"] = pd.to_datetime(df["data_compra_real"])
                            df = df.sort_values(by="data_compra_real", ascending=False)
                            return df, sum(c.valor for c in compras)
                        return pd.DataFrame(), 0.0

                    df_compras_ciclo, total_ciclo = get_compras_ciclo_df(st.session_state.gerenciador, cartao.id_cartao, ano_fatura, mes_fatura)

                    if not df_compras_ciclo.empty:
                        st.dataframe(df_compras_ciclo.drop(columns=["id_cartao", "id_compra", "id_compra_original", "id_fatura"]), width='stretch') # use_container_width=True -> width='stretch'
                        st.write(f"**Total do Ciclo:** {_format_currency(total_ciclo)}")

                        # Fechar Fatura
                        if st.button(f"🔒 Fechar Fatura ({cartao.nome} - {calendar.month_name[mes_fatura]}/{ano_fatura})", key=f"fechar_fatura_{cartao.id_cartao}_{ano_fatura}_{mes_fatura}"):
                            data_fechamento_fatura = date.today() # Pode ser ajustado
                            data_vencimento_fatura = date(ano_fatura, mes_fatura, cartao.dia_vencimento) # Pode ser ajustado
                            fatura_fechada = st.session_state.gerenciador.fechar_fatura(
                                id_cartao=cartao.id_cartao,
                                data_fechamento_real=data_fechamento_fatura,
                                data_vencimento_real=data_vencimento_fatura
                            )
                            if fatura_fechada:
                                st.session_state.gerenciador.salvar_dados()
                                st.success(f"Fatura de {calendar.month_name[mes_fatura]}/{ano_fatura} fechada com sucesso!")
                                st.rerun() # Necessário para atualizar a lista de ciclos e faturas
                            else:
                                st.error("Não foi possível fechar a fatura. Verifique se há compras no ciclo.")
                    else:
                        st.info("Nenhuma compra neste ciclo.")
                else:
                    st.info("Nenhum ciclo de fatura aberto para este cartão.")

                st.markdown("---")
                st.subheader("Faturas Fechadas e Pagas")
                # @st.cache_data para otimizar a listagem de faturas
                @st.cache_data(ttl=3600) # Cache por 1 hora
                def get_faturas_df(faturas_list, card_id):
                    faturas = [f for f in faturas_list if f.id_cartao == card_id]
                    if faturas:
                        df = pd.DataFrame([f.para_dict() for f in faturas])
                        df["data_fechamento"] = pd.to_datetime(df["data_fechamento"])
                        df["data_vencimento"] = pd.to_datetime(df["data_vencimento"])
                        df = df.sort_values(by="data_vencimento", ascending=False)
                        return df
                    return pd.DataFrame()

                df_faturas = get_faturas_df(st.session_state.gerenciador.faturas, cartao.id_cartao)

                if not df_faturas.empty:
                    st.dataframe(df_faturas.drop(columns=["id_cartao", "id_fatura"]), width='stretch') # use_container_width=True -> width='stretch'

                    # Pagar Fatura
                    faturas_abertas = [f for f in st.session_state.gerenciador.faturas if f.id_cartao == cartao.id_cartao and f.status == "Fechada"]
                    if faturas_abertas:
                        mapa_faturas_abertas = {f.id_fatura: f"Fatura {f.data_vencimento.strftime('%d/%m/%Y')} - {_format_currency(f.valor_total)}" for f in faturas_abertas}
                        id_fatura_pagar = st.selectbox("Selecione a fatura para pagar", options=list(mapa_faturas_abertas.keys()), format_func=lambda x: mapa_faturas_abertas[x], key=f"pagar_fatura_select_{cartao.id_cartao}")
                        
                        contas_correntes = [c for c in st.session_state.gerenciador.contas if isinstance(c, ContaCorrente)]
                        if contas_correntes:
                            mapa_contas_correntes = {c.id_conta: c.nome for c in contas_correntes}
                            id_conta_pagamento = st.selectbox("Pagar com a conta", options=list(mapa_contas_correntes.keys()), format_func=lambda x: mapa_contas_correntes[x], key=f"pagar_fatura_conta_{cartao.id_cartao}")
                            data_pagamento = st.date_input("Data do Pagamento", value=datetime.today(), format="DD/MM/YYYY", key=f"pagar_fatura_data_{cartao.id_cartao}")

                            if st.button(f"✅ Pagar Fatura Selecionada", key=f"pagar_fatura_btn_{cartao.id_cartao}"):
                                if st.session_state.gerenciador.pagar_fatura(id_fatura_pagar, id_conta_pagamento, data_pagamento):
                                    st.session_state.gerenciador.salvar_dados()
                                    st.success("Fatura paga com sucesso!")
                                    st.rerun() # Necessário para atualizar o status da fatura e o saldo da conta
                                else:
                                    st.error("Falha ao pagar fatura. Verifique o saldo da conta ou se a fatura já foi paga.")
                        else:
                            st.info("Crie uma conta corrente para pagar faturas.")
                    else:
                        st.info("Nenhuma fatura aberta para pagar.")
                else:
                    st.info("Nenhuma fatura fechada para este cartão.")

                st.markdown("---")
                if st.button(f"🗑️ Remover Cartão ({cartao.nome})", key=f"remove_card_{cartao.id_cartao}"):
                    if st.session_state.gerenciador.remover_cartao_credito(cartao.id_cartao):
                        st.session_state.gerenciador.salvar_dados()
                        st.success(f"Cartão '{cartao.nome}' removido com sucesso!")
                        st.rerun() # Necessário para atualizar a lista de cartões e selectboxes

# --- Configurações ---
elif pagina_selecionada == "Configurações":
    st.title("⚙️ Configurações")

    st.subheader("Categorias de Transação")
    st.write("Gerencie as categorias disponíveis para suas transações.")

    col_add_cat, col_rem_cat = st.columns(2)
    with col_add_cat:
        nova_categoria = st.text_input("Adicionar nova categoria")
        if st.button("➕ Adicionar Categoria"):
            if nova_categoria:
                st.session_state.gerenciador.adicionar_categoria(nova_categoria)
                st.session_state.gerenciador.salvar_dados()
                st.success(f"Categoria '{nova_categoria}' adicionada.")
                st.rerun() # Necessário para atualizar a lista de categorias em todos os selectboxes
            else:
                st.error("O nome da categoria não pode ser vazio.")

    with col_rem_cat:
        if st.session_state.gerenciador.categorias:
            categoria_remover = st.selectbox("Remover categoria existente", st.session_state.gerenciador.categorias)
            if st.button("🗑️ Remover Categoria"):
                st.session_state.gerenciador.remover_categoria(categoria_remover)
                st.session_state.gerenciador.salvar_dados()
                st.success(f"Categoria '{categoria_remover}' removida.")
                st.rerun() # Necessário para atualizar a lista de categorias em todos os selectboxes
        else:
            st.info("Nenhuma categoria para remover.")

    st.markdown("---")
    st.subheader("Backup e Restauração")
    st.info("Funcionalidade de backup e restauração de dados pode ser implementada aqui.")

# --- Final ---
st.sidebar.markdown("---")
st.sidebar.info("Desenvolvido com Streamlit")
