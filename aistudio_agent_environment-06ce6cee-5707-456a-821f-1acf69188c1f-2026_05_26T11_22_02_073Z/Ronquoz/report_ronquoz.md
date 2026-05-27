# Energy Planning for an Evolving District: The "Ronquoz 21" Master Plan (Sion, 2060)
**HES-SO Valais-Wallis - Numerical Simulation Course**  
**Author:** Energy Planning Sizing Agent  
**Date:** May 2026  

---

## Executive Summary
This report presents the complete energy planning, sizing, and optimization results for the **Ronquoz 21** district in Sion, projected for the year 2060. Historically an industrial area, the district will undergo a full urban transformation, incorporating a balanced mix of residential, administrative, educational, commercial, and recreational uses. 

The evaluation is structured across three primary laboratories:
1. **Laboratoire 1:** Hourly estimation of space heating and Domestic Hot Water (DHW) demands across all buildings, following the Swiss SIA 380/1 standard.
2. **Laboratoire 2:** Evaluation of solar photovoltaic (PV) generation potential on building roofs, integration of electrical consumption profiles, and estimation of short-term and seasonal battery storage requirements.
3. **Laboratoire 3:** Design and mathematical optimization of a District Heating Network (DHN) utilizing local aquifer and river heat sources, using linear programming (PuLP) to select optimized pipe diameters.

All computed metrics are compiled into an interactive web-based GIS and Energy Planning Dashboard (`results/dashboard.html`), allowing stakeholders to explore individual building characteristics, network topologies, and district hourly load profiles.

---

## 1. District Characterization & SRE Analysis (Laboratoire 1)

### 1.1 Mixed-Use Characterization
A critical component of modern urban planning is the creation of mixed-use eco-districts to ensure vibrant, resilient, and energy-efficient communities. We analyzed the Energy Reference Area (SRE - *Surface de Référence Énergétique*) of the district by use class (affectation) to evaluate this character.

The total SRE of the district is **745,190.4 m²**. The SRE distribution by affectation is shown in the table below:

| Use / Affectation | SRE Area [m²] | Percentage of Total [%] | Character |
| :--- | :---: | :---: | :---: |
| **Administration** | 246,375.0 | 33.1% | Heated (Offices, Labs, Energypolis Campus) |
| **Habitat collectif** | 244,023.3 | 32.8% | Heated (Multi-family apartment buildings) |
| **Ecole** | 103,032.9 | 13.8% | Heated (Schools and Educational spaces) |
| **Non chauffé** | 99,383.4 | 13.3% | Unheated (Warehouses, cellars, parkings) |
| **Industries** | 32,203.8 | 4.3% | Heated (Factories, light manufacturing) |
| **Commerce** | 14,846.4 | 2.0% | Heated (Shops, retail and supermarkets) |
| **Installation sportive** | 4,866.3 | 0.7% | Heated (Gymnasiums, arenas) |

#### Analysis:
*   **Mixed-Use Status:** The district **genuinely exhibits a highly mixed-use character**. It does not suffer from single-use zoning (such as purely residential suburbs or lifeless office blocks). 
*   **Predominant Uses:** The two dominant uses are **Administration (33.1%)** and **Habitat collectif (32.8%)**, which together account for **65.9%** of the district's SRE. Schools (13.8%) and unheated service areas (13.3%) make up the remainder, with minor retail, industrial, and sporting contributions.
*   **Complementary Demands:** This SRE balance is highly beneficial. Office spaces (Administration) and schools are occupied and heated primarily during weekdays from 8:00 to 18:00, whereas apartment buildings (Habitat collectif) have high thermal and electrical demands during evenings, mornings, and weekends. This complimentary scheduling flattens the district's aggregated load curves and increases the viability of shared energy systems (such as district heating networks and solar microgrids).

---

## 2. Thermal Energy Demand Sizing (Laboratoire 1)

### 2.1 Space Heating Demand Formula (SIA 380/1)
The space heating energy demand ($Q_{H,li}$ in kWh/m² SRE) for each building $i$ is calculated using the historical SIA 380/1 standards corresponding to the building's construction year:

$$Q_{H,li} = (Q_{H,li0} + \Delta Q_{H,li} \times f_{env}) \times f_{cor}$$

