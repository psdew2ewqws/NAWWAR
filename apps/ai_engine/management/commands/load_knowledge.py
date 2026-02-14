"""
Management command to load knowledge base documents into ChromaDB.

Usage:
    python manage.py load_knowledge         # Load/update documents
    python manage.py load_knowledge --reset  # Clear and reload from scratch
"""
from django.core.management.base import BaseCommand

from apps.ai_engine.knowledge.loader import KnowledgeBaseLoader


class Command(BaseCommand):
    help = 'Load knowledge base documents into ChromaDB vector store.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing collection and reload all documents from scratch.',
        )

    def handle(self, *args, **options):
        loader = KnowledgeBaseLoader()

        if options['reset']:
            self.stdout.write(self.style.WARNING('Resetting ChromaDB collection...'))
            loader.reset()

        self.stdout.write('Loading knowledge base documents...')

        count = loader.load_documents()

        if count > 0:
            self.stdout.write(self.style.SUCCESS(f'Successfully loaded {count} chunks into ChromaDB.'))
        else:
            self.stdout.write(self.style.WARNING('No documents were loaded.'))

        # Show collection stats
        collection_count = loader.collection.count()
        self.stdout.write(f'Total chunks in collection: {collection_count}')
