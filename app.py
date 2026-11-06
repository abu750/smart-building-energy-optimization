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


# ===== V3 | Research and engineering analysis =====
st.divider()
st.header("Research overview")
st.write("Simulation-based case study of a hypothetical 10,000 m² university building in Sakakah, Al Jouf, Saudi Arabia. Results are not field-calibrated measurements.")
with st.expander("Research workflow", expanded=True):
    st.markdown("**Building geometry and weather** → **EnergyPlus thermal-load simulations** → **Assumption-based electricity and cost model** → **NSGA-II multi-objective search** → **Feasible solution analysis**")
    st.caption("Cooling and heating results from IdealLoadsAirSystem represent thermal demand, not measured HVAC electricity.")

st.header("EnergyPlus thermal performance")
st.caption("Annual heating and cooling thermal loads (GJ/year) from three EnergyPlus insulation simulations.")
thermal = pd.DataFrame({
    "Insulation": ["Level 1 — baseline", "Level 2 — 5 cm", "Level 3 — 10 cm"],
    "Cooling (GJ/year)": [3236.12, 2351.68, 2231.41],
    "Heating (GJ/year)": [138.52, 6.85, 1.23],
})
thermal["Cooling reduction (%)"] = (1 - thermal["Cooling (GJ/year)"] / 3236.12) * 100
thermal["Heating reduction (%)"] = (1 - thermal["Heating (GJ/year)"] / 138.52) * 100
left, right = st.columns(2)
with left:
    st.plotly_chart(px.bar(thermal, x="Insulation", y="Cooling (GJ/year)", title="Cooling thermal load", color="Insulation"), use_container_width=True)
with right:
    st.plotly_chart(px.bar(thermal, x="Insulation", y="Heating (GJ/year)", title="Heating thermal load", color="Insulation"), use_container_width=True)
st.dataframe(thermal.round(2), use_container_width=True, hide_index=True)
st.caption("Thermal data are summarized from completed EnergyPlus simulations; no EnergyPlus runs occur on this website.")

st.header("Scenario comparison")
st.caption("Compare precomputed feasible optimization solutions; filters do not run NSGA-II again.")
min_energy = filtered.loc[filtered["Electricity_kWh_year"].idxmin()]
min_cost = filtered.loc[filtered["Annual_Cost_SAR_year"].idxmin()]
compare = pd.DataFrame([
    {"Scenario": "Baseline (surrogate)", "Electricity (kWh/year)": BASELINE_ENERGY, "Annual total cost (SAR/year)": BASELINE_COST, "CO₂ (kg/year)": BASELINE_CO2, "Investment (SAR)": 0.0},
    {"Scenario": "Minimum electricity", "Electricity (kWh/year)": min_energy["Electricity_kWh_year"], "Annual total cost (SAR/year)": min_energy["Annual_Cost_SAR_year"], "CO₂ (kg/year)": min_energy["CO2_kg_year"], "Investment (SAR)": min_energy["Initial_Investment_SAR"]},
    {"Scenario": "Minimum annualized cost", "Electricity (kWh/year)": min_cost["Electricity_kWh_year"], "Annual total cost (SAR/year)": min_cost["Annual_Cost_SAR_year"], "CO₂ (kg/year)": min_cost["CO2_kg_year"], "Investment (SAR)": min_cost["Initial_Investment_SAR"]},
])
st.dataframe(compare.round(2), use_container_width=True, hide_index=True)
st.plotly_chart(px.bar(compare, x="Scenario", y="Electricity (kWh/year)", color="Scenario", title="Annual electricity comparison"), use_container_width=True)

st.header("Economic assessment")
st.caption("Investment appraisal uses the study's assumed electricity tariff and a capital recovery factor; these are scenario assumptions, not verified market quotations.")
tariff = st.number_input("Electricity tariff (SAR/kWh) — sensitivity", min_value=0.01, max_value=2.0, value=0.32, step=0.01)
interest = st.number_input("Annual discount rate (%)", min_value=0.0, max_value=30.0, value=5.0, step=0.5)
life = st.number_input("Investment lifetime (years)", min_value=1, max_value=40, value=10, step=1)
rate = interest / 100
crf = rate * (1 + rate) ** life / ((1 + rate) ** life - 1) if rate else 1 / life
annual_operating = float(selected["Electricity_kWh_year"]) * tariff
annualized_capex = float(selected["Initial_Investment_SAR"]) * crf
annual_total = annual_operating + annualized_capex
baseline_operating = BASELINE_ENERGY * tariff
annual_saving = baseline_operating - annual_operating
simple_payback = float(selected["Initial_Investment_SAR"]) / annual_saving if annual_saving > 0 else None
x, y, z = st.columns(3)
x.metric("Estimated annual operating cost (SAR)", f"{annual_operating:,.0f}")
y.metric("Estimated annualized investment (SAR)", f"{annualized_capex:,.0f}")
z.metric("Estimated annual total cost (SAR)", f"{annual_total:,.0f}")
if simple_payback is None:
    st.warning("Simple payback is undefined because the estimated annual operating savings are not positive.")