Where:
*   $Q_{H,li0}$ is the base heating limit coefficient [kWh/m²].
*   $\Delta Q_{H,li}$ is the envelope correction factor [kWh/m²].
*   $f_{env}$ is the building's envelope factor (*facteur d'enveloppe*, ratio of envelope area to SRE).
*   $f_{cor}$ is the meteorological correction factor defined as:

$$f_{cor} = 1 + ((9.4^\circ\text{C} - \theta_{e,avg}) \times 0.06)$$

Using Sion's meteorological dataset, the annual average outdoor temperature ($\theta_{e,avg}$) is **11.21 °C**, which yields a meteorological correction factor ($f_{cor}$) of **0.8914** (representing a ~10.9% reduction in heating requirements compared to the Swiss plateau standard test climate of 9.4 °C).

### 2.2 SRE Normative Selection by Construction Year
To evaluate historical progression and accurately represent the current building stock alongside future high-performance buildings, the standard selected depends on the building's construction year:
*   **Year $\le$ 2001:** standard "SIA 380/1 1988-2001"
*   **2001 $<$ Year $\le$ 2007:** standard "SIA 380/1 2001"
*   **2007 $<$ Year $\le$ 2009:** standard "SIA 380/1 2007"
*   **Year $>$ 2009:** standard "SIA 380/1 2016" (highly insulated, high-performance designs)

The Domestic Hot Water (DHW / *Eau Chaude Sanitaire - ECS*) requirements are taken directly from the normative limit values ($q_{ECS}$ in kWh/m²) based on building affectation.

### 2.3 Thermal signature and Hourly Profile
The annual heating demands (kWh) are distributed hourly over the 8760 hours of the year using a thermal signature approach based on outdoor temperature:
*   **Heating limit temperature:** 18.5 °C. Heating occurs if $\theta_{e} < 18.5^\circ\text{C}$ with an intensity proportional to $(18.5 - \theta_{e})$.
*   **Thermal Inertia:** Sre-weighted moving average smoothing is applied to account for building thermal mass (ranging from 2 hours for light industrial buildings to 6 hours for heavy residential blocks).
*   **DHW Profile:** DHW consumption is modeled "in-band", operating at a constant rate between 8:00 and 20:00 (12 hours daily) and zero at night.

### 2.4 District Thermal Results & Peaks
*   **Total Heat Consumption (Heating + DHW):** **26,147,810.3 kWh (26.15 GWh/year)**
*   **Peak Thermal Power (Centralized):** **9,259.1 kW (9.26 MW)**
*   **Hourly Profile Analysis:** The peak occurs during winter (typically early morning hours of January) when space heating requirements are maximal and DHW loads activate at 8:00 AM. 

---

## 3. Photovoltaic Production, Electricity & Storage (Laboratoire 2)

### 3.1 PV Sizing and Production Sizing
Each building's available solar panel surface area is extracted from the GIS model. Photovoltaic generation is simulated with the following characteristics matching PVGIS guidelines for Sion:
*   **Installed capacity:** 165 Wp/m² (PV efficiency of 16.5%).
*   **Panel Tilt:** 15° for flat-roof or optimized building structures.
*   **Panel Orientation:** Half (50%) of the panels face full EAST (-90° azimuth) and half face full WEST (+90° azimuth). This East-West configuration reduces the noon generation peak and widens the daily production shoulder, facilitating higher self-consumption.
*   **System Losses:** 10% (dust, wiring, inverter efficiency).

The hourly generation profiles for 1 kWp of East and West facing panels were retrieved from PVGIS cache. The district's total annual PV production is **19,318,860.0 kWh (19.32 GWh/year)**.

### 3.2 Electrical Consumption Profiles
Electrical demands (appliances, ventilation, lighting, and processes, excluding space heating) are assigned to each building based on typical German Association of Energy and Water Industries (BDEW) standard load profiles. 
*   **Total District Electrical Demand:** **23,371,908.6 kWh (23.37 GWh/year)**

### 3.3 Autonomy and Self-Consumption Results
To evaluate the integration of local solar energy, we compute the hourly self-consumed PV power ($P_{self}(t)$) as:

$$P_{self}(t) = \min(P_{load}(t), P_{pv}(t))$$

Summing over the 8760 hours of the year yields:
*   **District Self-Consumption Rate (Autoconsommation):** **76.5%**  
    *(76.5% of the local solar PV generation is directly consumed within the district, which is exceptionally high due to the presence of high-baseload industrial and administrative buildings).*
