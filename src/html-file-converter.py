import os
from pathlib import Path
from html_to_markdown import HTMLToMarkdownConverter

def convert_html_file_to_markdown(input_path, output_path=None):
    """
    HTMLファイルを読み込んでMarkdownに変換し、ファイルに保存する

    Parameters:
        input_path (str): 入力HTMLファイルのパス
        output_path (str, optional): 出力Markdownファイルのパス。
            指定しない場合は入力ファイルと同じディレクトリに同名の.mdファイルを作成
    
    Returns:
        str: 作成されたMarkdownファイルのパス
    """
    # パスの処理
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {input_path}")
    
    # 出力パスが指定されていない場合は、入力ファイルと同じディレクトリに.mdファイルを作成
    if output_path is None:
        output_path = input_path.with_suffix('.md')
    else:
        output_path = Path(output_path)
    
    # HTMLファイルの読み込み
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except UnicodeDecodeError:
        # UTF-8で読めない場合はShift-JISで試行
        with open(input_path, 'r', encoding='shift_jis') as f:
            html_content = f.read()
    
    # Markdownに変換
    converter = HTMLToMarkdownConverter()
    markdown_content = converter.convert(html_content)
    
    # 結果を保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    return str(output_path)

def convert_html_directory(input_dir, output_dir=None, recursive=True):
    """
    ディレクトリ内のすべてのHTMLファイルをMarkdownに変換

    Parameters:
        input_dir (str): 入力HTMLファイルのあるディレクトリパス
        output_dir (str, optional): 出力Markdownファイルを保存するディレクトリパス
        recursive (bool): サブディレクトリも処理するかどうか（デフォルトはTrue）
    
    Returns:
        list: 変換されたファイルのパスのリスト
    """
    input_dir = Path(input_dir)
    converted_files = []
    
    if output_dir:
        output_dir = Path(output_dir)
    
    # HTMLファイルを検索
    pattern = '**/*.html' if recursive else '*.html'
    for html_file in input_dir.glob(pattern):
        # 出力パスの生成
        if output_dir:
            rel_path = html_file.relative_to(input_dir)
            output_path = output_dir / rel_path.with_suffix('.md')
        else:
            output_path = None
        
        try:
            # 変換実行
            converted_path = convert_html_file_to_markdown(html_file, output_path)
            converted_files.append(converted_path)
            print(f"変換成功: {html_file} -> {converted_path}")
        except Exception as e:
            print(f"変換失敗: {html_file} - エラー: {str(e)}")
    
    return converted_files

# 使用例
if __name__ == "__main__":
    # 単一ファイルの変換
    html_file = "example.html"
    try:
        output_path = convert_html_file_to_markdown(html_file)
        print(f"変換完了: {output_path}")
    except FileNotFoundError as e:
        print(f"エラー: {e}")
    
    # ディレクトリ内のすべてのHTMLファイルを変換
    input_directory = "html_files"
    output_directory = "markdown_files"
    try:
        converted_files = convert_html_directory(input_directory, output_directory)
        print(f"\n合計 {len(converted_files)} ファイルを変換しました。")
    except Exception as e:
        print(f"エラー: {e}")
