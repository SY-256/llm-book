class HTMLToMarkdownConverter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.markdown = []
        self.list_stack = []
        self.list_item_count = 0
        self.code_block = False
        self.emphasis = False
        self.strong = False
        self.in_function = False  # 関数内かどうかを追跡
        self.in_script = False    # scriptタグ内かどうかを追跡
        
    def handle_starttag(self, tag, attrs):
        # 関数内またはscriptタグ内の場合は処理をスキップ
        if self.in_function or self.in_script:
            return
            
        # scriptタグの開始
        if tag == 'script':
            self.in_script = True
            return
            
        attrs = dict(attrs)
        
        if tag == 'h1':
            if self.markdown and self.markdown[-1] != '\n\n':
                self.markdown.append('\n\n')
            self.markdown.append('# ')
        elif tag == 'h2':
            if self.markdown and self.markdown[-1] != '\n\n':
                self.markdown.append('\n\n')
            self.markdown.append('## ')
        elif tag == 'h3':
            if self.markdown and self.markdown[-1] != '\n\n':
                self.markdown.append('\n\n')
            self.markdown.append('### ')
        elif tag == 'h4':
            if self.markdown and self.markdown[-1] != '\n\n':
                self.markdown.append('\n\n')
            self.markdown.append('#### ')
        elif tag == 'h5':
            if self.markdown and self.markdown[-1] != '\n\n':
                self.markdown.append('\n\n')
            self.markdown.append('##### ')
        elif tag == 'h6':
            if self.markdown and self.markdown[-1] != '\n\n':
                self.markdown.append('\n\n')
            self.markdown.append('###### ')
        elif tag == 'p':
            if self.markdown and self.markdown[-1] != '\n\n':
                self.markdown.append('\n\n')
        elif tag == 'br':
            self.markdown.append('\n')
        elif tag == 'strong' or tag == 'b':
            self.strong = True
            self.markdown.append('**')
        elif tag == 'em' or tag == 'i':
            self.emphasis = True
            self.markdown.append('*')
        elif tag == 'code':
            content = ''.join(attrs.get('class', '')).lower()
            if 'function' in content or 'def' in content:
                self.in_function = True
            else:
                if 'class' in attrs:
                    self.code_block = True
                    self.markdown.append(f"\n```{attrs['class']}\n")
                else:
                    self.markdown.append('`')
        elif tag == 'pre':
            if not self.code_block and not self.in_function:
                self.code_block = True
                self.markdown.append('\n```\n')
        elif tag == 'ul':
            if self.markdown and self.markdown[-1] != '\n\n':
                self.markdown.append('\n\n')
            self.list_stack.append('*')
        elif tag == 'ol':
            if self.markdown and self.markdown[-1] != '\n\n':
                self.markdown.append('\n\n')
            self.list_stack.append('1')
            self.list_item_count = 0
        elif tag == 'li':
            indent = '  ' * (len(self.list_stack) - 1)
            if self.list_stack[-1] == '*':
                self.markdown.append(f'\n{indent}* ')
            else:
                self.list_item_count += 1
                self.markdown.append(f'\n{indent}{self.list_item_count}. ')
        elif tag == 'blockquote':
            if self.markdown and self.markdown[-1] != '\n\n':
                self.markdown.append('\n\n')
            self.markdown.append('> ')
            
    def handle_endtag(self, tag):
        # scriptタグの終了
        if tag == 'script':
            self.in_script = False
            return
            
        if tag == 'code' and self.in_function:
            self.in_function = False
            return
            
        if self.in_function or self.in_script:
            return
            
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.markdown.append('\n\n')
        elif tag == 'p':
            self.markdown.append('\n\n')
        elif tag == 'strong' or tag == 'b':
            self.strong = False
            self.markdown.append('**')
        elif tag == 'em' or tag == 'i':
            self.emphasis = False
            self.markdown.append('*')
        elif tag == 'code':
            if self.code_block:
                self.code_block = False
                self.markdown.append('\n```\n\n')
            else:
                self.markdown.append('`')
        elif tag == 'pre':
            if self.code_block:
                self.code_block = False
                self.markdown.append('\n```\n\n')
        elif tag in ['ul', 'ol']:
            self.list_stack.pop()
            if not self.list_stack:
                self.markdown.append('\n\n')
        elif tag == 'blockquote':
            self.markdown.append('\n\n')
            
    def handle_data(self, data):
        if self.in_function or self.in_script:
            return
            
        if data.strip():
            # 'def'で始まる行か関数定義っぽい行をスキップ
            if not (data.strip().startswith('def ') or 
                   re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*:', data.strip())):
                self.markdown.append(data.strip())
            
    def convert(self, html):
        self.feed(html)
        markdown = ''.join(self.markdown)
        # 複数の空行を1つにまとめる
        markdown = re.sub(r'\n\s*\n', '\n\n', markdown)
        # 前後の余分な改行を削除
        markdown = markdown.strip()
        return markdown

def convert_html_to_markdown(html):
    """
    HTMLをMarkdownに変換する関数
    
    Parameters:
        html (str): 変換するHTML文字列
    
    Returns:
        str: 変換されたMarkdown文字列
    """
    converter = HTMLToMarkdownConverter()
    return converter.convert(html)