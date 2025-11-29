# ML Setup Notes

## ✅ Automated Setup Complete

The Spark environment is now fully automated via `docker-compose.yml` and `spark/Dockerfile`.

**What's Automated:**
- **Dependencies**: `numpy`, `pandas`, `scikit-learn` are installed automatically during build.
- **Scripts**: The local `spark/` folder is mounted to `/opt/airflow/spark` in the container. Any changes to local scripts are immediately visible.

**No manual setup is required after restarting Docker.**

## Testing ML Training

You can trigger the ML training DAG:

```powershell
# Via Airflow UI: http://localhost:8081 → DAGs → ml_training → Trigger

# Via command line:
docker exec airflow-webserver airflow dags trigger ml_training
```

**Expected Runtime**: 5-10 minutes

**What to monitor**:
- Check Airflow UI for progress
- Watch Spark Master UI: http://localhost:8090
- Check logs if errors occur

## After Training

Verify model was saved:
```powershell
# Check MinIO Console: http://localhost:9001
# Look in: retail-lake bucket → models folder
```

Generate predictions:
```powershell
docker exec airflow-webserver airflow dags trigger ml_daily_predictions
```
