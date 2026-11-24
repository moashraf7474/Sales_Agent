# Sales Insights Agent

A dashboard-first sales analysis agent for CSV and Excel files. It turns raw sales records into an executive dashboard, highlights important trends and opportunities, and lets users ask follow-up questions in plain English.

## Project idea

Sales teams often have useful data in spreadsheets but need time to clean it, calculate totals, find trends, and prepare reports. This agent reduces that manual work:

1. The user uploads a sales CSV or Excel file.
2. The app detects the date, product, location, quantity, price, and revenue columns.
3. It calculates KPIs and aggregates the data locally with pandas.
4. Plotly charts present revenue trends, top products, stagnant products, and location performance.
5. The app identifies the strongest and weakest products and summarizes them as insights.
6. An optional OpenRouter AI agent answers additional questions using the uploaded DataFrame.

The goal is to make sales analysis accessible to users who are not data analysts. The dashboard provides an immediate answer, while the chatbot is available for deeper analysis.

## How the agent works

1. **File upload:** Streamlit loads CSV or Excel data into a pandas DataFrame.
2. **Column detection:** The app recognizes common names such as `date`, `product`, `city`, `quantity`, `unit_price`, `total`, and `revenue`.
3. **Automatic calculations:** It calculates total revenue, order count, average order value, product revenue, location revenue, and daily revenue.
4. **Dashboard generation:** KPIs are displayed as metric cards and aggregation results become Plotly charts.
5. **Insight generation:** The app compares product totals and identifies the best-selling and lowest-selling products.
6. **Optional chatbot loop:** The AI receives the question and tool definitions, requests a tool such as `inspect_data` or `run_python`, and uses the tool output to continue analysis.
7. **Final answer:** The AI produces a text response after it has gathered enough evidence from the data.

```text
Upload sales file
       |
       v
Load and inspect DataFrame
       |
       v
Detect columns and calculate totals
       |
       v
+------+-------------------+
| Sales dashboard         |
| KPIs + charts + insights|
+------+-------------------+
       |
       v
Optional AI chat + pandas analysis
```

## Dashboard features

- Total revenue
- Number of orders
- Average order value
- Best-selling product
- Revenue over time
- Top 10 products
- Lowest-selling products
- Revenue by city, branch, region, or category
- Key findings and sales opportunities
- Downloadable dashboard CSV

The main dashboard works without an API key. An OpenRouter key is only required for the AI chat follow-up.

## How the optional AI agent works

```text
Question -> OpenRouter -> tool request
                     <- tool result
Repeats until it produces an answer
```

Available tools:

- `inspect_data` - examines columns and sample rows
- `run_python` - calculates and analyzes pandas data
- `add_kpi` - adds a key-number card

## Run the app

```bash
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Open `http://localhost:8501`, upload `sample_sales.csv`, or upload another CSV/Excel sales file.

## Optional OpenRouter setup

1. Create a free key at <https://openrouter.ai/settings/keys>.
2. Enter the key in the **OpenRouter API Key** field, or add it to `.env`:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=openrouter/free
```

To use another model, change `OPENROUTER_MODEL`.

## Suggested questions

- Which products generated the most and least revenue?
- Which city or location has the highest sales?
- Which days had the strongest sales?
- Which products should receive a promotion?
- Compare sales between two locations.
- What are the main sales trends?
- Which products are slowing down in sales?
- Give me three practical recommendations to increase revenue.
- Identify unusual spikes or drops in revenue.
- What would be the best product bundle to offer?

## Sample data

To regenerate `sample_sales.csv`:

```bash
python make_sample_data.py
```

The sample file contains 1,500 sales records.

## Notes

- Revenue is read from a `total`, `revenue`, `sales`, `amount`, or `sales_amount` column. If no total column exists, the app calculates revenue as `quantity * unit_price`.
- Product, date, and location columns are detected using common names.
- `run_python` executes model-generated Python code on the local machine. Use the app locally and do not expose it to the public internet without sandboxing.
- Free-model availability and request limits can change.

## Ideas to extend

- **Filters:** add date, product, city, branch, and category filters to update every KPI and chart.
- **Advanced comparisons:** compare two periods, cities, products, or sales channels.
- **Anomaly detection:** identify unusual sales spikes and drops automatically.
- **Trend forecasting:** estimate next month's revenue and show confidence ranges.
- **Customer insights:** segment customers and calculate repeat purchases when customer data is available.
- **Inventory planning:** combine sales velocity with stock levels to recommend reorder quantities.
- **Promotion recommendations:** rank products and categories by promotion potential.
- **Product bundles:** suggest products that are frequently sold together.
- **Targets and budgets:** compare actual revenue with monthly sales targets.
- **Exports:** download a PDF or HTML dashboard and export charts as images.
- **Scheduled reports:** email or save a daily, weekly, or monthly sales report.
- **Database support:** load data from SQL databases, Google Sheets, or a cloud warehouse.
- **Uploaded-file history:** save and compare multiple sales files across sessions.
- **Model selection:** let users choose free or paid OpenRouter models from the sidebar.
- **Caching:** cache uploaded and aggregated data for faster dashboard updates.
- **Authentication:** add user accounts and role-based access before public deployment.
