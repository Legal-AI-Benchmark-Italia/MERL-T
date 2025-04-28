from typing import Any, Dict, List
from src.core.entities.entity_manager import get_entity_manager

GRAPH_FIELD_SEP = "<SEP>"

# Ora PROMPTS contiene template con placeholder
PROMPTS_TEMPLATES: dict[str, str] = {}

# Esempio aggiornato per il dominio giuridico - Manteniamo l'esempio hardcoded
# perché è più facile da gestire che generarlo dinamicamente.
PROMPTS_TEMPLATES["examples"] = '''Input: "L'Art. 1414 c.c. disciplina la simulazione del contratto. La simulazione è un istituto giuridico che si verifica quando le parti di un contratto manifestano esternamente una volontà diversa da quella reale. La Cassazione, con sentenza n. 5134/2008, ha interpretato la norma stabilendo che l'azione di regolamento di confini è imprescrittibile."
Output:
("entity"<|>{tuple_delimiter}<|>Art. 1414 c.c.<|>{tuple_delimiter}<|>Norma<|>{tuple_delimiter}<|>Norma del codice civile che disciplina la simulazione del contratto)##{record_delimiter}##
("entity"<|>{tuple_delimiter}<|>Simulazione<|>{tuple_delimiter}<|>ConcettoGiuridico<|>{tuple_delimiter}<|>Istituto giuridico che si verifica quando le parti di un contratto manifestano esternamente una volontà diversa da quella reale)##{record_delimiter}##
("entity"<|>{tuple_delimiter}<|>Cassazione<|>{tuple_delimiter}<|>SoggettoGiuridico<|>{tuple_delimiter}<|>Organo giurisdizionale supremo che assicura l'esatta osservanza e l'uniforme interpretazione della legge)##{record_delimiter}##
("entity"<|>{tuple_delimiter}<|>Sentenza n. 5134/2008<|>{tuple_delimiter}<|>AttoGiudiziario<|>{tuple_delimiter}<|>Pronuncia della Cassazione che ha stabilito l'imprescrittibilità dell'azione di regolamento di confini)##{record_delimiter}##
("entity"<|>{tuple_delimiter}<|>Codice Civile<|>{tuple_delimiter}<|>FonteDiritto<|>{tuple_delimiter}<|>Raccolta organica di norme che regolano i rapporti civili)##{record_delimiter}##
("relationship"<|>{tuple_delimiter}<|>Art. 1414 c.c.<|>{tuple_delimiter}<|>Simulazione<|>{tuple_delimiter}<|>Disciplina l'istituto giuridico<|>{tuple_delimiter}<|>DISCIPLINA<|>{tuple_delimiter}<|>0.9)##{record_delimiter}##
("relationship"<|>{tuple_delimiter}<|>Sentenza n. 5134/2008<|>{tuple_delimiter}<|>Art. 1414 c.c.<|>{tuple_delimiter}<|>Fornisce interpretazione della norma<|>{tuple_delimiter}<|>INTERPRETA<|>{tuple_delimiter}<|>0.8)##{record_delimiter}##
("relationship"<|>{tuple_delimiter}<|>Art. 1414 c.c.<|>{tuple_delimiter}<|>Codice Civile<|>{tuple_delimiter}<|>È contenuto nella fonte normativa<|>{tuple_delimiter}<|>FONTE<|>{tuple_delimiter}<|>0.9)##{record_delimiter}##
("relationship"<|>{tuple_delimiter}<|>Cassazione<|>{tuple_delimiter}<|>Sentenza n. 5134/2008<|>{tuple_delimiter}<|>Ha emesso il provvedimento<|>{tuple_delimiter}<|>EMESSO_DA<|>{tuple_delimiter}<|>0.9)
''' # Nota: Aggiustati i delimitatori nell'esempio per usare i placeholder

# Template per l'estrazione delle entità
PROMPTS_TEMPLATES["entity_extraction"] = """---Goal---
Given a text document that is potentially relevant to legal analysis and a list of entity types, identify all legal entities of those types from the text and all relationships among the identified entities.
Use {language} as output language.

---Steps---
1. Identify all legal entities. For each identified entity, extract the following information:
- entity_name: Name of the entity, use same language as input text. Preserve original references (e.g., "Art. 1414 c.c.") 
- entity_type: One of the following types: [{entity_types_str}]
- entity_description: Comprehensive description of the entity's attributes and purpose in the legal system
Format each entity as ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. From the entities identified in step 1, identify all pairs of (source_entity, target_entity) that are *clearly related* to each other.
For each pair of related entities, extract the following information:
- source_entity: name of the source entity, as identified in step 1
- target_entity: name of the target entity, as identified in step 1
- relationship_description: explanation as to why you think the source entity and the target entity are related to each other
- relationship_keywords: use one of the following legal relationship types that best describes the relationship (
    {relationship_keywords_str}
    ) 
- relationship_strength: a numeric score indicating strength of the relationship between the source entity and target entity (0.0 to 1.0)
Format each relationship as ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)

3. Identify high-level legal concepts and themes that summarize the main legal topics of the entire text.
Format the content-level key words as ("content_keywords"{tuple_delimiter}<high_level_keywords>)

4. Return output in {language} as a single list of all the entities and relationships identified in steps 1 and 2. Use **{record_delimiter}** as the list delimiter.

5. When finished, output {completion_delimiter}

######################
---Examples---
######################
{examples}

#############################
---Real Data---
######################
Entity_types: [{entity_types_str}]
Input text: {input_text}"""

