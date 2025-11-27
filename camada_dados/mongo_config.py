from pymongo import MongoClient

def conectar_mongo():
    """
    Estabelece a conexão com o banco de dados MongoDB.
    Retorna a instância do banco de dados (db).
    """
    try:
        # String de conexão padrão para um MongoDB local
        client = MongoClient('mongodb://localhost:27017/')
        
        # Seleciona o banco de dados 'udesc_quadras'
        db = client['udesc_quadras']
        
        print("✅ Conexão com o MongoDB estabelecida com sucesso.")
        return db
    except Exception as e:
        print(f"❌ Erro ao conectar ao MongoDB: {e}")
        return None
