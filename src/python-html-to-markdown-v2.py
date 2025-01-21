import re
from html.parser import HTMLParser
from html import unescape

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
        self.in_function = False    # 関数内かどうかを追跡
        self.in_script = False      # scriptタグ内かどうかを追跡
        self.in_excluded_tag = False # data-select-bank属性を持つタグ内かどうかを追跡
        
        # テーブル関連の状態
        self.in_table = False
        self.in_header = False
        self.current_row = []
        self.table_data = []
        self.column_count = 0
        
    def handle_starttag(self, tag, attrs):
        # 属性をdict形式に変換
        attrs = dict(attrs)
        
        # data-select-bank="埼玉りそな銀行"の属性を持つタグをチェック
        if 'data-select-bank' in attrs and attrs['data-select-bank'] == "埼玉りそな銀行":
            self.in_excluded_tag = True
            return

        # 除外されたタグ、関数内、scriptタグ内の場合は処理をスキップ
        if self.in_excluded_tag or self.in_function or self.in_script:
            return
            
        # scriptタグの開始
        if tag == 'script':
            self.in_script = True
            return

        # テーブル処理
        if tag == 'table':
            self.in_table = True
            self.table_data = []
            return
        elif tag == 'tr' and self.in_table:
            self.current_row = []
            return
        elif tag == 'th' and self.in_table:
            self.in_header = True
            return
        elif tag == 'td' and self.in_table:
            self.in_header = False
            return
            
        if self.in_table:
            return
            
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
            if not self.list_stack:
                return
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
        # 除外されたタグの終了をチェック
        if self.in_excluded_tag:
            self.in_excluded_tag = False
            return

        # scriptタグの終了
        if tag == 'script':
            self.in_script = False
            return

        # テーブル処理
        if tag == 'table':
            if self.table_data:
                self.markdown.append('\n\n')
                # 列数を取得（最大の行の長さを使用）
                max_cols = max(len(row) for row in self.table_data)
                
                # ヘッダー行の処理
                header = self.table_data[0] if self.table_data else []
                header += [''] * (max_cols - len(header))  # 足りない列を空文字で補完
                self.markdown.append('| ' + ' | '.join(header) + ' |\n')
                
                # 区切り行の追加
                self.markdown.append('| ' + ' | '.join(['---'] * max_cols) + ' |\n')
                
                # データ行の処理
                for row in self.table_data[1:]:
                    row += [''] * (max_cols - len(row))  # 足りない列を空文字で補完
                    self.markdown.append('| ' + ' | '.join(row) + ' |\n')
                
                self.markdown.append('\n')
                self.in_table = False
                self.table_data = []
            return
        elif tag == 'tr' and self.in_table:
            if self.current_row:
                self.table_data.append(self.current_row)
                self.current_row = []
            return
        elif (tag == 'th' or tag == 'td') and self.in_table:
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
            if self.list_stack:
                self.list_stack.pop()
                if not self.list_stack:
                    self.markdown.append('\n\n')
        elif tag == 'blockquote':
            self.markdown.append('\n\n')
            
    def handle_data(self, data):
        if self.in_excluded_tag or self.in_function or self.in_script:
            return

        if self.in_table and (self.in_header or not self.in_header) and data.strip():
            self.current_row.append(data.strip())
            return
            
        if data.strip():
            # 'def'で始まる行か関数定義っぽい行をスキップ
            if not (data.strip().startswith('def ') or 
                   re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*:', data.strip())):
                self.markdown.append(data.strip())
            
    def convert(self, html):
        # 状態をリセット
        self.markdown = []
        self.list_stack = []
        self.list_item_count = 0
        self.code_block = False
        self.emphasis = False
        self.strong = False
        self.in_function = False
        self.in_script = False
        self.in_excluded_tag = False
        self.in_table = False
        self.in_header = False
        self.current_row = []
        self.table_data = []
        
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