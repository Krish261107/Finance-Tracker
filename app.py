"""FinSight — AI Personal Finance Dashboard (Streamlit)."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date

import db
import style
import data_io
import ml_models
from sample_data import generate_sample_transactions

st.set_page_config(page_title="FinSight — AI Finance Dashboard", page_icon="💠", layout="wide")
style.inject_css(st)
db.init_db()

# ---------------- Session bootstrap ----------------
for key, default in [("user", None), ("confirm_delete", False), ("edit_tx_id", None)]:
    if key not in st.session_state:
        st.session_state[key] = default


# ==================================================================
# AUTH
# ==================================================================
def auth_screen():
    st.markdown('<div class="app-title">💠 FinSight</div>', unsafe_allow_html=True)
    st.caption("AI-powered personal finance dashboard — track, predict, and understand your money.")
    tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])

    with tab_login:
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In", use_container_width=True)
        if submitted:
            user = db.verify_user(u, p)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tab_signup:
        with st.form("signup_form"):
            u2 = st.text_input("Choose a username")
            p2 = st.text_input("Choose a password (min 6 chars)", type="password")
            submitted2 = st.form_submit_button("Create Account", use_container_width=True)
        if submitted2:
            ok, msg = db.create_user(u2, p2)
            if ok:
                st.success(msg + " Please log in.")
            else:
                st.error(msg)


# ==================================================================
# SIDEBAR
# ==================================================================
def sidebar_nav():
    with st.sidebar:
        st.markdown(f'<div class="app-title" style="font-size:1.4rem;">💠 FinSight</div>', unsafe_allow_html=True)
        st.markdown(f"Logged in as **{st.session_state.user['username']}**")
        page = st.radio(
            "Navigate",
            ["📊 Dashboard", "💳 Transactions", "📥 Import Data", "🤖 ML Insights", "📄 Reports", "⚙️ Account"],
            label_visibility="collapsed",
        )
        st.divider()
        if st.button("Log Out", use_container_width=True):
            st.session_state.user = None
            st.rerun()
        return page

def _load_sample(user_id):
    sample = generate_sample_transactions()
    db.bulk_add_transactions(user_id, sample.to_dict("records"))

# ==================================================================
# DASHBOARD
# ==================================================================
def page_dashboard(user_id):
    df = db.get_transactions_df(user_id)
    st.markdown('<div class="app-title">📊 Dashboard</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("No transactions yet. Load sample data or add your own from the Transactions page.")
        if st.button("✨ Load sample data"):
            _load_sample(user_id)
            st.rerun()
        return

    # ---------------- Layout Toggles ----------------
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        show_yearly = st.toggle("📅 Show Yearly Track", value=False)
    with t_col2:
        show_total = st.toggle("🌟 Show Total Track", value=False)

    st.markdown("<br>", unsafe_allow_html=True)

    # Resolve tracking views based on toggle rules
    show_monthly = not show_yearly and not show_total

    # ==================================================================
    # 1. DEFAULT MONTHLY VIEW
    # ==================================================================
    if show_monthly:
        st.subheader("📆 Current Month Tracking")
        current_month = pd.Timestamp.now().to_period("M")
        month_df = df[df["date"].dt.to_period("M") == current_month]
        
        income = month_df.loc[month_df.type == "income", "amount"].sum()
        expense = month_df.loc[month_df.type == "expense", "amount"].sum()
        net = income - expense
        savings_rate = (net / income * 100) if income > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(style.metric_card_html("Monthly Income", f"₹{income:,.0f}", True), unsafe_allow_html=True)
        c2.markdown(style.metric_card_html("Monthly Expense", f"₹{expense:,.0f}", False), unsafe_allow_html=True)
        c3.markdown(style.metric_card_html("Monthly Net Savings", f"₹{net:,.0f}", net >= 0), unsafe_allow_html=True)
        c4.markdown(style.metric_card_html("Monthly Savings Rate", f"{savings_rate:,.1f}%", savings_rate >= 0), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Pull only expense transactions for this month and sort them by value
        month_expenses = month_df[month_df.type == "expense"].copy()
        exp_by_cat = month_expenses.groupby("category")["amount"].sum().reset_index().sort_values(by="amount", ascending=False)

        if not exp_by_cat.empty:
            col1, col2 = st.columns(2)

            with col1:
                # Category-wise expense bar chart styled in a custom blue theme
                fig = px.bar(
                    exp_by_cat, 
                    x="category", 
                    y="amount",
                    title="Current Month Expenses by Category",
                    labels={"category": "Transaction Category", "amount": "Amount (₹)"}
                )
                # Enforce consistent dark-blue color theme on all expense bars
                fig.update_traces(marker_color="#4DA6FF") 
                st.plotly_chart(style.apply_plotly_theme(fig), use_container_width=True)

            with col2:
                # Categorical distributions share pie chart
                fig2 = px.pie(
                    exp_by_cat, 
                    names="category", 
                    values="amount", 
                    hole=0.55, 
                    title="Expense Percentage Distribution"
                )
                fig2.update_traces(textinfo="percent+label")
                st.plotly_chart(style.apply_plotly_theme(fig2), use_container_width=True)
        else:
            st.info("No expense data recorded yet for the current month loop.")

    # ==================================================================
    # 2. YEARLY TRACK VIEW
    # ==================================================================
    if show_yearly:
        st.divider()
        
        # Get active years from history
        available_years = sorted(df["date"].dt.year.unique(), reverse=True)
        current_year = datetime.now().year
        if current_year not in available_years:
            available_years.insert(0, current_year)
            
        selected_year = st.selectbox("Select Year to Track", available_years, index=0)
        
        year_df = df[df["date"].dt.year == selected_year]
        y_income = year_df.loc[year_df.type == "income", "amount"].sum()
        y_expense = year_df.loc[year_df.type == "expense", "amount"].sum()
        y_net = y_income - y_expense
        y_savings_rate = (y_net / y_income * 100) if y_income > 0 else 0

        st.subheader(f"📅 Yearly Report Summary — {selected_year}")
        yc1, yc2, yc3, yc4 = st.columns(4)
        yc1.markdown(style.metric_card_html("Yearly Income", f"₹{y_income:,.0f}", True), unsafe_allow_html=True)
        yc2.markdown(style.metric_card_html("Yearly Expense", f"₹{y_expense:,.0f}", False), unsafe_allow_html=True)
        yc3.markdown(style.metric_card_html("Yearly Net Savings", f"₹{y_net:,.0f}", y_net >= 0), unsafe_allow_html=True)
        yc4.markdown(style.metric_card_html("Yearly Savings Rate", f"{y_savings_rate:,.1f}%", y_savings_rate >= 0), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        y_col1, y_col2 = st.columns([2, 1])
        
        with y_col1:
            if not year_df.empty:
                year_df["month_label"] = year_df["date"].dt.strftime("%b")
                y_agg = year_df.groupby(["month_label", "type"])["amount"].sum().reset_index()
                # Order chronological months
                months_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                fig_y = px.bar(y_agg, x="month_label", y="amount", color="type", barmode="group",
                               category_orders={"month_label": months_order},
                               title=f"Monthly Trajectory in {selected_year}", color_discrete_map={"income": style.ACCENT, "expense": style.DANGER})
                st.plotly_chart(style.apply_plotly_theme(fig_y), use_container_width=True)
        
        with y_col2:
            if not year_df.empty:
                y_exp_by_cat = year_df[year_df.type == "expense"].groupby("category")["amount"].sum().reset_index()
                fig_y_pie = px.pie(y_exp_by_cat, names="category", values="amount", hole=0.55, title=f"Expense Breakdown ({selected_year})")
                fig_y_pie.update_traces(textinfo="percent+label")
                st.plotly_chart(style.apply_plotly_theme(fig_y_pie), use_container_width=True)

    # ==================================================================
    # 3. TOTAL/LIFETIME TRACK VIEW
    # ==================================================================
    if show_total:
        st.divider()
        st.subheader("🌟 Lifetime Total Analytics")
        
        t_income = df.loc[df.type == "income", "amount"].sum()
        t_expense = df.loc[df.type == "expense", "amount"].sum()
        t_net = t_income - t_expense
        t_savings_rate = (t_net / t_income * 100) if t_income > 0 else 0

        tc1, tc2, tc3, tc4 = st.columns(4)
        tc1.markdown(style.metric_card_html("Total Income (All-Time)", f"₹{t_income:,.0f}", True), unsafe_allow_html=True)
        tc2.markdown(style.metric_card_html("Total Expense (All-Time)", f"₹{t_expense:,.0f}", False), unsafe_allow_html=True)
        tc3.markdown(style.metric_card_html("Total Net Balance", f"₹{t_net:,.0f}", t_net >= 0), unsafe_allow_html=True)
        tc4.markdown(style.metric_card_html("Lifetime Savings Rate", f"{t_savings_rate:,.1f}%", t_savings_rate >= 0), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Cumulative Trajectory
        daily_cum = df.sort_values("date").groupby("date")["amount"].sum().reset_index()
        daily_cum["balance_change"] = df.apply(lambda r: r["amount"] if r["type"] == "income" else -r["amount"], axis=1)
        df_sorted = df.sort_values("date").copy()
        df_sorted["net_amount"] = np.where(df_sorted["type"] == "income", df_sorted["amount"], -df_sorted["amount"])
        df_sorted["cumulative_wealth"] = df_sorted["net_amount"].cumsum()
        
        fig_t = go.Figure(go.Scatter(x=df_sorted["date"], y=df_sorted["cumulative_wealth"], mode="lines", fill="tozeroy",
                                      line=dict(color=style.ACCENT2, width=2.5)))
        fig_t.update_layout(title="All-Time Cumulative Asset Net Growth Line")
        st.plotly_chart(style.apply_plotly_theme(fig_t), use_container_width=True)

# ==================================================================
# TRANSACTIONS (CRUD)
# ==================================================================
def page_transactions(user_id):
    st.markdown('<div class="app-title">💳 Transactions</div>', unsafe_allow_html=True)
    db.ensure_default_categories(user_id)

    with st.expander("➕ Add a transaction", expanded=False):
        with st.form("add_tx", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            d = c1.date_input("Date", value=date.today())
            ttype = c2.selectbox("Type", ["expense", "income"])
            amount = c3.number_input("Amount", min_value=0.0, step=10.0)
            cats = db.get_categories(user_id, ttype)
            cat_names = [c["name"] for c in cats] or ["Other"]
            category = st.selectbox("Category", cat_names)
            desc = st.text_input("Description")
            if st.form_submit_button("Add Transaction"):
                db.add_transaction(user_id, d.isoformat(), amount, ttype, category, desc)
                st.success("Transaction added.")
                st.rerun()

    with st.expander("🏷️ Manage categories"):
        cc1, cc2, cc3 = st.columns([2, 1, 1])
        new_cat = cc1.text_input("New category name")
        new_type = cc2.selectbox("Type", ["expense", "income"], key="newcat_type")
        if cc3.button("Add Category"):
            if db.add_category(user_id, new_cat.strip(), new_type):
                st.success("Category added.")
                st.rerun()
            else:
                st.warning("Category already exists.")
        for cat in db.get_categories(user_id):
            r1, r2 = st.columns([4, 1])
            r1.write(f"{cat['name']}  ·  _{cat['type']}_")
            if r2.button("🗑️", key=f"delcat_{cat['id']}"):
                db.delete_category(user_id, cat["id"])
                st.rerun()

    st.markdown("---")
    df = db.get_transactions_df(user_id)
    if df.empty:
        st.info("No transactions yet.")
        return

    fc1, fc2, fc3 = st.columns(3)
    type_filter = fc1.multiselect("Filter by type", ["income", "expense"], default=["income", "expense"])
    cat_filter = fc2.multiselect("Filter by category", sorted(df["category"].unique()))
    search = fc3.text_input("Search description")

    view = df[df["type"].isin(type_filter)]
    if cat_filter:
        view = view[view["category"].isin(cat_filter)]
    if search:
        view = view[view["description"].str.contains(search, case=False, na=False)]

    st.caption(f"Showing {len(view)} of {len(df)} transactions — edit or delete inline below.")
    for _, row in view.iterrows():
        with st.container():
            e1, e2, e3, e4, e5, e6 = st.columns([1.3, 0.9, 1.3, 1.3, 2, 0.8])
            e1.write(row["date"].strftime("%Y-%m-%d"))
            e2.write("🟢" if row["type"] == "income" else "🔴")
            e3.write(row["category"])
            e4.write(f"₹{row['amount']:,.2f}")
            e5.write(row["description"] or "—")
            b1, b2 = e6.columns(2)
            if b1.button("✏️", key=f"edit_{row['id']}"):
                st.session_state.edit_tx_id = int(row["id"])
            if b2.button("🗑️", key=f"del_{row['id']}"):
                db.delete_transaction(int(row["id"]), user_id)
                st.rerun()

    if st.session_state.edit_tx_id:
        tx = df[df["id"] == st.session_state.edit_tx_id].iloc[0]
        st.markdown("#### Edit transaction")
        with st.form("edit_tx_form"):
            c1, c2, c3 = st.columns(3)
            d2 = c1.date_input("Date", value=tx["date"].date())
            t2 = c2.selectbox("Type", ["expense", "income"], index=0 if tx["type"] == "expense" else 1)
            a2 = c3.number_input("Amount", value=float(tx["amount"]), min_value=0.0)
            cat_opts = [c["name"] for c in db.get_categories(user_id, t2)] or [tx["category"]]
            cat2 = st.selectbox("Category", cat_opts, index=cat_opts.index(tx["category"]) if tx["category"] in cat_opts else 0)
            desc2 = st.text_input("Description", value=tx["description"] or "")
            s1, s2 = st.columns(2)
            if s1.form_submit_button("Save changes"):
                db.update_transaction(int(tx["id"]), user_id, d2.isoformat(), a2, t2, cat2, desc2)
                st.session_state.edit_tx_id = None
                st.rerun()
            if s2.form_submit_button("Cancel"):
                st.session_state.edit_tx_id = None
                st.rerun()


# ==================================================================
# IMPORT DATA
# ==================================================================
def page_import(user_id):
    st.markdown('<div class="app-title">📥 Import Data</div>', unsafe_allow_html=True)
    st.write("Upload a CSV or Excel file in **any** layout — bank statement, expense app export, or custom sheet. "
             "Columns are auto-detected (date / amount / debit / credit / description / category).")

    file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
    if file:
        parsed, msg = data_io.smart_import(file)
        if parsed is None:
            st.error(msg)
        else:
            st.success(msg)
            st.dataframe(parsed.head(20), use_container_width=True)

            use_ml = st.checkbox("🤖 Auto-fill missing categories using ML", value=True)
            if st.button("Confirm import", type="primary"):
                rows = parsed.to_dict("records")
                if use_ml:
                    history = db.get_transactions_df(user_id)
                    model = ml_models.train_category_classifier(history)
                    for r in rows:
                        if r["category"] in ("Other", "", None):
                            r["category"] = ml_models.predict_category(model, r["description"])
                db.bulk_add_transactions(user_id, rows)
                st.success(f"Imported {len(rows)} transactions!")
                st.balloons()

    st.markdown("---")
    st.caption("Need data to try the app? Load a realistic synthetic history.")
    if st.button("✨ Load sample data"):
        _load_sample(user_id)
        st.success("Sample data loaded.")


# ==================================================================
# ML INSIGHTS
# ==================================================================
def page_ml(user_id):
    st.markdown('<div class="app-title">🤖 ML Insights</div>', unsafe_allow_html=True)
    df = db.get_transactions_df(user_id)
    if df.empty:
        st.info("Add or import some transactions first.")
        return

    tab1, tab2, tab3 = st.tabs(["🔮 Spend Forecast", "🏷️ Smart Categorizer", "🚨 Anomaly Detection"])

    with tab1:
        st.subheader("Forecast next months' expenses")
        result, err = ml_models.forecast_expenses(df, months_ahead=3)
        if err:
            st.warning(err)
        else:
            hist, fc = result["history"], result["forecast"]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist["month"], y=hist["actual_expense"], mode="lines+markers",
                                       name="Actual", line=dict(color=style.ACCENT, width=3)))
            fig.add_trace(go.Scatter(x=fc["month"], y=fc["predicted_expense"], mode="lines+markers",
                                       name="Forecast", line=dict(color=style.ACCENT2, width=3, dash="dash")))
            fig.update_layout(title="Expense Forecast (RandomForest)")
            st.plotly_chart(style.apply_plotly_theme(fig), use_container_width=True)
            st.dataframe(fc, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Predict a category from a transaction description")
        model = ml_models.train_category_classifier(df)
        text = st.text_input("Try a description", placeholder="e.g. Starbucks coffee downtown")
        if text:
            cat, conf = ml_models.predict_category_confidence(model, text)
            st.markdown(f"**Predicted category:** `{cat}`  ·  confidence **{conf*100:.1f}%**")
        st.caption("The model blends your own transaction history with a general-purpose seed vocabulary, "
                   "so it improves the more you use FinSight.")

    with tab3:
        st.subheader("Unusual transactions (IsolationForest)")
        flagged = ml_models.detect_anomalies(df)
        anomalies = flagged[flagged["is_anomaly"]].sort_values("amount", ascending=False)
        if anomalies.empty:
            st.success("No anomalies detected in your spending history.")
        else:
            st.markdown(f'<span class="anomaly-badge">{len(anomalies)} flagged</span>', unsafe_allow_html=True)
            fig = px.scatter(flagged, x="date", y="amount", color="is_anomaly",
                              color_discrete_map={True: style.DANGER, False: style.ACCENT},
                              hover_data=["category", "description"], title="Transactions (red = anomaly)")
            st.plotly_chart(style.apply_plotly_theme(fig), use_container_width=True)
            st.dataframe(anomalies[["date", "category", "amount", "description"]], use_container_width=True, hide_index=True)


# ==================================================================
# REPORTS
# ==================================================================
def page_reports(user_id):
    st.markdown('<div class="app-title">📄 Reports</div>', unsafe_allow_html=True)
    df = db.get_transactions_df(user_id)
    if df.empty:
        st.info("No data to report on yet.")
        return

    st.write("Export your data or generate a shareable PDF summary.")
    c1, c2 = st.columns(2)
    with c1:
        csv_bytes = data_io.to_csv_bytes(df.drop(columns=["created_at"], errors="ignore"))
        st.download_button("⬇️ Download CSV", csv_bytes, file_name="finsight_transactions.csv", mime="text/csv",
                            use_container_width=True)
    with c2:
        if st.button("📄 Generate PDF report", use_container_width=True):
            pdf_bytes = data_io.generate_pdf_report(df, st.session_state.user["username"])
            st.download_button("⬇️ Download PDF Report", pdf_bytes, file_name="finsight_report.pdf",
                                mime="application/pdf", use_container_width=True)

    st.markdown("---")
    st.subheader("Quick summary")
    st.dataframe(
        df.groupby(["type", "category"])["amount"].agg(["sum", "count", "mean"]).round(2),
        use_container_width=True,
    )


# ==================================================================
# ACCOUNT
# ==================================================================
def page_account(user_id):
    st.markdown('<div class="app-title">⚙️ Account</div>', unsafe_allow_html=True)
    user = st.session_state.user
    st.write(f"**Username:** {user['username']}")
    st.write(f"**Member since:** {user['created_at'][:10]}")

    df = db.get_transactions_df(user_id)
    st.write(f"**Total transactions stored:** {len(df)}")

    st.markdown("---")
    st.subheader("Danger zone")
    if st.button("🗑️ Clear all my transactions (keep account)"):
        db.clear_all_transactions(user_id)
        st.success("All transactions cleared.")
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.error("Deleting your account permanently removes your login and **all** transaction/category data. This cannot be undone.")
    confirm_text = st.text_input("Type DELETE to confirm account deletion")
    if st.button("🗑️ Permanently delete my account and all data", type="primary"):
        if confirm_text.strip() == "DELETE":
            db.delete_user_and_data(user_id)
            st.session_state.user = None
            st.success("Account and all associated data deleted.")
            st.rerun()
        else:
            st.warning("Type DELETE exactly (case-sensitive) to confirm.")


# ==================================================================
# ROUTER
# ==================================================================
if st.session_state.user is None:
    auth_screen()
else:
    uid = st.session_state.user["id"]
    page = sidebar_nav()
    if page == "📊 Dashboard":
        page_dashboard(uid)
    elif page == "💳 Transactions":
        page_transactions(uid)
    elif page == "📥 Import Data":
        page_import(uid)
    elif page == "🤖 ML Insights":
        page_ml(uid)
    elif page == "📄 Reports":
        page_reports(uid)
    elif page == "⚙️ Account":
        page_account(uid)
