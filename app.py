from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'palhete_super_secreta_2026'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'estoque.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# MODELOS
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
# SEGURANÇA
# ==========================================

@app.before_request
def verificar_login():
    rotas_publicas = ['login', 'static']
    if request.endpoint not in rotas_publicas and 'usuario_id' not in session:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        pin_digitado = request.form['pin']
        usuario = Usuario.query.filter_by(pin_acesso=pin_digitado).first()
        if usuario:
            session['usuario_id'] = usuario.id
            session['usuario_nome'] = usuario.nome
            return redirect(url_for('index'))
        erro = "PIN incorreto."
    return render_template('login.html', erro=erro)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# GESTÃO DE EQUIPA
# ==========================================

@app.route('/gerenciar-equipe')
def gerenciar_equipe():
    usuarios = Usuario.query.all()
    return render_template('gerenciar_equipe.html', usuarios=usuarios)

@app.route('/adicionar-usuario', methods=['GET', 'POST'])
def adicionar_usuario():
    if request.method == 'POST':
        db.session.add(Usuario(nome=request.form['nome'], pin_acesso=request.form['pin']))
        db.session.commit()
        return redirect(url_for('gerenciar_equipe'))
    return render_template('adicionar_usuario.html')

@app.route('/excluir-usuario/<int:id>', methods=['POST'])
def excluir_usuario(id):
    if id == session['usuario_id']:
        return redirect(url_for('gerenciar_equipe'))
    usuario = Usuario.query.get_or_404(id)
    db.session.delete(usuario)
    db.session.commit()
    return redirect(url_for('gerenciar_equipe'))

# ==========================================
# RESTO DAS ROTAS (ESTOQUE)
# ==========================================

@app.route('/')
def index():
    produtos = Produto.query.all()
    total_itens = len(produtos)
    produtos_baixo_estoque = []
    for produto in produtos:
        total_estoque = sum(lote.quantidade_atual for lote in produto.lotes if lote.quantidade_atual > 0)
        if total_estoque < produto.estoque_minimo and produto.estoque_minimo > 0:
            produtos_baixo_estoque.append({'nome': produto.nome, 'estoque_atual': total_estoque, 'minimo': produto.estoque_minimo, 'unidade': produto.unidade_medida})
    hoje = datetime.now().date()
    lotes_vencendo = LoteEstoque.query.filter(LoteEstoque.quantidade_atual > 0, LoteEstoque.data_validade <= hoje + timedelta(days=7)).order_by(LoteEstoque.data_validade).all()
    return render_template('index.html', total_itens=total_itens, produtos_baixo_estoque=produtos_baixo_estoque, lotes_vencendo=lotes_vencendo, total_alertas=len(produtos_baixo_estoque)+len(lotes_vencendo))

@app.route('/cadastro-produto', methods=['GET', 'POST'])
def cadastro_produto():
    if request.method == 'POST':
        db.session.add(Produto(nome=request.form['nome'], estoque_minimo=float(request.form['estoque_minimo']), unidade_medida=request.form['unidade']))
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('cadastro_produto.html')

@app.route('/estoque')
def ver_estoque():
    produtos = []
    for p in Produto.query.all():
        produtos.append({'id': p.id, 'nome': p.nome, 'unidade': p.unidade_medida, 'minimo': p.estoque_minimo, 'saldo': sum(l.quantidade_atual for l in p.lotes if l.quantidade_atual > 0)})
    return render_template('estoque.html', produtos=produtos)

@app.route('/editar-produto/<int:id>', methods=['GET', 'POST'])
def editar_produto(id):
    p = Produto.query.get_or_404(id)
    if request.method == 'POST':
        p.nome, p.estoque_minimo, p.unidade_medida = request.form['nome'], float(request.form['estoque_minimo']), request.form['unidade']
        db.session.commit()
        return redirect(url_for('ver_estoque'))
    return render_template('editar_produto.html', produto=p)

@app.route('/excluir-produto/<int:id>', methods=['POST'])
def excluir_produto(id):
    p = Produto.query.get_or_404(id)
    CodigoBarras.query.filter_by(produto_id=p.id).delete()
    for l in LoteEstoque.query.filter_by(produto_id=p.id).all():
        Movimentacao.query.filter_by(lote_id=l.id).delete()
        db.session.delete(l)
    db.session.delete(p)
    db.session.commit()
    return redirect(url_for('ver_estoque'))

