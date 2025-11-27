// ====================================================================
// Script para configuração inicial do banco de dados MongoDB
// para o Sistema de Agendamento de Quadras
// ====================================================================

// Conecta-se ao banco de dados 'udesc_quadras'. Se não existir, ele será criado.
const dbName = 'udesc_quadras';
const conn = new Mongo();
const db = conn.getDB(dbName);

print(`Conectado ao banco de dados: ${dbName}`);

// --- Limpa as coleções existentes para garantir um estado inicial limpo ---
print("Limpando coleções existentes...");
db.usuarios.drop();
db.ginasios.drop();
db.esportes.drop();
db.agendamentos.drop();
db.eventos.drop();
db.chamados.drop();

// ====================================================================
// 1. COLEÇÃO: usuarios
// Estrutura: Documento único por usuário, com sub-documentos para especializações.
// Usamos o CPF como chave primária (_id) para garantir unicidade.
// ====================================================================
print("Criando a coleção 'usuarios' e inserindo dados de exemplo...");
db.usuarios.insertMany([
    // Exemplo de Aluno
    {
        _id: "11122233344", // CPF como _id
        nome: "José Testador",
        email: "jose@teste.com",
        senha: "123", // Em um sistema real, seria um hash
        data_nasc: new Date("2002-05-10"),
        status: "ativo",
        tipo: "aluno",
        detalhes_aluno: {
            matricula: "202501",
            curso: "Ciência da Computação",
            ano_inicio: 2025,
            categoria: "nao_bolsista"
        }
    },
    // Exemplo de Aluno Bolsista
    {
        _id: "22233344455",
        nome: "Ana Bolsista",
        email: "ana.bolsista@email.com",
        senha: "123",
        data_nasc: new Date("2003-02-15"),
        status: "ativo",
        tipo: "aluno", // Continua sendo 'aluno'
        detalhes_aluno: {
            matricula: "202502",
            curso: "Engenharia de Software",
            ano_inicio: 2025,
            categoria: "bolsista",
            valor_remuneracao: 700.00,
            carga_horaria: 20,
            horario_inicio: "13:30",
            horario_fim: "17:30",
            id_supervisor_servidor: "SERV001" // Referência ao ID do supervisor
        }
    },
    // Exemplo de Servidor (que também é Admin)
    {
        _id: "00000000000",
        nome: "Administrador Geral",
        email: "admin@sistema.com",
        senha: "admin123",
        data_nasc: new Date("1990-01-01"),
        status: "ativo",
        tipo: "admin",
        detalhes_servidor: {
            id_servidor: "SERV001",
            data_admissao: new Date("2020-03-01")
        },
        detalhes_admin: {
            nivel_acesso: 1,
            area_responsabilidade: "Gestão Geral"
        }
    }
]);

// ====================================================================
// 2. COLEÇÃO: ginasios
// Estrutura: Embutimos as quadras e os materiais esportivos dentro de cada ginásio.
// Isso evita a necessidade de JOINs constantes.
// ====================================================================
print("Criando a coleção 'ginasios' com quadras e materiais embutidos...");
db.ginasios.insertMany([
    {
        _id: 1, // ID numérico para facilitar a referência
        nome: 'Ginásio Principal A',
        endereco: 'Rua UDESC, 123',
        capacidade: 1000,
        quadras: [
            { num_quadra: 1, capacidade: 100, tipo_piso: 'Madeira', cobertura: true, status: 'disponivel', esportes_permitidos: [1, 3] }, // IDs da coleção 'esportes'
            { num_quadra: 2, capacidade: 80, tipo_piso: 'Cimento', cobertura: true, status: 'manutencao', esportes_permitidos: [2] }
        ],
        materiais_esportivos: [
            { id_material: 101, nome: 'Bola de Basquete', descricao: 'Tamanho oficial', marca: 'Spalding', status: 'bom', qnt_total: 10, qnt_disponivel: 8 },
            { id_material: 102, nome: 'Bola de Vôlei', descricao: 'Couro sintético', marca: 'Penalty', status: 'bom', qnt_total: 15, qnt_disponivel: 15 }
        ]
    },
    {
        _id: 2,
        nome: 'Ginásio Anexo B',
        endereco: 'Rua dos Esportes, 456',
        capacidade: 500,
        quadras: [
            { num_quadra: 1, capacidade: 50, tipo_piso: 'Areia', cobertura: false, status: 'disponivel', esportes_permitidos: [3] }
        ],
        materiais_esportivos: [
            { id_material: 201, nome: 'Rede de Vôlei de Praia', marca: 'Master Rede', status: 'manutencao', qnt_total: 2, qnt_disponivel: 1 }
        ]
    }
]);

