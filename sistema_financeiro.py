import json
import os
import calendar
import time
from abc import ABC, abstractmethod
from uuid import uuid4
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dateutil.relativedelta import relativedelta
import yfinance as yf
from pycoingecko import CoinGeckoAPI


def parse_date_safe(value: Any, default: Optional[date] = None) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except Exception:
            pass
    return default if default is not None else date.today()


class Transacao:
    def __init__(
        self,
        id_conta: str,
        descricao: str,
        valor: float,
        tipo: str,
        data_transacao: date,
        categoria: str,
        observacao: str = "",
        tag: str = "",
        id_transacao: Optional[str] = None,
    ):
        self.id_transacao = id_transacao or str(uuid4())
        self.id_conta = id_conta
        self.descricao = descricao
        self.valor = float(valor)
        self.tipo = tipo
        self.data = data_transacao
        self.categoria = categoria
        self.observacao = observacao
        self.tag = tag

    def para_dict(self) -> Dict[str, Any]:
        return {
            "id_transacao": self.id_transacao,
            "id_conta": self.id_conta,
            "descricao": self.descricao,
            "valor": self.valor,
            "tipo": self.tipo,
            "data": self.data.isoformat(),
            "categoria": self.categoria,
            "observacao": self.observacao,
            "tag": self.tag,
        }


class Ativo:
    def __init__(
        self,
        ticker: str,
        quantidade: float,
        preco_medio: float,
        tipo_ativo: str = "Outro",
    ):
        self.ticker = ticker.upper()
        self.quantidade = float(quantidade)
        self.preco_medio = float(preco_medio)
        self.tipo_ativo = tipo_ativo

    @property
    def valor_total(self) -> float:
        return self.quantidade * self.preco_medio

    def para_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "quantidade": self.quantidade,
            "preco_medio": self.preco_medio,
            "tipo_ativo": self.tipo_ativo,
        }


class Conta(ABC):
    def __init__(self, nome: str, logo_url: str = "", id_conta: Optional[str] = None):
        self.id_conta = id_conta or str(uuid4())
        self.nome = nome
        self.logo_url = logo_url

    @abstractmethod
    def para_dict(self) -> Dict[str, Any]:
        ...

    def editar_nome(self, novo_nome: str) -> bool:
        if novo_nome and novo_nome != self.nome:
            self.nome = novo_nome
            return True
        return False

    def editar_logo_url(self, nova_url: str) -> bool:
        if nova_url != self.logo_url:
            self.logo_url = nova_url
            return True
        return False


class ContaCorrente(Conta):
    def __init__(
        self,
        nome: str,
        saldo: float = 0.0,
        limite_cheque_especial: float = 0.0,
        logo_url: str = "",
        id_conta: Optional[str] = None,
        arquivada: bool = False,
    ):
        super().__init__(nome=nome, logo_url=logo_url, id_conta=id_conta)
        self.saldo = float(saldo)
        self.limite_cheque_especial = float(limite_cheque_especial)
        self.arquivada = arquivada

    def editar_limite(self, novo: float) -> bool:
        novo = float(novo)
        if novo != self.limite_cheque_especial:
            self.limite_cheque_especial = novo
            return True
        return False

    def para_dict(self) -> Dict[str, Any]:
        return {
            "tipo": "ContaCorrente",
            "id_conta": self.id_conta,
            "nome": self.nome,
            "logo_url": self.logo_url,
            "saldo": self.saldo,
            "limite_cheque_especial": self.limite_cheque_especial,
            "arquivada": self.arquivada,
        }


class ContaInvestimento(Conta):
    def __init__(
        self,
        nome: str,
        logo_url: str = "",
        saldo_caixa: float = 0.0,
        ativos: Optional[List[Ativo]] = None,
        id_conta: Optional[str] = None,
        arquivada: bool = False,
    ):
        super().__init__(nome=nome, logo_url=logo_url, id_conta=id_conta)
        self.saldo_caixa = float(saldo_caixa)
        self.ativos: List[Ativo] = ativos or []
        self.arquivada = arquivada

    @property
    def valor_em_ativos(self) -> float:
        return sum(a.valor_total for a in self.ativos)

    @property
    def saldo(self) -> float:
        return self.saldo_caixa + self.valor_em_ativos

    def atualizar_ou_adicionar_ativo(
        self,
        ticker: str,
        quantidade: float,
        preco_medio: float,
        tipo_ativo: str = "Outro",
    ) -> None:
        ticker = ticker.upper()
        for a in self.ativos:
            if a.ticker == ticker and a.tipo_ativo == tipo_ativo:
                total_valor_antigo = a.preco_medio * a.quantidade
                total_valor_novo = preco_medio * quantidade
                nova_qtd = a.quantidade + quantidade
                if nova_qtd > 0:
                    a.preco_medio = (total_valor_antigo + total_valor_novo) / nova_qtd
                    a.quantidade = nova_qtd
                else:
                    a.quantidade = 0.0
                return
        self.ativos.append(Ativo(ticker, quantidade, preco_medio, tipo_ativo))

    def para_dict(self) -> Dict[str, Any]:
        return {
            "tipo": "ContaInvestimento",
            "id_conta": self.id_conta,
            "nome": self.nome,
            "logo_url": self.logo_url,
            "saldo_caixa": self.saldo_caixa,
            "ativos": [a.para_dict() for a in self.ativos],
             "arquivada": self.arquivada,
        }


class CartaoCredito:
    def __init__(
        self,
        nome: str,
        logo_url: str = "",
        dia_fechamento: int = 28,
        dia_vencimento: int = 10,
        id_cartao: Optional[str] = None,
        fechamentos_customizados: Optional[Dict[str, int]] = None,
    ):
        self.id_cartao = id_cartao or str(uuid4())
        self.nome = nome
        self.logo_url = logo_url
        self.dia_fechamento = int(dia_fechamento)
        self.dia_vencimento = int(dia_vencimento)
        self.fechamentos_customizados = fechamentos_customizados if fechamentos_customizados is not None else {}

    def para_dict(self) -> Dict[str, Any]:
        return {
            "id_cartao": self.id_cartao,
            "nome": self.nome,
            "logo_url": self.logo_url,
            "dia_fechamento": self.dia_fechamento,
            "dia_vencimento": self.dia_vencimento,
            "fechamentos_customizados": self.fechamentos_customizados,  
        }

    def editar_nome(self, novo_nome: str) -> bool:
        if novo_nome and novo_nome != self.nome:
            self.nome = novo_nome
            return True
        return False

    def editar_logo_url(self, nova_url: str) -> bool:
        if nova_url != self.logo_url:
            self.logo_url = nova_url
            return True
        return False