else:
    st.write(f"**Simple payback:** {simple_payback:,.1f} years (investment / annual operating savings).")
st.caption("Sensitivity calculations adjust tariff, discount rate and lifetime for the selected *precomputed* solution only. They do not rerun optimization, and exclude maintenance and tariff escalation.")

with st.expander("Model transparency and scientific limitations (V3)"):
    st.markdown("""- The building is hypothetical, with no measured energy data for calibration.
- EnergyPlus IdealLoadsAirSystem provides thermal loads; electricity is estimated using a separate surrogate model.
- Tariff 0.32 SAR/kWh, emission factor 0.55 kg CO₂/kWh, equipment assumptions and capital costs are study assumptions.
- Annualized optimized cost includes capital recovery; the baseline has zero initial investment.
- CO₂ is proportional to electricity under the constant emission factor, so it is not an independent objective.
- Optimization results are precomputed. Sidebar filtering does not perform a new NSGA-II run.
- EnergyPlus insulation levels are separate simulations. Level 3 may exceed the investment constraint for many configurations.
- Results must not be presented as measured savings or as experimentally validated performance.""")


# ===== V4 Updated | Restorable interactive design studio =====
st.divider()
st.header("Interactive design studio")
st.caption("Experiment with settings without changing or overwriting the 97 saved NSGA-II solutions.")

# References always come from the full original results, not sidebar filters.
best_energy = df.loc[df["Electricity_kWh_year"].idxmin()]
best_cost = df.loc[df["Annual_Cost_SAR_year"].idxmin()]
BASELINE_DESIGN = {"cop": 3.5, "lpd": 10.0, "temp": 24.0, "bms": False, "insulation": 1}
DESIGN_KEYS = ("cop", "lpd", "temp", "bms", "insulation")

def design_from_row(row):
    return {"cop": float(row["Cooling_COP"]), "lpd": float(row["Lighting_W_m2"]),
            "temp": float(row["Thermostat_C"]), "bms": bool(int(row["Smart_BMS"])),
            "insulation": int(row["Insulation_Level"])}

def load_preset(values, label):
    for k in DESIGN_KEYS:
        st.session_state["studio_" + k] = values[k]
    st.session_state["studio_preset"] = label
    st.session_state.pop("studio_result", None)

for k, v in BASELINE_DESIGN.items():
    if "studio_" + k not in st.session_state:
        st.session_state["studio_" + k] = v

st.markdown("**Restore a saved design**")
b1, b2, b3 = st.columns(3)
with b1:
    if st.button("Best energy solution", use_container_width=True):
        load_preset(design_from_row(best_energy), "Minimum electricity — saved NSGA-II solution")
with b2:
    if st.button("Best economic solution", use_container_width=True):
        load_preset(design_from_row(best_cost), "Minimum annualized cost — saved NSGA-II solution")
with b3:
    if st.button("Reset to baseline", use_container_width=True):
        load_preset(BASELINE_DESIGN, "Baseline design settings")

if "studio_preset" in st.session_state:
    st.caption("Loaded: " + st.session_state["studio_preset"])

with st.form("studio_form"):
    d1, d2, d3 = st.columns(3)
    with d1:
        cop = st.slider("Cooling COP", 2.5, 5.0, step=0.0001, format="%.4f", key="studio_cop")
        lpd = st.slider("Lighting density (W/m²)", 5.0, 10.0, step=0.0001, format="%.4f", key="studio_lpd")
    with d2:
        temp = st.slider("Cooling setpoint (°C)", 22.0, 25.0, step=0.0001, format="%.4f", key="studio_temp")
        bms = st.checkbox("Smart BMS enabled", key="studio_bms")
    with d3:
        insulation = st.selectbox("Insulation level", [1, 2, 3], key="studio_insulation",
                                  format_func=lambda n: {1: "Level 1 — baseline", 2: "Level 2 — 5 cm", 3: "Level 3 — 10 cm"}[n])
    evaluate = st.form_submit_button("Evaluate and compare", type="primary")