// ====================================================================
// 3. COLEÇÃO: esportes
// Estrutura: Coleção simples para manter a lista de esportes.
// ====================================================================
print("Criando a coleção 'esportes'...");
db.esportes.insertMany([
    { _id: 1, nome: 'Basquete', max_jogadores: 10 },
    { _id: 2, nome: 'Futsal', max_jogadores: 10 },
    { _id: 3, nome: 'Vôlei', max_jogadores: 12 }
]);

// ====================================================================
// 4. COLEÇÃO: agendamentos
// Estrutura: Desnormalizada. Embutimos informações do usuário e do local
// para evitar buscas adicionais ao listar agendamentos.
// ====================================================================
print("Criando a coleção 'agendamentos' com dados desnormalizados...");
db.agendamentos.insertOne({
    // O _id é gerado automaticamente pelo MongoDB (ObjectId)
    cpf_usuario: "11122233344",
    // Informações embutidas para leitura rápida
    usuario_info: {
        nome: "José Testador"
    },
    id_ginasio: 1,
    num_quadra: 1,
    local_info: {
        nome_ginasio: "Ginásio Principal A"
    },
    data_solicitacao: new Date(),
    hora_ini: new Date(new Date().setDate(new Date().getDate() + 1)), // Amanhã
    hora_fim: new Date(new Date().setDate(new Date().getDate() + 1) + 3600*1000), // Amanhã + 1 hora
    motivo: "Treino de Basquete",
    status_agendamento: "confirmado",
    // Campos opcionais podem simplesmente não existir
    // id_bolsista_operador: null,
    materiais_solicitados: [ // Exemplo de como a tabela de junção é representada
        { id_material: 101, nome: 'Bola de Basquete', quantidade: 2 }
    ]
});

// ====================================================================
// 5. COLEÇÃO: eventos
// Estrutura: Também desnormalizada. Embutimos as quadras bloqueadas
// diretamente no documento do evento.
// ====================================================================
print("Criando a coleção 'eventos'...");
db.eventos.insertOne({
    nome: "Campeonato Intercursos",
    descricao: "Primeira fase do campeonato.",
    cpf_admin_organizador: "00000000000",
    admin_info: {
        nome: "Administrador Geral"
    },
    tipo: "extraordinario", // 'extraordinario' ou 'recorrente'
    // Dados temporais dependem do tipo
    data_hora_inicio: new Date(new Date().setDate(new Date().getDate() + 2)), // Daqui a 2 dias
    data_hora_fim: new Date(new Date().setDate(new Date().getDate() + 2) + 4*3600*1000), // Daqui a 2 dias, com 4h de duração
    quadras_bloqueadas: [
        { id_ginasio: 1, num_quadra: 1 },
        { id_ginasio: 1, num_quadra: 2 }
    ]
});


// ====================================================================
// 6. COLEÇÃO: chamados (de manutenção)
// ====================================================================
print("Criando a coleção 'chamados'...");
db.chamados.insertOne({
    cpf_usuario_abriu: "22233344455",
    usuario_info: {
        nome: "Ana Bolsista"
    },
    id_ginasio: 2,
    num_quadra: 1,
    local_info: {
        nome_ginasio: "Ginásio Anexo B"
    },
    data: new Date(),
    descricao: "A rede da quadra de areia está rasgada.",
    status: "aberto" // 'aberto', 'em_atendimento', 'resolvido'
});


print("\nConfiguração do banco de dados MongoDB concluída com sucesso!");