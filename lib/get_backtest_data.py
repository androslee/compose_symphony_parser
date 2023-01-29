import os
import typing
import csv
import requests
import pandas as pd
import yfinance
import random
import string

"""
 Generate a random string that we can use for folder names to store data in so that harmony can be run in parallel 
 without different processes interfering with each other.
"""
def random_string(string_length=10):
    """Generate a random string of fixed length """
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(string_length))

"""
 yfinance changed the way they report dates at some point in Jan 2023. They used to return year-month-day, now there's
 an added timezone correction. The yfinance python library devs might fix this, so the following hack is meant to be 
 something that won't break once they do. To do that, clean_date_column() is dead simple, we simply remove everything 
 after the year-month-day portion that we need for adjusted close prices before feeding the yfinance data to functions 
 downstream.
"""
def clean_date_column(input_file, output_file):
    with open(input_file, 'r') as f_input, open(output_file, 'w', newline='') as f_output:
        csv_reader = csv.reader(f_input)
        csv_writer = csv.writer(f_output)
        headers = next(csv_reader)
        csv_writer.writerow(headers)
        for row in csv_reader:
            date = row[0].split(" ", 1)[0]
            row[0] = date
            csv_writer.writerow(row)

def get_backtest_data(tickers: typing.Set[str], use_simulated_data: bool = False) -> pd.DataFrame:
    if not os.path.exists("data"):
        os.mkdir("data")

    random_folder = random_string()
    output_folder = f"work/{random_folder}"
    print(f'random_folder : {random_folder}')
    print(f'output_folder : {output_folder}')
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # TODO: make sure all data is adjusted to the same date
    # (if writing to disc on Jan 1 but today is Dec 1, that's 11mo where dividends and splits may have invalided everything)
    # TODO: if current time is during market hours, then exclude today (yfinance inconsistent about including it)

    tickers_to_fetch = []
    for ticker in tickers:
        path = f"{output_folder}/adj-close_{ticker}.csv"
        if not os.path.exists(path):
            tickers_to_fetch.append(ticker)

    if tickers_to_fetch:
        data = yfinance.download(tickers_to_fetch)
        # yfinance behaves different depending on number of tickers
        if len(tickers_to_fetch) > 1:
            for ticker in tickers_to_fetch:
                path = f"{output_folder}/adj-close_{ticker}.csv"

                data['Adj Close'][ticker].dropna().sort_index().to_csv(path)

        else:
            ticker = tickers_to_fetch[0]
            path = f"{output_folder}/adj-close_{ticker}.csv"
            d = pd.DataFrame(data['Adj Close'])
            d = d.rename(columns={"Adj Close": ticker})
            d.to_csv(path)

    for file_name in os.listdir(output_folder):
        if os.path.splitext(file_name)[1] == '.csv':
           input_file = f"{output_folder}/{file_name}"
           output_file = f"{output_folder}/{file_name.split('.')[0]}_clean.csv"
           clean_date_column(input_file, output_file)

    main_dataframe = None
    for ticker in tickers:
        path = f"{output_folder}/adj-close_{ticker}_clean.csv"
        data = pd.read_csv(path, index_col="Date", parse_dates=True)
        data = data.sort_index()

        if main_dataframe is None:
            main_dataframe = data
        else:
            main_dataframe = pd.concat([main_dataframe, data], axis=1)

    main_dataframe = typing.cast(pd.DataFrame, main_dataframe)

    if use_simulated_data:
        filepath = "data/simulated_data.csv"
        if not os.path.exists(filepath):
            response = requests.get(
                "https://raw.githubusercontent.com/Newtoniano/simulated-leveraged-etf/master/extended-leveraged-etfs.csv")
            with open(filepath, 'w') as f:
                f.write(response.text)
        simulated_data = pd.read_csv(filepath, index_col=0, parse_dates=True)
        reconstructed_columns = []
        for ticker in main_dataframe.columns:
            if ticker in simulated_data.columns:
                combined_series = main_dataframe[ticker].combine_first(
                    simulated_data[ticker])
                reconstructed_columns.append(combined_series)
            else:
                reconstructed_columns.append(main_dataframe[ticker])

        main_simulated_dataframe = pd.concat(
            reconstructed_columns, axis=1).astype("float64")

        return typing.cast(pd.DataFrame, main_simulated_dataframe)

    return typing.cast(pd.DataFrame, main_dataframe)


def main():
    print(get_backtest_data(set(['SPY', 'UVXY', 'TLT']), True))
