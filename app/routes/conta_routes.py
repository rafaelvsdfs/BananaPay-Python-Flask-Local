from flask import Blueprint, render_template, request, redirect, url_for, session
from app.database import get_conexao

bp = Blueprint('conta', __name__)


# ─────────────────────────────────────────
# DEPÓSITO
# ─────────────────────────────────────────
@bp.route("/depositar", methods=["GET", "POST"])
def depositar():
    if request.method == "POST":
        cliente_id = session.get("cliente_id")
        if not cliente_id:
            return redirect(url_for("auth.login"))

        valor = float(request.form.get("valor", 0))

        conn   = get_conexao()
        cursor = conn.cursor()

        # Busca saldo e limite atuais do cliente
        cursor.execute("SELECT saldo, limite FROM contas WHERE cliente_id = ?", (cliente_id,))
        resultado = cursor.fetchone()
        if not resultado:
            conn.close()
            return "Conta não encontrada"

        saldo, limite = resultado

        # Lógica de recarregar limite antes de ir pro saldo:
        # Se o limite foi parcialmente usado, o depósito recarrega ele primeiro
        # Exemplo: limite máximo = 100, limite atual = 60 → foram usados 40
        limite_usado = 100 - limite
        if limite_usado > 0:
            if valor >= limite_usado:
                # O depósito cobre todo o limite usado, o resto vai pro saldo
                limite += limite_usado
                valor  -= limite_usado
            else:
                # O depósito não cobre tudo, só recarrega parcialmente o limite
                limite += valor
                valor   = 0

        # O que sobrou do valor vai pro saldo
        saldo += valor

        # Salva saldo e limite atualizados
        cursor.execute(
            "UPDATE contas SET saldo = ?, limite = ? WHERE cliente_id = ?",
            (saldo, limite, cliente_id)
        )

        # Registra no histórico com o valor ORIGINAL do formulário (antes dos cálculos)
        cursor.execute(
            "INSERT INTO transacoes (cliente_id, tipo, valor, destinatario_id) VALUES (?, 'deposito', ?, NULL)",
            (cliente_id, float(request.form.get("valor", 0)))
        )

        conn.commit()
        conn.close()
        return redirect(url_for("auth.home"))

    return render_template("depositar.html")


# ─────────────────────────────────────────
# SAQUE
# ─────────────────────────────────────────
@bp.route("/sacar", methods=["GET", "POST"])
def sacar():
    cliente_id = session.get("cliente_id")
    if not cliente_id:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        valor = float(request.form.get("valor", 0))

        conn   = get_conexao()
        cursor = conn.cursor()

        cursor.execute("SELECT saldo, limite FROM contas WHERE cliente_id = ?", (cliente_id,))
        resultado = cursor.fetchone()
        if not resultado:
            conn.close()
            return "Conta não encontrada"

        saldo, limite = resultado

        # Verifica se tem saldo + limite suficiente
        total_disponivel = saldo + limite
        if valor > total_disponivel:
            conn.close()
            return "Saldo + limite insuficiente"

        # Se o saque for maior que o saldo, o restante vem do limite
        # max(0, ...) garante que nunca fique negativo
        novo_saldo  = max(0, saldo - valor)
        novo_limite = limite - max(0, valor - saldo)

        cursor.execute(
            "UPDATE contas SET saldo = ?, limite = ? WHERE cliente_id = ?",
            (novo_saldo, novo_limite, cliente_id)
        )

        # Registra no histórico
        cursor.execute(
            "INSERT INTO transacoes (cliente_id, tipo, valor, destinatario_id) VALUES (?, 'saque', ?, NULL)",
            (cliente_id, valor)
        )

        conn.commit()
        conn.close()
        return redirect(url_for("auth.home"))

    return render_template("sacar.html")