*   **District Autonomy Rate (Autonomie):** **63.3%**  
    *(63.3% of the district's annual electricity requirements are covered by local solar energy).*

### 3.4 Electrical Storage Assessment (100% Self-Consumption)
We calculated the theoretical minimum electrical battery capacity required to achieve **100% solar self-consumption** at the district level (ensuring that zero PV energy is exported to the external grid):

$$C_{storage} = \max(\text{SOC}(t)) - \min(\text{SOC}(t)) \quad \text{where} \quad \text{SOC}(t) = \int_0^t (P_{pv}(\tau) - P_{load}(\tau)) d\tau$$

*   **Theoretical Sizing Capacity:** **4,052,612.5 kWh (4,052.6 MWh or 4.05 GWh)**

#### Critical Assessment:
This capacity is **completely unrealistic** and technically/economically unfeasible on a district scale. 
1.  **Chemical Batteries vs. Seasonal Storage:** Achieving 100% self-consumption forces the battery to act as a seasonal storage unit, charging with the massive excess solar energy in July and discharging it in December. Chemical lithium-ion batteries have a high self-discharge rate over months and are far too expensive for seasonal storage (estimated cost of 4.05 GWh at 150 CHF/kWh is over **600 million CHF**).
2.  **Space Requirements:** A 4.05 GWh battery bank would require thousands of square meters of dedicated industrial space, equipped with extensive cooling systems and fire safety containment.
3.  **Alternative Optimizations:**
    *   **Reduce Target:** Aiming for a more realistic 80-85% self-consumption reduces the battery storage requirements by over **98%** (to a few MWh scale), which can be managed with daily short-term battery cycles.
    *   **Power-to-Heat:** Storing surplus solar energy as heat (charging the district heating network, borehole thermal energy storage, or building hot water tanks) is more than 100 times cheaper per kWh than chemical batteries.
    *   **Demand-Side Management (DSM):** Smart EV charging stations can absorb daytime office peaks directly, reducing the need for stationary storage.

---

## 4. Optimized District Heating Network Design (Laboratoire 3)

### 4.1 Network Configuration & Sizing Assumptions
To supply thermal energy from local high-temperature sources to all buildings with active heating demands, an underground thermal network is designed along the existing road network.
*   **Temperature Difference ($\Delta T$):** Fixed at **30 °C** (supply/return difference).
*   **Maximum Pressure Drop:** **100 Pa/m**.
*   **Thermal Losses:** Assumed to be negligible (initial simplification).

The relationship between thermal power ($Q$ [W]) and mass flow rate ($\dot{m}$ [kg/h]) is governed by:

$$\dot{m} = \frac{Q \times 3600}{c_p \times \Delta T} = \frac{Q \times 3600}{4.18 \times 30} = 28.708 \times Q$$

Using the maximum peak power of each building ($P_{peak,i}$ with foisonnement factors), we size the peak mass flow rates for each node and pipe.

### 4.2 Diameter Sizing Optimization (Mixed-Integer Linear Programming)
We formulate a Mixed-Integer Linear Optimization problem in Python (using the PuLP library) to select the optimal pipe diameter for each segment from a discrete set of commercial nominal diameters (DN 25 to DN 400).

#### Objective Function:
Minimize the total investment cost of pipes and civil engineering trenches:

$$\min Z = \sum_{i \in \text{Edges}} (5553 \times D_i + 951.35) \times L_i$$

Where $D_i$ is the inner pipe diameter [m], and $L_i$ is the segment length [m].

#### Constraints:
1.  **Nodal Mass Flow Balance:** For every intersection node, inflow equals outflow. For building nodes, the net flow matches the building's peak demand.
2.  **Mass Flow - Diameter Capacity Limit:** For every pipe $i$, the maximum flow capacity is constrained by its selected diameter:

$$\dot{m}_i \le 765,000 \times D_i - 14,500 \quad [\text{kg/h}]$$

3.  **Discrete Diameter Selection:** Exactly one commercial nominal diameter from the standard set must be active for each edge.

### 4.3 Sizing Results & Economic Viability
The optimization problem was solved successfully, yielding the following results:
*   **Total Network Length:** **14,770.7 m (14.77 km)**
*   **Total Civil Engineering & Pipe Investment Cost:** **16,736,196.24 CHF (16.74 million CHF)**
*   **Selected Heat Resources Mass Flows:**
    *   `rhone` (Rhone River Source): **119,456.8 kg/h** (Primary source)
    *   `nappe` (Groundwater Aquifer): **57,416.3 kg/h**
    *   `nappe_ste_marguerite` (Ste-Marguerite Aquifer): **20,484.8 kg/h**
    *   `cad` (Existing Waste Heat / Central Loop): **9,980.0 kg/h**

#### Linear Energy Density Analysis:
The economic viability of a District Heating Network is evaluated using the **linear energy density** ($\rho_{linear}$ in MWh/m/year):

$$\rho_{linear} = \frac{\text{Annual Heat Delivered [MWh]}}{\text{Total Pipe Length [m]}} = \frac{26,147.81\text{ MWh}}{14,770.67\text{ m}} = 1.77\text{ MWh/m/year}$$

*   **Viability Threshold:** In Switzerland, a thermal network is considered highly viable and economically profitable if the linear energy density is above **1.5 MWh/m/year** (or 1.0 MWh/m/year in low-density suburban areas).
*   **Assessment:** With an energy density of **1.77 MWh/m/year**, the Ronquoz 21 network is **highly viable**. The high SRE concentration and balanced mix of uses ensure that the heavy civil engineering investment (~16.7 million CHF) will be easily amortized, making it an excellent investment for Sion's 2060 decarbonization strategy.

---

## 5. Methodological Criticisms & Recommendations (Laboratoire 3)

While the optimization models provide a robust baseline for sizing, several simplifying assumptions introduce biases that must be addressed before physical implementation.

### 5.1 Sizing Methodology Weaknesses
1.  **Neglecting Thermal Heat Losses:** Real pipes lose heat to the surrounding soil. This typically accounts for **5% to 15%** of annual energy transport. By assuming zero losses, our model underestimates the required heat production from our sources and overestimates network efficiency.
2.  **Fixed Delta-T of 30°C:** The model assumes the return temperature is always $30^\circ\text{C}$ below the supply. In reality, the return temperature depends on individual building heat emitters (e.g., floor heating at 35/30 °C vs old radiators at 70/50 °C). High return temperatures reduce the actual Delta-T, requiring much higher mass flow rates and larger pipe diameters.
3.  **Simplified Linear Capacity Formula:** The relationship $\dot{m} \le 765,000 \times D - 14,500$ is a simplified linear approximation of a quadratic relationship. In reality, friction pressure drops follow the Darcy-Weisbach equation and depend non-linearly on velocity and pipe roughness. This can lead to under-sizing of key trunk lines where velocity exceeds safety limits (typically 2 m/s).
4.  **Single Sizing Peak vs. Coincidence (Foisonnement):** Summing building peaks directly can lead to over-sizing the main supply pipes because not all buildings reach their peak demands at the exact same hour. While individual foisonnement factors were applied at the building level, a spatial co-incidence factor across the branch lines would optimize pipe sizing further.

### 5.2 Proposed Adaptations and Sizing Scheds
1.  **Incorporate Thermal Loss Functions:** Introduce a heat loss model based on soil thermal conductivity, pipe insulation properties, and diameter:
    $$Q_{loss, i} = U_i \times L_i \times (\theta_{fluid, i} - \theta_{soil})$$
2.  **Dynamic Temperature Modeling (4th Generation DHN):** Transition the network model to a low-temperature loop (50-60 °C supply) paired with decentralized booster heat pumps. This minimizes thermal losses and allows easier integration of low-grade waste heat.
3.  **Non-Linear Hydraulic Optimization:** Replace the linear capacity constraint with non-linear head loss constraints, solved using generalized reduced gradient solvers or iterative Hardy-Cross algorithms to ensure pressure drops do not exceed 100 Pa/m in any loop.
4.  **Decentralized Multi-source Routing:** Allow bi-directional flows where building solar thermal arrays or decentralized heat pumps can feed excess heat back into the network, transitioning the district from a passive consumer to an active thermal prosumer.

---

## Conclusion
The **Ronquoz 21** district energy plan represents a highly advanced, sustainable, and economically viable project for Sion 2060. The district heating network is highly justified by its linear energy density of **1.77 MWh/m/year**. On the electrical side, the district achieves an impressive **63.3% autonomy** directly from roof-mounted solar PV. By optimizing battery storage sizes to focus on daily peaks and utilizing power-to-heat integration via the district heating loop, the district can achieve outstanding decarbonization and energy independence with realistic financial investments.

*The full interactive data, maps, and load curves can be explored inside `results/dashboard.html`.*
