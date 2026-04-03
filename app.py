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
    
    produtos_baixo_estoque = []
    for produto in produtos:
        total_estoque = sum(lote.quantidade_atual for lote in produto.lotes if lote.quantidade_atual > 0)
        if total_estoque < produto.estoque_minimo and produto.estoque_minimo > 0:
            produtos_baixo_estoque.append({
                'nome': produto.nome,
                'estoque_atual': total_estoque,
                'minimo': produto.estoque_minimo,
                'unidade': produto.unidade_medida
            })
            
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
    
    # Criar uma lista turbinada para a tela, incluindo a soma do estoque atual de cada um
    produtos_com_saldo = []
    for p in produtos_cadastrados:
        saldo_total = sum(lote.quantidade_atual for lote in p.lotes if lote.quantidade_atual > 0)
        produtos_com_saldo.append({
            'id': p.id,
            'nome': p.nome,
            'unidade': p.unidade_medida,
            'minimo': p.estoque_minimo,
            'saldo': saldo_total
        })
        
    return render_template('estoque.html', produtos=produtos_com_saldo)

@app.route('/editar-produto/<int:id>', methods=['GET', 'POST'])
def editar_produto(id):
    produto = Produto.query.get_or_404(id)
    
    if request.method == 'POST':
        produto.nome = request.form['nome']
        produto.estoque_minimo = float(request.form['estoque_minimo'])
        produto.unidade_medida = request.form['unidade']
        
        db.session.commit()
        return redirect(url_for('ver_estoque'))
        
    return render_template('editar_produto.html', produto=produto)

@app.route('/excluir-produto/<int:id>', methods=['POST'])
def excluir_produto(id):
    produto = Produto.query.get_or_404(id)
    
    # Limpeza de Segurança (Deleta tudo que está ligado a este produto para não quebrar o banco)
    CodigoBarras.query.filter_by(produto_id=produto.id).delete()
    
    lotes = LoteEstoque.query.filter_by(produto_id=produto.id).all()
    for lote in lotes:
        Movimentacao.query.filter_by(lote_id=lote.id).delete()
        db.session.delete(lote)
        
    db.session.delete(produto)
    db.session.commit()
    
    return redirect(url_for('ver_estoque'))

@app.route('/entrada-lote', methods=['GET', 'POST'])
def entrada_lote():
    if request.method == 'POST':
        produto_id = request.form['produto_id']
        quantidade = float(request.form['quantidade'])
        data_validade = datetime.strptime(request.form['data_validade'], '%Y-%m-%d').date()
        
        novo_lote = LoteEstoque(
            produto_id=produto_id,
            quantidade_inicial=quantidade,
            quantidade_atual=quantidade,
            data_validade=data_validade
        )
        db.session.add(novo_lote)
        db.session.flush()
        
        mov = Movimentacao(lote_id=novo_lote.id, usuario_id=1, tipo_movimentacao='Entrada', quantidade=quantidade)
        db.session.add(mov)
        db.session.commit()
        return redirect(url_for('index'))
    
    produtos_cadastrados = Produto.query.all()
    mapa_codigos = {cb.codigo: cb.produto_id for cb in CodigoBarras.query.all()}
    return render_template('entrada_lote.html', produtos=produtos_cadastrados, mapa_codigos=mapa_codigos)

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
                qtd_descontada = quantidade_restante
                lote.quantidade_atual -= quantidade_restante
                quantidade_restante = 0
            else:
                qtd_descontada = lote.quantidade_atual
                quantidade_restante -= lote.quantidade_atual
                lote.quantidade_atual = 0
            
            mov = Movimentacao(lote_id=lote.id, usuario_id=1, tipo_movimentacao='Saída', quantidade=qtd_descontada)
            db.session.add(mov)
                
        db.session.commit()
        return redirect(url_for('index'))
        
    produtos_cadastrados = Produto.query.all()
    mapa_codigos = {cb.codigo: cb.produto_id for cb in CodigoBarras.query.all()}
    return render_template('retirar_produto.html', produtos=produtos_cadastrados, mapa_codigos=mapa_codigos)

@app.route('/historico')
def historico():
    movimentacoes = Movimentacao.query.order_by(Movimentacao.data_hora.desc()).limit(50).all()
    return render_template('historico.html', movimentacoes=movimentacoes)

@app.route('/estornar/<int:id>', methods=['POST'])
def estornar(id):
    mov = Movimentacao.query.get_or_404(id)
    lote = mov.lote
    if mov.tipo_movimentacao == 'Saída':
        lote.quantidade_atual += mov.quantidade
    elif mov.tipo_movimentacao == 'Entrada':
        lote.quantidade_atual -= mov.quantidade
        if lote.quantidade_atual < 0:
            lote.quantidade_atual = 0
            
    db.session.delete(mov)
    db.session.commit()
    return redirect(url_for('historico'))

@app.route('/vincular-codigo', methods=['GET', 'POST'])
def vincular_codigo():
    if request.method == 'POST':
        produto_id = request.form['produto_id']
        codigo = request.form['codigo']
        
        existe = CodigoBarras.query.filter_by(codigo=codigo).first()
        if not existe:
            novo_codigo = CodigoBarras(codigo=codigo, produto_id=produto_id)
            db.session.add(novo_codigo)
            db.session.commit()
            
        return redirect(url_for('index'))
        
    produtos = Produto.query.all()
    return render_template('vincular_codigo.html', produtos=produtos)

# ==========================================
# INICIALIZAÇÃO DO SERVIDOR
# ==========================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Usuario.query.first():
            chef = Usuario(nome="Chef", pin_acesso="1234")
            db.session.add(chef)
            db.session.commit()
            
    app.run(debug=True, host='0.0.0.0', port=5003, ssl_context='adhoc')