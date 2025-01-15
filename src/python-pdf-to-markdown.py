from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTLine, LAParams
import re

def extract_markdown_text(pdf_path):
    laparams = LAParams(
        detect_vertical=False,
        all_texts=True
    )
    
    def get_font_info(element):
        """フォントサイズと太さを取得"""
        fonts = []
        sizes = []
        for text_line in element:
            if isinstance(text_line, LTChar):
                fonts.append(text_line.fontname)
                sizes.append(text_line.size)
        
        # 最も多く使用されているフォントとサイズを返す
        if fonts and sizes:
            return max(set(fonts), key=fonts.count), max(set(sizes), key=sizes.count)
        return None, None

    markdown_blocks = []
    
    for page_layout in extract_pages(pdf_path, laparams=laparams):
        page_texts = []
        
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                x0, y0, x1, y1 = element.bbox
                text = element.get_text().strip()
                
                if not text:
                    continue
                
                font_name, font_size = get_font_info(element)
                
                # フォントサイズに基づいてマークダウンの見出しレベルを決定
                if font_size:
                    if font_size > 20:
                        text = f"# {text}"
                    elif font_size > 16:
                        text = f"## {text}"
                    elif font_size > 14:
                        text = f"### {text}"
                
                # 太字フォントの検出
                if font_name and ('bold' in font_name.lower() or 'heavy' in font_name.lower()):
                    if not text.startswith('#'):
                        text = f"**{text}**"
                
                page_texts.append({
                    'text': text,
                    'y': -y0,
                    'x': x0
                })
        
        # ソート
        page_texts.sort(key=lambda x: (x['y'], x['x']))
        
        # 箇条書きの検出と変換
        for block in page_texts:
            text = block['text']
            # 行頭の記号を検出して箇条書きに変換
            if text.lstrip().startswith(('•', '・', '○', '►')):
                text = re.sub(r'^[•・○►]\s*', '* ', text.lstrip())
            # 番号付きリストの検出
            elif re.match(r'^\d+[\.\)］】]\s', text):
                text = re.sub(r'^\d+([\.\)］】])\s', r'1. ', text)
            
            markdown_blocks.append(text)
        
        # ページ区切りの追加
        markdown_blocks.append('\n---\n')
    
    # 最後のページ区切りを削除
    if markdown_blocks[-1] == '\n---\n':
        markdown_blocks.pop()
    
    # 連続する空行を1つにまとめる
    markdown_text = '\n'.join(markdown_blocks)
    markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
    
    return markdown_text


# 使用例
pdf_path = 'example.pdf'
markdown_text = extract_markdown_text(pdf_path)
print(markdown_text)

# マークダウンファイルとして保存
with open('output.md', 'w', encoding='utf-8') as f:
    f.write(markdown_text)

def enhance_markdown_formatting(text):
    # インラインコードの検出と変換
    text = re.sub(r'`([^`]+)`', r'`\1`', text)
    
    # 引用の検出と変換
    text = re.sub(r'^>.+', lambda m: f"> {m.group(0)[1:].strip()}", text, flags=re.M)
    
    # テーブルの検出と変換
    # （簡単な表の場合）
    text = re.sub(r'[\|｜]', '|', text)
    
    # リンクの検出と変換
    text = re.sub(r'(https?://\S+)', r'[\1](\1)', text)
    
    return text

# 使用時
markdown_text = enhance_markdown_formatting(markdown_text)