from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, timedelta
from camada_dados.usuario_dao import UsuarioDAO
from camada_dados.agendamento_dao  import AgendamentoDAO
from modelos.usuario import Aluno, Funcionario, Admin, Servidor
from camada_negocio.servicos import ServicoLogin, ServicoAdmin, ServicoBolsista

from camada_dados.agendamento_dao import buscar_quadras_por_ginasio, verificar_disponibilidade,get_ginasio_por_id,  criar_agendamento,buscar_agendamentos_por_quadra,  verificar_usuario_existe, buscar_ginasios, buscar_agendamentos_por_usuario

from camada_dados.mongo_config import conectar_mongo
import re

import os


app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

servico_login = ServicoLogin()
servico_admin = ServicoAdmin()
servico_bolsista = ServicoBolsista()

usuario_dao = UsuarioDAO()

def get_form_value(key, default=None, cast_type=None):
    value = request.form.get(key)
    if value is None or value == '': # Trata None e string vazia
        return default
    if cast_type:
        try:
            return cast_type(value)
        except ValueError:
            print(f"DEBUG: Erro de conversão para {key}: '{value}' para tipo {cast_type.__name__}")
            return default
    return value

def eh_bolsista():
    """Verifica se o usuário logado é bolsista"""
    usuario_info = session.get('usuario_logado', {})
    if usuario_info.get('tipo') != "aluno":
        return False
    
    # Buscar informações completas do usuário
    usuario_dao = UsuarioDAO()
    usuario_completo = usuario_dao.buscar_por_cpf(usuario_info['cpf'])
    
    return (usuario_completo and 
            hasattr(usuario_completo, 'categoria') and 
            usuario_completo.categoria == "Bolsista")


@app.route('/')
@app.route('/index')
def index():
    print(f"DEBUG: Acessando a rota index. Conteúdo da sessão: {session}")
    if 'usuario_logado' in session:
        usuario_info = session['usuario_logado']
        print(f"DEBUG: Usuário está logado. Renderizando index.html para {usuario_info['nome']}")
        return render_template('index.html', usuario=usuario_info)
    else:
        print("DEBUG: Usuário não está na sessão. Redirecionando para /login.")
        flash('Por favor, faça o login para acessar o sistema.', 'info')
        return redirect(url_for('login'))
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        print(f"DEBUG: Tentativa de login com email: {email}")

        usuario = servico_login.verificar_credenciais(email, senha)

        if usuario:
            print(f"DEBUG: Login BEM-SUCEDIDO para o usuário: {usuario.nome} (Tipo: {usuario.tipo})")
            
            # Adicionar informação se é bolsista na sessão
            eh_bolsista_flag = False
            if hasattr(usuario, 'categoria'):
                eh_bolsista_flag = (usuario.categoria == "Bolsista")
            
            session['usuario_logado'] = {
                'cpf': usuario.cpf,
                'nome': usuario.nome,
                'email': usuario.email,
                'tipo': usuario.tipo,
                'eh_bolsista': eh_bolsista_flag
            }
            print(f"DEBUG: Informações do usuário armazenadas na sessão: {session['usuario_logado']}")

            flash(f'Bem-vindo, {usuario.nome}!', 'success')
            return redirect(url_for('index'))
        else:
            print(f"DEBUG: Login FALHOU para o email: {email}")
            flash('Email ou senha inválidos.', 'error')
            return redirect(url_for('login')) 

    return render_template('login.html')


@app.route('/novo_agendamento/<int:ginasio_id>')
@app.route('/selecionar_quadra/<int:ginasio_id>')
def selecionar_quadra(ginasio_id):
    from camada_dados.agendamento_dao import get_ginasio_por_id, buscar_quadras_por_ginasio
    
    gin = get_ginasio_por_id(ginasio_id)
    if not gin:
        flash('Ginásio não encontrado.', 'error')
        return redirect(url_for('novo_agendamento'))
    
    quadras = buscar_quadras_por_ginasio(ginasio_id)
    
    return render_template('selecionar_quadra.html', 
                         gin=ginasio_id, 
                         nome_ginasio=gin.nome, 
                         quadras=quadras)

@app.route('/cadastrar_aluno', methods=['GET', 'POST'])
def cadastrar_aluno():
    if request.method == 'POST':
        # Coleta os dados do formulário HTML
        cpf = request.form['cpf']
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        data_nasc = request.form['data_nasc']
        matricula = request.form['matricula']
        curso = request.form['curso']

        ano_inicio = datetime.now().year

        # Cria o objeto Aluno
        aluno = Aluno(
            cpf=cpf,
            nome=nome,
            email=email,
            senha=senha,
            data_nasc=data_nasc,
            status='ativo',
            matricula=matricula,
            curso=curso,
            ano_inicio=ano_inicio
        )

        dao = UsuarioDAO()
        sucesso = dao.salvar(aluno)

        if sucesso:
            flash("Aluno cadastrado com sucesso! Agora você pode fazer o login.", "success")
            return redirect(url_for('login'))
        else:
            flash("Erro ao cadastrar aluno. Verifique se o CPF ou Email já estão em uso.", "error")
            return redirect(url_for('cadastrar_aluno'))

    return render_template('cadastrar_aluno.html')

@app.route("/meus_agendamentos")
def meus_agendamentos():
    if "usuario_logado" not in session:
        return redirect(url_for("login"))

    usuario_info = session["usuario_logado"]
    usuario_id = usuario_info["cpf"]
    agendamentos = buscar_agendamentos_por_usuario(usuario_id)

    return render_template("meus_agendamentos.html", agendamentos=agendamentos)

@app.route('/novo_agendamento')
def novo_agendamento():
    ginasios = buscar_ginasios()
    return render_template('novo_agendamento.html', ginasios=ginasios)

@app.route('/logout')
def logout():
    session.clear()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('login'))

@app.route('/painel_admin')
def painel_admin():
    if session.get('usuario_logado', {}).get('tipo') != "admin":
        flash('Acesso negado. Apenas administradores podem ver esta página.', 'error')
        return redirect(url_for('index'))
    return render_template('painel_admin.html', usuario=session['usuario_logado'])

