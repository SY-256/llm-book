from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LAParams
from collections import defaultdict


def analyze_pdf_structure(pdf_path):
    """PDFの構造を解析し、適切なマークダウン変換方法を決定する"""
    laparams = LAParams(detect_vertical=False, all_texts=True)

    # ページ内のテキスト位置を分析
    left_positions = []
    right_positions = []

    for page_layout in extract_pages(pdf_path, laparams=laparams):
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                x0 = element.bbox[0]
                text = element.get_text().strip()
                if text and not text.isspace():
                    if x0 < 200:  # 左側の位置を収集
                        left_positions.append(x0)
                    else:  # 右側の位置を収集
                        right_positions.append(x0)

    # 最も頻出するX座標を基準として使用
    left_threshold = (
        max(set(left_positions), key=left_positions.count) if left_positions else 100
    )
    right_threshold = (
        max(set(right_positions), key=right_positions.count) if right_positions else 300
    )

    return left_threshold, right_threshold


def extract_markdown_content(pdf_path):
    """PDFをマークダウンに変換する"""
    # PDFの構造を解析
    left_threshold, right_threshold = analyze_pdf_structure(pdf_path)

    laparams = LAParams(detect_vertical=False, all_texts=True)

    # テキストを格納する辞書
    content_dict = defaultdict(list)
    current_key = None

    for page_layout in extract_pages(pdf_path, laparams=laparams):
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                x0 = element.bbox[0]
                text = element.get_text().strip()

                if not text or text.isspace():
                    continue

                # タイトルや日付の検出
                if "商品概要説明書" in text:
                    content_dict["title"].append(text)
                elif "現在" in text and "年" in text and "月" in text:
                    content_dict["date"].append(text)
                # 項目（左側）の検出
                elif x0 < left_threshold:
                    if text.startswith(tuple(str(i) + "." for i in range(1, 15))):
                        current_key = text
                        content_dict[current_key] = []
                # 内容（右側）の検出
                elif x0 > right_threshold and current_key:
                    content_dict[current_key].append(text)

    # マークダウンの生成
    markdown_lines = []

    # タイトルと日付
    if "title" in content_dict:
        markdown_lines.extend(["# " + title.strip() for title in content_dict["title"]])
    if "date" in content_dict:
        markdown_lines.extend(["\n" + date.strip() for date in content_dict["date"]])

    # 内容の整形
    for key, contents in content_dict.items():
        if key not in ["title", "date"]:
            markdown_lines.append(f"\n## {key}")
            for content in contents:
                # 箇条書きの処理
                if content.strip().startswith("・"):
                    for line in content.split("・"):
                        if line.strip():
                            markdown_lines.append(f"- {line.strip()}")
                # 番号付きリストの処理
                elif content.strip().startswith(
                    tuple(str(i) + "." for i in range(1, 10))
                ):
                    markdown_lines.append(content.strip())
                # その他の通常テキスト
                else:
                    markdown_lines.append(content.strip())

    return "\n".join(markdown_lines)


# 使用例
def convert_pdf_to_markdown(pdf_path, output_path):
    """PDFファイルをマークダウンに変換して保存"""
    try:
        markdown_content = extract_markdown_content(pdf_path)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return True, "変換が成功しました"
    except Exception as e:
        return False, f"エラーが発生しました: {str(e)}"


# 実行例
pdf_path = "example.pdf"
output_path = "output.md"
success, message = convert_pdf_to_markdown(pdf_path, output_path)
print(message)
