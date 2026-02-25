import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Page configuration
st.set_page_config(
    page_title="2025 Financial Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E75B6;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2E75B6;
    }
    .insight-box {
        background-color: #E7F3FF;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_google_sheet_data():
    """Load data from Google Sheets using credentials from Streamlit secrets"""
    try:
        # Set up credentials from Streamlit secrets
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
        
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )
        
        client = gspread.authorize(credentials)
        
        # Open the spreadsheet by key (from secrets)
        spreadsheet = client.open_by_key(st.secrets["spreadsheet_key"])
        
        # Load each sheet
        trip_finance = pd.DataFrame(spreadsheet.worksheet("Trip Finance").get_all_records())
        eating_out = pd.DataFrame(spreadsheet.worksheet("Eating out").get_all_records())
        grocery = pd.DataFrame(spreadsheet.worksheet("Grocery Analysis").get_all_records())
        
        # Convert date columns
        trip_finance['Date'] = pd.to_datetime(trip_finance['Date'], errors='coerce')
        eating_out['Date'] = pd.to_datetime(eating_out['Date'], errors='coerce')
        grocery['Date'] = pd.to_datetime(grocery['Date'], errors='coerce')
        
        return trip_finance, eating_out, grocery
    
    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {str(e)}")
        st.info("Please ensure your Google Sheets API credentials are properly configured in Streamlit secrets.")
        return None, None, None

@st.cache_data
def load_local_data():
    """Fallback: Load data from uploaded files"""
    try:
        trip_finance = pd.read_excel("Join_Finance.xlsx", sheet_name="Trip Finance")
        eating_out = pd.read_excel("Join_Finance.xlsx", sheet_name="Eating out")
        grocery = pd.read_excel("Join_Finance.xlsx", sheet_name="Grocery Analysis")
        
        trip_finance['Date'] = pd.to_datetime(trip_finance['Date'], errors='coerce')
        eating_out['Date'] = pd.to_datetime(eating_out['Date'], errors='coerce')
        grocery['Date'] = pd.to_datetime(grocery['Date'], errors='coerce')
        
        return trip_finance, eating_out, grocery
    except:
        return None, None, None

def calculate_summary_stats(year, trip_finance, eating_out, grocery):
    """Calculate summary statistics for a given year"""
    # Filter by year
    trip_year = trip_finance[trip_finance['Date'].dt.year == year]
    eating_year = eating_out[eating_out['Date'].dt.year == year]
    grocery_year = grocery[grocery['Date'].dt.year == year]
    
    # Calculate totals
    trip_total = trip_year['Corrected Amount'].sum() if 'Corrected Amount' in trip_year.columns else 0
    eating_total = eating_year['Final Total'].sum() if 'Final Total' in eating_year.columns else 0
    grocery_total = grocery_year['Amount'].sum() if 'Amount' in grocery_year.columns else 0
    
    return {
        'trip_total': trip_total,
        'eating_total': eating_total,
        'grocery_total': grocery_total,
        'total_expenses': trip_total + eating_total + grocery_total,
        'trip_count': len(trip_year),
        'eating_count': len(eating_year),
        'grocery_count': len(grocery_year)
    }

def main():
    # Header
    st.markdown('<h1 class="main-header">💰 2025 Financial Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("📊 Navigation")
    page = st.sidebar.radio("Go to", [
        "Overview",
        "Trip Finance",
        "Eating Out",
        "Grocery Analysis",
        "Year Comparison",
        "Housing Analysis"
    ])
    
    # Data source selection
    st.sidebar.markdown("---")
    data_source = st.sidebar.radio("Data Source", ["Google Sheets", "Upload File"])
    
    # Load data based on source
    if data_source == "Google Sheets":
        trip_finance, eating_out, grocery = load_google_sheet_data()
    else:
        uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=['xlsx'])
        if uploaded_file:
            trip_finance = pd.read_excel(uploaded_file, sheet_name="Trip Finance")
            eating_out = pd.read_excel(uploaded_file, sheet_name="Eating out")
            grocery = pd.read_excel(uploaded_file, sheet_name="Grocery Analysis")
            
            trip_finance['Date'] = pd.to_datetime(trip_finance['Date'], errors='coerce')
            eating_out['Date'] = pd.to_datetime(eating_out['Date'], errors='coerce')
            grocery['Date'] = pd.to_datetime(grocery['Date'], errors='coerce')
        else:
            st.warning("Please upload your Excel file to view the dashboard.")
            return
    
    if trip_finance is None or eating_out is None or grocery is None:
        st.error("Failed to load data. Please check your configuration.")
        return
    
    # Year selector
    st.sidebar.markdown("---")
    available_years = sorted(trip_finance['Date'].dt.year.dropna().unique(), reverse=True)
    selected_year = st.sidebar.selectbox("Select Year", available_years, index=0)
    
    # Calculate stats for selected year
    stats = calculate_summary_stats(selected_year, trip_finance, eating_out, grocery)
    
    # Page routing
    if page == "Overview":
        show_overview(selected_year, stats, trip_finance, eating_out, grocery)
    elif page == "Trip Finance":
        show_trip_finance(selected_year, trip_finance)
    elif page == "Eating Out":
        show_eating_out(selected_year, eating_out)
    elif page == "Grocery Analysis":
        show_grocery_analysis(selected_year, grocery)
    elif page == "Year Comparison":
        show_year_comparison(trip_finance, eating_out, grocery)
    elif page == "Housing Analysis":
        show_housing_analysis(selected_year)

