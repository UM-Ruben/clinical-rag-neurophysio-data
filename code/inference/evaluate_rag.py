from __future__ import annotations

import argparse
import json
import platform
import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import time
import os
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError


def trim_to_sentence_boundary(text: str, min_ratio: float = 0.6) -> str:
    cleaned = text.strip()
    if not cleaned:
        return cleaned

    if re.search(r'[.!?;:…]["”’)\]]?\s*$', cleaned):
        return cleaned

    min_index = int(len(cleaned) * min_ratio)
    end_matches = list(re.finditer(r'[.!?;:…]["”’)\]]?(?=\s|$)', cleaned))

    for match in reversed(end_matches):
        if match.end() >= min_index:
            return cleaned[:match.end()].rstrip()

    comma_matches = list(re.finditer(r',["”’)\]]?(?=\s|$)', cleaned))
    for match in reversed(comma_matches):
        if match.end() >= int(len(cleaned) * 0.8):
            return cleaned[:match.end()].rstrip()

    return cleaned


def load_documents(data_dir: Path):
    from langchain_community.document_loaders import PyPDFDirectoryLoader

    loader = PyPDFDirectoryLoader(str(data_dir))
    return loader.load()


def split_documents(documents, chunk_size: int = 1500, chunk_overlap: int = 400):
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", ".\n", ", ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    # Post-procesar: ajustar cada chunk a límites de frase para no cortar ideas
    for chunk in chunks:
        chunk.page_content = trim_to_sentence_boundary(chunk.page_content, min_ratio=0.55)
    return chunks


def normalize_tokens(text: str) -> List[str]:
    stopwords = {
        "de", "la", "el", "los", "las", "y", "o", "u", "en", "con", "por", "para", "del", "al",
        "que", "se", "un", "una", "unos", "unas", "es", "son", "como", "su", "sus", "lo", "a"
    }
    tokens = re.findall(r"[a-záéíóúñü]{3,}", text.lower())
    return [token for token in tokens if token not in stopwords]


def chunk_by_sentence_boundaries(text: str) -> List[str]:
    parts = re.split(r'(?<=[.!?;:…])\s+', text.strip())
    return [part.strip() for part in parts if part.strip()]


def physio_synonym_expansions(tokens: List[str]) -> List[str]:
    synonym_map = {
        "marcha": ["deambulación", "gait"],
        "espasticidad": ["hipertonía", "espasmo"],
        "propiocepción": ["sensibilidad profunda"],
        "abducción": ["separación"],
        "aducción": ["aproximación"],
        "hemiplejia": ["paresia", "déficit motor"],
        "equilibrio": ["balance postural", "estabilidad"],
        "escápula": ["omóplato"],
        "húmero": ["brazo proximal"],
        "tapiz": ["cinta de marcha", "rodante"],
    }
    expansions: List[str] = []
    token_set = set(tokens)
    for token in token_set:
        expansions.extend(synonym_map.get(token, []))
    return expansions


def build_query_variants(test_item: Dict[str, Any], use_query_expansion: bool = True) -> List[str]:
    question = test_item.get("pregunta", "").strip()
    options = test_item.get("opciones", {})
    option_values = [value for _, value in sorted(options.items())]
    longest_option = max(option_values, key=len) if option_values else ""

    queries = [question]
    if longest_option:
        queries.append(f"{question} {longest_option[:220]}".strip())

    if use_query_expansion:
        q_tokens = normalize_tokens(question)
        expansions = physio_synonym_expansions(q_tokens)
        if expansions:
            queries.append(f"{question} {' '.join(expansions[:6])}".strip())

        if len(option_values) >= 2:
            combined_options = " ".join(option_values[:2])
            queries.append(f"{question} {combined_options[:240]}".strip())

    deduped = list(OrderedDict.fromkeys([q for q in queries if q]))
    return deduped[:5]


def score_document_relevance(doc_text: str, question_text: str, options: Dict[str, str]) -> float:
    doc_tokens = set(normalize_tokens(doc_text))
    if not doc_tokens:
        return 0.0

    question_tokens = set(normalize_tokens(question_text))
    options_tokens = set(normalize_tokens(" ".join(options.values())))

    q_overlap = len(question_tokens.intersection(doc_tokens)) / max(1, len(question_tokens))
    o_overlap = len(options_tokens.intersection(doc_tokens)) / max(1, len(options_tokens))

    return 0.65 * q_overlap + 0.35 * o_overlap


def jaccard_similarity(a_tokens: set[str], b_tokens: set[str]) -> float:
    union = a_tokens.union(b_tokens)
    if not union:
        return 0.0
    return len(a_tokens.intersection(b_tokens)) / len(union)


def remove_redundant_docs(docs: List[Any], threshold: float = 0.88) -> List[Any]:
    filtered: List[Any] = []
    filtered_token_sets: List[set[str]] = []

    for doc in docs:
        token_set = set(normalize_tokens(doc.page_content))
        if not token_set:
            continue

        is_redundant = any(jaccard_similarity(token_set, prev) >= threshold for prev in filtered_token_sets)
        if not is_redundant:
            filtered.append(doc)
            filtered_token_sets.append(token_set)

    return filtered


def adaptive_retrieved_top_k(test_item: Dict[str, Any], base_k: int, max_k: int = 12) -> int:
    question = test_item.get("pregunta", "")
    options = test_item.get("opciones", {})
    text_len = len(question) + sum(len(v) for v in options.values())

    if text_len >= 1400:
        return min(max_k, base_k + 4)
    if text_len >= 900:
        return min(max_k, base_k + 2)
    return base_k


