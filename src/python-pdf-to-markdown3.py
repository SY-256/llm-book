def extract_paired_content_advanced(pdf_path, x_threshold=300, y_tolerance=5):
    laparams = LAParams(detect_vertical=False, all_texts=True)
    
    def is_same_line(y1, y2):
        """2つのY座標が同じ行とみなせるかを判定"""
        return abs(y1 - y2) <= y_tolerance
    
    def format_text(text, font_size=None):
        """テキストのフォーマット処理"""
        text = text.strip()
        if font_size and font_size > 14:
            return f"**{text}**"
        return text
    
    paired_content = []
    current_left = []
    current_right = []
    last_y = None
    
    for page_layout in extract_pages(pdf_path, laparams=laparams):
        texts = []
        
        # テキスト要素の収集
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                x0, y0, x1, y1 = element.bbox
                text = element.get_text().strip()
                
                if text:
                    texts.append({
                        'text': text,
                        'x': x0,
                        'y': y0,
                        'height': y1 - y0,
                        'width': x1 - x0
                    })
        
        # Y座標でソート（上から下）
        texts.sort(key=lambda x: (-x['y'], x['x']))
        
        for text_obj in texts:
            if last_y is None:
                last_y = text_obj['y']
            
            # 新しい行の開始を検出
            if not is_same_line(text_obj['y'], last_y):
                if current_left or current_right:
                    paired_content.append({
                        'left': ' '.join(current_left),
                        'right': ' '.join(current_right)
                    })
                current_left = []
                current_right = []
                last_y = text_obj['y']
            
            # 左右の振り分け
            if text_obj['x'] < x_threshold:
                current_left.append(text_obj['text'])
            else:
                current_right.append(text_obj['text'])
    
        # 最後の行を処理
        if current_left or current_right:
            paired_content.append({
                'left': ' '.join(current_left),
                'right': ' '.join(current_right)
            })
    
    return paired_content

# マークダウンフォーマットの改善
def format_as_markdown_advanced(pairs):
    markdown_lines = []
    in_definition_list = False
    
    for pair in pairs:
        left = pair['left'].strip()
        right = pair['right'].strip()
        
        if left and right:
            # 定義リスト形式で出力
            markdown_lines.append(f"### {left}")
            markdown_lines.append(right)
            markdown_lines.append("")
        elif left:
            markdown_lines.append(f"### {left}")
            markdown_lines.append("")
        elif right:
            markdown_lines.append(right)
            markdown_lines.append("")
    
    return '\n'.join(markdown_lines)

# 使用例
pdf_path = 'example.pdf'
content_pairs = extract_paired_content_advanced(pdf_path)
markdown_content = format_as_markdown_advanced(content_pairs)

# 保存
with open('paired_content.md', 'w', encoding='utf-8') as f:
    f.write(markdown_content)