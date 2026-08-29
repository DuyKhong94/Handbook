import streamlit as st





USERS = {

    "tech01": {
        "password": "123456",
        "permissions": [


    
  
            "dashboard",
            "ai",
            "daily_passdown"
        ]
    },

    "user01": {
        "password": "123456",
        "permissions": [
            "ai"
        ]
    },

    "admin": {
        "password": "trungduy94",
        "permissions": [
            "dashboard",
            "add_error",
            "analysis",
            "erp",
            "team_center",
            "reference",
            "spreadsheet",
            "ai",
            "daily_passdown"
        ]
    }
}
def require_login():

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:

        st.title("Login Process Engineering App")

        st.warning(
            "Hold on 😅! Who are you? "
            "- Please contact Mr Duy Khong for access."
        )

        username = st.text_input("User")

        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button("Login"):

            user = USERS.get(username)

            if user and user["password"] == password:

                st.session_state.logged_in = True

                # Lưu username
                st.session_state.username = username

                # Lưu quyền
                st.session_state.permissions = user["permissions"]

                st.rerun()

            else:

                st.error(
                    "Your password is invalid or Your account is expired
                    \n Please contact IT support!"
                )

        st.stop()