def compute_option_evidence_scores(options: Dict[str, str], docs: List[Any]) -> Dict[str, float]:
    corpus_tokens = set(normalize_tokens(" ".join(doc.page_content for doc in docs)))
    scores: Dict[str, float] = {}

    for label, text in sorted(options.items()):
        option_tokens = set(normalize_tokens(text))
        overlap = len(option_tokens.intersection(corpus_tokens)) / max(1, len(option_tokens))
        scores[label] = round(overlap, 4)

    return scores


def compute_answer_confidence(
    selected_option: str,
    option_evidence_scores: Dict[str, float],
    llm_response: str,
) -> float:
    if selected_option not in option_evidence_scores:
        return 0.0

    chosen_score = option_evidence_scores[selected_option]
    sorted_scores = sorted(option_evidence_scores.values(), reverse=True)
    second_score = sorted_scores[1] if len(sorted_scores) > 1 else 0.0
    evidence_margin = max(0.0, chosen_score - second_score)

    format_bonus = 0.1 if re.search(r'respuesta\s*:\s*\(?[a-d]\)?', llm_response.lower()) else 0.0
    confidence = min(1.0, 0.65 * chosen_score + 0.25 * evidence_margin + format_bonus)
    return round(confidence, 4)


def pack_context_by_relevance(
    docs: List[Any],
    question_text: str,
    options: Dict[str, str],
    max_tokens: int,
) -> str:
    scored_docs = sorted(
        docs,
        key=lambda doc: score_document_relevance(doc.page_content, question_text, options),
        reverse=True,
    )

    selected_sentences: List[str] = []
    token_budget = max_tokens

    for doc in scored_docs:
        sentences = chunk_by_sentence_boundaries(doc.page_content)
        for sentence in sentences:
            sentence_tokens = sentence.split()
            if not sentence_tokens:
                continue
            if len(sentence_tokens) <= token_budget:
                selected_sentences.append(sentence)
                token_budget -= len(sentence_tokens)
            else:
                truncated = truncate_text_to_max_tokens(sentence, token_budget)
                if truncated:
                    selected_sentences.append(truncated)
                token_budget = 0
            if token_budget <= 0:
                break
        if token_budget <= 0:
            break

    return "\n\n".join(selected_sentences).strip()


def build_retriever(documents, embedding_model: str):
    from langchain_community.retrievers import BM25Retriever
    from langchain_community.vectorstores import FAISS
    from langchain_community.cross_encoders import HuggingFaceCrossEncoder
    from langchain_huggingface import HuggingFaceEmbeddings
    try:
        from langchain.retrievers import EnsembleRetriever, ContextualCompressionRetriever
        from langchain.retrievers.document_compressors import CrossEncoderReranker
    except ModuleNotFoundError:
        from langchain_classic.retrievers import EnsembleRetriever, ContextualCompressionRetriever
        from langchain_classic.retrievers.document_compressors import CrossEncoderReranker

    cache_dir = Path(os.environ.get("HF_HOME", "/tmp/huggingface"))
    cache_dir.mkdir(parents=True, exist_ok=True)

    selected_embedding_model = embedding_model
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=selected_embedding_model,
            cache_folder=str(cache_dir),
        )
    except Exception as exc:
        fallback_embedding = "sentence-transformers/all-MiniLM-L6-v2"
        print(
            f"Aviso: no se pudo cargar embedding '{selected_embedding_model}' de forma segura ({exc}). "
            f"Usando fallback: {fallback_embedding}"
        )
        embeddings = HuggingFaceEmbeddings(
            model_name=fallback_embedding,
            cache_folder=str(cache_dir),
        )
        selected_embedding_model = fallback_embedding
    vector_store = FAISS.from_documents(documents, embeddings)
    faiss_retriever = vector_store.as_retriever(search_kwargs={"k": 20})

    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = 20

    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever],
        weights=[0.4, 0.6],
    )

    # Re-ranking con CrossEncoder para mejorar precision
    cross_encoder = HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
    compressor = CrossEncoderReranker(model=cross_encoder, top_n=5)
    
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=ensemble_retriever
    )
    
    return compression_retriever, vector_store, selected_embedding_model


# ── Prompts ───────────────────────────────────────────────────────────────────

