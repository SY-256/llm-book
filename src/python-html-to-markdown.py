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
        
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        
        if tag == 'h1':
            self.markdown.append('# ')
        elif tag == 'h2':
            self.markdown.append('## ')
        elif tag == 'h3':
            self.markdown.append('### ')
        elif tag == 'h4':
            self.markdown.append('#### ')
        elif tag == 'h5':
            self.markdown.append('##### ')
        elif tag == 'h6':
            self.markdown.append('###### ')
        elif tag == 'p':
            if self.markdown and self.markdown[-1] != '\n':
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
            if 'class' in attrs:
                self.code_block = True
                self.markdown.append(f"\n```{attrs['class']}\n")
            else:
                self.markdown.append('`')
        elif tag == 'pre':
            if not self.code_block:
                self.code_block = True
                self.markdown.append('\n```\n')
        elif tag == 'img' and 'src' in attrs:
            alt = attrs.get('alt', '')
            self.markdown.append(f'![{alt}]({attrs["src"]})')
        elif tag == 'ul':
            self.list_stack.append('*')
        elif tag == 'ol':
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
            self.markdown.append('\n> ')
            
    def handle_endtag(self, tag):
        if tag == 'p':
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
                self.markdown.append('\n')
        elif tag == 'blockquote':
            self.markdown.append('\n\n')
            
    def handle_data(self, data):
        if data.strip():
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

# 使用例
if __name__ == "__main__":
    html_example = """
    <h1>Welcome to My Page</h1>
    <p>This is a <strong>sample</strong> paragraph with some <em>emphasized</em> text.</p>
    <h2>Features</h2>
    <ul>
        <li>Simple to use</li>
        <li>Lightweight</li>
        <li>Fast conversion</li>
    </ul>
    <p>Visit our <a href="https://example.com">website</a> for more information.</p>
    <pre><code class="python">
    def hello_world():
        print("Hello, World!")
    </code></pre>
    """
    
    markdown = convert_html_to_markdown(html_example)
    print(markdown)