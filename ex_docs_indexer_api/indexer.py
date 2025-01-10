from langchain_community.document_loaders import RecursiveUrlLoader
from langchain_community.document_transformers import MarkdownifyTransformer
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import argparse
import os

PERSIST_DIR = "chroma_data"

def process_url(url: str):
    print(f"Processing URL: {url}")

    # Initialize ChromaDB with local persistence
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings)

    try:
        # Load and process content
        loader = RecursiveUrlLoader(
            url=url,
            base_url=url,
            max_depth=15,
            use_async=False,
            prevent_outside=True,
        )
        docs = loader.load()

        content_docs = []
        for doc in docs:
            soup = BeautifulSoup(doc.page_content, 'html.parser')
            main_content = soup.find('main')
            if main_content == "":
                continue

            for a_tag in main_content.find_all('a', href=True):
                # Convert relative URL to absolute
                a_tag['href'] = urljoin(doc.metadata['source'], a_tag['href'])

            doc.page_content = str(main_content)
            content_docs.append(doc)

        print(f"Num docs loaded recursively: {len(docs)}")
        for doc in docs:
            print(doc.metadata['source'])
        print()

        md = MarkdownifyTransformer(autolinks=False)
        docs = md.transform_documents(docs)

        # Split into chunks
        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ('#', 'h1'),
                ('##', 'h2'),
                ('###', 'h3'),
            ]
        )

        all_chunks = []
        for doc in docs:
            chunks = splitter.split_text(doc.page_content)
            for chunk in chunks:
                chunk.metadata = {
                    **chunk.metadata,
                    **doc.metadata,
                }
                if len(all_chunks) % 100 == 0:
                    print(chunk)
                all_chunks.append(chunk)

        # Store in ChromaDB
        print(f"Adding {len(all_chunks)} document chunks to ChromaDB...")
        db.add_documents(all_chunks)
        print("Successfully processed and stored content")

    except Exception as e:
        print(f"Error processing URL: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process URL content into ChromaDB')
    parser.add_argument('url', help='URL to process')
    args = parser.parse_args()

    process_url(args.url)
