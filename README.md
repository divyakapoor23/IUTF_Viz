# Rainfall and Traffic Flow Across Eight Cities

This project explores how hourly rainfall relates to traffic flow in eight cities and how flow changes after well-observed rain events. The analysis is descriptive; it does not establish that rain caused a traffic change.

## Run the notebook

Open [Project2.ipynb in Google Colab](https://colab.research.google.com/github/divyakapoor23/IUTF_Viz/blob/main/Project2.ipynb) and run the notebook from top to bottom. The default source is the public Google Cloud Storage CSV configured in the notebook. It streams the source and retains the selected cities, so no local data-file upload is required.

Colab will ask you to authorize Google Sheets and Drive access. The notebook creates or reuses a spreadsheet named `IUTF_Viz_Rainfall_Traffic_Analysis_google_cloud` for the default source, publishes the processed analysis tables, and sets viewer access for anyone with the link. The title ends with the selected `DATA_SOURCE` value, keeping tables from different sources separate. Enable the Google Sheets API and Google Drive API if your account's Google Cloud project reports that either API is disabled. The sheet contains the hourly summaries, qualifying rain events, and recovery curves used by the app.

After the analysis and publication complete, run the single `# @title My Web App` cell. It loads the tables from Google Sheets and starts the Dash application through the Colab port proxy. The link is valid while that Colab runtime is active; this is not an always-on Render deployment.

## Visualizations

1. **Rainfall coverage:** stacked city-hour counts by rainfall class, including unknown weather; switch between hours and within-city percentages.
2. **Traffic flow by rainfall intensity:** a zero-centered heatmap of median percentage change from matched dry baselines. Estimates require at least 10 supported hours across 3 dates; missing and insufficient cells are labelled.
3. **Traffic flow after rain ends:** event-aligned city panels with event medians and middle-50% bands. Bands show event variation, not confidence intervals.

The responsive dashboard filters all relevant charts and KPI cards by city, weekday/weekend, and rainfall intensity. It includes data-derived insights and sample-size guidance.

The sage-and-cream interface uses a zero-centered brown-to-teal intensity scale with dark heatmap labels for contrast; the rainfall legend uses ordered colors plus a hatch for unknown weather.

## Data and limitations

The cloud CSV's original weather-match status and raw timestamps are unavailable, so imputed zeros may be mistaken for dry weather and the weather join cannot be fully audited. Cloud-derived comparisons are provisional. Cities have unequal observation periods and seasons, and the analysis does not adjust for holidays or seasonal effects. Recovery depends on available sensor panels and limited follow-up. Findings describe associations, not causal effects.

The optional raw-Parquet mode and full-city audit require separate local source folders; they are not used in the default Colab workflow.

## Walkthrough

**Stream recording link: to be added by the author.** The required face-camera walkthrough and Stream sharing verification must be completed after running the notebook with current data.
