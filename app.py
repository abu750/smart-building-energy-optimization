from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Smart Building | Al Jouf", page_icon="🏢", layout="wide")

BASELINE_ENERGY = 751721.08
BASELINE_COST = 240550.75
BASELINE_CO2 = 413446.60
DATA_FILE = Path(__file__).with_name("NSGA2_Pareto_AUDIT.csv")

st.title("Smart Building Energy Optimization")
st.caption("Al Jouf University Building · Sakakah, Saudi Arabia · EnergyPlus-informed surrogate + NSGA-II")

@st.cache_data
def load_data(path):
    return pd.read_csv(path)

if not DATA_FILE.exists():
    st.error("NSGA2_Pareto_AUDIT.csv is missing. Place it beside app.py.")
    st.stop()

df = load_data(DATA_FILE)
required = ["Cooling_COP", "Lighting_W_m2", "Thermostat_C", "Smart_BMS", "Insulation_Level", "Electricity_kWh_year", "Annual_Cost_SAR_year", "CO2_kg_year", "Initial_Investment_SAR"]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"Missing CSV columns: {', '.join(missing)}")
    st.stop()

st.sidebar.header("Solution filters")
budget = st.sidebar.slider("Maximum initial investment (SAR)", 0, 1500000, 1500000, 25000)
max_temp = st.sidebar.slider("Maximum cooling setpoint (°C)", 22.0, 25.0, 25.0, 0.1)
levels = st.sidebar.multiselect("Insulation levels", sorted(df["Insulation_Level"].unique().tolist()), default=sorted(df["Insulation_Level"].unique().tolist()))
bms_choice = st.sidebar.selectbox("Smart BMS", ["All", "Enabled", "Disabled"])

filtered = df[(df["Initial_Investment_SAR"] <= budget) & (df["Thermostat_C"] <= max_temp + 1e-8) & (df["Insulation_Level"].isin(levels))].copy()
if bms_choice != "All":
    filtered = filtered[filtered["Smart_BMS"] == (1 if bms_choice == "Enabled" else 0)]

st.subheader("Baseline scenario")
a, b, c = st.columns(3)
a.metric("Annual electricity (kWh)", f"{BASELINE_ENERGY:,.0f}")
b.metric("Annual operating cost (SAR)", f"{BASELINE_COST:,.0f}")
c.metric("Annual CO₂ (kg)", f"{BASELINE_CO2:,.0f}")

if filtered.empty:
    st.warning("No optimized solutions match these filters. Adjust the sidebar settings.")
    st.stop()

selection = st.radio("Highlight a solution", ["Lowest electricity", "Lowest annualized cost", "Lowest emissions"], horizontal=True)
objective = {"Lowest electricity": "Electricity_kWh_year", "Lowest annualized cost": "Annual_Cost_SAR_year", "Lowest emissions": "CO2_kg_year"}[selection]
selected = filtered.loc[filtered[objective].idxmin()]

st.subheader("Selected optimized solution")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Electricity (kWh/year)", f"{selected['Electricity_kWh_year']:,.0f}", f"{(BASELINE_ENERGY-selected['Electricity_kWh_year'])/BASELINE_ENERGY:.1%} reduction")
c2.metric("Annualized total cost (SAR/year)", f"{selected['Annual_Cost_SAR_year']:,.0f}")
c3.metric("CO₂ (kg/year)", f"{selected['CO2_kg_year']:,.0f}", f"{(BASELINE_CO2-selected['CO2_kg_year'])/BASELINE_CO2:.1%} reduction")
c4.metric("Initial investment (SAR)", f"{selected['Initial_Investment_SAR']:,.0f}")

st.info("Cost comparison: baseline cost is operating cost only; optimized annualized total cost includes operating cost plus annualized investment. Negative cost savings may occur.")