class CompraCartao:
    def __init__(
        self,
        id_cartao: str,
        descricao: str,
        valor: float,
        data_compra: date,  # data de vencimento da parcela
        categoria: str,
        total_parcelas: int = 1,
        parcela_atual: int = 1,
        id_compra_original: Optional[str] = None,
        observacao: str = "",
        id_compra: Optional[str] = None,
        id_fatura: Optional[str] = None,
        data_compra_real: Optional[date] = None,  # data real da compra
        tag: str=""
    ):    
        self.id_compra = id_compra or str(uuid4())
        self.id_cartao = id_cartao
        self.descricao = descricao
        self.valor = float(valor)
        self.data_compra = data_compra
        self.categoria = categoria
        self.total_parcelas = int(total_parcelas)
        self.parcela_atual = int(parcela_atual)
        self.id_compra_original = id_compra_original or self.id_compra
        self.observacao = observacao
        self.tag = tag
        self.id_fatura = id_fatura
        self.data_compra_real = data_compra_real or self.data_compra

    def para_dict(self) -> Dict[str, Any]:
        return {
            "id_compra": self.id_compra,
            "id_cartao": self.id_cartao,
            "descricao": self.descricao,
            "valor": self.valor,
            "data_compra": self.data_compra.isoformat(),          # vencimento
            "categoria": self.categoria,
            "total_parcelas": self.total_parcelas,
            "parcela_atual": self.parcela_atual,
            "id_compra_original": self.id_compra_original,
            "observacao": self.observacao,
            "tag": self.tag,
            "id_fatura": self.id_fatura,
            "data_compra_real": self.data_compra_real.isoformat(),  # real
        }


class Fatura:
    def __init__(
        self,
        id_cartao: str,
        data_fechamento: date,
        data_vencimento: date,
        valor_total: float,
        status: str = "Fechada",
        id_fatura: Optional[str] = None,
    ):
        self.id_fatura = id_fatura or str(uuid4())
        self.id_cartao = id_cartao
        self.data_fechamento = data_fechamento
        self.data_vencimento = data_vencimento
        self.valor_total = float(valor_total)
        self.status = status

    def para_dict(self) -> Dict[str, Any]:
        return {
            "id_fatura": self.id_fatura,
            "id_cartao": self.id_cartao,
            "data_fechamento": self.data_fechamento.isoformat(),
            "data_vencimento": self.data_vencimento.isoformat(),
            "valor_total": self.valor_total,
            "status": self.status,
        }


