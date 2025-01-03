from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.chat_models import ChatOpenAI
from config import OPENAI_API_KEY
import os

# Initialize HuggingFace Embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = Chroma(persist_directory="chroma_db", embedding_function=embeddings)

# Initialize OpenAI LLM (GPT-4o Mini)
llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY)


# Load all documents from the 'documents' folder into ChromaDB
def load_documents():
    try:
        document_folder = "documents"
        
        if not os.path.exists(document_folder):
            print(f"❌ Error: Folder '{document_folder}' not found. Please ensure the folder exists.")
            return
        
        files = [f for f in os.listdir(document_folder) if f.endswith('.txt')]
        
        if not files:
            print(f"❌ Error: No text files found in '{document_folder}'.")
            return
        
        print(f"📂 Found {len(files)} text file(s) in '{document_folder}': {', '.join(files)}")
        
        for file in files:
            document_path = os.path.join(document_folder, file)
            print(f"📄 Ingesting Document: {file}")
            
            # Load each document
            loader = TextLoader(document_path)
            documents = loader.load()
            
            # Optimal chunking
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=200,
                chunk_overlap=50
            )
            chunks = text_splitter.split_documents(documents)
            
            if not chunks:
                print(f"❌ Warning: Document '{file}' splitting resulted in no chunks. Skipping...")
                continue
            
            db.add_documents(chunks)
            print(f"✅ Document '{file}' successfully ingested with {len(chunks)} chunks into ChromaDB!")
    
    except FileNotFoundError:
        print("❌ Error: Document file not found. Please ensure the folder and files exist.")
    except Exception as e:
        print(f"❌ Unexpected Error during ingestion: {e}")


# Process user query with Retriever + OpenAI LLM
def query_document(query: str) -> str:
    try:
        retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        docs = retriever.get_relevant_documents(query)
        
        if not docs:
            return "No relevant information found."
        
        # Combine chunks into a single context
        context = "\n".join([doc.page_content for doc in docs])
        
        # Build a prompt for GPT-4o Mini
        prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        
        response = llm.predict(prompt)
        return response.strip()
    
    except Exception as e:
        return f"❌ Error processing query: {e}"


# Automatically ingest documents when script is run directly
if __name__ == "__main__":
    print("🚀 Starting document ingestion...")
    load_documents()
    print("✅ Ingestion complete")
