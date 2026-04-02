from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Configuração do Banco de Dados SQLite
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
    pin_acesso = db.Column(db.String(4), nullable=False)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    estoque_minimo = db.Column(db.Float, default=0.0)
    unidade_medida = db.Column(db.String(20), nullable=False)

class CodigoBarras(db.Model):
    codigo = db.Column(db.String(100), primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
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
    produtos = Produto.query.all()
    total_itens = len(produtos)
    
    # Lógica Inteligente 1: Alertas de Estoque Mínimo
    produtos_baixo_estoque = []
    for produto in produtos:
        # Soma a quantidade de todos os lotes deste produto
        total_estoque = sum(lote.quantidade_atual for lote in produto.lotes if lote.quantidade_atual > 0)
        
        # Só alerta se o estoque estiver abaixo do mínimo (e ignora se o mínimo for zero)
        if total_estoque < produto.estoque_minimo and produto.estoque_minimo > 0:
            produtos_baixo_estoque.append({
                'nome': produto.nome,
                'estoque_atual': total_estoque,
                'minimo': produto.estoque_minimo,
                'unidade': produto.unidade_medida
            })
            
    # Lógica Inteligente 2: Alertas de Vencimento (Próximos 7 dias ou já vencidos)
    hoje = datetime.now().date()
    limite_validade = hoje + timedelta(days=7)
    
    lotes_vencendo = LoteEstoque.query.filter(
        LoteEstoque.quantidade_atual > 0,
        LoteEstoque.data_validade <= limite_validade
    ).order_by(LoteEstoque.data_validade).all()
    
    total_alertas = len(produtos_baixo_estoque) + len(lotes_vencendo)
    
    return render_template('index.html', 
                           total_itens=total_itens, 
                           produtos_baixo_estoque=produtos_baixo_estoque,
                           lotes_vencendo=lotes_vencendo,
                           total_alertas=total_alertas)

@app.route('/cadastro-produto', methods=['GET', 'POST'])
def cadastro_produto():
    if request.method == 'POST':
        nome = request.form['nome']
        estoque_minimo = float(request.form['estoque_minimo'])
        unidade = request.form['unidade']
        
        novo_produto = Produto(nome=nome, estoque_minimo=estoque_minimo, unidade_medida=unidade)
        db.session.add(novo_produto)
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('cadastro_produto.html')

@app.route('/estoque')
def ver_estoque():
    produtos_cadastrados = Produto.query.all()
    return render_template('estoque.html', produtos=produtos_cadastrados)

@app.route('/entrada-lote', methods=['GET', 'POST'])
def entrada_lote():
    if request.method == 'POST':
        produto_id = request.form['produto_id']
        quantidade = float(request.form['quantidade'])
        data_validade_str = request.form['data_validade']
        
        data_validade = datetime.strptime(data_validade_str, '%Y-%m-%d').date()
        
        novo_lote = LoteEstoque(
            produto_id=produto_id,
            quantidade_inicial=quantidade,
            quantidade_atual=quantidade,
            data_validade=data_validade
        )
        db.session.add(novo_lote)
        db.session.commit()
        return redirect(url_for('index'))
    
    produtos_cadastrados = Produto.query.all()
    return render_template('entrada_lote.html', produtos=produtos_cadastrados)

@app.route('/retirar-produto', methods=['GET', 'POST'])
def retirar_produto():
    if request.method == 'POST':
        produto_id = request.form['produto_id']
        quantidade_retirar = float(request.form['quantidade'])
        
        lotes_disponiveis = LoteEstoque.query.filter_by(produto_id=produto_id)\
                                             .filter(LoteEstoque.quantidade_atual > 0)\
                                             .order_by(LoteEstoque.data_validade).all()
        
        quantidade_restante = quantidade_retirar
        
        for lote in lotes_disponiveis:
            if quantidade_restante <= 0:
                break
                
            if lote.quantidade_atual >= quantidade_restante:
                lote.quantidade_atual -= quantidade_restante
                quantidade_restante = 0
            else:
                quantidade_restante -= lote.quantidade_atual
                lote.quantidade_atual = 0
                
        db.session.commit()
        return redirect(url_for('index'))
        
    produtos_cadastrados = Produto.query.all()
    return render_template('retirar_produto.html', produtos=produtos_cadastrados)

# ==========================================
# INICIALIZAÇÃO DO SERVIDOR
# ==========================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5003)