st.subheader("Pareto solution explorer")
fig = px.scatter(filtered, x="Electricity_kWh_year", y="Annual_Cost_SAR_year", color="CO2_kg_year", size="Initial_Investment_SAR", hover_data=["Cooling_COP", "Lighting_W_m2", "Thermostat_C", "Smart_BMS", "Insulation_Level"], labels={"Electricity_kWh_year":"Annual electricity (kWh)", "Annual_Cost_SAR_year":"Annualized total cost (SAR)", "CO2_kg_year":"CO₂ (kg/year)", "Initial_Investment_SAR":"Initial investment (SAR)"}, color_continuous_scale="Viridis")
fig.add_scatter(x=[selected["Electricity_kWh_year"]], y=[selected["Annual_Cost_SAR_year"]], mode="markers", marker={"symbol":"star", "size":18, "color":"red"}, name="Selected solution")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Selected design parameters")
p1, p2, p3, p4, p5 = st.columns(5)
p1.metric("Cooling COP", f"{selected['Cooling_COP']:.3f}")
p2.metric("Lighting (W/m²)", f"{selected['Lighting_W_m2']:.3f}")
p3.metric("Setpoint (°C)", f"{selected['Thermostat_C']:.3f}")
p4.metric("Smart BMS", "On" if selected["Smart_BMS"] == 1 else "Off")
p5.metric("Insulation level", f"{int(selected['Insulation_Level'])}")

st.subheader(f"Filtered optimization results ({len(filtered)} solutions)")
st.dataframe(filtered.sort_values("Electricity_kWh_year"), use_container_width=True, hide_index=True)
st.download_button("Download filtered CSV", data=filtered.to_csv(index=False).encode("utf-8"), file_name="filtered_optimization_results.csv", mime="text/csv")

with st.expander("Methods, assumptions and limitations"):
    st.markdown("""- Building: hypothetical 10,000 m² university building, Sakakah, Al Jouf.
- Weather: Sakakah TMYx weather file; EnergyPlus v26.1.0 for thermal-load simulations.
- Optimization: NSGA-II over a surrogate energy/cost/emissions model, with maximum 25°C cooling setpoint and 1.5 million SAR investment cap.
- The baseline electricity total is **surrogate-estimated**, not a direct EnergyPlus metered HVAC-electricity output. IdealLoadsAirSystem models thermal loads.
- Electricity tariff (0.32 SAR/kWh), CO₂ factor (0.55 kg/kWh), HVAC and investment assumptions are scenario inputs, not field-verified measurements.
- CO₂ is proportional to electricity in this model, so it is not an independent optimization objective.
- No measured building data were available for field calibration; results are simulation-based, not experimentally validated.
- The chart shows **precomputed solutions**, not new optimization runs when filters change.""")

# ===== EnergyPlus Insulation Comparison (V2) =====
st.divider()
st.header("EnergyPlus Thermal Performance")
st.caption("Annual simulated thermal loads — not direct HVAC electricity consumption.")

insulation = pd.DataFrame({
    "Insulation": ["Level 1 - Baseline", "Level 2 - 5 cm", "Level 3 - 10 cm"],
    "Cooling_GJ": [3236.12, 2351.68, 2231.41],
    "Heating_GJ": [138.52, 6.85, 1.23]
})

insulation["Cooling_Reduction_pct"] = (
    (1 - insulation["Cooling_GJ"] / 3236.12) * 100
)
insulation["Heating_Reduction_pct"] = (
    (1 - insulation["Heating_GJ"] / 138.52) * 100
)

fig_insulation = px.bar(
    insulation,
    x="Insulation",
    y=["Cooling_GJ", "Heating_GJ"],
    barmode="group",
    labels={"value": "Annual thermal load (GJ)", "variable": "Load type"},
    title="Effect of Insulation on Annual Heating and Cooling Loads"
)
st.plotly_chart(fig_insulation, use_container_width=True)

st.dataframe(
    insulation.round(2),
    use_container_width=True,
    hide_index=True
)

st.info(
    "Results are based on EnergyPlus simulations. "
    "The baseline and insulation scenarios use the same building and weather conditions."
)