def build_prompt():
    """Prompt general (español, chain-of-thought detallado).
===============================================================================================
AVISO. Este script NO es ejecutable por terceros y se publica solo para inspeccion.

Necesita el CORPUS de 9 PDF (no distribuible: material docente con copyright) para construir el indice
FAISS + BM25, y un servidor Ollama local. Es el motor de recuperacion y evaluacion del que
dependen todos los demas: define el troceado (chunk_size=1500, overlap=400), el reranking
hibrido y el extractor de respuesta que se reutiliza sin cambios en P1 y P2.
===============================================================================================
"""
    from langchain_core.prompts import PromptTemplate

    template = (
        "Eres un catedrático experto en fisioterapia, anatomía, neurología y rehabilitación neurológica. "
        "Debes responder preguntas tipo test de examen usando EXCLUSIVAMENTE la información del contexto.\n\n"
        "CONTEXTO:\n{context}\n\n"
        "PREGUNTA:\n{question}\n\n"
        "INSTRUCCIONES DE RAZONAMIENTO (sigue estos pasos en orden):\n\n"
        "PASO 1 - VERIFICAR CADA OPCIÓN PALABRA POR PALABRA:\n"
        "Para cada opción, compárala con el contexto PALABRA POR PALABRA. Presta especial atención a:\n"
        "- Prefijos: ABductor ≠ ADuctor, ABducción ≠ ADucción (son movimientos OPUESTOS)\n"
        "- Nombres similares: tibial ANTERIOR ≠ tibial POSTERIOR, trapecio SUPERIOR ≠ INFERIOR\n"
        "- Lateralidad: DERECHO ≠ IZQUIERDO, IPSILATERAL (mismo lado) ≠ CONTRALATERAL (lado opuesto)\n"
        "- Fases temporales: músculo que PREPARA el movimiento ≠ músculo que EJECUTA el movimiento\n"
        "- Una sola palabra diferente puede hacer FALSA una opción que parece correcta\n"
        "- Lee TODA la frase del contexto, no solo el inicio\n\n"
        "PASO 2 - DESCARTAR OPCIONES CON ERRORES:\n"
        "Si una opción cambia UNA SOLA PALABRA respecto al contexto (ej: dice 'aductor' cuando el contexto dice 'abductor'), esa opción es FALSA. Descártala.\n\n"
        "PASO 3 - OPCIONES 'A Y B SON CIERTAS':\n"
        "Si existe una opción tipo 'a y b son ciertas/correctas', verifica que AMBAS (a Y b) sean verdaderas según el contexto. "
        "Si ambas son verdaderas, la opción combinada es la correcta. No elijas solo a) o solo b) cuando ambas son ciertas y existe la opción combinada.\n\n"
        "PASO 4 - ELEGIR LA MÁS COMPLETA:\n"
        "Entre las opciones que NO tienen errores, elige la más completa (la que incluye más información correcta del contexto).\n\n"
        "RESPUESTA FINAL (formato obligatorio):\n"
        "RESPUESTA: [una sola letra]\n\n"
        "Razona paso a paso:\n"
    )
    return PromptTemplate(template=template, input_variables=["context", "question"])


def build_prompt_medical():
    """
    Prompt específico para modelos médicos legacy (meditron:7b, medllama2:7b).

    Estos modelos:
      - Fueron entrenados en inglés médico  → prompt en inglés, conciso.
      - Tienen ventana de contexto limitada (2k–4k tokens).
      - Siguen formato de instrucción Llama-2 que Ollama aplica automáticamente
        vía su template interno, así que el usuario solo envía el contenido.
      - NO ejecutan bien chain-of-thought largo en español.

    El prompt se simplifica drásticamente para maximizar la probabilidad de
    que el modelo devuelva al menos una letra (a/b/c/d).
    """
    from langchain_core.prompts import PromptTemplate

    template = (
        "You are a clinical physiotherapy expert.  "
        "Answer the multiple-choice question below using ONLY the provided context.\n\n"
        "CONTEXT:\n{context}\n\n"
        "QUESTION:\n{question}\n\n"
        "INSTRUCTIONS:\n"
        "1. Read every option carefully and compare it word-by-word with the context.\n"
        "2. Eliminate options that contradict the context.\n"
        "3. Pick the single best option.\n\n"
        "Reply with EXACTLY one line:\n"
        "ANSWER: <letter>\n"
    )
    return PromptTemplate(template=template, input_variables=["context", "question"])


def build_prompt_no_context():
    """Prompt para el modo SIN-RAG (baseline de conocimiento paramétrico).

    El modelo responde la pregunta tipo test SIN material de apoyo, usando
    exclusivamente su conocimiento interno. Se mantiene la variable {context}
    (renderizada vacía) para conservar la firma de answer_question(); así la
    comparación con/sin RAG es justa: idéntico modelo y formato de salida,
    única diferencia = presencia o ausencia de contexto recuperado.
    """
    from langchain_core.prompts import PromptTemplate

    template = (
        "{context}"  # vacío en modo sin-RAG; presente solo por compatibilidad de formato
        "Eres un catedrático experto en fisioterapia, anatomía, neurología y rehabilitación neurológica. "
        "Responde la siguiente pregunta tipo test de examen basándote EXCLUSIVAMENTE en tu propio "
        "conocimiento clínico experto. NO dispones de material de apoyo ni contexto adicional.\n\n"
        "PREGUNTA:\n{question}\n\n"
        "INSTRUCCIONES DE RAZONAMIENTO:\n"
        "- Analiza cada opción con cuidado (prefijos ABductor≠ADuctor, lateralidad ipsi/contralateral, "
        "tibial anterior≠posterior, fase que prepara≠ejecuta el movimiento).\n"
        "- Si existe una opción tipo 'a y b son ciertas', verifica que AMBAS lo sean.\n"
        "- Elige la opción más correcta y completa.\n\n"
        "RESPUESTA FINAL (formato obligatorio):\n"
        "RESPUESTA: [una sola letra]\n\n"
        "Razona paso a paso:\n"
    )
    return PromptTemplate(template=template, input_variables=["context", "question"])


def select_prompt(model_name: str, no_rag: bool = False):
    """Devuelve el prompt adecuado al modelo.

    En modo SIN-RAG se usa un prompt de conocimiento paramétrico (sin contexto).
    Modelos médicos obsoletos reciben un prompt simplificado en inglés;
    el resto usan el prompt general de cadena de razonamiento en español.
    """
    lowered = model_name.lower()
    is_medical_legacy = "meditron" in lowered or "medllama" in lowered
    if no_rag:
        return build_prompt_no_context(), is_medical_legacy
    if is_medical_legacy:
        return build_prompt_medical(), True   # (prompt, is_medical_legacy)
    return build_prompt(), False


def truncate_text_to_max_tokens(text: str, max_tokens: int) -> str:
    words = text.split()
    if len(words) <= max_tokens:
        return trim_to_sentence_boundary(text, min_ratio=0.55)

    truncated = " ".join(words[:max_tokens])
    return trim_to_sentence_boundary(truncated, min_ratio=0.5)