# ─────────────────────────────────────────
# TRANSFERÊNCIA
# ─────────────────────────────────────────
@bp.route("/transferencia", methods=["GET", "POST"])
def transferencia():
    cliente_id = session.get("cliente_id")
    if not cliente_id:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        cpf_destino = request.form["cpf_destino"]
        valor       = float(request.form["valor"])

        conn   = get_conexao()
        cursor = conn.cursor()

        # Verifica se o destinatário existe pelo CPF
        cursor.execute("SELECT id FROM clientes WHERE cpf = ?", (cpf_destino,))
        destino = cursor.fetchone()
        if not destino:
            conn.close()
            return "Usuário destino não encontrado"
        destino_id = destino[0]

        # Busca saldo e limite do remetente (quem está transferindo)
        cursor.execute("SELECT saldo, limite FROM contas WHERE cliente_id = ?", (cliente_id,))
        remetente = cursor.fetchone()
        if not remetente:
            conn.close()
            return "Conta remetente não encontrada"

        saldo, limite = remetente
        total_disponivel = saldo + limite

        if valor > total_disponivel:
            conn.close()
            return "Saldo + limite insuficiente"

        # Calcula novo saldo do remetente
        novo_saldo = saldo - valor
        if novo_saldo < 0:
            # Saldo zerou e ainda falta — desconta do limite
            # novo_saldo é negativo aqui, então soma para reduzir o limite
            novo_limite = limite + novo_saldo
            novo_saldo  = 0
        else:
            novo_limite = limite

        try:
            cursor.execute("BEGIN TRANSACTION;")

            # Debita do remetente
            cursor.execute(
                "UPDATE contas SET saldo = ?, limite = ? WHERE cliente_id = ?",
                (novo_saldo, novo_limite, cliente_id)
            )

            # Credita no destinatário (só soma no saldo dele)
            cursor.execute(
                "UPDATE contas SET saldo = saldo + ? WHERE cliente_id = ?",
                (valor, destino_id)
            )

            # Histórico do remetente → aparece como 'transferencia'
            cursor.execute(
                "INSERT INTO transacoes (cliente_id, tipo, valor, destinatario_id) VALUES (?, 'transferencia', ?, ?)",
                (cliente_id, valor, destino_id)
            )

            # Histórico do destinatário → aparece como 'deposito' (recebeu dinheiro)
            cursor.execute(
                "INSERT INTO transacoes (cliente_id, tipo, valor, destinatario_id) VALUES (?, 'deposito', ?, ?)",
                (destino_id, valor, cliente_id)
            )

            conn.commit()

        except Exception as e:
            # Se qualquer coisa der errado, DESFAZ tudo (rollback)
            # Garante que nunca fique num estado inconsistente
            # Ex: dinheiro saiu do remetente mas não chegou no destinatário
            conn.rollback()
            conn.close()
            return f"Erro na transferência: {e}"

        finally:
            # finally sempre executa, mesmo se der erro
            # garante que a conexão sempre fecha
            conn.close()

        return redirect(url_for("auth.home"))

    return render_template("transferencia.html")


# ─────────────────────────────────────────
# HISTÓRICO
# ─────────────────────────────────────────
@bp.route("/historico")
def historico():
    cliente_id = session.get("cliente_id")
    if not cliente_id:
        return redirect(url_for("auth.login"))

    conn   = get_conexao()
    cursor = conn.cursor()

    # CASE WHEN: lógica condicional dentro do SQL
    # Se for transferencia → pega o nome do destinatário
    # Se for deposito com destinatario_id → veio de uma transferência, pega quem enviou
    # Senão → mostra '-' (depósito ou saque comum)
    cursor.execute("""
        SELECT t.tipo, t.valor, 
               CASE
                   WHEN t.tipo = 'transferencia' THEN (SELECT nome FROM clientes WHERE id = t.destinatario_id)
                   WHEN t.tipo = 'deposito' AND t.destinatario_id IS NOT NULL THEN (SELECT nome FROM clientes WHERE id = t.destinatario_id)
                   ELSE '-' 
               END as outro_usuario,
               t.data
        FROM transacoes t
        WHERE t.cliente_id = ?
        ORDER BY t.data DESC
    """, (cliente_id,))

    # fetchall() retorna todas as linhas como uma lista de tuplas
    # Ex: [('deposito', 200.0, 'Rafael', '2026-03-20'), ...]
    transacoes = cursor.fetchall()
    conn.close()

    return render_template("historico.html", transacoes=transacoes)