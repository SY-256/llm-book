from pathlib import Path
import numpy as np
import json
import os
import pickle
from typing import List, Dict, Tuple, Optional, Union
from openai import AzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import time
from datetime import datetime

class EnhancedVectorStore:
    def __init__(self):
        self.vectors = []        # 埋め込みベクトルを保存
        self.texts = []          # 元のテキストを保存
        self.metadatas = []      # メタデータを保存
        self.source_stats = {}   # ソースタイプごとの統計情報

    def add_vectors(
        self, 
        vectors: List[List[float]], 
        texts: List[str], 
        metadatas: Optional[List[Dict]] = None,
        source_type: str = None,
        original_format: str = None
    ):
        """ベクトル、テキスト、メタデータを追加"""
        if not metadatas:
            metadatas = [{} for _ in texts]

        # メタデータの拡張
        for metadata in metadatas:
            if source_type:
                metadata["source_type"] = source_type
            if original_format:
                metadata["original_format"] = original_format
            metadata["added_at"] = datetime.now().isoformat()

        self.vectors.extend(vectors)
        self.texts.extend(texts)
        self.metadatas.extend(metadatas)
        self._update_stats()

    def similarity_search(
        self, 
        query_vector: List[float], 
        k: int = 5,
        source_type: Optional[Union[str, List[str]]] = None
    ) -> List[Tuple[Dict, float]]:
        """
        コサイン類似度に基づく検索を実行
        source_typeを指定して特定のソースタイプのみを検索可能
        """
        if not self.vectors:
            return []

        # ソースタイプによるフィルタリング用のマスクを作成
        if source_type:
            if isinstance(source_type, str):
                source_types = [source_type]
            else:
                source_types = source_type
            
            mask = [
                metadata.get("source_type") in source_types 
                for metadata in self.metadatas
            ]
            filtered_vectors = [v for v, m in zip(self.vectors, mask) if m]
            filtered_texts = [t for t, m in zip(self.texts, mask) if m]
            filtered_metadatas = [m for m, mask_val in zip(self.metadatas, mask) if mask_val]
        else:
            filtered_vectors = self.vectors
            filtered_texts = self.texts
            filtered_metadatas = self.metadatas

        if not filtered_vectors:
            return []

        # numpy配列に変換
        vectors = np.array(filtered_vectors)
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
                "page_content": filtered_texts[idx],
                "metadata": filtered_metadatas[idx]
            }
            results.append((doc, float(similarities[idx])))

        return results

    def get_stats(self) -> Dict:
        """ベクトルストアの統計情報を取得"""
        self._update_stats()
        return self.source_stats

    def _update_stats(self):
        """統計情報を更新"""
        stats = {}
        for metadata in self.metadatas:
            source_type = metadata.get("source_type", "unknown")
            if source_type not in stats:
                stats[source_type] = {
                    "count": 0,
                    "formats": set(),
                    "oldest": None,
                    "newest": None
                }
            
            stats[source_type]["count"] += 1
            
            if "original_format" in metadata:
                stats[source_type]["formats"].add(metadata["original_format"])
            
            added_at = metadata.get("added_at")
            if added_at:
                if not stats[source_type]["oldest"] or added_at < stats[source_type]["oldest"]:
                    stats[source_type]["oldest"] = added_at
                if not stats[source_type]["newest"] or added_at > stats[source_type]["newest"]:
                    stats[source_type]["newest"] = added_at

        # setをリストに変換（JSON対応のため）
        for source_type in stats:
            stats[source_type]["formats"] = list(stats[source_type]["formats"])

        self.source_stats = stats

    def clear_by_source(self, source_type: str):
        """特定のソースタイプのデータのみを削除"""
        indices_to_keep = [
            i for i, metadata in enumerate(self.metadatas)
            if metadata.get("source_type") != source_type
        ]
        
        self.vectors = [self.vectors[i] for i in indices_to_keep]
        self.texts = [self.texts[i] for i in indices_to_keep]
        self.metadatas = [self.metadatas[i] for i in indices_to_keep]
        self._update_stats()

    def save(self, path: str):
        """ベクトルストアをファイルに保存"""
        data = {
            'vectors': self.vectors,
            'texts': self.texts,
            'metadatas': self.metadatas,
            'source_stats': self.source_stats
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
        store.source_stats = data.get('source_stats', {})
        return store

def create_vectorstore_from_markdown_directory(
    directory_path: str,
    client: AzureOpenAI,
    source_type: str,
    original_format: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    batch_size: int = 100
) -> EnhancedVectorStore:
    """
    ディレクトリ内の全マークダウンファイルからベクトルストアを作成
    """
    from langchain.text_splitter import MarkdownTextSplitter
    
    embedder = AzureOpenAIEmbedder(client=client)
    vectorstore = EnhancedVectorStore()

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
                    vectorstore.add_vectors(
                        vectors=embeddings,
                        texts=current_texts,
                        metadatas=current_metadatas,
                        source_type=source_type,
                        original_format=original_format
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
            vectorstore.add_vectors(
                vectors=embeddings,
                texts=current_texts,
                metadatas=current_metadatas,
                source_type=source_type,
                original_format=original_format
            )
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

        # 各ソースからベクトルストアを作成
        vectorstore = EnhancedVectorStore()

        # Wordから変換されたマークダウンの処理
        word_markdown_dir = "path/to/word/markdown/files"
        word_vectors = create_vectorstore_from_markdown_directory(
            word_markdown_dir,
            client=client,
            source_type="word",
            original_format="docx",
            chunk_size=500,
            chunk_overlap=100,
            batch_size=50
        )

        # PDFから変換されたマークダウンの処理
        pdf_markdown_dir = "path/to/pdf/markdown/files"
        pdf_vectors = create_vectorstore_from_markdown_directory(
            pdf_markdown_dir,
            client=client,
            source_type="pdf",
            original_format="pdf",
            chunk_size=500,
            chunk_overlap=100,
            batch_size=50
        )

        # HTMLから変換されたマークダウンの処理
        html_markdown_dir = "path/to/html/markdown/files"
        html_vectors = create_vectorstore_from_markdown_directory(
            html_markdown_dir,
            client=client,
            source_type="html",
            original_format="html",
            chunk_size=500,
            chunk_overlap=100,
            batch_size=50
        )

        # 統計情報の表示
        stats = vectorstore.get_stats()
        print("\n統計情報:")
        for source_type, info in stats.items():
            print(f"\nソースタイプ: {source_type}")
            print(f"ドキュメント数: {info['count']}")
            print(f"元のフォーマット: {', '.join(info['formats'])}")
            print(f"最古のドキュメント: {info['oldest']}")
            print(f"最新のドキュメント: {info['newest']}")

        # 検索例（全ソース）
        embedder = AzureOpenAIEmbedder(client=client)
        query = "検索したいキーワード"
        query_vector = embedder.embed_query(query)
        results = vectorstore.similarity_search(query_vector, k=3)
        
        print("\n全ソースからの検索結果:")
        for doc, score in results:
            print(f"\nスコア: {score}")
            print(f"ソース: {doc['metadata'].get('source', '不明')}")
            print(f"ソースタイプ: {doc['metadata'].get('source_type', '不明')}")
            print(f"元のフォーマット: {doc['metadata'].get('original_format', '不明')}")
            print(f"内容: {doc['page_content']}")

        # 特定のソースタイプのみ検索
        word_results = vectorstore.similarity_search(
            query_vector, 
            k=3,
            source_type="word"
        )
        
        print("\nWordドキュメントからの検索結果:")
        for doc, score in word_results:
            print(f"\nスコア: {score}")
            print(f"ソース: {doc['metadata'].get('source', '不明')}")
            print(f"内容: {doc['page_content']}")

        # ベクトルストアの保存
        vectorstore.save("enhanced_vectorstore.pkl")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
