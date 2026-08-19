import pandas as pd
import statsmodels.api as sm

def train_state_space_model(delay_series):
    """
    Trains a Bayesian Structural Time Series / Unobserved Components model.
    
    This models the transit delay as a combination of:
    1. A local level (hidden state for baseline congestion)
    2. A seasonal component (e.g., daily rush hour patterns)
    
    Args:
        delay_series (pd.Series): A time-indexed pandas Series of delays for a specific station/route.
    """
    
    # Define an Unobserved Components model
    # 'local level' allows the baseline delay to randomly walk (modeling structural shifts)
    # 'freq_seasonal' models the daily/hourly seasonality
    
    # Note: Depending on the sampling frequency, adjust the seasonal period
    model = sm.tsa.UnobservedComponents(
        delay_series,
        level='local level',
        freq_seasonal=[{'period': 24, 'harmonics': 3}] # Example: 24-hour cycle
    )
    
    print("Fitting State Space Model via Maximum Likelihood...")
    results = model.fit(disp=False)
    
    print(results.summary())
    return results

def predict_future_delays(ssm_results, steps=5):
    """
    Forecast future delays using the Kalman Filter internal to the fitted model.
    """
    forecast = ssm_results.get_forecast(steps=steps)
    mean_forecast = forecast.predicted_mean
    conf_intervals = forecast.conf_int()
    
    return mean_forecast, conf_intervals
