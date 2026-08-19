import json
from datetime import datetime, timedelta
import great_expectations as ge

def validate_trafiklab_payload(json_data: dict) -> bool:
    """
    Validates a Trafiklab JSON payload using Great Expectations.
    This acts as a strict Data Contract. If the upstream API silently mutates,
    this validation will fail and halt the pipeline.
    """
    # Convert the raw JSON to a Pandas dataframe so GE can parse it easily
    # For a real payload, we extract the array of deviations/departures
    if "ResponseData" not in json_data or "Buses" not in json_data["ResponseData"]:
        return False
        
    df = ge.dataset.PandasDataset(json_data["ResponseData"]["Buses"])
    
    # Expected schema contracts
    df.expect_column_to_exist("LineNumber")
    df.expect_column_to_exist("Destination")
    df.expect_column_to_exist("ExpectedDateTime")
    df.expect_column_to_exist("TimeTabledDateTime")
    
    # Data quality contracts
    df.expect_column_values_to_not_be_null("LineNumber")
    df.expect_column_values_to_be_of_type("LineNumber", "str")
    
    # Run the validation suite
    results = df.validate()
    
    if not results["success"]:
        print(f"Schema Contract Violation: {json.dumps(results['statistics'])}")
        return False
        
    return True

if __name__ == "__main__":
    # Example payload matching Trafiklab format
    sample_payload = {
        "ResponseData": {
            "Buses": [
                {
                    "LineNumber": "4",
                    "Destination": "Gullmarsplan",
                    "ExpectedDateTime": "2023-10-10T14:30:00",
                    "TimeTabledDateTime": "2023-10-10T14:30:00"
                }
            ]
        }
    }
    
    is_valid = validate_trafiklab_payload(sample_payload)
    print(f"Payload valid: {is_valid}")
