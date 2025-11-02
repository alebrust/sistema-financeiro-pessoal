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
    ):
        super().__init__(nome=nome, logo_url=logo_url, id_conta=id_conta)
        self.saldo = float(saldo)
        self.limite_cheque_especial = float(limite_cheque_especial)

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
        }


class ContaInvestimento(Conta):
    def __init__(
        self,
        nome: str,
        logo_url: str = "",
        saldo_caixa: float = 0.0,
        ativos: Optional[List[Ativo]] = None,
        id_conta: Optional[str] = None,
    ):
        super().__init__(nome=nome, logo_url=logo_url, id_conta=id_conta)
        self.saldo_caixa = float(saldo_caixa)
        self.ativos: List[Ativo] = ativos or []

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
        }


class CartaoCredito:
    def __init__(
        self,
        nome: str,
        logo_url: str = "",
        dia_fechamento: int = 28,
        dia_vencimento: int = 10,
        id_cartao: Optional[str] = None,
    ):
        self.id_cartao = id_cartao or str(uuid4())
        self.nome = nome
        self.logo_url = logo_url
        self.dia_fechamento = int(dia_fechamento)
        self.dia_vencimento = int(dia_vencimento)

    def para_dict(self) -> Dict[str, Any]:
        return {
            "id_cartao": self.id_cartao,
            "nome": self.nome,
            "logo_url": self.logo_url,
            "dia_fechamento": self.dia_fechamento,
            "dia_vencimento": self.dia_vencimento,
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
        data_compra: date,  # neste sistema, é a data de vencimento da parcela
        categoria: str,
        total_parcelas: int = 1,
        parcela_atual: int = 1,
        id_compra_original: Optional[str] = None,
        observacao: str = "",
        id_compra: Optional[str] = None,
        id_fatura: Optional[str] = None,
        data_compra_real: Optional[date] = None,  # data real da compra
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
        # Cache simples de cotações (sessão do app)
        self._cotacoes_cache: Dict[str, Dict[str, float]] = {}
        self._cotacoes_ttl: int = 60  # segundos
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
        }
        with open(self.caminho_arquivo, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

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
        symbol = self._normalizar_ticker(ticker, tipo_ativo)
        now = self._agora_epoch()
        cached = self._cotacoes_cache.get(symbol)
        if cached and (now - cached["ts"] <= self._cotacoes_ttl):
            return cached["preco"]

        try:
            preco = self._obter_preco_yf(symbol)
            self._cotacoes_cache[symbol] = {"preco": preco, "ts": now}
            return preco
        except Exception:
            return None

    def calcular_posicao_conta_investimento(self, id_conta: str) -> Optional[Dict[str, Any]]:
        conta = self.buscar_conta_por_id(id_conta)
        if not conta or not isinstance(conta, ContaInvestimento):
            return None

        ativos_resumo: List[Dict[str, Any]] = []
        total_valor_atual = 0.0
        total_custo = 0.0

        for a in conta.ativos:
            preco_atual = self.obter_preco_atual(a.ticker, a.tipo_ativo)
            custo = a.preco_medio * a.quantidade
            total_custo += custo

            if preco_atual is not None:
                valor_atual = preco_atual * a.quantidade
                pl = valor_atual - custo
                pl_pct = (pl / custo * 100.0) if custo > 0 else 0.0
                total_valor_atual += valor_atual
            else:
                valor_atual = None
                pl = None
                pl_pct = None

            ativos_resumo.append({
                "ticker": a.ticker,
                "tipo": a.tipo_ativo,
                "quantidade": a.quantidade,
                "preco_medio": a.preco_medio,
                "preco_atual": preco_atual,
                "valor_atual": valor_atual,
                "custo": custo,
                "pl": pl,
                "pl_pct": pl_pct,
            })

        patrimonio_atualizado = conta.saldo_caixa + total_valor_atual
        return {
            "conta": conta.nome,
            "saldo_caixa": conta.saldo_caixa,
            "ativos": ativos_resumo,
            "total_valor_atual_ativos": total_valor_atual,
            "total_custo_ativos": total_custo,
            "patrimonio_atualizado": patrimonio_atualizado,
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
    ) -> bool:
        cartao = self.buscar_cartao_por_id(id_cartao)
        if not cartao:
            return False

        valor_parcela = round(float(valor_total) / int(num_parcelas), 2)
        id_compra_original = str(uuid4())

        try:
            data_fechamento_ciclo = date(data_compra.year, data_compra.month, cartao.dia_fechamento)
        except ValueError:
            ultimo = calendar.monthrange(data_compra.year, data_compra.month)[1]
            data_fechamento_ciclo = date(data_compra.year, data_compra.month, ultimo)

        try:
            base_venc = date(data_compra.year, data_compra.month, cartao.dia_vencimento)
        except ValueError:
            ultimo = calendar.monthrange(data_compra.year, data_compra.month)[1]
            base_venc = date(data_compra.year, data_compra.month, ultimo)

        if data_compra <= data_fechamento_ciclo:
            vencimento_primeira = base_venc + relativedelta(months=1)
        else:
            vencimento_primeira = base_venc + relativedelta(months=2)

        for i in range(num_parcelas):
            data_venc_parcela = vencimento_primeira + relativedelta(months=i)
            desc_parcela = f"{descricao} ({i + 1}/{num_parcelas})" if num_parcelas > 1 else descricao
            nova = CompraCartao(
                id_cartao=id_cartao,
                descricao=desc_parcela,
                valor=valor_parcela,
                data_compra=data_venc_parcela,      # vencimento
                categoria=categoria,
                total_parcelas=num_parcelas,
                parcela_atual=i + 1,
                id_compra_original=id_compra_original,
                observacao=observacao,
                data_compra_real=data_compra,        # real
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

    def adicionar_categoria(self, nome: str) -> None:
        nome = (nome or "").strip()
        if nome and nome not in self.categorias:
            self.categorias.append(nome)

    def remover_categoria(self, nome: str) -> None:
        self.categorias = [c for c in self.categorias if c != nome]
