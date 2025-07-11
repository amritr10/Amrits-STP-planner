import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import uuid
import json
import os
import io
import zipfile

# Set page config
st.set_page_config(page_title="Amrit STP Timeline Manager", layout="wide")

# File paths for persistent storage
DATA_FILE = "activities_data.json"
CONFIG_FILE = "categories_config.json"

# Helper functions for category configuration
def load_categories():
    default_categories = {
        "Work": "#FF6B6B",
        "Personal": "#4ECDC4",
        "Project": "#45B7D1",
        "Meeting": "#FFA07A",
        "Travel": "#98D8C8",
        "Other": "#6C5CE7"
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading categories config: {e}")
            return default_categories
    return default_categories

def save_categories(categories):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(categories, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving categories config: {e}")
        return False

def load_activities():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                for act in data:
                    act["start_date"] = datetime.strptime(act["start_date"], "%Y-%m-%d").date()
                    act["end_date"]   = datetime.strptime(act["end_date"], "%Y-%m-%d").date()
                    act["created_at"] = datetime.strptime(act["created_at"], "%Y-%m-%d %H:%M:%S")
                return data
        except Exception as e:
            st.error(f"Error loading activities: {e}")
            return []
    return []

def save_activities(activities):
    try:
        out = []
        for act in activities:
            a = act.copy()
            a["start_date"] = a["start_date"].strftime("%Y-%m-%d")
            a["end_date"]   = a["end_date"].strftime("%Y-%m-%d")
            a["created_at"] = a["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            out.append(a)
        with open(DATA_FILE, "w") as f:
            json.dump(out, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving activities: {e}")
        return False

# Helper to zip both JSONs for export
def generate_export_zip(activities, categories):
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # prepare activities JSON
        act_list = []
        for act in activities:
            a = act.copy()
            a["start_date"] = a["start_date"].strftime("%Y-%m-%d")
            a["end_date"]   = a["end_date"].strftime("%Y-%m-%d")
            a["created_at"] = a["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            act_list.append(a)
        zf.writestr(DATA_FILE, json.dumps(act_list, indent=2))
        zf.writestr(CONFIG_FILE, json.dumps(categories, indent=2))
    mem.seek(0)
    return mem.getvalue()

# Initialize session state
if "activities" not in st.session_state:
    st.session_state.activities = load_activities()
if "categories" not in st.session_state:
    st.session_state.categories = load_categories()

def get_color_for_activity(cat, cats_dict):
    return cats_dict.get(cat, "#6C5CE7")

# Title & Status
st.title("🗓️ Amrit STP Timeline Manager")
st.markdown("Add activities with date ranges and visualize them on an interactive timeline")
c1, c2 = st.columns([3,1])
with c1:
    if os.path.exists(DATA_FILE):
        st.success("✅ Data is automatically saved and will persist across sessions")
    else:
        st.info("ℹ️ No saved data found - start by adding your first activity")
with c2:
    if st.button("🔄 Reload Data"):
        st.session_state.activities = load_activities()
        st.rerun()

# Sidebar: Add activity & manage categories
with st.sidebar:
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
                if nn and nn not in st.session_state.categories:
                    st.session_state.categories[nn] = nc
                    if save_categories(st.session_state.categories):
                        st.success(f"Added '{nn}'")
                    else:
                        st.error("Failed to save")
                    st.rerun()
                elif nn in st.session_state.categories:
                    st.error("Already exists!")
                else:
                    st.error("Enter a name")
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
            if an and sd <= ed:
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
                if save_activities(st.session_state.activities):
                    st.success(f"Added '{an}'")
                else:
                    st.error("Added but failed to save")
                st.rerun()
            else:
                st.error("Enter valid name & dates")

# Main layout
left, right = st.columns([2,1])

with left:
    st.header("📊 Timeline Visualization")
    if st.session_state.activities:
        acts = sorted(st.session_state.activities, key=lambda x:x["start_date"])
        fig = go.Figure()
        for i, a in enumerate(acts):
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
        for a in st.session_state.activities:
            d = a["start_date"]
            while d <= a["end_date"]:
                cal.append({"date":d, "activity":a["name"]})
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
        acts = sorted(st.session_state.activities, key=lambda x:x["start_date"])
        for a in acts:
            exp = st.expander(f"{a['name']} ({a['category']})")
            with exp:
                ek = f"edit_{a['id']}"
                if not st.session_state.get(ek, False):
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
                            st.session_state[ek] = True
                            st.rerun()
                    with b2:
                        if st.button("🗑️ Delete", key=f"d_{a['id']}"):
                            st.session_state.activities = [x for x in st.session_state.activities if x["id"]!=a["id"]]
                            save_activities(st.session_state.activities)
                            st.rerun()
                else:
                    with st.form(f"form_{a['id']}"):
                        name2 = st.text_input("Name", value=a["name"])
                        c1f,c2f = st.columns(2)
                        with c1f:
                            sd2 = st.date_input("Start", a["start_date"])
                        with c2f:
                            ed2 = st.date_input("End", a["end_date"])
                        cat2 = st.selectbox("Category", list(st.session_state.categories.keys()),
                                            index=list(st.session_state.categories).index(a["category"]))
                        pr2  = st.selectbox("Priority", ["High","Medium","Low"],
                                            index=["High","Medium","Low"].index(a["priority"]))
                        desc2 = st.text_area("Desc", value=a["description"])
                        s1,s2 = st.columns(2)
                        with s1:
                            if st.form_submit_button("💾 Save"):
                                if name2 and sd2<=ed2:
                                    for idx,x in enumerate(st.session_state.activities):
                                        if x["id"]==a["id"]:
                                            st.session_state.activities[idx].update({
                                                "name":name2,
                                                "start_date":sd2,
                                                "end_date":ed2,
                                                "category":cat2,
                                                "priority":pr2,
                                                "description":desc2
                                            })
                                            break
                                    save_activities(st.session_state.activities)
                                    st.session_state[ek] = False
                                    st.rerun()
                                else:
                                    st.error("Invalid data")
                        with s2:
                            if st.form_submit_button("❌ Cancel"):
                                st.session_state[ek] = False
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

        st.subheader("💾 Export Data")
        if st.button("📥 Download as CSV"):
            df = pd.DataFrame(st.session_state.activities)
            csv = df.to_csv(index=False)
            st.download_button("Download CSV", data=csv, file_name="activities.csv", mime="text/csv")
    else:
        st.info("No activities to display")

    # ─────── Data Management (always visible) ─────────
    st.subheader("🔧 Data Management")

    # Export both JSONs as a ZIP
    zip_data = generate_export_zip(st.session_state.activities, st.session_state.categories)
    st.download_button(
        "📥 Download JSON (Activities + Categories)",
        data=zip_data,
        file_name="amrit_export.zip",
        mime="application/zip"
    )

    # Import activities from CSV
    up_csv = st.file_uploader("📤 Import activities from CSV", type=["csv"], key="impcsv")
    if up_csv:
        try:
            df_imp = pd.read_csv(up_csv)
            df_imp["start_date"] = pd.to_datetime(df_imp["start_date"]).dt.date
            df_imp["end_date"]   = pd.to_datetime(df_imp["end_date"]).dt.date
            if "created_at" in df_imp.columns:
                df_imp["created_at"] = pd.to_datetime(df_imp["created_at"])
            else:
                df_imp["created_at"] = datetime.now()
            if st.button("Confirm Import CSV", key="imp_csv_btn"):
                if "id" not in df_imp.columns:
                    df_imp["id"] = [str(uuid.uuid4()) for _ in range(len(df_imp))]
                recs = df_imp.to_dict("records")
                st.session_state.activities.extend(recs)
                save_activities(st.session_state.activities)
                st.success(f"Imported {len(recs)} activities from CSV")
                st.rerun()
        except Exception as e:
            st.error(f"Error importing CSV: {e}")

    # Import activities from JSON
    up_act_j = st.file_uploader("📤 Import activities from JSON", type=["json"], key="impjson_act")
    if up_act_j:
        try:
            text = up_act_j.getvalue().decode("utf-8")
            arr  = json.loads(text)
            if not isinstance(arr, list):
                st.error("Activities JSON must be an array")
            else:
                if st.button("Confirm Import Activities JSON", key="imp_json_act_btn"):
                    to_add = []
                    for r in arr:
                        parsed = {
                            "id": r.get("id", str(uuid.uuid4())),
                            "name": r.get("name",""),
                            "start_date": datetime.strptime(r["start_date"],"%Y-%m-%d").date(),
                            "end_date":   datetime.strptime(r["end_date"],  "%Y-%m-%d").date(),
                            "category":   r.get("category",""),
                            "priority":   r.get("priority",""),
                            "description":r.get("description",""),
                            "created_at": datetime.strptime(r.get("created_at"),"%Y-%m-%d %H:%M:%S") if r.get("created_at") else datetime.now()
                        }
                        to_add.append(parsed)
                    st.session_state.activities.extend(to_add)
                    save_activities(st.session_state.activities)
                    st.success(f"Imported {len(to_add)} activities from JSON")
                    st.rerun()
        except Exception as e:
            st.error(f"Error parsing activities JSON: {e}")

    # Import categories from JSON
    up_cat_j = st.file_uploader("📤 Import categories from JSON", type=["json"], key="impjson_cat")
    if up_cat_j:
        try:
            txt = up_cat_j.getvalue().decode("utf-8")
            cd  = json.loads(txt)
            if not isinstance(cd, dict):
                st.error("Categories JSON must be an object")
            else:
                if st.button("Confirm Import Categories JSON", key="imp_json_cat_btn"):
                    st.session_state.categories = cd
                    save_categories(cd)
                    st.success("Imported categories from JSON")
                    st.rerun()
        except Exception as e:
            st.error(f"Error parsing categories JSON: {e}")

    # Clear all activities
    if st.button("🗑️ Clear All Activities", type="secondary", key="clear_all_btn"):
        st.session_state.activities = []
        save_activities(st.session_state.activities)
        st.rerun()

# Footer
st.markdown("---")
st.markdown("*Built by Amrit | Data automatically saves across sessions*")