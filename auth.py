import streamlit as st

def require_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in=False
    
    if not st.session_state.logged_in:
        st.title("Login Process Engineering App")
        st.warning("Who are you? - Please contact Mr Duy Khong for access.")

        username=st.text_input("User")
        password=st.text_input("Password", type="password") 
        if st.button("Login"):
            if username=="peacbp" and password=="peacbpdeptrai":
                st.session_state.logged_in=True
                st.rerun()
            else:
                st.error("Invalid username or password")

        st.stop()

