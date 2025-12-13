"""
Indian Bank Branch Analytics Dashboard - Advanced Version
Provides actionable insights for banking expansion and competition analysis
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium
import numpy as np
import sys
from pathlib import Path
from scipy.spatial import distance_matrix

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from data.data_loader import BankDataLoader

# Page configuration
st.set_page_config(
    page_title="Bank Branch Analytics & Insights",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .insight-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    .warning-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    .opportunity-box {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize data loader
@st.cache_resource
def load_data():
    """Load and cache the bank data."""
    loader = BankDataLoader()
    return loader

@st.cache_data
def get_combined_data(_loader):
    """Get and cache the combined dataset."""
    return _loader.load_combined_data()

def calculate_branch_density(df, state):
    """Calculate branches per 1000 sq km (approximate)."""
    # Approximate state areas in sq km
    state_areas = {
        'Rajasthan': 342239, 'Maharashtra': 307713, 'Uttar Pradesh': 240928,
        'Madhya Pradesh': 308245, 'Gujarat': 196244, 'Karnataka': 191791,
        'Andhra Pradesh': 160205, 'Tamil Nadu': 130060, 'Bihar': 94163,
        'West Bengal': 88752, 'Telangana': 112077, 'Haryana': 44212,
        'Punjab': 50362, 'Kerala': 38852, 'Jharkhand': 79716
    }

    area = state_areas.get(state, 100000)  # Default 100k if unknown
    branch_count = len(df[df['State'] == state])
    return round(branch_count / (area / 1000), 2)

def find_underserved_cities(df, threshold=2):
    """Find cities with less than threshold branches."""
    city_counts = df.groupby(['State', 'City']).size().reset_index(name='Branch_Count')
    underserved = city_counts[city_counts['Branch_Count'] < threshold]
    return underserved.sort_values('Branch_Count')

def calculate_market_concentration(df, state):
    """Calculate HHI (Herfindahl-Hirschman Index) for market concentration."""
    state_df = df[df['State'] == state]
    bank_shares = state_df['Bank'].value_counts(normalize=True)
    hhi = (bank_shares ** 2).sum() * 10000  # Scale to 0-10000
    return round(hhi, 2)

def main():
    """Main dashboard application."""

    # Header
    st.markdown('<h1 class="main-header">🏦 Banking Expansion & Competition Analytics</h1>', unsafe_allow_html=True)
    st.markdown("**Actionable insights for identifying market opportunities and banking deserts**")

    # Load data
    loader = load_data()
    df = get_combined_data(loader)

    # Sidebar
    st.sidebar.header("🎯 Analysis Options")

    analysis_type = st.sidebar.radio(
        "Select Analysis Type",
        ["🗺️ Market Overview",
         "🔍 Banking Desert Analysis",
         "⚡ Competition Heatmap",
         "📊 Market Concentration",
         "🎯 Expansion Opportunities"]
    )

    # Bank filter
    all_banks = sorted(df['Bank'].unique().tolist())

    if analysis_type == "⚡ Competition Heatmap":
        selected_banks = st.sidebar.multiselect(
            "Compare Banks",
            options=all_banks,
            default=all_banks[:3] if len(all_banks) >= 3 else all_banks,
            help="Select banks to compare on the heatmap"
        )
    else:
        selected_banks = all_banks

    # Filter data
    filtered_df = df[df['Bank'].isin(selected_banks)]

    # ==================== MARKET OVERVIEW ====================
    if analysis_type == "🗺️ Market Overview":
        st.markdown("## 📊 Market Overview & Key Metrics")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Branches", f"{len(filtered_df):,}")
        with col2:
            st.metric("Banks Covered", f"{filtered_df['Bank'].nunique()}")
        with col3:
            st.metric("States Covered", f"{filtered_df['State'].nunique()}")
        with col4:
            st.metric("Cities Covered", f"{filtered_df['City'].nunique()}")

        st.markdown("---")

        col_left, col_right = st.columns([1.2, 1])

        with col_left:
            st.markdown("### 🗺️ Geographic Distribution")

            # Create clustered map
            center_lat = filtered_df['Latitude'].median()
            center_lng = filtered_df['Longitude'].median()

            m = folium.Map(
                location=[center_lat, center_lng],
                zoom_start=5,
                tiles='OpenStreetMap'
            )

            # Add marker cluster for performance
            marker_cluster = MarkerCluster().add_to(m)

            # Color code by bank
            bank_colors = {bank: color for bank, color in zip(
                all_banks,
                ['red', 'blue', 'green', 'purple', 'orange', 'darkred',
                 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue',
                 'darkpurple', 'white', 'pink', 'lightblue']
            )}

            sample_size = min(500, len(filtered_df))
            sample_df = filtered_df.sample(n=sample_size, random_state=42)

            for idx, row in sample_df.iterrows():
                folium.CircleMarker(
                    location=[row['Latitude'], row['Longitude']],
                    radius=5,
                    popup=f"<b>{row['Bank']}</b><br>{row['City']}, {row['State']}",
                    color=bank_colors.get(row['Bank'], 'gray'),
                    fill=True,
                    fillOpacity=0.7
                ).add_to(marker_cluster)

            st_folium(m, width=800, height=500)

        with col_right:
            st.markdown("### 📈 Top 10 States by Branch Density")

            # Calculate density for top states
            top_states = filtered_df['State'].value_counts().head(10).index
            density_data = []

            for state in top_states:
                count = len(filtered_df[filtered_df['State'] == state])
                density = calculate_branch_density(filtered_df, state)
                density_data.append({'State': state, 'Branches': count, 'Density': density})

            density_df = pd.DataFrame(density_data)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=density_df['Density'],
                y=density_df['State'],
                orientation='h',
                marker_color='lightblue',
                name='Branches/1000 sq km'
            ))
            fig.update_layout(
                xaxis_title="Branches per 1000 sq km",
                yaxis_title="State",
                height=450,
                yaxis={'categoryorder': 'total ascending'}
            )
            st.plotly_chart(fig, use_container_width=True)

    # ==================== BANKING DESERT ANALYSIS ====================
    elif analysis_type == "🔍 Banking Desert Analysis":
        st.markdown("## 🏜️ Banking Desert Analysis")
        st.markdown("**Identify underserved cities and regions with limited banking access**")

        threshold = st.sidebar.slider(
            "Define 'Underserved' (branches less than)",
            min_value=1,
            max_value=5,
            value=2,
            help="Cities with fewer branches than this are considered underserved"
        )

        underserved = find_underserved_cities(filtered_df, threshold)

        st.markdown(f"### ⚠️ Found {len(underserved)} Underserved Cities")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown(f"**Cities with < {threshold} branches:**")
            st.dataframe(
                underserved.head(20),
                use_container_width=True,
                height=400
            )

        with col2:
            # State-wise underserved cities
            state_underserved = underserved.groupby('State').size().reset_index(name='Underserved_Cities')
            state_underserved = state_underserved.sort_values('Underserved_Cities', ascending=False).head(10)

            fig = px.bar(
                state_underserved,
                x='Underserved_Cities',
                y='State',
                orientation='h',
                title=f"Top 10 States with Most Underserved Cities",
                color='Underserved_Cities',
                color_continuous_scale='Reds'
            )
            fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

        # Insights
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.markdown(f"""
        ### 💡 Key Insights:
        - **{len(underserved)}** cities have less than {threshold} branches
        - **{underserved['State'].nunique()}** states have underserved cities
        - **Top underserved state**: {state_underserved.iloc[0]['State']} ({state_underserved.iloc[0]['Underserved_Cities']} cities)
        - **Expansion Opportunity**: These cities represent greenfield markets with low competition
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    # ==================== COMPETITION HEATMAP ====================
    elif analysis_type == "⚡ Competition Heatmap":
        st.markdown("## 🔥 Competition Intensity Heatmap")
        st.markdown("**Visualize branch concentration and competitive hotspots**")

        if len(selected_banks) < 1:
            st.warning("Please select at least one bank from the sidebar")
            return

        # Create heatmap
        st.markdown("### 🗺️ Branch Density Heatmap")

        center_lat = filtered_df['Latitude'].median()
        center_lng = filtered_df['Longitude'].median()

        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=5,
            tiles='OpenStreetMap'
        )

        # Prepare heatmap data
        heat_data = [[row['Latitude'], row['Longitude']] for idx, row in filtered_df.iterrows()]

        HeatMap(heat_data, radius=15, blur=25, max_zoom=13).add_to(m)

        st_folium(m, width=1200, height=600)

        # Competition matrix
        st.markdown("### 📊 State-wise Competition Matrix")

        top_states = filtered_df['State'].value_counts().head(10).index
        competition_matrix = []

        for state in top_states:
            state_data = filtered_df[filtered_df['State'] == state]
            row_data = {'State': state}

            for bank in selected_banks:
                bank_count = len(state_data[state_data['Bank'] == bank])
                row_data[bank] = bank_count

            row_data['Total'] = len(state_data)
            competition_matrix.append(row_data)

        comp_df = pd.DataFrame(competition_matrix)

        # Create heatmap visualization
        fig = go.Figure(data=go.Heatmap(
            z=comp_df[selected_banks].values.T,
            x=comp_df['State'],
            y=selected_banks,
            colorscale='Blues',
            text=comp_df[selected_banks].values.T,
            texttemplate='%{text}',
            textfont={"size": 10}
        ))
        fig.update_layout(
            title="Branch Count by Bank and State",
            xaxis_title="State",
            yaxis_title="Bank",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

        # Insights
        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        most_competitive_state = comp_df.loc[comp_df['Total'].idxmax(), 'State']
        st.markdown(f"""
        ### 💡 Competition Insights:
        - **Most competitive state**: {most_competitive_state} ({comp_df['Total'].max()} total branches)
        - **Comparing {len(selected_banks)} banks** across top states
        - Darker blue = higher branch concentration
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    # ==================== MARKET CONCENTRATION ====================
    elif analysis_type == "📊 Market Concentration":
        st.markdown("## 📊 Market Concentration Analysis (HHI)")
        st.markdown("**Measure market competitiveness using Herfindahl-Hirschman Index**")

        st.info("""
        **HHI Interpretation:**
        - HHI < 1500: Competitive market
        - HHI 1500-2500: Moderate concentration
        - HHI > 2500: High concentration (near monopoly)
        """)

        # Calculate HHI for each state
        top_states = filtered_df['State'].value_counts().head(15).index
        hhi_data = []

        for state in top_states:
            hhi = calculate_market_concentration(filtered_df, state)
            branch_count = len(filtered_df[filtered_df['State'] == state])
            bank_count = filtered_df[filtered_df['State'] == state]['Bank'].nunique()

            hhi_data.append({
                'State': state,
                'HHI': hhi,
                'Branches': branch_count,
                'Banks': bank_count,
                'Market Type': 'Competitive' if hhi < 1500 else 'Moderate' if hhi < 2500 else 'Concentrated'
            })

        hhi_df = pd.DataFrame(hhi_data).sort_values('HHI', ascending=False)

        col1, col2 = st.columns([1, 1])

        with col1:
            # HHI bar chart
            fig = px.bar(
                hhi_df,
                x='HHI',
                y='State',
                orientation='h',
                color='Market Type',
                color_discrete_map={
                    'Competitive': 'green',
                    'Moderate': 'orange',
                    'Concentrated': 'red'
                },
                title="Market Concentration by State"
            )
            fig.add_vline(x=1500, line_dash="dash", line_color="orange", annotation_text="Moderate")
            fig.add_vline(x=2500, line_dash="dash", line_color="red", annotation_text="Concentrated")
            fig.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("### 📋 Market Concentration Data")
            st.dataframe(hhi_df, use_container_width=True, height=500)

        # Insights
        competitive_markets = len(hhi_df[hhi_df['HHI'] < 1500])
        concentrated_markets = len(hhi_df[hhi_df['HHI'] > 2500])

        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown(f"""
        ### 💡 Market Insights:
        - **{competitive_markets}** competitive markets (HHI < 1500)
        - **{concentrated_markets}** concentrated markets (HHI > 2500)
        - **Most concentrated**: {hhi_df.iloc[0]['State']} (HHI: {hhi_df.iloc[0]['HHI']})
        - **Most competitive**: {hhi_df.iloc[-1]['State']} (HHI: {hhi_df.iloc[-1]['HHI']})
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    # ==================== EXPANSION OPPORTUNITIES ====================
    elif analysis_type == "🎯 Expansion Opportunities":
        st.markdown("## 🎯 Strategic Expansion Opportunities")
        st.markdown("**Data-driven recommendations for new branch locations**")

        # Criteria: Low competition + Some existing presence
        expansion_scores = []

        for state in filtered_df['State'].unique():
            state_df = filtered_df[filtered_df['State'] == state]
            branch_count = len(state_df)
            bank_count = state_df['Bank'].nunique()
            cities = state_df['City'].nunique()

            # Scoring logic (customize as needed)
            # Higher score = better opportunity
            score = 0

            # Moderate branch count (not too crowded, not empty)
            if 10 <= branch_count <= 50:
                score += 30
            elif branch_count < 10:
                score += 10

            # Good city coverage potential
            if cities > 5:
                score += 20

            # Low competition (fewer banks)
            if bank_count < 5:
                score += 25

            # Calculate HHI
            hhi = calculate_market_concentration(filtered_df, state)
            if hhi > 2500:  # Concentrated market
                score += 25

            expansion_scores.append({
                'State': state,
                'Opportunity_Score': score,
                'Current_Branches': branch_count,
                'Banks_Present': bank_count,
                'Cities_Covered': cities,
                'HHI': hhi
            })

        exp_df = pd.DataFrame(expansion_scores).sort_values('Opportunity_Score', ascending=False).head(10)

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("### 🏆 Top 10 Expansion Opportunities")

            fig = px.bar(
                exp_df,
                x='Opportunity_Score',
                y='State',
                orientation='h',
                color='Opportunity_Score',
                color_continuous_scale='Greens',
                text='Opportunity_Score'
            )
            fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("### 📊 Detailed Metrics")
            st.dataframe(exp_df, use_container_width=True, height=400)

        # Recommendations
        top_state = exp_df.iloc[0]

        st.markdown('<div class="opportunity-box">', unsafe_allow_html=True)
        st.markdown(f"""
        ### 💡 Expansion Recommendations:

        **Top Opportunity: {top_state['State']}**
        - Opportunity Score: {top_state['Opportunity_Score']}/100
        - Current Branches: {top_state['Current_Branches']}
        - Competing Banks: {top_state['Banks_Present']}
        - Cities Available: {top_state['Cities_Covered']}
        - Market Concentration (HHI): {top_state['HHI']:.0f}

        **Why this is a good opportunity:**
        - {'Low competition' if top_state['Banks_Present'] < 5 else 'Moderate competition'}
        - {'High market concentration - dominated by few players' if top_state['HHI'] > 2500 else 'Balanced market'}
        - Multiple cities available for expansion
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666; padding: 1rem;'>
            <p><b>Data Source:</b> Web scraped from 19 financial institutions | <b>Sample Data</b> for demonstration</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
