from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LAParams
from collections import defaultdict

def extract_paired_content(pdf_path, x_threshold=300):  # x_thresholdは左右を分ける境界のX座標
    laparams = LAParams(
        detect_vertical=False,
        all_texts=True
    )
    
    def classify_position(x0):
        """テキストブロックの位置（左/右）を判定"""
        return 'left' if x0 < x_threshold else 'right'
    
    paired_content = []
    
    for page_layout in extract_pages(pdf_path, laparams=laparams):
        # 同じY座標付近のテキストをグループ化するための辞書
        line_groups = defaultdict(lambda: {'left': [], 'right': []})
        
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                x0, y0, x1, y1 = element.bbox
                text = element.get_text().strip()
                
                if not text:
                    continue
                
                # Y座標を丸める（近い位置のテキストをグループ化するため）
                rounded_y = round(y0, 0)  # 精度は必要に応じて調整
                position = classify_position(x0)
                
                line_groups[rounded_y][position].append({
                    'text': text,
                    'x': x0,
                    'y': y0
                })
        
        # 各行のグループを処理
        for y_pos in sorted(line_groups.keys(), reverse=True):
            group = line_groups[y_pos]
            
            # 左側のテキスト（項目）を取得
            left_texts = sorted(group['left'], key=lambda x: x['x'])
            left_text = ' '.join(item['text'] for item in left_texts)
            
            # 右側のテキスト（内容）を取得
            right_texts = sorted(group['right'], key=lambda x: x['x'])
            right_text = ' '.join(item['text'] for item in right_texts)
            
            if left_text or right_text:
                paired_content.append((left_text, right_text))
    
    return paired_content

# 使用例
pdf_path = 'example.pdf'
content_pairs = extract_paired_content(pdf_path)

# マークダウン形式で出力
def format_as_markdown(pairs):
    markdown_lines = []
    for left, right in pairs:
        if left and right:
            markdown_lines.append(f"**{left.strip()}**\n: {right.strip()}\n")
        elif left:
            markdown_lines.append(f"**{left.strip()}**\n")
        elif right:
            markdown_lines.append(f": {right.strip()}\n")
    
    return '\n'.join(markdown_lines)

# マークダウンとして保存
markdown_content = format_as_markdown(content_pairs)
with open('paired_content.md', 'w', encoding='utf-8') as f:
    f.write(markdown_content)