def show_overview(year, stats, trip_finance, eating_out, grocery):
    """Overview page with key metrics"""
    st.header(f"📊 Financial Overview - {year}")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Expenses", f"${stats['total_expenses']:,.2f}")
    with col2:
        st.metric("Trip Finance", f"${stats['trip_total']:,.2f}")
    with col3:
        st.metric("Eating Out", f"${stats['eating_total']:,.2f}")
    with col4:
        st.metric("Grocery", f"${stats['grocery_total']:,.2f}")
    
    # Expense breakdown pie chart
    st.subheader("Expense Distribution")
    
    expense_data = pd.DataFrame({
        'Category': ['Trip Finance', 'Eating Out', 'Grocery'],
        'Amount': [stats['trip_total'], stats['eating_total'], stats['grocery_total']]
    })
    
    fig = px.pie(expense_data, values='Amount', names='Category',
                 title=f'{year} Expense Breakdown',
                 color_discrete_sequence=['#2E75B6', '#51CF66', '#FF6B6B'])
    st.plotly_chart(fig, use_container_width=True)
    
    # Monthly trends
    st.subheader("Monthly Spending Trends")
    
    trip_year = trip_finance[trip_finance['Date'].dt.year == year].copy()
    eating_year = eating_out[eating_out['Date'].dt.year == year].copy()
    grocery_year = grocery[grocery['Date'].dt.year == year].copy()
    
    if len(trip_year) > 0:
        trip_year['Month'] = trip_year['Date'].dt.month
        eating_year['Month'] = eating_year['Date'].dt.month
        grocery_year['Month'] = grocery_year['Date'].dt.month
        
        monthly_trip = trip_year.groupby('Month')['Corrected Amount'].sum()
        monthly_eating = eating_year.groupby('Month')['Final Total'].sum()
        monthly_grocery = grocery_year.groupby('Month')['Amount'].sum()
        
        months = range(1, 13)
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=month_names, y=[monthly_trip.get(m, 0) for m in months],
                            name='Trip Finance', marker_color='#2E75B6'))
        fig.add_trace(go.Bar(x=month_names, y=[monthly_eating.get(m, 0) for m in months],
                            name='Eating Out', marker_color='#51CF66'))
        fig.add_trace(go.Bar(x=month_names, y=[monthly_grocery.get(m, 0) for m in months],
                            name='Grocery', marker_color='#FF6B6B'))
        
        fig.update_layout(barmode='stack', title=f'{year} Monthly Spending',
                         xaxis_title='Month', yaxis_title='Amount ($)')
        st.plotly_chart(fig, use_container_width=True)
    
    # Key insights
    st.markdown('<div class="insight-box">', unsafe_allow_html=True)
    st.subheader("💡 Key Insights")
    st.write(f"- Total tracked expenses: **${stats['total_expenses']:,.2f}**")
    st.write(f"- Number of trips taken: **{stats['trip_count']}**")
    st.write(f"- Dining occasions: **{stats['eating_count']}** (avg ${stats['eating_total']/stats['eating_count']:.2f} per meal)" 
             if stats['eating_count'] > 0 else "")
    st.write(f"- Grocery shopping trips: **{stats['grocery_count']}** (avg ${stats['grocery_total']/stats['grocery_count']:.2f} per trip)"
             if stats['grocery_count'] > 0 else "")
    st.markdown('</div>', unsafe_allow_html=True)

