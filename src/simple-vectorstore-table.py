from typing import List, Dict, Tuple, Optional, Union
import re

class MarkdownTableParser:
    """マークダウンの表を解析するクラス"""
    
    @staticmethod
    def is_table_row(line: str) -> bool:
        """行が表の一部かどうかを判定"""
        return bool(line.strip().startswith('|') and line.strip().endswith('|'))
    
    @staticmethod
    def is_separator_row(line: str) -> bool:
        """区切り行かどうかを判定"""
        clean_line = line.strip().strip('|')
        return bool(re.match(r'^[\s\-:]+$', clean_line))
    
    @staticmethod
    def parse_row(row: str) -> List[str]:
        """表の行をパースして各セルの値を取得"""
        return [cell.strip() for cell in row.strip().strip('|').split('|')]
    
    def extract_tables(self, markdown_text: str) -> List[Dict[str, Union[List[str], List[Dict[str, str]]]]]:
        """マークダウンテキストから表を抽出"""
        tables = []
        current_table = None
        lines = markdown_text.split('\n')
        
        for i, line in enumerate(lines):
            if not line.strip():
                if current_table and current_table.get('data'):  # データがある場合のみ追加
                    tables.append(current_table)
                    current_table = None
                continue
            
            if self.is_table_row(line):
                if not current_table:
                    # 新しい表の開始
                    current_table = {
                        'headers': self.parse_row(line),
                        'data': []
                    }
                elif not self.is_separator_row(line):
                    # データ行の処理
                    row_data = self.parse_row(line)
                    if len(row_data) == len(current_table['headers']):
                        row_dict = dict(zip(current_table['headers'], row_data))
                        current_table['data'].append(row_dict)
        
        # 最後の表を処理
        if current_table and current_table.get('data'):
            tables.append(current_table)
        
        return tables

class TableAwareMarkdownTextSplitter:
    """表構造を認識するマークダウンテキストスプリッター"""
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.table_parser = MarkdownTableParser()
    
    def create_table_chunk(self, table: Dict) -> Tuple[str, Dict]:
        """表データからチャンクとメタデータを生成"""
        headers = table['headers']
        structured_text = "表形式データ:\n"
        
        # ヘッダー情報を含める
        structured_text += f"列: {', '.join(headers)}\n\n"
        
        # 各行のデータを構造化テキストに変換
        for row in table['data']:
            row_text = []
            for header in headers:
                row_text.append(f"{header}: {row[header]}")
            structured_text += "- " + " | ".join(row_text) + "\n"
        
        metadata = {
            "type": "table",
            "headers": headers,
            "row_count": len(table['data'])
        }
        
        return structured_text, metadata
    
    def split_text(self, text: str) -> List[Tuple[str, Dict]]:
        """テキストを表とその他のチャンクに分割"""
        # 表の抽出
        tables = self.table_parser.extract_tables(text)
        chunks_with_metadata = []
        
        # 表をチャンクに変換
        for table in tables:
            chunk_text, metadata = self.create_table_chunk(table)
            chunks_with_metadata.append((chunk_text, metadata))
        
        # 残りのテキストの処理（表以外の部分）
        # ここでは簡単のため、表以外のテキストは1つのチャンクとして扱う
        non_table_text = text
        for table in tables:
            # 表の部分を空行に置換
            table_text = "\n".join(
                "|" + "|".join(row.values()) + "|"
                for row in table['data']
            )
            non_table_text = non_table_text.replace(table_text, "\n\n")
        
        if non_table_text.strip():
            chunks_with_metadata.append((
                non_table_text.strip(),
                {"type": "text"}
            ))
        
        return chunks_with_metadata

def create_vectorstore_from_markdown_directory(
    directory_path,
    client=None,
    chunk_size=1000,
    chunk_overlap=200,
    batch_size=100
):
    """ディレクトリ内の全マークダウンファイルからベクトルストアを作成（表対応版）"""
    embedder = AzureOpenAIEmbedder(client=client)
    vectorstore = SimpleVectorStore()

    # 表認識付きテキストスプリッターの設定
    text_splitter = TableAwareMarkdownTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    markdown_files = read_markdown_files(directory_path)
    
    current_texts = []
    current_metadatas = []
    
    for file_path, content in markdown_files:
        # テキストを表を含むチャンクに分割
        chunks_with_metadata = text_splitter.split_text(content)
        
        for chunk_text, chunk_metadata in chunks_with_metadata:
            # ファイル情報をメタデータに追加
            chunk_metadata["source"] = file_path
            
            current_texts.append(chunk_text)
            current_metadatas.append(chunk_metadata)
            
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