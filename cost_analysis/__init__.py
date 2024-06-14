
def calculate_costs(df_generation, df_consumption, df_fit, df_rates, supply_charge):

    # Calculate the feed-in energy
    df_feed_in = df_generation * df_fit

    # Calculate the cost of energy consumed
    df_cost = df_consumption * df_rates

    # Add a column to each row for the supply charge
    df_cost['Supply Charge'] = supply_charge

    # Calculate the total daily cost
    df_cost['Total Cost'] = df_cost.sum(axis=1)

    # Calculate the total daily generation rebate
    df_feed_in['Total Generation'] = df_feed_in.sum(axis=1)

    df_net = df_cost['Total Cost'] - df_feed_in['Total Generation']

    return df_cost, df_feed_in, df_net
