import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import uuid
import io

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Amrit STP Timeline Manager", layout="wide")

# ────────────── GOOGLE SHEETS AUTH & HELPERS ──────────────

@st.cache_resource
def init_gsheet():
    """
    Authenticate via service‐account JSON stored in st.secrets["gcp_service_account"],
    open by spreadsheet_id in st.secrets["gspread"]["spreadsheet_id"]
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    client = gspread.authorize(creds)
    sh = client.open_by_key(st.secrets["gspread"]["spreadsheet_id"])
    # Ensure the two worksheets exist:
    try:
        acts_ws = sh.worksheet("Activities")
    except gspread.WorksheetNotFound:
        acts_ws = sh.add_worksheet("Activities", rows="1000", cols="20")
        acts_ws.append_row(["id","name","start_date","end_date","category","priority","description","created_at"])
    try:
        cats_ws = sh.worksheet("Categories")
    except gspread.WorksheetNotFound:
        cats_ws = sh.add_worksheet("Categories", rows="100", cols="5")
        cats_ws.append_row(["name","color"])
        # add a default category
        cats_ws.append_row(["Other","#6C5CE7"])
    return sh

sh = init_gsheet()

def load_activities():
    ws = sh.worksheet("Activities")
    records = ws.get_all_records()
    out = []
    for r in records:
        # skip empty rows
        if not r.get("id"):
            continue
        try:
            sd = datetime.strptime(r["start_date"], "%Y-%m-%d").date()
            ed = datetime.strptime(r["end_date"], "%Y-%m-%d").date()
        except:
            # if invalid or blank, skip
            continue
        try:
            ca = datetime.strptime(r.get("created_at",""), "%Y-%m-%d %H:%M:%S")
        except:
            ca = datetime.now()
        out.append({
            "id": r["id"],
            "name": r.get("name",""),
            "start_date": sd,
            "end_date":   ed,
            "category":   r.get("category",""),
            "priority":   r.get("priority",""),
            "description":r.get("description",""),
            "created_at": ca
        })
    return out

def save_activities(activities):
    ws = sh.worksheet("Activities")
    # clear everything
    ws.clear()
    # write header + rows
    header = ["id","name","start_date","end_date","category","priority","description","created_at"]
    rows = [header]
    for a in activities:
        rows.append([
            a["id"],
            a["name"],
            a["start_date"].strftime("%Y-%m-%d"),
            a["end_date"].strftime("%Y-%m-%d"),
            a["category"],
            a["priority"],
            a["description"],
            a["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        ])
    ws.update(rows)

def load_categories():
    ws = sh.worksheet("Categories")
    records = ws.get_all_records()
    out = {}
    for r in records:
        name = r.get("name")
        color = r.get("color")
        if name:
            out[name] = color
    return out

def save_categories(categories):
    ws = sh.worksheet("Categories")
    ws.clear()
    header = ["name","color"]
    rows = [header] + [[n,c] for n,c in categories.items()]
    ws.update(rows)

def get_color_for_activity(cat, cats_dict):
    return cats_dict.get(cat, "#6C5CE7")


# ────────────── SESSION STATE INIT ──────────────

if "activities" not in st.session_state:
    st.session_state.activities = load_activities()
if "categories" not in st.session_state:
    st.session_state.categories = load_categories()
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


# ────────────── HEADER & RELOAD ──────────────

st.title("🗓️ Amrit STP Timeline Manager")
st.markdown("Use this app to manage your timeline. All data is read/written to a Google Sheet.")

c1, c2 = st.columns([3,1])
with c1:
    st.success("✅ Connected to Google Sheet")
with c2:
    if st.button("🔄 Reload Data"):
        st.session_state.activities = load_activities()
        st.session_state.categories = load_categories()
        st.rerun()


# ────────────── SIDEBAR: LOGIN + SECURED CONTENT ──────────────

with st.sidebar:
    if not st.session_state.authenticated:
        pwd = st.text_input("Password", type="password", key="password_input")
        if st.button("Login", key="login_button"):
            if pwd == "Amrit123#":
                st.session_state.authenticated = True
                st.success("🔓 Logged in")
                st.rerun()
            else:
                st.error("❌ Incorrect password")
    else:
        st.header("➕ Add New Activity")

        with st.expander("🎨 Manage Categories"):
            st.subheader("Current Categories")
            for name, color in st.session_state.categories.items():
                col1, col2, col3 = st.columns([2,1,1])
                with col1:
                    st.markdown(f"<span style='color:{color}'>●</span> {name}", unsafe_allow_html=True)
                with col2:
                    newc = st.color_picker("", value=color, key=f"col_{name}")
                    if newc != color:
                        st.session_state.categories[name] = newc
                        save_categories(st.session_state.categories)
                with col3:
                    if st.button("🗑️", key=f"del_{name}"):
                        if len(st.session_state.categories) > 1:
                            del st.session_state.categories[name]
                            save_categories(st.session_state.categories)
                            st.rerun()
                        else:
                            st.error("Must have at least one category!")

            st.subheader("Add New Category")
            with st.form("form_add_cat"):
                nn = st.text_input("Category Name")
                nc = st.color_picker("Category Color", "#FF6B6B")
                if st.form_submit_button("Add Category"):
                    if not nn:
                        st.error("Enter a name")
                    elif nn in st.session_state.categories:
                        st.error("Already exists!")
                    else:
                        st.session_state.categories[nn] = nc
                        save_categories(st.session_state.categories)
                        st.success(f"Added '{nn}'")
                        st.rerun()

        with st.form("form_add_act"):
            an = st.text_input("Activity Name")
            c1a, c2a = st.columns(2)
            with c1a:
                sd = st.date_input("Start Date", datetime.now().date())
            with c2a:
                ed = st.date_input("End Date", datetime.now().date() + timedelta(days=1))
            cat = st.selectbox("Category", list(st.session_state.categories.keys()))
            pr = st.selectbox("Priority", ["High","Medium","Low"])
            desc = st.text_area("Description (opt.)")
            if st.form_submit_button("Add Activity"):
                if not an:
                    st.error("Enter a name")
                elif sd > ed:
                    st.error("Start ≤ End")
                else:
                    new = {
                        "id": str(uuid.uuid4()),
                        "name": an,
                        "start_date": sd,
                        "end_date": ed,
                        "category": cat,
                        "priority": pr,
                        "description": desc,
                        "created_at": datetime.now()
                    }
                    st.session_state.activities.append(new)
                    save_activities(st.session_state.activities)
                    st.success(f"Added '{an}'")
                    st.rerun()


# ────────────── MAIN LAYOUT ──────────────

left, right = st.columns([2,1])

with left:
    st.header("📊 Timeline Visualization")
    if st.session_state.activities:
        acts = sorted(st.session_state.activities, key=lambda x: x["start_date"])
        fig = go.Figure()
        for i,a in enumerate(acts):
            col = get_color_for_activity(a["category"], st.session_state.categories)
            fig.add_trace(go.Scatter(
                x=[a["start_date"], a["end_date"]],
                y=[i,i],
                mode="lines+markers",
                line=dict(color=col, width=20),
                marker=dict(size=8,color=col),
                hovertemplate=(
                    f"<b>{a['name']}</b><br>"
                    f"Category: {a['category']}<br>"
                    f"Priority: {a['priority']}<br>"
                    f"Start: {a['start_date']}<br>"
                    f"End: {a['end_date']}<br>"
                    f"Desc: {a['description']}<extra></extra>"
                ),
                showlegend=False
            ))
        fig.update_layout(
            title="Activity Timeline",
            xaxis_title="Date",
            yaxis=dict(
                tickmode="array",
                tickvals=list(range(len(acts))),
                ticktext=[a["name"] for a in acts],
                autorange="reversed"
            ),
            height=max(400, len(acts)*50),
            hovermode="closest"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📅 Calendar View")
        cal = []
        for a in acts:
            d = a["start_date"]
            while d <= a["end_date"]:
                cal.append({"date": d, "activity": a["name"]})
                d += timedelta(days=1)
        if cal:
            cdf = pd.DataFrame(cal)
            fig2 = px.density_heatmap(cdf, x="date", y="activity", color_continuous_scale="Blues")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("📝 Use the sidebar to add your first activity")

with right:
    st.header("📋 Activity List")
    if st.session_state.activities:
        acts = sorted(st.session_state.activities, key=lambda x: x["start_date"])
        for a in acts:
            exp = st.expander(f"{a['name']} ({a['category']})")
            with exp:
                edit_flag = f"edit_{a['id']}"
                if not st.session_state.get(edit_flag, False):
                    col = get_color_for_activity(a["category"], st.session_state.categories)
                    st.markdown(f"**Category:** <span style='color:{col}'>●</span> {a['category']}", unsafe_allow_html=True)
                    st.write(f"**Start:** {a['start_date']}")
                    st.write(f"**End:** {a['end_date']}")
                    st.write(f"**Priority:** {a['priority']}")
                    if a["description"]:
                        st.write(f"**Desc:** {a['description']}")
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("✏️ Edit", key=f"e_{a['id']}"):
                            st.session_state[edit_flag] = True
                            st.rerun()
                    with b2:
                        if st.button("🗑️ Delete", key=f"d_{a['id']}"):
                            st.session_state.activities = [
                                x for x in st.session_state.activities if x["id"] != a["id"]
                            ]
                            save_activities(st.session_state.activities)
                            st.rerun()
                else:
                    with st.form(f"form_{a['id']}"):
                        name2 = st.text_input("Name", value=a["name"])
                        c1f, c2f = st.columns(2)
                        with c1f:
                            sd2 = st.date_input("Start", a["start_date"])
                        with c2f:
                            ed2 = st.date_input("End", a["end_date"])
                        cat2 = st.selectbox("Category", list(st.session_state.categories.keys()), index=list(st.session_state.categories).index(a["category"]))
                        pr2 = st.selectbox("Priority", ["High","Medium","Low"], index=["High","Medium","Low"].index(a["priority"]))
                        desc2 = st.text_area("Desc", value=a["description"])
                        s1, s2 = st.columns(2)
                        with s1:
                            if st.form_submit_button("💾 Save"):
                                if not name2:
                                    st.error("Enter a name")
                                elif sd2 > ed2:
                                    st.error("Start ≤ End")
                                else:
                                    # update
                                    for idx,x in enumerate(st.session_state.activities):
                                        if x["id"] == a["id"]:
                                            st.session_state.activities[idx].update({
                                                "name": name2,
                                                "start_date": sd2,
                                                "end_date": ed2,
                                                "category": cat2,
                                                "priority": pr2,
                                                "description": desc2
                                            })
                                            break
                                    save_activities(st.session_state.activities)
                                    st.session_state[edit_flag] = False
                                    st.rerun()
                        with s2:
                            if st.form_submit_button("❌ Cancel"):
                                st.session_state[edit_flag] = False
                                st.rerun()

        # Summary & CSV Export
        st.subheader("📈 Summary")
        tot = len(st.session_state.activities)
        st.metric("Total Activities", tot)
        cats = pd.Series([x["category"] for x in st.session_state.activities]).value_counts()
        st.write("**By Category:**")
        for k,v in cats.items():
            st.write(f"• {k}: {v}")
        pris = pd.Series([x["priority"] for x in st.session_state.activities]).value_counts()
        st.write("**By Priority:**")
        for k,v in pris.items():
            st.write(f"• {k}: {v}")

        st.subheader("💾 Export as CSV")
        df = pd.DataFrame(st.session_state.activities)
        csv = df.to_csv(index=False)
        st.download_button("Download Activities CSV", data=csv, file_name="activities.csv", mime="text/csv")

        # ────────────── DATA MANAGEMENT ──────────────
        if st.session_state.authenticated:
            st.subheader("🔧 Data Management")
            # Download entire Google Sheet as Excel
            if st.button("📥 Download Google-Sheet as Excel"):
                # read both sheets
                df_acts = pd.DataFrame(sh.worksheet("Activities").get_all_records())
                df_cats = pd.DataFrame(sh.worksheet("Categories").get_all_records())
                towrite = io.BytesIO()
                with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
                    df_acts.to_excel(writer, sheet_name="Activities", index=False)
                    df_cats.to_excel(writer, sheet_name="Categories", index=False)
                towrite.seek(0)
                st.download_button(
                    label="Click to download .xlsx",
                    data=towrite,
                    file_name="amrit_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            # Upload an Excel file to overwrite both tabs
            up_xlsx = st.file_uploader("📤 Upload .xlsx to overwrite Sheet", type=["xlsx"])
            if up_xlsx:
                try:
                    all_dfs = pd.read_excel(up_xlsx, sheet_name=None)
                except Exception as e:
                    st.error(f"Error reading 📥 Excel: {e}")
                    all_dfs = None
                if all_dfs:
                    if st.button("✅ Confirm Overwrite Google-Sheet from .xlsx"):
                        # categories
                        if "Categories" not in all_dfs or "Activities" not in all_dfs:
                            st.error("Excel must have both 'Activities' and 'Categories' sheets")
                        else:
                            # parse categories
                            dfc = all_dfs["Categories"]
                            cats = {row["name"]: row["color"] for _,row in dfc.iterrows() if pd.notna(row.get("name"))}
                            # parse activities
                            dfa = all_dfs["Activities"]
                            acts = []
                            for _,row in dfa.iterrows():
                                try:
                                    sd = pd.to_datetime(row["start_date"]).date()
                                    ed = pd.to_datetime(row["end_date"]).date()
                                except:
                                    continue
                                ca = None
                                if "created_at" in row and pd.notna(row["created_at"]):
                                    try:
                                        ca = pd.to_datetime(row["created_at"]).to_pydatetime()
                                    except:
                                        ca = datetime.now()
                                else:
                                    ca = datetime.now()
                                act = {
                                    "id": str(row["id"]) if pd.notna(row["id"]) else str(uuid.uuid4()),
                                    "name": row.get("name",""),
                                    "start_date": sd,
                                    "end_date": ed,
                                    "category": row.get("category",""),
                                    "priority": row.get("priority",""),
                                    "description": row.get("description",""),
                                    "created_at": ca
                                }
                                acts.append(act)
                            # overwrite
                            st.session_state.categories = cats
                            st.session_state.activities = acts
                            save_categories(cats)
                            save_activities(acts)
                            st.success("✅ Overwrote Google Sheet from uploaded Excel")
                            st.rerun()
            # Clear all
            if st.button("🗑️ Clear All Activities", type="secondary"):
                save_activities([])
                st.session_state.activities = []
                st.success("All activities cleared")
                st.rerun()
        else:
            st.info("🔒 Please login to access Data Management")

# ────────────── FOOTER ──────────────
st.markdown("---")
st.markdown("*Built by Amrit | Data lives in Google Sheets*")