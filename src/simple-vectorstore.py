from pathlib import Path
import numpy as np
import json
import os
from typing import List, Dict, Tuple, Optional
from openai import AzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import pickle

class SimpleVectorStore:
    def __init__(self):
        self.vectors = []        # 埋め込みベクトルを保存
        self.texts = []          # 元のテキストを保存
        self.metadatas = []      # メタデータを保存

    def add_vectors(self, vectors: List[List[float]], texts: List[str], metadatas: Optional[List[Dict]] = None):
        """ベクトル、テキスト、メタデータを追加"""
        if not metadatas:
            metadatas = [{} for _ in texts]
        
        for vector, text, metadata in zip(vectors, texts, metadatas):
            self.vectors.append(vector)
            self.texts.append(text)
            self.metadatas.append(metadata)

    def similarity_search(self, query_vector: List[float], k: int = 5) -> List[Tuple[Dict, float]]:
        """コサイン類似度に基づく検索を実行"""
        if not self.vectors:
            return []

        # numpy配列に変換
        vectors = np.array(self.vectors)
        query_vector = np.array(query_vector)

        # コサイン類似度を計算
        similarities = np.dot(vectors, query_vector) / (
            np.linalg.norm(vectors, axis=1) * np.linalg.norm(query_vector)
        )

        # 上位k件のインデックスを取得
        top_k_indices = np.argsort(similarities)[-k:][::-1]

        # 結果を作成
        results = []
        for idx in top_k_indices:
            doc = {
                "page_content": self.texts[idx],
                "metadata": self.metadatas[idx]
            }
            results.append((doc, float(similarities[idx])))

        return results

    def save(self, path: str):
        """ベクトルストアをファイルに保存"""
        data = {
            'vectors': self.vectors,
            'texts': self.texts,
            'metadatas': self.metadatas
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)

    @classmethod
    def load(cls, path: str):
        """ファイルからベクトルストアを読み込み"""
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        store = cls()
        store.vectors = data['vectors']
        store.texts = data['texts']
        store.metadatas = data['metadatas']
        return store

class AzureOpenAIEmbedder:
    """Azure OpenAIを使用して埋め込みを生成するクラス"""
    def __init__(self, client=None, model=None, timeout=60):
        self.client = client or AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        )
        self.model = model or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def embed_documents(self, texts):
        """テキストの配列を埋め込みベクトルに変換"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                timeout=self.timeout
            )
            return [embedding.embedding for embedding in response.data]
        except Exception as e:
            print(f"埋め込み生成中にエラーが発生: {e}")
            raise

    def embed_query(self, text):
        """単一のクエリテキストを埋め込みベクトルに変換"""
        return self.embed_documents([text])[0]

def read_markdown_files(directory_path):
    """指定されたディレクトリから全てのマークダウンファイルを読み込む"""
    markdown_files = []
    directory = Path(directory_path)
    
    for extension in ['*.md', '*.markdown']:
        for file_path in directory.rglob(extension):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    relative_path = str(file_path.relative_to(directory))
                    markdown_files.append((relative_path, content))
            except Exception as e:
                print(f"警告: ファイル {file_path} の読み込み中にエラーが発生しました: {e}")
    
    return markdown_files

def create_vectorstore_from_markdown_directory(
    directory_path,
    client=None,
    chunk_size=1000,
    chunk_overlap=200,
    batch_size=100
):
    """ディレクトリ内の全マークダウンファイルからベクトルストアを作成"""
    from langchain.text_splitter import MarkdownTextSplitter
    
    embedder = AzureOpenAIEmbedder(client=client)
    vectorstore = SimpleVectorStore()

    # テキストスプリッターの設定
    text_splitter = MarkdownTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    markdown_files = read_markdown_files(directory_path)
    
    current_texts = []
    current_metadatas = []
    
    for file_path, content in markdown_files:
        chunks = text_splitter.split_text(content)
        
        for chunk in chunks:
            current_texts.append(chunk)
            current_metadatas.append({"source": file_path})
            
            if len(current_texts) >= batch_size:
                try:
                    embeddings = embedder.embed_documents(current_texts)
                    vectorstore.add_vectors(embeddings, current_texts, current_metadatas)
                    
                    current_texts = []
                    current_metadatas = []
                    
                except Exception as e:
                    print(f"警告: バッチ処理中にエラーが発生しました: {e}")
                    current_texts = []
                    current_metadatas = []
    
    # 残りのテキストを処理
    if current_texts:
        try:
            embeddings = embedder.embed_documents(current_texts)
            vectorstore.add_vectors(embeddings, current_texts, current_metadatas)
        except Exception as e:
            print(f"警告: 最終バッチの処理中にエラーが発生しました: {e}")

    return vectorstore

# 使用例
if __name__ == "__main__":
    # Azure OpenAI の環境変数設定
    os.environ["AZURE_OPENAI_API_KEY"] = "your-api-key"
    os.environ["AZURE_OPENAI_ENDPOINT"] = "your-endpoint"
    os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "your-deployment-name"
    os.environ["AZURE_OPENAI_API_VERSION"] = "2024-02-15-preview"

    try:
        # クライアントの初期化
        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION")
        )

        # マークダウンファイルのあるディレクトリからベクトルストアを作成
        markdown_dir = "path/to/markdown/files"
        vectorstore = create_vectorstore_from_markdown_directory(
            markdown_dir,
            client=client,
            chunk_size=500,
            chunk_overlap=100,
            batch_size=50
        )

        # 検索例
        embedder = AzureOpenAIEmbedder(client=client)
        query = "検索したいキーワード"
        query_vector = embedder.embed_query(query)
        results = vectorstore.similarity_search(query_vector, k=3)
        
        print("検索結果:")
        for doc, score in results:
            print(f"\nスコア: {score}")
            print(f"ソース: {doc['metadata'].get('source', '不明')}")
            print(f"内容: {doc['page_content']}")

        # ベクトルストアの保存
        vectorstore.save("vectorstore_save.pkl")

        # ベクトルストアの読み込み
        loaded_vectorstore = SimpleVectorStore.load("vectorstore_save.pkl")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
