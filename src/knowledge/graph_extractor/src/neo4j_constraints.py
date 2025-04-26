"""
Modulo per la gestione dei constraint Neo4j specifici per il knowledge graph giuridico.
"""

# Query per creare constraint generici
# Modificato ASSERT con REQUIRE per compatibilità con versioni Neo4j recenti
GENERIC_CONSTRAINT_QUERY = "CREATE CONSTRAINT node_id_unique IF NOT EXISTS FOR (n:Node) REQUIRE n.id IS UNIQUE"

# Constraint specifici per ogni tipo di entità giuridica
# Modificato ASSERT con REQUIRE
LEGAL_ENTITY_CONSTRAINTS = [
    "CREATE CONSTRAINT norma_id_unique IF NOT EXISTS FOR (n:Norma) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT concetto_id_unique IF NOT EXISTS FOR (n:ConcettoGiuridico) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT soggetto_id_unique IF NOT EXISTS FOR (n:SoggettoGiuridico) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT atto_id_unique IF NOT EXISTS FOR (n:AttoGiudiziario) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT fonte_id_unique IF NOT EXISTS FOR (n:FonteDiritto) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT dottrina_id_unique IF NOT EXISTS FOR (n:Dottrina) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT procedura_id_unique IF NOT EXISTS FOR (n:Procedura) REQUIRE n.id IS UNIQUE"
]

# Query per creare indici per supportare le ricerche più comuni
LEGAL_INDEX_QUERIES = [
    # Indice per cercare norme per nome
    "CREATE INDEX norma_name_idx IF NOT EXISTS FOR (n:Norma) ON (n.name)",
    
    # Indice per cercare concetti giuridici
    "CREATE INDEX concetto_name_idx IF NOT EXISTS FOR (n:ConcettoGiuridico) ON (n.name)",
    
    # Indice full-text per ricerche sulla descrizione (richiede Neo4j Enterprise)
    # "CALL db.index.fulltext.createNodeIndex('description_fulltext', ['Norma', 'ConcettoGiuridico', 'AttoGiudiziario'], ['description'])" # Commentato: richiede Enterprise Edition o configurazione specifica
]

# Query di esempio per verificare lo schema dopo la creazione
SCHEMA_CHECK_QUERY = """
CALL db.schema.visualization()
"""

# Query per ottenere statistiche sul grafo
GRAPH_STATS_QUERY = """
MATCH (n)
RETURN labels(n) as label, count(*) as count
ORDER BY count DESC
"""

# Query relazioni frequenti
RELATION_STATS_QUERY = """
MATCH ()-[r]->()
RETURN type(r) as type, count(*) as count
ORDER BY count DESC
"""

# Query di esempio per ricerche comuni
EXAMPLE_QUERIES = {
    "search_norm_by_name": "MATCH (n:Norma) WHERE n.name CONTAINS 'Art. 1414' RETURN n",
    "find_related_concepts": "MATCH (n:Norma)-[:DISCIPLINA]->(c:ConcettoGiuridico) RETURN n.name, c.name",
    "find_interpretation": "MATCH (a:AttoGiudiziario)-[:INTERPRETA]->(n:Norma) RETURN a.name, n.name",
    "complex_path": """
        MATCH path = (s:SoggettoGiuridico)-[r1:EMESSO_DA]->(a:AttoGiudiziario)-[r2:INTERPRETA]->(n:Norma)
        RETURN path LIMIT 10
    """
}