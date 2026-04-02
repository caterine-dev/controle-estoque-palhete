from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# Configuração do Banco de Dados SQLite
# Ele vai criar um arquivo chamado 'estoque.db' na mesma pasta
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'estoque.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# DEFINIÇÃO DAS TABELAS DO BANCO DE DADOS
# ==========================================

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    pin_acesso = db.Column(db.String(4), nullable=False) # Senha de 4 dígitos

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    estoque_minimo = db.Column(db.Float, default=0.0)
    unidade_medida = db.Column(db.String(20), nullable=False) # Ex: Unidade, Caixa, Kg

class CodigoBarras(db.Model):
    # O próprio código lido pela câmera será a chave primária
    codigo = db.Column(db.String(100), primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    
    # Relação para facilitar as buscas no Python
    produto = db.relationship('Produto', backref=db.backref('codigos', lazy=True))

class LoteEstoque(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade_inicial = db.Column(db.Float, nullable=False)
    quantidade_atual = db.Column(db.Float, nullable=False)
    data_validade = db.Column(db.Date, nullable=False)
    data_entrada = db.Column(db.DateTime, default=datetime.now)
    
    produto = db.relationship('Produto', backref=db.backref('lotes', lazy=True))

class Movimentacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey('lote_estoque.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    # tipo_movimentacao: 'Entrada', 'Saída' ou 'Devolução'
    tipo_movimentacao = db.Column(db.String(20), nullable=False) 
    quantidade = db.Column(db.Float, nullable=False)
    data_hora = db.Column(db.DateTime, default=datetime.now)

    lote = db.relationship('LoteEstoque', backref=db.backref('movimentacoes', lazy=True))
    usuario = db.relationship('Usuario', backref=db.backref('movimentacoes', lazy=True))

# ==========================================
# ROTAS DO SISTEMA
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastro-produto', methods=['GET', 'POST'])
def cadastro_produto():
    if request.method == 'POST':
        # Pega as informações que o usuário digitou na tela
        nome = request.form['nome']
        estoque_minimo = float(request.form['estoque_minimo'])
        unidade = request.form['unidade']
        
        # Cria o objeto Produto e salva no banco de dados
        novo_produto = Produto(nome=nome, estoque_minimo=estoque_minimo, unidade_medida=unidade)
        db.session.add(novo_produto)
        db.session.commit()
        
        # Após salvar, volta para o painel inicial
        return redirect(url_for('index'))
    
    # Se não for POST (se estiver só abrindo a página), mostra a tela
    return render_template('cadastro_produto.html')

@app.route('/estoque')
def ver_estoque():
    # Isso faz o Python ir no banco e pegar TODOS os produtos cadastrados
    produtos_cadastrados = Produto.query.all()
    
    # Manda esses produtos para a nossa nova tela
    return render_template('estoque.html', produtos=produtos_cadastrados)

# ==========================================
# INICIALIZAÇÃO DO SERVIDOR
# ==========================================

if __name__ == '__main__':
    # Este bloco garante que o banco de dados (estoque.db) seja criado 
    # fisicamente antes do servidor rodar pela primeira vez.
    with app.app_context():
        db.create_all()
    
    # Rodando o servidor na porta 5003
    app.run(debug=True, host='0.0.0.0', port=5003)