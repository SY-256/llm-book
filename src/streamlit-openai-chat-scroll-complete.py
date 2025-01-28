import os
import streamlit as st
from openai import OpenAI
import streamlit.components.v1 as components
import json

# APIキーの設定
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# カスタムCSSを追加
st.markdown("""
    <style>
    /* ページ全体のパディングを削除 */
    .main > div {
        padding-top: 0.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    /* ヘッダー部分のスタイル */
    .header-container {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background-color: white;
        padding: 1rem 1rem 0.5rem 1rem;
        z-index: 1000;
        border-bottom: 1px solid #ddd;
    }

    /* チャットコンテナのスタイル */
    .chat-container {
        margin-top: 8rem;  /* ヘッダーの高さ分マージンを設定 */
        margin-bottom: 5rem;  /* 入力欄の高さ分マージンを設定 */
        overflow-y: auto;
        height: calc(100vh - 13rem);  /* ヘッダーと入力欄の高さを考慮 */
    }

    /* 入力欄のスタイル */
    .input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: white;
        padding: 1rem;
        z-index: 1000;
        border-top: 1px solid #ddd;
    }

    /* クリアボタンのスタイル */
    .stButton button {
        background-color: #ff4b4b;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        font-size: 0.9em;
        font-weight: 500;
        border-radius: 0.3rem;
        margin: 0;
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
    }
    .stButton button:hover {
        background-color: #ff3333;
        color: white;
    }

    /* Streamlitデフォルトのパディングを調整 */
    .stChatInput {
        padding-bottom: 0;
    }
    </style>
""", unsafe_allow_html=True)

def calculate_height(text):
    """メッセージの表示に必要な高さを計算する関数"""
    # 1行あたりの文字数（目安）
    chars_per_line = 50
    # テキストの文字数
    total_chars = len(text)
    # 改行の数
    newlines = text.count('\n')
    # 推定される行数（文字数による行数 + 改行数）
    estimated_lines = (total_chars / chars_per_line) + newlines
    # 1行あたりの高さ（ピクセル）+ マージン
    line_height = 30
    # 最小の高さを確保
    min_height = 100
    # 計算された高さ
    calculated_height = max(min_height, (estimated_lines * line_height) + 50)
    return int(calculated_height)

def create_copy_button(text, button_id):
    """コピーボタン付きのHTMLを生成する関数"""
    # テキストの処理
    text_for_display = text.replace('"', '&quot;').replace('\n', '<br>')
    text_for_copy = json.dumps(text)

    html = f"""
    <div style="display: flex; align-items: start; margin: 0; font-family: 'Source Sans Pro', sans-serif;">
        <div style="flex-grow: 1; white-space: pre-wrap; word-wrap: break-word; line-height: 1.5;">
            {text_for_display}
        </div>
        <button
            onclick='copyToClipboard({text_for_copy}, "{button_id}")'
            id="{button_id}"
            style="
                background-color: #f0f2f6;
                border: none;
                padding: 5px 10px;
                border-radius: 4px;
                cursor: pointer;
                display: flex;
                align-items: center;
                font-size: 0.8em;
                margin-left: 10px;
                min-width: 70px;
                justify-content: center;
                height: fit-content;
                position: sticky;
                top: 0;
            "
        >
            📋 Copy
        </button>
    </div>

    <script>
    async function copyToClipboard(text, buttonId) {{
        try {{
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);

            const button = document.getElementById(buttonId);
            const originalText = button.innerHTML;
            button.innerHTML = '✅ Copied!';
            button.style.backgroundColor = '#90EE90';
            
            setTimeout(function() {{
                button.innerHTML = originalText;
                button.style.backgroundColor = '#f0f2f6';
            }}, 2000);
        }} catch (err) {{
            const button = document.getElementById(buttonId);
            button.innerHTML = '❌ Failed';
            button.style.backgroundColor = '#ffcccb';
            
            setTimeout(function() {{
                button.innerHTML = '📋 Copy';
                button.style.backgroundColor = '#f0f2f6';
            }}, 2000);
            console.error('Failed to copy:', err);
        }}
    }}
    </script>
    """
    return html

# 定数定義
USER_NAME = "user"
ASSISTANT_NAME = "assistant"

def response_chatgpt(
    user_msg: str,
):
    """ChatGPTのレスポンスを取得"""
    response = client.chat.completions.create(
        messages=[
            {"role": "user", "content": user_msg},
        ],
        model="gpt-3.5-turbo",
        stream=True,
    )
    return response

def main():
    # ヘッダー部分
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("StreamlitのChatGPTサンプル")
    with col2:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_log = []
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # チャットログを保存したセッション情報を初期化
    if "chat_log" not in st.session_state:
        st.session_state.chat_log = []

    # チャット表示部分
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    # 以前のチャットログを表示
    for i, chat in enumerate(st.session_state.chat_log):
        with st.chat_message(chat["name"]):
            if chat["name"] == ASSISTANT_NAME:
                components.html(
                    create_copy_button(chat["msg"], f"copy_button_log_{i}"),
                    height=calculate_height(chat["msg"])
                )
            else:
                st.write(chat["msg"])
    st.markdown('</div>', unsafe_allow_html=True)

    # 入力部分
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    user_msg = st.chat_input("ここにメッセージを入力")
    st.markdown('</div>', unsafe_allow_html=True)

    if user_msg:
        # 最新のユーザーメッセージを表示
        with st.chat_message(USER_NAME):
            st.write(user_msg)

        # アシスタントのメッセージを表示
        response = response_chatgpt(user_msg)
        with st.chat_message(ASSISTANT_NAME):
            assistant_msg = ""
            message_placeholder = st.empty()
            
            for chunk in response:
                if chunk.choices[0].finish_reason is not None:
                    break
                assistant_msg += chunk.choices[0].delta.content
                message_placeholder.empty()
                with message_placeholder:
                    components.html(
                        create_copy_button(assistant_msg, "copy_button_current"),
                        height=calculate_height(assistant_msg)
                    )

        # セッションにチャットログを追加
        st.session_state.chat_log.append({"name": USER_NAME, "msg": user_msg})
        st.session_state.chat_log.append({"name": ASSISTANT_NAME, "msg": assistant_msg})
        
        # 追加後に最新のメッセージまでスクロール
        st.markdown(
            """
            <script>
                var chatContainer = document.querySelector('.chat-container');
                chatContainer.scrollTop = chatContainer.scrollHeight;
            </script>
            """,
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()
