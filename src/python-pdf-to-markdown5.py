from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LAParams
from collections import defaultdict
import re


def detect_table_structure(text_blocks):
    """表構造を検出する"""
    # 表のヘッダーらしき行を検出
    headers = ["期間", "保証料", "手数料", "お手続内容", "お手続方法"]
    return any(
        header in " ".join([block["text"] for block in text_blocks])
        for header in headers
    )


def format_table_row(cells):
    """表の行をマークダウン形式にフォーマット"""
    return "| " + " | ".join(cells) + " |"


def extract_markdown_content(pdf_path):
    laparams = LAParams(detect_vertical=False, all_texts=True)

    content_dict = defaultdict(list)
    current_key = None
    table_data = []
    in_table = False

    for page_layout in extract_pages(pdf_path, laparams=laparams):
        page_texts = []

        for element in page_layout:
            if isinstance(element, LTTextContainer):
                x0, y0 = element.bbox[0], element.bbox[1]
                text = element.get_text().strip()

                if text and not text.isspace():
                    page_texts.append({"text": text, "x": x0, "y": y0})

        # Y座標でソート
        page_texts.sort(key=lambda x: -x["y"])

        for text_block in page_texts:
            text = text_block["text"]
            x0 = text_block["x"]

            # 表の検出
            if "期間" in text or "10年" in text or "20年" in text:
                in_table = True
                table_data.append(text)
                continue

            if in_table and ("円" in text or text.isdigit()):
                table_data.append(text)
                continue

            if (
                in_table
                and len(table_data) > 0
                and not any(char in text for char in ["円", "年"])
            ):
                # 表の終了を検出
                if table_data:
                    # 表データの整形
                    table_markdown = format_table_markdown(table_data)
                    if current_key:
                        content_dict[current_key].append(table_markdown)
                    table_data = []
                in_table = False

            # 通常のテキスト処理
            if not in_table:
                if "商品概要説明書" in text:
                    content_dict["title"].append(text)
                elif "現在" in text and "年" in text and "月" in text:
                    content_dict["date"].append(text)
                elif text.startswith(tuple(str(i) + "." for i in range(1, 15))):
                    current_key = text
                    content_dict[current_key] = []
                elif current_key:
                    content_dict[current_key].append(text)

    # マークダウンの生成
    markdown_lines = []

    if "title" in content_dict:
        markdown_lines.extend(["# " + title.strip() for title in content_dict["title"]])
    if "date" in content_dict:
        markdown_lines.extend(["\n" + date.strip() for date in content_dict["date"]])

    for key, contents in content_dict.items():
        if key not in ["title", "date"]:
            markdown_lines.append(f"\n## {key}")
            for content in contents:
                if content.startswith("|"):  # 表の場合
                    markdown_lines.append(content)
                elif content.strip().startswith("・"):
                    for line in content.split("・"):
                        if line.strip():
                            markdown_lines.append(f"- {line.strip()}")
                else:
                    markdown_lines.append(content.strip())

    return "\n".join(markdown_lines)


def format_table_markdown(table_data):
    """表データをマークダウン形式に変換"""
    # データを行と列に整理
    rows = []
    current_row = []
    headers = []

    # ヘッダーの検出と設定
    if "期間" in " ".join(table_data):
        headers = ["期間", "保証料"]
    elif "お手続内容" in " ".join(table_data):
        headers = ["お手続方法", "お手続内容", "手数料"]

    if headers:
        # ヘッダー行の作成
        header_row = format_table_row(headers)
        separator_row = format_table_row(["-" * len(header) for header in headers])
        rows.append(header_row)
        rows.append(separator_row)

        # データ行の作成
        for i in range(0, len(table_data), len(headers)):
            if i + len(headers) <= len(table_data):
                row_data = table_data[i : i + len(headers)]
                rows.append(format_table_row(row_data))

    return "\n".join(rows) if rows else ""


# 使用例
def convert_pdf_to_markdown(pdf_path, output_path):
    try:
        markdown_content = extract_markdown_content(pdf_path)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return True, "変換が成功しました"
    except Exception as e:
        return False, f"エラーが発生しました: {str(e)}"


# 実行
pdf_path = "example.pdf"
output_path = "output.md"
success, message = convert_pdf_to_markdown(pdf_path, output_path)
print(message)
