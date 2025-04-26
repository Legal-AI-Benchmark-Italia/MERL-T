from typing import Any

GRAPH_FIELD_SEP = "<SEP>"

PROMPTS: dict[str, Any] = {}

PROMPTS["DEFAULT_LANGUAGE"] = "English"
PROMPTS["DEFAULT_TUPLE_DELIMITER"] = "<|>"
PROMPTS["DEFAULT_RECORD_DELIMITER"] = "##"
PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"
PROMPTS["examples"] = '''Input: "Apple Inc. ha sede a Cupertino. Tim Cook è il CEO di Apple dal 2011."
Output:
("entity"<|>Apple Inc.<|>organizzazione<|>Azienda tecnologica multinazionale che produce elettronica di consumo, software e servizi online)##
("entity"<|>Tim Cook<|>persona<|>CEO di Apple Inc. dal 2011)##
("entity"<|>Cupertino<|>luogo<|>Città in California dove ha sede Apple Inc.)##
("relationship"<|>Tim Cook<|>Apple Inc.<|>È il CEO dell'azienda dal 2011<|>DIRIGENTE_DI<|>0.9)##
("relationship"<|>Apple Inc.<|>Cupertino<|>Ha la sede principale in questa città<|>SEDE_IN<|>0.8)
'''

PROMPTS["entity_extraction"] = """---Goal---
Given a text document that is potentially relevant to this activity and a list of entity types, identify all entities of those types from the text and all relationships among the identified entities.
Use {language} as output language.

---Steps---
1. Identify all entities. For each identified entity, extract the following information:
- entity_name: Name of the entity, use same language as input text. If English, capitalized the name.
- entity_type: One of the following types: [{entity_types}]
- entity_description: Comprehensive description of the entity's attributes and activities
Format each entity as ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. From the entities identified in step 1, identify all pairs of (source_entity, target_entity) that are *clearly related* to each other.
For each pair of related entities, extract the following information:
- source_entity: name of the source entity, as identified in step 1
- target_entity: name of the target entity, as identified in step 1
- relationship_description: explanation as to why you think the source entity and the target entity are related to each other
- relationship_strength: a numeric score indicating strength of the relationship between the source entity and target entity
- relationship_keywords: one or more high-level key words that summarize the overarching nature of the relationship, focusing on concepts or themes rather than specific details
Format each relationship as ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)

3. Identify high-level key words that summarize the main concepts, themes, or topics of the entire text. These should capture the overarching ideas present in the document.
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
Entity_types: [{entity_types}]
Input text: {input_text}"""

PROMPTS["entity_continue_extraction"] = """Continue extracting more entities and relationships from the same text. Focus on finding any entities or relationships that might have been missed in the previous extraction.

Use the same format as before:
- For entities: ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)
- For relationships: ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)
- For content keywords: ("content_keywords"{tuple_delimiter}<high_level_keywords>)

Use {record_delimiter} as the list delimiter.
When finished, output {completion_delimiter}"""

PROMPTS["entity_if_loop_extraction"] = """Based on the previous extractions, are there any more entities or relationships that could be extracted from the text? If yes, continue extracting. If no, just output {completion_delimiter}."""

PROMPTS["DEFAULT_ENTITY_TYPES"] = ["organization", "person", "geo", "event", "category"]

constraint_query = "CREATE CONSTRAINT node_id_unique IF NOT EXISTS FOR (n:Node) ASSERT n.id IS UNIQUE" 