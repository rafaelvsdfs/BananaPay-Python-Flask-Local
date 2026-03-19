from flask import Blueprint, request, redirect, url_for
from flask import Blueprint, render_template, request, redirect, url_for
from app.database import get_conexao

bp = Blueprint('conta', __name__)

# abre a página (GET)
@bp.route("/depositar", methods=["GET"])
def tela_deposito():
    return render_template("depositar.html")

@bp.route("/depositar", methods=["POST"])
def depositar():
    valor = float(request.form.get("valor", 0))

    conn = get_conexao()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM clientes ORDER BY id DESC LIMIT 1")
    cliente = cursor.fetchone()

    if cliente:
        cliente_id = cliente[0]

        cursor.execute("""
            UPDATE contas
            SET saldo = saldo + ?
            WHERE cliente_id = ?
        """, (valor, cliente_id))

        conn.commit()

    conn.close()

    return redirect(url_for("auth.home"))

@bp.route("/sacar", methods=["GET"])
def tela_saque():
    return render_template("sacar.html")

@bp.route("/sacar", methods=["POST"])
def sacar():
    valor = float(request.form.get("valor", 0))

    conn = get_conexao()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.id, co.saldo, co.limite
        FROM clientes c
        JOIN contas co ON co.cliente_id = c.id
        ORDER BY c.id DESC
        LIMIT 1
    """)

    cliente = cursor.fetchone()

    if cliente:
        cliente_id, saldo, limite = cliente

        total_disponivel = saldo + limite

        # não tem dinheiro suficiente
        if valor > total_disponivel:
            conn.close()
            return "Saldo e limite insuficientes"

        # tem saldo suficiente
        if valor <= saldo:
            novo_saldo = saldo - valor
            novo_limite = limite

        # precisa usar limite
        else:
            restante = valor - saldo
            novo_saldo = 0
            novo_limite = limite - restante

        # atualiza no banco
        cursor.execute("""
            UPDATE contas
            SET saldo = ?, limite = ?
            WHERE cliente_id = ?
        """, (novo_saldo, novo_limite, cliente_id))

        conn.commit()

    conn.close()

    return redirect(url_for("auth.home"))