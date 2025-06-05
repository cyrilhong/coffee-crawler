import chromadb
from sentence_transformers import SentenceTransformer
import json
import os

# PersistentClient
client = chromadb.PersistentClient(path="./chroma_store") # Modified path

# Get or create collection
collection_name = "coffee"
try:
    # Check if collection exists
    collection_exists = any(col.name == collection_name for col in client.list_collections())
    if collection_exists:
        print(f"Found existing collection '{collection_name}'. Clearing it for a fresh build.")
        client.delete_collection(name=collection_name)
    collection = client.create_collection(name=collection_name)
    print(f"Collection '{collection_name}' created successfully.")
except Exception as e:
    print(f"Error during collection handling: {e}. Attempting to create collection '{collection_name}' directly.")
    # If any error occurs (e.g. listing collections not supported, or delete fails unexpectedly)
    # try to create it directly. If it exists, get_or_create_collection would handle it.
    # However, to ensure a clean state as per requirements, explicit deletion is preferred.
    # For simplicity in this fallback, we'll use create_collection which might error if it exists and delete failed.
    # A more robust solution might involve get_or_create and then clearing if needed, but this fits the "fresh build" idea.
    try:
        collection = client.create_collection(name=collection_name)
        print(f"Collection '{collection_name}' created successfully after initial error.")
    except Exception as e2:
        print(f"Critical error: Could not ensure a clean collection '{collection_name}'. Error: {e2}")
        print("Please manually delete the 'chroma_store' directory and retry.")
        exit()


# Load SentenceTransformer
embedder_name = "BAAI/bge-small-zh-v1.5"
print(f"Loading SentenceTransformer model: {embedder_name}...")
try:
    embedder = SentenceTransformer(embedder_name)
    print("SentenceTransformer model loaded successfully.")
except Exception as e:
    print(f"Error loading SentenceTransformer model: {e}")
    exit()

# Lists to hold data for ChromaDB
chunks_data_list = []
documents_for_embedding = []
metadatas_for_chroma = []
ids_for_chroma = []

# Read and parse output.txt
output_file_path = "./output.txt" # Modified path
if not os.path.exists(output_file_path):
    print(f"Error: {output_file_path} not found. Please generate it using json2doc.py first.")
    exit()

print(f"Reading and parsing {output_file_path}...")
with open(output_file_path, "r", encoding="utf-8") as f:
    for line_number, line in enumerate(f, 1):
        try:
            chunk_data = json.loads(line.strip())
            if not all(k in chunk_data for k in ['doc_id', 'chunk_id', 'type', 'content', 'metadata']):
                print(f"Warning: Skipping line {line_number} due to missing essential keys: {line.strip()}")
                continue
            chunks_data_list.append(chunk_data)
        except json.JSONDecodeError:
            print(f"Warning: Skipping invalid JSON line {line_number}: {line.strip()}")
            continue

if not chunks_data_list:
    print(f"Error: No valid chunk data found in {output_file_path} or essential keys missing in all parsed chunks.")
    exit()
print(f"Successfully parsed {len(chunks_data_list)} chunks from {output_file_path}.")

# Prepare data for ChromaDB
print("Preparing data for ChromaDB...")
for idx, chunk_data_item in enumerate(chunks_data_list):
    documents_for_embedding.append(chunk_data_item['content'])

    chroma_metadata = chunk_data_item['metadata'].copy()
    chroma_metadata['doc_id'] = chunk_data_item['doc_id']
    chroma_metadata['chunk_id'] = chunk_data_item['chunk_id']
    chroma_metadata['type'] = chunk_data_item['type']

    for key, value in list(chroma_metadata.items()):
        if isinstance(value, (list, dict)):
            try:
                chroma_metadata[key] = json.dumps(value, ensure_ascii=False)
            except TypeError as e:
                print(f"Warning: Could not serialize metadata field '{key}' for chunk_id '{chunk_data_item['chunk_id']}'. Error: {e}. Storing as empty string.")
                chroma_metadata[key] = ""
        elif value is None:
            chroma_metadata[key] = ""

    for numeric_field in ['price', 'sold_count', 'rating', 'shop_rating']:
        value_str = str(chroma_metadata.get(numeric_field, "")).strip()
        processed_value = 0.0

        if numeric_field == 'price' and value_str:
            parts = value_str.split('-')
            first_part = parts[0].strip().replace(",", "") # Remove commas for float conversion
            try:
                processed_value = float(first_part)
            except ValueError:
                # Try to extract any number if the above fails (e.g. "NT$100")
                import re
                match = re.search(r'\d+\.?\d*', first_part)
                if match:
                    try:
                        processed_value = float(match.group(0))
                    except ValueError:
                        print(f"Warning: Could not parse number from price string '{value_str}' for chunk_id '{chunk_data_item['chunk_id']}' after regex. Setting to 0.0.")
                else:
                    print(f"Warning: Could not parse first number from price string '{value_str}' for chunk_id '{chunk_data_item['chunk_id']}'. Setting to 0.0.")
        elif value_str:
            try:
                # Remove commas for fields like sold_count ("1,234")
                processed_value = float(value_str.replace(",", ""))
            except ValueError:
                print(f"Warning: Could not convert metadata field '{numeric_field}' ('{value_str}') to float for chunk_id '{chunk_data_item['chunk_id']}'. Setting to 0.0.")

        chroma_metadata[numeric_field] = processed_value

    metadatas_for_chroma.append(chroma_metadata)
    ids_for_chroma.append(chunk_data_item['chunk_id'])

# Generate embeddings
if documents_for_embedding:
    print(f"Generating embeddings for {len(documents_for_embedding)} documents...")
    embeddings = embedder.encode(documents_for_embedding, show_progress_bar=True)
    print("Embeddings generated.")

    print(f"Adding {len(documents_for_embedding)} items to ChromaDB collection '{collection.name}'...")
    batch_size = 5000 # ChromaDB's default max batch size; can be tuned
    for i in range(0, len(documents_for_embedding), batch_size):
        batch_documents = documents_for_embedding[i:i+batch_size]
        batch_metadatas = metadatas_for_chroma[i:i+batch_size]
        batch_embeddings_list = [e.tolist() for e in embeddings[i:i+batch_size]]
        batch_ids = ids_for_chroma[i:i+batch_size]

        try:
            collection.add(
                documents=batch_documents,
                metadatas=batch_metadatas,
                embeddings=batch_embeddings_list,
                ids=batch_ids
            )
            print(f"Added batch {i//batch_size + 1} ({len(batch_ids)} items) to ChromaDB.")
        except Exception as e:
            print(f"Error adding batch {i//batch_size + 1} to ChromaDB: {e}")
            # Consider how to handle partial failures: skip batch, retry, or halt.
            # For now, just print error and continue.

    try:
        final_count = collection.count()
        print(f"✅ Successfully built vector store. Collection '{collection_name}' now contains {final_count} chunks.")
    except Exception as e:
        print(f"✅ Vector store build process completed. Error counting items: {e}")

else:
    print("No documents to embed. Vector store not updated.")

print("Script finished.")