@app.route('/painel_funcionario')
def painel_funcionario():
    # Use 'usuario_logado' na sessão
    if session.get('usuario_logado', {}).get('tipo') not in ["funcionario", "admin"]:
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))
    return render_template('painel_funcionario.html', usuario=session['usuario_logado'])

@app.route('/painel_aluno')
def painel_aluno():
    # Use 'usuario_logado' na sessão
    if session.get('usuario_logado', {}).get('tipo') != "aluno":
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))
    return render_template('painel_aluno.html', usuario=session['usuario_logado'])

# --- PAINEL DO BOLSISTA ---
@app.route('/painel_bolsista')
def painel_bolsista():
    if not eh_bolsista():
        flash('Acesso restrito a bolsistas.', 'error')
        return redirect(url_for('index'))
    
    usuario_info = session.get('usuario_logado', {})
    
    # Buscar agendamentos do dia para confirmação
    agendamentos_hoje = servico_bolsista.buscar_agendamentos_para_confirmacao(usuario_info['cpf'])
    
    return render_template('painel_bolsista.html', 
                         usuario=usuario_info, 
                         agendamentos_hoje=agendamentos_hoje)


# --- ROTAS DO BOLSISTA ---
@app.route('/bolsista/agendamento/novo', methods=['GET', 'POST'])
def bolsista_novo_agendamento():
    if not eh_bolsista():
        flash('Acesso restrito a bolsistas.', 'error')
        return redirect(url_for('index'))
    
    usuario_info = session.get('usuario_logado', {})
    
    if request.method == 'POST':
        cpf_beneficiario = request.form.get('cpf_beneficiario')
        id_ginasio = request.form.get('id_ginasio')
        num_quadra = request.form.get('num_quadra')
        data_agendamento = request.form.get('data_agendamento')
        hora_inicio = request.form.get('hora_inicio')
        motivo = request.form.get('motivo', '')
        
        # Combinar data e hora
        hora_ini = f"{data_agendamento} {hora_inicio}:00"
        hora_fim = f"{data_agendamento} {int(hora_inicio) + 1}:00"  # 1 hora de duração
        
        sucesso = servico_bolsista.fazer_agendamento_em_nome_de(
            usuario_info['cpf'], cpf_beneficiario, id_ginasio, num_quadra, 
            hora_ini, hora_fim, motivo
        )
        
        if sucesso:
            flash('Agendamento realizado com sucesso!', 'success')
            return redirect(url_for('painel_bolsista'))
        else:
            flash('Erro ao realizar agendamento. Tente novamente.', 'error')
    
    # Buscar ginásios para o dropdown
    ginasios = buscar_ginasios()
    return render_template('bolsista_novo_agendamento.html', 
                         usuario=usuario_info, 
                         ginasios=ginasios)

@app.route('/bolsista/buscar_usuarios')
def bolsista_buscar_usuarios():
    """API para buscar usuários por nome ou CPF (usado no autocomplete)"""
    if not eh_bolsista():
        return jsonify([])
    
    termo = request.args.get('q', '')
    if len(termo) < 2:
        return jsonify([])
    
    usuarios = servico_bolsista.buscar_usuarios_para_agendamento(termo)
    return jsonify(usuarios)

@app.route('/bolsista/confirmar_presenca', methods=['POST'])
def bolsista_confirmar_presenca():
    if not eh_bolsista():
        flash('Acesso restrito a bolsistas.', 'error')
        return redirect(url_for('index'))
    
    usuario_info = session.get('usuario_logado', {})
    id_agendamento = request.form.get('id_agendamento')
    
    sucesso = servico_bolsista.confirmar_comparecimento(id_agendamento, usuario_info['cpf'])
    
    if sucesso:
        flash('Presença confirmada com sucesso!', 'success')
    else:
        flash('Erro ao confirmar presença.', 'error')
    
    return redirect(url_for('painel_bolsista'))

@app.route('/bolsista/relatorios', methods=['GET', 'POST'])
def bolsista_relatorios():
    if not eh_bolsista():
        flash('Acesso restrito a bolsistas.', 'error')
        return redirect(url_for('index'))
    
    usuario_info = session.get('usuario_logado', {})
    relatorio = []
    
    if request.method == 'POST':
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        id_ginasio = request.form.get('id_ginasio') or None
        
        relatorio = servico_bolsista.gerar_relatorio_uso(data_inicio, data_fim, id_ginasio)
    
    ginasios = buscar_ginasios()
    return render_template('bolsista_relatorios.html', 
                         usuario=usuario_info, 
                         ginasios=ginasios, 
                         relatorio=relatorio)

@app.route('/admin/usuarios', methods=['GET', 'POST'])
def admin_gerenciar_usuarios():
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado. Apenas administradores podem ver esta página.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        acao = request.form.get('acao')
        cpf_usuario = request.form.get('cpf')

        print(f"DEBUG[Rota]: Ação recebida: '{acao}' para o CPF: {cpf_usuario}")

        if acao == 'alterar_status':
            status_atual = request.form.get('status_atual')
            sucesso = servico_admin.alterar_status_usuario(cpf_usuario, status_atual)
            if sucesso:
                flash('Status do usuário alterado com sucesso!', 'success')
            else:
                flash('Ocorreu um erro ao alterar o status do usuário.', 'error')
        
        elif acao == 'excluir':
            sucesso = servico_admin.remover_usuario(cpf_usuario)
            if sucesso:
                flash('Usuário excluído com sucesso!', 'success')
            else:
                flash('Erro ao excluir o usuário.', 'error')
        
        else:
            flash('Ação desconhecida.', 'error')
        
        return redirect(url_for('admin_gerenciar_usuarios'))

    print("DEBUG[Rota]: Carregando a lista de usuários para a página de gerenciamento.")
    lista_de_usuarios = servico_admin.listar_usuarios()
    
    return render_template('admin_gerenciar_usuarios.html', usuarios=lista_de_usuarios)