def build_context_for_model(
    documents: List[Any],
    model_name: str,
    question_text: str,
    options: Dict[str, str],
    default_max_tokens: int,
) -> str:
    lowered = model_name.lower()
    max_tokens = default_max_tokens
    if "meditron" in lowered or "medllama" in lowered:
        max_tokens = min(default_max_tokens, 1200)

    return pack_context_by_relevance(
        docs=documents,
        question_text=question_text,
        options=options,
        max_tokens=max_tokens,
    )


def answer_question(llm, prompt, question: str, context: str):
    formatted_prompt = prompt.format(context=context, question=question)
    start_ts = time.time()
    response = llm.invoke(formatted_prompt)
    latency_seconds = time.time() - start_ts
    return response, latency_seconds


def extract_answer_from_response(response: str) -> str:
    """Extrae la opción seleccionada (a, b, c, d) de la respuesta del LLM.

    Estrategia: se recogen TODAS las declaraciones explícitas de respuesta del
    modelo y se devuelve la de MAYOR posición en el texto (es decir, su veredicto
    final). Se tolera el formato con corchetes/markdown ('RESPUESTA: [b]',
    '**A**'), las construcciones 'la respuesta final es X' y 'opción X ... es la
    correcta', la selección por posición ('la primera/segunda/tercera') y el
    patrón 'a y b son ciertas' -> c. Los rechazos del modelo ('lo siento, no
    puedo...', 'ninguna de las opciones es correcta') se tratan como respuesta no
    válida ('desconocida'), ya que operativamente el sistema no obtiene respuesta.

    Nota: corrige un fallo previo que, en algunos patrones con dos grupos de
    captura, devolvía la palabra descriptiva ('correcta'/'correct') en lugar de
    la letra (se usaba match.lastindex), y que no reconocía 'RESPUESTA: [letra]'
    con corchetes, infravalorando las respuestas más narrativas (típicas con RAG).
    """
    rl = response.lower()
    SEP = r'[\s:*\[\(\)"“”\'’.\-]{0,6}'
    POS = {"primera": "a", "segunda": "b", "tercera": "c", "cuarta": "d"}
    letter_markers = [
        r'respuesta\s+final\s*(?:es)?' + SEP + r'([a-d])\b',
        r'respuesta' + SEP + r'([a-d])\b',
        r'answer' + SEP + r'([a-d])\b',
        r'la\s+respuesta\s+(?:final\s+)?es' + SEP + r'([a-d])\b',
        r'la\s+opci[oó]n\s+correcta\s+es' + SEP + r'([a-d])\b',
        r'la\s+respuesta\s+correcta\s+es' + SEP + r'([a-d])\b',
        r'(?:m[aá]s\s+)?correcta\s+y\s+completa\s+es' + SEP + r'([a-d])\b',
        r'opci[oó]n\s+([a-d])\)?[^.\n]{0,70}?\bes\s+la\s+(?:m[aá]s\s+\w+\s+|única\s+|)?(?:correcta|respuesta)',
        r'la\s+opci[oó]n\s+([a-d])\)?\s+es\s+la\s+(?:correcta|respuesta|m[aá]s)',
        r'the\s+(?:correct\s+)?answer\s+is' + SEP + r'([a-d])\b',
    ]
    pos_markers = [r'(?:respuesta|opci[oó]n)\s+(?:final\s+|correcta\s+|m[aá]s\s+\w+\s+)*(?:es\s+)?(?:la\s+)?(primera|segunda|tercera|cuarta)\b']
    ayb = r'\b[ab]\s+y\s+[ab]\s+son\s+(?:ciertas|correctas|verdaderas)'
    safety = r'lo siento|no puedo proporcionar|no puedo ayudar|no puedo asistir'
    reject = (r'ninguna\s+(?:de\s+las\s+)?opci|no\s+est[aá]\s+entre\s+las\s+opciones|'
              r'no\s+se\s+ajusta\s+a\s+ninguna|no\s+hay\s+(?:una\s+)?opci[oó]n\s+correcta|'
              r'none\s+of\s+the|respuesta' + SEP + r'\bn\b|no\s+puedo\s+proporcionar\s+una\s+respuesta')

    cands = []  # (posición, letra | None si es rechazo)
    for p in letter_markers:
        for m in re.finditer(p, rl):
            cands.append((m.start(), m.group(1)))
    for p in pos_markers:
        for m in re.finditer(p, rl):
            cands.append((m.start(), POS[m.group(1)]))
    for m in re.finditer(ayb, rl):
        cands.append((m.start(), "c"))
    for p in (safety, reject):
        for m in re.finditer(p, rl):
            cands.append((m.start(), None))
    if cands:
        cands.sort(key=lambda x: x[0])
        return cands[-1][1] or "desconocida"

    # Respaldo: última 'x)' al final del texto, o primera línea con 'x)'
    last = None
    for mm in re.finditer(r'\b([a-d])\)', rl[-160:]):
        last = mm
    if last:
        return last.group(1)
    match = re.search(r'^\s*\(?\[?([a-d])\s*[\)\.\]]', rl[:160], re.MULTILINE)
    if match:
        return match.group(1)

    return "desconocida"


def multi_query_retrieve(
    retriever,
    vector_store,
    test_item: Dict[str, Any],
    retrieval_cache: Dict[str, List[Any]],
    use_query_expansion: bool,
    final_top_k: int,
) -> List[Any]:
    """Recupera documentos usando múltiples queries: pregunta + opciones clave."""
    queries = build_query_variants(test_item, use_query_expansion=use_query_expansion)

    seen_contents = set()
    combined = []
    for idx, query in enumerate(queries):
        if query in retrieval_cache:
            docs_query = retrieval_cache[query]
        else:
            if idx == 0:
                docs_query = retriever.invoke(query)
            else:
                docs_query = vector_store.similarity_search(query, k=10)
            retrieval_cache[query] = docs_query

        for doc in docs_query:
            content_hash = hash(doc.page_content[:120])
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                combined.append(doc)

    deduped = remove_redundant_docs(combined, threshold=0.88)
    return deduped[:final_top_k]


