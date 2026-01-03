import streamlit as st
import pandas as pd
from datetime import datetime, date
from collections import defaultdict

from sistema_financeiro import (
    GerenciadorContas,
    ContaCorrente,
    ContaInvestimento,
    Ativo,
    CartaoCredito,
)

def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.set_page_config(page_title="BRUST Personal Finance", page_icon="💰", layout="wide")

if "gerenciador" not in st.session_state:
    st.session_state.gerenciador = GerenciadorContas("dados_v15.json")

for key, default in [
    ("transacao_para_excluir", None),
    ("conta_para_excluir", None),
    ("compra_para_excluir", None),
    ("fatura_para_pagar", None),
    ("fatura_para_reabrir", None),
    ("cartao_para_excluir", None),
    ("categoria_para_excluir", None),
   ]:
    if key not in st.session_state:
        st.session_state[key] = default

st.title("BRUST Personal Finance 💰")

tab_dashboard, tab_transacoes, tab_contas, tab_cartoes, tab_config, tab_gerenciar = st.tabs(
    ["📊 Dashboard", "📈 Histórico", "🏦 Contas", "💳 Cartões", "⚙️ Configurações", "📦 Gerenciar Contas"]
)

# --- DASHBOARD ---
with tab_dashboard:
    col1, col2 = st.columns([1, 1])

    with col2:
        st.header("Ações Rápidas")

        # --------------------------
        # Comprar Ativo (por ID, exibindo apenas nome)
        # --------------------------
        with st.expander("📈 Comprar Ativo"):
            contas_investimento = [
                c for c in st.session_state.gerenciador.obter_contas_ativas() if isinstance(c, ContaInvestimento)
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
                            sucesso = st.session_state.gerenciador.obter_contas_ativas().comprar_ativo(
                                id_conta_destino=conta_destino_id,
                                ticker=ticker,
                                quantidade=quantidade,
                                preco_unitario=preco_unitario,
                                tipo_ativo=tipo_ativo,
                                data_compra=data_compra,
                            )
                            if sucesso:
                                st.session_state.gerenciador.obter_contas_ativas().salvar_dados()
                                st.success(f"Compra de {ticker} registrada!")
                                st.rerun()
                            else:
                                st.error("Falha na compra. Verifique o saldo em caixa da corretora.")


        # Vender Ativo
        with st.expander("📊 Vender Ativo", expanded=False):
            contas_inv_venda = [c for c in st.session_state.gerenciador.obter_contas_ativas() if isinstance(c, ContaInvestimento)]
            
            if not contas_inv_venda:
                st.info("Crie uma Conta de Investimento para vender ativos.")
            else:
                conta_venda_sel = st.selectbox("Conta de Investimento", contas_inv_venda, format_func=lambda x: x.nome, key="conta_venda_sel")
                
                # Lista os ativos disponíveis para venda
                ativos_disponiveis = conta_venda_sel.ativos if conta_venda_sel.ativos else []
                
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
                        sucesso, mensagem = st.session_state.gerenciador.obter_contas_ativas().vender_ativo(
                            id_conta=conta_venda_sel.id_conta,
                            ticker=ticker_venda.ticker,
                            quantidade=qtd_venda,
                            preco_venda=preco_venda,
                            data_venda=data_venda.strftime("%Y-%m-%d"),
                            observacao=obs_venda
                        )
                        if sucesso:
                            st.session_state.gerenciador.obter_contas_ativas().salvar_dados()
                            st.success(mensagem)
                            st.rerun()
                        else:
                            st.error(mensagem)

         # --------------------------
        # Registrar Receita/Despesa (por ID, exibindo apenas nome)
        # --------------------------
        with st.expander("💸 Registrar Receita/Despesa", expanded=True):
            contas_correntes = [
                c for c in st.session_state.gerenciador.obter_contas_ativas() if isinstance(c, ContaCorrente)
            ]
            if not contas_correntes:
                st.warning("Crie uma Conta Corrente para registrar receitas/despesas.")
            else:
                mapa_cc = {c.id_conta: c for c in contas_correntes}
                ids_cc = list(mapa_cc.keys())
                with st.form("new_transaction_form", clear_on_submit=True):
                    tipo_transacao = st.selectbox("Tipo", ["Receita", "Despesa"])
                    conta_selecionada_id = st.selectbox(
                        "Conta Corrente",
                        options=ids_cc,
                        format_func=lambda cid: mapa_cc[cid].nome,
                        key="tx_conta_corrente_id"
                    )
                    descricao = st.text_input("Descrição")
                    categoria = st.selectbox("Categoria", st.session_state.gerenciador.categorias)
                    valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
                    data_transacao = st.date_input("Data", value=datetime.today(), format="DD/MM/YYYY")
                    observacao = st.text_area("Observações (Opcional)")
                    tag = st.text_input("TAG (Opcional)", placeholder="Ex: Viagem Matinhos 2025", help="Use TAGs para agrupar despesas relacionadas")
                    

                    if st.form_submit_button("Registrar"):
                        if not all([descricao, categoria]):
                            st.error("Descrição e Categoria são obrigatórios.")
                        else:
                            sucesso = st.session_state.gerenciador.registrar_transacao(
                                id_conta=conta_selecionada_id,
                                descricao=descricao,
                                valor=valor,
                                tipo=tipo_transacao,
                                data_transacao=data_transacao,
                                categoria=categoria,
                                observacao=observacao,
                                tag=tag,
                            )
                            if sucesso:
                                st.session_state.gerenciador.salvar_dados()
                                st.success("Transação registrada!")
                                st.rerun()
                            else:
                                st.error("Falha ao registrar. Saldo insuficiente?")

            # --------------------------
            # Resumo (com valor atual de investimentos)
            # --------------------------
            st.header("Resumo ")
            todas_as_contas = st.session_state.gerenciador.obter_contas_ativas()
            if todas_as_contas:
                saldos_agrupados = defaultdict(float)
                patrimonio_total = 0.0
            
                for conta in todas_as_contas:
                    if isinstance(conta, ContaCorrente):
                        # Contas correntes: usa saldo direto
                        saldos_agrupados["Contas Correntes"] += float(conta.saldo or 0.0)
                        patrimonio_total += float(conta.saldo or 0.0)
            
                    elif isinstance(conta, ContaInvestimento):
                        # Investimentos: usa posição atual (inclui rendimentos)
                        pos = st.session_state.gerenciador.calcular_posicao_conta_investimento(conta.id_conta)
            
                        saldo_caixa = float(pos.get("saldo_caixa", 0.0) or 0.0)
                        total_valor_atual_ativos = float(pos.get("total_valor_atual_ativos", 0.0) or 0.0)
                        patrimonio_atualizado = float(pos.get("patrimonio_atualizado", saldo_caixa + total_valor_atual_ativos) or 0.0)
            
                        # Agrupa caixa das corretoras
                        saldos_agrupados["Caixa Corretoras"] += saldo_caixa
            
                        # Agrupa por tipo de ativo com VALOR ATUAL
                        for item in pos.get("ativos", []):
                            tipo = item.get("tipo", "Ativos")
                            valor_atual = float(item.get("valor_atual", 0.0) or 0.0)
                            saldos_agrupados[tipo] += valor_atual
            
                        # Patrimônio total usa o consolidado atualizado da conta de investimento
                        patrimonio_total += patrimonio_atualizado
            
                st.subheader("Patrimônio por Categoria")
                for categoria, saldo in saldos_agrupados.items():
                    st.metric(label=categoria, value=formatar_moeda(saldo))
            
                st.divider()
                st.metric(label="Patrimônio Total", value=formatar_moeda(patrimonio_total))
            else:
                st.metric(label="Patrimônio Total", value="R$ 0,00")



    with col1:
        st.header("Realizar Transferência")
        todas_as_contas = st.session_state.gerenciador.obter_contas_ativas()

        if len(todas_as_contas) >= 2:
            # Mapa por ID, exibindo apenas nome
            mapa_todas = {c.id_conta: c for c in todas_as_contas}
            ids_todas = list(mapa_todas.keys())

            with st.form("transfer_form", clear_on_submit=True):
                # Seleção por ID (valor único), mostrando apenas nome
                conta_origem_id = st.selectbox(
                    "De:",
                    options=ids_todas,
                    format_func=lambda cid: mapa_todas[cid].nome,
                    key="transfer_origem_id"
                )

                ids_destino = [cid for cid in ids_todas if cid != conta_origem_id]
                conta_destino_id = st.selectbox(
                    "Para:",
                    options=ids_destino,
                    format_func=lambda cid: mapa_todas[cid].nome,
                    key="transfer_destino_id"
                )

                valor_transferencia = st.number_input("Valor (R$)", min_value=0.01, format="%.2f", key="transfer_valor")

                # Validação específica de saldo_caixa quando origem é ContaInvestimento
                conta_origem_obj = mapa_todas[conta_origem_id]
                if isinstance(conta_origem_obj, ContaInvestimento):
                    saldo_caixa_origem = float(conta_origem_obj.saldo_caixa)
                    if valor_transferencia > saldo_caixa_origem:
                        st.warning(
                            f"Saldo em caixa insuficiente na corretora de origem. Caixa atual: "
                            f"{formatar_moeda(saldo_caixa_origem)}. "
                            f"Para transferir, é necessário ter saldo em caixa (não apenas em ativos)."
                        )

                if st.form_submit_button("Confirmar Transferência", use_container_width=True):
                    ok = st.session_state.gerenciador.realizar_transferencia(
                        conta_origem_id, conta_destino_id, valor_transferencia
                    )
                    if ok:
                        st.session_state.gerenciador.salvar_dados()
                        st.success("Transferência realizada!")
                        st.rerun()
                    else:
                        if isinstance(conta_origem_obj, ContaCorrente):
                            st.error("Falha na transferência. Saldo insuficiente na conta corrente (considerando o limite)?")
                        else:
                            st.error("Falha na transferência. Saldo em caixa insuficiente na conta de investimento de origem.")
        else:
            st.info("Adicione pelo menos duas contas para realizar transferências.")


# --- HISTÓRICO ---
# --- HISTÓRICO ---
with tab_transacoes:
    st.header("Histórico de Todas as Transações")

    
    # === DIAGNÓSTICO FORÇADO ===
    st.error("=" * 50)
    st.error("DIAGNÓSTICO INICIADO")
    st.error("=" * 50)
    
    try:
        total = len(st.session_state.gerenciador.transacoes)
        st.success(f"Total de transações: {total}")
        
        # Verifica se transacoes_filtradas existe
        if 'transacoes_filtradas' in locals():
            st.info(f"Transações filtradas: {len(transacoes_filtradas)}")
        else:
            st.warning("Variável 'transacoes_filtradas' ainda não existe aqui")
        
    except Exception as e:
        st.error(f"ERRO: {e}")
    
    st.error("=" * 50)
    st.divider()
    # === FIM DO DIAGNÓSTICO ===



    
    # === DIAGNÓSTICO TEMPORÁRIO ===
    st.error("🔍 INÍCIO DO DIAGNÓSTICO")
    st.write(f"**Total de transações no sistema:** {len(st.session_state.gerenciador.transacoes)}")
    
    if st.session_state.gerenciador.transacoes:
        st.success("✅ Há transações no sistema!")
        st.write("**Primeiras 3 transações:**")
        for i, t in enumerate(st.session_state.gerenciador.transacoes[:3]):
            st.write(f"{i+1}. Data: {t.data} | Descrição: {t.descricao} | Valor: R$ {t.valor:.2f}")
    else:
        st.error("❌ NÃO HÁ TRANSAÇÕES NO SISTEMA!")
    
    st.error("🔍 FIM DO DIAGNÓSTICO")
    st.divider()
    # === FIM DO DIAGNÓSTICO ===
    
    # === FILTROS ===
    from datetime import timedelta
    from dateutil.relativedelta import relativedelta
    
    st.write("### 🔍 Filtros")
    
    col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
    
    with col_filtro1:
        periodo = st.selectbox(
            "📅 Período:",
            ["Últimos 30 dias", "Últimos 3 meses", "Últimos 6 meses", 
             "Este ano", "Ano passado", "Período Personalizado", "Tudo"],
            index=1,
            key="filtro_periodo_transacoes"
        )
        
        # Se período personalizado, mostra seletor de datas
        if periodo == "Período Personalizado":
            col_data1, col_data2 = st.columns(2)
            with col_data1:
                data_inicio_custom = st.date_input(
                    "De:",
                    value=date.today() - timedelta(days=90),
                    format="DD/MM/YYYY",
                    key="data_inicio_hist"
                )
            with col_data2:
                data_fim_custom = st.date_input(
                    "Até:",
                    value=date.today(),
                    format="DD/MM/YYYY",
                    key="data_fim_hist"
                )
        
        # Filtro por conta
        contas_opcoes = ["Todas"] + [c.nome for c in st.session_state.gerenciador.obter_contas_ativas()]
        conta_filtro = st.selectbox(
            "🏦 Conta:",
            options=contas_opcoes,
            index=0,
            key="filtro_conta_hist"
        )
    
    with col_filtro2:
        # Filtro por categoria
        categorias_transacoes = set(t.categoria for t in st.session_state.gerenciador.transacoes if t.categoria)
        categorias_opcoes = ["Todas"] + sorted(list(categorias_transacoes))
        categoria_filtro = st.selectbox(
            "📂 Categoria:",
            options=categorias_opcoes,
            index=0,
            key="filtro_categoria_hist"
        )
        
        # Filtro por TAG
        tags_transacoes = set(getattr(t, 'tag', '') for t in st.session_state.gerenciador.transacoes if getattr(t, 'tag', ''))
        tags_opcoes = ["Todas"] + sorted(list(tags_transacoes))
        tag_filtro = st.selectbox(
            "🏷️ TAG:",
            options=tags_opcoes,
            index=0,
            key="filtro_tag_hist"
        )
    
    with col_filtro3:
        # Filtro por descrição
        descricao_filtro = st.text_input(
            "🔎 Buscar descrição:",
            placeholder="Digite para filtrar...",
            help="Busca parcial (não diferencia maiúsculas/minúsculas)",
            key="filtro_descricao_hist"
        )
        
        # Filtro por tipo
        tipo_filtro = st.selectbox(
            "💰 Tipo:",
            options=["Todos", "Receita", "Despesa"],
            index=0,
            key="filtro_tipo_hist"
        )
    
    st.divider()

    # === FILTRO DE TRANSAÇÕES INFORMATIVAS ===
    mostrar_compras_cartao = st.checkbox(
    "💳 Mostrar compras de cartão no histórico",
    value=True,
    help="Exibe as compras individuais de cartão de crédito (transações informativas que não afetam o saldo)",
    key="filtro_mostrar_compras_cartao"
)

st.divider()
    
    # === CALCULAR PERÍODO ===
    hoje = date.today()
    
    if periodo == "Últimos 30 dias":
        data_inicio = hoje - timedelta(days=30)
        data_fim = hoje
    elif periodo == "Últimos 3 meses":
        data_inicio = hoje - relativedelta(months=3)
        data_fim = hoje
    elif periodo == "Últimos 6 meses":
        data_inicio = hoje - relativedelta(months=6)
        data_fim = hoje
    elif periodo == "Este ano":
        data_inicio = date(hoje.year, 1, 1)
        data_fim = hoje
    elif periodo == "Ano passado":
        data_inicio = date(hoje.year - 1, 1, 1)
        data_fim = date(hoje.year - 1, 12, 31)
    elif periodo == "Período Personalizado":
        data_inicio = data_inicio_custom
        data_fim = data_fim_custom
    else:  # Tudo
        data_inicio = None
        data_fim = None
        
    # === APLICAR FILTROS ===
    transacoes_filtradas = st.session_state.gerenciador.transacoes.copy()
    
    # Filtro de período
    if data_inicio and data_fim:
        transacoes_filtradas = [
            t for t in transacoes_filtradas
            if data_inicio <= t.data <= data_fim
        ]
    
    # Filtro por conta
    if conta_filtro != "Todas":
        conta_selecionada = next((c for c in st.session_state.gerenciador.obter_contas_ativas() if c.nome == conta_filtro), None)
        if conta_selecionada:
            transacoes_filtradas = [
                t for t in transacoes_filtradas
                if t.id_conta == conta_selecionada.id_conta
            ]
    
    # Filtro por categoria
    if categoria_filtro != "Todas":
        transacoes_filtradas = [
            t for t in transacoes_filtradas
            if t.categoria == categoria_filtro
        ]
    
    # Filtro por TAG
    if tag_filtro != "Todas":
        transacoes_filtradas = [
            t for t in transacoes_filtradas
            if getattr(t, 'tag', '') == tag_filtro
        ]
    
    # Filtro por descrição
    if descricao_filtro:
        transacoes_filtradas = [
            t for t in transacoes_filtradas
            if descricao_filtro.lower() in t.descricao.lower()
        ]
    
    # Filtro por tipo
    if tipo_filtro != "Todos":
        transacoes_filtradas = [
            t for t in transacoes_filtradas
            if t.tipo == tipo_filtro
        ]

    # Filtro de compras de cartão (transações informativas)
    if not mostrar_compras_cartao:
        transacoes_filtradas = [
            t for t in transacoes_filtradas
            if not getattr(t, 'informativa', False)
        ]





    # Filtro de compras de cartão (transações informativas)
    if not mostrar_compras_cartao:
        transacoes_filtradas = [
            t for t in transacoes_filtradas
            if not getattr(t, 'informativa', False)
        ]
    
    # === DIAGNÓSTICO DETALHADO DOS FILTROS ===
    st.error("🔍 DIAGNÓSTICO DETALHADO")
    
    # Total inicial
    total_inicial = len(st.session_state.gerenciador.transacoes)
    st.write(f"**1. Total inicial de transações:** {total_inicial}")
    
    # Após filtro de período
    transacoes_teste = st.session_state.gerenciador.transacoes.copy()
    if data_inicio and data_fim:
        transacoes_teste = [t for t in transacoes_teste if data_inicio <= t.data <= data_fim]
    st.write(f"**2. Após filtro de período ({periodo}):** {len(transacoes_teste)}")
    st.write(f"   - Data início: {data_inicio if data_inicio else 'Sem filtro'}")
    st.write(f"   - Data fim: {data_fim if data_fim else 'Sem filtro'}")
    
    # Mostra algumas datas de transações para comparar
    if total_inicial > 0:
        datas_exemplo = sorted([t.data for t in st.session_state.gerenciador.transacoes])
        st.write(f"   - Data mais antiga no sistema: {datas_exemplo[0]}")
        st.write(f"   - Data mais recente no sistema: {datas_exemplo[-1]}")
    
    # Após filtro de conta
    if conta_filtro != "Todas":
        conta_selecionada = next((c for c in st.session_state.gerenciador.obter_contas_ativas() if c.nome == conta_filtro), None)
        if conta_selecionada:
            transacoes_teste = [t for t in transacoes_teste if t.id_conta == conta_selecionada.id_conta]
    st.write(f"**3. Após filtro de conta ({conta_filtro}):** {len(transacoes_teste)}")
    
    # Após filtro de categoria
    if categoria_filtro != "Todas":
        transacoes_teste = [t for t in transacoes_teste if t.categoria == categoria_filtro]
    st.write(f"**4. Após filtro de categoria ({categoria_filtro}):** {len(transacoes_teste)}")
    
    # Após filtro de TAG
    if tag_filtro != "Todas":
        transacoes_teste = [t for t in transacoes_teste if getattr(t, 'tag', '') == tag_filtro]
    st.write(f"**5. Após filtro de TAG ({tag_filtro}):** {len(transacoes_teste)}")
    
    # Após filtro de descrição
    if descricao_filtro:
        transacoes_teste = [t for t in transacoes_teste if descricao_filtro.lower() in t.descricao.lower()]
    st.write(f"**6. Após filtro de descrição ('{descricao_filtro}'):** {len(transacoes_teste)}")
    
    # Após filtro de tipo
    if tipo_filtro != "Todos":
        transacoes_teste = [t for t in transacoes_teste if t.tipo == tipo_filtro]
    st.write(f"**7. Após filtro de tipo ({tipo_filtro}):** {len(transacoes_teste)}")
    
    # Após filtro de compras de cartão
    if not mostrar_compras_cartao:
        transacoes_teste = [t for t in transacoes_teste if not getattr(t, 'informativa', False)]
    st.write(f"**8. Após filtro de compras de cartão (mostrar={mostrar_compras_cartao}):** {len(transacoes_teste)}")
    
    st.write(f"**RESULTADO FINAL:** {len(transacoes_filtradas)} transações")
    
    st.error("🔍 FIM DO DIAGNÓSTICO DETALHADO")
    st.divider()
    # === FIM DO DIAGNÓSTICO ===
    
    
    
    
    
    
    

    

    # === ESTATÍSTICAS ===
    # Exclui transações informativas do cálculo (compras de cartão não afetam saldo)
    transacoes_para_calculo = [t for t in transacoes_filtradas if not getattr(t, 'informativa', False)]
    
    total_receitas = sum(t.valor for t in transacoes_para_calculo if t.tipo == "Receita")
    total_despesas = sum(t.valor for t in transacoes_para_calculo if t.tipo == "Despesa")
    saldo_periodo = total_receitas - total_despesas
    
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        st.metric("📊 Transações", len(transacoes_filtradas))
    
    with col_stat2:
        st.metric("💰 Receitas", formatar_moeda(total_receitas))
    
    with col_stat3:
        st.metric("💸 Despesas", formatar_moeda(total_despesas))
    
    with col_stat4:
        delta_color = "normal" if saldo_periodo >= 0 else "inverse"
        st.metric("📈 Saldo Período", formatar_moeda(saldo_periodo), delta_color=delta_color)
    
    st.divider()













    # === DIAGNÓSTICO TEMPORÁRIO ===
    st.write("---")
    st.write("### 🔍 DIAGNÓSTICO DE DEPURAÇÃO")
    
    st.write(f"**Total de transações no sistema:** {len(st.session_state.gerenciador.transacoes)}")
    st.write(f"**Transações após todos os filtros:** {len(transacoes_filtradas)}")
    st.write(f"**Checkbox 'Mostrar compras de cartão' está:** {'✅ Marcado' if mostrar_compras_cartao else '❌ Desmarcado'}")
    
    # Mostra detalhes das primeiras transações
    if st.session_state.gerenciador.transacoes:
        st.write("**Primeiras 3 transações do sistema (antes dos filtros):**")
        for i, t in enumerate(st.session_state.gerenciador.transacoes[:3]):
            informativa = getattr(t, 'informativa', False)
            st.write(f"{i+1}. {t.data.strftime('%d/%m/%Y')} | {t.descricao} | R$ {t.valor:.2f} | Tipo: {t.tipo} | Informativa: {informativa}")
    else:
        st.error("⚠️ **PROBLEMA:** Não há NENHUMA transação no sistema!")
    
    # Verifica se o filtro de compras de cartão está removendo tudo
    transacoes_sem_filtro_cartao = st.session_state.gerenciador.transacoes.copy()
    st.write(f"**Transações SEM filtro de cartão:** {len(transacoes_sem_filtro_cartao)}")
    
    st.write("---")
    # === FIM DO DIAGNÓSTICO ===











    

    
    # === EXIBIÇÃO DAS TRANSAÇÕES ===
    if not transacoes_filtradas:
        st.info("🔍 Nenhuma transação encontrada com os filtros aplicados.")
    else:
        # Ordena por data (mais recente primeiro)
        transacoes_ordenadas = sorted(
            transacoes_filtradas,
            key=lambda t: t.data,
            reverse=True
        )
        
        for t in transacoes_ordenadas:
            # Busca nome da conta
            conta = st.session_state.gerenciador.buscar_conta_por_id(t.id_conta)
            nome_conta = conta.nome if conta else "Conta não encontrada"
            
            # Cor baseada no tipo
            cor_valor = "green" if t.tipo == "Receita" else "red"
            sinal = "+" if t.tipo == "Receita" else "-"
            
            # === LINHA PRINCIPAL ===
            col1, col2, col3, col4, col5 = st.columns([1.2, 2, 2.5, 1.3, 0.8])
            
            with col1:
                st.text(t.data.strftime("%d/%m/%Y"))
            
            with col2:
                st.text(nome_conta)
            
            with col3:
                # Identifica compras de cartão
                if getattr(t, 'informativa', False) and t.tipo == "Compra Cartão":
                    st.text(f"💳 {t.descricao}")
                # Destaque para vendas de investimento
                elif t.categoria == "Venda de Investimento":
                    if "Lucro:" in t.descricao:
                        st.text(f"💰 {t.descricao}")
                    elif "Prejuízo:" in t.descricao:
                        st.text(f"📉 {t.descricao}")
                    else:
                        st.text(t.descricao)
                else:
                    st.text(t.descricao)

            
            with col4:
                # Se for transação informativa (compra de cartão)
                if getattr(t, 'informativa', False):
                    st.markdown(f":gray[**ℹ️ {formatar_moeda(t.valor)}**]")
                else:
                    st.markdown(f":{cor_valor}[**{sinal}{formatar_moeda(t.valor)}**]")           
            
            with col5:
                # Não permite excluir compras de cartão (são gerenciadas pelo módulo de cartões)
                if not getattr(t, 'informativa', False):
                    if st.button("🗑️", key=f"del_trans_{t.id_transacao}", help="Excluir transação"):
                        st.session_state.transacao_para_excluir = t.id_transacao
                        st.rerun()
                else:
                    st.text("")  # Espaço vazio para manter alinhamento
            
            # === DETALHES SEMPRE VISÍVEIS ===
            col_det1, col_det2, col_det3 = st.columns([2, 2, 3])
            
            with col_det1:
                st.caption(f"📂 {t.categoria}")
            
            with col_det2:
                tag_texto = getattr(t, "tag", "")
                if tag_texto:
                    st.caption(f"🏷️ {tag_texto}")
                else:
                    st.caption("🏷️ -")
            
            with col_det3:
                if t.observacao:
                    st.caption(f"📝 {t.observacao}")
                else:
                    st.caption("📝 -")
            
            # === CONFIRMAÇÃO DE EXCLUSÃO ===
            if st.session_state.get('transacao_para_excluir') == t.id_transacao:
                st.warning(f"⚠️ Tem certeza que deseja excluir esta transação?")
                
                col_confirm, col_cancel = st.columns(2)
                
                with col_confirm:
                    if st.button("✅ Sim, excluir", key=f"confirm_del_{t.id_transacao}", type="primary"):
                        # Estorna o valor na conta
                        if t.tipo == "Receita":
                            conta.saldo -= t.valor
                        else:
                            conta.saldo += t.valor
                        
                        # Remove a transação
                        st.session_state.gerenciador.transacoes.remove(t)
                        st.session_state.gerenciador.salvar_dados()
                        st.toast("Transação excluída com sucesso!")
                        st.session_state.transacao_para_excluir = None
                        st.rerun()
                
                with col_cancel:
                    if st.button("❌ Cancelar", key=f"cancel_del_{t.id_transacao}"):
                        st.session_state.transacao_para_excluir = None
                        st.rerun()
            
            st.divider()
# --- CONTAS ---
with tab_contas:
    st.header("Gerenciar Contas")
    col_contas1, col_contas2 = st.columns(2)

    with col_contas2:
        with st.form("add_account_form", clear_on_submit=True):
            st.subheader("Adicionar Nova Conta")
            tipo_conta = st.selectbox("Tipo de Conta", ["Conta Corrente", "Conta Investimento"])
            nome_conta = st.text_input("Nome da Conta")
            logo_url_add = st.text_input("URL do Logo (Opcional)")
            if tipo_conta == "Conta Corrente":
                saldo_inicial = st.number_input("Saldo Inicial (R$)", min_value=0.0, format="%.2f")
                limite = st.number_input("Limite do Cheque Especial (R$)", min_value=0.0, format="%.2f")
            if st.form_submit_button("Adicionar Conta", use_container_width=True):
                if not nome_conta:
                    st.error("O nome da conta é obrigatório.")
                else:
                    nova_conta = None
                    if tipo_conta == "Conta Corrente":
                        nova_conta = ContaCorrente(
                            nome=nome_conta,
                            saldo=saldo_inicial,
                            limite_cheque_especial=limite,
                            logo_url=logo_url_add,
                        )
                    else:
                        nova_conta = ContaInvestimento(nome=nome_conta, logo_url=logo_url_add)
                    if nova_conta:
                        st.session_state.gerenciador.adicionar_conta(nova_conta)
                        st.session_state.gerenciador.salvar_dados()
                        st.success(f"Conta '{nome_conta}' adicionada!")
                        st.rerun()

    with col_contas1:
        st.subheader("Contas Existentes")
        todas_as_contas = st.session_state.gerenciador.obter_contas_ativas()
        if not todas_as_contas:
            st.info("Nenhuma conta cadastrada.")
        else:
            tab_cc_ger, tab_ci_ger = st.tabs(["Contas Correntes", "Contas de Investimento"])

            def render_conta_com_confirmacao(conta):
                logo_col, expander_col = st.columns([1, 5])
                with logo_col:
                    if conta.logo_url:
                        st.image(conta.logo_url, width=65)
                    else:
                        st.write("🏦" if isinstance(conta, ContaCorrente) else "📈")
                
                # Valor do título do expansor:
                # - ContaCorrente: saldo
                # - ContaInvestimento: patrimônio atualizado (saldo_caixa + valor atual dos ativos)
                if isinstance(conta, ContaInvestimento):
                    pos_header = st.session_state.gerenciador.calcular_posicao_conta_investimento(conta.id_conta)
                    patrimonio_header = pos_header.get("patrimonio_atualizado", float(conta.saldo))
                else:
                    patrimonio_header = float(conta.saldo)
                
                with expander_col:
                    with st.expander(f"{conta.nome} - {formatar_moeda(patrimonio_header)}"):
                        if isinstance(conta, ContaCorrente):
                            st.write(f"Limite: {formatar_moeda(conta.limite_cheque_especial)}")
                        elif isinstance(conta, ContaInvestimento):
                            # Métricas base (preço médio)
                            st.metric("Patrimônio Consolidado (preço médio)", formatar_moeda(conta.saldo))
                            col_caixa, col_ativos = st.columns(2)
                            col_caixa.metric("Saldo em Caixa", formatar_moeda(conta.saldo_caixa))
                            col_ativos.metric("Valor em Ativos (preço médio)", formatar_moeda(conta.valor_em_ativos))

                            st.divider()
                            st.write("Cotações e Posição Atual")

                            col_btn, _ = st.columns([1, 5])
                            with col_btn:
                                if st.button("Atualizar cotações", key=f"upd_quotes_{conta.id_conta}"):
                                    st.session_state.gerenciador._cotacoes_cache = {}
                                    st.rerun()

                            pos = st.session_state.gerenciador.calcular_posicao_conta_investimento(conta.id_conta)
                            if not pos or not pos["ativos"]:
                                st.info("Nenhum ativo nesta conta ainda.")
                            else:
                                met1, met2, met3 = st.columns(3)
                                met1.metric("Saldo em Caixa", formatar_moeda(pos["saldo_caixa"]))
                                met2.metric("Valor Atual em Ativos", formatar_moeda(pos["total_valor_atual_ativos"]))
                                met3.metric("Patrimônio Atualizado", formatar_moeda(pos["patrimonio_atualizado"]))

                                # Detalhe por ativo
                                st.caption("Detalhe por ativo:")

                                def _to_float(x):
                                    return float(x) if x is not None else None

                                linhas = []
                                for item in pos.get("ativos", []):
                                    linhas.append({
                                        "Ticker": item.get("ticker", ""),
                                        "Tipo": item.get("tipo", ""),
                                        "Quantidade": float(item.get("quantidade", 0.0) or 0.0),
                                        "Preço Médio": float(item.get("preco_medio", 0.0) or 0.0),
                                        "Preço Atual": _to_float(item.get("preco_atual")),
                                        "Valor Atual": _to_float(item.get("valor_atual")),
                                        "P/L (R$)": _to_float(item.get("pl")),
                                        "P/L (%)": _to_float(item.get("pl_pct")),
                                    })

                                df = pd.DataFrame(linhas)
                                colunas = ["Ticker", "Tipo", "Quantidade", "Preço Médio", "Preço Atual", "Valor Atual", "P/L (R$)", "P/L (%)"]
                                df = df[colunas] if not df.empty else pd.DataFrame(columns=colunas)

                                def _fmt_num6(v: float) -> str:
                                    if pd.isna(v):
                                        return ""
                                    # Se valor >= 1000, formata sem casas decimais (ex.: 1.500.000)
                                    if v >= 1000:
                                        return f"{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                    # Se valor >= 1, formata com 2 casas (ex.: 123,45)
                                    elif v >= 1:
                                        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                    # Se valor < 1, formata com até 6 casas (ex.: 0,000123)
                                    else:
                                        return f"{v:,.6f}".replace(",", "X").replace(".", ",").replace("X", ".")

                                def _fmt_preco_cripto(v: float) -> str:
                                    """Formata preços incluindo criptos de centavos (pode ter até 8 casas)"""
                                    if pd.isna(v):
                                        return ""
                                    if v >= 1000:
                                        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                    elif v >= 1:
                                        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                    elif v >= 0.01:
                                        return f"R$ {v:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                    else:
                                        # Para valores muito pequenos (< 0,01), mostra até 8 casas
                                        return f"R$ {v:,.8f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                
                                def _fmt_moeda(v: float) -> str:
                                    if pd.isna(v):
                                        return ""
                                    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                
                                def _fmt_pct(v: float) -> str:
                                    if pd.isna(v):
                                        return ""
                                    return f"{v:.2f}%".replace(".", ",")
                                
                                def _cor_pl(val: float) -> str:
                                    if pd.isna(val):
                                        return ""
                                    return "color: red;" if val < 0 else "color: #0b3d91;"
                                
                                styled = (
                                    df.style
                                      .format({
                                          "Quantidade": _fmt_num6,
                                          "Preço Médio": _fmt_preco_cripto,
                                          "Preço Atual": _fmt_preco_cripto,
                                          "Valor Atual": lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                                          "P/L (R$)": lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                                          "P/L (%)": lambda v: f"{v:,.2f}%".replace(",", "X").replace(".", ",").replace("X", "."),
                                      })
                                      .map(_cor_pl, subset=["P/L (R$)", "P/L (%)"])
                                      .hide(axis="index")
                                )
                                
                                st.dataframe(styled, width="stretch")

                                st.divider()
                                st.caption("Obs.: Cotações provenientes do Yahoo Finance (yfinance). Alguns ativos podem não ter preço disponível.")
                            
                            st.divider()
                            # Ativos (base de custo)
                            if conta.ativos:
                                st.write("Ativos (base de custo):")
                                df_ativos = pd.DataFrame([a.para_dict() for a in conta.ativos])
                                df_ativos["valor_total"] = df_ativos.apply(
                                    lambda row: row["quantidade"] * row["preco_medio"], axis=1
                                )
                                
                                # Formatação inteligente da quantidade (mesma lógica do "Detalhe por ativo")
                                def _fmt_qtd_base(v: float) -> str:
                                    if pd.isna(v):
                                        return ""
                                    if v >= 1000:
                                        return f"{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                    elif v >= 1:
                                        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                    else:
                                        return f"{v:,.6f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                
                                def _fmt_moeda_base(v: float) -> str:
                                    if pd.isna(v):
                                        return ""
                                    if v >= 1000:
                                        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                    elif v >= 1:
                                        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                    elif v >= 0.01:
                                        return f"R$ {v:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                    else:
                                        # Para valores muito pequenos (< 0,01), mostra até 8 casas
                                        return f"R$ {v:,.8f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                
                                styled_base = (
                                    df_ativos[["ticker", "quantidade", "preco_medio", "tipo_ativo", "valor_total"]]
                                    .style.format({
                                        "quantidade": _fmt_qtd_base,
                                        "preco_medio": _fmt_moeda_base,
                                        "valor_total": _fmt_moeda_base,
                                    })
                                    .hide(axis="index")
                                )
                                
                                st.dataframe(styled_base, width="stretch")
                            
                        st.divider()
                        with st.form(f"edit_form_{conta.id_conta}"):
                            novo_nome = st.text_input("Nome", value=conta.nome)
                            nova_logo_url = st.text_input("URL do Logo", value=conta.logo_url)
                            if isinstance(conta, ContaCorrente):
                                novo_limite = st.number_input(
                                    "Limite", min_value=0.0, value=float(conta.limite_cheque_especial), format="%.2f"
                                )
                            if st.form_submit_button("Salvar Alterações"):
                                nome_mudou = conta.editar_nome(novo_nome)
                                logo_mudou = conta.editar_logo_url(nova_logo_url)
                                attr_mudou = False
                                if isinstance(conta, ContaCorrente):
                                    attr_mudou = conta.editar_limite(novo_limite)
                                if nome_mudou or logo_mudou or attr_mudou:
                                    st.session_state.gerenciador.salvar_dados()
                                    st.toast(f"Conta '{novo_nome}' atualizada!")
                                    st.rerun()
                        if st.button("Remover Conta", key=f"remove_{conta.id_conta}", type="primary"):
                            st.session_state.conta_para_excluir = conta.id_conta
                            st.rerun()

                if st.session_state.conta_para_excluir == conta.id_conta:
                    st.warning(f"ATENÇÃO: Tem certeza que deseja excluir a conta '{conta.nome}'?")
                    col_confirm, col_cancel, _ = st.columns([1, 1, 4])
                    with col_confirm:
                        if st.button("Sim, excluir permanentemente", key=f"confirm_del_acc_{conta.id_conta}", type="primary"):
                            if st.session_state.gerenciador.remover_conta(conta.id_conta):
                                st.session_state.gerenciador.salvar_dados()
                                st.toast(f"Conta '{conta.nome}' removida!")
                                st.session_state.conta_para_excluir = None
                                st.rerun()
                    with col_cancel:
                        if st.button("Cancelar", key=f"cancel_del_acc_{conta.id_conta}"):
                            st.session_state.conta_para_excluir = None
                            st.rerun()

            with tab_cc_ger:
                contas_correntes = [c for c in todas_as_contas if isinstance(c, ContaCorrente)]
                if not contas_correntes:
                    st.info("Nenhuma conta corrente cadastrada.")
                for conta in contas_correntes:
                    render_conta_com_confirmacao(conta)

            with tab_ci_ger:
                contas_investimento = [c for c in todas_as_contas if isinstance(c, ContaInvestimento)]
                if not contas_investimento:
                    st.info("Nenhuma conta de investimento cadastrada.")
                for conta in contas_investimento:
                    render_conta_com_confirmacao(conta)

# --- CARTÕES ---
with tab_cartoes:
    st.header("Gerenciar Cartões de Crédito")
    col_cartoes1, col_cartoes2 = st.columns(2)

    with col_cartoes2:
        with st.form("add_card_form", clear_on_submit=True):
            st.subheader("Adicionar Novo Cartão")
            nome_cartao = st.text_input("Nome do Cartão")
            logo_url_cartao = st.text_input("URL do Logo (Opcional)")
            dia_fechamento = st.number_input("Dia do Fechamento", min_value=1, max_value=31, value=28)
            dia_vencimento = st.number_input("Dia do Vencimento", min_value=1, max_value=31, value=10)
            if st.form_submit_button("Adicionar Cartão", use_container_width=True):
                if not nome_cartao:
                    st.error("O nome do cartão é obrigatório.")
                else:
                    novo_cartao = CartaoCredito(
                        nome=nome_cartao,
                        logo_url=logo_url_cartao,
                        dia_fechamento=dia_fechamento,
                        dia_vencimento=dia_vencimento,
                    )
                    st.session_state.gerenciador.adicionar_cartao_credito(novo_cartao)
                    st.session_state.gerenciador.salvar_dados()
                    st.success(f"Cartão '{nome_cartao}' adicionado!")
                    st.rerun()

                # === GERENCIAR FECHAMENTOS CUSTOMIZADOS ===
        st.divider()
        st.subheader("⚙️ Datas de Fechamento Customizadas")
        st.caption("Configure datas de fechamento específicas para meses onde o banco altera o dia padrão (feriados, finais de semana, etc.)")
        
        if not st.session_state.gerenciador.cartoes_credito:
            st.info("Adicione um cartão primeiro.")
        else:

            # Usa índice ao invés de objeto direto
            cartoes_disponiveis = st.session_state.gerenciador.cartoes_credito
            if not cartoes_disponiveis:
                st.info("Adicione um cartão primeiro.")
            else:
                # Cria mapeamento de nome para índice
                nomes_cartoes = [c.nome for c in cartoes_disponiveis]
                
                cartao_selecionado_nome = st.selectbox(
                    "Selecione o Cartão",
                    options=nomes_cartoes,
                    key="cartao_config_fechamento"
                )
                
                # Busca o índice do cartão selecionado
                idx_cartao = nomes_cartoes.index(cartao_selecionado_nome)
                cartao_config = cartoes_disponiveis[idx_cartao]

            st.write(f"**Dia de fechamento padrão:** {cartao_config.dia_fechamento}")
            
            # Exibe fechamentos customizados existentes
            st.write("**Fechamentos customizados:**")
                            
            if cartao_config.fechamentos_customizados and len(cartao_config.fechamentos_customizados) > 0:
                for chave_mes, dia in sorted(cartao_config.fechamentos_customizados.items()):
                    col_mes, col_dia, col_del = st.columns([2, 2, 1])
                    
                    ano, mes = chave_mes.split("-")
                    col_mes.text(f"{mes}/{ano}")
                    col_dia.text(f"Fecha dia {dia}")

                    if col_del.button("🗑️", key=f"del_fechamento_{cartao_config.id_cartao}_{chave_mes}"):
                        del st.session_state.gerenciador.cartoes_credito[idx_cartao].fechamentos_customizados[chave_mes]
                        st.session_state.gerenciador.salvar_dados()
                        st.toast("Fechamento customizado removido!")
                        st.rerun()

            else:
                st.info("Nenhum fechamento customizado configurado.")

            st.write("**Adicionar fechamento customizado:**")
            
            col_ano, col_mes, col_dia = st.columns(3)
            
            with col_ano:
                ano_custom = st.number_input("Ano", min_value=2024, max_value=2030, value=datetime.today().year, key="ano_fechamento_custom")
            
            with col_mes:
                mes_custom = st.number_input("Mês", min_value=1, max_value=12, value=datetime.today().month, key="mes_fechamento_custom")
            
            with col_dia:
                dia_custom = st.number_input("Dia de Fechamento", min_value=1, max_value=31, value=cartao_config.dia_fechamento, key="dia_fechamento_custom")

            if st.button("Adicionar Fechamento Customizado", key="add_fechamento_custom"):
                chave = f"{ano_custom}-{mes_custom:02d}"
                
                # Modifica diretamente o cartão na lista do gerenciador
                st.session_state.gerenciador.cartoes_credito[idx_cartao].fechamentos_customizados[chave] = dia_custom
                                                
                # Salva
                st.session_state.gerenciador.salvar_dados()
                
                st.success(f"✅ Fechamento customizado adicionado: {mes_custom:02d}/{ano_custom} fecha dia {dia_custom}")
                st.rerun()

        st.divider()
        
        st.subheader("Lançar Compra no Cartão")
        cartoes_cadastrados = st.session_state.gerenciador.cartoes_credito
        if not cartoes_cadastrados:
            st.warning("Adicione um cartão de crédito para poder lançar compras.")
        else:
            # Por ID, exibindo apenas nome do cartão
            mapa_cartao = {c.id_cartao: c for c in cartoes_cadastrados}
            ids_cartao = list(mapa_cartao.keys())
            
            # Tabs para separar os modos
            # Removida a aba de Lançamento Individual - usando apenas Lançamento Rápido# Removida a aba de Lançamento Individual - usando apenas Lançamento Rápido

           
        st.info("💡 **Lançamento de Compras no Cartão:** Use os campos abaixo para adicionar múltiplas compras. Clique em 'Salvar Todas' apenas quando terminar.")
        
        # Inicializa lista de compras pendentes
        if "compras_pendentes" not in st.session_state:
            st.session_state.compras_pendentes = []
        
        # Contador para gerar keys únicas
        if "contador_compras" not in st.session_state:
            st.session_state.contador_compras = 0
        
        # === BOTÃO ADICIONAR FORNECEDOR (FORA DO FORMULÁRIO) ===
        col_btn_add = st.columns([6, 1])
        with col_btn_add[1]:
            if st.button("➕ Novo Fornecedor", key="add_forn_rapido", help="Adicionar novo fornecedor", use_container_width=True):
                st.session_state.mostrar_add_fornecedor_rapido = True
                st.rerun()
        
        # Modal para adicionar fornecedor
        if st.session_state.get("mostrar_add_fornecedor_rapido", False):
            with st.container():
                st.write("**Adicionar Novo Fornecedor:**")
                novo_fornecedor = st.text_input(
                    "Nome do fornecedor:",
                    key="input_novo_forn_rapido",
                    placeholder="Ex: Supermercado XYZ"
                )
                
                col_salvar, col_cancelar = st.columns(2)
                
                with col_salvar:
                    if st.button("✅ Salvar", key="salvar_novo_forn_rapido", type="primary"):
                        if novo_fornecedor.strip():
                            if st.session_state.gerenciador.adicionar_fornecedor(novo_fornecedor):
                                st.session_state.gerenciador.salvar_dados()
                                st.toast(f"Fornecedor '{novo_fornecedor}' adicionado!")
                                st.session_state.mostrar_add_fornecedor_rapido = False
                                st.rerun()
                            else:
                                st.warning("Fornecedor já existe!")
                        else:
                            st.warning("Digite um nome válido!")
                
                with col_cancelar:
                    if st.button("❌ Cancelar", key="cancelar_novo_forn_rapido"):
                        st.session_state.mostrar_add_fornecedor_rapido = False
                        st.rerun()
            
            st.divider()
        
        # === FORMULÁRIO DE COMPRA ===
        with st.form("form_rapido_compras", clear_on_submit=True):
            st.write("**Dados da Compra:**")
            
            cartao_selecionado_id = st.selectbox(
                "Cartão",
                options=ids_cartao,
                format_func=lambda cid: mapa_cartao[cid].nome,
            )
            
            col1, col2 = st.columns(2)
            with col1:
                # Seleção de fornecedor DENTRO do formulário
                fornecedores = st.session_state.gerenciador.obter_fornecedores()
                
                if fornecedores:
                    descricao_compra = st.selectbox(
                        "Descrição/Fornecedor",
                        options=fornecedores,
                        key="desc_rapida"
                    )
                else:
                    st.warning("⚠️ Nenhum fornecedor cadastrado. Use o botão '➕ Novo Fornecedor' acima.")
                    descricao_compra = ""
            
            with col2:
                categoria_compra = st.selectbox("Categoria", st.session_state.gerenciador.categorias)
            
            col3, col4, col5 = st.columns(3)
            with col3:
                valor_compra = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
            with col4:
                num_parcelas = st.number_input("Parcelas", min_value=1, value=1)
            with col5:
                data_compra_cartao = st.date_input("Data", value=datetime.today(), format="DD/MM/YYYY")
            
            col6, col7 = st.columns(2)
            
            with col6:
                tags_disponiveis = [""] + st.session_state.gerenciador.tags
                tag_compra = st.selectbox(
                    "TAG (Opcional)",
                    options=tags_disponiveis,
                    format_func=lambda x: "Nenhuma" if x == "" else x,
                    key="tag_rapida"
                )
            
            with col7:
                observacao_compra = st.text_input("Observação", placeholder="Opcional")
    
            submitted = st.form_submit_button("➕ Adicionar à Lista", use_container_width=True, type="primary")
    
            if submitted:
                if not all([descricao_compra, categoria_compra, valor_compra > 0]):
                    st.error("⚠️ Preencha descrição, categoria e valor.")
                else:
                    ano_ciclo, mes_ciclo = st.session_state.gerenciador.calcular_ciclo_compra(
                        cartao_selecionado_id,
                        data_compra_cartao
                    )
                    
                    if st.session_state.gerenciador.ciclo_esta_fechado(cartao_selecionado_id, ano_ciclo, mes_ciclo):
                        cartao_nome = mapa_cartao[cartao_selecionado_id].nome
                        st.error(f"❌ **Não é possível adicionar esta compra!**\n\nO ciclo **{mes_ciclo:02d}/{ano_ciclo}** do cartão **{cartao_nome}** já está fechado.\n\nPara lançar compras neste período, você precisa reabrir a fatura correspondente.")
                    else:
                        st.session_state.compras_pendentes.append({
                            "id_cartao": cartao_selecionado_id,
                            "cartao_nome": mapa_cartao[cartao_selecionado_id].nome,
                            "descricao": descricao_compra,
                            "valor_total": valor_compra,
                            "data_compra": data_compra_cartao,
                            "categoria": categoria_compra,
                            "num_parcelas": num_parcelas,
                            "observacao": observacao_compra,
                            "tag": tag_compra,
                        })
                        st.session_state.contador_compras += 1
        
        # Mostra compras pendentes
        if st.session_state.compras_pendentes:
            st.divider()
            st.success(f"✅ **{len(st.session_state.compras_pendentes)} compra(s) na lista**")
            
            # Lista as compras com opção de remover
            for idx, compra in enumerate(st.session_state.compras_pendentes):
                col_info, col_remove = st.columns([6, 1])
                                            
                with col_info:
                    parcelas_txt = f" ({compra['num_parcelas']}x)" if compra['num_parcelas'] > 1 else ""
                    tag_txt = f" 🏷️ {compra['tag']}" if compra['tag'] else ""
                    
                    # Calcula o ciclo
                    ano_ciclo, mes_ciclo = st.session_state.gerenciador.calcular_ciclo_compra(
                        compra['id_cartao'], 
                        compra['data_compra']
                    )
                    ciclo_txt = f"{mes_ciclo:02d}/{ano_ciclo}"
                    
                    st.text(
                        f"{idx+1}. {compra['cartao_nome']} | {compra['descricao']} | "
                        f"R$ {compra['valor_total']:.2f}{parcelas_txt} | "
                        f"{compra['data_compra'].strftime('%d/%m/%Y')} | "
                        f"📅 Ciclo: {ciclo_txt}{tag_txt}"
                    )
                
                with col_remove:
                    if st.button("🗑️", key=f"remove_pending_{idx}_{st.session_state.contador_compras}", help="Remover"):
                        st.session_state.compras_pendentes.pop(idx)
                        st.rerun()
            
            st.divider()
            
            # Botões de ação
            col_salvar, col_limpar = st.columns(2)
            
            with col_salvar:
                if st.button("💾 Salvar Todas as Compras", type="primary", use_container_width=True):
                    sucesso_total = 0
                    falhas = []
                    
                    for compra in st.session_state.compras_pendentes:
                        sucesso = st.session_state.gerenciador.registrar_compra_cartao(
                            id_cartao=compra["id_cartao"],
                            descricao=compra["descricao"],
                            valor_total=compra["valor_total"],
                            data_compra=compra["data_compra"],
                            categoria=compra["categoria"],
                            num_parcelas=compra["num_parcelas"],
                            observacao=compra["observacao"],
                            tag=compra["tag"],
                        )
                        if sucesso:
                            sucesso_total += 1
                        else:
                            falhas.append(compra["descricao"])
                    
                    st.session_state.gerenciador.salvar_dados()
                    
                    if falhas:
                        st.warning(f"⚠️ {sucesso_total} salvas, {len(falhas)} falharam: {', '.join(falhas)}")
                    else:
                        st.success(f"🎉 {sucesso_total} compras registradas com sucesso!")
                    
                    st.session_state.compras_pendentes = []
                    st.rerun()
            
            with col_limpar:
                if st.button("🗑️ Limpar Lista", use_container_width=True):
                    st.session_state.compras_pendentes = []
                    st.rerun()
        else:
            st.info("📝 Nenhuma compra na lista ainda. Use o formulário acima para adicionar.")


    with col_cartoes1:
        st.subheader("Faturas dos Cartões")
        cartoes = st.session_state.gerenciador.cartoes_credito
        if not cartoes:
            st.info("Nenhum cartão de crédito cadastrado.")
        else:
            for cartao in cartoes:
                logo_col, expander_col = st.columns([1, 5])

                with logo_col:
                    if cartao.logo_url:
                        st.image(cartao.logo_url, width=65)
                    else:
                        st.write("💳")

                with expander_col:
                    ciclos = st.session_state.gerenciador.listar_ciclos_navegacao(cartao.id_cartao)
                    if not ciclos:
                        hoje = date.today()
                        ciclos = st.session_state.gerenciador.listar_ciclos_navegacao(cartao.id_cartao, hoje)

                    padrao = st.session_state.gerenciador.ciclo_aberto_mais_antigo(cartao.id_cartao) or ciclos[0]
                    labels = [f"{mes:02d}/{ano}" for (ano, mes) in ciclos]
                    idx_padrao = ciclos.index(padrao) if padrao in ciclos else 0

                    sel_label = st.selectbox(
                        "Ciclo de Referência",
                        options=labels,
                        index=idx_padrao,
                        key=f"ciclo_ref_{cartao.id_cartao}",
                    )
                    sel_idx = labels.index(sel_label)
                    sel_ano, sel_mes = ciclos[sel_idx]

                    aberto_do_ciclo = st.session_state.gerenciador.obter_lancamentos_do_ciclo(cartao.id_cartao, sel_ano, sel_mes)
                    valor_fatura_aberta = sum(c.valor for c in aberto_do_ciclo)
                    futuros = st.session_state.gerenciador.obter_lancamentos_futuros_desde(cartao.id_cartao, sel_ano, sel_mes)
                    faturas_fechadas = [f for f in st.session_state.gerenciador.faturas if f.id_cartao == cartao.id_cartao]

                    with st.expander(f"{cartao.nome} - Fatura Aberta ({sel_label}): {formatar_moeda(valor_fatura_aberta)}"):
                        tab_aberta, tab_futuros, tab_fechadas = st.tabs(["Lançamentos em Aberto", "Lançamentos Futuros", "Histórico de Faturas"])

                        with tab_aberta:
                            st.metric("Total em Aberto (Ciclo Selecionado)", formatar_moeda(valor_fatura_aberta))
                            if not aberto_do_ciclo:
                                st.info("Nenhum lançamento em aberto para o ciclo selecionado.")
                            else:
                                    # Ordena por data da compra real
                                    compras_ordenadas = sorted(aberto_do_ciclo, key=lambda x: getattr(x, "data_compra_real", x.data_compra))
                                    
                                    # Mostra vencimento apenas uma vez no topo
                                    if compras_ordenadas:
                                        primeiro_venc = compras_ordenadas[0].data_compra
                                        st.markdown(f"**📅 Vencimento: {primeiro_venc.strftime('%d/%m/%Y')}** | **Total: {formatar_moeda(sum(c.valor for c in compras_ordenadas))}**")
                                        st.divider()
                                    
                                    for compra in compras_ordenadas:
                                        c1, c2 = st.columns([6, 1])
                                        
                                        real_str = getattr(compra, "data_compra_real", compra.data_compra).strftime("%d/%m/%Y")
                                        obs_txt = f" | 📝 {compra.observacao}" if getattr(compra, "observacao", None) else ""
                                        tag_txt = f" | 🏷️ {compra.tag}" if getattr(compra, "tag", None) else ""
                                        
                                        # Tudo em uma linha
                                        c1.markdown(f"<small>{real_str} | {compra.descricao} | {formatar_moeda(compra.valor)}{obs_txt}{tag_txt}</small>", unsafe_allow_html=True)
                                        
                                        with c2:
                                            if st.button("🗑️", key=f"del_compra_{compra.id_compra}", help="Excluir esta compra"):
                                                st.session_state.compra_para_excluir = compra.id_compra_original
                                                st.rerun()

        

                                    if st.session_state.compra_para_excluir == compra.id_compra_original:
                                        st.warning(f"Excluir '{compra.descricao}' e todas as suas parcelas?")
                                        cc1, cc2 = st.columns(2)
                                        if cc1.button("Sim, excluir", key=f"conf_del_compra_{compra.id_compra}", type="primary"):
                                            st.session_state.gerenciador.remover_compra_cartao(compra.id_compra_original)
                                            st.session_state.gerenciador.salvar_dados()
                                            st.toast("Compra removida!")
                                            st.session_state.compra_para_excluir = None
                                            st.rerun()
                                        if cc2.button("Cancelar", key=f"cancel_del_compra_{compra.id_compra}"):
                                            st.session_state.compra_para_excluir = None
                                            st.rerun()

                            st.divider()
                            with st.form(f"close_bill_form_{cartao.id_cartao}", clear_on_submit=True):
                                st.write("Fechar Fatura")
                                col_form_f1, col_form_f2 = st.columns(2)
                                try:
                                    data_venc_sugerida = date(sel_ano, sel_mes, 10)
                                except Exception:
                                    data_venc_sugerida = date(sel_ano, sel_mes, 1)

                                data_fechamento_real = col_form_f1.date_input("Data Real do Fechamento", value=date.today(), format="DD/MM/YYYY")
                                data_vencimento_real = col_form_f2.date_input("Data Real do Vencimento", value=data_venc_sugerida, format="DD/MM/YYYY")
                                if st.form_submit_button("Confirmar Fechamento", type="primary"):
                                    nova_fatura = st.session_state.gerenciador.fechar_fatura(cartao.id_cartao, data_fechamento_real, data_vencimento_real)
                                    if nova_fatura:
                                        st.session_state.gerenciador.salvar_dados()
                                        st.success(f"Fatura de {nova_fatura.data_vencimento.strftime('%m/%Y')} fechada!")
                                        st.rerun()
                                    else:
                                        st.warning("Nenhuma compra encontrada no período para fechar a fatura.")

                        with tab_futuros:
                            total_futuro = sum(c.valor for c in futuros)
                            st.metric("Total Futuro (Próximas Competências)", formatar_moeda(total_futuro))
                            if not futuros:
                                st.info("Nenhum lançamento futuro para este cartão.")
                            else:
                                 # Ordena por vencimento e depois por data real
                                futuros_ordenados = sorted(futuros, key=lambda x: (x.data_compra, getattr(x, "data_compra_real", x.data_compra)))
                                
                                for compra in futuros_ordenados:
                                    venc_str = compra.data_compra.strftime("%d/%m/%Y")
                                    real_str = getattr(compra, "data_compra_real", compra.data_compra).strftime("%d/%m/%Y")
                                    obs_txt = f" | 📝 {compra.observacao}" if getattr(compra, "observacao", None) else ""
                                    tag_txt = f" | 🏷️ {compra.tag}" if getattr(compra, "tag", None) else ""
                                    
                                    # Tudo em uma linha com vencimento
                                    st.markdown(f"<small>📅 Venc: {venc_str} | {real_str} | {compra.descricao} | {formatar_moeda(compra.valor)}{obs_txt}{tag_txt}</small>", unsafe_allow_html=True)                       
                                
                                
                        with tab_fechadas:
                            if not faturas_fechadas:
                                st.info("Nenhuma fatura fechada para este cartão.")
                            else:
                                for fatura in sorted(faturas_fechadas, key=lambda f: f.data_vencimento, reverse=True):
                                    fatura_col1, fatura_col2 = st.columns([3, 1])
                                    cor = "green" if fatura.status == "Paga" else "red"
                                    fatura_col1.metric(
                                        f"Fatura {fatura.data_vencimento.strftime('%m/%Y')}", 
                                        formatar_moeda(fatura.valor_total)
                                    )
                                    fatura_col1.caption(
                                        f"Vencimento: {fatura.data_vencimento.strftime('%d/%m/%Y')} - Status: :{cor}[{fatura.status}]"
                                    )
                        
                                    with st.expander("Ver Lançamentos"):
                                        lancamentos_fatura = [
                                            c for c in st.session_state.gerenciador.compras_cartao 
                                            if c.id_fatura == fatura.id_fatura
                                        ]
                                        if not lancamentos_fatura:
                                            st.caption("Nenhum lançamento encontrado para esta fatura.")
                                        else:
                                            for lanc in sorted(lancamentos_fatura, key=lambda l: l.data_compra):
                                                venc_str = lanc.data_compra.strftime("%d/%m/%Y")
                                                real_str = getattr(lanc, "data_compra_real", lanc.data_compra).strftime("%d/%m/%Y")
                                                st.text(f"Venc.: {venc_str} • Compra: {real_str} — {lanc.descricao}: {formatar_moeda(lanc.valor)}")
                                                
                                                # Exibe observação diretamente abaixo (se existir)
                                                if getattr(lanc, "observacao", None):
                                                    st.caption(f"📝 {lanc.observacao}")
                                                
                                                # Exibe TAG diretamente abaixo (se existir)
                                                if getattr(lanc, "tag", None):
                                                    st.caption(f"🏷️ {lanc.tag}")

                                    # === BOTÕES DE AÇÃO ===
                                    if fatura.status == "Fechada":
                                        # Fatura fechada mas não paga
                                        col_btn1, col_btn2 = st.columns(2)
                                        
                                        with col_btn1:
                                            if st.button("💰 Pagar Fatura", key=f"pay_bill_{fatura.id_fatura}", use_container_width=True):
                                                st.session_state.fatura_para_pagar = fatura.id_fatura
                                                st.rerun()
                                        
                                        with col_btn2:
                                            if st.button("🔓 Reabrir Fatura", key=f"reopen_bill_{fatura.id_fatura}", type="secondary", use_container_width=True):
                                                st.session_state.fatura_para_reabrir = fatura.id_fatura
                                                st.rerun()
                                    
                                    else:
                                        # Fatura paga
                                        col_btn1, col_btn2 = st.columns(2)
                                        
                                        with col_btn1:
                                            st.success("✅ Paga")
                                        
                                        with col_btn2:
                                            if st.button("🔓 Reabrir Fatura", key=f"reopen_paid_bill_{fatura.id_fatura}", type="secondary", use_container_width=True, help="Estorna o pagamento e reabre a fatura"):
                                                st.session_state.fatura_para_reabrir = fatura.id_fatura
                                                st.rerun()

                                    # === CONFIRMAÇÃO DE PAGAMENTO ===
                                    if st.session_state.fatura_para_pagar == fatura.id_fatura:
                                        with st.form(f"pay_bill_form_{fatura.id_fatura}"):
                                            st.warning(f"Pagar {formatar_moeda(fatura.valor_total)} da fatura de {fatura.data_vencimento.strftime('%m/%Y')}?")
                                            contas_correntes_pagamento = [
                                                c for c in st.session_state.gerenciador.obter_contas_ativas() 
                                                if isinstance(c, ContaCorrente)
                                            ]
                                            mapa_cc_pag = {c.id_conta: c for c in contas_correntes_pagamento}
                                            ids_cc_pag = list(mapa_cc_pag.keys())

                                            conta_pagamento_id = st.selectbox(
                                                "Pagar com a conta:",
                                                options=ids_cc_pag,
                                                format_func=lambda cid: mapa_cc_pag[cid].nome,
                                                key=f"pay_fatura_conta_id_{fatura.id_fatura}"
                                            )
                                            data_pagamento = st.date_input(
                                                "Data do Pagamento", 
                                                value=date.today(), 
                                                format="DD/MM/YYYY"
                                            )
                                            if st.form_submit_button("Confirmar Pagamento"):
                                                sucesso = st.session_state.gerenciador.pagar_fatura(
                                                    fatura.id_fatura, conta_pagamento_id, data_pagamento
                                                )
                                                if sucesso:
                                                    st.session_state.gerenciador.salvar_dados()
                                                    st.toast("Fatura paga com sucesso!")
                                                    st.session_state.fatura_para_pagar = None
                                                    st.rerun()
                                                else:
                                                    st.error("Pagamento falhou. Saldo insuficiente.")
                                        
                                        if st.button("Cancelar Pagamento", key=f"cancel_pay_{fatura.id_fatura}"):
                                            st.session_state.fatura_para_pagar = None
                                            st.rerun()
                                    
                                    # === CONFIRMAÇÃO DE REABERTURA ===
                                    if st.session_state.fatura_para_reabrir == fatura.id_fatura:
                                        st.warning(f"⚠️ Tem certeza que deseja REABRIR a fatura de {fatura.data_vencimento.strftime('%m/%Y')}?")
                                        
                                        if fatura.status == "Paga":
                                            st.error("🔄 Esta ação irá ESTORNAR o pagamento e devolver o valor para a conta!")
                                        
                                        st.info(f"📋 {len([c for c in st.session_state.gerenciador.compras_cartao if c.id_fatura == fatura.id_fatura])} lançamentos voltarão para 'em aberto'")
                                        
                                        col_confirm, col_cancel = st.columns(2)
                                        
                                        with col_confirm:
                                            if st.button("✅ Sim, reabrir", key=f"confirm_reopen_{fatura.id_fatura}", type="primary"):
                                                sucesso = st.session_state.gerenciador.reabrir_fatura(fatura.id_fatura)
                                                if sucesso:
                                                    st.session_state.gerenciador.salvar_dados()
                                                    st.toast("Fatura reaberta com sucesso!")
                                                    st.session_state.fatura_para_reabrir = None
                                                    st.rerun()
                                                else:
                                                    st.error("Erro ao reabrir fatura.")
                                        
                                        with col_cancel:
                                            if st.button("❌ Cancelar", key=f"cancel_reopen_{fatura.id_fatura}"):
                                                st.session_state.fatura_para_reabrir = None
                                                st.rerun()
                                    
                                    st.divider()

                        st.divider()
                        if st.button("Remover Cartão", key=f"remove_card_{cartao.id_cartao}", type="primary"):
                            st.session_state.cartao_para_excluir = cartao.id_cartao
                            st.rerun()

                if st.session_state.cartao_para_excluir == cartao.id_cartao:
                    st.warning(f"ATENÇÃO: Tem certeza que deseja excluir o cartão '{cartao.nome}' e todos os seus lançamentos associados?")
                    col_confirm, col_cancel, _ = st.columns([1, 1, 3])
                        
                    with col_confirm:
                        if st.button("Sim, excluir permanentemente", key=f"confirm_del_card_{cartao.id_cartao}", type="primary"):
                            if st.session_state.gerenciador.remover_cartao_credito(cartao.id_cartao):
                                st.session_state.gerenciador.salvar_dados()
                                st.toast(f"Cartão '{cartao.nome}' removido!")
                                st.session_state.cartao_para_excluir = None
                                st.rerun()
                    with col_cancel:
                        if st.button("Cancelar", key=f"cancel_del_card_{cartao.id_cartao}"):
                            st.session_state.cartao_para_excluir = None
                            st.rerun()
    
with tab_config:
    st.header("Configurações Gerais")
    st.subheader("Gerenciar Categorias")

    col_cat1, col_cat2 = st.columns([3, 2])

    with col_cat1:
        st.write("Categorias existentes:")
        categorias = st.session_state.gerenciador.categorias

        if not categorias:
            st.info("Nenhuma categoria cadastrada.")
        else:
            for cat in categorias:
                cat_col1, cat_col2 = st.columns([4, 1])
                cat_col1.write(f"- {cat}")

                if cat_col2.button("🗑️", key=f"del_cat_{cat}", help=f"Excluir categoria '{cat}'"):
                    st.session_state.categoria_para_excluir = cat
                    st.rerun()

                if st.session_state.categoria_para_excluir == cat:
                    st.warning(f"ATENÇÃO: Tem certeza que deseja excluir a categoria '{cat}'?")
                    col_confirm, col_cancel, _ = st.columns([1, 1, 3])

                    with col_confirm:
                        if st.button("Sim, excluir permanentemente", key=f"confirm_del_cat_{cat}", type="primary"):
                            st.session_state.gerenciador.remover_categoria(cat)
                            st.session_state.gerenciador.salvar_dados()
                            st.toast(f"Categoria '{cat}' removida!")
                            st.session_state.categoria_para_excluir = None
                            st.rerun()

                    with col_cancel:
                        if st.button("Cancelar", key=f"cancel_del_cat_{cat}"):
                            st.session_state.categoria_para_excluir = None
                            st.rerun()

    with col_cat2:
        st.write("Nova categoria")
        nova_cat = st.text_input("Nome da categoria", key="nova_categoria_input")
        if st.button("Adicionar categoria", key="add_categoria_btn"):
            nome = (nova_cat or "").strip()
            if not nome:
                st.warning("Informe um nome para a categoria.")
            elif nome in st.session_state.gerenciador.categorias:
                st.info(f"A categoria '{nome}' já existe.")
            else:
                st.session_state.gerenciador.adicionar_categoria(nome)
                st.session_state.gerenciador.salvar_dados()
                st.toast(f"Categoria '{nome}' adicionada!")
                st.rerun()

    st.divider()
    st.subheader("Gerenciar TAGs")
    st.caption("TAGs são opcionais e servem para organizar transações e compras por projetos, viagens, eventos, etc.")

    col_tag1, col_tag2 = st.columns([3, 2])

    with col_tag1:
        st.write("TAGs existentes:")
        tags = st.session_state.gerenciador.tags

        if not tags:
            st.info("Nenhuma TAG cadastrada.")
        else:
            for tag in tags:
                tag_col1, tag_col2 = st.columns([4, 1])
                tag_col1.write(f"🏷️ {tag}")

                if tag_col2.button("🗑️", key=f"del_tag_{tag}", help=f"Excluir TAG '{tag}'"):
                    st.session_state.tag_para_excluir = tag
                    st.rerun()

                if st.session_state.get("tag_para_excluir") == tag:
                    st.warning(f"ATENÇÃO: Tem certeza que deseja excluir a TAG '{tag}'?")
                    col_confirm, col_cancel, _ = st.columns([1, 1, 3])

                    with col_confirm:
                        if st.button("Sim, excluir", key=f"confirm_del_tag_{tag}", type="primary"):
                            st.session_state.gerenciador.remover_tag(tag)
                            st.session_state.gerenciador.salvar_dados()
                            st.toast(f"TAG '{tag}' removida!")
                            st.session_state.tag_para_excluir = None
                            st.rerun()

                    with col_cancel:
                        if st.button("Cancelar", key=f"cancel_del_tag_{tag}"):
                            st.session_state.tag_para_excluir = None
                            st.rerun()

    with col_tag2:
        st.write("Nova TAG")
        nova_tag = st.text_input("Nome da TAG", key="nova_tag_input", placeholder="Ex: Viagem 2025")
        if st.button("Adicionar TAG", key="add_tag_btn"):
            nome = (nova_tag or "").strip()
            if not nome:
                st.warning("Informe um nome para a TAG.")
            elif nome in st.session_state.gerenciador.tags:
                st.info(f"A TAG '{nome}' já existe.")
            else:
                st.session_state.gerenciador.adicionar_tag(nome)
                st.session_state.gerenciador.salvar_dados()
                st.toast(f"TAG '{nome}' adicionada!")
                st.rerun()


    st.divider()
    st.subheader("Gerenciar Fornecedores")
    st.caption("Cadastre os fornecedores que você utiliza com frequência para facilitar o lançamento de compras.")


    # === IMPORTAÇÃO VIA EXCEL ===
    with st.expander("📤 Importar Fornecedores via Excel"):
        st.write("**Como usar:**")
        st.write("1. Prepare um arquivo Excel (.xlsx ou .csv) com os fornecedores")
        st.write("2. Os fornecedores devem estar na **primeira coluna**")
        st.write("3. Pode ter cabeçalho ou não (será ignorado se for texto)")
        
        arquivo_upload = st.file_uploader(
            "Selecione o arquivo Excel",
            type=["xlsx", "xls", "csv"],
            key="upload_fornecedores"
        )
        
        if arquivo_upload is not None:
            try:
                import pandas as pd
                
                # Lê o arquivo
                if arquivo_upload.name.endswith('.csv'):
                    df = pd.read_csv(arquivo_upload, header=None)
                else:
                    df = pd.read_excel(arquivo_upload, header=None)
                
                # Pega a primeira coluna
                fornecedores_lista = df.iloc[:, 0].dropna().astype(str).tolist()
                
                # Remove possíveis cabeçalhos (linhas que parecem títulos)
                fornecedores_lista = [f for f in fornecedores_lista if f.strip() and not f.lower() in ['fornecedor', 'fornecedores', 'nome', 'descrição', 'descricao']]
                
                st.write(f"**📋 {len(fornecedores_lista)} fornecedores encontrados no arquivo:**")
                
                # Mostra preview
                preview = fornecedores_lista[:10]
                for f in preview:
                    st.text(f"• {f}")
                
                if len(fornecedores_lista) > 10:
                    st.caption(f"... e mais {len(fornecedores_lista) - 10} fornecedores")
                
                col_import, col_cancel = st.columns(2)
                
                with col_import:
                    if st.button("✅ Importar Todos", type="primary", use_container_width=True):
                        novos, duplicados = st.session_state.gerenciador.importar_fornecedores_de_lista(fornecedores_lista)
                        st.session_state.gerenciador.salvar_dados()
                        
                        if novos > 0:
                            st.success(f"✅ {novos} fornecedores importados com sucesso!")
                        if duplicados > 0:
                            st.info(f"ℹ️ {duplicados} fornecedores já existiam e foram ignorados.")
                        
                        st.rerun()
                
                with col_cancel:
                    if st.button("❌ Cancelar", use_container_width=True):
                        st.rerun()
                        
            except Exception as e:
                st.error(f"❌ Erro ao ler o arquivo: {str(e)}")
                st.info("Certifique-se de que o arquivo está no formato correto (Excel ou CSV).")
    
    st.divider()
    
    col_forn1, col_forn2 = st.columns([3, 2])
    
    with col_forn1:
        st.write("Fornecedores cadastrados:")
        fornecedores = st.session_state.gerenciador.fornecedores
    
        if not fornecedores:
            st.info("Nenhum fornecedor cadastrado.")
        else:
            for fornecedor in fornecedores:
                forn_col1, forn_col2 = st.columns([4, 1])
                forn_col1.write(f"🏪 {fornecedor}")
    
                if forn_col2.button("🗑️", key=f"del_forn_{fornecedor}", help=f"Excluir fornecedor '{fornecedor}'"):
                    st.session_state.fornecedor_para_excluir = fornecedor
                    st.rerun()
    
                if st.session_state.get("fornecedor_para_excluir") == fornecedor:
                    st.warning(f"ATENÇÃO: Tem certeza que deseja excluir o fornecedor '{fornecedor}'?")
                    col_confirm, col_cancel, _ = st.columns([1, 1, 3])
    
                    with col_confirm:
                        if st.button("Sim, excluir", key=f"confirm_del_forn_{fornecedor}", type="primary"):
                            st.session_state.gerenciador.remover_fornecedor(fornecedor)
                            st.session_state.gerenciador.salvar_dados()
                            st.toast(f"Fornecedor '{fornecedor}' removido!")
                            st.session_state.fornecedor_para_excluir = None
                            st.rerun()
    
                    with col_cancel:
                        if st.button("Cancelar", key=f"cancel_del_forn_{fornecedor}"):
                            st.session_state.fornecedor_para_excluir = None
                            st.rerun()
    
    with col_forn2:
        st.write("Novo fornecedor")
        novo_forn = st.text_input("Nome do fornecedor", key="novo_fornecedor_input", placeholder="Ex: Supermercado XYZ")
        if st.button("Adicionar fornecedor", key="add_fornecedor_btn"):
            nome = (novo_forn or "").strip()
            if not nome:
                st.warning("Informe um nome para o fornecedor.")
            elif nome in st.session_state.gerenciador.fornecedores:
                st.info(f"O fornecedor '{nome}' já existe.")
            else:
                st.session_state.gerenciador.adicionar_fornecedor(nome)
                st.session_state.gerenciador.salvar_dados()
                st.toast(f"Fornecedor '{nome}' adicionado!")
                st.rerun()


# --- GERENCIAR CONTAS (ARQUIVAR/DESARQUIVAR) ---  ← ADICIONE AQUI (LOGO APÓS)
with tab_gerenciar:
    st.header("📦 Gerenciar Contas")
    
    st.info("""
    💡 **Como funciona o arquivamento:**
    - Contas arquivadas não aparecem nos seletores de transações
    - O saldo e histórico são preservados
    - Você pode desarquivar a qualquer momento
    """)
    
    st.divider()
    
    col_ativas, col_arquivadas = st.columns(2)
    
    # === CONTAS ATIVAS ===
    with col_ativas:
        st.subheader("✅ Contas Ativas")
        
        contas_ativas = st.session_state.gerenciador.obter_contas_ativas()
        
        if not contas_ativas:
            st.info("Nenhuma conta ativa no momento.")
        else:
            for conta in contas_ativas:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        tipo_icon = "🏦" if isinstance(conta, ContaCorrente) else "📈"
                        st.text(f"{tipo_icon} {conta.nome}")
                    
                    with col2:
                        saldo_cor = "green" if conta.saldo >= 0 else "red"
                        st.markdown(f":{saldo_cor}[{formatar_moeda(conta.saldo)}]")
                    
                    with col3:
                        if st.button("📦", key=f"arquivar_{conta.id_conta}", help="Arquivar conta"):
                            if st.session_state.gerenciador.arquivar_conta(conta.id_conta):
                                st.toast(f"✅ '{conta.nome}' arquivada!")
                                st.rerun()
                            else:
                                st.error("Erro ao arquivar.")
                    
                    tipo_texto = "Conta Corrente" if isinstance(conta, ContaCorrente) else "Investimento"
                    st.caption(f"Tipo: {tipo_texto}")
                    st.divider()
    
    # === CONTAS ARQUIVADAS ===
    with col_arquivadas:
        st.subheader("📦 Contas Arquivadas")
        
        contas_arquivadas = st.session_state.gerenciador.obter_contas_arquivadas()
        
        if not contas_arquivadas:
            st.info("Nenhuma conta arquivada.")
        else:
            for conta in contas_arquivadas:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        tipo_icon = "🏦" if isinstance(conta, ContaCorrente) else "📈"
                        st.text(f"{tipo_icon} {conta.nome}")
                    
                    with col2:
                        st.text(formatar_moeda(conta.saldo))
                    
                    with col3:
                        if st.button("🔓", key=f"desarquivar_{conta.id_conta}", help="Desarquivar conta"):
                            if st.session_state.gerenciador.desarquivar_conta(conta.id_conta):
                                st.toast(f"✅ '{conta.nome}' desarquivada!")
                                st.rerun()
                            else:
                                st.error("Erro ao desarquivar.")
                    
                    tipo_texto = "Conta Corrente" if isinstance(conta, ContaCorrente) else "Investimento"
                    st.caption(f"Tipo: {tipo_texto}")
                    st.divider()
