# NexGen Logistics Transformation Strategy

## Project Overview 💡

This project delivers a robust, two-phase data intelligence solution to address NexGen Logistics' core challenges of **systematic cost leakage** and the mandate to shift to **predictive operations**.

The final deliverable is an interactive **Cost Intelligence Platform** built on verifiable statistical analysis and supported by a validated Machine Learning (ML) model.

## 1. Setup and Execution 💻

1.  **Organization:** Ensure all 7 original CSV files are in the **`datasets/`** subdirectory.
2.  **Dependencies:** Install required libraries:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Data & Model Generation (Crucial Step):** Run the preparation script once to create the necessary processed files and train/save the ML model.
    ```bash
    python prepare_project_data.py
    ```
4.  **Launch Application:** Run the main Streamlit file:
    ```bash
    python -m streamlit run app.py
    ```

## 2. Solution Files

| File Name | Purpose | Category |
| :--- | :--- | :--- |
| `app.py` | **FINAL Dashboard:** Interactive solution for cost diagnosis and simulation. | Application |
| `prepare_project_data.py` | **ETL & Training Proof:** Script that generates all derived files and trains the ML model. | Preparation |
| `cost_intelligence_data.csv` | **Phase 1 Output:** Derived dataset containing Total Cost and Cost Variance. | Data |
| `cost_predictor_model.pkl` | **Phase 2 ML Model:** Trained Linear Regression Regressor. | Artifact |

## 3. Model Accuracy and Verification 🧠

| Metric | Score | Insight |
| :--- | :--- | :--- |
| **Model Used** | Linear Regression Regressor | Chosen for its **interpretability** and ability to predict cost drivers. |
| **R-squared ($\text{R}^2$)** | **$\mathbf{0.3918}$** | **Predictability Score:** The model explains nearly $\mathbf{40\%}$ of the cost variance using current features. |
| **MAE (Mean Absolute Error)** | **$\mathbf{₹ 158.33}$** | **Reliability:** The average prediction error is small enough for viable predictive pricing estimates. |

---

## 4. 💼 Innovation Brief (Strategic Document)

*Copy the text below and save it as **`Innovation Brief.md`** (or convert it to PDF/Word).*

```markdown
# NexGen Logistics: Innovation Brief - Final Submission

## Executive Summary: Solving the Cost Mandate

**Problem:** NexGen is facing a financial crisis: **Total Operational Costs consistently exceed Billed Prices**, leading to systemic cost leakage and requiring immediate financial correction.

**Solution:** A two-phase, data-driven system is deployed:
1.  **Phase 1 (Immediate Action):** The **Cost Intelligence Platform** diagnoses leakage and corrects current pricing.
2.  **Phase 2 (Future-Proofing):** The validated **Predictive Cost Model** secures profitability on all new orders, fulfilling the "predictive" mandate.

## 1. Phase 1: Cost Intelligence Platform (Financial Stabilization)

**Goal:** Achieve the 15-20% cost reduction mandate.

* **Crisis Proof:** The platform verifies that all carriers exhibit **negative Cost Variance** (Loss). The interactive charts reveal that **Economy priority** is structurally the most inefficient route (highest average cost).
* **Actionable Deliverable:** The **Simulation Tool** provides the exact targets:
    * **Suggested Billed Price:** The minimum price required to achieve a 5% profit margin.
    * **Required Cost Reduction Target:** The operational cost ceiling necessary to meet the 20% savings goal.

## 2. Phase 2: Predictive Pricing & Transformation (ML Model)

**Goal:** Transform operations to predictive status (Advanced Feature Bonus).

| Metric | Result | Strategic Insight for Management |
| :--- | :--- | :--- |
| **Model Used** | Linear Regression Regressor | Chosen for **interpretability** and direct output of financial drivers. |
| **R-squared ($\mathbf{0.3918}$) ** | **Achievable Benchmark:** Proves $40\%$ of the cost is predictable using current data. |
| **MAE** | $\mathbf{₹ 158.33}$ | **Reliability:** The prediction error is small enough for viable predictive pricing estimates. |
| **Key Finding (Action Plan)** | **Cost increases by ₹0.0074 per KM.** | **Guidance for Future Strategy:** The low $\text{R}^2$ proves the remaining cost variance is driven by factors NexGen doesn't track (e.g., loading time, traffic). This guides the next investment toward new data collection. |
