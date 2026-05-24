# ============================================================
#  SaúdeConectada Nordeste — Backend
#  Hospital Regional Santa Cruz | Petrolina-PE
# ============================================================

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import sqlite3
import re

app = Flask(__name__, static_folder="static")
CORS(app)

DB_PATH = "prontuario.db"


# ============================================================
#  BANCO DE DADOS
# ============================================================

def init_db():
    """
    Cria as tabelas no SQLite na primeira execução.
    Uma tabela unificada de atendimentos, com todos os campos
    do formulário: identificação + queixa + sinais vitais.
    SQLite escolhido para o MVP — sem instalação extra.
    Em produção: migrar para PostgreSQL.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prontuarios (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nome          TEXT    NOT NULL,
            cpf           TEXT    NOT NULL,
            nascimento    TEXT    NOT NULL,
            queixa        TEXT    NOT NULL,
            observacoes   TEXT,
            altura        REAL,
            peso          REAL,
            pressao       TEXT,
            temperatura   REAL,
            freq_cardiaca INTEGER,
            spo2          INTEGER,
            horario       TEXT    NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def get_conn():
    """
    Conexão com row_factory: permite acessar colunas pelo nome
    (row['nome']) em vez de índice (row[0]).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    """Converte sqlite3.Row em dict serializável para JSON."""
    return dict(row)


# ============================================================
#  VALIDAÇÕES
# ============================================================

def normalizar_cpf(cpf):
    """
    Remove pontuação → apenas 11 dígitos.
    Padroniza armazenamento e buscas.
    Ex: '123.456.789-09' → '12345678909'
    """
    return re.sub(r'\D', '', cpf)


def validar_cpf_formato(cpf):
    """Aceita CPF com ou sem pontuação, desde que tenha 11 dígitos."""
    return len(normalizar_cpf(cpf)) == 11


def validar_obrigatorios(dados, campos):
    """
    Centraliza validação de campos obrigatórios — princípio DRY.
    Retorna mensagem de erro ou None se tudo OK.
    """
    for campo in campos:
        if not dados.get(campo) or str(dados[campo]).strip() == "":
            return f"Campo obrigatório ausente ou vazio: '{campo}'"
    return None


# ============================================================
#  ROTAS
# ============================================================

# ------------------------------------------------------------
# POST /prontuario
# Recebe JSON do formulário e salva novo atendimento.
# POST (e não GET) porque dados de saúde são sensíveis
# (LGPD Art. 11) — não devem aparecer na URL.
# ------------------------------------------------------------
@app.route("/prontuario", methods=["POST"])
def criar_prontuario():
    dados = request.get_json()

    if not dados:
        return jsonify({"erro": "Corpo inválido. Envie JSON."}), 400

    erro = validar_obrigatorios(dados, ["nome", "cpf", "nascimento", "queixa"])
    if erro:
        return jsonify({"erro": erro}), 400

    if not validar_cpf_formato(dados["cpf"]):
        return jsonify({"erro": "CPF inválido. Use 000.000.000-00 ou 11 dígitos."}), 400

    # Validações clínicas dos sinais vitais
    temperatura = None
    if dados.get("temperatura") not in (None, ""):
        try:
            temperatura = float(dados["temperatura"])
            if not (30.0 <= temperatura <= 45.0):
                return jsonify({"erro": "Temperatura fora do intervalo plausível (30–45 °C)."}), 400
        except (ValueError, TypeError):
            return jsonify({"erro": "Temperatura deve ser um número."}), 400

    freq_cardiaca = None
    if dados.get("freq_cardiaca") not in (None, ""):
        try:
            freq_cardiaca = int(dados["freq_cardiaca"])
            if not (20 <= freq_cardiaca <= 300):
                return jsonify({"erro": "FC fora do intervalo plausível (20–300 bpm)."}), 400
        except (ValueError, TypeError):
            return jsonify({"erro": "Frequência cardíaca deve ser inteiro."}), 400

    spo2 = None
    if dados.get("spo2") not in (None, ""):
        try:
            spo2 = int(dados["spo2"])
            if not (0 <= spo2 <= 100):
                return jsonify({"erro": "SpO2 deve estar entre 0 e 100%."}), 400
        except (ValueError, TypeError):
            return jsonify({"erro": "SpO2 deve ser inteiro."}), 400

    altura = None
    if dados.get("altura") not in (None, ""):
        try:
            altura = float(dados["altura"])
            if not (50 <= altura <= 250):
                return jsonify({"erro": "Altura fora do intervalo plausível (50–250 cm)."}), 400
        except (ValueError, TypeError):
            return jsonify({"erro": "Altura deve ser um número."}), 400

    peso = None
    if dados.get("peso") not in (None, ""):
        try:
            peso = float(dados["peso"])
            if not (1 <= peso <= 400):
                return jsonify({"erro": "Peso fora do intervalo plausível (1–400 kg)."}), 400
        except (ValueError, TypeError):
            return jsonify({"erro": "Peso deve ser um número."}), 400

    cpf_norm = normalizar_cpf(dados["cpf"])

    # Horário gerado no servidor — garante consistência
    # independente do relógio do cliente
    horario = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO prontuarios
            (nome, cpf, nascimento, queixa, observacoes,
             altura, peso, pressao, temperatura, freq_cardiaca, spo2, horario)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dados["nome"].strip(),
        cpf_norm,
        dados["nascimento"],
        dados["queixa"].strip(),
        dados.get("observacoes", "").strip(),
        altura, peso,
        dados.get("pressao", ""),
        temperatura, freq_cardiaca, spo2,
        horario,
    ))
    conn.commit()
    novo_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "mensagem": "Atendimento registrado com sucesso.",
        "id": novo_id,
        "horario": horario
    }), 201