# Template per la continuazione dell'estrazione
PROMPTS_TEMPLATES["entity_continue_extraction"] = """Continue extracting more legal entities and relationships from the same text. Focus on finding any legal entities or relationships that might have been missed in the previous extraction.

Remember to use the correct entity types: [{entity_types_str}]
And relationship types: 
    {relationship_keywords_str}

Use the same format as before:
- For entities: ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)
- For relationships: ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)
- For content keywords: ("content_keywords"{tuple_delimiter}<high_level_keywords>)

Use {record_delimiter} as the list delimiter.
When finished, output {completion_delimiter}"""

# Template per il controllo del loop
PROMPTS_TEMPLATES["entity_if_loop_extraction"] = """Based on the previous extractions, are there any more legal entities or relationships that could be extracted from the text? If yes, continue extracting. If no, just output {completion_delimiter}."""

def enrich_prompt_with_entity_descriptions(prompt_template, config):
    """Arricchisce il prompt con descrizioni dettagliate dagli entity types."""
    entity_manager = get_entity_manager()
    
    # Ottieni tutte le entità
    entities = entity_manager.get_all_entities()
    
    # Crea le descrizioni formattate
    entity_descriptions = []
    for entity in entities:
        description = entity.description or f"Un'entità di tipo {entity.display_name}"
        metadata = ", ".join([f"{k}: {v}" for k, v in entity.metadata_schema.items()])
        entity_descriptions.append(
            f"- {entity.name}: {description}. Metadati: [{metadata}]"
        )
    
    # Inserisci le descrizioni nella configurazione
    config["entity_descriptions"] = "\n".join(entity_descriptions)
    
    # Aggiorna il template
    enriched_template = prompt_template.replace(
        "[{entity_types_str}]",
        "[{entity_types_str}]\n\nDettagli sui tipi di entità:\n{entity_descriptions}"
    )
    
    return enriched_template

# Applica l'arricchimento ai template esistenti
PROMPTS_TEMPLATES["entity_extraction"] = enrich_prompt_with_entity_descriptions(
    PROMPTS_TEMPLATES["entity_extraction"], 
    {}  # Config base, verrà aggiornata in get_formatted_prompt
)

# Funzione per formattare i prompt
def get_formatted_prompt(prompt_key: str, config: Dict[str, Any], **kwargs) -> str:
    """Formatta un template di prompt usando la configurazione e argomenti aggiuntivi."""
    
    template = PROMPTS_TEMPLATES.get(prompt_key)
    if not template:
        raise ValueError(f"Chiave prompt non trovata: {prompt_key}")
        
    # Recupera valori dalla configurazione
    language = config.get("language", "Italian")
    entity_types = config.get("entity_types", [])
    relationship_keywords = config.get("relationship_keywords", [])
    delimiters = config.get("delimiters", {})
    tuple_delimiter = delimiters.get("tuple", "<|>")
    record_delimiter = delimiters.get("record", "##")
    completion_delimiter = delimiters.get("completion", "<|COMPLETE|>")
    
    # Prepara stringhe formattate per le liste
    entity_types_str = ", ".join(entity_types)
    # Formatta le keyword per l'inserimento nel prompt (indentate)
    relationship_keywords_str = ", \n    ".join(relationship_keywords)
    
    # Recupera l'esempio (che ora usa placeholder per i delimitatori)
    examples_template = PROMPTS_TEMPLATES.get("examples", "")
    examples = examples_template.format(
        tuple_delimiter=tuple_delimiter,
        record_delimiter=record_delimiter
    )

    # Crea il dizionario di formattazione
    format_args = {
        "language": language,
        "entity_types_str": entity_types_str,
        "relationship_keywords_str": relationship_keywords_str,
        "tuple_delimiter": tuple_delimiter,
        "record_delimiter": record_delimiter,
        "completion_delimiter": completion_delimiter,
        "examples": examples,
        **kwargs # Aggiunge eventuali argomenti passati direttamente (es. input_text)
    }
    
    return template.format(**format_args)