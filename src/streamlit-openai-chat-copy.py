import os
import streamlit as st
from openai import OpenAI
import streamlit.components.v1 as components

# APIキーの設定
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

def create_copy_button(text, button_id):
    """コピーボタン付きのHTMLを生成する関数"""
    html = f"""
    <div style="display: flex; align-items: start; margin: 0;">
        <div style="flex-grow: 1;">{text}</div>
        <button
            id="{button_id}"
            onclick="copyText('{text.replace("'", "\\'").replace('"', '\\"').replace('\\n', ' ')}')"
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
            "
        >
            📋 Copy
        </button>
    </div>

    <script>
    function copyText(text) {{
        navigator.clipboard.writeText(text).then(
            function() {{
                const button = document.getElementById('{button_id}');
                const originalText = button.innerHTML;
                button.innerHTML = '✅ Copied!';
                button.style.backgroundColor = '#90EE90';
                
                setTimeout(function() {{
                    button.innerHTML = originalText;
                    button.style.backgroundColor = '#f0f2f6';
                }}, 2000);
            }}
        ).catch(
            function() {{
                const button = document.getElementById('{button_id}');
                button.innerHTML = '❌ Failed';
                button.style.backgroundColor = '#ffcccb';
                
                setTimeout(function() {{
                    button.innerHTML = '📋 Copy';
                    button.style.backgroundColor = '#f0f2f6';
                }}, 2000);
            }}
        );
    }}
    </script>
    """
    return html

st.title("StreamlitのChatGPTサンプル")

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

# チャットログを保存したセッション情報を初期化
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []

user_msg = st.chat_input("ここにメッセージを入力")

if user_msg:
    # 以前のチャットログを表示
    for i, chat in enumerate(st.session_state.chat_log):
        with st.chat_message(chat["name"]):
            if chat["name"] == ASSISTANT_NAME:
                # アシスタントの返答にはコピーボタンを追加
                components.html(
                    create_copy_button(chat["msg"], f"copy_button_log_{i}"),
                    height=len(chat["msg"].split('\n')) * 25 + 40  # メッセージの行数に応じて高さを調整
                )
            else:
                st.write(chat["msg"])

    # 最新のユーザーメッセージを表示
    with st.chat_message(USER_NAME):
        st.write(user_msg)

    # アシスタントのメッセージを表示
    response = response_chatgpt(user_msg)
    with st.chat_message(ASSISTANT_NAME):
        assistant_msg = ""
        assistant_response_area = st.empty()
        
        for chunk in response:
            if chunk.choices[0].finish_reason is not None:
                break
            # 回答を逐次表示
            assistant_msg += chunk.choices[0].delta.content
            # 最新の完全なメッセージに対してコピーボタンを表示
            assistant_response_area.components.html(
                create_copy_button(assistant_msg, "copy_button_current"),
                height=len(assistant_msg.split('\n')) * 25 + 40  # メッセージの行数に応じて高さを調整
            )

    # セッションにチャットログを追加
    st.session_state.chat_log.append({"name": USER_NAME, "msg": user_msg})
    st.session_state.chat_log.append({"name": ASSISTANT_NAME, "msg": assistant_msg})
