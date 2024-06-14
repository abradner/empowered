import pandas as pd
import json


# Helper function to map days to DataFrame index (0 = Monday, 6 = Sunday)
def map_days(days):
    day_map = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}
    days_list = days.replace('Business Days', 'Monday|Tuesday|Wednesday|Thursday|Friday').split('|')
    return [day_map[day] for day in days_list]


def load_rate_plan(filepath):

    # Load the JSON data
    with open(filepath, 'r') as file:
        data = json.load(file)

    # Initialize DataFrames
    solar_df = pd.DataFrame(0.0, index=range(7), columns=range(24))  # 7 days, 24 hours
    variable_df = pd.DataFrame(0.0, index=range(7), columns=range(24))  # 7 days, 24 hours

    # Populate the solar feed-in tariff DataFrame
    solar_rate = data['data']['planData']['contract'][0]['solarFit'][0]['rate']
    solar_df[:] = solar_rate

    # Populate the variable tariffs DataFrame
    for block in data['data']['planData']['contract'][0]['tariffPeriod'][0]['touBlock']:
        price = block['blockRate'][0]['unitPrice']
        for period in block['timeOfUse']:
            days = map_days(period['days'])
            start_hour = int(period['startTime']) // 100
            end_hour = int(period['endTime']) // 100

            if end_hour < start_hour:
                # Handle wrap-around from one day to the next
                evening_hours = list(range(start_hour, 24))
                morning_hours = list(range(0, end_hour + 1))
            else:
                evening_hours = []
                morning_hours = list(range(start_hour, end_hour + 1 if period['endTime'].endswith('59') else end_hour))

            for day in days:
                if evening_hours:
                    variable_df.loc[day, evening_hours] = price
                variable_df.loc[day, morning_hours] = price

    # Convert to float for compatibility, but keep hours as strings
    solar_df = solar_df.astype(float)
    # solar_df.columns = solar_df.columns.astype(str)
    solar_df.columns = [str(col) for col in solar_df.columns]
    variable_df = variable_df.astype(float)
    # variable_df.columns = variable_df.columns.astype(str)
    variable_df.columns = [str(col) for col in variable_df.columns]



    # Extract the supply charge
    supply_charge = data['data']['planData']['contract'][0]['tariffPeriod'][0]['dailySupplyCharge']

    print("Solar Feed-in Tariff DataFrame:")
    print(solar_df)
    print("\nVariable Tariff DataFrame:")
    print(variable_df)
    print("\nSupply Charge:")
    print(supply_charge)

    return solar_df, variable_df, supply_charge
