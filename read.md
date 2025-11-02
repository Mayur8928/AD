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