@app.route('/entrada-lote', methods=['GET', 'POST'])
def entrada_lote():
    if request.method == 'POST':
        novo_lote = LoteEstoque(produto_id=request.form['produto_id'], quantidade_inicial=float(request.form['quantidade']), quantidade_atual=float(request.form['quantidade']), data_validade=datetime.strptime(request.form['data_validade'], '%Y-%m-%d').date())
        db.session.add(novo_lote)
        db.session.flush()
        db.session.add(Movimentacao(lote_id=novo_lote.id, usuario_id=session['usuario_id'], tipo_movimentacao='Entrada', quantidade=float(request.form['quantidade'])))
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('entrada_lote.html', produtos=Produto.query.all(), mapa_codigos={cb.codigo: cb.produto_id for cb in CodigoBarras.query.all()})

@app.route('/retirar-produto', methods=['GET', 'POST'])
def retirar_produto():
    if request.method == 'POST':
        qtd = float(request.form['quantidade'])
        lotes = LoteEstoque.query.filter_by(produto_id=request.form['produto_id']).filter(LoteEstoque.quantidade_atual > 0).order_by(LoteEstoque.data_validade).all()
        for l in lotes:
            if qtd <= 0: break
            baixa = min(l.quantidade_atual, qtd)
            l.quantidade_atual -= baixa
            qtd -= baixa
            db.session.add(Movimentacao(lote_id=l.id, usuario_id=session['usuario_id'], tipo_movimentacao='Saída', quantidade=baixa))
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('retirar_produto.html', produtos=Produto.query.all(), mapa_codigos={cb.codigo: cb.produto_id for cb in CodigoBarras.query.all()})

@app.route('/historico')
def historico():
    return render_template('historico.html', movimentacoes=Movimentacao.query.order_by(Movimentacao.data_hora.desc()).limit(50).all())

@app.route('/estornar/<int:id>', methods=['POST'])
def estornar(id):
    m = Movimentacao.query.get_or_404(id)
    if m.tipo_movimentacao == 'Saída': m.lote.quantidade_atual += m.quantidade
    else: m.lote.quantidade_atual = max(0, m.lote.quantidade_atual - m.quantidade)
    db.session.delete(m)
    db.session.commit()
    return redirect(url_for('historico'))

@app.route('/vincular-codigo', methods=['GET', 'POST'])
def vincular_codigo():
    if request.method == 'POST':
        if not CodigoBarras.query.filter_by(codigo=request.form['codigo']).first():
            db.session.add(CodigoBarras(codigo=request.form['codigo'], produto_id=request.form['produto_id']))
            db.session.commit()
        return redirect(url_for('index'))
    return render_template('vincular_codigo.html', produtos=Produto.query.all())

@app.route('/perfil')
def perfil():
    return render_template('perfil.html', usuario=Usuario.query.get(session['usuario_id']))

# ROTA DE RELATÓRIOS INTELIGENTES (NOVO!)
@app.route('/relatorios')
def relatorios():
    # Pega as saídas dos últimos 30 dias
    trinta_dias_atras = datetime.now() - timedelta(days=30)
    saidas = Movimentacao.query.filter(
        Movimentacao.tipo_movimentacao == 'Saída',
        Movimentacao.data_hora >= trinta_dias_atras
    ).all()

    # Dicionário para somar tudo que saiu de cada produto
    consumo = {}
    for mov in saidas:
        p = mov.lote.produto
        if p.id not in consumo:
            consumo[p.id] = {'nome': p.nome, 'unidade': p.unidade_medida, 'total': 0}
        consumo[p.id]['total'] += mov.quantidade

    # Ordena do maior pro menor e pega só os Top 5
    top_produtos = sorted(consumo.values(), key=lambda x: x['total'], reverse=True)[:5]
    
    return render_template('relatorios.html', top_produtos=top_produtos)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Usuario.query.first():
            db.session.add(Usuario(nome="Chef Palhete", pin_acesso="1234"))
            db.session.commit()
    app.run(debug=True, host='0.0.0.0', port=5003, ssl_context='adhoc')