st.caption("The baseline preset is COP 3.5, lighting 10 W/m², setpoint 24°C, BMS off, insulation level 1. It is a reference configuration, not an optimized result.")

if evaluate:
    inputs = {"cop": cop, "lpd": lpd, "temp": temp, "bms": bms, "insulation": insulation}
    try:
        from evaluate_solution_AUDIT import evaluate_solution as audited_evaluator
    except (ImportError, SyntaxError, OSError) as exc:
        audited_evaluator = None
    if audited_evaluator is not None:
        try:
            import math
            values = audited_evaluator(cop, lpd, temp, int(bms), insulation)
            energy, cost, co2, investment = map(float, values[:4])
            if not all(math.isfinite(v) for v in (energy, cost, co2, investment)):
                raise ValueError("Non-finite result returned")
            st.session_state["studio_result"] = {
                "mode": "estimated", "inputs": inputs,
                "energy": energy, "cost": cost, "co2": co2, "investment": investment}
        except Exception as exc:
            st.session_state["studio_result"] = {"mode": "error", "message": str(exc)}
    else:
        # No surrogate: only retrieve a recorded design, without presenting it as a prediction.
        distance = (((df["Cooling_COP"] - cop) / 2.5) ** 2
                    + ((df["Lighting_W_m2"] - lpd) / 5.0) ** 2
                    + ((df["Thermostat_C"] - temp) / 3.0) ** 2
                    + (df["Smart_BMS"] - int(bms)) ** 2
                    + ((df["Insulation_Level"] - insulation) / 2.0) ** 2) ** 0.5
        nearest = df.loc[distance.idxmin()]
        st.session_state["studio_result"] = {
            "mode": "nearest", "inputs": inputs,
            "energy": float(nearest["Electricity_kWh_year"]),
            "cost": float(nearest["Annual_Cost_SAR_year"]),
            "co2": float(nearest["CO2_kg_year"]),
            "investment": float(nearest["Initial_Investment_SAR"]),
            "nearest_inputs": design_from_row(nearest)}

result = st.session_state.get("studio_result")
if result:
    if result["mode"] == "error":
        st.error("The audited evaluator could not calculate this design: " + result["message"])
    else:
        if result["mode"] == "nearest":
            st.warning("The audited evaluator is not installed on this website. Values below belong to the **nearest saved NSGA-II solution**, NOT to your custom settings. No new calculation was made.")
            st.write("Nearest recorded design:", result["nearest_inputs"])
        else:
            st.success("Calculated using the audited assumption-based surrogate. This is NOT a new EnergyPlus simulation or NSGA-II run.")
        st.subheader("Your design versus the saved energy optimum")
        reference = best_energy
        comparison = pd.DataFrame([
            {"Design": "Your evaluated design" if result["mode"] == "estimated" else "Nearest recorded solution",
             "Electricity (kWh/year)": result["energy"], "Annualized cost (SAR/year)": result["cost"],
             "CO₂ (kg/year)": result["co2"], "Investment (SAR)": result["investment"]},
            {"Design": "Saved best energy solution", "Electricity (kWh/year)": float(reference["Electricity_kWh_year"]),
             "Annualized cost (SAR/year)": float(reference["Annual_Cost_SAR_year"]),
             "CO₂ (kg/year)": float(reference["CO2_kg_year"]),
             "Investment (SAR)": float(reference["Initial_Investment_SAR"])}
        ])
        st.dataframe(comparison.round(2), hide_index=True, use_container_width=True)
        st.plotly_chart(px.bar(comparison, x="Design", y="Electricity (kWh/year)",
                               color="Design", title="Electricity comparison"), use_container_width=True)
        if result["investment"] > 1_500_000:
            st.warning("This design exceeds the 1,500,000 SAR initial investment limit.")
        st.caption("Reference optimum is read from the original AUDIT CSV, independent of sidebar filters. The saved optimization results are never overwritten.")

with st.expander("How saved solutions and custom evaluation work"):
    st.markdown("""- The **Best energy** and **Best economic** buttons load the original recorded decision variables into the controls.
- **Reset to baseline** restores the baseline inputs. It does not modify the original optimization file.
- **Evaluate and compare** calculates new estimates only when `evaluate_solution_AUDIT.py` is available and compatible.
- Without the evaluator, the app shows a **nearest saved solution** and clearly labels it as a lookup, not a custom prediction.
- Saved optimum values come from `NSGA2_Pareto_AUDIT.csv`. No new optimization or EnergyPlus simulation runs here.
- The comparison uses annualized cost for optimized solutions; baseline operating cost excludes capital investment.""")
