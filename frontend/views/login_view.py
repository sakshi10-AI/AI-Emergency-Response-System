"""
Login & Registration View - Authentication Gatekeeper

Renders user authentication interface for logging into the EOC Command Center with JWT token issuance,
role selection (Admin, Police, Hospital, Dispatcher, Viewer), and user registration.
"""

import streamlit as st
import asyncio
from frontend.theme import render_command_header, render_metric_card
from frontend.api_clients.auth_client import auth_client
from frontend.state_manager import set_auth_token


def render_login_view():
    """Renders sleek Dark Command Center Login / Register Page."""
    st.markdown("""
    <div style="text-align: center; margin-top: 1rem; margin-bottom: 2rem;">
        <h1 style="color: #f9fafb; font-size: 2.5rem;">🚨 NAGPUR EOC COMMAND CENTER</h1>
        <p style="color: #9ca3af; font-size: 1.1rem;">AI-Powered Multi-Agent Emergency Response System — Nagpur, Maharashtra, India 🇮🇳</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        tab_login, tab_register = st.tabs(["🔐 Sign In", "📝 Register New Account"])

        with tab_login:
            st.markdown("### EOC Officer Authentication")
            username = st.text_input("Email / Username:", value="dispatcher@eoc.gov", key="login_user")
            password = st.text_input("Password:", value="password123", type="password", key="login_pass")
            role_choice = st.selectbox(
                "Select Active Operating Role:",
                ["DISPATCHER", "ADMIN", "POLICE", "HOSPITAL", "VIEWER"],
                index=0,
                key="login_role_select"
            )

            if st.button("🚀 Log In to Command Center", use_container_width=True):
                with st.spinner("Authenticating credentials & requesting JWT token..."):
                    # Demo local credentials (always work even if backend is offline)
                    DEMO_USERS = {
                        "admin": ("admin123", "admin", "EOC Admin"),
                        "dispatcher": ("dispatch123", "dispatcher", "EOC Dispatcher"),
                        "police": ("police123", "police", "Officer"),
                        "hospital_admin": ("hosp123", "hospital", "Hospital Admin"),
                        "guest": ("guest123", "viewer", "Guest Viewer"),
                        "dispatcher@eoc.gov": ("password123", "dispatcher", "EOC Dispatcher"),
                    }

                    res = None
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        res = loop.run_until_complete(auth_client.login(username, password))
                    except Exception as e:
                        # Backend unavailable or DB offline — fall back to demo credentials
                        demo = DEMO_USERS.get(username.lower().strip())
                        if demo and demo[0] == password:
                            res = {
                                "access_token": f"demo-token-{username}",
                                "token_type": "bearer",
                                "user": {
                                    "username": username,
                                    "email": username,
                                    "role": demo[1],
                                    "name": demo[2]
                                }
                            }
                        else:
                            st.error(f"❌ Authentication failed: {str(e)[:120]}")
                            st.info("💡 **Demo Mode**: Try username `admin` / password `admin123` to explore the dashboard offline.")

                if res and ("access_token" in res or "token" in res):
                    token = res.get("access_token", res.get("token", "mock-jwt-token"))
                    user_data = res.get("user", {
                        "username": username,
                        "email": username,
                        "role": role_choice.lower(),
                        "name": f"{role_choice.capitalize()} Officer"
                    })
                    user_data["role"] = user_data.get("role", role_choice.lower())

                    set_auth_token(token, user_data)
                    st.success(f"✅ Authenticated as {user_data.get('role', role_choice).upper()}! Access Granted.")
                    st.rerun()
                elif res:
                    st.error("❌ Invalid credentials. Please check your password.")

        with tab_register:
            st.markdown("### Create New Agency / Officer Profile")
            reg_name = st.text_input("Full Name / Call-Sign:", value="Officer John Doe", key="reg_name")
            reg_email = st.text_input("Official Agency Email:", value="john.doe@eoc.gov", key="reg_email")
            reg_pass = st.text_input("Create Password:", type="password", key="reg_pass")
            reg_role = st.selectbox(
                "Select Assigned Role:",
                ["DISPATCHER", "ADMIN", "POLICE", "HOSPITAL", "VIEWER"],
                index=0,
                key="reg_role_select"
            )

            if st.button("Register Account", use_container_width=True):
                with st.spinner("Registering user profile..."):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    reg_res = loop.run_until_complete(auth_client.register({
                        "email": reg_email,
                        "password": reg_pass,
                        "full_name": reg_name,
                        "role": reg_role.lower()
                    }))

                st.success(f"Account created for {reg_name} ({reg_role})! You can now log in.")
