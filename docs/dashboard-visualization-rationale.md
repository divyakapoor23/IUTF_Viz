# Why the Dash app uses these five charts

The dashboard takes readers from data coverage to traffic patterns during and after rain. It starts with how much evidence each city contributes, moves through comparisons with matched dry conditions, and ends with individual storms and recovery. The five views span two units of analysis: city-hours and qualifying rain events.

## The five dashboard views

| View | Why it belongs in the dashboard |
| --- | --- |
| **Rainfall coverage** | Stacked city-hours show how much data each city contributes by rainfall class. The hours view exposes unequal sample sizes, and the percentage view shows the mix of rainfall classes within each city. This gives readers the context needed to interpret the later comparisons. |
| **Traffic flow by rainfall intensity** | The heatmap brings eight cities and five rainfall classes into one view. Signed values show the direction and size of median deviations from matched dry flow. Support labels distinguish sparse or missing cells from measured values near zero. |
| **Traffic patterns by hour of day** | Paired dry and rainy profiles show when deviations differ across the recorded clock day. The sample-count bars help readers judge how much evidence supports each comparison. The profile always includes both dry and rainy hours. |
| **Storm intensity vs. traffic disruption** | Each point pairs a qualifying event’s peak rainfall with its lowest flow deviation during rain. Readers can see variation between storms, including similarly intense events with different flow patterns. In the notebook app, selecting a storm highlights its corresponding recovery trajectory. |
| **Traffic flow after rain ends** | Aligning events at the first dry hour makes their timelines comparable. City panels show the median trajectory, the middle half of observed deviations, and the number of events contributing at each hour. These cues help readers account for variable follow-up. |

## Why the exploratory plots stay in the notebook

Section 7a supports follow-up questions after a reader has seen the main comparisons. Five additional plots are especially useful for investigating details that the dashboard summarizes.

| Exploratory plot | What it adds |
| --- | --- |
| **Rainfall intensity and flow deviation scatter** | Shows individual rainy city-hours. It is useful for inspecting outliers and within-class variation after identifying a pattern in the heatmap. Repeated observations can make the scatter dense at a glance. |
| **Daily rainfall calendar** | Shows when recorded precipitation occurred and where daily coverage is partial. It is useful for checking a city’s observation period and seasonal gaps. The dashboard’s coverage bars summarize the evidence across cities directly. |
| **Recovery outcomes by city** | Breaks qualifying events into no measured deficit, confirmed recovery, and unconfirmed recovery. It is useful for auditing counts behind the recovery summary and comparing outcomes across cities. |
| **Distribution of flow deviations** | Shows the spread, median, and outliers within rainfall classes. It is useful for checking how much variation sits behind the heatmap medians. |
| **Event duration and recovery follow-up** | Examines a narrower question about duration among events with a measured deficit. It shows unconfirmed events at their last observed follow-up hour, which requires distinguishing follow-up length from confirmation time. |

The hour-of-day profile appears in both places. In the notebook it supports standalone exploration, and in Dash it contributes to the shared city and day-type comparison.