@app.route('/admin/agendamentos', methods=['GET', 'POST'])
def admin_ver_agendamentos():
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        id_agendamento = request.form.get('id_agendamento')
        sucesso = servico_admin.cancelar_agendamento_admin(id_agendamento)
        if sucesso:
            flash(f'Agendamento ID {id_agendamento} cancelado com sucesso!', 'success')
        else:
            flash('Erro ao cancelar o agendamento.', 'error')
        return redirect(url_for('admin_ver_agendamentos'))

    lista_de_agendamentos = servico_admin.listar_todos_agendamentos()
    return render_template('admin_ver_agendamentos.html', agendamentos=lista_de_agendamentos)

@app.route('/admin/quadras', methods=['GET', 'POST'])
def admin_gerenciar_quadras():
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        acao = request.form.get('acao')
        id_ginasio = request.form.get('id_ginasio')
        num_quadra = request.form.get('num_quadra')

        if acao == 'atualizar_status':
            novo_status = request.form.get('novo_status')
            sucesso = servico_admin.alterar_status_quadra(id_ginasio, num_quadra, novo_status)
            if sucesso:
                flash(f'Status da quadra {num_quadra} do ginásio {id_ginasio} atualizado com sucesso!', 'success')
            else:
                flash('Erro ao atualizar o status da quadra.', 'error')
        
        elif acao == 'excluir':
            sucesso = servico_admin.remover_quadra(id_ginasio, num_quadra)
            if sucesso:
                flash(f'Quadra {num_quadra} do ginásio {id_ginasio} excluída com sucesso!', 'success')
            else:
                flash('Erro ao excluir a quadra. Verifique se existem dependências.', 'error')
        
        return redirect(url_for('admin_gerenciar_quadras'))

    lista_de_quadras = servico_admin.listar_quadras_para_gerenciar()
    status_possiveis = ['disponivel', 'manutencao', 'interditada']
    
    return render_template('admin_gerenciar_quadras.html', 
                           quadras=lista_de_quadras, 
                           status_possiveis=status_possiveis)

@app.route('/admin/quadras/nova', methods=['GET', 'POST'])
def admin_adicionar_quadra():
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        id_ginasio = request.form['id_ginasio']
        num_quadra = request.form['num_quadra']
        capacidade = request.form['capacidade']
        tipo_piso = request.form['tipo_piso']
        cobertura = request.form.get('cobertura') # .get() retorna None se o checkbox não for marcado
        
        sucesso = servico_admin.adicionar_nova_quadra(id_ginasio, num_quadra, capacidade, tipo_piso, cobertura)
        
        if sucesso:
            flash('Nova quadra adicionada com sucesso!', 'success')
            return redirect(url_for('admin_gerenciar_quadras'))
        else:
            flash('Erro ao adicionar a quadra. Verifique se o número da quadra já existe para este ginásio.', 'error')
            return redirect(url_for('admin_adicionar_quadra'))

    lista_de_ginasios = servico_admin.listar_ginasios()
    return render_template('admin_adicionar_quadra.html', ginasios=lista_de_ginasios)


@app.route('/admin/usuarios/novo', methods=['GET', 'POST'])
def admin_adicionar_usuario():
    # Proteção da rota
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))
    
    # Lógica POST para processar o formulário
    if request.method == 'POST':
        # 1. Coleta TODOS os dados do formulário em um único dicionário
        dados_do_formulario = request.form.to_dict()
        
        # 2. Delega TODA a lógica para a camada de serviço
        sucesso = servico_admin.criar_novo_usuario(dados_do_formulario)
        
        # 3. Dá o feedback com base na resposta do serviço
        if sucesso:
            flash(f"Usuário do tipo '{dados_do_formulario.get('tipo_usuario')}' criado com sucesso!", 'success')
            return redirect(url_for('admin_gerenciar_usuarios'))
        else:
            flash('Erro ao criar usuário. Verifique se o CPF ou Email já estão em uso.', 'error')
            return redirect(url_for('admin_adicionar_usuario'))

    # Lógica GET para exibir o formulário
    # A única responsabilidade no GET é buscar os dados para os dropdowns
    lista_de_supervisores = usuario_dao.buscar_todos_os_servidores()
    return render_template('admin_adicionar_usuario.html', supervisores=lista_de_supervisores)



@app.route('/admin/materiais', methods=['GET', 'POST'])
def admin_gerenciar_materiais():
    # Proteção da rota
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))

    # Lógica POST para exclusão
    if request.method == 'POST':
        id_material = request.form.get('id_material')
        
        # Delega a ação de remoção para a camada de serviço
        sucesso = servico_admin.remover_material(id_material)
        
        if sucesso:
            flash('Material esportivo excluído com sucesso!', 'success')
        else:
            flash('Erro ao excluir o material. Ele pode estar em uso em um agendamento.', 'error')
        
        return redirect(url_for('admin_gerenciar_materiais'))

    # Lógica GET para listar os materiais
    # Delega a busca para a camada de serviço
    lista_de_materiais = servico_admin.listar_materiais()
    
    return render_template('admin_gerenciar_materiais.html', materiais=lista_de_materiais)

