# app.py

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)

ARQUIVO = 'prontuarios.json'


# =========================
# CRIAR JSON SE NÃO EXISTIR
# =========================

if not os.path.exists(ARQUIVO):

    with open(ARQUIVO, 'w') as f:
        json.dump([], f)


# =========================
# FUNÇÕES AUXILIARES
# =========================

def ler_dados():

    with open(ARQUIVO, 'r') as f:
        return json.load(f)


def salvar_dados(dados):

    with open(ARQUIVO, 'w') as f:
        json.dump(dados, f, indent=4)


# =========================
# FRONTEND
# =========================

@app.route('/')
def home():

    return send_from_directory(
        'static',
        'index.html'
    )


# =========================
# POST /prontuario
# =========================

@app.route('/prontuario', methods=['POST'])
def criar_prontuario():

    dados = request.json

    campos = [
        'nome',
        'cpf',
        'nascimento',
        'queixa',
        'pressao',
        'temperatura',
        'fc'
    ]

    # valida campos obrigatórios
    for campo in campos:

        if campo not in dados or str(dados[campo]).strip() == '':

            return jsonify({
                'erro': f'Campo obrigatório: {campo}'
            }), 400

    cpf = ''.join(
        filter(str.isdigit, dados['cpf'])
    )

    # valida cpf
    if len(cpf) != 11:

        return jsonify({
            'erro': 'CPF inválido'
        }), 400

    # valida temperatura
    try:

        temperatura = float(
            dados['temperatura']
        )

        if temperatura < 30 or temperatura > 45:

            return jsonify({
                'erro': 'Temperatura inválida'
            }), 400

    except:

        return jsonify({
            'erro': 'Temperatura inválida'
        }), 400

    # valida fc
    try:

        fc = int(dados['fc'])

        if fc < 20 or fc > 250:

            return jsonify({
                'erro': 'Frequência cardíaca inválida'
            }), 400

    except:

        return jsonify({
            'erro': 'Frequência cardíaca inválida'
        }), 400

    lista = ler_dados()

    # impede cpf repetido
    for paciente in lista:

        if paciente['cpf'] == cpf:

            return jsonify({
                'erro': 'Paciente já cadastrado'
            }), 409

    novo_atendimento = {
    "nome": nome,
    "cpf": cpf,
    "nascimento": nascimento,
    "queixa": queixa,
    "pressao": pressao,
    "temperatura": temperatura,
    "fc": fc,
    "observacoes": observacoes,
    "horario": datetime.now().strftime("%d/%m/%Y %H:%M")
}
    

    lista.append(novo)

    salvar_dados(lista)

    return jsonify({
        'mensagem': 'Prontuário salvo'
    }), 201


# =========================
# GET /prontuarios
# =========================

@app.route('/prontuarios', methods=['GET'])
def listar_prontuarios():

    return jsonify(
        ler_dados()
    ), 200


# =========================
# GET /prontuarios/<cpf>
# =========================

@app.route('/prontuarios/<cpf>', methods=['GET'])
def buscar_paciente(cpf):

    cpf_limpo = ''.join(
        filter(str.isdigit, cpf)
    )

    lista = ler_dados()

    for paciente in lista:

        if paciente['cpf'] == cpf_limpo:

            return jsonify(
                paciente
            ), 200

    return jsonify({
        'erro': 'Paciente não encontrado'
    }), 404


# =========================
# DELETE
# =========================

@app.route('/deletar/<cpf>', methods=['DELETE'])
def deletar(cpf):

    cpf_limpo = ''.join(
        filter(str.isdigit, cpf)
    )

    lista = ler_dados()

    nova_lista = [

        p for p in lista
        if p['cpf'] != cpf_limpo
    ]

    salvar_dados(nova_lista)

    return jsonify({
        'mensagem': 'Paciente deletado'
    }), 200


# =========================

if __name__ == '__main__':

    print(
        '🚀 Servidor rodando em http://127.0.0.1:5000'
    )

    app.run(debug=True)