class GerenciadorContas:
    def __init__(self, caminho_arquivo: str = "dados.json"):
        self.caminho_arquivo = caminho_arquivo
        self.contas: List[Conta] = []
        self.transacoes: List[Transacao] = []
        self.cartoes_credito: List[CartaoCredito] = []
        self.compras_cartao: List[CompraCartao] = []
        self.faturas: List[Fatura] = []
        self.categorias: List[str] = [
            "Alimentação",
            "Transporte",
            "Moradia",
            "Saúde",
            "Lazer",
            "Educação",
            "Impostos",
            "Investimentos",
            "Outros",
        ]
        self.tags: List[str] = []  
        # Cache de cotações
        self._cotacoes_cache: Dict[str, Dict[str, float]] = {}
        self._cotacoes_ttl: int = 60  # segundos
        self._cg = CoinGeckoAPI()  # Cliente CoinGecko
        self._cg_cache_ids: Dict[str, str] = {}  # Cache de ticker -> coin_id
        self.carregar_dados()

    # ------------------------
    # Persistência
    # ------------------------

    def salvar_dados(self) -> None:
        data = {
            "contas": [c.para_dict() for c in self.contas],
            "transacoes": [t.para_dict() for t in self.transacoes],
            "cartoes_credito": [c.para_dict() for c in self.cartoes_credito],
            "compras_cartao": [c.para_dict() for c in self.compras_cartao],
            "faturas": [f.para_dict() for f in self.faturas],
            "categorias": self.categorias,
            "tags": self.tags, 
        }
        try:
            # Cria o diretório se não existir
            diretorio = os.path.dirname(self.caminho_arquivo)
            if diretorio and not os.path.exists(diretorio):
                os.makedirs(diretorio)
            
            # Salva o arquivo
            with open(self.caminho_arquivo, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"✅ Dados salvos com sucesso em: {os.path.abspath(self.caminho_arquivo)}")
        except Exception as e:
            print(f"❌ Erro ao salvar dados: {e}")
            import traceback
            traceback.print_exc()






    
    

    def carregar_dados(self) -> None:
        if not os.path.exists(self.caminho_arquivo):
            return
        try:
            with open(self.caminho_arquivo, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        self.contas = []
        for c in data.get("contas", []):
            tipo = c.get("tipo", "ContaCorrente")
            if tipo == "ContaCorrente":
                conta = ContaCorrente(
                    nome=c.get("nome", "Sem Nome"),
                    saldo=float(c.get("saldo", 0.0)),
                    limite_cheque_especial=float(c.get("limite_cheque_especial", 0.0)),
                    logo_url=c.get("logo_url", ""),
                    id_conta=c.get("id_conta"),
                    arquivada=c.get("arquivada", False),
                )
            else:
                ativos_lidos: List[Ativo] = []
                for a in c.get("ativos", []):
                    ativos_lidos.append(
                        Ativo(
                            ticker=a.get("ticker", ""),
                            quantidade=float(a.get("quantidade", 0.0)),
                            preco_medio=float(a.get("preco_medio", 0.0)),
                            tipo_ativo=a.get("tipo_ativo", "Outro"),
                        )
                    )
                conta = ContaInvestimento(
                    nome=c.get("nome", "Sem Nome"),
                    logo_url=c.get("logo_url", ""),
                    saldo_caixa=float(c.get("saldo_caixa", 0.0)),
                    ativos=ativos_lidos,
                    id_conta=c.get("id_conta"),
                    arquivada=c.get("arquivada", False),
                )
            self.contas.append(conta)

        self.transacoes = []
        for t in data.get("transacoes", []):
            self.transacoes.append(
                Transacao(
                    id_conta=t.get("id_conta", ""),
                    descricao=t.get("descricao", ""),
                    valor=float(t.get("valor", 0.0)),
                    tipo=t.get("tipo", "Despesa"),
                    data_transacao=parse_date_safe(t.get("data"), date.today()),
                    categoria=t.get("categoria", "Outros"),
                    observacao=t.get("observacao", ""),
                    tag=t.get("tag", ""),
                    id_transacao=t.get("id_transacao"),
                )
            )

        self.cartoes_credito = []
        for cc in data.get("cartoes_credito", []):
            self.cartoes_credito.append(
                CartaoCredito(
                    nome=cc.get("nome", "Cartão"),
                    logo_url=cc.get("logo_url", ""),
                    dia_fechamento=int(cc.get("dia_fechamento", 28)),
                    dia_vencimento=int(cc.get("dia_vencimento", 10)),
                    id_cartao=cc.get("id_cartao"),
                    fechamentos_customizados=cc.get("fechamentos_customizados", {}), 
                )
            )

        self.compras_cartao = []
        for c in data.get("compras_cartao", []):
            data_venc = parse_date_safe(c.get("data_compra"), date.today())
            data_real = parse_date_safe(c.get("data_compra_real"), data_venc)
            self.compras_cartao.append(
                CompraCartao(
                    id_compra=c.get("id_compra"),
                    id_cartao=c.get("id_cartao", ""),
                    descricao=c.get("descricao", ""),
                    valor=float(c.get("valor", 0.0)),
                    data_compra=data_venc,  # vencimento
                    categoria=c.get("categoria", "Outros"),
                    total_parcelas=int(c.get("total_parcelas", 1)),
                    parcela_atual=int(c.get("parcela_atual", 1)),
                    id_compra_original=c.get("id_compra_original"),
                    observacao=c.get("observacao", ""),
                    tag=c.get("tag", ""),
                    id_fatura=c.get("id_fatura"),
                    data_compra_real=data_real,  # real
                )
            )

        self.faturas = []
        for f in data.get("faturas", []):
            self.faturas.append(
                Fatura(
                    id_fatura=f.get("id_fatura"),
                    id_cartao=f.get("id_cartao", ""),
                    data_fechamento=parse_date_safe(f.get("data_fechamento"), date.today()),
                    data_vencimento=parse_date_safe(f.get("data_vencimento"), date.today()),
                    valor_total=float(f.get("valor_total", 0.0)),
                    status=f.get("status", "Fechada"),
                )
            )

        cats = data.get("categorias")
        if isinstance(cats, list) and cats:
            self.categorias = cats

        self.tags = data.get("tags", [])

    # ------------------------
    # Utilidades de Ciclos (Cartões)
    # ------------------------

    def _calcular_mes_ano_fatura_aberta(self, cartao: CartaoCredito, data_ref: Optional[date] = None) -> Tuple[int, int]:
        hoje = data_ref or date.today()
        try:
            fechamento_atual = date(hoje.year, hoje.month, cartao.dia_fechamento)
        except ValueError:
            ultimo = calendar.monthrange(hoje.year, hoje.month)[1]
            fechamento_atual = date(hoje.year, hoje.month, ultimo)

        try:
            base_venc = date(hoje.year, hoje.month, cartao.dia_vencimento)
        except ValueError:
            ultimo = calendar.monthrange(hoje.year, hoje.month)[1]
            base_venc = date(hoje.year, hoje.month, ultimo)

        if hoje <= fechamento_atual:
            vencimento = base_venc + relativedelta(months=1)
        else:
            vencimento = base_venc + relativedelta(months=2)

        return vencimento.year, vencimento.month

    def ciclos_abertos_unicos(self, id_cartao: str) -> List[Tuple[int, int]]:
        ciclos = {
            (c.data_compra.year, c.data_compra.month)
            for c in self.compras_cartao
            if c.id_cartao == id_cartao and c.id_fatura is None
        }
        return sorted(list(ciclos))

    def ciclo_aberto_mais_antigo(self, id_cartao: str) -> Optional[Tuple[int, int]]:
        ciclos = self.ciclos_abertos_unicos(id_cartao)
        return ciclos[0] if ciclos else None

    def listar_ciclos_navegacao(self, id_cartao: str, data_ref: Optional[date] = None) -> List[Tuple[int, int]]:
        cartao = self.buscar_cartao_por_id(id_cartao)
        if not cartao:
            return []
        base = self.ciclos_abertos_unicos(id_cartao)
        ano_corr, mes_corr = self._calcular_mes_ano_fatura_aberta(cartao, data_ref)
        if (ano_corr, mes_corr) not in base:
            base.append((ano_corr, mes_corr))
        base = sorted(base)
        return base

    def obter_lancamentos_do_ciclo(self, id_cartao: str, ano: int, mes: int) -> List[CompraCartao]:
        return [
            c for c in self.compras_cartao
            if c.id_cartao == id_cartao and c.id_fatura is None
            and c.data_compra.year == ano and c.data_compra.month == mes
        ]

    def obter_lancamentos_futuros_desde(self, id_cartao: str, ano: int, mes: int) -> List[CompraCartao]:
        return [
            c for c in self.compras_cartao
            if c.id_cartao == id_cartao and c.id_fatura is None
            and (c.data_compra.year, c.data_compra.month) > (ano, mes)
        ]

    # ------------------------
    # Operações de Contas e Ativos
    # ------------------------

    def adicionar_conta(self, conta: Conta) -> None:
        self.contas.append(conta)

    def remover_conta(self, id_conta: str) -> bool:
        conta = next((c for c in self.contas if c.id_conta == id_conta), None)
        if not conta:
            return False
        self.transacoes = [t for t in self.transacoes if t.id_conta != id_conta]
        self.contas = [c for c in self.contas if c.id_conta != id_conta]
        return True

    def remover_transacao(self, id_transacao: str) -> bool:
        """
        Remove uma transação pelo ID e reverte seus efeitos no saldo da conta.
        Se a transação for uma compra de investimento, reverte proporcionalmente os ativos.
        """
        transacao = next((t for t in self.transacoes if t.id_transacao == id_transacao), None)
        if not transacao:
            return False
        
        conta = self.buscar_conta_por_id(transacao.id_conta)
        if not conta:
            return False
        
        if transacao.tipo == "Receita":
            if isinstance(conta, ContaCorrente):
                conta.saldo -= transacao.valor
            elif isinstance(conta, ContaInvestimento):
                conta.saldo_caixa -= transacao.valor
        
        elif transacao.tipo == "Despesa":
            if isinstance(conta, ContaCorrente):
                conta.saldo += transacao.valor
            elif isinstance(conta, ContaInvestimento):
                if transacao.categoria == "Investimentos" and "Compra de" in transacao.descricao:
                    ticker_desc = transacao.descricao.replace("Compra de ", "").strip()
                    
                    ativo = None
                    for a in conta.ativos:
                        if a.ticker.upper() == ticker_desc.upper():
                            ativo = a
                            break
                    
                    if ativo:
                        quantidade_comprada = transacao.valor / ativo.preco_medio
                        ativo.quantidade -= quantidade_comprada
                        
                        if ativo.quantidade <= 0.000001:
                            conta.ativos = [a for a in conta.ativos if a.ticker.upper() != ticker_desc.upper()]
                        else:
                            for i, a in enumerate(conta.ativos):
                                if a.ticker.upper() == ticker_desc.upper():
                                    conta.ativos[i] = ativo
                                    break
                
                conta.saldo_caixa += transacao.valor
        
        self.transacoes = [t for t in self.transacoes if t.id_transacao != id_transacao]
        return True



    def vender_ativo(self, id_conta: str, ticker: str, quantidade: float, preco_venda: float, data_venda: str, observacao: str = "") -> tuple[bool, str]:
        """
        Vende uma quantidade de um ativo e registra a transação com lucro/prejuízo.
        Retorna (sucesso: bool, mensagem: str)
        """
        conta = self.buscar_conta_por_id(id_conta)
        if not conta or not isinstance(conta, ContaInvestimento):
            return False, "Conta de investimento não encontrada."
        
        # Busca o ativo na conta
        ativo = next((a for a in conta.ativos if a.ticker == ticker), None)
        if not ativo:
            return False, f"Ativo {ticker} não encontrado na conta."
        
        # Verifica se há quantidade suficiente
        if ativo.quantidade < quantidade:
            return False, f"Quantidade insuficiente. Você tem {ativo.quantidade:.6f} de {ticker}."
        
        # Calcula o valor da venda
        valor_venda = quantidade * preco_venda
        
        # Calcula o custo médio dessa quantidade vendida
        custo_medio = quantidade * ativo.preco_medio
        
        # Calcula o lucro/prejuízo
        lucro_prejuizo = valor_venda - custo_medio
        lucro_prejuizo_pct = (lucro_prejuizo / custo_medio * 100) if custo_medio > 0 else 0
        
        # Monta a descrição com P/L
        if lucro_prejuizo >= 0:
            descricao = f"Venda de {ticker} | Lucro: R$ {lucro_prejuizo:.2f} ({lucro_prejuizo_pct:+.2f}%)"
        else:
            descricao = f"Venda de {ticker} | Prejuízo: R$ {abs(lucro_prejuizo):.2f} ({lucro_prejuizo_pct:.2f}%)"
        
        # Adiciona observação se fornecida
        if observacao:
            descricao += f" | {observacao}"
        
        # Remove a quantidade do ativo
        ativo.quantidade -= quantidade
        
        # Se zerou, remove o ativo da lista
        if ativo.quantidade <= 0:
            conta.ativos = [a for a in conta.ativos if a.ticker != ticker]
        
        # Adiciona o valor da venda ao saldo em caixa
        conta.saldo_caixa += valor_venda
        
        # Converte a string de data para objeto date
        data_venda_obj = datetime.strptime(data_venda, "%Y-%m-%d").date()
        
        # Registra a transação de venda com a ordem correta de parâmetros
        nova_transacao = Transacao(
            id_conta=id_conta,
            descricao=descricao,
            valor=valor_venda,
            tipo="Receita",
            data_transacao=data_venda_obj,
            categoria="Venda de Investimento",
        )
        self.transacoes.append(nova_transacao)
        
        return True, f"Venda registrada com sucesso! {descricao}"

    def buscar_conta_por_id(self, id_conta: str) -> Optional[Conta]:
        return next((c for c in self.contas if c.id_conta == id_conta), None)

    def registrar_transacao(
        self,
        id_conta: str,
        descricao: str,
        valor: float,
        tipo: str,
        data_transacao: date,
        categoria: str,
        observacao: str = "",
        tag: str = "",
    ) -> bool:
        conta = self.buscar_conta_por_id(id_conta)
        if not conta:
            return False

        if tipo == "Receita":
            if isinstance(conta, ContaCorrente):
                conta.saldo += float(valor)
            elif isinstance(conta, ContaInvestimento):
                conta.saldo_caixa += float(valor)
        elif tipo == "Despesa":
            if isinstance(conta, ContaCorrente):
                if conta.saldo + conta.limite_cheque_especial < float(valor):
                    return False
                conta.saldo -= float(valor)
            elif isinstance(conta, ContaInvestimento):
                if conta.saldo_caixa < float(valor):
                    return False
                conta.saldo_caixa -= float(valor)

        self.transacoes.append(
            Transacao(
                id_conta=id_conta,
                descricao=descricao,
                valor=float(valor),
                tipo=tipo,
                data_transacao=data_transacao,
                categoria=categoria,
                observacao=observacao,
                tag=tag,
            )
        )
        return True

    def realizar_transferencia(self, id_origem: str, id_destino: str, valor: float) -> bool:
        if id_origem == id_destino:
            return False
        valor = float(valor)
        conta_origem = self.buscar_conta_por_id(id_origem)
        conta_destino = self.buscar_conta_por_id(id_destino)
        if not conta_origem or not conta_destino:
            return False

        if isinstance(conta_origem, ContaCorrente):
            if conta_origem.saldo + conta_origem.limite_cheque_especial < valor:
                return False
            conta_origem.saldo -= valor
        elif isinstance(conta_origem, ContaInvestimento):
            if conta_origem.saldo_caixa < valor:
                return False
            conta_origem.saldo_caixa -= valor

        if isinstance(conta_destino, ContaCorrente):
            conta_destino.saldo += valor
        elif isinstance(conta_destino, ContaInvestimento):
            conta_destino.saldo_caixa += valor

        hoje = date.today()
        self.transacoes.append(
            Transacao(
                id_conta=id_origem,
                descricao=f"Transferência para {conta_destino.nome}",
                valor=valor,
                tipo="Despesa",
                data_transacao=hoje,
                categoria="Transferência",
            )
        )
        self.transacoes.append(
            Transacao(
                id_conta=id_destino,
                descricao=f"Transferência de {conta_origem.nome}",
                valor=valor,
                tipo="Receita",
                data_transacao=hoje,
                categoria="Transferência",
            )
        )
        return True

    def comprar_ativo(
        self,
        id_conta_destino: str,
        ticker: str,
        quantidade: float,
        preco_unitario: float,
        tipo_ativo: str,
        data_compra: date,
    ) -> bool:
        conta = self.buscar_conta_por_id(id_conta_destino)
        if not conta or not isinstance(conta, ContaInvestimento):
            return False
        custo = float(quantidade) * float(preco_unitario)
        if conta.saldo_caixa < custo:
            return False
        conta.saldo_caixa -= custo
        conta.atualizar_ou_adicionar_ativo(
            ticker=ticker,
            quantidade=float(quantidade),
            preco_medio=float(preco_unitario),
            tipo_ativo=tipo_ativo,
        )
        self.transacoes.append(
            Transacao(
                id_conta=conta.id_conta,
                descricao=f"Compra de {ticker}",
                valor=custo,
                tipo="Despesa",
                data_transacao=data_compra,
                categoria="Investimentos",
            )
        )
        return True

    # ------------------------
    # Cotações e Posição (Investimentos)
    # ------------------------

    def _agora_epoch(self) -> float:
        return time.time()

    def _obter_coingecko_id(self, ticker: str) -> Optional[str]:
        """
        Mapeia ticker de cripto para CoinGecko ID.
        Ex: BTC -> bitcoin, ETH -> ethereum, PEPE -> pepe
        """
        ticker_upper = ticker.upper().strip()
        
        # Cache para evitar múltiplas consultas
        if ticker_upper in self._cg_cache_ids:
            return self._cg_cache_ids[ticker_upper]
        
        # Mapeamento manual dos mais populares (performance)
        mapeamento_comum = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "BNB": "binancecoin",
            "XRP": "ripple",
            "ADA": "cardano",
            "DOGE": "dogecoin",
            "SOL": "solana",
            "DOT": "polkadot",
            "MATIC": "matic-network",
            "SHIB": "shiba-inu",
            "PEPE": "pepe",
            "AVAX": "avalanche-2",
            "LINK": "chainlink",
            "UNI": "uniswap",
            "LTC": "litecoin",
            "ATOM": "cosmos",
            "XLM": "stellar",
            "USDT": "tether",
            "USDC": "usd-coin",
        }
        
        if ticker_upper in mapeamento_comum:
            coin_id = mapeamento_comum[ticker_upper]
            self._cg_cache_ids[ticker_upper] = coin_id
            return coin_id
        
        # Busca dinâmica (fallback para criptos não mapeadas)
        try:
            lista = self._cg.get_coins_list()
            ticker_lower = ticker.lower()
            for coin in lista:
                if coin["symbol"].lower() == ticker_lower:
                    coin_id = coin["id"]
                    self._cg_cache_ids[ticker_upper] = coin_id
                    return coin_id
        except Exception:
            pass
        
        return None    
  
    def _obter_preco_coingecko(self, ticker: str) -> float:
        """
        Busca preço atual da cripto no CoinGecko (em BRL).
        """
        coin_id = self._obter_coingecko_id(ticker)
        if not coin_id:
            raise ValueError(f"Cripto '{ticker}' não encontrada no CoinGecko")
        
        try:
            data = self._cg.get_price(ids=coin_id, vs_currencies="brl")
            preco_brl = data[coin_id]["brl"]
            if preco_brl and float(preco_brl) > 0:
                return float(preco_brl)
            raise ValueError(f"Preço inválido para {ticker}")
        except Exception as e:
            raise ValueError(f"Erro ao buscar cotação de {ticker}: {str(e)}")

    def _obter_preco_tesouro(self, ticker: str) -> Optional[float]:
        """
        Obtém o preço unitário de um título do Tesouro Direto via API oficial.
        Usa cache local para evitar downloads repetidos.
        """
        try:
            import requests
            import re
            from pathlib import Path
            
            cache_dir = Path("cache_tesouro")
            cache_dir.mkdir(exist_ok=True)
            cache_file = cache_dir / "precos_tesouro.csv"
            cache_ttl_horas = 4
            
            usar_cache = False
            if cache_file.exists():
                import time
                idade_cache = time.time() - cache_file.stat().st_mtime
                idade_cache_horas = idade_cache / 3600
                
                if idade_cache_horas < cache_ttl_horas:
                    usar_cache = True
            
            if not usar_cache:
                url = "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv"
                response = requests.get(url, timeout=30)
                
                if response.status_code != 200:
                    if cache_file.exists():
                        usar_cache = True
                    else:
                        return None
                else:
                    cache_file.write_text(response.text, encoding='utf-8')
                    texto_csv = response.text
            
            if usar_cache:
                texto_csv = cache_file.read_text(encoding='utf-8')
            
            linhas = texto_csv.strip().split('\n')
            if len(linhas) < 2:
                return None
            
            ano_match = re.search(r'(\d{4})', ticker)
            ano_busca = ano_match.group(1) if ano_match else None
            
            def normalizar(texto):
                texto = texto.upper().strip()
                texto = re.sub(r'\s+', ' ', texto)
                texto = texto.replace('Á', 'A').replace('É', 'E').replace('Í', 'I')
                texto = texto.replace('Ó', 'O').replace('Ú', 'U').replace('Ã', 'A')
                texto = texto.replace('+', '')
                return texto
            
            ticker_normalizado = normalizar(ticker)
            ultimas_cotacoes = {}
            
            for linha in linhas[1:]:
                campos = linha.split(';')
                if len(campos) < 8:
                    continue
                
                tipo_titulo = campos[0].strip()
                data_vencimento = campos[1].strip()
                data_base = campos[2].strip()
                pu_venda = campos[6].strip()
                
                ano_titulo = None
                if '/' in data_vencimento:
                    partes = data_vencimento.split('/')
                    if len(partes) == 3 and len(partes[2]) == 4:
                        ano_titulo = partes[2]
                
                if ano_titulo:
                    chave_titulo = f"{tipo_titulo}_{data_vencimento}"
                    ultimas_cotacoes[chave_titulo] = {
                        'data': data_base,
                        'tipo': tipo_titulo,
                        'vencimento': data_vencimento,
                        'pu_venda': pu_venda,
                        'ano': ano_titulo
                    }
            
            for chave, dados in ultimas_cotacoes.items():
                tipo_titulo = dados['tipo']
                ano_titulo = dados['ano']
                pu_venda = dados['pu_venda']
                
                if ano_busca and ano_titulo == ano_busca:
                    nome_titulo = f"{tipo_titulo} {ano_titulo}"
                    nome_titulo_normalizado = normalizar(nome_titulo)
                    
                    match_encontrado = False
                    
                    if "RENDA" in ticker_normalizado and "RENDA" in nome_titulo_normalizado:
                        match_encontrado = True
                    elif "SELIC" in ticker_normalizado and "SELIC" in nome_titulo_normalizado:
                        match_encontrado = True
                    elif "IPCA" in ticker_normalizado and "IPCA" in nome_titulo_normalizado:
                        match_encontrado = True
                    elif "PREFIXADO" in ticker_normalizado and "PREFIXADO" in nome_titulo_normalizado:
                        match_encontrado = True
                    elif "EDUCA" in ticker_normalizado and "EDUCA" in nome_titulo_normalizado:
                        match_encontrado = True
                    
                    if match_encontrado:
                        try:
                            preco = float(pu_venda.replace(',', '.'))
                            return preco
                        except ValueError:
                            continue
            
            return None
        
        except Exception:
            return None
            
    def _normalizar_ticker(self, ticker: str, tipo_ativo: str) -> str:
        t = (ticker or "").upper().strip()
        if tipo_ativo in ("Ação BR", "FII"):
            if not t.endswith(".SA"):
                t = f"{t}.SA"
        elif tipo_ativo == "Cripto":
            if not t.endswith("-USD"):
                t = f"{t}-USD"
        return t

    def _obter_preco_yf(self, symbol: str) -> float:
        tk = yf.Ticker(symbol)

        try:
            fi = getattr(tk, "fast_info", None)
            if fi:
                last = fi.get("last_price") or fi.get("lastPrice")
                if last is None:
                    last = fi.get("last_price")
                if last is not None and float(last) > 0:
                    return float(last)
        except Exception:
            pass

        try:
            hist = tk.history(period="1d")
            if hist is not None and not hist.empty:
                last = hist["Close"].iloc[-1]
                if last is not None and float(last) > 0:
                    return float(last)
        except Exception:
            pass

        try:
            info = tk.info or {}
            last = info.get("regularMarketPrice")
            if last is not None and float(last) > 0:
                return float(last)
        except Exception:
            pass

        raise ValueError(f"Cotação indisponível para {symbol}")

    
    def obter_preco_atual(self, ticker: str, tipo_ativo: str) -> Optional[float]:
        """
        Retorna o preço atual (em BRL) de um ativo.
        - Tesouro Direto: usa API do Tesouro Nacional
        - Criptomoedas: usa CoinGecko
        - Ações EUA: usa yfinance com conversão USD→BRL
        - Ações BR/FII: usa yfinance
        """
        try:
            # Tesouro Direto - API oficial
            if tipo_ativo == "Tesouro Direto":
                cache_key = f"TD_{ticker.upper()}"
                now = self._agora_epoch()
                cached = self._cotacoes_cache.get(cache_key)
                if cached and (now - cached.get("ts", 0) <= self._cotacoes_ttl):
                    return cached.get("preco")
                
                preco = self._obter_preco_tesouro(ticker)
                if preco:
                    self._cotacoes_cache[cache_key] = {"preco": preco, "ts": now}
                return preco
            
            # Criptomoedas - CoinGecko
            if tipo_ativo == "Cripto":
                cache_key = f"CG_{ticker.upper()}"
                now = self._agora_epoch()
                cached = self._cotacoes_cache.get(cache_key)
                if cached and (now - cached.get("ts", 0) <= self._cotacoes_ttl):
                    return cached.get("preco")
                
                try:
                    preco = self._obter_preco_coingecko(ticker)
                    self._cotacoes_cache[cache_key] = {"preco": preco, "ts": now}
                    return preco
                except Exception:
                    return None
            
            # Ações e FIIs - yfinance (com normalização)
            symbol = self._normalizar_ticker(ticker, tipo_ativo)
            now = self._agora_epoch()
            cached = self._cotacoes_cache.get(symbol)
            if cached and (now - cached.get("ts", 0) <= self._cotacoes_ttl):
                return cached.get("preco")

            try:
                preco = self._obter_preco_yf(symbol)
                self._cotacoes_cache[symbol] = {"preco": preco, "ts": now}
                return preco
            except Exception:
                return None
        
        except Exception as e:
            print(f"Erro ao obter preço de {ticker} ({tipo_ativo}): {e}")
            return None
    
    def _obter_preco_atual_seguro(self, ticker: str) -> float:
        # Obtém o preço atual do ticker com cache. Fallback via yfinance; retorna 0.0 em erro.
        try:
            if not hasattr(self, "_cotacoes_cache"):
                self._cotacoes_cache = {}

            cache_key = f"TICKER_{ticker}"
            if cache_key in self._cotacoes_cache and self._cotacoes_cache[cache_key] is not None:
                return float(self._cotacoes_cache[cache_key])

            preco = None

            # Se existir método oficial no backend, use-o
            if hasattr(self, "obter_preco_atual") and callable(getattr(self, "obter_preco_atual")):
                try:
                    preco = float(self.obter_preco_atual(ticker))
                except Exception:
                    preco = None

            # Fallback via yfinance
            if preco is None:
                tk = yf.Ticker(ticker)
                preco = tk.info.get("regularMarketPrice") or tk.info.get("previousClose")
                if preco is None:
                    hist = tk.history(period="5d", interval="1d")
                    if not hist.empty:
                        preco = float(hist["Close"].dropna().iloc[-1])

            preco_val = float(preco) if preco is not None else 0.0
            self._cotacoes_cache[cache_key] = preco_val
            return preco_val
        except Exception:
            return 0.0

    def _obter_fx_usd_brl(self) -> float:
        # Retorna o câmbio USD/BRL com cache (USDBRL=X). Fallback seguro: 1.0
        try:
            if not hasattr(self, "_cotacoes_cache"):
                self._cotacoes_cache = {}

            cache_key = "FX_USDBRL"
            if cache_key in self._cotacoes_cache and self._cotacoes_cache[cache_key] is not None:
                return float(self._cotacoes_cache[cache_key])

            ticker_fx = yf.Ticker("USDBRL=X")
            fx = ticker_fx.info.get("regularMarketPrice") or ticker_fx.info.get("previousClose")
            if fx is None:
                hist = ticker_fx.history(period="5d", interval="1d")
                fx = float(hist["Close"].dropna().iloc[-1]) if not hist.empty else None

            fx_val = float(fx) if fx is not None else None
            self._cotacoes_cache[cache_key] = fx_val
            return fx_val if fx_val is not None else 1.0
        except Exception:
            return 1.0

    def calcular_posicao_conta_investimento(self, conta_id: str) -> dict:
        """
        Calcula posição em BRL, convertendo USD→BRL quando necessário.
        Suporta: Ação BR, Ação EUA, FII, Cripto, Tesouro Direto.
        """
        conta = None
        for c in getattr(self, "contas", []):
            if getattr(c, "id_conta", None) == conta_id and hasattr(c, "ativos") and hasattr(c, "saldo_caixa"):
                conta = c
                break

        if conta is None:
            return {
                "saldo_caixa": 0.0,
                "total_valor_atual_ativos": 0.0,
                "patrimonio_atualizado": 0.0,
                "ativos": []
            }

        itens = []
        total_valor_atual_ativos = 0.0
        saldo_caixa = float(getattr(conta, "saldo_caixa", 0.0) or 0.0)

        for ativo in getattr(conta, "ativos", []):
            try:
                ticker = getattr(ativo, "ticker", "")
                tipo_ativo = getattr(ativo, "tipo_ativo", "")
                quantidade = float(getattr(ativo, "quantidade", 0.0) or 0.0)
                preco_medio_brl = float(getattr(ativo, "preco_medio", 0.0) or 0.0)

                preco_atual_brl = None
                
                if tipo_ativo == "Tesouro Direto":
                    preco_atual_brl = self.obter_preco_atual(ticker, tipo_ativo)
                    if preco_atual_brl is None:
                        preco_atual_brl = preco_medio_brl
                
                elif tipo_ativo == "Cripto":
                    preco_atual_brl = self.obter_preco_atual(ticker, tipo_ativo)
                    if preco_atual_brl is None:
                        preco_atual_brl = preco_medio_brl
                
                else:
                    symbol = self._normalizar_ticker(ticker, tipo_ativo)
                    preco_atual_raw = self._obter_preco_atual_seguro(symbol)
                    
                    preco_atual_brl = float(preco_atual_raw or 0.0)
                    
                    if tipo_ativo == "Ação EUA" and preco_atual_brl > 0:
                        fx = self._obter_fx_usd_brl()
                        preco_atual_brl = float(preco_atual_raw) * float(fx)
                    
                    if preco_atual_brl == 0.0:
                        preco_atual_brl = preco_medio_brl

                valor_atual = quantidade * preco_atual_brl
                custo_total = quantidade * preco_medio_brl
                pl_reais = valor_atual - custo_total
                pl_pct = (pl_reais / custo_total) * 100 if custo_total > 0 else 0.0

                itens.append({
                    "ticker": ticker,
                    "tipo": tipo_ativo,
                    "quantidade": quantidade,
                    "preco_medio": preco_medio_brl,
                    "preco_atual": preco_atual_brl,
                    "valor_atual": valor_atual,
                    "pl": pl_reais,
                    "pl_pct": pl_pct,
                })

                total_valor_atual_ativos += valor_atual

            except Exception:
                continue

        patrimonio_atualizado = saldo_caixa + total_valor_atual_ativos

        return {
            "saldo_caixa": float(saldo_caixa),
            "total_valor_atual_ativos": float(total_valor_atual_ativos),
            "patrimonio_atualizado": float(patrimonio_atualizado),
            "ativos": itens
        }

    
    # ------------------------
    # Cartões
    # ------------------------

    def buscar_cartao_por_id(self, id_cartao: str) -> Optional[CartaoCredito]:
        return next((c for c in self.cartoes_credito if c.id_cartao == id_cartao), None)

    def adicionar_cartao_credito(self, cartao: CartaoCredito) -> None:
        self.cartoes_credito.append(cartao)

    def remover_cartao_credito(self, id_cartao: str) -> bool:
        cartao = self.buscar_cartao_por_id(id_cartao)
        if not cartao:
            return False
        self.compras_cartao = [c for c in self.compras_cartao if c.id_cartao != id_cartao]
        self.faturas = [f for f in self.faturas if f.id_cartao != id_cartao]
        self.cartoes_credito = [c for c in self.cartoes_credito if c.id_cartao != id_cartao]
        return True

    def obter_compras_fatura_aberta(self, id_cartao: str) -> List[CompraCartao]:
        return [
            c for c in self.compras_cartao
            if c.id_cartao == id_cartao and c.id_fatura is None
        ]
    def registrar_compra_cartao(
        self,
        id_cartao: str,
        descricao: str,
        valor_total: float,
        data_compra: date,  # data real da compra
        categoria: str,
        num_parcelas: int = 1,
        observacao: str = "",
        tag: str = "",
    ) -> bool:
        cartao = self.buscar_cartao_por_id(id_cartao)
        if not cartao:
            return False
    
        valor_parcela = round(float(valor_total) / int(num_parcelas), 2)
        id_compra_original = str(uuid4())
    
        # Para cada parcela
        for i in range(num_parcelas):
            # Calcula a data da compra considerando o mês da parcela
            # Parcela 1 = mês da compra, Parcela 2 = mês seguinte, etc.
            data_compra_parcela = data_compra + relativedelta(months=i)
            
            # Calcula o ciclo correto para esta parcela
            ano_ciclo, mes_ciclo = self.calcular_ciclo_compra(id_cartao, data_compra_parcela)
            
            # Calcula a data de vencimento baseada no ciclo
            try:
                data_vencimento = date(ano_ciclo, mes_ciclo, cartao.dia_vencimento)
            except ValueError:
                # Se o dia de vencimento não existe no mês, usa o último dia
                ultimo_dia = calendar.monthrange(ano_ciclo, mes_ciclo)[1]
                data_vencimento = date(ano_ciclo, mes_ciclo, min(cartao.dia_vencimento, ultimo_dia))
            
            # Cria a descrição da parcela
            desc_parcela = f"{descricao} ({i + 1}/{num_parcelas})" if num_parcelas > 1 else descricao
            
            # Cria a compra
            nova = CompraCartao(
                id_cartao=id_cartao,
                descricao=desc_parcela,
                valor=valor_parcela,
                data_compra=data_vencimento,      # vencimento
                categoria=categoria,
                total_parcelas=num_parcelas,
                parcela_atual=i + 1,
                id_compra_original=id_compra_original,
                observacao=observacao,
                tag=tag,
                data_compra_real=data_compra,     # data real da compra
            )
            self.compras_cartao.append(nova)
    
        return True

    def remover_compra_cartao(self, id_compra_original: str) -> None:
        self.compras_cartao = [
            c for c in self.compras_cartao if c.id_compra_original != id_compra_original
        ]







    
    def fechar_fatura(
        self,
        id_cartao: str,
        data_fechamento_real: date,
        data_vencimento_real: date,
    ) -> Optional[Fatura]:
        cartao = self.buscar_cartao_por_id(id_cartao)
        if not cartao:
            return None

        ano = data_vencimento_real.year
        mes = data_vencimento_real.month

        elegiveis = [
            c for c in self.compras_cartao
            if c.id_cartao == id_cartao and c.id_fatura is None
            and c.data_compra.year == ano and c.data_compra.month == mes
        ]
        if not elegiveis:
            return None

        total = round(sum(c.valor for c in elegiveis), 2)
        fatura = Fatura(
            id_cartao=id_cartao,
            data_fechamento=data_fechamento_real,
            data_vencimento=data_vencimento_real,
            valor_total=total,
            status="Fechada",
        )
        self.faturas.append(fatura)

        for c in elegiveis:
            c.id_fatura = fatura.id_fatura

        return fatura

    def fechar_fatura(
        self, id_cartao: str, data_fechamento_real: date, data_vencimento_real: date
    ) -> Optional[Fatura]:
        """
        Fecha a fatura do cartão para o ciclo correspondente à data de fechamento.
        Registra a data real de fechamento como customizada para uso futuro.
        """
        cartao = self.buscar_cartao_por_id(id_cartao)
        if not cartao:
            return None
    
        # Calcula o ciclo baseado na data de fechamento real
        ano_ciclo = data_fechamento_real.year
        mes_ciclo = data_fechamento_real.month
    
        # Busca compras em aberto deste ciclo
        compras_do_ciclo = [
            c for c in self.compras_cartao
            if c.id_cartao == id_cartao
            and c.data_compra.year == ano_ciclo
            and c.data_compra.month == mes_ciclo
            and not c.id_fatura
        ]
    
        if not compras_do_ciclo:
            return None
    
        valor_total = sum(c.valor for c in compras_do_ciclo)
        nova_fatura = Fatura(
            id_cartao=id_cartao,
            data_fechamento=data_fechamento_real,
            data_vencimento=data_vencimento_real,
            valor_total=valor_total,
            status="Fechada",
        )
        self.faturas.append(nova_fatura)
    
        # Vincula as compras à fatura
        for compra in compras_do_ciclo:
            compra.id_fatura = nova_fatura.id_fatura
    
        # ✅ ADICIONE ESTA PARTE: Registra o fechamento customizado se for diferente do padrão
        if data_fechamento_real.day != cartao.dia_fechamento:
            chave_mes = f"{ano_ciclo}-{mes_ciclo:02d}"
            cartao.fechamentos_customizados[chave_mes] = data_fechamento_real.day
            # Salva automaticamente (será salvo quando chamar salvar_dados no app.py)
    
        return nova_fatura
 
    def pagar_fatura(self, id_fatura: str, id_conta_pagamento: str, data_pagamento: date) -> bool:
        fatura = next((f for f in self.faturas if f.id_fatura == id_fatura), None)
        if not fatura or fatura.status == "Paga":
            return False
        conta = self.buscar_conta_por_id(id_conta_pagamento)
        if not conta or not isinstance(conta, ContaCorrente):
            return False

        valor = fatura.valor_total
        if conta.saldo + conta.limite_cheque_especial < valor:
            return False

        conta.saldo -= valor
        fatura.status = "Paga"

        self.transacoes.append(
            Transacao(
                id_conta=conta.id_conta,
                descricao=f"Pagamento Fatura {fatura.data_vencimento.strftime('%m/%Y')}",
                valor=valor,
                tipo="Despesa",
                data_transacao=data_pagamento,
                categoria="Cartão de Crédito",
            )
        )
        return True

    def reabrir_fatura(self, id_fatura: str) -> bool:
        """
        Reabre uma fatura fechada, voltando as compras para status 'em aberto'
        e estornando o pagamento se já foi pago.
        
        Args:
            id_fatura: ID da fatura a ser reaberta
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        # Busca a fatura
        fatura = None
        for f in self.faturas:
            if f.id_fatura == id_fatura:
                fatura = f
                break
        
        if not fatura:
            return False
        
        # Se a fatura foi paga, estorna o pagamento
        if fatura.status == "Paga":
            # Busca a transação de pagamento
            transacao_pagamento = None
            for t in self.transacoes:
                if (t.categoria == "Cartão de Crédito" and 
                    f"Pagamento Fatura {fatura.data_vencimento.strftime('%m/%Y')}" in t.descricao):
                    # Verifica se é do cartão correto
                    cartao = self.buscar_cartao_por_id(fatura.id_cartao)
                    if cartao and cartao.nome in t.descricao:
                        transacao_pagamento = t
                        break
            
            # Estorna o valor na conta
            if transacao_pagamento:
                conta = self.buscar_conta_por_id(transacao_pagamento.id_conta)
                if conta and isinstance(conta, ContaCorrente):
                    # Devolve o dinheiro (era despesa, agora estorna)
                    conta.saldo += transacao_pagamento.valor
                    
                    # Remove a transação de pagamento
                    self.transacoes.remove(transacao_pagamento)
        
        # Volta as compras para "em aberto" (remove id_fatura)
        compras_da_fatura = [c for c in self.compras_cartao if c.id_fatura == id_fatura]
        for compra in compras_da_fatura:
            compra.id_fatura = None
        
        # Remove a fatura
        self.faturas.remove(fatura)
        
        return True      
    def adicionar_categoria(self, nome: str) -> None:
        nome = (nome or "").strip()
        if nome and nome not in self.categorias:
            self.categorias.append(nome)

    def remover_categoria(self, nome: str) -> None:
        self.categorias = [c for c in self.categorias if c != nome]


    # ------------------------
    # Fornecedores únicos
    # ------------------------

    def obter_fornecedores_unicos(self) -> list:
        """Retorna lista única de descrições de compras de cartão já lançadas"""
        fornecedores = set()
        for compra in self.compras_cartao:
            if compra.descricao:
                fornecedores.add(compra.descricao.strip())
        return sorted(list(fornecedores))
    
    def adicionar_tag(self, nome_tag: str) -> bool:
        """Adiciona uma nova TAG ao cadastro"""
        nome_tag = nome_tag.strip()
        if nome_tag and nome_tag not in self.tags:
            self.tags.append(nome_tag)
            self.tags.sort()
            return True
        return False
    
    def remover_tag(self, nome_tag: str) -> bool:
        """Remove uma TAG do cadastro"""
        if nome_tag in self.tags:
            self.tags.remove(nome_tag)
            return True
        return False
    
    def ciclo_esta_fechado(self, id_cartao: str, ano: int, mes: int) -> bool:
        """Verifica se o ciclo já tem fatura fechada"""
        for fatura in self.faturas:
            if (fatura.id_cartao == id_cartao and 
                fatura.data_vencimento.year == ano and 
                fatura.data_vencimento.month == mes):
                return True
        return False


    def calcular_ciclo_compra(self, id_cartao: str, data_compra: date) -> tuple:
        """
        Calcula em qual ciclo (ano, mês) a compra cairá baseado na data de fechamento.
        
        LÓGICA:
        - Se a compra foi feita ATÉ o dia de fechamento do mês atual → ciclo do mês atual
        - Se a compra foi feita APÓS o dia de fechamento do mês atual → ciclo do próximo mês
        
        Exemplo: Fechamento dia 02
        - Compra em 30/11/2025 (antes do dia 02/12) → ciclo 12/2025
        - Compra em 03/12/2025 (depois do dia 02/12) → ciclo 01/2026
        
        Retorna (ano, mes) do vencimento.
        """
        cartao = self.buscar_cartao_por_id(id_cartao)
        if not cartao:
            return (data_compra.year, data_compra.month)
        
        ano_ciclo = data_compra.year
        mes_ciclo = data_compra.month
        
        # Verifica se há fechamento customizado para o mês atual da compra
        chave_mes = f"{data_compra.year}-{data_compra.month:02d}"
        dia_fechamento = cartao.fechamentos_customizados.get(chave_mes, cartao.dia_fechamento)
        
        # Se a compra foi feita APÓS o dia de fechamento, vai para o próximo ciclo
        if data_compra.day > dia_fechamento:
            if mes_ciclo == 12:
                ano_ciclo += 1
                mes_ciclo = 1
            else:
                mes_ciclo += 1
        
        # Caso contrário, permanece no ciclo do mês atual
        return (ano_ciclo, mes_ciclo)

    
    # ------------------------
    # Arquivamento de Contas
    # ------------------------

    def arquivar_conta(self, id_conta: str) -> bool:
        """Arquiva uma conta (oculta das listagens principais)"""
        conta = self.buscar_conta_por_id(id_conta)
        if not conta:
            return False
        
        conta.arquivada = True
        self.salvar_dados()
        return True

    def desarquivar_conta(self, id_conta: str) -> bool:
        """Desarquiva uma conta (volta a aparecer nas listagens)"""
        conta = self.buscar_conta_por_id(id_conta)
        if not conta:
            return False
        
        conta.arquivada = False
        self.salvar_dados()
        return True

    def obter_contas_ativas(self) -> List[Conta]:
        """Retorna apenas contas não arquivadas"""
        return [c for c in self.contas if not c.arquivada]

    def obter_contas_arquivadas(self) -> List[Conta]:
        """Retorna apenas contas arquivadas"""
        return [c for c in self.contas if c.arquivada]
