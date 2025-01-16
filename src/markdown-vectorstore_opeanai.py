from langchain_community.vectorstores import FAISS
from pathlib import Path
import os
import numpy as np
from openai import AzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import time

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
        """
        テキストの配列を埋め込みベクトルに変換
        """
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
        """
        単一のクエリテキストを埋め込みベクトルに変換
        """
        return self.embed_documents([text])[0]

def read_markdown_files(directory_path):
    """
    指定されたディレクトリから全てのマークダウンファイルを読み込む

    Parameters:
        directory_path (str): マークダウンファイルのあるディレクトリパス

    Returns:
        list: (ファイル名, コンテンツ) のタプルのリスト
    """
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
    include_metadata=True,
    batch_size=100
):
    """
    ディレクトリ内の全マークダウンファイルからFAISSベクトルストアを作成する

    Parameters:
        directory_path (str): マークダウンファイルのあるディレクトリパス
        client: Azure OpenAIクライアント（オプション）
        chunk_size (int): チャンクサイズ
        chunk_overlap (int): チャンクオーバーラップ
        include_metadata (bool): メタデータを含めるかどうか
        batch_size (int): 一度に処理するテキストの数

    Returns:
        FAISS: 作成されたベクトルストア
    """
    from langchain.text_splitter import MarkdownTextSplitter
    
    # 埋め込みモデルの初期化
    embedder = AzureOpenAIEmbedder(client=client)

    # テキストスプリッターの設定
    text_splitter = MarkdownTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    markdown_files = read_markdown_files(directory_path)
    
    vectorstore = None
    current_texts = []
    current_metadatas = []
    
    for file_path, content in markdown_files:
        chunks = text_splitter.split_text(content)
        
        for chunk in chunks:
            current_texts.append(chunk)
            if include_metadata:
                current_metadatas.append({"source": file_path})
            
            if len(current_texts) >= batch_size:
                try:
                    embeddings = embedder.embed_documents(current_texts)
                    
                    if vectorstore is None:
                        if include_metadata:
                            vectorstore = FAISS.from_embeddings(
                                text_embeddings=list(zip(current_texts, embeddings)),
                                embedding=embedder,
                                metadatas=current_metadatas
                            )
                        else:
                            vectorstore = FAISS.from_embeddings(
                                text_embeddings=list(zip(current_texts, embeddings)),
                                embedding=embedder
                            )
                    else:
                        if include_metadata:
                            vectorstore.add_embeddings(
                                text_embeddings=list(zip(current_texts, embeddings)),
                                metadatas=current_metadatas
                            )
                        else:
                            vectorstore.add_embeddings(
                                text_embeddings=list(zip(current_texts, embeddings))
                            )
                    
                    current_texts = []
                    current_metadatas = []
                    time.sleep(1)  # レート制限を避けるための待機
                    
                except Exception as e:
                    print(f"警告: バッチ処理中にエラーが発生しました: {e}")
                    current_texts = []
                    current_metadatas = []
    
    # 残りのテキストを処理
    if current_texts:
        try:
            embeddings = embedder.embed_documents(current_texts)
            
            if vectorstore is None:
                if include_metadata:
                    vectorstore = FAISS.from_embeddings(
                        text_embeddings=list(zip(current_texts, embeddings)),
                        embedding=embedder,
                        metadatas=current_metadatas
                    )
                else:
                    vectorstore = FAISS.from_embeddings(
                        text_embeddings=list(zip(current_texts, embeddings)),
                        embedding=embedder
                    )
            else:
                if include_metadata:
                    vectorstore.add_embeddings(
                        text_embeddings=list(zip(current_texts, embeddings)),
                        metadatas=current_metadatas
                    )
                else:
                    vectorstore.add_embeddings(
                        text_embeddings=list(zip(current_texts, embeddings))
                    )
        except Exception as e:
            print(f"警告: 最終バッチの処理中にエラーが発生しました: {e}")

    return vectorstore

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def search_vectorstore(vectorstore, query, k=5):
    """
    ベクトルストアから類似度検索を実行する

    Parameters:
        vectorstore (FAISS): 検索対象のベクトルストア
        query (str): 検索クエリ
        k (int): 返す結果の数

    Returns:
        list: 類似度が高い順のドキュメントとスコアのリスト
    """
    results = vectorstore.similarity_search_with_score(query, k=k)
    return results

def save_vectorstore(vectorstore, save_path):
    """ベクトルストアを保存する"""
    vectorstore.save_local(save_path)

def load_vectorstore(load_path, client=None):
    """保存されたベクトルストアを読み込む"""
    embedder = AzureOpenAIEmbedder(client=client)
    vectorstore = FAISS.load_local(load_path, embedder)
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
        query = "検索したいキーワード"
        results = search_vectorstore(vectorstore, query, k=3)
        
        print("検索結果:")
        for doc, score in results:
            print(f"\nスコア: {score}")
            print(f"ソース: {doc.metadata.get('source', '不明')}")
            print(f"内容: {doc.page_content}")

        # ベクトルストアの保存
        save_vectorstore(vectorstore, "vectorstore_save")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
