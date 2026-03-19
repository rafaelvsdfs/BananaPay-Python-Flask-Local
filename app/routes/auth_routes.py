from flask import Blueprint, render_template, request, redirect, url_for
from app.database import get_conexao

bp = Blueprint('auth', __name__)

# Rota Home
@bp.route("/")
def home():
    conn = get_conexao()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.nome, co.saldo, co.limite
        FROM clientes c
        JOIN contas co ON co.cliente_id = c.id
        ORDER BY c.id DESC
        LIMIT 1
    """)

    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        nome, saldo, limite = resultado
    else:
        nome, saldo, limite = "", 0, 0

    return render_template("index.html", nome=nome, saldo=saldo, limite=limite)


# Rota Cadastro
@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome"]
        cpf = request.form["cpf"]
        salario = float(request.form.get("salario", 0))
        limite = float(request.form.get("limite", 0))  # 🔥 agora pegando o limite

        conn = get_conexao()
        cursor = conn.cursor()

        # Inserir cliente
        cursor.execute(
            "INSERT INTO clientes (nome, cpf) VALUES (?, ?)",
            (nome, cpf)
        )
        cliente_id = cursor.lastrowid

        # Criar conta com saldo e limite
        cursor.execute(
            "INSERT INTO contas (cliente_id, saldo, limite) VALUES (?, ?, ?)",
            (cliente_id, salario, limite)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("auth.home"))

    return render_template("cadastro.html")