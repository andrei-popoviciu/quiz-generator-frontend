from base import API_URL, QUIZ_GEN_INSTRUCTIONS, COOKIE_NAME
import streamlit as st
import requests
from typing import Optional
import extra_streamlit_components as stx
import time


@st.cache_resource(experimental_allow_widgets=True)
def get_manager():
    return stx.CookieManager()


def update_conversations():
    st.session_state.conversations = get_conversations()


def register_user(username, password):
    response = requests.post(
        f"{API_URL}/register", json={"username": username, "password": password})
    return response.json()


def login_user(username, password):
    response = requests.post(
        f"{API_URL}/login", json={"username": username, "password": password})
    cookie_value = None

    if response.status_code == 200:
        cookie_value = response.headers["Set-Cookie"].split(";")[
            0].split("=")[-1]
    return response.json(), cookie_value


def generate_quiz(prompt: str, pdfs: Optional[list] = None, web_search_enabled: bool = False):
    url = f"{API_URL}/generate"
    data = {"prompt": prompt}
    files = None
    headers = {'Cookie': f"{COOKIE_NAME}={st.session_state[COOKIE_NAME]}"}
    if 'conversation_id' in st.session_state:
        data["conversation_id"] = st.session_state["conversation_id"]

    if web_search_enabled:
        data["web_search_enabled"] = "true"
    if pdfs:
        files = [("pdfs", (pdf.name, pdf, "application/pdf")) for pdf in pdfs]

    response = requests.post(url, files=files, data=data, headers=headers)
    if response.status_code != 200:
        raise Exception(response.text)

    data = response.json()
    st.session_state["conversation_id"] = data["conversation_id"]
    return data["answer"]


def get_conversations():
    response = requests.get(f"{API_URL}/get_conversations", headers={
        'Cookie': f"{COOKIE_NAME}={st.session_state[COOKIE_NAME]}"
    })
    return response.json()


def main():
    if "web_search_enabled" not in st.session_state:
        st.session_state.web_search_enabled = False

    if 'authenticated' not in st.session_state:
        cookie_manager = get_manager()
        session_cookie = cookie_manager.get(COOKIE_NAME)
        time.sleep(2)
        print(cookie_manager.get_all())
        if session_cookie:
            st.session_state.authenticated = True
            st.session_state[COOKIE_NAME] = session_cookie
        else:
            st.session_state.authenticated = False

    if not st.session_state.authenticated:
        option = st.sidebar.selectbox(
            "Choose an option", ["Login", "Register"])
        if option == "Login":
            show_login()
        else:
            show_register()
    else:
        if 'conversations' not in st.session_state:
            update_conversations()
        show_quiz_generation()


def show_login():
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        response, cookie_value = login_user(username, password)
        if "message" in response and response["message"] == "Login successful":
            cookie_manager = get_manager()
            cookie_manager.set(COOKIE_NAME, cookie_value)
            st.session_state[COOKIE_NAME] = cookie_value
            st.session_state.user_id = response["user_id"]
            st.session_state.username = username
            st.session_state.authenticated = True
        else:
            st.error(response.get("error", "Login failed"))


def show_register():
    st.sidebar.title("Register")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    confirm_password = st.sidebar.text_input(
        "Confirm Password", type="password")

    if st.sidebar.button("Register"):
        if password != confirm_password:
            st.error("Passwords do not match")
        else:
            response = register_user(username, password)
            if "message" in response and response["message"] == "User registered successfully":
                st.success("Registered successfully! Please login.")
            else:
                st.error(response.get("error", "Registration failed"))


def show_quiz_generation():
    with st.sidebar:
        new_conv = st.button("###### Start New Conversation")
        if new_conv:
            st.session_state.conversations = get_conversations()
            st.session_state.web_search_enabled = False
            st.session_state.pop("conversation_id", None)
            st.session_state.pop("messages", None)
        st.text("Conversation History")
        with st.container(height=180):
            if st.session_state.get("conversations"):
                titles = []
                for conv in st.session_state.conversations:
                    if isinstance(conv, dict) and 'conversation_id' in conv:
                        title = f'###### {conv["messages"][0]["content"][:70]}'
                        if title in titles:
                            title += "#2"
                        else:
                            titles.append(title)
                        if st.button(title):
                            st.session_state.conversations = get_conversations()
                            st.session_state.conversation_id = conv["conversation_id"]
                            st.session_state.messages = conv['messages']
                            if conv["conversation_type"] == "web":
                                st.session_state.web_search_enabled = True

        pdfs = st.file_uploader("Upload PDFs here", type=[
            "pdf"], accept_multiple_files=True)
        st.markdown("**or**")
        web_search_enabled = st.checkbox(
            "Enable Web Search", value=st.session_state.web_search_enabled)

        if st.button("Logout"):
            st.session_state.clear()
            cookie_manager = get_manager()
            print(cookie_manager.get_all())
            try:
                cookie_manager.delete(COOKIE_NAME)
            except Exception as e:
                print(e)
            st.rerun()

    if "messages" not in st.session_state.keys():
        st.session_state.messages = [
            {"role": "assistant", "content": QUIZ_GEN_INSTRUCTIONS}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            content = message["content"]
            if message["role"] == "assistant" and "ANSWERS:" in content:
                quiz, answers = content.split("ANSWERS:")
                st.write(quiz)
                with st.popover("show answers"):
                    st.text(answers)
            else:
                st.write(content)

    if prompt := st.chat_input("Enter your prompt"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

    if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = generate_quiz(prompt, pdfs, web_search_enabled)
                    message = {"role": "assistant", "content": response}
                    st.session_state.messages.append(message)
                    st.rerun()
                except Exception as exc:
                    print(exc)


if __name__ == "__main__":
    main()
