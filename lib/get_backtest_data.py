import os
import typing

import pandas as pd
import yfinance


def get_backtest_data(tickers: typing.Set[str]) -> pd.DataFrame:
    # TODO: make sure all data is adjusted to the same date
    # (if writing to disc on Jan 1 but today is Dec 1, that's 11mo where dividends and splits may have invalided everything)

    # TODO: if current time is during market hours, then exclude today (yfinance inconsistent about including it)

    # TODO: use LETF synthesized data where possible

    tickers_to_fetch = []
    for ticker in tickers:
        path = f"data/adj-close_{ticker}.csv"
        if not os.path.exists(path):
            tickers_to_fetch.append(ticker)

    if tickers_to_fetch:
        data = yfinance.download(tickers_to_fetch)

        # yfinance behaves different depending on number of tickers
        if len(tickers_to_fetch) > 1:
            for ticker in tickers_to_fetch:
                path = f"data/adj-close_{ticker}.csv"
                data['Adj Close'][ticker].dropna().sort_index().to_csv(path)
        else:
            ticker = tickers_to_fetch[0]
            path = f"data/adj-close_{ticker}.csv"
            d = pd.DataFrame(data['Adj Close'])
            d = d.rename(columns={"Adj Close": ticker})
            d.to_csv(path)

    main_dataframe = None
    for ticker in tickers:
        path = f"data/adj-close_{ticker}.csv"
        data = pd.read_csv(path, index_col="Date", parse_dates=True)
        data = data.sort_index()

        if main_dataframe is None:
            main_dataframe = data
        else:
            main_dataframe = pd.concat([main_dataframe, data], axis=1)
    return typing.cast(pd.DataFrame, main_dataframe)
