FROM apache/spark:3.4.1-scala2.12-java11-python3-ubuntu

USER root

# Install Python ML dependencies
RUN pip3 install --no-cache-dir numpy pandas scikit-learn

# Create directory for scripts
RUN mkdir -p /opt/airflow/spark

# Switch back to default user (optional, but good practice, though compose overrides to root)
# USER spark