# ------------------------------------------------------------
# GET /prontuarios
# Retorna todos os atendimentos, do mais recente ao mais antigo.
# Usado pela tela "Acessar Dados" para montar a tabela geral.
# ------------------------------------------------------------
@app.route("/prontuarios", methods=["GET"])
def listar_prontuarios():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prontuarios ORDER BY horario DESC")
    registros = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(registros), 200


# ------------------------------------------------------------
# GET /prontuarios/<cpf>
# Histórico completo de um paciente pelo CPF.
# Aceita CPF com ou sem pontuação na URL.
# ------------------------------------------------------------
@app.route("/prontuarios/<cpf>", methods=["GET"])
def historico_paciente(cpf):
    cpf_norm = normalizar_cpf(cpf)
    if len(cpf_norm) != 11:
        return jsonify({"erro": "CPF inválido. Informe 11 dígitos."}), 400

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM prontuarios WHERE cpf = ? ORDER BY horario DESC",
        (cpf_norm,)
    )
    registros = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()

    if not registros:
        return jsonify({
            "erro": "Nenhum atendimento encontrado para este CPF.",
            "cpf": cpf_norm
        }), 404

    return jsonify({
        "paciente": registros[0]["nome"],
        "cpf": cpf_norm,
        "total_atendimentos": len(registros),
        "atendimentos": registros
    }), 200


# ------------------------------------------------------------
# DELETE /prontuarios/<cpf>
# Remove todos os atendimentos de um paciente.
# Método DELETE comunica a intenção claramente (semântica REST).
# ------------------------------------------------------------
@app.route("/prontuarios/<cpf>", methods=["DELETE"])
def deletar_paciente(cpf):
    cpf_norm = normalizar_cpf(cpf)
    if len(cpf_norm) != 11:
        return jsonify({"erro": "CPF inválido."}), 400

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM prontuarios WHERE cpf = ?", (cpf_norm,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"erro": "Paciente não encontrado."}), 404

    cursor.execute("DELETE FROM prontuarios WHERE cpf = ?", (cpf_norm,))
    deletados = cursor.rowcount
    conn.commit()
    conn.close()

    return jsonify({
        "mensagem": "Paciente deletado com sucesso.",
        "atendimentos_removidos": deletados
    }), 200


# ------------------------------------------------------------
# Serve as páginas HTML
# /        → index.html  (formulário novo atendimento)
# /dados   → dados.html  (listagem e detalhes)
# ------------------------------------------------------------
@app.route("/")
def pagina_formulario():
    return send_from_directory("static", "index.html")


@app.route("/dados")
def pagina_dados():
    return send_from_directory("static", "dados.html")


# ============================================================
#  PONTO DE ENTRADA
# ============================================================
if __name__ == "__main__":
    init_db()
    print("=" * 55)
    print("  SaúdeConectada Nordeste — Backend iniciado")
    print("  Hospital Regional Santa Cruz | Petrolina-PE")
    print("=" * 55)
    print("  Formulário : http://localhost:5000")
    print("  Dados      : http://localhost:5000/dados")
    print("  Rotas API  :")
    print("    POST   /prontuario        → novo atendimento")
    print("    GET    /prontuarios       → todos os atendimentos")
    print("    GET    /prontuarios/<cpf> → histórico do paciente")
    print("    DELETE /prontuarios/<cpf> → deletar paciente")
    print("=" * 55)
    app.run(debug=True, port=5000)
