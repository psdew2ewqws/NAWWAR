"""
Knowledge base loader — ingest markdown documents into ChromaDB.

Reads .md files from ai_engine/knowledge/documents/, splits them into
section-level chunks, and stores them in a ChromaDB collection with
embeddings from OpenAI text-embedding-3-small.
"""
import logging
import re
from pathlib import Path

import chromadb
from django.conf import settings

from apps.ai_engine.clients.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

DOCUMENTS_DIR = Path(__file__).resolve().parent / 'documents'


class KnowledgeBaseLoader:
    """Manages the ChromaDB vector store for Nawwar's knowledge base."""

    COLLECTION_NAME = 'nawwar_knowledge'

    def __init__(self):
        self.chroma = chromadb.PersistentClient(path=str(settings.CHROMADB_PATH))
        self.collection = self.chroma.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={'hnsw:space': 'cosine'},
        )
        self._openai = None

    @property
    def openai_client(self) -> OpenAIClient:
        if self._openai is None:
            self._openai = OpenAIClient()
        return self._openai

    def load_documents(self) -> int:
        """
        Read all .md files from the knowledge/documents/ directory,
        chunk them by section headers, embed, and upsert into ChromaDB.

        Returns:
            Number of chunks loaded.
        """
        md_files = sorted(DOCUMENTS_DIR.glob('*.md'))
        if not md_files:
            logger.warning("No .md files found in %s", DOCUMENTS_DIR)
            return 0

        all_chunks = []
        for md_path in md_files:
            chunks = self._chunk_document(md_path)
            all_chunks.extend(chunks)
            logger.info("Chunked %s into %d sections", md_path.name, len(chunks))

        if not all_chunks:
            return 0

        # Batch upsert into ChromaDB
        ids = [c['id'] for c in all_chunks]
        documents = [c['text'] for c in all_chunks]
        metadatas = [c['metadata'] for c in all_chunks]

        # Embed in batches of 50
        batch_size = 50
        for i in range(0, len(documents), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]

            self.collection.upsert(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_meta,
            )

        logger.info("Loaded %d chunks into ChromaDB collection '%s'", len(all_chunks), self.COLLECTION_NAME)
        return len(all_chunks)

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        """
        Similarity search over the knowledge base.

        Args:
            query: User query text.
            n_results: Number of top results to return.

        Returns:
            List of dicts with keys: text, source, section, distance.
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
        )

        hits = []
        if results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i] if results['metadatas'] else {}
                distance = results['distances'][0][i] if results['distances'] else 0.0
                hits.append({
                    'text': doc,
                    'source': meta.get('source', ''),
                    'section': meta.get('section', ''),
                    'language': meta.get('language', 'mixed'),
                    'distance': distance,
                })

        return hits

    def reset(self):
        """Delete and re-create the collection."""
        self.chroma.delete_collection(self.COLLECTION_NAME)
        self.collection = self.chroma.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={'hnsw:space': 'cosine'},
        )
        logger.info("Reset ChromaDB collection '%s'", self.COLLECTION_NAME)

    @staticmethod
    def _chunk_document(file_path: Path) -> list[dict]:
        """
        Split a markdown file into chunks by ## headers.

        Each chunk includes:
        - id: unique identifier (filename + section index)
        - text: the section content
        - metadata: source filename, section title, detected language
        """
        content = file_path.read_text(encoding='utf-8')
        source = file_path.stem  # e.g., "tariffs", "jepco_faq"

        # Split on ## headers (keep the header with its content)
        sections = re.split(r'(?=^## )', content, flags=re.MULTILINE)

        chunks = []
        for idx, section in enumerate(sections):
            text = section.strip()
            if not text or len(text) < 20:
                continue

            # Extract section title if present
            title_match = re.match(r'^##\s*(.+)', text)
            title = title_match.group(1).strip() if title_match else f'intro-{idx}'

            # Detect language
            arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
            total_alpha = len(re.findall(r'[a-zA-Z\u0600-\u06FF]', text))
            if total_alpha == 0:
                lang = 'mixed'
            elif arabic_chars / total_alpha > 0.5:
                lang = 'ar'
            elif arabic_chars / total_alpha > 0.1:
                lang = 'mixed'
            else:
                lang = 'en'

            chunks.append({
                'id': f'{source}__{idx:03d}',
                'text': text,
                'metadata': {
                    'source': source,
                    'section': title,
                    'language': lang,
                },
            })

        return chunks