def show_trip_finance(year, trip_finance):
    """Trip finance analysis page"""
    st.header(f"✈️ Trip Finance - {year}")
    
    trip_year = trip_finance[trip_finance['Date'].dt.year == year]
    
    if len(trip_year) == 0:
        st.warning(f"No trip data available for {year}")
        return
    
    # Filter out South East Asia Adventure if needed
    trip_year_filtered = trip_year[trip_year['Trip'] != 'South East Asia Adventure']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Trip Spending", f"${trip_year_filtered['Corrected Amount'].sum():,.2f}")
    with col2:
        st.metric("Number of Trips", f"{trip_year_filtered['Trip'].nunique()}")
    
    # Top trips
    st.subheader("Top Trips by Spending")
    top_trips = trip_year_filtered.groupby('Trip')['Corrected Amount'].sum().sort_values(ascending=False).head(10)
    
    fig = px.bar(x=top_trips.values, y=top_trips.index, orientation='h',
                 labels={'x': 'Amount ($)', 'y': 'Trip'},
                 title=f'Top 10 Trips in {year}',
                 color=top_trips.values,
                 color_continuous_scale='Blues')
    st.plotly_chart(fig, use_container_width=True)
    
    # Category breakdown
    st.subheader("Spending by Category")
    category_spending = trip_year_filtered.groupby('Category')['Corrected Amount'].sum().sort_values(ascending=False)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig = px.pie(values=category_spending.values, names=category_spending.index,
                     title='Category Distribution',
                     color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.dataframe(pd.DataFrame({
            'Category': category_spending.index,
            'Amount': [f"${x:,.2f}" for x in category_spending.values],
            'Percentage': [f"{x/category_spending.sum()*100:.1f}%" for x in category_spending.values]
        }), hide_index=True)

def show_eating_out(year, eating_out):
    """Eating out analysis page"""
    st.header(f"🍽️ Eating Out - {year}")
    
    eating_year = eating_out[eating_out['Date'].dt.year == year]
    
    if len(eating_year) == 0:
        st.warning(f"No eating out data available for {year}")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Spending", f"${eating_year['Final Total'].sum():,.2f}")
    with col2:
        st.metric("Dining Occasions", f"{len(eating_year)}")
    with col3:
        st.metric("Average per Meal", f"${eating_year['Final Total'].mean():.2f}")
    
    # Category breakdown
    st.subheader("Dine In vs Take Out")
    category_breakdown = eating_year.groupby('Category')['Final Total'].agg(['sum', 'count'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.pie(values=category_breakdown['sum'].values, 
                     names=category_breakdown.index,
                     title='Spending Distribution',
                     color_discrete_sequence=['#51CF66', '#FF6B6B'])
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.bar(x=category_breakdown.index, y=category_breakdown['count'],
                     title='Number of Occasions',
                     labels={'x': 'Category', 'y': 'Count'},
                     color=category_breakdown.index,
                     color_discrete_sequence=['#51CF66', '#FF6B6B'])
        st.plotly_chart(fig, use_container_width=True)
    
    # Monthly trend
    st.subheader("Monthly Spending Trend")
    eating_year['Month'] = eating_year['Date'].dt.to_period('M').astype(str)
    monthly = eating_year.groupby('Month').agg({
        'Final Total': 'sum',
        'Resturant': 'count'
    }).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly['Month'], y=monthly['Final Total'],
                             mode='lines+markers', name='Spending',
                             line=dict(color='#2E75B6', width=3)))
    fig.update_layout(title='Monthly Eating Out Spending',
                     xaxis_title='Month', yaxis_title='Amount ($)')
    st.plotly_chart(fig, use_container_width=True)

def show_grocery_analysis(year, grocery):
    """Grocery analysis page"""
    st.header(f"🛒 Grocery Analysis - {year}")
    
    grocery_year = grocery[grocery['Date'].dt.year == year]
    
    if len(grocery_year) == 0:
        st.warning(f"No grocery data available for {year}")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Spending", f"${grocery_year['Amount'].sum():,.2f}")
    with col2:
        st.metric("Shopping Trips", f"{len(grocery_year)}")
    with col3:
        st.metric("Average per Trip", f"${grocery_year['Amount'].mean():.2f}")
    
    # Store breakdown
    st.subheader("Spending by Store")
    store_spending = grocery_year.groupby('Store')['Amount'].sum().sort_values(ascending=False).head(10)
    
    fig = px.bar(x=store_spending.values, y=store_spending.index, orientation='h',
                 title='Top 10 Stores',
                 labels={'x': 'Amount ($)', 'y': 'Store'},
                 color=store_spending.values,
                 color_continuous_scale='Greens')
    st.plotly_chart(fig, use_container_width=True)
    
    # Location comparison
    if 'Location' in grocery_year.columns:
        st.subheader("Spending by Location")
        
        location_data = grocery_year.groupby('Location').agg({
            'Amount': ['sum', 'count', 'mean']
        }).round(2)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.dataframe(location_data, use_container_width=True)
        
        with col2:
            fig = px.pie(values=location_data[('Amount', 'sum')].values,
                        names=location_data.index,
                        title='Spending by Location',
                        color_discrete_sequence=['#2E75B6', '#51CF66'])
            st.plotly_chart(fig, use_container_width=True)

def show_year_comparison(trip_finance, eating_out, grocery):
    """Year-over-year comparison page"""
    st.header("📈 Year-over-Year Comparison")
    
    years = sorted(trip_finance['Date'].dt.year.dropna().unique())
    
    if len(years) < 2:
        st.warning("Need at least 2 years of data for comparison")
        return
    
    # Calculate stats for all years
    comparison_data = []
    for year in years:
        stats = calculate_summary_stats(year, trip_finance, eating_out, grocery)
        comparison_data.append({
            'Year': year,
            'Trip Finance': stats['trip_total'],
            'Eating Out': stats['eating_total'],
            'Grocery': stats['grocery_total'],
            'Total': stats['total_expenses']
        })
    
    df_comparison = pd.DataFrame(comparison_data)
    
    # Display table
    st.subheader("Summary Table")
    st.dataframe(df_comparison.style.format({
        'Trip Finance': '${:,.2f}',
        'Eating Out': '${:,.2f}',
        'Grocery': '${:,.2f}',
        'Total': '${:,.2f}'
    }), use_container_width=True)
    
    # Comparison chart
    st.subheader("Spending Trends")
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_comparison['Year'], y=df_comparison['Trip Finance'],
                        name='Trip Finance', marker_color='#2E75B6'))
    fig.add_trace(go.Bar(x=df_comparison['Year'], y=df_comparison['Eating Out'],
                        name='Eating Out', marker_color='#51CF66'))
    fig.add_trace(go.Bar(x=df_comparison['Year'], y=df_comparison['Grocery'],
                        name='Grocery', marker_color='#FF6B6B'))
    
    fig.update_layout(barmode='group', title='Year-over-Year Expense Comparison',
                     xaxis_title='Year', yaxis_title='Amount ($)')
    st.plotly_chart(fig, use_container_width=True)

