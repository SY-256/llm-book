from typing import List, Dict, Optional
import re
from dataclasses import dataclass
from langchain.text_splitter import MarkdownTextSplitter

@dataclass
class ChunkMetadata:
    source: str
    title: Optional[str] = None
    heading_hierarchy: List[str] = None
    is_code_block: bool = False
    is_table: bool = False
    is_list: bool = False

class OptimizedMarkdownChunker:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Markdownからタイトルを抽出"""
        lines = text.split('\n')
        for line in lines:
            # H1ヘッダーをタイトルとして扱う
            if line.startswith('# '):
                return line.lstrip('# ').strip()
        return None

    def _get_heading_hierarchy(self, text: str) -> List[str]:
        """見出しの階層構造を抽出"""
        headings = []
        lines = text.split('\n')
        for line in lines:
            if line.startswith('#'):
                level = len(re.match(r'^#+', line).group())
                heading = line.lstrip('#').strip()
                headings.append((level, heading))
        return [h[1] for h in headings]

    def _is_code_block(self, text: str) -> bool:
        """コードブロックかどうかを判定"""
        return text.strip().startswith('```') and text.strip().endswith('```')

    def _is_table(self, text: str) -> bool:
        """テーブルかどうかを判定"""
        lines = text.split('\n')
        if len(lines) < 2:
            return False
        # テーブルヘッダーとセパレータの検出
        return '|' in lines[0] and re.match(r'^[\s|:-]+$', lines[1])

    def _is_list(self, text: str) -> bool:
        """リストかどうかを判定"""
        lines = text.split('\n')
        for line in lines:
            if re.match(r'^\s*[-*+]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
                return True
        return False

    def _split_by_structure(self, text: str) -> List[str]:
        """構造に基づいてテキストを分割"""
        # 段落での分割
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # 特殊な構造（コードブロック、テーブル、リスト）は分割しない
            if (self._is_code_block(paragraph) or 
                self._is_table(paragraph) or 
                self._is_list(paragraph)):
                if current_chunk:
                    chunks.append(current_chunk)
                chunks.append(paragraph)
                current_chunk = ""
                continue
            
            # 通常の段落の処理
            if len(current_chunk) + len(paragraph) <= self.chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = paragraph + "\n\n"
                
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    def create_chunks(self, text: str, source: str) -> List[Dict]:
        """最適化されたチャンクを生成"""
        chunks = []
        title = self._extract_title(text)
        heading_hierarchy = self._get_heading_hierarchy(text)
        
        # 構造に基づいて分割
        raw_chunks = self._split_by_structure(text)
        
        for chunk in raw_chunks:
            if len(chunk) < self.min_chunk_size:
                continue
                
            metadata = ChunkMetadata(
                source=source,
                title=title,
                heading_hierarchy=heading_hierarchy,
                is_code_block=self._is_code_block(chunk),
                is_table=self._is_table(chunk),
                is_list=self._is_list(chunk)
            )
            
            chunks.append({
                "text": chunk.strip(),
                "metadata": metadata
            })
        
        return chunks

def create_vectorstore_from_markdown_directory(
    directory_path,
    client=None,
    chunk_size=1000,
    chunk_overlap=200,
    batch_size=100
):
    """最適化されたチャンク分割を使用してベクトルストアを作成"""
    embedder = AzureOpenAIEmbedder(client=client)
    vectorstore = SimpleVectorStore()
    
    # 最適化されたチャンカーの初期化
    chunker = OptimizedMarkdownChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    markdown_files = read_markdown_files(directory_path)
    current_texts = []
    current_metadatas = []
    
    for file_path, content in markdown_files:
        # 最適化されたチャンク分割を実行
        chunks = chunker.create_chunks(content, file_path)
        
        for chunk in chunks:
            current_texts.append(chunk["text"])
            current_metadatas.append({
                "source": chunk["metadata"].source,
                "title": chunk["metadata"].title,
                "heading_hierarchy": chunk["metadata"].heading_hierarchy,
                "is_code_block": chunk["metadata"].is_code_block,
                "is_table": chunk["metadata"].is_table,
                "is_list": chunk["metadata"].is_list
            })
            
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