@app.route('/admin/materiais/form', defaults={'id_material': None}, methods=['GET', 'POST'])
@app.route('/admin/materiais/form/<id_material>', methods=['GET', 'POST'])
def admin_form_material(id_material):
    # Proteção da rota
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))
    
    # Lógica POST para salvar (criar ou editar)
    if request.method == 'POST':
        print("\n--- DEBUG: RECEBIDA REQUISIÇÃO POST EM /admin/materiais/form ---")
        print(f"ID do Material (da URL): {id_material}")
        print(f"Dados recebidos do formulário: {request.form}")
        
        # Coleta os dados brutos do formulário
        id_ginasio = request.form.get('id_ginasio')
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        marca = request.form.get('marca')
        status = request.form.get('status')
        qnt_total = request.form.get('qnt_total')

        if id_material: # Modo de edição
            print(f"-> Entrando no modo de EDIÇÃO para o material ID: {id_material}")
            qnt_disponivel = request.form.get('qnt_disponivel')
            sucesso = servico_admin.atualizar_material(id_material, nome, descricao, marca, status, qnt_total, qnt_disponivel)
        else: # Modo de criação
            print("-> Entrando no modo de CRIAÇÃO de novo material.")
            sucesso = servico_admin.adicionar_material(id_ginasio, nome, descricao, marca, status, qnt_total)

        print(f"-> Resultado da operação (sucesso): {sucesso}")
        if sucesso:
            flash('Operação com material realizada com sucesso!', 'success')
            return redirect(url_for('admin_gerenciar_materiais'))
        else:
            flash('Erro ao processar o material.', 'error')
            # Em caso de erro, redireciona de volta para o formulário para correção
            if id_material:
                return redirect(url_for('admin_form_material', id_material=id_material))
            else:
                return redirect(url_for('admin_form_material'))

    # Lógica GET para exibir o formulário (sem alteração nos prints por enquanto)
    material_existente = None
    if id_material:
        todos_materiais = servico_admin.listar_materiais()
        material_existente = next((m for m in todos_materiais if m.get('id_material') == id_material), None)

    lista_de_ginasios = servico_admin.listar_ginasios()
    status_possiveis = ['bom', 'danificado', 'manutencao']
    
    return render_template('admin_form_material.html', 
                           ginasios=lista_de_ginasios,
                           status_possiveis=status_possiveis,
                           material=material_existente)


@app.route('/admin/ginasios', methods=['GET', 'POST'])
def admin_gerenciar_ginasios():
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        id_ginasio = request.form.get('id_ginasio')
        sucesso = servico_admin.remover_ginasio(id_ginasio)
        if sucesso:
            flash('Ginásio excluído com sucesso! Todas as quadras e agendamentos associados foram removidos.', 'success')
        else:
            flash('Erro ao excluir o ginásio.', 'error')
        return redirect(url_for('admin_gerenciar_ginasios'))

    lista_de_ginasios = servico_admin.listar_ginasios()
    return render_template('admin_gerenciar_ginasios.html', ginasios=lista_de_ginasios)


@app.route('/admin/ginasios/form', defaults={'id_ginasio': None}, methods=['GET', 'POST'])
@app.route('/admin/ginasios/form/<int:id_ginasio>', methods=['GET', 'POST'])
def admin_form_ginasio(id_ginasio):
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))
    
    ginasio_existente = None
    if id_ginasio:
        ginasio_existente = servico_admin.buscar_ginasio_por_id(id_ginasio)

    if request.method == 'POST':
        nome = get_form_value('nome')
        endereco = get_form_value('endereco')
        capacidade = get_form_value('capacidade', cast_type=int)

        if id_ginasio: # Modo de edição
            sucesso = servico_admin.atualizar_ginasio(id_ginasio, nome, endereco, capacidade)
            if sucesso:
                flash('Ginásio atualizado com sucesso!', 'success')
            else:
                flash('Erro ao atualizar o ginásio.', 'error')
        else: # Modo de criação
            sucesso = servico_admin.adicionar_ginasio(nome, endereco, capacidade)
            if sucesso:
                flash('Novo ginásio adicionado com sucesso!', 'success')
            else:
                flash('Erro ao adicionar o ginásio.', 'error')
        
        return redirect(url_for('admin_gerenciar_ginasios'))

    return render_template('admin_form_ginasio.html', ginasio=ginasio_existente)


@app.route('/admin/chamados', methods=['GET', 'POST'])
def admin_gerenciar_chamados():
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        id_chamado = request.form.get('id_chamado')
        sucesso = servico_admin.resolver_chamado_manutencao(id_chamado)
        if sucesso:
            flash('Chamado de manutenção resolvido com sucesso!', 'success')
        else:
            flash('Erro ao processar o chamado.', 'error')
        return redirect(url_for('admin_gerenciar_chamados'))

    lista_de_chamados = servico_admin.listar_chamados_manutencao()
    return render_template('admin_gerenciar_chamados.html', chamados=lista_de_chamados)


@app.route('/admin/esportes', methods=['GET', 'POST'])
def admin_gerenciar_esportes():
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        id_esporte = request.form.get('id_esporte')
        sucesso = servico_admin.remover_esporte(id_esporte)
        if sucesso:
            flash('Esporte excluído com sucesso!', 'success')
        else:
            flash('Erro ao excluir o esporte. Ele pode estar associado a uma quadra.', 'error')
        return redirect(url_for('admin_gerenciar_esportes'))

    lista_de_esportes = servico_admin.listar_esportes()
    return render_template('admin_gerenciar_esportes.html', esportes=lista_de_esportes)


@app.route('/admin/esportes/form', defaults={'id_esporte': None}, methods=['GET', 'POST'])
@app.route('/admin/esportes/form/<id_esporte>', methods=['GET', 'POST'])
def admin_form_esporte(id_esporte):
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))
    
    esporte_existente = None
    if id_esporte:
        esporte_existente = servico_admin.buscar_esporte_por_id(id_esporte)

    if request.method == 'POST':
        nome = get_form_value('nome')
        max_jogadores = get_form_value('max_jogadores', cast_type=int)

        if id_esporte: # Modo de edição
            sucesso = servico_admin.atualizar_esporte(id_esporte, nome, max_jogadores)
            if sucesso:
                flash('Esporte atualizado com sucesso!', 'success')
            else:
                flash('Erro ao atualizar o esporte.', 'error')
        else: # Modo de criação
            sucesso = servico_admin.adicionar_esporte(nome, max_jogadores)
            if sucesso:
                flash('Novo esporte adicionado com sucesso!', 'success')
            else:
                flash('Erro ao adicionar o esporte.', 'error')
        
        return redirect(url_for('admin_gerenciar_esportes'))

    return render_template('admin_form_esporte.html', esporte=esporte_existente)


