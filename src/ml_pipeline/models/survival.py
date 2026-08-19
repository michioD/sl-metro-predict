import pandas as pd
from lifelines import CoxPHFitter

def train_cox_survival_model(delay_df):
    """
    Trains a Cox Proportional Hazards model on transit delay data.
    
    Instead of predicting the magnitude of the delay directly, this models 
    the "time until the train arrives" (survival time).
    
    Expected DataFrame format:
    - duration: Time observed (e.g., scheduled arrival time minus current time)
    - event_observed: 1 if the train arrived, 0 if it is still delayed (right-censored)
    - peak_hour: Covariate (binary)
    - distance_from_hub: Covariate (continuous)
    """
    cph = CoxPHFitter()
    
    # Fit the model: 'duration' is the time-to-event, 'event_observed' is the censoring flag
    cph.fit(delay_df, duration_col='duration', event_col='event_observed')
    
    print("Cox Proportional Hazards Model Summary:")
    cph.print_summary()
    
    # We can predict the partial hazard (relative risk of delay) for new data
    # or predict the expected time to arrival (expected survival time)
    return cph

def predict_time_to_arrival(cph_model, new_covariates_df):
    """
    Given the trained Cox model and real-time covariates (weather, time of day),
    predict the median expected time until the train arrives.
    """
    # Predict the median survival time (when probability of train NOT arriving hits 50%)
    median_times = cph_model.predict_median(new_covariates_df)
    return median_times
