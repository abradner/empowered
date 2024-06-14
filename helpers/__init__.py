def map_numeric_day_to_name(day):
    return {
        0: 'Monday',
        1: 'Tuesday',
        2: 'Wednesday',
        3: 'Thursday',
        4: 'Friday',
        5: 'Saturday',
        6: 'Sunday'
    }[day]


def map_df_day_to_name(df):
    df['weekday'] = df.index.map(map_numeric_day_to_name)
    df.set_index('weekday', inplace=True)
    return df