@app.route('/admin/quadras/associar_esportes/<int:id_ginasio>/<int:num_quadra>', methods=['GET', 'POST'])
def admin_associar_esportes(id_ginasio, num_quadra):
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Pega a lista de strings do formulário
        ids_dos_esportes_selecionados = request.form.getlist('esportes_selecionados')
        ids_dos_esportes_selecionados = [id for id in ids_dos_esportes_selecionados if id]
        
        sucesso = servico_admin.salvar_associacao_esportes_quadra(id_ginasio, num_quadra, ids_dos_esportes_selecionados)
        
        if sucesso:
            flash('Esportes associados à quadra atualizados com sucesso!', 'success')
        else:
            flash('Erro ao atualizar as associações de esportes.', 'error')
        
        return redirect(url_for('admin_gerenciar_quadras'))

    dados_para_pagina = servico_admin.buscar_dados_para_associacao(id_ginasio, num_quadra)
    
    quadra_info = servico_admin.listar_quadras_para_gerenciar()
    quadra_especifica = next((q for q in quadra_info if q['id_ginasio'] == id_ginasio and q['num_quadra'] == num_quadra), None)
    
    return render_template('admin_associar_esportes.html',
                           quadra=quadra_especifica,
                           todos_esportes=dados_para_pagina['todos_esportes'],
                           esportes_associados_ids=dados_para_pagina['esportes_associados_ids'])

@app.route('/admin/eventos', methods=['GET', 'POST'])
def admin_gerenciar_eventos():
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        id_evento = request.form.get('id_evento')
        sucesso = servico_admin.remover_evento(id_evento)
        if sucesso:
            flash('Evento excluído com sucesso!', 'success')
        else:
            flash('Erro ao excluir o evento.', 'error')
        return redirect(url_for('admin_gerenciar_eventos'))

    lista_de_eventos = servico_admin.listar_eventos()
    return render_template('admin_gerenciar_eventos.html', eventos=lista_de_eventos)

@app.route('/admin/eventos/novo', methods=['GET', 'POST'])
def admin_form_evento():
    # Proteção da rota
    if session.get('usuario_logado', {}).get('tipo') != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Dados comuns do formulário
        cpf_admin_organizador = request.form.get('cpf_admin_organizador')
        nome_evento = request.form.get('nome')
        desc_evento = request.form.get('descricao')
        tipo_evento = request.form.get('tipo_evento')
        lista_quadras = request.form.getlist('quadras_selecionadas')
        
        dados_tempo = {}
        # Lógica para construir os dados de tempo
        if tipo_evento == 'extraordinario':
            dados_tempo['inicio'] = request.form.get('data_hora_inicio')
            dados_tempo['fim'] = request.form.get('data_hora_fim')
        elif tipo_evento == 'recorrente':
            # Coleta os dados específicos do formulário recorrente
            dia_semana = request.form.get('dia_semana')
            hora_inicio_rec = request.form.get('hora_inicio_recorrente')
            hora_fim_rec = request.form.get('hora_fim_recorrente')
            
            # Passa os dados brutos para o dicionário 'dados_tempo'
            dados_tempo['dia_semana'] = dia_semana
            dados_tempo['hora_inicio_recorrente'] = hora_inicio_rec
            dados_tempo['hora_fim_recorrente'] = hora_fim_rec
            dados_tempo['data_fim'] = request.form.get('data_fim_recorrencia')

        # Chama o serviço passando todos os dados
        sucesso = servico_admin.adicionar_evento(
            cpf_admin_organizador, nome_evento, desc_evento, tipo_evento, dados_tempo, lista_quadras
        )
        
        if sucesso:
            flash('Novo evento criado com sucesso!', 'success')
            return redirect(url_for('admin_gerenciar_eventos'))
        else:
            flash('Erro ao criar o evento. Verifique se os horários para eventos extraordinários não conflitam com agendamentos existentes.', 'error')
            return redirect(url_for('admin_form_evento'))

    # Lógica GET para exibir o formulário (sem alteração)
    todas_as_quadras = servico_admin.listar_quadras_para_gerenciar()
    todos_os_usuarios = servico_admin.listar_usuarios()
    lista_de_admins = [u for u in todos_os_usuarios if u['tipo'] == 'admin']
    
    return render_template('admin_form_evento.html', 
                           quadras=todas_as_quadras,
                           admins=lista_de_admins)

