from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import AzureOpenAIEmbeddings
from langchain.text_splitter import MarkdownTextSplitter
from pathlib import Path
import os

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
    
    # .mdと.markdownの両方のファイルを検索
    for extension in ['*.md', '*.markdown']:
        for file_path in directory.rglob(extension):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # ファイル名（パスを含む）とコンテンツを保存
                    relative_path = str(file_path.relative_to(directory))
                    markdown_files.append((relative_path, content))
            except Exception as e:
                print(f"警告: ファイル {file_path} の読み込み中にエラーが発生しました: {e}")
    
    return markdown_files

def create_vectorstore_from_markdown_directory(
    directory_path,
    embeddings_model=None,
    chunk_size=1000,
    chunk_overlap=200,
    include_metadata=True
):
    """
    ディレクトリ内の全マークダウンファイルからFAISSベクトルストアを作成する

    Parameters:
        directory_path (str): マークダウンファイルのあるディレクトリパス
        embeddings_model: 埋め込みモデル（デフォルトはAzureOpenAIEmbeddings）
        chunk_size (int): チャンクサイズ
        chunk_overlap (int): チャンクオーバーラップ
        include_metadata (bool): メタデータを含めるかどうか

    Returns:
        FAISS: 作成されたベクトルストア
    """
    # 埋め込みモデルの設定
    if embeddings_model is None:
        embeddings_model = AzureOpenAIEmbeddings(
            azure_deployment="your-embeddings-deployment",
            openai_api_version="2024-02-15-preview"
        )

    # テキストスプリッターの設定
    text_splitter = MarkdownTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    all_texts = []
    all_metadatas = []

    # 全てのマークダウンファイルを読み込み
    markdown_files = read_markdown_files(directory_path)
    
    for file_path, content in markdown_files:
        # テキストを分割
        chunks = text_splitter.split_text(content)
        
        # メタデータを追加
        if include_metadata:
            metadatas = [{"source": file_path} for _ in chunks]
            all_metadatas.extend(metadatas)
        
        all_texts.extend(chunks)

    # ベクトルストアの作成
    if include_metadata:
        vectorstore = FAISS.from_texts(
            texts=all_texts,
            embedding=embeddings_model,
            metadatas=all_metadatas
        )
    else:
        vectorstore = FAISS.from_texts(
            texts=all_texts,
            embedding=embeddings_model
        )

    return vectorstore

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
    """
    ベクトルストアを保存する

    Parameters:
        vectorstore (FAISS): 保存するベクトルストア
        save_path (str): 保存先のパス
    """
    vectorstore.save_local(save_path)

def load_vectorstore(load_path, embeddings_model=None):
    """
    保存されたベクトルストアを読み込む

    Parameters:
        load_path (str): 読み込むベクトルストアのパス
        embeddings_model: 埋め込みモデル（デフォルトはAzureOpenAIEmbeddings）

    Returns:
        FAISS: 読み込まれたベクトルストア
    """
    if embeddings_model is None:
        embeddings_model = AzureOpenAIEmbeddings(
            azure_deployment="your-embeddings-deployment",
            openai_api_version="2024-02-15-preview"
        )
    
    vectorstore = FAISS.load_local(load_path, embeddings_model)
    return vectorstore

# 使用例
if __name__ == "__main__":
    # Azure OpenAI APIの環境変数設定
    os.environ["AZURE_OPENAI_API_KEY"] = "your-api-key-here"
    os.environ["AZURE_OPENAI_ENDPOINT"] = "your-endpoint-here"

    # 埋め込みモデルの設定
    embeddings_model = AzureOpenAIEmbeddings(
        azure_deployment="your-embeddings-deployment",
        openai_api_version="2024-02-15-preview"
    )

    # マークダウンファイルのあるディレクトリからベクトルストアを作成
    markdown_dir = "path/to/markdown/files"
    vectorstore = create_vectorstore_from_markdown_directory(
        markdown_dir,
        embeddings_model=embeddings_model,
        chunk_size=500,
        chunk_overlap=100
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

    # ベクトルストアの読み込み
    loaded_vectorstore = load_vectorstore("vectorstore_save")