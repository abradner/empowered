import pandas as pd
from io import StringIO


# Data Shape and Structure
# 
# 1. Dual CSVs in One File:
#   - The file appears to contain two distinct CSV sections.
#       Each section starts with metadata headers and ends with a footer row containing a total for the period.
#   - The first section deals with solar feed-in, and the second section deals with energy consumption.
# 2. Header Information:
#   - Each section begins with three header lines:
#   - The first header provides general information (e.g., Nmi number and network type).
#   - The second header identifies the meter involved and the type of data recorded (e.g., solar or consumption).
#   - The third header indicates the time zone.
# 3. Data Columns:
#   - Following the headers, there is a row specifying the column names,
#       primarily consisting of time intervals in 5-minute blocks across a 24-hour period.
#   - Data rows follow this header, with each row starting with a date and then data values for each time interval.
# 4. Footer Rows:
#   - Each section concludes with a footer row that aggregates the totals
#       for the period, which we will need to exclude during parsing.

def load_energy_data(filepath):

    # Open and read all lines
    with open(filepath, 'r') as file:
        data = file.readlines()

    # Find the index of the total row to split the data
    # the total row starts with 'Total for Period'
    halfway = data.index([x for x in data if x.startswith('Total for Period')][0])

    first_half = data[:halfway]
    second_half = data[halfway:]

    # Now we need to exclude the metadata rows and the footer row from each section
    # The metadata rows are the first three rows of each section
    first_half = first_half[3:-1]
    second_half = second_half[3:-1]

    # use pandas.read_csv to read the data
    # the first row contains the column headers

    df1 = pd.read_csv(StringIO('\n'.join(first_half)))
    df2 = pd.read_csv(StringIO('\n'.join(second_half)))



    # # now we can create the dataframes from the remaining rows
    # df1 = pd.DataFrame([x.strip().split(',') for x in first_half[4:-1]], columns=col_headers1.strip().split(','))
    # df2 = pd.DataFrame([x.strip().split(',') for x in second_half[4:-1]], columns=col_headers2.strip().split(','))

    # # for each numeric column, convert to float
    # for col in df1.columns:
    #     if col != 'Date/Time':
    #         df1[col] = df1[col].astype(float)
    #         df2[col] = df2[col].astype(float)

    return df1, df2


def group_by_hour(df, index_name):
    # Remove any non-time columns like 'Date/Time', 'Quality', 'Total' if they exist in the DataFrame
    time_columns = [col for col in df.columns if ':' in col]

    # Create a new DataFrame to store the hourly sums
    hourly_data = pd.DataFrame()

    # The DataFrame index (for merging later)
    hourly_data[index_name] = df[index_name]

    # Loop through each hour (0 to 23) and sum the corresponding 12 columns for each hour
    for hour in range(24):
        # Generate column names for this hour
        columns = [f'{hour}:{minute:02}' for minute in range(0, 60, 5)]

        # Select only the columns that exist in the DataFrame to handle cases where some columns might be missing
        valid_columns = [col for col in columns if col in time_columns]

        # Sum these columns and add to the hourly_data DataFrame
        hourly_data[f'{hour}'] = df[valid_columns].sum(axis=1)

    return hourly_data


def add_metadata(df):
    # Add metadata to the DataFrame
    df['date'] = pd.to_datetime(df['Date/Time'], format='%Y%m%d')
    df['month'] = df['date'].dt.month
    df['dayofweek'] = df['date'].dt.dayofweek
    return df


def prepare_df(df):
    df = group_by_hour(df, 'Date/Time')
    df = add_metadata(df)
    return df