def show_housing_analysis(year):
    """Housing analysis page with fixed costs"""
    st.header(f"🏠 Housing Analysis - {year}")
    
    # Fixed 2025 data
    if year == 2025:
        rent_paid = 81097.59
        mortgage = 30558.87
        rental_income = 36000.00
        car_payment = 5536.89
        electric = 953.29
        internet = 250.00
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Rent Paid", f"${rent_paid:,.2f}")
            st.caption("Your primary residence")
        with col2:
            st.metric("Mortgage", f"${mortgage:,.2f}")
            st.caption("Investment property")
        with col3:
            st.metric("Rental Income", f"${rental_income:,.2f}")
            st.caption("Apr-Dec, $4,000/mo")
        
        # Net housing
        net_housing = rent_paid + mortgage - rental_income
        st.subheader("Net Housing Cost")
        st.metric("Out-of-Pocket Housing", f"${net_housing:,.2f}",
                 help="Total housing costs minus rental income received")
        
        # Housing breakdown
        housing_data = pd.DataFrame({
            'Category': ['Rent Paid', 'Mortgage', 'Car Payment', 'Electric', 'Internet'],
            'Amount': [rent_paid, mortgage, car_payment, electric, internet]
        })
        
        fig = px.pie(housing_data, values='Amount', names='Category',
                     title='Fixed Expenses Breakdown',
                     color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig, use_container_width=True)
        
        # Insights
        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.subheader("💡 Housing Insights")
        st.write(f"- Total housing costs: **${rent_paid + mortgage:,.2f}**")
        st.write(f"- Rental income covers: **{rental_income/(rent_paid+mortgage)*100:.1f}%** of housing costs")
        st.write(f"- Net out-of-pocket: **${net_housing:,.2f}**")
        st.write(f"- Monthly car payment: **$615.21** (started Apr 2025)")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info(f"Housing analysis is only available for 2025. Selected year: {year}")

if __name__ == "__main__":
    main()