def format_question_with_options(test_item: Dict[str, Any]) -> str:
    """Formatea la pregunta con todas sus opciones."""
    question_text = test_item['pregunta']
    options = test_item['opciones']
    
    formatted = question_text + "\n\n"
    for key in sorted(options.keys()):
        formatted += f"{key}) {options[key]}\n"
    
    return formatted.strip()


def load_test_questions(filepath: Path) -> List[Dict[str, Any]]:
    """Carga las preguntas de test desde un archivo JSON."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Motor de evaluación RAG para benchmark de modelos y hardware")
    parser.add_argument("--model", required=True, help="Nombre del modelo en Ollama, por ejemplo: llama3.1:8b")
    parser.add_argument("--device", required=True, help="Etiqueta del equipo, por ejemplo: Local_Laptop")
    parser.add_argument("--mode", required=True, choices=["CPU", "GPU"], help="Modo de ejecución")
    parser.add_argument("--param_size", required=True, help="Tamaño de parámetros, por ejemplo: 7b, 8b, 70b")
    parser.add_argument("--no_rag", action="store_true", help="Modo SIN-RAG: el modelo responde solo con la pregunta + opciones, sin recuperación de contexto (para medir la contribución del RAG = accuracy_con − accuracy_sin).")
    parser.add_argument("--oracle_context", action="store_true", help="Usa contexto oracle (incluye la opción correcta en la query de recuperación)")
    parser.add_argument("--oracle_k", type=int, default=7, help="Número de fragmentos para contexto oracle")
    parser.add_argument("--recall_overlap_threshold", type=float, default=0.35, help="Umbral de solapamiento para considerar recall hit")
    parser.add_argument("--chunk_size", type=int, default=1500, help="Tamaño de chunk para split de documentos")
    parser.add_argument("--chunk_overlap", type=int, default=400, help="Solapamiento entre chunks")
    parser.add_argument("--embedding_model", default="BAAI/bge-m3", help="Modelo de embeddings")
    parser.add_argument("--context_max_tokens", type=int, default=5000, help="Máximo de tokens aproximados para contexto en modelos no-limitados")
    parser.add_argument("--retrieved_top_k", type=int, default=7, help="Número máximo de fragmentos finales recuperados")
    parser.add_argument("--disable_query_expansion", action="store_true", help="Desactiva expansión semántica de queries")
    parser.add_argument("--redundancy_threshold", type=float, default=0.88, help="Umbral Jaccard para filtrar chunks redundantes")
    parser.add_argument("--question_timeout", type=int, default=720, help="Timeout en segundos por pregunta (default: 720 = 12 min). 0 = sin timeout.")
    parser.add_argument("--questions_file", default="test_questions.json",
                        help="Ruta al JSON con las preguntas (default: test_questions.json)")
    parser.add_argument(
        "--hardware_type",
        default=None,
        choices=["Local_GPU", "Local_CPU", "Cluster_CPU", "Cluster_GPU"],
        help="Tipo de entorno de ejecución.  Si se omite se infiere de --device + --mode.",
    )
    args = parser.parse_args()

    # ---------- Inferencia automática de hardware_type ----------
    if args.hardware_type is None:
        device_lower = args.device.lower()
        if "cluster" in device_lower or "amdahl" in device_lower or "ibsen" in device_lower:
            args.hardware_type = f"Cluster_{args.mode}"   # Cluster_CPU / Cluster_GPU
        else:
            args.hardware_type = f"Local_{args.mode}"     # Local_CPU  / Local_GPU

    return args


def safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip())


def compute_recall_hit(test_item: Dict[str, Any], docs: List[Any], overlap_threshold: float = 0.35) -> Dict[str, Any]:
    correct_label = test_item.get("respuesta_correcta", "")
    correct_option = test_item.get("opciones", {}).get(correct_label, "")

    evidence_text = f"{test_item.get('pregunta', '')} {correct_option}".strip()
    evidence_tokens = normalize_tokens(evidence_text)
    evidence_set = set(evidence_tokens)

    if not evidence_set:
        return {"hit": False, "overlap": 0.0, "matched_tokens": []}

    best_overlap = 0.0
    best_tokens: List[str] = []
    for doc in docs:
        doc_tokens = set(normalize_tokens(doc.page_content))
        if not doc_tokens:
            continue
        overlap_tokens = sorted(evidence_set.intersection(doc_tokens))
        overlap_ratio = len(overlap_tokens) / max(1, len(evidence_set))
        if overlap_ratio > best_overlap:
            best_overlap = overlap_ratio
            best_tokens = overlap_tokens

    hit = best_overlap >= overlap_threshold and len(best_tokens) >= 2
    return {
        "hit": hit,
        "overlap": round(best_overlap, 4),
        "matched_tokens": best_tokens[:20],
    }


def oracle_retrieve(vector_store, test_item: Dict[str, Any], k: int = 7) -> List[Any]:
    correct_label = test_item.get("respuesta_correcta", "")
    correct_option = test_item.get("opciones", {}).get(correct_label, "")

    oracle_queries = [
        f"{test_item.get('pregunta', '')} {correct_option}".strip(),
        correct_option,
    ]

    seen_contents = set()
    oracle_docs: List[Any] = []
    for query in oracle_queries:
        if not query:
            continue
        candidates = vector_store.similarity_search(query, k=k)
        for doc in candidates:
            content_hash = hash(doc.page_content[:120])
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                oracle_docs.append(doc)
            if len(oracle_docs) >= k:
                return oracle_docs

    return oracle_docs[:k]


def evaluate_rag_system(args: argparse.Namespace):
    """Evalúa el sistema RAG con un conjunto de preguntas de test."""
    from langchain_ollama import OllamaLLM

    print("="*80)
    print("EVALUACIÓN AUTOMÁTICA DEL SISTEMA RAG")
    print("="*80)
    print(f"Modelo: {args.model}")
    print(f"Dispositivo: {args.device}")
    print(f"Modo: {args.mode}")
    print(f"Tamaño de parámetros: {args.param_size}")
    print(f"Hardware type: {args.hardware_type}")
    print(f"Oracle context: {'ON' if args.oracle_context else 'OFF'}")
    print(f"Expansión de query: {'OFF' if args.disable_query_expansion else 'ON'}")
    print(f"Embedding model: {args.embedding_model}")
    print()
    
    # Cargar documentos y preparar el sistema
    retriever, vector_store = None, None
    effective_embedding_model = args.embedding_model
    if args.no_rag:
        print("[NO-RAG] Modo sin recuperación: se omite la carga de documentos y la construcción del retriever.")
        effective_embedding_model = "none"
    else:
        print("Cargando documentos...")
        data_dir = Path.cwd() / "data"
        if not data_dir.exists():
            print(f"Error: No se encontró la carpeta data en: {data_dir}")
            return

        documents = load_documents(data_dir)
        if not documents:
            print("Error: No se encontraron PDFs en la carpeta data.")
            return

        print(f"Documentos cargados: {len(documents)}")
        print("Dividiendo en chunks...")
        chunks = split_documents(documents, chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
        print(f"Chunks creados: {len(chunks)}")

        print("Construyendo retriever con re-ranking...")
        retriever_start = time.perf_counter()
        retriever, vector_store, effective_embedding_model = build_retriever(chunks, embedding_model=args.embedding_model)
        retriever_elapsed = time.perf_counter() - retriever_start
        print(f"Retriever listo en {retriever_elapsed:.2f}s")
        if effective_embedding_model != args.embedding_model:
            print(f"Embedding efectivo en uso: {effective_embedding_model}")
    
    # ---------- Detección de modelo visión-lenguaje ----------
    _model_lower = args.model.lower()
    is_vision_language_model = any(tag in _model_lower for tag in ["vl", "vision", "llava", "cogvlm"])
    if is_vision_language_model:
        print(f"[INFO] Modelo visión-lenguaje detectado ({args.model}). Se usará en modo solo-texto para el benchmark RAG.")

    # ---------- Contexto ampliado para modelos ≥70B ----------
    num_ctx = 8192
    if any(tag in _model_lower for tag in ["70b", "72b", "110b"]):
        num_ctx = 16384
        print(f"[INFO] Modelo grande detectado → num_ctx={num_ctx}")

    print("Inicializando LLM...")
    llm = OllamaLLM(model=args.model, base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"), temperature=0, num_ctx=num_ctx)

    # ---------- Selección de prompt según tipo de modelo ----------
    prompt, is_medical_legacy = select_prompt(args.model, no_rag=args.no_rag)
    if is_medical_legacy:
        print(f"[MEDICAL-LEGACY] Modelo médico legacy detectado ({args.model}).")
        print(f"  → Prompt simplificado EN INGLÉS activado.")
        print(f"  → Contexto limitado a 1200 tokens.")
        print(f"  → Se generará log de diagnóstico al finalizar.")
    
    # Cargar preguntas de test
    questions_file = Path(args.questions_file)
    if not questions_file.is_absolute():
        questions_file = Path.cwd() / questions_file
    if not questions_file.exists():
        print(f"Error: No se encontró el archivo {questions_file}")
        return
    
    print(f"Cargando preguntas desde {questions_file}...")
    test_questions = load_test_questions(questions_file)
    print(f"Preguntas cargadas: {len(test_questions)}")
    print()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    embedding_short = safe_name(effective_embedding_model.split('/')[-1])
    report_filename = f"report_{safe_name(args.model)}_{safe_name(args.mode)}_{safe_name(args.device)}_{embedding_short}_{timestamp}.json"
    preferred_reports_dir = Path(os.environ.get("REPORTS_DIR", str(Path.cwd() / "reports")))
    try:
        preferred_reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = preferred_reports_dir / report_filename
    except PermissionError:
        fallback_dir = Path("/tmp/rag_reports")
        fallback_dir.mkdir(parents=True, exist_ok=True)
        report_path = fallback_dir / report_filename
        print(f"Aviso: sin permisos en REPORTS_DIR. Usando fallback: {fallback_dir}")
    inprogress_path = report_path.with_name(f"inprogress_{report_filename}")
    
    # Evaluar cada pregunta
    results = []
    correct_count = 0
    incorrect_count = 0
    unknown_count = 0
    timeout_count = 0
    recall_hits = 0
    retrieval_cache: Dict[str, List[Any]] = {}

    def dump_report(path: Path, completed: bool) -> Path:
        payload = {
            "header": {
                "timestamp": datetime.now().isoformat(),
                "benchmark_engine_version": "3.0.0",
                "model": args.model,
                "device": args.device,
                "mode": args.mode,
                "param_size": args.param_size,
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "context_limit_tokens_for_small_window_models": 1200,
                "small_window_model_detected": ("meditron" in args.model.lower() or "medllama" in args.model.lower()),
                "questions_file": questions_file.name,
                "questions_count": len(test_questions),
                "no_rag": args.no_rag,
                "oracle_context": args.oracle_context,
                "oracle_k": args.oracle_k,
                "recall_overlap_threshold": args.recall_overlap_threshold,
                "chunk_size": args.chunk_size,
                "chunk_overlap": args.chunk_overlap,
                "context_max_tokens": args.context_max_tokens,
                "retrieved_top_k": args.retrieved_top_k,
                "embedding_model": effective_embedding_model,
                "query_expansion": (not args.disable_query_expansion),
                "redundancy_threshold": args.redundancy_threshold,
                "question_timeout": args.question_timeout,
                "hardware_type": args.hardware_type,
                "is_vision_language_model": is_vision_language_model,
                "is_medical_legacy_model": is_medical_legacy,
                "prompt_language": "en" if is_medical_legacy else "es",
                "num_ctx": num_ctx,
                "completed": completed,
            },
            "summary": {
                "total": len(test_questions),
                "processed": len(results),
                "correct": correct_count,
                "incorrect": incorrect_count,
                "unknown": unknown_count,
                "timeout": timeout_count,
                "recall_hits": recall_hits,
                "recall_at_k": (recall_hits / len(results) * 100) if results else 0.0,
                "accuracy": (correct_count / len(results) * 100) if results else 0.0,
            },
            "questions": results,
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return path
        except PermissionError:
            fallback_dir = Path("/tmp/rag_reports")
            fallback_dir.mkdir(parents=True, exist_ok=True)
            fallback_path = fallback_dir / path.name
            with open(fallback_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print(f"Aviso: sin permisos para escribir en {path.parent}. Guardado en {fallback_path}")
            return fallback_path
    
    for i, test_item in enumerate(test_questions, 1):
        print(f"\n{'='*80}")
        print(f"PREGUNTA {i}/{len(test_questions)}")
        print(f"{'='*80}")
        print(f"ID: {test_item['id']}")
        print(f"Pregunta: {test_item['pregunta']}")
        print(f"Opciones:")
        for key, value in sorted(test_item['opciones'].items()):
            print(f"  {key}) {value}")
        print(f"Respuesta correcta: {test_item['respuesta_correcta']}")
        print()
        
        # Formatear pregunta con opciones
        full_question = format_question_with_options(test_item)
        options = test_item.get('opciones', {})
        
        if args.no_rag:
            # ── Modo SIN-RAG: el modelo responde con su conocimiento paramétrico, sin contexto ──
            docs = []
            effective_top_k = 0
            recall_info = compute_recall_hit(
                test_item=test_item,
                docs=[],
                overlap_threshold=args.recall_overlap_threshold,
            )
            context_text = ""
            print("[NO-RAG] Sin recuperación: contexto vacío.")
        else:
            # Recuperar documentos usando multi-query (pregunta + opciones)
            effective_top_k = adaptive_retrieved_top_k(test_item, base_k=args.retrieved_top_k)

            docs = multi_query_retrieve(
                retriever=retriever,
                vector_store=vector_store,
                test_item=test_item,
                retrieval_cache=retrieval_cache,
                use_query_expansion=not args.disable_query_expansion,
                final_top_k=effective_top_k,
            )
            docs = remove_redundant_docs(docs, threshold=args.redundancy_threshold)

            recall_info = compute_recall_hit(
                test_item=test_item,
                docs=docs,
                overlap_threshold=args.recall_overlap_threshold,
            )
            if recall_info["hit"]:
                recall_hits += 1

            if args.oracle_context:
                oracle_docs = oracle_retrieve(vector_store, test_item, k=args.oracle_k)
                if oracle_docs:
                    docs = oracle_docs

            print(f"Fragmentos recuperados: {len(docs)}")
            context_text = build_context_for_model(
                documents=docs,
                model_name=args.model,
                question_text=test_item.get('pregunta', ''),
                options=options,
                default_max_tokens=args.context_max_tokens,
            )
        
        fragments_debug = []
        for j, doc in enumerate(docs, 1):
            print(f"\n--- Fragmento {j} ---")
            fragment_text = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
            print(fragment_text)
            fragments_debug.append(doc.page_content)
        
        # Generar respuesta con la pregunta completa (incluyendo opciones)
        print(f"\n{'='*40}")
        print("Generando respuesta de la IA...")

        timed_out = False
        if args.question_timeout and args.question_timeout > 0:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(answer_question, llm, prompt, full_question, context_text)
                try:
                    answer, latency_seconds = future.result(timeout=args.question_timeout)
                except (FuturesTimeoutError, TimeoutError):
                    timed_out = True
                    latency_seconds = float(args.question_timeout)
                    answer = "TIMEOUT"
                    print(f"\n⏰ TIMEOUT: la pregunta excedió el límite de {args.question_timeout}s ({args.question_timeout/60:.0f} min). Saltando.")
        else:
            answer, latency_seconds = answer_question(llm, prompt, full_question, context_text)

        answer_str = str(answer)
        if not timed_out:
            print(f"\nRespuesta de la IA:\n{answer_str}")
            print(f"Latencia llm.invoke(): {latency_seconds:.4f} s")
        
        # Extraer la opción seleccionada
        selected_option = "timeout" if timed_out else extract_answer_from_response(answer_str)
        print(f"\nOpción detectada: {selected_option}")
        
        # Verificar si es correcta
        is_correct = selected_option == test_item['respuesta_correcta']
        if timed_out:
            timeout_count += 1
            status = "⏰ TIMEOUT"
        elif is_correct:
            correct_count += 1
            status = "✓ CORRECTA"
        elif selected_option == "desconocida":
            unknown_count += 1
            status = "? NO DETECTADA"
        else:
            incorrect_count += 1
            status = "✗ INCORRECTA"
        
        print(f"\nResultado: {status}")

        option_evidence_scores = compute_option_evidence_scores(options, docs)
        answer_confidence = compute_answer_confidence(selected_option, option_evidence_scores, answer_str)
        
        # Guardar resultado
        results.append({
            "id": test_item['id'],
            "pregunta": test_item['pregunta'],
            "opciones": test_item['opciones'],
            "respuesta_correcta": test_item['respuesta_correcta'],
            "respuesta_ia": answer_str,
            "opcion_detectada": selected_option,
            "es_correcta": is_correct,
            "timed_out": timed_out,
            "latency_seconds": latency_seconds,
            "fragmentos": fragments_debug,
            "num_fragmentos": len(docs),
            "context_truncated_for_small_window": ("meditron" in args.model.lower() or "medllama" in args.model.lower()),
            "retrieval_recall_hit": recall_info["hit"],
            "retrieval_overlap": recall_info["overlap"],
            "retrieval_matched_tokens": recall_info["matched_tokens"],
            "oracle_context_used": args.oracle_context,
            "option_evidence_scores": option_evidence_scores,
            "answer_confidence": answer_confidence,
            "effective_retrieved_top_k": effective_top_k,
            "context_token_count": len(context_text.split()),
        })
        inprogress_written_path = dump_report(inprogress_path, completed=False)
    
    # Generar reporte final
    print(f"\n\n{'='*80}")
    print("RESUMEN DE EVALUACIÓN")
    print(f"{'='*80}")
    print(f"Total de preguntas: {len(test_questions)}")
    print(f"Correctas: {correct_count} ({correct_count/len(test_questions)*100:.1f}%)")
    print(f"Incorrectas: {incorrect_count} ({incorrect_count/len(test_questions)*100:.1f}%)")
    print(f"No detectadas: {unknown_count} ({unknown_count/len(test_questions)*100:.1f}%)")
    if timeout_count > 0:
        print(f"Timeout: {timeout_count} ({timeout_count/len(test_questions)*100:.1f}%)")
    print(f"Recall@k (heurístico): {recall_hits}/{len(test_questions)} ({recall_hits/len(test_questions)*100:.1f}%)")
    print(f"{'='*80}")
    
    final_report_path = dump_report(report_path, completed=True)
    if 'inprogress_written_path' in locals() and inprogress_written_path.exists():
        inprogress_written_path.unlink()
    
    print(f"\nReporte guardado en: {final_report_path}")

    # ── Diagnóstico de modelos médicos legacy ─────────────────────────────
    if is_medical_legacy:
        accuracy = correct_count / max(1, len(results)) * 100
        diag_lines: List[str] = [
            "=" * 80,
            "DIAGNÓSTICO MODELO MÉDICO LEGACY",
            "=" * 80,
            f"Modelo:          {args.model}",
            f"Hardware:         {args.hardware_type}",
            f"Prompt language:  EN (simplificado)",
            f"Accuracy:         {accuracy:.1f}% ({correct_count}/{len(results)})",
            f"Timeouts:         {timeout_count}",
            f"Unknown:          {unknown_count}",
            f"Recall@k:         {recall_hits}/{len(results)}",
            "",
        ]

        # Detectar fallo sistémico
        SYSTEMIC_FAILURE_THRESHOLD = 20.0   # %
        if accuracy <= SYSTEMIC_FAILURE_THRESHOLD:
            diag_lines.append(
                f"⚠ FALLO SISTÉMICO: accuracy ({accuracy:.1f}%) <= umbral ({SYSTEMIC_FAILURE_THRESHOLD}%)."
            )
            diag_lines.append(
                "  CONCLUSIÓN: Este modelo médico especializado NO es viable para "
                "el benchmark RAG clínico de fisioterapia en español."
            )
            diag_lines.append(
                "  RECOMENDACIÓN para el TFG: documentar como OBSOLETO frente a "
                "generalistas modernos (llama3, qwen2.5, deepseek-r1)."
            )
        else:
            diag_lines.append(
                f"El modelo supera el umbral de fallo sistémico ({SYSTEMIC_FAILURE_THRESHOLD}%) "
                "pero su rendimiento es inferior al de generalistas modernos."
            )

        # Desglose de errores
        diag_lines.append("")
        diag_lines.append("DESGLOSE POR PREGUNTA:")
        for r in results:
            flag = "✓" if r["es_correcta"] else ("⏰" if r.get("timed_out") else "✗")
            detected = r.get("opcion_detectada", "?")
            correct = r.get("respuesta_correcta", "?")
            lat = r.get("latency_seconds", 0)
            diag_lines.append(
                f"  {flag} Q{r['id']:>2d}  detected={detected}  correct={correct}  "
                f"latency={lat:.1f}s  recall_hit={r.get('retrieval_recall_hit', False)}"
            )

        diag_lines.append("=" * 80)
        diag_text = "\n".join(diag_lines)
        print(f"\n{diag_text}")

        # Guardar log de diagnóstico junto al reporte
        diag_path = final_report_path.with_suffix(".medical_diag.txt")
        try:
            with open(diag_path, "w", encoding="utf-8") as fh:
                fh.write(diag_text + "\n")
            print(f"Log diagnóstico médico: {diag_path}")
        except OSError as exc:
            print(f"[WARN] No se pudo escribir diagnóstico: {exc}")

    print("\n¡Evaluación completada!")


if __name__ == "__main__":
    cli_args = parse_args()
    evaluate_rag_system(cli_args)
