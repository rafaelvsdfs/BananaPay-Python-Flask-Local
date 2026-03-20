from flask import Blueprint, render_template, request, redirect, url_for, session
from app.database import get_conexao

bp = Blueprint('auth', __name__)


# ─────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────
@bp.route("/", methods=["GET", "POST"])
def login():
    # GET = só exibe a página | POST = usuário enviou o formulário
    if request.method == "POST":
        nome = request.form["nome"]
        cpf  = request.form["cpf"]

        conn   = get_conexao()
        cursor = conn.cursor()

        # Busca o cliente que tenha exatamente esse nome E esse CPF
        # Os ? evitam SQL Injection (nunca coloque variáveis direto na string)
        cursor.execute("""
            SELECT id, nome FROM clientes
            WHERE nome = ? AND cpf = ?
        """, (nome, cpf))

        usuario = cursor.fetchone()  # retorna uma linha ou None se não achar
        conn.close()

        if usuario:
            # Salva o ID e nome na sessão para usar nas outras páginas
            session["cliente_id"] = usuario[0]
            session["nome"]       = usuario[1]
            return redirect(url_for("auth.home"))
        else:
            return "Usuário não encontrado"

    return render_template("login.html")


# ─────────────────────────────────────────
# HOME
# ─────────────────────────────────────────
@bp.route("/home")
def home():
    cliente_id = session.get("cliente_id")

    # Proteção: se não estiver logado, volta pro login
    if not cliente_id:
        return redirect(url_for("auth.login"))

    conn   = get_conexao()
    cursor = conn.cursor()

    # JOIN liga a tabela clientes com a tabela contas
    # c = apelido de clientes | co = apelido de contas
    # co.cliente_id = c.id é a "ponte" entre as duas tabelas
    cursor.execute("""
        SELECT c.nome, co.saldo, co.limite
        FROM clientes c
        JOIN contas co ON co.cliente_id = c.id
        WHERE c.id = ?
    """, (cliente_id,))

    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        nome, saldo, limite = resultado  # desempacota a tupla retornada
    else:
        nome, saldo, limite = "", 0, 0   # valores padrão se não achar conta

    return render_template("home.html", nome=nome, saldo=saldo, limite=limite)


# ─────────────────────────────────────────
# CADASTRO
# ─────────────────────────────────────────
@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome   = request.form["nome"]
        cpf    = request.form["cpf"]
        salario = float(request.form.get("salario", 0))  # .get() usa 0 se o campo vier vazio
        limite  = float(request.form.get("limite", 0))

        conn   = get_conexao()
        cursor = conn.cursor()

        # Passo 1: insere o cliente
        cursor.execute(
            "INSERT INTO clientes (nome, cpf) VALUES (?, ?)",
            (nome, cpf)
        )
        # lastrowid pega o ID gerado automaticamente pelo banco para esse novo cliente
        # precisamos dele para vincular a conta ao cliente na linha abaixo
        cliente_id = cursor.lastrowid

        # Passo 2: cria a conta vinculada ao cliente recém-criado
        cursor.execute(
            "INSERT INTO contas (cliente_id, saldo, limite) VALUES (?, ?, ?)",
            (cliente_id, salario, limite)
        )

        # commit() confirma as duas operações no banco
        # sem ele nada é salvo de verdade
        conn.commit()
        conn.close()

        return redirect(url_for("auth.login"))

    return render_template("cadastro.html")