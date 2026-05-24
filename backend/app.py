from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime #Configurações do App para rodar no navegador web e funcionar conforme demandado


app = Flask(__name__, static_folder="static")
CORS(app)  #frontend acessa a API

DB_PATH = "prontuario.db"
#  Inicializa o banco de dados SQLite

def init_db():
    """Cria as tabelas no banco de dados se não existirem."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nome       TEXT    NOT NULL,
            cpf        TEXT    UNIQUE NOT NULL,
            nascimento TEXT    NOT NULL,
            sexo       TEXT    NOT NULL,
            telefone   TEXT,
            email      TEXT,
            endereco   TEXT,
            criado_em  TEXT    NOT NULL
        
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prontuarios (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id   INTEGER NOT NULL,
            data_consulta TEXT    NOT NULL,
            medico        TEXT    NOT NULL,
            queixa        TEXT,
            historico     TEXT,
            exame_fisico  TEXT,
            diagnostico   TEXT,
            sinais vitais TEXT,
            prescricao    TEXT,
            queixas       TEXT,
            observações   TEXT,
                   
            criado_em     TEXT    NOT NULL,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        )
    """)

    conn.commit()
    conn.close()



#  Helper: converte linha do banco em dicionário (Mais explicação no DOCS)
# ─────────────────────────────────────────────
def row_to_dict(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


# ═════════════════════════════════════════════
#  ROTAS – Pacientes
# ═════════════════════════════════════════════

@app.route("/api/pacientes", methods=["GET"])
def listar_pacientes():
    """Retorna todos os pacientes cadastrados."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pacientes ORDER BY nome")
    pacientes = [row_to_dict(cursor, row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(pacientes)


@app.route("/api/pacientes", methods=["POST"])
def cadastrar_paciente():
    """Cadastra um novo paciente."""
    dados = request.get_json()

    campos_obrigatorios = ["nome", "cpf", "nascimento", "sexo"]
    for campo in campos_obrigatorios:
        if not dados.get(campo):
            return jsonify({"erro": f"Campo obrigatório ausente: {campo}"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor() # conn é a ponte entre python e SQLite

    try:
        cursor.execute("""
            INSERT INTO pacientes (nome, cpf, nascimento, sexo, telefone, email, endereco, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dados["nome"],
            dados["cpf"],
            dados["nascimento"],
            dados["sexo"],
            dados.get("telefone", ""),
            dados.get("email", ""),
            dados.get("endereco", ""),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        conn.commit()
        paciente_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"erro": "CPF já cadastrado no sistema"}), 409
    finally:
        conn.close()

    return jsonify({"mensagem": "Paciente cadastrado com sucesso", "id": paciente_id}), 201
# Faz com que todos os dados sejam inseridos, vai dando erro caso não e caso esteja repetindo

@app.route("/api/pacientes/<int:paciente_id>", methods=["GET"])
def obter_paciente(paciente_id):
    """Retorna os dados de um paciente específico."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pacientes WHERE id = ?", (paciente_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"erro": "Paciente não encontrado"}), 404

    return jsonify(row_to_dict(cursor, row))


@app.route("/api/pacientes/buscar", methods=["GET"])
def buscar_paciente():
    """Busca pacientes por nome ou CPF."""
    termo = request.args.get("q", "")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM pacientes WHERE nome LIKE ? OR cpf LIKE ? ORDER BY nome",
        (f"%{termo}%", f"%{termo}%"),
    )
    pacientes = [row_to_dict(cursor, row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(pacientes)


# ═════════════════════════════════════════════
#  ROTAS – Prontuários
# ═════════════════════════════════════════════

@app.route("/api/prontuarios", methods=["POST"])
def criar_prontuario():
    """Cria um novo registro de consulta para um paciente."""
    dados = request.get_json()

    campos_obrigatorios = ["paciente_id", "data_consulta", "medico"]
    for campo in campos_obrigatorios:
        if not dados.get(campo):
            return jsonify({"erro": f"Campo obrigatório ausente: {campo}"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Verifica se o paciente existe
    cursor.execute("SELECT id FROM pacientes WHERE id = ?", (dados["paciente_id"],))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"erro": "Paciente não encontrado"}), 404

    cursor.execute("""
        INSERT INTO prontuarios
            (paciente_id, data_consulta, medico, queixa, historico,
             exame_fisico, diagnostico, prescricao, observacoes, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dados["paciente_id"],
        dados["data_consulta"],
        dados["medico"],
        dados.get("queixa", ""),
        dados.get("historico", ""),
        dados.get("exame_fisico", ""),
        dados.get("diagnostico", ""),
        dados.get("prescricao", ""),
        dados.get("observacoes", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))
    conn.commit()
    prontuario_id = cursor.lastrowid
    conn.close()

    return jsonify({"mensagem": "Prontuário salvo com sucesso", "id": prontuario_id}), 201


@app.route("/api/prontuarios/<int:paciente_id>", methods=["GET"])
def listar_prontuarios(paciente_id):
    """Lista todos os prontuários de um paciente."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM prontuarios WHERE paciente_id = ? ORDER BY data_consulta DESC",
        (paciente_id,),
    )
    registros = [row_to_dict(cursor, row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(registros)


# ─────────────────────────────────────────────
#  Serve o frontend (index.html)
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ─────────────────────────────────────────────
#  Ponto de entrada
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("✅  Banco de dados inicializado.")
    print("🛞  Servidor rodando em http://localhost:5000")
    app.run(debug=True, port=5000)
# como rodar
