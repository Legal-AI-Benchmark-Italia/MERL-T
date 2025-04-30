import logging
from typing import Any, Dict, List, Optional, Tuple
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession, Record, Query
from neo4j.exceptions import Neo4jError
import re
import os
import sys

# Aggiungiamo il percorso root al PYTHONPATH
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT_DIR)

from .base import BaseGraphStorage
from .neo4j_constraints import GENERIC_CONSTRAINT_QUERY, LEGAL_ENTITY_CONSTRAINTS, LEGAL_INDEX_QUERIES

# Importiamo il gestore di configurazione centralizzato
from src.core.config import get_config_manager

# Configurazione di logging con livello INFO di default
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Neo4jGraphStorage(BaseGraphStorage):
    """Implementazione di BaseGraphStorage per Neo4j specializzata per knowledge graph giuridico."""

    def __init__(self, uri: str = None, user: str = None, password: str = None, database: str = None):
        """
        Inizializza la connessione a Neo4j, utilizzando il ConfigManager se i parametri non sono specificati.

        Args:
            uri: URI del database Neo4j (es. "neo4j://localhost:7687").
            user: Nome utente per la connessione.
            password: Password per la connessione.
            database: Nome del database a cui connettersi.
        """
        # Ottieni il ConfigManager
        config_manager = get_config_manager()
        neo4j_params = config_manager.get_neo4j_connection_params()
        
        # Usa parametri forniti o predefiniti dal ConfigManager
        self._uri = uri or neo4j_params.get('uri')
        self._user = user or neo4j_params.get('user')
        self._password = password or neo4j_params.get('password')
        self._database = database or neo4j_params.get('database')
        
        self._driver: Optional[AsyncDriver] = None
        
        # Ottieni la configurazione aggiuntiva per Neo4j
        kg_config = config_manager.get_knowledge_graph_config()
        self._constraints_enabled = kg_config.get('constraints', {}).get('enable', True)
        self._max_retries = kg_config.get('constraints', {}).get('max_retries', 3)
        self._indices_enabled = kg_config.get('indices', {}).get('enable', True)
        self._fulltext_search = kg_config.get('indices', {}).get('fulltext_search', False)
        
        logger.info(f"Inizializzazione Neo4jGraphStorage per Knowledge Graph Giuridico: {self._database} su {self._uri}")
        logger.debug(f"Parametri di connessione configurati: uri={self._uri}, user={self._user}, database={self._database}")

    async def initialize(self) -> None:
        """Inizializza il driver Neo4j, verifica la connettività e crea constraint e indici."""
        if self._driver:
            logger.debug("Driver esistente trovato, chiusura in corso...")
            await self._driver.close()

        try:
            logger.debug(f"Creazione di un nuovo driver Neo4j per {self._uri}")
            self._driver = AsyncGraphDatabase.driver(self._uri, auth=(self._user, self._password))
            logger.debug("Verifica della connettività in corso...")
            await self._driver.verify_connectivity()
            logger.info("Connessione a Neo4j stabilita e verificata.")
            
            # Creazione dei constraint e indici per il knowledge graph giuridico
            if self._constraints_enabled:
                logger.debug("Creazione constraint e indici per migliorare le prestazioni...")
                await self._create_constraints()
                logger.info("Schema del Knowledge Graph giuridico inizializzato con successo.")
            else:
                logger.info("Creazione constraint e indici disabilitata nella configurazione.")
        except Neo4jError as e:
            logger.error(f"Errore durante la connessione o l'inizializzazione dello schema Neo4j: {e}")
            self._driver = None
            raise

    async def _create_constraints(self) -> None:
        """Crea constraint e indici per lo schema del knowledge graph giuridico."""
        async with self._driver.session(database=self._database) as session:
            try:
                # 1. Creiamo constraint generico (fallback)
                logger.debug(f"Creazione constraint generico: {GENERIC_CONSTRAINT_QUERY}")
                await session.run(GENERIC_CONSTRAINT_QUERY)
                logger.info("Constraint generico 'node_id_unique' creato/verificato.")
                
                # 2. Creiamo constraint specifici per entità giuridiche
                for constraint_query in LEGAL_ENTITY_CONSTRAINTS:
                    try:
                        logger.debug(f"Creazione constraint entità giuridica: {constraint_query}")
                        await session.run(constraint_query)
                    except Neo4jError as e:
                        # Alcune versioni di Neo4j potrebbero dare errori per syntax o altre ragioni
                        logger.warning(f"Errore durante la creazione del constraint '{constraint_query}': {e}")
                
                logger.info("Constraint per le entità giuridiche creati/verificati.")
                
                # 3. Creiamo indici per migliorare le prestazioni delle query più comuni
                if self._indices_enabled:
                    for index_query in LEGAL_INDEX_QUERIES:
                        try:
                            if "fulltext" in index_query.lower():
                                if not self._fulltext_search:
                                    logger.debug(f"Saltato indice fulltext (disabilitato nella configurazione): {index_query}")
                                    continue
                                # Gli indici fulltext richiedono Neo4j Enterprise e possono fallire silenziosamente
                                logger.debug(f"Tentativo di creazione indice fulltext (richiede Neo4j Enterprise): {index_query}")
                            else:
                                logger.debug(f"Creazione indice: {index_query}")
                            await session.run(index_query)
                        except Neo4jError as e:
                            logger.warning(f"Errore durante la creazione dell'indice '{index_query}': {e}")
                    
                    logger.info("Indici per il knowledge graph giuridico creati/verificati.")
                else:
                    logger.info("Creazione indici disabilitata nella configurazione.")
                
            except Neo4jError as e:
                logger.warning(f"Errore durante la creazione degli schema per il knowledge graph: {e}")
                logger.info("Il knowledge graph funzionerà comunque, ma potrebbe avere prestazioni non ottimali.")

    async def close(self) -> None:
        """Chiude la connessione al driver Neo4j."""
        if self._driver:
            logger.info("Chiusura della connessione Neo4j.")
            logger.debug("Chiamata al metodo close() del driver Neo4j")
            await self._driver.close()
            self._driver = None
            logger.debug("Driver Neo4j chiuso con successo.")

    async def _execute_read(self, query: str, params: Dict[str, Any] = None) -> List[Record]:
        """Esegue una query Cypher di lettura."""
        if not self._driver:
            logger.error("Tentativo di eseguire query senza driver inizializzato")
            raise ConnectionError("Driver Neo4j non inizializzato.")
        
        logger.debug(f"Esecuzione query di lettura: {query}, params: {params}")
        async with self._driver.session(database=self._database) as session:
            result = await session.run(query, params)
            # Raccolta dei record usando un loop asincrono invece di result.list()
            records = []
            async for record in result:
                records.append(record)
            logger.debug(f"Query di lettura completata, {len(records)} record restituiti")
            return records

    async def _execute_write(self, query: str, params: Dict[str, Any] = None) -> None:
        """Esegue una query Cypher di scrittura."""
        if not self._driver:
            logger.error("Tentativo di eseguire query senza driver inizializzato")
            raise ConnectionError("Driver Neo4j non inizializzato.")
        
        logger.debug(f"Esecuzione query di scrittura: {query}, params: {params}")
        async with self._driver.session(database=self._database) as session:
            await session.run(query, params) # run() in scrittura non restituisce dati direttamente
            logger.debug("Query di scrittura completata con successo")

    async def has_node(self, node_id: str) -> bool:
        """Verifica se un nodo esiste."""
        logger.debug(f"Verifica esistenza nodo con id: {node_id}")
        query = "MATCH (n {id: $node_id}) RETURN n LIMIT 1"
        result = await self._execute_read(query, {"node_id": node_id})
        exists = len(result) > 0
        logger.debug(f"Nodo {node_id} {'trovato' if exists else 'non trovato'}")
        return exists

    async def has_edge(self, source_node_id: str, target_node_id: str, relation_type: str = None) -> bool:
        """
        Verifica se un arco specifico esiste.
        Se relation_type è specificato, cerca solo relazioni di quel tipo.
        """
        logger.debug(f"Verifica esistenza arco da {source_node_id} a {target_node_id}")
        
        if relation_type:
            query = f"""
            MATCH (n1 {{id: $source_id}})-[r:{relation_type}]->(n2 {{id: $target_id}})
            RETURN r LIMIT 1
            """
        else:
            query = """
            MATCH (n1 {id: $source_id})-[r]->(n2 {id: $target_id})
            RETURN r LIMIT 1
            """
            
        result = await self._execute_read(query, {"source_id": source_node_id, "target_id": target_node_id})
        exists = len(result) > 0
        relation_info = f" di tipo {relation_type}" if relation_type else ""
        logger.debug(f"Arco{relation_info} da {source_node_id} a {target_node_id} {'trovato' if exists else 'non trovato'}")
        return exists

    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Recupera un nodo per ID insieme alle sue label."""
        logger.debug(f"Recupero nodo con id: {node_id}")
        query = """
        MATCH (n {id: $node_id}) 
        RETURN properties(n) as props, labels(n) as labels
        """
        result = await self._execute_read(query, {"node_id": node_id})
        if result:
            node_props = dict(result[0]["props"])
            node_labels = result[0]["labels"]
            # Aggiungiamo le label alle proprietà
            node_props["_labels"] = node_labels
            logger.debug(f"Nodo {node_id} trovato con proprietà: {node_props}")
            return node_props
        logger.debug(f"Nodo {node_id} non trovato")
        return None

    async def get_edge(self, source_node_id: str, target_node_id: str, relation_type: str = None) -> Optional[Dict[str, Any]]:
        """
        Recupera le proprietà di un arco specifico.
        Se relation_type è specificato, cerca solo relazioni di quel tipo.
        """
        logger.debug(f"Recupero proprietà arco da {source_node_id} a {target_node_id}")
        
        if relation_type:
            query = f"""
            MATCH (n1 {{id: $source_id}})-[r:{relation_type}]->(n2 {{id: $target_id}})
            RETURN properties(r) as props, type(r) as type LIMIT 1
            """
        else:
            query = """
            MATCH (n1 {id: $source_id})-[r]->(n2 {id: $target_id})
            RETURN properties(r) as props, type(r) as type LIMIT 1
            """
            
        result = await self._execute_read(query, {"source_id": source_node_id, "target_id": target_node_id})
        if result and result[0]["props"] is not None:
            edge_props = dict(result[0]["props"])
            edge_type = result[0]["type"]
            # Aggiungiamo il tipo di relazione alle proprietà
            edge_props["_type"] = edge_type
            logger.debug(f"Arco trovato con proprietà: {edge_props}")
            return edge_props
        relation_info = f" di tipo {relation_type}" if relation_type else ""
        logger.debug(f"Nessun arco{relation_info} trovato da {source_node_id} a {target_node_id}")
        return None

    async def get_node_edges(self, source_node_id: str, relation_type: str = None) -> List[Tuple[str, str, str]]:
        """
        Recupera tutti gli archi *uscenti* da un nodo.
        Esteso per supportare il filtraggio per tipo di relazione.
        Restituisce triple (source_id, relation_type, target_id)
        """
        logger.debug(f"Recupero archi uscenti dal nodo {source_node_id}")
        
        if relation_type:
            query = f"""
            MATCH (n1 {{id: $source_id}})-[r:{relation_type}]->(n2)
            RETURN n1.id AS source_id, type(r) as relation_type, n2.id AS target_id
            """
        else:
            query = """
            MATCH (n1 {id: $source_id})-[r]->(n2)
            RETURN n1.id AS source_id, type(r) as relation_type, n2.id AS target_id
            """
            
        result = await self._execute_read(query, {"source_id": source_node_id})
        if result:
            edges = [(record["source_id"], record["relation_type"], record["target_id"]) for record in result]
            relation_filter = f" di tipo {relation_type}" if relation_type else ""
            logger.debug(f"Trovati {len(edges)} archi{relation_filter} uscenti dal nodo {source_node_id}")
            return edges
        logger.debug(f"Nessun arco uscente trovato per il nodo {source_node_id}")
        return []

    async def upsert_node(self, node_id: str, node_data: Dict[str, Any]) -> None:
        """
        Inserisce o aggiorna un nodo.
        Gestisce correttamente i tipi di entità giuridiche.
        """
        logger.info(f"Upsert nodo con id: {node_id}")
        logger.debug(f"Dati nodo: {node_data}")
        
        # Assicurati che l'ID sia anche nei dati per MERGE
        node_properties = node_data.copy()
        # Non è necessario aggiungere l'ID qui se node_id è già usato correttamente nel MERGE
        # node_properties['id'] = node_id 

        # Usa la chiave corretta preparata da extractor.py
        label = node_properties.pop('entity_label', 'Node') # Get label and remove from props
        # Sanifica ulteriormente la label e assicurati che non sia vuota
        if not isinstance(label, str) or not label.strip():
            logger.warning(f"Label vuota o non valida per nodo ID {node_id}, usando 'Node' come fallback.")
            label = "Node"
        else:
            label = label.replace(" ", "") # Normalize label

        # Aggiunta protezione contro label non valide per Cypher (anche se la normalizzazione dovrebbe aiutare)
        label = re.sub(r'[^a-zA-Z0-9_]', '', label)
        if not label:
            logger.warning(f"Label diventata vuota dopo sanificazione per nodo ID {node_id}, usando 'Node' come fallback.")
            label = "Node"

        logger.debug(f"Label determinata per il nodo '{node_id}': {label}")
        
        # Rimuovi la label dal dizionario delle proprietà da impostare
        props_to_set = node_properties # node_properties è già una copia senza entity_label

        # Adatta la query in base alla label
        if label == 'Node':
            # Se la label è 'Node', cerca/crea :Node e aggiorna props.
            # Non rimuovere altre label specifiche eventualmente già presenti.
            query = f"""
            MERGE (n:Node {{id: $node_id}})
            SET n += $props
            """
            params = {"node_id": node_id, "props": props_to_set}
            logger.debug(f"Esecuzione upsert per :Node con ID {node_id}")
        else:
            # Se la label è specifica, cerca/crea il nodo per ID,
            # rimuovi la label :Node (se esiste) e imposta la nuova label specifica,
            # poi aggiorna le proprietà.
            # Assicurati che la label sia sicura (già fatto dalla sanificazione precedente)
            query = f"""
            MERGE (n {{id: $node_id}})
            ON CREATE SET n = $props, n:{label} 
            ON MATCH SET n += $props, n:{label}
            WITH n
            REMOVE n:Node
            """ 
            # Nota: SET n:{label} aggiunge la label se non c'è, non serve ON CREATE/ON MATCH separato per la label.
            # L'ordine è: trova/crea, imposta/aggiorna props e label specifica, Rimuovi :Node.
            params = {"node_id": node_id, "props": props_to_set}
            logger.debug(f"Esecuzione upsert per label specifica :{label} con ID {node_id}, rimuovendo :Node se presente.")

        await self._execute_write(query, params)
        logger.info(f"Nodo {node_id} di tipo {label} creato/aggiornato con successo")

    async def upsert_edge(self, source_node_id: str, target_node_id: str, edge_data: Dict[str, Any]) -> None:
        """
        Inserisce o aggiorna un arco.
        Gestisce correttamente i tipi di relazione giuridica.
        """
        logger.info(f"Upsert arco da {source_node_id} a {target_node_id}")
        logger.debug(f"Dati arco: {edge_data}")
        
        # Recupera il tipo di relazione GIÀ normalizzato da extractor.py
        # Il campo si chiama "legal_relation_type" in extractor.py
        relation_type = edge_data.get("legal_relation_type") 
        # Rimuovilo dal dizionario così non viene impostato come proprietà standard
        if "legal_relation_type" in edge_data:
            del edge_data["legal_relation_type"]

        # Fallback se non trovato (non dovrebbe accadere con la nuova logica)
        if not relation_type:
            relation_type = edge_data.pop('relation_type', 'RELATED_TO') # Vecchio fallback
            logger.warning(f"Tipo relazione 'legal_relation_type' non trovato in edge_data per {source_node_id}->{target_node_id}. Usato fallback: {relation_type}")

        # La normalizzazione (maiuscole, underscore, caratteri validi) 
        # è già stata fatta in get_normalized_relationship_type in extractor.py

        logger.debug(f"Tipo di relazione giuridica: {relation_type}")

        # Usiamo direttamente edge_data come props, dopo aver rimosso relation_type
        edge_properties = edge_data 

        # Query MERGE per creare o aggiornare l'arco
        query = f"""
        MATCH (n1 {{id: $source_id}}), (n2 {{id: $target_id}})
        MERGE (n1)-[r:{relation_type}]->(n2)
        SET r += $props
        """
        
        try:
            await self._execute_write(query, {
                "source_id": source_node_id,
                "target_id": target_node_id,
                "props": edge_properties
            })
            logger.info(f"Arco {relation_type} da {source_node_id} a {target_node_id} creato/aggiornato con successo")
        except Neo4jError as e:
            logger.error(f"Errore durante la creazione dell'arco: {e}")
            # Fallback: prova a creare una relazione generica in caso di problemi
            if "RELATED_TO" != relation_type:
                logger.warning(f"Tentativo fallback con relazione generica RELATED_TO")
                fallback_query = """
                MATCH (n1 {id: $source_id}), (n2 {id: $target_id})
                MERGE (n1)-[r:RELATED_TO]->(n2)
                SET r += $props
                """
                edge_properties["original_relation_type"] = relation_type  # Salva il tipo originale
                await self._execute_write(fallback_query, {
                    "source_id": source_node_id,
                    "target_id": target_node_id,
                    "props": edge_properties
                })
                logger.info(f"Arco RELATED_TO (fallback) da {source_node_id} a {target_node_id} creato con successo")
            else:
                raise  # Rilancia l'errore se anche il tipo di default fallisce

    async def delete_node(self, node_id: str) -> None:
        """Elimina un nodo e tutti i suoi archi."""
        logger.info(f"Eliminazione nodo {node_id} e relativi archi")
        query = "MATCH (n {id: $node_id}) DETACH DELETE n"
        await self._execute_write(query, {"node_id": node_id})
        logger.info(f"Nodo {node_id} eliminato con successo")

    async def remove_nodes(self, nodes: List[str]) -> None:
        """Elimina una lista di nodi."""
        # Esegui l'eliminazione in batch per efficienza, se possibile
        logger.info(f"Eliminazione di {len(nodes)} nodi: {nodes}")
        query = "MATCH (n) WHERE n.id IN $node_ids DETACH DELETE n"
        await self._execute_write(query, {"node_ids": nodes})
        logger.info(f"{len(nodes)} nodi eliminati con successo")

    async def remove_edges(self, edges: List[Tuple[str, str, str]]) -> None:
        """
        Elimina una lista di archi.
        Formato di ogni elemento in edges: (source_id, relation_type, target_id)
        Se relation_type è None, elimina tutte le relazioni tra source e target.
        """
        logger.info(f"Eliminazione di {len(edges)} archi")
        
        for source_id, relation_type, target_id in edges:
            if relation_type:
                query = f"""
                MATCH (n1 {{id: $source_id}})-[r:{relation_type}]->(n2 {{id: $target_id}})
                DELETE r
                """
            else:
                query = """
                MATCH (n1 {id: $source_id})-[r]->(n2 {id: $target_id})
                DELETE r
                """
                
            logger.debug(f"Eliminazione arco {'di tipo ' + relation_type if relation_type else ''} da {source_id} a {target_id}")
            await self._execute_write(query, {"source_id": source_id, "target_id": target_id})
            
        logger.info(f"{len(edges)} archi eliminati con successo")

    async def get_all_labels(self) -> List[str]:
        """Recupera tutte le label dei nodi presenti nel database."""
        logger.debug("Recupero di tutte le label dei nodi presenti nel database")
        query = "CALL db.labels() YIELD label RETURN label"
        result = await self._execute_read(query)
        labels = [record["label"] for record in result]
        logger.debug(f"Label trovate: {labels}")
        return labels

    async def get_all_relationship_types(self) -> List[str]:
        """Recupera tutti i tipi di relazione presenti nel database."""
        logger.debug("Recupero di tutti i tipi di relazione presenti nel database")
        query = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        result = await self._execute_read(query)
        types = [record["relationshipType"] for record in result]
        logger.debug(f"Tipi di relazione trovati: {types}")
        return types

    async def get_knowledge_graph(
        self, 
        node_label: Optional[str] = None, 
        depth: int = 3, 
        limit: int = 1000,
        relation_types: List[str] = None
    ) -> Any:
        """
        Recupera un sottografo del knowledge graph giuridico.
        
        Args:
            node_label: Label dei nodi da cui partire (opzionale)
            depth: Profondità massima del grafo
            limit: Limite massimo di percorsi da restituire
            relation_types: Lista di tipi di relazione da considerare (opzionale)
            
        Returns:
            Lista di percorsi (nodi e relazioni)
        """
        logger.info(f"Recupero knowledge graph giuridico con label: {node_label}, profondità: {depth}, limite: {limit}")
        
        # Costruisci la query in base ai parametri
        if node_label:
            match_clause = f"MATCH p=(n:{node_label})"
        else:
            match_clause = f"MATCH p=(n)"
            
        # Aggiungi filtro su tipi di relazione se specificato
        if relation_types:
            rel_filter = "|".join([f"{rel_type}" for rel_type in relation_types])
            path_pattern = f"-[:{rel_filter}*1..{depth}]-"
        else:
            path_pattern = f"-[*1..{depth}]-"
            
        match_clause += f"{path_pattern}(m)"
        
        logger.debug(f"Clausola MATCH per la query: {match_clause}")

        query = f"""
        {match_clause}
        RETURN p LIMIT {limit}
        """
        
        logger.info(f"Recupero knowledge graph con query: {query}")
        async with self._driver.session(database=self._database) as session:
            logger.debug(f"Esecuzione query: {query}")
            result = await session.run(Query(query))
            
            # Estrarre e formattare i dati dai percorsi Neo4j
            paths_data = []
            async for record in result:
                 path = record["p"]
                 path_info = {
                     "nodes": [dict(node.items()) for node in path.nodes],
                     "relationships": [
                         {
                             "start_node": dict(rel.start_node.items()),
                             "end_node": dict(rel.end_node.items()),
                             "type": rel.type,
                             "properties": dict(rel.items())
                         } for rel in path.relationships]
                 }
                 paths_data.append(path_info)
            
            logger.info(f"Trovati {len(paths_data)} percorsi nel knowledge graph giuridico")
            return paths_data

    async def get_legal_entity_by_name(self, name: str, entity_type: str = None) -> List[Dict[str, Any]]:
        """
        Cerca entità giuridiche per nome (ricerca parziale).
        
        Args:
            name: Nome o parte del nome da cercare
            entity_type: Tipo di entità giuridica (opzionale)
            
        Returns:
            Lista di entità trovate
        """
        logger.debug(f"Ricerca entità giuridiche con nome contenente '{name}'")
        
        if entity_type:
            query = f"""
            MATCH (n:{entity_type})
            WHERE n.name CONTAINS $name
            RETURN n
            LIMIT 10
            """
        else:
            query = """
            MATCH (n)
            WHERE n.name CONTAINS $name
            RETURN n
            LIMIT 10
            """
            
        result = await self._execute_read(query, {"name": name})
        entities = [dict(record["n"].items()) for record in result]
        
        logger.debug(f"Trovate {len(entities)} entità contenenti '{name}'")
        return entities

    async def get_related_entities(
        self, 
        entity_id: str, 
        relation_type: str = None, 
        target_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        Trova entità correlate ad un'entità specifica.
        
        Args:
            entity_id: ID dell'entità di partenza
            relation_type: Tipo di relazione da cercare (opzionale)
            target_type: Tipo di entità target da cercare (opzionale)
            
        Returns:
            Lista di tuple (entità_target, tipo_relazione)
        """
        logger.debug(f"Ricerca entità correlate a '{entity_id}'")
        
        # Costruisci la query in base ai parametri
        if relation_type and target_type:
            query = f"""
            MATCH (n {{id: $entity_id}})-[r:{relation_type}]->(m:{target_type})
            RETURN m, type(r) as relation_type
            """
        elif relation_type:
            query = f"""
            MATCH (n {{id: $entity_id}})-[r:{relation_type}]->(m)
            RETURN m, type(r) as relation_type
            """
        elif target_type:
            query = f"""
            MATCH (n {{id: $entity_id}})-[r]->(m:{target_type})
            RETURN m, type(r) as relation_type
            """
        else:
            query = """
            MATCH (n {id: $entity_id})-[r]->(m)
            RETURN m, type(r) as relation_type
            """
            
        result = await self._execute_read(query, {"entity_id": entity_id})
        related = [(dict(record["m"].items()), record["relation_type"]) for record in result]
        
        logger.debug(f"Trovate {len(related)} entità correlate a '{entity_id}'")
        return related

    async def index_done_callback(self) -> bool:
        """Callback dopo che l'indicizzazione è completata."""
        logger.info("Callback index_done chiamato.")
        
        try:
            # Esegui statistiche sul grafo per verifica
            async with self._driver.session(database=self._database) as session:
                # Conteggio nodi per tipo
                node_count_query = """
                MATCH (n)
                RETURN labels(n) as type, count(*) as count
                ORDER BY count DESC
                """
                result = await session.run(node_count_query)
                logger.info("Statistiche del Knowledge Graph giuridico:")
                
                node_counts = []
                async for record in result:
                    node_type = record["type"][0] if record["type"] else "Unknown"
                    count = record["count"]
                    node_counts.append(f"{node_type}: {count}")
                
                if node_counts:
                    logger.info(f"Distribuzione nodi per tipo: {', '.join(node_counts)}")
                else:
                    logger.info("Nessun nodo trovato nel grafo")
                
                # Conteggio relazioni per tipo
                rel_count_query = """
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as count
                ORDER BY count DESC
                """
                result = await session.run(rel_count_query)
                
                rel_counts = []
                async for record in result:
                    rel_type = record["type"]
                    count = record["count"]
                    rel_counts.append(f"{rel_type}: {count}")
                
                if rel_counts:
                    logger.info(f"Distribuzione relazioni per tipo: {', '.join(rel_counts)}")
                else:
                    logger.info("Nessuna relazione trovata nel grafo")
                
                return True
        except Exception as e:
            logger.error(f"Errore durante l'analisi statistica del grafo: {e}")
            return False

    async def drop(self) -> Dict[str, str]:
        """Elimina tutti i dati dal database (NODI E RELAZIONI). ATTENZIONE!"""
        logger.warning(f"Tentativo di eliminare TUTTI i dati dal database: {self._database}")
        try:
            query = "MATCH (n) DETACH DELETE n"
            logger.debug(f"Esecuzione query per eliminare tutti i dati: {query}")
            await self._execute_write(query)
            logger.info(f"Tutti i dati eliminati con successo dal database: {self._database}")
            return {"status": "success", "message": f"Knowledge Graph giuridico svuotato."}
        except Neo4jError as e:
            logger.error(f"Errore durante l'eliminazione dei dati: {e}")
            return {"status": "error", "message": str(e)}

    async def __aenter__(self):
        """Supporto per context manager async: inizializza la connessione."""
        logger.debug("Chiamata __aenter__ del context manager")
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Supporto per context manager async: chiude la connessione."""
        logger.debug("Chiamata __aexit__ del context manager")
        await self.close()

    async def get_node_neighborhood(self, seed_node_id: str) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """Recupera il vicinato a 1 hop (nodi e relazioni) per un dato seed node ID."""
        logger.debug(f"Recupero vicinato per seed node: {seed_node_id}")
        query = """
        MATCH (seed {id: $seedId})-[r]-(neighbor)
        RETURN
          seed {.*, _labels: labels(seed)} as seedNode,
          neighbor {.*, _labels: labels(neighbor)} as neighborNode,
          r {.*, _type: type(r), _start: seed.id, _end: neighbor.id} as relationship
        """
        # Note: _start and _end now use the application IDs directly
        
        try:
            results = await self._execute_read(query, {"seedId": seed_node_id})
            
            if not results:
                logger.warning(f"Nessun vicinato trovato per il seed node {seed_node_id}")
                # Check if the seed node exists at all
                seed_exists = await self.has_node(seed_node_id)
                if not seed_exists:
                     logger.error(f"Seed node {seed_node_id} non trovato nel grafo.")
                return None
            
            nodes_map = {}
            edges_map = {}
            
            for record in results:
                seed_data = dict(record["seedNode"])
                neighbor_data = dict(record["neighborNode"])
                rel_data = dict(record["relationship"])
                
                # Add nodes to map (avoids duplicates)
                if seed_data["id"] not in nodes_map:
                    nodes_map[seed_data["id"]] = seed_data
                if neighbor_data["id"] not in nodes_map:
                    nodes_map[neighbor_data["id"]] = neighbor_data
                
                # Format and add relationship
                rel_id = rel_data.get('id') # Relationships might not have a custom ID 
                if not rel_id:
                    # Generate a temporary ID if missing, based on nodes and type
                    rel_id = f"{rel_data['_start']}-{rel_data['_type']}-{rel_data['_end']}"
                
                if rel_id not in edges_map:
                    formatted_edge = {
                        "id": rel_id,
                        "source": rel_data['_start'],
                        "target": rel_data['_end'],
                        "type": rel_data['_type']
                    }
                    # Add other properties, excluding internal ones
                    for key, value in rel_data.items():
                        if not key.startswith('_'):
                            formatted_edge[key] = value
                    edges_map[rel_id] = formatted_edge
            
            neighborhood_data = {
                "nodes": list(nodes_map.values()),
                "edges": list(edges_map.values())
            }
            logger.debug(f"Vicinato per {seed_node_id} recuperato: {len(neighborhood_data['nodes'])} nodi, {len(neighborhood_data['edges'])} relazioni.")
            return neighborhood_data
            
        except Exception as e:
            logger.error(f"Errore nel recupero del vicinato per {seed_node_id}: {e}")
            logger.exception(e)
            return None