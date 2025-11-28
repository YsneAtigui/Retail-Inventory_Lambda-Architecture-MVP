# Gemini / Google Slides Prompts

Copy and paste these prompts into the "Help me visualize" or "Create slide" feature in Google Slides (Gemini sidebar).

## Slide 1: Title Slide
**Prompt:**
> Create a professional title slide with the main title "Retail Inventory Management System" and subtitle "A Lambda Architecture MVP for Real-Time & Batch Analytics". Use a sleek, modern background image featuring abstract blue digital data streams connecting to a retail store icon.

## Slide 2: The Problem
**Prompt:**
> Create a slide titled "The Problem: Retail Data Challenges". Add a bulleted list with these points: "Retailers generate massive data every second", "Latency issues: Need real-time stock visibility", "Accuracy needs: Analyzing months of history", "Forecasting: Predicting demand to avoid stockouts". Add an image on the right showing a busy supermarket aisle with a digital overlay representing data overload.

## Slide 3: The Solution - Lambda Architecture
**Prompt:**
> Create a slide titled "The Solution: Lambda Architecture". Add a split layout. On the left, bullet points: "Hybrid approach for data processing", "Speed Layer: Low latency, real-time views (Kafka)", "Batch Layer: High accuracy, historical views (Spark)", "Serving Layer: Unified view (ClickHouse)". On the right, generate a diagram showing two parallel data pipelines merging into one.

## Slide 4: Technology Stack
**Prompt:**
> Create a slide titled "Technology Stack". Use a grid layout to list these technologies: "Ingestion: Apache Kafka", "Processing: Apache Spark", "Orchestration: Apache Airflow", "Storage: MinIO (Data Lake) & ClickHouse (Data Warehouse)", "Visualization: Power BI", "Infrastructure: Docker". Add a background with a subtle tech circuit pattern.

## Slide 5: Real-Time Analytics (Speed Layer)
**Prompt:**
> Create a slide titled "Key Feature: Real-Time Analytics". Add bullet points: "Data Flow: Producer -> Kafka -> ClickHouse", "Latency: Sub-second availability", "Use Case: Live sales dashboards and instant stock updates". Add an image showing a futuristic dashboard monitor displaying live sales graphs and charts.

## Slide 6: Machine Learning & Forecasting (Batch Layer)
**Prompt:**
> Create a slide titled "Key Feature: ML & Forecasting". Add bullet points: "Goal: Predict product demand 7 days ahead", "Model: Random Forest Regressor via Spark MLlib", "Features: Seasonality, Historical Demand, Holidays", "Pipeline: Automated weekly training via Airflow". Add an illustration of a brain or neural network connecting to a calendar.

## Slide 7: Demo Walkthrough
**Prompt:**
> Create a slide titled "System Demo". Add a numbered list: "1. Airflow UI: Orchestrating the ML pipeline", "2. ClickHouse: Querying the predictions", "3. Power BI: Visualizing the final forecast". Add a placeholder image frame titled "Live Demo Video".

## Slide 8: Challenges & Learnings
**Prompt:**
> Create a slide titled "Challenges & Learnings". Add a bulleted list: "Complexity: Orchestrating 6+ distributed services", "Data Consistency: Merging real-time streams with batch data", "Resource Management: Optimizing Docker memory usage". Add an icon of a puzzle being solved or a balancing scale.

## Slide 9: Future Improvements
**Prompt:**
> Create a slide titled "Future Improvements". Add a timeline or list layout with: "Scalability: Deploy to Kubernetes (K8s)", "Advanced ML: Implement Deep Learning (LSTM)", "Alerting: Real-time Slack notifications for low stock". Add a background image of a roadmap or an upward trending arrow.

## Slide 10: Conclusion
**Prompt:**
> Create a summary slide titled "Conclusion". Add text: "Successfully built a scalable, modern data platform for retail. Enables data-driven decisions through real-time insights and accurate forecasting." Add a large "Thank You" text at the bottom and a placeholder for "Q&A".
