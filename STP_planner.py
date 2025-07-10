import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import uuid
import json
import os

# Set page config
st.set_page_config(page_title="Activity Timeline Manager", layout="wide")

# File paths for persistent storage
DATA_FILE = "activities_data.json"
CONFIG_FILE = "categories_config.json"

# Helper functions for category configuration
def load_categories():
    """Load categories and their colors from JSON file"""
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
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError) as e:
            st.error(f"Error loading categories config: {e}")
            return default_categories
    return default_categories

def save_categories(categories):
    """Save categories and their colors to JSON file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(categories, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving categories config: {e}")
        return False
def load_activities():
    """Load activities from JSON file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                # Convert date strings back to date objects
                for activity in data:
                    activity['start_date'] = datetime.strptime(activity['start_date'], '%Y-%m-%d').date()
                    activity['end_date'] = datetime.strptime(activity['end_date'], '%Y-%m-%d').date()
                    activity['created_at'] = datetime.strptime(activity['created_at'], '%Y-%m-%d %H:%M:%S')
                return data
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            st.error(f"Error loading data: {e}")
            return []
    return []

def save_activities(activities):
    """Save activities to JSON file"""
    try:
        # Convert date objects to strings for JSON serialization
        data_to_save = []
        for activity in activities:
            activity_copy = activity.copy()
            activity_copy['start_date'] = activity['start_date'].strftime('%Y-%m-%d')
            activity_copy['end_date'] = activity['end_date'].strftime('%Y-%m-%d')
            activity_copy['created_at'] = activity['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            data_to_save.append(activity_copy)
        
        with open(DATA_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving data: {e}")
        return False

# Initialize session state for storing activities and categories
if 'activities' not in st.session_state:
    st.session_state.activities = load_activities()

if 'categories' not in st.session_state:
    st.session_state.categories = load_categories()

if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = True

# Helper function to get color for activity based on category
def get_color_for_activity(category, categories_dict):
    return categories_dict.get(category, "#6C5CE7")  # Default purple if category not found

# Main title
st.title("🗓️ Activity Timeline Manager")
st.markdown("Add activities with date ranges and visualize them on an interactive timeline")

# Display data persistence status
col_status1, col_status2 = st.columns([3, 1])
with col_status1:
    if os.path.exists(DATA_FILE):
        st.success("✅ Data is automatically saved and will persist across sessions")
    else:
        st.info("ℹ️ No saved data found - start by adding your first activity")

with col_status2:
    if st.button("🔄 Reload Data"):
        st.session_state.activities = load_activities()
        st.rerun()

# Sidebar for adding new activities and managing categories
with st.sidebar:
    st.header("➕ Add New Activity")
    
    # Category management section
    with st.expander("🎨 Manage Categories"):
        st.subheader("Current Categories")
        
        # Display existing categories with color indicators
        for cat_name, cat_color in st.session_state.categories.items():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"<span style='color: {cat_color}'>●</span> {cat_name}", unsafe_allow_html=True)
            with col2:
                new_color = st.color_picker(f"", value=cat_color, key=f"color_{cat_name}")
                if new_color != cat_color:
                    st.session_state.categories[cat_name] = new_color
                    save_categories(st.session_state.categories)
            with col3:
                if st.button("🗑️", key=f"del_cat_{cat_name}"):
                    if len(st.session_state.categories) > 1:  # Keep at least one category
                        del st.session_state.categories[cat_name]
                        save_categories(st.session_state.categories)
                        st.rerun()
                    else:
                        st.error("Must have at least one category!")
        
        # Add new category
        st.subheader("Add New Category")
        with st.form("add_category"):
            new_cat_name = st.text_input("Category Name")
            new_cat_color = st.color_picker("Category Color", value="#FF6B6B")
            
            if st.form_submit_button("Add Category"):
                if new_cat_name and new_cat_name not in st.session_state.categories:
                    st.session_state.categories[new_cat_name] = new_cat_color
                    if save_categories(st.session_state.categories):
                        st.success(f"Added category '{new_cat_name}'!")
                    else:
                        st.error("Failed to save category")
                    st.rerun()
                elif new_cat_name in st.session_state.categories:
                    st.error("Category already exists!")
                else:
                    st.error("Please enter a category name")
    
    with st.form("add_activity"):
        activity_name = st.text_input("Activity Name", placeholder="Enter activity name...")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=datetime.now().date())
        with col2:
            end_date = st.date_input("End Date", value=datetime.now().date() + timedelta(days=1))
        
        activity_category = st.selectbox(
            "Category",
            list(st.session_state.categories.keys())
        )
        
        priority = st.selectbox(
            "Priority",
            ["High", "Medium", "Low"]
        )
        
        description = st.text_area("Description (optional)", placeholder="Add details about the activity...")
        
        submit_button = st.form_submit_button("Add Activity", use_container_width=True)
        
        if submit_button:
            if activity_name and start_date <= end_date:
                new_activity = {
                    'id': str(uuid.uuid4()),
                    'name': activity_name,
                    'start_date': start_date,
                    'end_date': end_date,
                    'category': activity_category,
                    'priority': priority,
                    'description': description,
                    'created_at': datetime.now()
                }
                st.session_state.activities.append(new_activity)
                
                # Save to file
                if save_activities(st.session_state.activities):
                    st.success(f"✅ Added '{activity_name}' and saved to file!")
                else:
                    st.error("❌ Activity added but failed to save to file")
                st.rerun()
            else:
                st.error("❌ Please enter a valid activity name and ensure start date is before end date.")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📊 Timeline Visualization")
    
    if st.session_state.activities:
        # Sort activities by start date (earliest first)
        sorted_activities = sorted(st.session_state.activities, key=lambda x: x['start_date'])
        
        # Create timeline chart
        df = pd.DataFrame(sorted_activities)
        
        # Create Gantt chart using plotly
        fig = go.Figure()
        
        for i, activity in enumerate(sorted_activities):
            color = get_color_for_activity(activity['category'], st.session_state.categories)
            
            # Add horizontal bar for each activity
            fig.add_trace(go.Scatter(
                x=[activity['start_date'], activity['end_date']],
                y=[i, i],
                mode='lines+markers',
                line=dict(color=color, width=20),
                marker=dict(size=8, color=color),
                name=activity['name'],
                hovertemplate=f"<b>{activity['name']}</b><br>" +
                             f"Category: {activity['category']}<br>" +
                             f"Priority: {activity['priority']}<br>" +
                             f"Start: {activity['start_date']}<br>" +
                             f"End: {activity['end_date']}<br>" +
                             f"Description: {activity['description']}<extra></extra>",
                showlegend=False
            ))
        
        # Update layout - reverse y-axis so earliest dates appear at top
        fig.update_layout(
            title="Activity Timeline (Sorted by Start Date)",
            xaxis_title="Date",
            yaxis_title="Activities",
            yaxis=dict(
                tickmode='array',
                tickvals=list(range(len(sorted_activities))),
                ticktext=[act['name'] for act in sorted_activities],
                autorange='reversed'  # This reverses the y-axis
            ),
            height=max(400, len(sorted_activities) * 50),
            hovermode='closest'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Additional timeline view (calendar style)
        st.subheader("📅 Calendar View")
        
        # Create a calendar-style visualization
        calendar_data = []
        for activity in st.session_state.activities:
            current_date = activity['start_date']
            while current_date <= activity['end_date']:
                calendar_data.append({
                    'date': current_date,
                    'activity': activity['name'],
                    'category': activity['category'],
                    'priority': activity['priority']
                })
                current_date += timedelta(days=1)
        
        if calendar_data:
            cal_df = pd.DataFrame(calendar_data)
            
            # Create heatmap-style calendar
            fig_cal = px.density_heatmap(
                cal_df, 
                x='date', 
                y='activity',
                title="Activity Calendar Heatmap",
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_cal, use_container_width=True)
    
    else:
        st.info("📝 No activities added yet. Use the sidebar to add your first activity!")

with col2:
    st.header("📋 Activity List")
    
    if st.session_state.activities:
        # Sort activities by start date (earliest first) for display
        sorted_activities = sorted(st.session_state.activities, key=lambda x: x['start_date'])
        
        # Display current activities (sorted by start date)
        for i, activity in enumerate(sorted_activities):
            with st.expander(f"{activity['name']} ({activity['category']})"):
                # Check if this activity is being edited
                edit_key = f"edit_{activity['id']}"
                is_editing = st.session_state.get(edit_key, False)
                
                if not is_editing:
                    # Display mode with category color indicator
                    category_color = get_color_for_activity(activity['category'], st.session_state.categories)
                    st.markdown(f"**Category:** <span style='color: {category_color}'>●</span> {activity['category']}", unsafe_allow_html=True)
                    st.write(f"**Start:** {activity['start_date']}")
                    st.write(f"**End:** {activity['end_date']}")
                    st.write(f"**Priority:** {activity['priority']}")
                    if activity['description']:
                        st.write(f"**Description:** {activity['description']}")
                    
                    # Edit and Delete buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"✏️ Edit", key=f"edit_btn_{activity['id']}"):
                            st.session_state[edit_key] = True
                            st.rerun()
                    with col2:
                        if st.button(f"🗑️ Delete", key=f"delete_{activity['id']}"):
                            st.session_state.activities = [
                                act for act in st.session_state.activities 
                                if act['id'] != activity['id']
                            ]
                            # Save after deletion
                            if save_activities(st.session_state.activities):
                                st.success("Activity deleted and saved!")
                            else:
                                st.error("Activity deleted but failed to save")
                            st.rerun()
                
                else:
                    # Edit mode
                    st.subheader("✏️ Edit Activity")
                    
                    with st.form(f"edit_form_{activity['id']}"):
                        edit_name = st.text_input("Activity Name", value=activity['name'])
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_start = st.date_input("Start Date", value=activity['start_date'])
                        with col2:
                            edit_end = st.date_input("End Date", value=activity['end_date'])
                        
                        edit_category = st.selectbox(
                            "Category",
                            list(st.session_state.categories.keys()),
                            index=list(st.session_state.categories.keys()).index(activity['category']) if activity['category'] in st.session_state.categories else 0
                        )
                        
                        edit_priority = st.selectbox(
                            "Priority",
                            ["High", "Medium", "Low"],
                            index=["High", "Medium", "Low"].index(activity['priority'])
                        )
                        
                        edit_description = st.text_area("Description", value=activity.get('description', ''))
                        
                        # Form buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            save_changes = st.form_submit_button("💾 Save Changes", use_container_width=True)
                        with col2:
                            cancel_edit = st.form_submit_button("❌ Cancel", use_container_width=True)
                        
                        if save_changes:
                            if edit_name and edit_start <= edit_end:
                                # Update the activity
                                for j, act in enumerate(st.session_state.activities):
                                    if act['id'] == activity['id']:
                                        st.session_state.activities[j].update({
                                            'name': edit_name,
                                            'start_date': edit_start,
                                            'end_date': edit_end,
                                            'category': edit_category,
                                            'priority': edit_priority,
                                            'description': edit_description
                                        })
                                        break
                                
                                # Save to file
                                if save_activities(st.session_state.activities):
                                    st.success("✅ Activity updated and saved!")
                                else:
                                    st.error("❌ Activity updated but failed to save")
                                
                                # Exit edit mode
                                st.session_state[edit_key] = False
                                st.rerun()
                            else:
                                st.error("❌ Please enter a valid activity name and ensure start date is before end date.")
                        
                        if cancel_edit:
                            st.session_state[edit_key] = False
                            st.rerun()
        
        # Summary statistics
        st.subheader("📈 Summary")
        total_activities = len(st.session_state.activities)
        categories = [act['category'] for act in st.session_state.activities]
        priorities = [act['priority'] for act in st.session_state.activities]
        
        st.metric("Total Activities", total_activities)
        
        if categories:
            category_counts = pd.Series(categories).value_counts()
            st.write("**By Category:**")
            for cat, count in category_counts.items():
                st.write(f"• {cat}: {count}")
        
        if priorities:
            priority_counts = pd.Series(priorities).value_counts()
            st.write("**By Priority:**")
            for pri, count in priority_counts.items():
                st.write(f"• {pri}: {count}")
        
        # Export functionality
        st.subheader("💾 Export Data")
        if st.button("📥 Download as CSV"):
            df = pd.DataFrame(st.session_state.activities)
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="activities_timeline.csv",
                mime="text/csv"
            )
        
        # Data management
        st.subheader("🔧 Data Management")
        
        # Import from CSV
        uploaded_file = st.file_uploader("📤 Import activities from CSV", type=['csv'])
        if uploaded_file is not None:
            try:
                import_df = pd.read_csv(uploaded_file)
                # Convert date columns
                import_df['start_date'] = pd.to_datetime(import_df['start_date']).dt.date
                import_df['end_date'] = pd.to_datetime(import_df['end_date']).dt.date
                import_df['created_at'] = pd.to_datetime(import_df.get('created_at', datetime.now()))
                
                # Add IDs if not present
                if 'id' not in import_df.columns:
                    import_df['id'] = [str(uuid.uuid4()) for _ in range(len(import_df))]
                
                # Convert to list of dictionaries
                imported_activities = import_df.to_dict('records')
                
                if st.button("Confirm Import"):
                    st.session_state.activities.extend(imported_activities)
                    if save_activities(st.session_state.activities):
                        st.success(f"Successfully imported {len(imported_activities)} activities!")
                    else:
                        st.error("Import successful but failed to save")
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error importing CSV: {e}")
        
        # Clear all activities
        if st.button("🗑️ Clear All Activities", type="secondary"):
            st.session_state.activities = []
            save_activities(st.session_state.activities)
            st.rerun()
    
    else:
        st.info("No activities to display")

# Footer
st.markdown("---")
st.markdown("*Built with Streamlit and Plotly | Data automatically saves across sessions*")