@app.route('/novo_agendamento/<int:ginasio_id>/<int:quadra_id>')
@app.route('/tabela_agendamento/<int:ginasio_id>/<int:quadra_id>')
def tabela_agendamento(ginasio_id, quadra_id):
    # 1. Lógica de navegação por semanas (mantida)
    semana_offset = request.args.get('semana', 0, type=int)
    hoje = datetime.now() + timedelta(weeks=semana_offset)
    segunda_feira = hoje - timedelta(days=hoje.weekday())
    dias_da_semana = [segunda_feira.date() + timedelta(days=i) for i in range(7)]
    
    data_inicio_semana = dias_da_semana[0]
    data_fim_semana = dias_da_semana[-1] + timedelta(days=1)

    # 2. Busca de dados
    dao = AgendamentoDAO()
    ocupacoes = dao.buscar_agendamentos_por_quadra(ginasio_id, quadra_id, data_inicio_semana, data_fim_semana)

    # 3. Processamento dos dados
    horarios = [f"{h:02d}:00" for h in range(7, 23)]
    agendamentos_por_dia = {dia: {hora: None for hora in horarios} for dia in dias_da_semana}

    dias_pt = { 'Monday': 'Toda Segunda-feira', 'Tuesday': 'Toda Terça-feira', 'Wednesday': 'Toda Quarta-feira', 'Thursday': 'Toda Quinta-feira', 'Friday': 'Toda Sexta-feira', 'Saturday': 'Todo Sábado', 'Sunday': 'Todo Domingo' }
    dias_map_num = { 'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6 }

    print("--- DEBUG: Processando Ocupações ---")
    for ocup in ocupacoes:
        print(f"Analisando: {ocup}")
        
        # Lógica para eventos recorrentes (verificada PRIMEIRO)
        if ocup['status'] == 'recorrente':
            regra = ocup['regra_recorrencia']
            print(f"  -> É recorrente. Regra: '{regra}'")
            
            match = re.search(r"Toda ([\w\s-]+), das (\d{2}:\d{2}) às (\d{2}:\d{2})", regra)
            
            if match:
                dia_evento_pt, hora_ini_str, hora_fim_str = match.groups()
                dia_semana_en = next((key for key, val in dias_pt.items() if val == f"Toda {dia_evento_pt}"), None)
                
                if dia_semana_en:
                    dia_semana_num = dias_map_num.get(dia_semana_en)
                    if dia_semana_num is not None:
                        data_do_evento_na_semana = dias_da_semana[dia_semana_num]
                        
                        hora_ini_evento = int(hora_ini_str[:2])
                        hora_fim_evento = int(hora_fim_str[:2])
                        
                        # ======================= INÍCIO DA CORREÇÃO =======================
                        
                        # Se a hora final for 00, trate como 24 para o range funcionar
                        if hora_fim_evento == 0:
                            hora_fim_evento = 24
                        
                        # ======================== FIM DA CORREÇÃO =========================
                        
                        for hora in range(hora_ini_evento, hora_fim_evento):
                            hora_str_loop = f"{hora:02d}:00"
                            if hora_str_loop in agendamentos_por_dia[data_do_evento_na_semana]:
                                agendamentos_por_dia[data_do_evento_na_semana][hora_str_loop] = ocup
                                print(f"    -> PREENCHIDO (Recorrente): {data_do_evento_na_semana} às {hora_str_loop}")
            else:
                print("    -> ERRO: A regra de recorrência não correspondeu ao padrão esperado.")


        # Lógica para agendamentos e eventos extraordinários
        elif ocup['hora_ini'] is not None and ocup['hora_fim'] is not None:
            
            # Verificação de segurança: só processa se o fim for depois do início
            if ocup['hora_fim'] <= ocup['hora_ini']:
                print(f"  -> AVISO: Ocupação ID (ou nome '{ocup['nome_evento']}') tem hora_fim antes de hora_ini. Pulando.")
                continue # Pula para a próxima ocupação no loop
            print(f"  -> É agendamento/extraordinário. Período: {ocup['hora_ini']} a {ocup['hora_fim']}")
            hora_atual = ocup['hora_ini']
            while hora_atual < ocup['hora_fim']:
                data = hora_atual.date()
                hora_str = f"{hora_atual.hour:02d}:00"
                if data in agendamentos_por_dia and hora_str in agendamentos_por_dia[data]:
                    agendamentos_por_dia[data][hora_str] = ocup
                    print(f"    -> PREENCHIDO: {data} às {hora_str}")
                hora_atual += timedelta(hours=1)
    print("--- FIM DEBUG ---")

    # 4. Busca de dados adicionais
    from camada_dados.agendamento_dao import get_ginasio_por_id
    ginasio = get_ginasio_por_id(ginasio_id)
    nome_ginasio = ginasio.nome if ginasio else f"Ginásio {ginasio_id}"
    
    from camada_dados.material_dao import MaterialDAO
    material_dao = MaterialDAO()
    # Chama o novo método para buscar materiais APENAS do ginásio atual
    materiais_disponiveis = material_dao.buscar_por_ginasio(ginasio_id)

    return render_template('tabela_agendamento.html', 
                         ginasio_id=ginasio_id, quadra_id=quadra_id, dias=dias_da_semana,
                         horarios=horarios, agendamentos_por_dia=agendamentos_por_dia,
                         semana_offset=semana_offset, nome_ginasio=nome_ginasio,
                         materiais_disponiveis=materiais_disponiveis)
    
@app.route('/fazer_agendamento', methods=['POST'])
def fazer_agendamento():
    print(f"=== INICIANDO FAZER_AGENDAMENTO ===")
    print(f"Sessão ANTES: {dict(session)}")
    
    # CORREÇÃO: Use 'usuario_logado' em vez de 'cpf_usuario'
    if 'usuario_logado' not in session:
        print("DEBUG: Usuário NÃO logado - redirecionando para login")
        flash('Você precisa estar logado para fazer um agendamento.', 'error')
        return redirect(url_for('login'))
    
    try:
        # CORREÇÃO: Pegue o CPF do objeto usuario_logado
        usuario = session['usuario_logado']
        cpf_usuario = usuario['cpf']
        
        id_ginasio = request.form.get('id_ginasio')
        num_quadra = request.form.get('num_quadra')
        data = request.form.get('data')
        hora_ini = request.form.get('hora_ini')
        hora_fim = request.form.get('hora_fim')
        
        print(f"DEBUG: Dados do formulário - CPF:{cpf_usuario}, Ginásio:{id_ginasio}, Quadra:{num_quadra}")
        print(f"DEBUG: Data:{data}, Hora:{hora_ini}-{hora_fim}")
        
        # Verificar se todos os campos estão presentes
        if not all([cpf_usuario, id_ginasio, num_quadra, data, hora_ini, hora_fim]):
            print("DEBUG: Campos faltando no formulário")
            flash('Dados incompletos para o agendamento.', 'error')
            return redirect(url_for('tabela_agendamento', ginasio_id=id_ginasio, quadra_id=num_quadra))
        
        # Converter para inteiros
        id_ginasio = int(id_ginasio)
        num_quadra = int(num_quadra)
        
        # Verificar disponibilidade
        from camada_dados.agendamento_dao import verificar_disponibilidade, criar_agendamento
        disponivel = verificar_disponibilidade(id_ginasio, num_quadra, data, hora_ini, hora_fim)
        print(f"DEBUG: Disponível? {disponivel}")
        
        if disponivel:
            # Criar agendamento
            sucesso = criar_agendamento(cpf_usuario, id_ginasio, num_quadra, data, hora_ini, hora_fim)
            print(f"DEBUG: Agendamento criado? {sucesso}")
            
            if sucesso:
                flash('Agendamento realizado com sucesso!', 'success')
            else:
                flash('Erro ao realizar agendamento.', 'error')
        else:
            flash('Horário indisponível.', 'error')
            print("DEBUG: Horário indisponível")
        
        print(f"Sessão DEPOIS: {dict(session)}")
        return redirect(url_for('tabela_agendamento', ginasio_id=id_ginasio, quadra_id=num_quadra))
        
    except Exception as e:
        print(f"ERRO GRAVE em fazer_agendamento: {e}")
        print(f"Sessão no ERRO: {dict(session)}")
        flash('Erro interno ao processar agendamento.', 'error')
        return redirect(url_for('index'))
    
@app.route('/fazer_agendamento_outra_pessoa', methods=['POST'])
def fazer_agendamento_outra_pessoa():
    """
    Rota para bolsistas fazerem agendamentos para outras pessoas.
    """
    print(f"=== INICIANDO FAZER_AGENDAMENTO_OUTRA_PESSOA ===")
    print(f"Sessão: {dict(session)}")
    
    # Verificar se é bolsista - CORREÇÃO: verificar eh_bolsista em vez de tipo
    if 'usuario_logado' not in session:
        print("DEBUG: Nenhum usuário logado")
        flash('Você precisa estar logado.', 'error')
        return redirect(url_for('login'))
    
    usuario = session['usuario_logado']
    
    # CORREÇÃO: Verificar eh_bolsista em vez do tipo
    if not usuario.get('eh_bolsista'):
        print(f"DEBUG: Usuário não é bolsista. eh_bolsista: {usuario.get('eh_bolsista')}")
        flash('Apenas bolsistas podem fazer reservas para outras pessoas.', 'error')
        return redirect(url_for('index'))
    
    print("DEBUG: Usuário é bolsista - continuando...")
    
    try:
        # Resto do código permanece igual...
        cpf_usuario = request.form.get('cpf_usuario')
        id_ginasio = request.form.get('id_ginasio')
        num_quadra = request.form.get('num_quadra')
        data = request.form.get('data')
        hora_ini = request.form.get('hora_ini')
        hora_fim = request.form.get('hora_fim')
        
        print(f"DEBUG: Dados recebidos - CPF:{cpf_usuario}, Ginásio:{id_ginasio}, Quadra:{num_quadra}")
        print(f"DEBUG: Data:{data}, Hora:{hora_ini}-{hora_fim}")

        
        # Verificar se todos os campos estão presentes
        if not all([cpf_usuario, id_ginasio, num_quadra, data, hora_ini, hora_fim]):
            print("DEBUG: Campos faltando no formulário")
            missing = []
            if not cpf_usuario: missing.append('CPF')
            if not id_ginasio: missing.append('Ginásio')
            if not num_quadra: missing.append('Quadra')
            if not data: missing.append('Data')
            if not hora_ini: missing.append('Hora Início')
            if not hora_fim: missing.append('Hora Fim')
            print(f"DEBUG: Campos em falta: {missing}")
            flash('Todos os campos são obrigatórios.', 'error')
            return redirect(url_for('tabela_agendamento', ginasio_id=id_ginasio, quadra_id=num_quadra))
        
        # Verificar se o usuário existe
        from camada_dados.agendamento_dao import verificar_usuario_existe
        usuario_existe = verificar_usuario_existe(cpf_usuario)
        print(f"DEBUG: Usuário {cpf_usuario} existe? {usuario_existe}")
        
        if not usuario_existe:
            flash('Usuário não encontrado.', 'error')
            print("DEBUG: Usuário não encontrado")
            return redirect(url_for('tabela_agendamento', ginasio_id=id_ginasio, quadra_id=num_quadra))
        
        # Converter para inteiros
        id_ginasio = int(id_ginasio)
        num_quadra = int(num_quadra)
        
        # Verificar disponibilidade
        from camada_dados.agendamento_dao import verificar_disponibilidade, criar_agendamento
        disponivel = verificar_disponibilidade(id_ginasio, num_quadra, data, hora_ini, hora_fim)
        print(f"DEBUG: Horário disponível? {disponivel}")
        
        if disponivel:
            # Criar agendamento para o outro usuário
            sucesso = criar_agendamento(cpf_usuario, id_ginasio, num_quadra, data, hora_ini, hora_fim)
            print(f"DEBUG: Agendamento criado com sucesso? {sucesso}")
            
            if sucesso:
                flash(f'Agendamento realizado com sucesso para o usuário {cpf_usuario}!', 'success')
                print("DEBUG: Agendamento para outra pessoa criado com sucesso!")
            else:
                flash('Erro ao realizar agendamento.', 'error')
                print("DEBUG: Erro ao criar agendamento para outra pessoa")
        else:
            flash('Horário indisponível.', 'error')
            print("DEBUG: Horário indisponível para outra pessoa")
        
        return redirect(url_for('tabela_agendamento', ginasio_id=id_ginasio, quadra_id=num_quadra))
        
    except Exception as e:
        print(f"ERRO em fazer_agendamento_outra_pessoa: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro interno ao processar agendamento.', 'error')
        return redirect(url_for('index'))
    

@app.route('/bolsista/agendamentos')
def bolsista_agendamentos():
    """
    Página para bolsistas visualizarem e gerenciarem todos os agendamentos.
    """
    if 'usuario_logado' not in session or not session['usuario_logado'].get('eh_bolsista'):
        flash('Acesso restrito a bolsistas.', 'error')
        return redirect(url_for('index'))
    
    usuario_info = session.get('usuario_logado', {})
    
    # Buscar todos os agendamentos do bolsista
    agendamentos = servico_bolsista.buscar_todos_agendamentos_bolsista(usuario_info['cpf'])
    
    # Separar agendamentos por status
    agendamentos_ativos = [a for a in agendamentos if a['status_agendamento'] == 'confirmado']
    agendamentos_cancelados = [a for a in agendamentos if a['status_agendamento'] == 'cancelado']
    agendamentos_realizados = [a for a in agendamentos if a['status_agendamento'] == 'realizado']
    
    return render_template('bolsista_agendamentos.html',
                         agendamentos_ativos=agendamentos_ativos,
                         agendamentos_cancelados=agendamentos_cancelados,
                         agendamentos_realizados=agendamentos_realizados)

@app.route('/bolsista/cancelar_agendamento/<int:id_agendamento>', methods=['POST'])
def bolsista_cancelar_agendamento(id_agendamento):
    """
    Rota para bolsistas cancelarem agendamentos.
    """
    print(f"DEBUG[ROTA BOLSISTA]: Cancelando agendamento {id_agendamento}")
    
    if 'usuario_logado' not in session or not session['usuario_logado'].get('eh_bolsista'):
        flash('Acesso restrito a bolsistas.', 'error')
        return redirect(url_for('index'))
    
    usuario_info = session.get('usuario_logado', {})
    
    # Usar o serviço para cancelar
    sucesso = servico_bolsista.cancelar_agendamento_bolsista(id_agendamento, usuario_info['cpf'])
    
    if sucesso:
        flash(f'Agendamento #{id_agendamento} cancelado com sucesso!', 'success')
        print(f"DEBUG[ROTA BOLSISTA]: Cancelamento bem-sucedido para agendamento {id_agendamento}")
    else:
        flash('Erro ao cancelar agendamento.', 'error')
        print(f"DEBUG[ROTA BOLSISTA]: Falha no cancelamento para agendamento {id_agendamento}")
    
    # Forçar um refresh da página para garantir que os dados atualizados sejam buscados
    return redirect(url_for('bolsista_agendamentos', _t=int(datetime.now().timestamp())))

@app.route('/bolsista/concluir_agendamento/<int:id_agendamento>', methods=['POST'])
def bolsista_concluir_agendamento(id_agendamento):
    """
    Rota para bolsistas marcarem agendamentos como concluídos.
    """
    if 'usuario_logado' not in session or not session['usuario_logado'].get('eh_bolsista'):
        flash('Acesso restrito a bolsistas.', 'error')
        return redirect(url_for('index'))
    
    usuario_info = session.get('usuario_logado', {})
    
    # Usar o serviço para marcar como concluído
    sucesso = servico_bolsista.marcar_como_concluido(id_agendamento, usuario_info['cpf'])
    
    if sucesso:
        flash(f'Agendamento #{id_agendamento} marcado como concluído com sucesso!', 'success')
    else:
        flash('Erro ao marcar agendamento como concluído.', 'error')
    
    return redirect(url_for('bolsista_agendamentos'))

@app.route('/teste_agendamento')
def teste_agendamento():
    from camada_dados.agendamento_dao import criar_agendamento, verificar_disponibilidade, verificar_estrutura_tabela
    
    print("=== INICIANDO TESTE COMPLETO ===")
    
    # 1. Verificar estrutura da tabela
    verificar_estrutura_tabela()
    
    # 2. Dados de teste
    cpf_teste = session.get('cpf_usuario', '68376340972')
    id_ginasio_teste = 1
    num_quadra_teste = 1
    data_teste = '2024-01-15'
    hora_ini_teste = '10:00'
    hora_fim_teste = '11:00'
    
    print("=== TESTE DE DISPONIBILIDADE ===")
    disponivel = verificar_disponibilidade(id_ginasio_teste, num_quadra_teste, data_teste, hora_ini_teste, hora_fim_teste)
    print(f"Disponibilidade: {disponivel}")
    
    if disponivel:
        print("=== TENTANDO CRIAR AGENDAMENTO ===")
        sucesso = criar_agendamento(cpf_teste, id_ginasio_teste, num_quadra_teste, data_teste, hora_ini_teste, hora_fim_teste)
        print(f"Agendamento criado: {sucesso}")
    else:
        print("=== AGENDAMENTO NÃO DISPONÍVEL ===")
    
    return "Teste realizado - verifique o console"

@app.route('/debug_bolsista')
def debug_bolsista():
    if 'usuario_logado' in session:
        usuario = session['usuario_logado']
        return f"""
        <h2>Debug Bolsista</h2>
        <p>Usuário: {usuario}</p>
        <p>CPF: {usuario.get('cpf')}</p>
        <p>Nome: {usuario.get('nome')}</p>
        <p>Tipo: {usuario.get('tipo')}</p>
        <p>É bolsista? {usuario.get('tipo') == 'bolsista'}</p>
        <p><a href="{{ url_for('tabela_agendamento', ginasio_id=1, quadra_id=1) }}">Ir para tabela</a></p>
        """
    else:
        return "Nenhum usuário logado"

@app.before_request
def debug_session():
    # Não debug em arquivos estáticos
    if request.endpoint and 'static' not in request.endpoint:
        print(f"=== DEBUG SESSÃO ===")
        print(f"Endpoint: {request.endpoint}")
        print(f"CPF na sessão: {session.get('cpf_usuario')}")
        print(f"Toda sessão: {dict(session)}")
        print("=====================")

@app.route('/teste_form_bolsista')
def teste_form_bolsista():
    """Página de teste direto do formulário"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Teste Form Bolsista</title>
    </head>
    <body>
        <h1>Teste Direto do Formulário</h1>
        <form action="/fazer_agendamento_outra_pessoa" method="post">
            <input type="hidden" name="id_ginasio" value="1">
            <input type="hidden" name="num_quadra" value="1">
            <input type="text" name="cpf_usuario" value="68376340972" required>
            <input type="date" name="data" value="2024-01-15" required>
            <input type="text" name="hora_ini" value="10:00" required>
            <input type="text" name="hora_fim" value="11:00" required>
            <button type="submit">ENVIAR TESTE</button>
        </form>
        
        <script>
            document.querySelector('form').addEventListener('submit', function(e) {
                console.log('Formulário de teste enviado!');
            });
        </script>
    </body>
    </html>
    '''
# Chamar esta função temporariamente na rota de bolsista para debug
@app.route('/bolsista/debug_estrutura')
def bolsista_debug_estrutura():
    if 'usuario_logado' not in session or not session['usuario_logado'].get('eh_bolsista'):
        return "Acesso negado"
    
    from camada_dados.agendamento_dao import verificar_estrutura_agendamento
    verificar_estrutura_agendamento()
    
    # Também verificar alguns agendamentos de exemplo
    conexao = conectar_mongo()
    cursor = conexao.cursor()
    cursor.execute("SELECT id_agendamento, cpf_usuario, id_bolsista_operador, status_agendamento FROM agendamento LIMIT 5")
    exemplos = cursor.fetchall()
    cursor.close()
    conexao.close()
    
    print(f"DEBUG: Exemplos de agendamentos: {exemplos}")
    
    return f"Estrutura verificada. Ver console. Exemplos: {exemplos}"

if __name__ == "__main__":
    app.run(debug=True)